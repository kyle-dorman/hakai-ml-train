"""Predict cleaned TIFFs sequentially using a copied model and plain accumulators."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from kelpseg.model_bundle import PortableModel, load_model_bundle
from kelpseg.prediction.settings import PredictionSettings, Source, read_sources
from kelpseg.prediction.windows import prediction_windows
from kelpseg.preprocessing import native_validity

logger = logging.getLogger(__name__)
WINDOW_COLUMNS = (
    "source_key",
    "row",
    "col",
    "height",
    "width",
    "pad_top",
    "pad_bottom",
    "pad_left",
    "pad_right",
    "valid_fraction",
    "disposition",
)
COUNT_COLUMNS = (
    "total_pixels",
    "valid_pixels",
    "nodata_pixels",
    "predicted_valid_pixels",
    "uncovered_valid_pixels",
    "candidate_windows",
    "predicted_windows",
    "skipped_windows",
)


def _accumulate(
    model: PortableModel,
    images: list[np.ndarray],
    windows: list[Window],
    band_names: tuple[str, ...],
    sums: np.ndarray,
    counts: np.ndarray,
) -> None:
    """Add one batch's valid probabilities to source sums/counts in place."""
    predictions = model.predict_batch(images, band_names)
    for window, probability in zip(windows, predictions, strict=True):
        row, col = int(window.row_off), int(window.col_off)
        height, width = probability.shape
        # Nodata is NaN; it must contribute neither probability nor weight.
        valid = np.isfinite(probability)
        sums[row : row + height, col : col + width] += np.where(valid, probability, 0)
        counts[row : row + height, col : col + width] += valid


def _write_rasters(
    source: rasterio.io.DatasetReader,
    probability_path: Path,
    mask_path: Path,
    probabilities: np.ndarray,
    mask: np.ndarray,
) -> None:
    """Write probability/mask TIFFs on the source grid without stale source metadata."""
    profile = dict(
        driver="GTiff",
        height=source.height,
        width=source.width,
        count=1,
        crs=source.crs,
        transform=source.transform,
        compress="deflate",
        BIGTIFF="IF_SAFER",
    )
    for path, array, nodata in (
        (probability_path, probabilities, np.nan),
        (mask_path, mask, 255),
    ):
        with rasterio.open(
            path, "w", **profile, dtype=array.dtype, nodata=nodata
        ) as destination:
            destination.write(array, 1)


