#!/usr/bin/env python3
"""Audit and transactionally repair source-aware nodata chip statistics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window

from src.prepare.make_chip_dataset import (
    _chip_source,
    manifest_columns,
    remap_label_array,
)
from src.prepare.nodata import declared_nodata_values, nodata_mask, nodata_value_text
from src.prepare.remove_bg_only_tiles import (
    SELECTION_COLUMNS,
    SUMMARY_COLUMNS,
    select_training_chips,
)

SCHEMA = "metadata-nodata-repair-v2"
HISTORY_RELATIVE = Path("repair_history/metadata_nodata_v2")
CALIFORNIA_LABEL_REPAIR_SOURCE = "004_20210525_174950_2463"
CHIP_SIZE = 1024
CHIP_STRIDE = 512
NUM_BANDS = 8
BAND_REMAPPING = (0, 1, 0, -100, 0)
COUNT_COLUMNS = (
    "class_0_pixel_count",
    "class_1_pixel_count",
    "ignore_pixel_count",
    "nodata_pixel_count",
    "total_pixel_count",
)
REPAIRED_COLUMNS = [
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "source_nodata_value",
    *[f"old_{column}" for column in COUNT_COLUMNS],
    "old_nodata_pct",
    *[f"new_{column}" for column in COUNT_COLUMNS],
    "new_nodata_pct",
    "reason",
    "npz_byte_size",
    "trusted_v1_sha256",
]
LABEL_AUDIT_COLUMNS = [
    "source_tiff_id",
    "dataset",
    "region_id",
    "source_nodata_value",
    "pre_label_sha256",
    "pre_label_values",
    "total_pixel_count",
    "image_nodata_pixel_count",
    "true_positive_count",
    "false_positive_count",
    "false_negative_count",
    "true_negative_count",
    "pixels_to_change",
    "source_fragment_chip_count",
    "repair_reason",
]
REWRITTEN_NPZ_COLUMNS = [
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "retained_after_filter",
    "old_present",
    "old_byte_size",
    "old_sha256",
    "new_byte_size",
    "new_sha256",
    "reason",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("w") as file:
            json.dump(payload, file, indent=2, sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=False, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _source_image(raster_root: Path, source_id: str) -> Path:
    matches = list((raster_root / "all/images").glob(f"{source_id}.[tT][iI][fF]"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one merged source image for {source_id}")
    return matches[0]


def inventory_sources(
    raster_root: Path, raster_rows: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], dict[str, tuple[int | float, ...]]]:
    inventory: list[dict[str, Any]] = []
    values_by_source: dict[str, tuple[int | float, ...]] = {}
    for row in sorted(raster_rows, key=lambda value: value["source_tiff_id"]):
        source_id = row["source_tiff_id"]
        path = _source_image(raster_root, source_id)
        with rasterio.open(path) as source:
            raw_values = tuple(source.nodatavals[:8])
            defaulted = all(value is None for value in raw_values)
            values = declared_nodata_values(source, retained_bands=8, missing_value=0)
            values_by_source[source_id] = values
            inventory.append(
                {
                    "source_tiff_id": source_id,
                    "dataset": row["dataset"],
                    "region_id": row["region_id"],
                    "image_dtype": source.dtypes[0],
                    "band_count": source.count,
                    "source_nodata_value": nodata_value_text(values),
                    "source_nodata_values": json.dumps(list(values)),
                    "nodata_metadata_status": (
                        "missing_defaulted_to_zero" if defaulted else "declared"
                    ),
                    "status": "valid_effective_single_value",
                }
            )
    return inventory, values_by_source


def _repair_source_ids(raster_rows: list[dict[str, str]]) -> list[str]:
    """Return the deliberately bounded label/re-chip scope."""
    available = {row["source_tiff_id"] for row in raster_rows}
    if CALIFORNIA_LABEL_REPAIR_SOURCE not in available:
        raise RuntimeError(
            f"Missing required California repair source {CALIFORNIA_LABEL_REPAIR_SOURCE}"
        )
    sources = [
        row["source_tiff_id"]
        for row in raster_rows
        if row["dataset"] == "bc"
        or row["source_tiff_id"] == CALIFORNIA_LABEL_REPAIR_SOURCE
    ]
    if len(sources) != len(set(sources)):
        raise RuntimeError("Duplicate source IDs in the label repair scope")
    return sorted(sources)


def _source_label(raster_root: Path, source_id: str) -> Path:
    matches = list((raster_root / "all/labels").glob(f"{source_id}.[tT][iI][fF]"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one merged source label for {source_id}")
    return matches[0]


def _validate_bc_source_label(path: Path) -> None:
    values: set[int] = set()
    with rasterio.open(path) as source:
        for _, window in source.block_windows(1):
            values.update(
                int(value) for value in np.unique(source.read(1, window=window))
            )
    if values - {0, 1}:
        raise RuntimeError(
            f"BC source label {path.stem} contains values outside 0/1: {sorted(values)}"
        )


def _label_audit(
    *,
    image_path: Path,
    label_path: Path,
    dataset: str,
    nodata_values: tuple[int | float, ...],
) -> dict[str, Any]:
    """Audit image nodata against derived label class 3 blockwise."""
    totals = Counter()
    values: set[int] = set()
    with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
        if (
            image.width != label.width
            or image.height != label.height
            or image.transform != label.transform
            or image.crs != label.crs
        ):
            raise RuntimeError(f"Image/label grid mismatch for {image_path.stem}")
        for _, window in image.block_windows(1):
            image_block = image.read(indexes=range(1, 9), window=window)
            label_block = label.read(1, window=window)
            image_nodata = nodata_mask(image_block, nodata_values, band_axis=0)
            label_nodata = label_block == 3
            values.update(int(value) for value in np.unique(label_block))
            totals["total"] += label_block.size
            totals["image_nodata"] += int(np.count_nonzero(image_nodata))
            totals["tp"] += int(np.count_nonzero(image_nodata & label_nodata))
            totals["fp"] += int(np.count_nonzero(~image_nodata & label_nodata))
            totals["fn"] += int(np.count_nonzero(image_nodata & ~label_nodata))
            totals["tn"] += int(np.count_nonzero(~image_nodata & ~label_nodata))
    if dataset == "bc":
        unsupported = values - {0, 1, 3}
        if unsupported:
            raise RuntimeError(
                f"BC label {label_path.stem} contains unsupported values {sorted(unsupported)}"
            )
    return {
        "pre_label_sha256": sha256_file(label_path),
        "pre_label_values": json.dumps(sorted(values)),
        "total_pixel_count": totals["total"],
        "image_nodata_pixel_count": totals["image_nodata"],
        "true_positive_count": totals["tp"],
        "false_positive_count": totals["fp"],
        "false_negative_count": totals["fn"],
        "true_negative_count": totals["tn"],
        "pixels_to_change": totals["fn"],
    }


def _write_repaired_label(
    *,
    image_path: Path,
    source_label: Path,
    original_label: Path | None,
    destination: Path,
    dataset: str,
    nodata_values: tuple[int | float, ...],
) -> None:
    """Create one staged derived label; never edit the canonical file in place."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if dataset == "bc":
        if original_label is None:
            raise RuntimeError("BC label repair requires the original source label")
        with rasterio.open(image_path) as image, rasterio.open(original_label) as raw:
            raw_values: set[int] = set()
            for _, window in raw.block_windows(1):
                raw_values.update(
                    int(value) for value in np.unique(raw.read(1, window=window))
                )
            if raw_values - {0, 1}:
                raise RuntimeError(
                    f"BC source label {original_label.stem} contains values outside 0/1: "
                    f"{sorted(raw_values)}"
                )
            profile = image.profile.copy()
            profile.update(count=1, dtype="uint8", nodata=3, compress="deflate")
            if not profile.get("tiled"):
                profile.pop("blockxsize", None)
                profile.pop("blockysize", None)
            with (
                rasterio.open(destination, "w", **profile) as output,
                WarpedVRT(
                    raw,
                    crs=image.crs,
                    transform=image.transform,
                    width=image.width,
                    height=image.height,
                    resampling=Resampling.nearest,
                    src_nodata=255,
                    nodata=255,
                ) as aligned,
            ):
                for _, window in image.block_windows(1):
                    label_block = aligned.read(1, window=window)
                    label_block[label_block == 255] = 0
                    image_block = image.read(indexes=range(1, 9), window=window)
                    image_nodata = nodata_mask(image_block, nodata_values, band_axis=0)
                    label_block[image_nodata] = 3
                    output.write(label_block.astype(np.uint8), 1, window=window)
    else:
        shutil.copy2(source_label, destination)
    with rasterio.open(image_path) as image, rasterio.open(destination, "r+") as label:
        for _, window in image.block_windows(1):
            image_block = image.read(indexes=range(1, 9), window=window)
            label_block = label.read(1, window=window)
            image_nodata = nodata_mask(image_block, nodata_values, band_axis=0)
            if dataset != "bc":
                label_block[image_nodata & (label_block != 3)] = 3
                label.write(label_block, 1, window=window)
    post = _label_audit(
        image_path=image_path,
        label_path=destination,
        dataset=dataset,
        nodata_values=nodata_values,
    )
    if post["false_negative_count"] or (
        dataset == "bc" and post["false_positive_count"]
    ):
        raise RuntimeError(
            f"Staged label repair did not produce an exact mask: {source_label.stem}"
        )


