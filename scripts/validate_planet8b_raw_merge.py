#!/usr/bin/env python3
"""Validate a materialized PlanetScope 8-band raw merge at raster level."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import rasterio

from src.prepare.nodata import declared_nodata_values, nodata_mask, nodata_value_text

QA_FIELDS = [
    "source_tiff_id",
    "dataset",
    "region_id",
    "image_width",
    "image_height",
    "label_width",
    "label_height",
    "image_count",
    "label_count",
    "image_dtype",
    "label_dtype",
    "label_nodata",
    "image_crs",
    "label_crs",
    "image_transform",
    "label_transform",
    "bounds_match",
    "shape_match",
    "crs_match",
    "transform_match",
    "image_min",
    "image_max",
    "label_values",
    "image_nodata_not_3_pixels",
    "status",
    "details",
]
METADATA_FIELDS = [
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "width",
    "height",
    "band_count",
    "image_dtype",
    "source_nodata_value",
    "label_dtype",
    "crs",
    "transform_a",
    "transform_b",
    "transform_c",
    "transform_d",
    "transform_e",
    "transform_f",
    "bounds_left",
    "bounds_bottom",
    "bounds_right",
    "bounds_top",
]
MANIFEST_REQUIRED = {
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "source_image",
    "source_label",
    "merged_image",
    "merged_label",
    "materialization_mode",
    "label_preparation",
}
TRANSFORM_PRECISION = 1e-9
BOUNDS_ATOL = 1e-6


class ValidationError(RuntimeError):
    """Raised when the merge cannot satisfy its data contract."""


def _atomic_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def load_manifest(root: Path) -> list[dict[str, str]]:
    """Load and structurally validate the raw-merge manifest."""
    path = root / "raster_manifest.csv"
    if not path.is_file():
        raise ValidationError(f"Missing raster manifest: {path}")
    rows = _read_csv(path)
    fields = set(rows[0]) if rows else set()
    missing = sorted(MANIFEST_REQUIRED - fields)
    if missing:
        raise ValidationError(f"Manifest is missing columns: {', '.join(missing)}")
    ids = [row["source_tiff_id"].casefold() for row in rows]
    duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValidationError(f"Duplicate source_tiff_id values: {duplicates[:5]}")
    return rows


def _dtype_name(dtypes: tuple[str, ...]) -> str:
    unique = sorted(set(dtypes))
    return unique[0] if len(unique) == 1 else json.dumps(unique)


def _number(value: np.generic | int | float) -> int | float:
    scalar = value.item() if isinstance(value, np.generic) else value
    return int(scalar) if isinstance(scalar, (int, np.integer)) else float(scalar)


def _stream_image_range(dataset: rasterio.io.DatasetReader) -> tuple[Any, Any]:
    minimum: Any = None
    maximum: Any = None
    for _, window in dataset.block_windows(1):
        block = dataset.read(window=window)
        block_min = _number(block.min())
        block_max = _number(block.max())
        minimum = block_min if minimum is None else min(minimum, block_min)
        maximum = block_max if maximum is None else max(maximum, block_max)
    return minimum, maximum


def _stream_label_values(dataset: rasterio.io.DatasetReader) -> list[Any]:
    values: set[Any] = set()
    for _, window in dataset.block_windows(1):
        values.update(
            _number(value) for value in np.unique(dataset.read(1, window=window))
        )
    return sorted(values)


def _materialization_issue(row: dict[str, str], image: Path, label: Path) -> str | None:
    source_image = Path(row["source_image"])
    source_label = Path(row["source_label"])
    if not source_image.is_file() or not source_label.is_file():
        return "recorded source image or label is missing"
    mode = row["materialization_mode"]
    label_preparation = row["label_preparation"]
    if mode == "hardlink" and not os.path.samefile(source_image, image):
        return "merged image is not a hard link to the recorded source"
    if mode == "copy" and (
        source_image.stat().st_size != image.stat().st_size
        or os.path.samefile(source_image, image)
    ):
        return "copied image size or inode does not satisfy the copy contract"
    if mode not in {"hardlink", "copy"}:
        return f"unsupported materialization mode {mode!r}"
    if label_preparation == "source":
        if mode == "hardlink" and not os.path.samefile(source_label, label):
            return "merged label is not a hard link to the recorded source"
        if mode == "copy" and source_label.stat().st_size != label.stat().st_size:
            return "copied label size differs from the recorded source"
    elif label_preparation != "derived_aligned":
        return f"unsupported label preparation {label_preparation!r}"
    return None


def validate_pair(row: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Validate one manifest pair and return QA plus portable metadata rows."""
    source_id = row["source_tiff_id"]
    image = Path(row["merged_image"])
    label = Path(row["merged_label"])
    qa: dict[str, Any] = {field: "" for field in QA_FIELDS}
    qa.update(
        source_tiff_id=source_id,
        dataset=row["dataset"],
        region_id=row["region_id"],
        status="error",
    )
    issues: list[str] = []
    expected_image = f"{source_id}.tif"
    if image.name != expected_image or label.name != expected_image:
        issues.append("manifest identity does not match merged filenames")
    if not image.is_file() or not label.is_file():
        missing = [str(path) for path in (image, label) if not path.is_file()]
        issues.append(f"missing merged file(s): {', '.join(missing)}")
        qa["details"] = "; ".join(issues)
        return qa, None
    materialization_issue = _materialization_issue(row, image, label)
    if materialization_issue:
        issues.append(materialization_issue)

    try:
        with rasterio.open(image) as image_ds, rasterio.open(label) as label_ds:
            image_range = _stream_image_range(image_ds)
            label_values = _stream_label_values(label_ds)
            shape_match = (image_ds.width, image_ds.height) == (
                label_ds.width,
                label_ds.height,
            )
            crs_match = image_ds.crs == label_ds.crs
            transform_match = image_ds.transform.almost_equals(
                label_ds.transform, precision=TRANSFORM_PRECISION
            )
            bounds_match = bool(
                np.allclose(
                    tuple(image_ds.bounds),
                    tuple(label_ds.bounds),
                    rtol=0,
                    atol=BOUNDS_ATOL,
                )
            )
            if not shape_match:
                issues.append("image/label shape mismatch")
            if not crs_match:
                issues.append("image/label CRS mismatch")
            if not transform_match:
                issues.append("image/label transform mismatch")
            if not bounds_match:
                issues.append("image/label bounds mismatch")
            if image_ds.count != 8:
                issues.append(f"image has {image_ds.count} bands, expected 8")
            if label_ds.count != 1:
                issues.append(f"label has {label_ds.count} bands, expected 1")

            image_dtype = _dtype_name(image_ds.dtypes)
            label_dtype = _dtype_name(label_ds.dtypes)
            image_nodata_not_3 = 0
            if shape_match and image_ds.count == 8 and label_ds.count == 1:
                for _, window in image_ds.block_windows(1):
                    image_block = image_ds.read(window=window)
                    label_block = label_ds.read(1, window=window)
                    source_nodata = declared_nodata_values(
                        image_ds, retained_bands=8, missing_value=0
                    )
                    image_nodata_not_3 += int(
                        (
                            nodata_mask(image_block, source_nodata, band_axis=0)
                            & (label_block != 3)
                        ).sum()
                    )
            if label_dtype != "uint8":
                issues.append(f"label dtype is {label_dtype}, expected uint8")
            if label_ds.nodata != 3:
                issues.append(f"label nodata is {label_ds.nodata}, expected 3")
            unsupported_values = sorted(set(label_values) - {0, 1, 2, 3, 4})
            if unsupported_values:
                issues.append(f"unsupported KATE label values: {unsupported_values}")
            if image_nodata_not_3:
                issues.append(
                    f"{image_nodata_not_3} all-band-zero image pixels are not label 3"
                )
            qa.update(
                image_width=image_ds.width,
                image_height=image_ds.height,
                label_width=label_ds.width,
                label_height=label_ds.height,
                image_count=image_ds.count,
                label_count=label_ds.count,
                image_dtype=image_dtype,
                label_dtype=label_dtype,
                label_nodata=label_ds.nodata,
                image_crs=str(image_ds.crs or ""),
                label_crs=str(label_ds.crs or ""),
                image_transform=json.dumps(tuple(image_ds.transform)[:6]),
                label_transform=json.dumps(tuple(label_ds.transform)[:6]),
                bounds_match=str(bounds_match).lower(),
                shape_match=str(shape_match).lower(),
                crs_match=str(crs_match).lower(),
                transform_match=str(transform_match).lower(),
                image_min=image_range[0],
                image_max=image_range[1],
                label_values=json.dumps(label_values),
                image_nodata_not_3_pixels=image_nodata_not_3,
            )
            transform = image_ds.transform
            bounds = image_ds.bounds
            metadata = {
                "source_tiff_id": source_id,
                "dataset": row["dataset"],
                "region_id": row["region_id"],
                "region_name": row["region_name"],
                "acquisition_date": row["acquisition_date"],
                "width": image_ds.width,
                "height": image_ds.height,
                "band_count": image_ds.count,
                "image_dtype": image_dtype,
                "source_nodata_value": nodata_value_text(
                    declared_nodata_values(image_ds, retained_bands=8, missing_value=0)
                ),
                "label_dtype": label_dtype,
                "crs": str(image_ds.crs or ""),
                "transform_a": transform.a,
                "transform_b": transform.b,
                "transform_c": transform.c,
                "transform_d": transform.d,
                "transform_e": transform.e,
                "transform_f": transform.f,
                "bounds_left": bounds.left,
                "bounds_bottom": bounds.bottom,
                "bounds_right": bounds.right,
                "bounds_top": bounds.top,
            }
    except Exception as error:  # Rasterio drivers expose several exception classes.
        issues.append(f"raster read failed: {type(error).__name__}: {error}")
        qa["details"] = "; ".join(issues)
        return qa, None

    qa["status"] = "error" if issues else "pass"
    qa["details"] = "; ".join(issues)
    return qa, metadata