def _predict_source(
    source: Source,
    model: PortableModel,
    settings: PredictionSettings,
    window_writer: csv.DictWriter,
) -> dict:
    """Read a source's tiles, reconstruct probabilities, write rasters and counts."""
    size = model.metadata["input_size"]
    candidate = retained = 0
    with rasterio.open(source.image, GEOREF_SOURCES="INTERNAL") as image:
        shape = (image.height, image.width)
        sums = np.zeros(shape, dtype=np.float32)
        counts = np.zeros(shape, dtype=np.uint32)
        native_valid = np.zeros(shape, dtype=bool)
        batch_images, batch_windows = [], []
        for window in prediction_windows(
            image.width, image.height, size, settings.stride
        ):
            values = np.moveaxis(image.read(window=window), 0, -1)
            valid = native_validity(values)
            row, col = int(window.row_off), int(window.col_off)
            height, width = valid.shape
            # Include skipped windows here so their uncovered valid pixels count.
            native_valid[row : row + height, col : col + width] |= valid
            valid_pixels = int(valid.sum())
            fraction = valid_pixels / valid.size
            keep = valid_pixels > 0 and fraction >= settings.min_valid_fraction
            candidate += 1
            window_writer.writerow(
                dict(
                    source_key=source.source_key,
                    row=row,
                    col=col,
                    height=height,
                    width=width,
                    pad_top=0,
                    pad_bottom=size - height,
                    pad_left=0,
                    pad_right=size - width,
                    valid_fraction=fraction,
                    disposition="retained" if keep else "skipped_nodata",
                )
            )
            if keep:
                retained += 1
                batch_images.append(values)
                batch_windows.append(window)
                if len(batch_images) == settings.batch_size:
                    _accumulate(
                        model,
                        batch_images,
                        batch_windows,
                        source.band_names,
                        sums,
                        counts,
                    )
                    batch_images.clear()
                    batch_windows.clear()
            if candidate % 10 == 0:
                logger.info(
                    "%s: %d windows read; %d retained",
                    source.source_key,
                    candidate,
                    retained,
                )
        if batch_images:
            _accumulate(
                model, batch_images, batch_windows, source.band_names, sums, counts
            )

        # Each source pixel gets one averaged probability, then one classification.
        covered = counts > 0
        np.divide(sums, counts, out=sums, where=covered)
        sums[~covered] = np.nan
        mask = np.full(shape, 255, dtype=np.uint8)
        mask[covered] = sums[covered] >= model.metadata["threshold"]
        probability_path = Path("probabilities") / f"{source.source_key}.tif"
        mask_path = Path("masks") / f"{source.source_key}.tif"
        _write_rasters(
            image,
            settings.output / probability_path,
            settings.output / mask_path,
            sums,
            mask,
        )

    valid_count = int(native_valid.sum())
    predicted_count = int(covered.sum())
    logger.info(
        "%s: predicted %d/%d valid pixels; %d uncovered; %d/%d windows retained",
        source.source_key,
        predicted_count,
        valid_count,
        valid_count - predicted_count,
        retained,
        candidate,
    )
    return dict(
        source_key=source.source_key,
        image=str(source.image),
        band_names=";".join(source.band_names),
        **source.identity,
        probability=probability_path.as_posix(),
        mask=mask_path.as_posix(),
        total_pixels=int(native_valid.size),
        valid_pixels=valid_count,
        nodata_pixels=int(native_valid.size) - valid_count,
        predicted_valid_pixels=predicted_count,
        uncovered_valid_pixels=valid_count - predicted_count,
        candidate_windows=candidate,
        predicted_windows=retained,
        skipped_windows=candidate - retained,
    )


def _write_json(path: Path, value: dict) -> None:
    """Publish a complete JSON document by replacing its temporary sibling."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def predict(settings: PredictionSettings) -> Path:
    """Predict declared cleaned sources into a fresh directory; stop on failure.

    Uses one source's in-memory sum/count/validity arrays and bounded tile batches.
    No labels are read. A failed output is left for inspection, never resumed.
    Returns the completed output directory.
    """
    if settings.output.exists():
        raise ValueError(
            f"Output already exists: {settings.output}. Choose a fresh directory."
        )
    model = load_model_bundle(settings.model, device=settings.device)
    sources = read_sources(settings, model.metadata["band_names"])
    logger.info(
        "Model: %s; bands: %s; sources: %d; output: %s",
        settings.model,
        model.metadata["band_names"],
        len(sources),
        settings.output,
    )
    settings.output.mkdir(parents=True)
    (settings.output / "probabilities").mkdir()
    (settings.output / "masks").mkdir()
    resolved = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in asdict(settings).items()
    }
    _write_json(
        settings.output / "settings.json", dict(recipe=resolved, model=model.metadata)
    )
    rows = []
    windows_tmp = settings.output / "windows.tmp"
    with windows_tmp.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=WINDOW_COLUMNS)
        writer.writeheader()
        for index, source in enumerate(sources, 1):
            logger.info(
                "Source %d/%d: %s (%s)",
                index,
                len(sources),
                source.source_key,
                source.image,
            )
            rows.append(_predict_source(source, model, settings, writer))
    sources_tmp = settings.output / "sources.tmp"
    with sources_tmp.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    windows_tmp.replace(settings.output / "windows.csv")
    sources_tmp.replace(settings.output / "sources.csv")
    totals = {name: sum(row[name] for row in rows) for name in COUNT_COLUMNS}
    _write_json(
        settings.output / "summary.json",
        dict(status="complete", sources=len(rows), **totals),
    )
    return settings.output
