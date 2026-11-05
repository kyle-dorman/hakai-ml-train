"""Save image-only predictions on the existing disjoint evaluation chip footprint."""

import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio import Affine

from kelpseg.model_bundle import PortableModel, load_model_bundle
from kelpseg.prediction.predict import _write_json
from kelpseg.prediction.selection import training_sample
from kelpseg.prepare.splits import select_windows
from kelpseg.preprocessing import native_validity

logger = logging.getLogger(__name__)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Publish flat records after all sources finish; encode nested CSV values as JSON."""
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value)
                    if isinstance(value, (list, tuple, dict))
                    else value
                    for key, value in row.items()
                }
            )
    temporary.replace(path)


def _predict_source(
    rows: list[dict[str, Any]],
    model: PortableModel,
    bands: list[str],
    output: Path,
    source_key: str,
) -> dict[str, Any]:
    """Place disjoint image predictions on one original source grid and save a TIFF.

    Rows are already selected and spatially validated by select_windows. Only image
    arrays are read. Return source identity, canvas offsets and unique coverage
    counts; gaps in the bounding canvas retain NaN rather than background.
    """
    top = min(int(row["original_row"]) for row in rows)
    left = min(int(row["original_col"]) for row in rows)
    bottom = max(int(row["original_row"]) + int(row["height"]) for row in rows)
    right = max(int(row["original_col"]) + int(row["width"]) for row in rows)
    probability = np.full((bottom - top, right - left), np.nan, dtype=np.float32)
    valid_pixels = retained_pixels = 0
    for index, row in enumerate(rows, 1):
        with np.load(row["payload"]) as arrays:
            image = arrays["image"]
        h, w = int(row["height"]), int(row["width"])
        if image.shape[:2] != (h, w):
            raise ValueError(
                f"{row['payload']}: image dimensions differ from the window manifest."
            )
        prediction = model.predict_probabilities(image, bands)
        y, x = int(row["original_row"]) - top, int(row["original_col"]) - left
        probability[y : y + h, x : x + w] = prediction
        valid_pixels += int(native_validity(image).sum())
        retained_pixels += h * w
        if index % 10 == 0 or index == len(rows):
            logger.info("%s: predicted %d/%d chips", source_key, index, len(rows))
    first = rows[0]
    # The saved transform belongs to the crop; move from its origin to this canvas.
    transform = Affine(*first["transform"][:6]) * Affine.translation(
        left - int(first["col_offset"]), top - int(first["row_offset"])
    )
    relative = Path("probabilities") / f"{source_key}.tif"
    with rasterio.open(
        output / relative,
        "w",
        driver="GTiff",
        height=probability.shape[0],
        width=probability.shape[1],
        count=1,
        dtype="float32",
        crs=first["crs"],
        transform=transform,
        nodata=np.nan,
        compress="deflate",
        BIGTIFF="IF_SAFER",
    ) as destination:
        destination.write(probability, 1)
    predicted = int(np.isfinite(probability).sum())
    return dict(
        source_key=source_key,
        dataset_id=first["dataset_id"],
        release_id=first["release_id"],
        original_source_id=first["original_tiff"],
        region_id=first["region"],
        acquisition_date=first["acquisition_date"],
        row_offset=top,
        col_offset=left,
        probability=relative.as_posix(),
        band_names=";".join(bands),
        total_pixels=int(probability.size),
        retained_window_pixels=retained_pixels,
        geometric_gap_pixels=int(probability.size) - retained_pixels,
        valid_pixels=valid_pixels,
        nodata_pixels=retained_pixels - valid_pixels,
        predicted_valid_pixels=predicted,
        uncovered_valid_pixels=valid_pixels - predicted,
        predicted_windows=len(rows),
    )


def predict_chips(
    run_directory: str | Path,
    output_directory: str | Path,
    *,
    device: str = "cpu",
    split: str = "val",
    sources_per_region: int = 3,
    seed: int = 42,
) -> Path:
    """Save selected chip probabilities from a completed run into a fresh directory.

    Validation uses all disjoint selected windows; train uses the existing seeded,
    label-blind source sample and disjoint grid. Preserve model/selection metadata
    and payload references for later reports. No labels, test arrays or figures
    are read or generated. On failure stop and leave the incomplete output.
    """
    run_directory = Path(run_directory).expanduser().resolve()
    output = Path(output_directory).expanduser().resolve()
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a fresh directory.")
    if device not in ("cpu", "cuda"):
        raise ValueError("device must be cpu or cuda.")
    if split not in ("val", "train"):
        raise ValueError(
            "Chip prediction split must be val or train; test is excluded."
        )
    run = json.loads((run_directory / "run.json").read_text())
    if run["status"] != "complete":
        raise ValueError(
            "Chip prediction requires a completed run; leave running training untouched."
        )
    metadata = json.loads((run_directory / "model/model.json").read_text())
    if metadata["run_id"] != run["run_id"]:
        raise ValueError("Model bundle and run.json have different run identities.")
    if split == "train":
        rows = training_sample(run, sources_per_region, seed)
    else:
        rows = [
            row
            for row in select_windows(
                run["chips"],
                run["assignments"],
                experiment=run["experiment"],
                variant=run["variant"],
            )
            if row["split"] == "val"
        ]
    if not rows:
        raise ValueError("No prediction chips selected.")
    bands = json.loads((Path(run["chips"]) / "recipe.json").read_text())[
        "source_band_names"
    ]
    model = load_model_bundle(run_directory / "model", device=device)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["dataset_id"], row["release_id"], row["original_tiff"])].append(row)
    logger.info(
        "Chip prediction %s: model %s; bands %s; %d sources/%d windows; output %s",
        split,
        run_directory / "model",
        bands,
        len(groups),
        len(rows),
        output,
    )
    output.mkdir(parents=True)
    (output / "probabilities").mkdir()
    sources, windows = [], []
    for index, (identity, source_rows) in enumerate(sorted(groups.items()), 1):
        key = f"source_{index:06d}"
        logger.info(
            "Predict %s source %d/%d: %s", split, index, len(groups), identity[2]
        )
        sources.append(_predict_source(source_rows, model, bands, output, key))
        windows.extend(
            dict(row, chip_source_key=row["source_key"], source_key=key)
            for row in source_rows
        )
    _write_csv(output / "sources.csv", sources)
    _write_csv(output / "windows.csv", windows)
    _write_json(
        output / "settings.json",
        dict(
            scope="chip_disjoint",
            model=metadata,
            split=split,
            run_id=run["run_id"],
            recipe=dict(
                run=str(run_directory),
                chips=run["chips"],
                assignments=run["assignments"],
                experiment=run["experiment"],
                variant=run["variant"],
                device=device,
                split=split,
                sources_per_region=sources_per_region if split == "train" else None,
                seed=seed if split == "train" else None,
            ),
        ),
    )
    counts = (
        "total_pixels",
        "retained_window_pixels",
        "geometric_gap_pixels",
        "valid_pixels",
        "nodata_pixels",
        "predicted_valid_pixels",
        "uncovered_valid_pixels",
        "predicted_windows",
    )
    _write_json(
        output / "summary.json",
        dict(
            status="complete",
            scope="chip_disjoint",
            sources=len(sources),
            **{name: sum(row[name] for row in sources) for name in counts},
        ),
    )
    return output