def reconcile_split(manifest: list[dict[str, str]], split_csv: Path) -> dict[str, int]:
    """Require a one-to-one identity and metadata join with the temporal split."""
    split_rows = _read_csv(split_csv)
    split_by_id: dict[str, dict[str, str]] = {}
    for row in split_rows:
        source_id = row.get("image_name_stem", "")
        if not source_id or source_id.casefold() in split_by_id:
            raise ValidationError(
                f"Missing or duplicate split source ID: {source_id!r}"
            )
        split_by_id[source_id.casefold()] = row
    manifest_by_id = {row["source_tiff_id"].casefold(): row for row in manifest}
    missing = sorted(set(split_by_id) - set(manifest_by_id))
    extra = sorted(set(manifest_by_id) - set(split_by_id))
    if missing or extra:
        raise ValidationError(
            f"Split reconciliation failed: {len(missing)} missing, {len(extra)} extra"
        )
    mismatches = []
    for source_id, merged in manifest_by_id.items():
        split = split_by_id[source_id]
        compared = {
            "dataset": merged["dataset"],
            "region_id": merged["region_id"],
            "acquisition_date": merged["acquisition_date"],
        }
        if any(split[field] != value for field, value in compared.items()):
            mismatches.append(merged["source_tiff_id"])
    if mismatches:
        raise ValidationError(f"Split metadata mismatch for: {mismatches[:5]}")
    return {
        "manifest_rows": len(manifest),
        "split_rows": len(split_rows),
        "joined_rows": len(manifest),
    }