def _recompute_fragment_from_rasters(
    *,
    rows: list[dict[str, str]],
    image_path: Path,
    label_path: Path,
    nodata_values: tuple[int | float, ...],
) -> list[dict[str, str]]:
    """Recompute portable statistics for an unchanged NPZ/source fragment."""
    output: list[dict[str, str]] = []
    with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
        for row in rows:
            window = Window(
                int(row["col_off"]),
                int(row["row_off"]),
                int(row["chip_width"]),
                int(row["chip_height"]),
            )
            image_block = image.read(indexes=range(1, 9), window=window)
            raw_label = label.read(1, window=window)
            remapped = remap_label_array(raw_label, BAND_REMAPPING)
            mask = nodata_mask(image_block, nodata_values, band_axis=0)
            updated = dict(row)
            total = int(remapped.size)
            updated.update(
                {
                    "source_nodata_value": nodata_value_text(nodata_values),
                    "class_0_pixel_count": str(np.count_nonzero(remapped == 0)),
                    "class_1_pixel_count": str(np.count_nonzero(remapped == 1)),
                    "ignore_pixel_count": str(np.count_nonzero(remapped == -100)),
                    "nodata_pixel_count": str(np.count_nonzero(mask)),
                    "nodata_pct": str(100.0 * np.count_nonzero(mask) / total),
                    "total_pixel_count": str(total),
                }
            )
            output.append(updated)
    return output


