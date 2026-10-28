"""Read true-size windows sequentially and publish one fresh chip directory."""

from __future__ import annotations

import csv
import json
import logging
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path

import numpy as np
import rasterio

from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.chip_inputs import ChipPlan, chip_windows
from kelpseg.prepare.nodata import nodata_mask

logger = logging.getLogger(__name__)
WINDOW_COLUMNS = (
    "source_key",
    "row",
    "col",
    "height",
    "width",
    "original_row",
    "original_col",
    "nodata_pixels",
    "background_pixels",
    "kelp_pixels",
    "ignored_pixels",
    "valid_ignored_pixels",
    "disposition",
    "payload",
)


def map_labels(
    stored: np.ndarray, mapping: dict[int, int], invalid: np.ndarray
) -> np.ndarray:
    """Map stored categories, preserving background even if label nodata is zero."""
    target = np.empty(stored.shape, dtype=np.int8)
    for category in np.unique(stored):
        if int(category) not in mapping:
            raise PreparationError(
                f"Unmapped label category {category}; correct label_mapping or use check/clean first."
            )
        target[stored == category] = mapping[int(category)]
    target[invalid] = -100
    return target


def _write_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def _window_record(source, window, invalid, target) -> dict:
    """Keep true window placement and separate source-nodata/target counts."""
    row, col = int(window.row_off), int(window.col_off)
    record = dict(
        source_key=source["source_key"],
        row=row,
        col=col,
        height=int(window.height),
        width=int(window.width),
        original_row=source["row_offset"] + row,
        original_col=source["col_offset"] + col,
        nodata_pixels=int(invalid.sum()),
        background_pixels=None,
        kelp_pixels=None,
        ignored_pixels=None,
        valid_ignored_pixels=None,
        disposition="omitted_nodata",
        payload="",
    )
    if target is not None:
        record.update(
            background_pixels=int((target == 0).sum()),
            kelp_pixels=int((target == 1).sum()),
            ignored_pixels=int((target == -100).sum()),
            valid_ignored_pixels=int(((target == -100) & ~invalid).sum()),
        )
    return record


def _write_source(pair, source, recipe, work, writer) -> tuple[int, int, int]:
    """Read one source's windows, write eligible payloads, and return totals."""
    retained = omitted = payload_bytes = 0
    with ExitStack() as files:
        image = files.enter_context(
            rasterio.open(pair.image, GEOREF_SOURCES="INTERNAL")
        )
        label = (
            files.enter_context(rasterio.open(pair.label, GEOREF_SOURCES="INTERNAL"))
            if pair.label
            else None
        )
        for window in chip_windows(
            image.width, image.height, recipe.chip_size, recipe.stride
        ):
            values = image.read(window=window)
            invalid = nodata_mask(values, (0,) * image.count, band_axis=0)
            # Stored category zero remains background, regardless of label masks/nodata.
            target = (
                map_labels(
                    label.read(1, window=window, masked=False),
                    recipe.label_mapping,
                    invalid,
                )
                if label
                else None
            )
            record = _window_record(source, window, invalid, target)
            # Compare source pixels only; equality is retained. No foreground filter.
            if record["nodata_pixels"] * 100 <= recipe.max_nodata_pct * invalid.size:
                relative = (
                    Path("chips") / pair.key / f"r{record['row']}_c{record['col']}.npz"
                )
                destination = work / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                arrays = {"image": np.moveaxis(values, 0, -1)}
                if target is not None:
                    arrays["label"] = target
                with destination.open("xb") as payload:
                    np.savez_compressed(payload, **arrays)
                payload_bytes += destination.stat().st_size
                record.update(disposition="retained", payload=relative.as_posix())
                retained += 1
            else:
                omitted += 1
            writer.writerow(record)
            if (retained + omitted) % 100 == 0:
                logger.info(
                    "%s: windows %d; retained %d; omitted %d; payload bytes %d",
                    pair.key,
                    retained + omitted,
                    retained,
                    omitted,
                    payload_bytes,
                )
    return retained, omitted, payload_bytes


def chip_dataset(plan: ChipPlan) -> Path:
    """Write once, stopping on failure. Incomplete outputs are never reused."""
    output = plan.output
    work = output.with_name(f".{output.name}.incomplete")
    if output.exists() or work.exists():
        raise PreparationError(
            f"Output or incomplete directory exists; choose a fresh output: {output}"
        )
    work.mkdir()
    retained = omitted = payload_bytes = 0
    try:
        (work / "chips").mkdir()
        _write_json(work / "recipe.json", asdict(plan.recipe))
        _write_json(work / "sources.json", list(plan.sources))
        with (
            rasterio.Env(GDAL_PAM_ENABLED="NO"),
            (work / "windows.csv").open("x", newline="", encoding="utf-8") as stream,
        ):
            writer = csv.DictWriter(stream, fieldnames=WINDOW_COLUMNS)
            writer.writeheader()
            for number, (pair, source) in enumerate(
                zip(plan.pairs, plan.sources, strict=True), 1
            ):
                logger.info("Chipping %d/%d: %s", number, len(plan.pairs), pair.key)
                kept, excluded, size = _write_source(
                    pair, source, plan.recipe, work, writer
                )
                retained += kept
                omitted += excluded
                payload_bytes += size
                logger.info(
                    "Finished %s; total retained %d, omitted %d, payload bytes %d",
                    pair.key,
                    retained,
                    omitted,
                    payload_bytes,
                )
        _write_json(
            work / "summary.json",
            dict(
                status="complete",
                sources=len(plan.sources),
                candidate_windows=retained + omitted,
                retained=retained,
                omitted_nodata=omitted,
                payload_bytes=payload_bytes,
                input_bytes=plan.source_bytes,
                counts_scope="Window counts overlap; not unique source-pixel coverage.",
            ),
        )
        work.rename(output)
    except (OSError, ValueError, rasterio.errors.RasterioError) as error:
        raise PreparationError(
            f"Chipping stopped; inspect {work}, then use a fresh output. {error}"
        ) from error
    logger.info(
        "Complete: %s; retained %d/%d windows", output, retained, retained + omitted
    )
    return output