def _count(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def _validate_provenance(
    root: Path, manifest: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    expected_ids = {row["source_tiff_id"] for row in manifest}
    manifest_by_id = {row["source_tiff_id"]: row for row in manifest}
    alignment = _read_csv(root / "label_alignment.csv")
    copies = _read_csv(root / "copy_verification.csv")
    alignment_ids = {row["source_tiff_id"] for row in alignment}
    copy_ids = {row["source_tiff_id"] for row in copies}
    if alignment_ids != expected_ids or len(alignment) != len(manifest):
        raise ValidationError("Label-alignment provenance is incomplete or duplicated")
    if copy_ids != expected_ids or len(copies) != len(manifest):
        raise ValidationError(
            "Copy-verification provenance is incomplete or duplicated"
        )
    for row in alignment:
        if row["resampling"] != "nearest" or row["output_label_nodata"] != "3":
            raise ValidationError(
                f"Invalid label-alignment policy for {row['source_tiff_id']}"
            )
        outside_not_nodata = int(row["outside_source_label_not_nodata_pixels"])
        if manifest_by_id[row["source_tiff_id"]]["dataset"] == "bc":
            expected = int(row["outside_source_label_pixels"]) - int(
                row["image_nodata_and_outside_label_pixels"]
            )
            if outside_not_nodata != expected:
                raise ValidationError(
                    f"BC outside-coverage provenance mismatch for {row['source_tiff_id']}"
                )
        elif outside_not_nodata != 0:
            raise ValidationError(
                f"Missing-coverage pixels were not nodata for {row['source_tiff_id']}"
            )
    for row in copies:
        if (
            row["source_sha256"] != row["copied_sha256"]
            or row["source_size_bytes"] != row["copied_size_bytes"]
            or row["same_inode"].casefold() != "false"
        ):
            raise ValidationError(
                f"Image copy verification failed for {row['source_tiff_id']}"
            )
    return alignment, copies


def validate_merge(root: Path, split_csv: Path) -> dict[str, Any]:
    """Run full validation and atomically write the QA artifacts."""
    manifest = load_manifest(root)
    split_reconciliation = reconcile_split(manifest, split_csv)
    alignment, copies = _validate_provenance(root, manifest)
    qa_rows: list[dict[str, Any]] = []
    metadata_rows: list[dict[str, Any]] = []
    for index, row in enumerate(manifest, start=1):
        qa, metadata = validate_pair(row)
        qa_rows.append(qa)
        if metadata is not None:
            metadata_rows.append(metadata)
        if index == 1 or index % 25 == 0 or index == len(manifest):
            print(f"Validated {index}/{len(manifest)} pairs", flush=True)
    alignment_totals = {
        field: sum(int(row[field]) for row in alignment)
        for field in (
            "total_pixels",
            "image_nodata_pixels",
            "outside_source_label_pixels",
            "image_nodata_and_outside_label_pixels",
            "assigned_nodata_pixels",
        )
    }
    summary = {
        "bounds_absolute_tolerance": BOUNDS_ATOL,
        "transform_absolute_precision": TRANSFORM_PRECISION,
        "total_pairs": len(qa_rows),
        "counts_by_dataset": _count(manifest, "dataset"),
        "counts_by_region": _count(manifest, "region_id"),
        "counts_by_acquisition_year": dict(
            sorted(Counter(row["acquisition_date"][:4] for row in manifest).items())
        ),
        "counts_by_image_dtype": _count(qa_rows, "image_dtype"),
        "counts_by_label_dtype": _count(qa_rows, "label_dtype"),
        "counts_by_image_band_count": _count(qa_rows, "image_count"),
        "counts_by_label_value_set": _count(qa_rows, "label_values"),
        "counts_by_qa_status": _count(qa_rows, "status"),
        "label_alignment_totals": alignment_totals,
        "copy_verification": {
            "rows": len(copies),
            "matching_sha256": sum(
                row["source_sha256"] == row["copied_sha256"] for row in copies
            ),
            "independent_inodes": sum(
                row["same_inode"].casefold() == "false" for row in copies
            ),
        },
        "split_reconciliation": split_reconciliation,
    }
    _atomic_csv(root / "raster_qa.csv", QA_FIELDS, qa_rows)
    _atomic_csv(root / "raster_metadata.csv", METADATA_FIELDS, metadata_rows)
    _atomic_json(root / "raster_qa_summary.json", summary)
    errors = [row for row in qa_rows if row["status"] != "pass"]
    if errors:
        raise ValidationError(f"Raster QA failed for {len(errors)} pair(s)")
    if len(metadata_rows) != len(manifest):
        raise ValidationError("Portable metadata is incomplete")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--split-csv", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = validate_merge(args.root, args.split_csv)
    except (OSError, ValidationError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 2
    print(
        f"Validation complete: {summary['total_pairs']} pairs, "
        f"{summary['counts_by_qa_status'].get('pass', 0)} passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