def _trusted_v1_inventory(
    archive: Path, checksum: Path
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    expected_parts = checksum.read_text().strip().split()
    if len(expected_parts) != 2 or expected_parts[1].lstrip("*") != archive.name:
        raise RuntimeError(f"Invalid v1 checksum sidecar: {checksum}")
    expected_archive_sha = expected_parts[0]
    if sha256_file(archive) != expected_archive_sha:
        raise RuntimeError("The v1 archive does not match its trusted checksum sidecar")
    with zipfile.ZipFile(archive) as source_zip:
        candidates = [
            name
            for name in source_zip.namelist()
            if name.endswith("/metadata/archive_inventory.csv")
        ]
        if len(candidates) != 1:
            raise RuntimeError("Could not identify one v1 archive inventory")
        content = source_zip.read(candidates[0])
    inventory_sha = hashlib.sha256(content).hexdigest()
    reader = csv.DictReader(content.decode().splitlines())
    rows = list(reader)
    by_path = {row["relative_path"]: row for row in rows}
    if len(by_path) != len(rows):
        raise RuntimeError("The trusted v1 inventory contains duplicate paths")
    return by_path, {
        "trusted_v1_archive": str(archive.resolve()),
        "trusted_v1_archive_sha256": expected_archive_sha,
        "trusted_v1_inventory_sha256": inventory_sha,
    }


def _updated_row(
    row: dict[str, str],
    *,
    chip_root: Path,
    source: rasterio.io.DatasetReader,
    nodata_values: tuple[int | float, ...],
    trusted_inventory: dict[str, dict[str, str]],
) -> tuple[dict[str, str], dict[str, Any]]:
    path = chip_root / Path(*PurePosixPath(row["chip_path"]).parts)
    with np.load(path) as chip:
        image = chip["image"]
        label = chip["label"]
    window = Window(
        int(row["col_off"]),
        int(row["row_off"]),
        int(row["chip_width"]),
        int(row["chip_height"]),
    )
    expected_image = np.moveaxis(source.read(indexes=range(1, 9), window=window), 0, -1)
    if not np.array_equal(image, expected_image):
        raise RuntimeError(f"NPZ image differs from source window: {row['chip_id']}")
    mask = nodata_mask(image, nodata_values, band_axis=-1)
    if np.any(label[mask] != -100):
        count = int(np.count_nonzero(label[mask] != -100))
        raise RuntimeError(
            f"{count} source-nodata pixels are not label -100: {row['chip_id']}"
        )
    total = int(label.size)
    counts = {
        "class_0_pixel_count": int(np.count_nonzero(label == 0)),
        "class_1_pixel_count": int(np.count_nonzero(label == 1)),
        "ignore_pixel_count": int(np.count_nonzero(label == -100)),
        "nodata_pixel_count": int(np.count_nonzero(mask)),
        "total_pixel_count": total,
    }
    if (
        counts["class_0_pixel_count"]
        + counts["class_1_pixel_count"]
        + counts["ignore_pixel_count"]
        != total
    ):
        raise RuntimeError(f"Unexpected label values in {row['chip_id']}")
    updated = dict(row)
    updated.update({key: str(value) for key, value in counts.items()})
    updated["nodata_pct"] = str(100.0 * counts["nodata_pixel_count"] / total)
    updated["source_nodata_value"] = nodata_value_text(nodata_values)
    archive_path = PurePosixPath(
        "chips", *PurePosixPath(row["chip_path"]).parts
    ).as_posix()
    trusted = trusted_inventory.get(archive_path)
    if trusted is None or int(trusted["byte_size"]) != path.stat().st_size:
        raise RuntimeError(f"Trusted v1 inventory path/size mismatch: {archive_path}")
    repair = {
        "chip_id": row["chip_id"],
        "chip_path": row["chip_path"],
        "source_tiff_id": row["source_tiff_id"],
        "dataset": row["dataset"],
        "region_id": row["region_id"],
        "source_nodata_value": updated["source_nodata_value"],
        **{f"old_{key}": row[key] for key in COUNT_COLUMNS},
        "old_nodata_pct": row["nodata_pct"],
        **{f"new_{key}": updated[key] for key in COUNT_COLUMNS},
        "new_nodata_pct": updated["nodata_pct"],
        "reason": "source_declared_nodata_recount",
        "npz_byte_size": path.stat().st_size,
        "trusted_v1_sha256": trusted["sha256"],
    }
    return updated, repair


def _add_source_nodata(
    rows: list[dict[str, str]], values_by_source: dict[str, tuple[int | float, ...]]
) -> list[dict[str, str]]:
    output = []
    for row in rows:
        updated = dict(row)
        updated["source_nodata_value"] = nodata_value_text(
            values_by_source[row["source_tiff_id"]]
        )
        output.append(updated)
    return output


def _summary_rows(
    original_rows: list[dict[str, str]],
    active_rows: list[dict[str, str]],
    removed_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    active_ids = {row["chip_id"] for row in active_rows}
    removed_ids = {row["chip_id"] for row in removed_rows}
    groups = [("global", "", "", original_rows)]
    for region in sorted({row["region_id"] for row in original_rows}):
        groups.append(
            (
                "region",
                region,
                "",
                [row for row in original_rows if row["region_id"] == region],
            )
        )
    for source_id in sorted({row["source_tiff_id"] for row in original_rows}):
        source_rows = [
            row for row in original_rows if row["source_tiff_id"] == source_id
        ]
        groups.append(
            ("source_tiff", source_rows[0]["region_id"], source_id, source_rows)
        )
    output = []
    for scope, region, source, rows in groups:
        kept = [row for row in rows if row["chip_id"] in active_ids]
        removed = [row for row in rows if row["chip_id"] in removed_ids]
        output.append(
            {
                "scope": scope,
                "region_id": region,
                "source_tiff_id": source,
                "original_chip_count": len(rows),
                "retained_chip_count": len(kept),
                "removed_chip_count": len(removed),
                "retained_total_pixel_count": sum(
                    int(row["total_pixel_count"]) for row in kept
                ),
                "retained_class_0_pixel_count": sum(
                    int(row["class_0_pixel_count"]) for row in kept
                ),
                "retained_class_1_pixel_count": sum(
                    int(row["class_1_pixel_count"]) for row in kept
                ),
                "retained_ignore_pixel_count": sum(
                    int(row["ignore_pixel_count"]) for row in kept
                ),
                "retained_nodata_pixel_count": sum(
                    int(row["nodata_pixel_count"]) for row in kept
                ),
                "maximum_retained_nodata_pct": max(
                    (float(row["nodata_pct"]) for row in kept), default=0
                ),
            }
        )
    return output


def _affected_audit(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    output = []
    for source_id in sorted({row["source_tiff_id"] for row in rows}):
        source_rows = [row for row in rows if row["source_tiff_id"] == source_id]
        output.append(
            {
                "source_tiff_id": source_id,
                "region_id": source_rows[0]["region_id"],
                "chip_count": len(source_rows),
                "nodata_pct_eq_0_count": sum(
                    float(row["nodata_pct"]) == 0 for row in source_rows
                ),
                "nodata_pct_gt_0_le_50_count": sum(
                    0 < float(row["nodata_pct"]) <= 50 for row in source_rows
                ),
                "nodata_pct_gt_50_count": sum(
                    float(row["nodata_pct"]) > 50 for row in source_rows
                ),
                "nodata_pixel_count": sum(
                    int(row["nodata_pixel_count"]) for row in source_rows
                ),
            }
        )
    return output


def _source_count_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    output = []
    for source_id in sorted({row["source_tiff_id"] for row in rows}):
        source_rows = [row for row in rows if row["source_tiff_id"] == source_id]
        first = source_rows[0]
        presence = Counter()
        for row in source_rows:
            if int(row["class_1_pixel_count"]) > 0:
                presence["positive"] += 1
            elif (
                int(row["class_0_pixel_count"]) > 0
                and int(row["nodata_pixel_count"]) == 0
            ):
                presence["clean_background_only"] += 1
            elif int(row["class_0_pixel_count"]) > 0:
                presence["mixed_background_nodata"] += 1
            else:
                presence["ignore_only"] += 1
        output.append(
            {
                "source_tiff_id": source_id,
                "dataset": first["dataset"],
                "region_id": first["region_id"],
                "region_name": first["region_name"],
                "acquisition_date": first["acquisition_date"],
                "year": first["acquisition_date"][:4],
                "source_width": first["source_width"],
                "source_height": first["source_height"],
                "chip_count": len(source_rows),
                "partial_chip_count": sum(
                    int(row["chip_width"]) < 1024 or int(row["chip_height"]) < 1024
                    for row in source_rows
                ),
                "positive_chip_count": presence["positive"],
                "clean_background_only_chip_count": presence["clean_background_only"],
                "mixed_background_nodata_chip_count": presence[
                    "mixed_background_nodata"
                ],
                "ignore_only_chip_count": presence["ignore_only"],
                **{
                    column: sum(int(row[column]) for row in source_rows)
                    for column in COUNT_COLUMNS
                },
            }
        )
    return output


def _replace_from_staging(
    staging: Path, targets: list[tuple[Path, Path]]
) -> list[tuple[Path, Path]]:
    backups = staging / "backups"
    backups.mkdir()
    replaced: list[tuple[Path, Path]] = []
    try:
        for staged, target in targets:
            relative_backup = backups / f"{len(replaced):04d}_{target.name}"
            shutil.copy2(target, relative_backup)
            os.replace(staged, target)
            replaced.append((relative_backup, target))
    except BaseException:
        for backup, target in reversed(replaced):
            os.replace(backup, target)
        raise
    return replaced


def repair_dataset(
    *,
    chip_root: Path,
    raster_root: Path,
    temporal_split: Path,
    prior_archive: Path,
    prior_checksum: Path,
    apply: bool,
) -> dict[str, Any]:
    chip_root = chip_root.resolve()
    raster_root = raster_root.resolve()
    history = chip_root / HISTORY_RELATIVE
    history.mkdir(parents=True, exist_ok=True)
    completion = history / "repair_metadata.json"
    active_path = chip_root / "chip_manifest.csv"
    if apply and completion.exists():
        with completion.open() as file:
            existing = json.load(file)
        if existing.get("status") == "complete" and sha256_file(
            active_path
        ) == existing.get("post_active_manifest_sha256"):
            return existing
        raise RuntimeError("Existing repair history does not match the active manifest")

    _, raster_rows = _read_csv(raster_root / "raster_manifest.csv")
    if not raster_rows:
        raise RuntimeError("Raster manifest is empty")
    source_by_id = {row["source_tiff_id"]: row for row in raster_rows}
    if len(source_by_id) != len(raster_rows):
        raise RuntimeError("Raster manifest contains duplicate source IDs")
    source_inventory, values_by_source = inventory_sources(raster_root, raster_rows)
    affected_sources = sorted(
        source_id for source_id, values in values_by_source.items() if values[0] != 0
    )
    repair_sources = _repair_source_ids(raster_rows)
    trusted_inventory, trust = _trusted_v1_inventory(prior_archive, prior_checksum)

    fragment_paths = sorted((chip_root / "manifest_parts/all").glob("*.csv"))
    if len(fragment_paths) != len(raster_rows):
        raise RuntimeError("Fragment inventory does not match the raster source count")
    old_fragments: dict[str, list[dict[str, str]]] = {}
    old_fields: list[str] | None = None
    for fragment in fragment_paths:
        fields, rows = _read_csv(fragment)
        old_fields = old_fields or fields
        if fields != old_fields:
            raise RuntimeError("Pre-repair fragment schemas differ")
        old_fragments[fragment.stem] = rows
    if sum(len(rows) for rows in old_fragments.values()) != 6003:
        raise RuntimeError("Original source fragments no longer contain 6,003 chips")

    label_audits: list[dict[str, Any]] = []
    for source_id in repair_sources:
        source_row = source_by_id[source_id]
        if source_row["dataset"] == "bc":
            _validate_bc_source_label(Path(source_row["source_label"]))
        audit = _label_audit(
            image_path=_source_image(raster_root, source_id),
            label_path=_source_label(raster_root, source_id),
            dataset=source_row["dataset"],
            nodata_values=values_by_source[source_id],
        )
        label_audits.append(
            {
                "source_tiff_id": source_id,
                "dataset": source_row["dataset"],
                "region_id": source_row["region_id"],
                "source_nodata_value": nodata_value_text(values_by_source[source_id]),
                **audit,
                "source_fragment_chip_count": len(old_fragments[source_id]),
                "repair_reason": (
                    "california_declared_nodata_false_negatives"
                    if source_id == CALIFORNIA_LABEL_REPAIR_SOURCE
                    else "bc_image_derived_class_3_nodata"
                ),
            }
        )

    final_fields = manifest_columns(BAND_REMAPPING)
    staging = chip_root / ".metadata_nodata_repair_v2"
    if staging.exists():
        raise RuntimeError(f"Unresolved repair staging directory: {staging}")
    staged_fragments: dict[str, list[dict[str, str]]] = {}
    staged_labels: dict[str, Path] = {}
    if apply:
        staging.mkdir()
        input_root = staging / "rechip_input/all"
        (input_root / "images").mkdir(parents=True)
        (input_root / "labels").mkdir(parents=True)
        for source_id in repair_sources:
            source_row = source_by_id[source_id]
            image_path = _source_image(raster_root, source_id)
            staged_label = input_root / "labels" / f"{source_id}.tif"
            _write_repaired_label(
                image_path=image_path,
                source_label=_source_label(raster_root, source_id),
                original_label=Path(source_row["source_label"]),
                destination=staged_label,
                dataset=source_row["dataset"],
                nodata_values=values_by_source[source_id],
            )
            os.symlink(image_path, input_root / "images" / f"{source_id}.tif")
            staged_labels[source_id] = staged_label
            fragment = staging / "rechipped/manifest_parts/all" / f"{source_id}.csv"
            fragment.parent.mkdir(parents=True, exist_ok=True)
            _chip_source(
                data_dir=staging / "rechip_input",
                output_dir=staging / "rechipped",
                split="all",
                source_row=source_row,
                fragment_path=fragment,
                staging_dir=staging / "chip_work" / source_id,
                chip_size=CHIP_SIZE,
                chip_stride=CHIP_STRIDE,
                num_bands=NUM_BANDS,
                band_remapping=BAND_REMAPPING,
                dtype=np.dtype("uint16"),
                fieldnames=final_fields,
            )
            _, staged_fragments[source_id] = _read_csv(fragment)

    repaired_fragments: dict[str, list[dict[str, str]]] = {}
    all_original_rows: list[dict[str, str]] = []
    for source_id, rows in sorted(old_fragments.items()):
        if source_id in repair_sources and apply:
            repaired = staged_fragments[source_id]
        elif source_id in affected_sources:
            repaired = _recompute_fragment_from_rasters(
                rows=rows,
                image_path=_source_image(raster_root, source_id),
                label_path=(
                    staged_labels[source_id]
                    if source_id in staged_labels
                    else _source_label(raster_root, source_id)
                ),
                nodata_values=values_by_source[source_id],
            )
        else:
            repaired = _add_source_nodata(rows, values_by_source)
        repaired_fragments[source_id] = repaired
        all_original_rows.extend(repaired)

    original_by_id = {row["chip_id"]: row for row in all_original_rows}
    if len(original_by_id) != 6003:
        raise RuntimeError(
            "Repaired original inventory has duplicate or missing chip IDs"
        )
    final_active = [row for row in all_original_rows if float(row["nodata_pct"]) <= 50]
    combined_removals = [
        row for row in all_original_rows if float(row["nodata_pct"]) > 50
    ]
    _, old_removals = _read_csv(
        chip_root / "filter_history/nodata_50/removal_manifest.csv"
    )
    old_removed_ids = {row["chip_id"] for row in old_removals}
    added_removals = [
        row for row in combined_removals if row["chip_id"] not in old_removed_ids
    ]
    if {row["chip_id"] for row in final_active}.intersection(
        row["chip_id"] for row in combined_removals
    ) or len(final_active) + len(combined_removals) != 6003:
        raise RuntimeError("Active plus removed chips do not reconcile to 6,003")
    _, split_rows = _read_csv(temporal_split)
    if {row["image_name_stem"] for row in split_rows} != set(values_by_source):
        raise RuntimeError("Temporal split no longer joins one-to-one to source TIFFs")

    old_by_id = {row["chip_id"]: row for rows in old_fragments.values() for row in rows}
    repair_rows: list[dict[str, Any]] = []
    for source_id in affected_sources:
        for row in repaired_fragments[source_id]:
            old = old_by_id[row["chip_id"]]
            archive_path = f"chips/{row['chip_path']}"
            prior = trusted_inventory.get(archive_path)
            path = chip_root / row["chip_path"]
            repair_rows.append(
                {
                    "chip_id": row["chip_id"],
                    "chip_path": row["chip_path"],
                    "source_tiff_id": source_id,
                    "dataset": row["dataset"],
                    "region_id": row["region_id"],
                    "source_nodata_value": row["source_nodata_value"],
                    **{f"old_{column}": old[column] for column in COUNT_COLUMNS},
                    "old_nodata_pct": old["nodata_pct"],
                    **{f"new_{column}": row[column] for column in COUNT_COLUMNS},
                    "new_nodata_pct": row["nodata_pct"],
                    "reason": "source_declared_nodata_recount",
                    "npz_byte_size": path.stat().st_size if path.exists() else "",
                    "trusted_v1_sha256": prior["sha256"] if prior else "",
                }
            )

    active_path = chip_root / "chip_manifest.csv"
    mutable = [
        active_path,
        raster_root / "raster_metadata.csv",
        raster_root / "label_alignment.csv",
        chip_root / "chip_counts_by_source.csv",
        chip_root / "chip_qa_summary.json",
        chip_root / "background_selection/exclude_all/training_selection.csv",
        chip_root / "background_selection/exclude_all/selection_summary.csv",
        *[
            chip_root / "manifest_parts/all" / f"{source_id}.csv"
            for source_id in sorted(set(affected_sources) | set(repair_sources))
        ],
    ]
    plan = {
        "schema_version": SCHEMA,
        "mode": "apply" if apply else "dry_run",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "affected_source_tiff_ids": affected_sources,
        "label_repair_and_rechip_source_tiff_ids": repair_sources,
        "effective_nodata_value_counts": dict(
            sorted(
                Counter(row["source_nodata_value"] for row in source_inventory).items()
            )
        ),
        "nodata_metadata_status_counts": dict(
            sorted(
                Counter(
                    row["nodata_metadata_status"] for row in source_inventory
                ).items()
            )
        ),
        "pre_repair_mutable_files": [
            {
                "path": str(path),
                "row_count": len(_read_csv(path)[1]) if path.suffix == ".csv" else None,
                "sha256": sha256_file(path),
            }
            for path in mutable
        ],
        "operations": {
            "patch": [str(path) for path in mutable],
            "regenerate_label": [
                str(_source_label(raster_root, source)) for source in repair_sources
            ],
            "rechip_source_fragment": repair_sources,
            "remove_active_npz": [
                str(chip_root / row["chip_path"]) for row in added_removals
            ],
            "preserve": [
                str(prior_archive),
                str(prior_checksum),
                str(chip_root / "filter_history/nodata_50"),
            ],
        },
        "transaction_boundary": (
            "all repaired labels, 31 complete source fragments, rewritten NPZs, and "
            "small manifests are staged first; canonical labels/NPZs are quarantined "
            "and all replacements roll back together on failure"
        ),
        "hash_reuse": {
            **trust,
            "criteria": (
                "reuse only unchanged retained NPZs with matching archive path and byte "
                "size; every NPZ in rewritten_npz_inventory.csv must be freshly hashed"
            ),
        },
        "counts": {
            "source_count": len(source_inventory),
            "declared_nonzero_source_count": len(affected_sources),
            "label_repair_source_count": len(repair_sources),
            "label_pixels_to_change": sum(
                int(row["pixels_to_change"]) for row in label_audits
            ),
            "repaired_row_count": len(repair_rows),
            "added_removal_count": len(added_removals),
            "final_active_count": len(final_active),
            "combined_removal_count": len(combined_removals),
        },
    }
    _write_json(history / "repair_plan.json", plan)
    _write_csv(
        history / "source_nodata_inventory.csv",
        source_inventory,
        list(source_inventory[0]),
    )
    _write_csv(history / "label_repair_audit.csv", label_audits, LABEL_AUDIT_COLUMNS)
    affected_rows = [
        row for row in all_original_rows if row["source_tiff_id"] in affected_sources
    ]
    affected_audit = _affected_audit(affected_rows)
    _write_csv(
        history / "affected_source_audit.csv", affected_audit, list(affected_audit[0])
    )
    _write_csv(history / "repaired_rows.csv", repair_rows, REPAIRED_COLUMNS)
    _write_csv(history / "added_removals.csv", added_removals, final_fields)
    if not apply:
        return plan

    final_active_ids = {row["chip_id"] for row in final_active}
    rewritten_rows: list[dict[str, Any]] = []
    for source_id in repair_sources:
        for row in staged_fragments[source_id]:
            staged_npz = staging / "rechipped" / row["chip_path"]
            old_npz = chip_root / row["chip_path"]
            rewritten_rows.append(
                {
                    "chip_id": row["chip_id"],
                    "chip_path": row["chip_path"],
                    "source_tiff_id": source_id,
                    "dataset": row["dataset"],
                    "region_id": row["region_id"],
                    "retained_after_filter": str(
                        row["chip_id"] in final_active_ids
                    ).lower(),
                    "old_present": str(old_npz.exists()).lower(),
                    "old_byte_size": old_npz.stat().st_size if old_npz.exists() else "",
                    "old_sha256": sha256_file(old_npz) if old_npz.exists() else "",
                    "new_byte_size": staged_npz.stat().st_size,
                    "new_sha256": sha256_file(staged_npz),
                    "reason": "derived_label_repair_complete_source_rechip",
                }
            )
    _write_csv(
        history / "rewritten_npz_inventory.csv", rewritten_rows, REWRITTEN_NPZ_COLUMNS
    )

    _write_csv(staging / "chip_manifest.csv", final_active, final_fields)
    summary = _summary_rows(all_original_rows, final_active, combined_removals)
    _write_csv(
        history / "combined_removal_manifest.csv", combined_removals, final_fields
    )
    _write_csv(history / "post_filter_summary.csv", summary, list(summary[0]))
    selections, selection_summary = select_training_chips(
        staging / "chip_manifest.csv", policy="exclude_all"
    )
    _write_csv(staging / "training_selection.csv", selections, SELECTION_COLUMNS)
    _write_csv(staging / "selection_summary.csv", selection_summary, SUMMARY_COLUMNS)
    source_summary = _source_count_rows(all_original_rows)
    _write_csv(
        staging / "chip_counts_by_source.csv", source_summary, list(source_summary[0])
    )

    metadata_fields, metadata_rows = _read_csv(raster_root / "raster_metadata.csv")
    inventory_by_id = {row["source_tiff_id"]: row for row in source_inventory}
    extra_metadata_fields = [
        field
        for field in ("source_nodata_value", "source_nodata_values")
        if field not in metadata_fields
    ]
    patched_metadata = [
        {
            **row,
            "source_nodata_value": inventory_by_id[row["source_tiff_id"]][
                "source_nodata_value"
            ],
            "source_nodata_values": inventory_by_id[row["source_tiff_id"]][
                "source_nodata_values"
            ],
        }
        for row in metadata_rows
    ]
    _write_csv(
        staging / "raster_metadata.csv",
        patched_metadata,
        [*metadata_fields, *extra_metadata_fields],
    )

    alignment_fields, alignment_rows = _read_csv(raster_root / "label_alignment.csv")
    label_audit_by_id = {row["source_tiff_id"]: row for row in label_audits}
    patched_alignment = []
    for row in alignment_rows:
        updated = dict(row)
        audit = label_audit_by_id.get(row["source_tiff_id"])
        if audit:
            updated["image_nodata_pixels"] = str(audit["image_nodata_pixel_count"])
            updated["assigned_nodata_pixels"] = str(
                int(audit["true_positive_count"]) + int(audit["false_negative_count"])
            )
            if source_by_id[updated["source_tiff_id"]]["dataset"] == "bc":
                updated["outside_source_label_not_nodata_pixels"] = str(
                    int(updated["outside_source_label_pixels"])
                    - int(updated["image_nodata_and_outside_label_pixels"])
                )
            values = set(json.loads(audit["pre_label_values"])) | {3}
            updated["output_label_values"] = json.dumps(sorted(values))
        patched_alignment.append(updated)
    _write_csv(staging / "label_alignment.csv", patched_alignment, alignment_fields)

    with (chip_root / "chip_qa_summary.json").open() as file:
        chip_qa = json.load(file)
    chip_qa["artifact"]["chip_manifest_sha256"] = sha256_file(
        staging / "chip_manifest.csv"
    )
    chip_qa["parameters"]["nodata_definition"] = (
        "all retained image bands equal the source TIFF effective nodata value"
    )
    chip_qa["repair"] = {
        "schema_version": SCHEMA,
        "rechip_source_count": len(repair_sources),
    }
    _write_json(staging / "chip_qa_summary.json", chip_qa)

    targets: list[tuple[Path, Path]] = [
        (staging / "chip_manifest.csv", active_path),
        (staging / "raster_metadata.csv", raster_root / "raster_metadata.csv"),
        (staging / "label_alignment.csv", raster_root / "label_alignment.csv"),
        (
            staging / "chip_counts_by_source.csv",
            chip_root / "chip_counts_by_source.csv",
        ),
        (staging / "chip_qa_summary.json", chip_root / "chip_qa_summary.json"),
        (
            staging / "training_selection.csv",
            chip_root / "background_selection/exclude_all/training_selection.csv",
        ),
        (
            staging / "selection_summary.csv",
            chip_root / "background_selection/exclude_all/selection_summary.csv",
        ),
    ]
    for source_id in sorted(set(affected_sources) | set(repair_sources)):
        staged_fragment = staging / f"fragment_{source_id}.csv"
        _write_csv(staged_fragment, repaired_fragments[source_id], final_fields)
        targets.append(
            (staged_fragment, chip_root / "manifest_parts/all" / f"{source_id}.csv")
        )

    shutil.copy2(active_path, history / "pre_repair_active_manifest.csv")
    snapshot_dir = history / "pre_repair_manifests"
    snapshot_dir.mkdir(exist_ok=True)
    for index, path in enumerate(mutable):
        shutil.copy2(path, snapshot_dir / f"{index:03d}_{path.name}")
    label_snapshot_dir = history / "pre_repair_labels"
    label_snapshot_dir.mkdir(exist_ok=True)
    for source_id in repair_sources:
        shutil.copy2(
            _source_label(raster_root, source_id),
            label_snapshot_dir / f"{source_id}.tif",
        )

    quarantine = staging / "quarantine/all"
    quarantine.mkdir(parents=True)
    label_backups = staging / "label_backups"
    label_backups.mkdir()
    replaced: list[tuple[Path, Path]] = []
    installed_npzs: list[Path] = []
    try:
        scoped_existing = [
            path
            for source_id in repair_sources
            for path in (chip_root / "all").glob(f"{source_id}__*.npz")
        ]
        added_removal_paths = [chip_root / row["chip_path"] for row in added_removals]
        for source in sorted(set(scoped_existing + added_removal_paths)):
            if source.exists():
                os.replace(source, quarantine / source.name)
        for source_id in repair_sources:
            canonical_label = _source_label(raster_root, source_id)
            backup = label_backups / canonical_label.name
            os.replace(canonical_label, backup)
            os.replace(staged_labels[source_id], canonical_label)
        for source_id in repair_sources:
            for row in staged_fragments[source_id]:
                if row["chip_id"] not in final_active_ids:
                    continue
                source = staging / "rechipped" / row["chip_path"]
                destination = chip_root / row["chip_path"]
                os.replace(source, destination)
                installed_npzs.append(destination)
        replaced = _replace_from_staging(staging, targets)

        filesystem_ids = {path.stem for path in (chip_root / "all").glob("*.npz")}
        if filesystem_ids != final_active_ids:
            raise RuntimeError("Post-repair active manifest/NPZ inventory mismatch")
        post_label_audits = []
        for source_id in repair_sources:
            row = source_by_id[source_id]
            audit = _label_audit(
                image_path=_source_image(raster_root, source_id),
                label_path=_source_label(raster_root, source_id),
                dataset=row["dataset"],
                nodata_values=values_by_source[source_id],
            )
            if audit["false_negative_count"] or (
                row["dataset"] == "bc" and audit["false_positive_count"]
            ):
                raise RuntimeError(f"Post-repair label mask mismatch for {source_id}")
            post_label_audits.append(
                {
                    "source_tiff_id": source_id,
                    "dataset": row["dataset"],
                    "region_id": row["region_id"],
                    "source_nodata_value": nodata_value_text(
                        values_by_source[source_id]
                    ),
                    **audit,
                    "source_fragment_chip_count": len(repaired_fragments[source_id]),
                    "repair_reason": "post_repair_validation",
                }
            )
        _write_csv(
            history / "post_repair_label_audit.csv",
            post_label_audits,
            LABEL_AUDIT_COLUMNS,
        )

        active_qa = {
            "active_chip_count": len(final_active),
            "active_source_tiff_count": len(
                {row["source_tiff_id"] for row in final_active}
            ),
            "active_npz_bytes": sum(
                (chip_root / row["chip_path"]).stat().st_size for row in final_active
            ),
            "maximum_active_nodata_pct": max(
                float(row["nodata_pct"]) for row in final_active
            ),
            "training_selected_count": sum(
                row["selected_for_training"] == "true" for row in selections
            ),
            "validation": {
                "active_plus_removals_equal_original_6003": True,
                "active_manifest_npz_bijection": True,
                "active_nodata_pct_at_most_50": True,
                "temporal_split_source_join": True,
                "training_selection_one_to_one": len(selections) == len(final_active),
                "california_label_false_negatives_zero": True,
                "bc_label_false_positives_and_false_negatives_zero": True,
            },
        }
        _write_json(history / "active_chip_qa_summary.json", active_qa)
        metadata = {
            "schema_version": SCHEMA,
            "status": "complete",
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "git_commit": _git_commit(),
            "nodata_definition": "all eight retained bands equal the declared value, or explicit effective zero when metadata is wholly missing",
            "threshold_pct": 50,
            "pre_active_manifest_sha256": sha256_file(
                history / "pre_repair_active_manifest.csv"
            ),
            "post_active_manifest_sha256": sha256_file(active_path),
            "repaired_rows_sha256": sha256_file(history / "repaired_rows.csv"),
            "rewritten_npz_inventory_sha256": sha256_file(
                history / "rewritten_npz_inventory.csv"
            ),
            "combined_removal_manifest_sha256": sha256_file(
                history / "combined_removal_manifest.csv"
            ),
            "source_nodata_inventory_sha256": sha256_file(
                history / "source_nodata_inventory.csv"
            ),
            "npz_mutation_count": len(rewritten_rows),
            "npz_retained_rewrite_count": sum(
                row["retained_after_filter"] == "true" for row in rewritten_rows
            ),
            "npz_membership_removal_count": len(added_removals),
            "counts": plan["counts"],
            "hash_reuse": plan["hash_reuse"],
            "artifacts": {
                "active_manifest": "chip_manifest.csv",
                "combined_removal_manifest": (
                    HISTORY_RELATIVE / "combined_removal_manifest.csv"
                ).as_posix(),
                "post_filter_summary": (
                    HISTORY_RELATIVE / "post_filter_summary.csv"
                ).as_posix(),
                "repaired_rows": (HISTORY_RELATIVE / "repaired_rows.csv").as_posix(),
                "rewritten_npz_inventory": (
                    HISTORY_RELATIVE / "rewritten_npz_inventory.csv"
                ).as_posix(),
            },
        }
        _write_json(completion, metadata)
        with (history / "repair.log").open("a") as log:
            log.write(
                json.dumps({"event": "complete", "metadata": metadata}, sort_keys=True)
                + "\n"
            )
        shutil.rmtree(staging)
        return metadata
    except BaseException:
        for backup, target in reversed(replaced):
            if backup.exists():
                os.replace(backup, target)
        for path in installed_npzs:
            path.unlink(missing_ok=True)
        for quarantined in quarantine.glob("*.npz"):
            destination = chip_root / "all" / quarantined.name
            if not destination.exists():
                os.replace(quarantined, destination)
        for backup in label_backups.glob("*.tif"):
            destination = raster_root / "all/labels" / backup.name
            destination.unlink(missing_ok=True)
            os.replace(backup, destination)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chip-root", type=Path, required=True)
    parser.add_argument("--raster-root", type=Path, required=True)
    parser.add_argument("--temporal-split", type=Path, required=True)
    parser.add_argument("--prior-archive", type=Path, required=True)
    parser.add_argument("--prior-checksum", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = repair_dataset(
            chip_root=args.chip_root,
            raster_root=args.raster_root,
            temporal_split=args.temporal_split,
            prior_archive=args.prior_archive,
            prior_checksum=args.prior_checksum,
            apply=args.apply,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
