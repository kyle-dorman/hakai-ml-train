from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from validate_planet8b_raw_merge import ValidationError, validate_merge


def _write_raster(
    path: Path, data: np.ndarray, transform=None, nodata: int | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[2],
        height=data.shape[1],
        count=data.shape[0],
        dtype=data.dtype,
        crs="EPSG:32610",
        transform=transform or from_origin(500_000, 5_500_000, 3, 3),
        tiled=True,
        blockxsize=16,
        blockysize=16,
        nodata=nodata,
    ) as dataset:
        dataset.write(data)


def _fixture(tmp_path: Path, bad_label_transform: bool = False) -> tuple[Path, Path]:
    root = tmp_path / "merged"
    source = tmp_path / "source"
    source_id = "001_20210101_scene"
    source_image = source / "images" / f"{source_id}.tif"
    source_label = source / "labels" / f"{source_id}.tif"
    image = np.arange(8 * 4 * 4, dtype=np.uint16).reshape(8, 4, 4)
    label = np.array([[[0, 1, 0, 1]] * 4], dtype=np.uint8)
    _write_raster(source_image, image)
    label_transform = (
        from_origin(500_003, 5_500_000, 3, 3) if bad_label_transform else None
    )
    _write_raster(source_label, label, label_transform, nodata=3)
    merged_image = root / "all" / "images" / f"{source_id}.tif"
    merged_label = root / "all" / "labels" / f"{source_id}.tif"
    merged_image.parent.mkdir(parents=True)
    merged_label.parent.mkdir(parents=True)
    shutil.copy2(source_image, merged_image)
    shutil.copy2(source_label, merged_label)
    fields = [
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
    ]
    with (root / "raster_manifest.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "source_tiff_id": source_id,
                "dataset": "ca",
                "region_id": "ca_001",
                "region_name": "baja_islaNavidad",
                "acquisition_date": "2021-01-01",
                "source_image": source_image,
                "source_label": source_label,
                "merged_image": merged_image,
                "merged_label": merged_label,
                "materialization_mode": "copy",
                "label_preparation": "derived_aligned",
            }
        )
    with (root / "label_alignment.csv").open("w", newline="") as stream:
        fields = [
            "source_tiff_id",
            "resampling",
            "output_label_nodata",
            "outside_source_label_not_nodata_pixels",
            "total_pixels",
            "image_nodata_pixels",
            "outside_source_label_pixels",
            "image_nodata_and_outside_label_pixels",
            "assigned_nodata_pixels",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "source_tiff_id": source_id,
                "resampling": "nearest",
                "output_label_nodata": 3,
                "outside_source_label_not_nodata_pixels": 0,
                "total_pixels": 16,
                "image_nodata_pixels": 0,
                "outside_source_label_pixels": 0,
                "image_nodata_and_outside_label_pixels": 0,
                "assigned_nodata_pixels": 0,
            }
        )
    digest = hashlib.sha256(source_image.read_bytes()).hexdigest()
    with (root / "copy_verification.csv").open("w", newline="") as stream:
        fields = [
            "source_tiff_id",
            "source_size_bytes",
            "copied_size_bytes",
            "source_sha256",
            "copied_sha256",
            "same_inode",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "source_tiff_id": source_id,
                "source_size_bytes": source_image.stat().st_size,
                "copied_size_bytes": merged_image.stat().st_size,
                "source_sha256": digest,
                "copied_sha256": digest,
                "same_inode": False,
            }
        )
    split = tmp_path / "split.csv"
    with split.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["image_name_stem", "dataset", "region_id", "acquisition_date"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "image_name_stem": source_id,
                "dataset": "ca",
                "region_id": "ca_001",
                "acquisition_date": "2021-01-01",
            }
        )
    return root, split


def test_validate_merge_writes_qa_metadata_and_summary(tmp_path: Path) -> None:
    root, split = _fixture(tmp_path)
    summary = validate_merge(root, split)
    assert summary["counts_by_qa_status"] == {"pass": 1}
    assert summary["counts_by_label_value_set"] == {"[0, 1]": 1}
    with (root / "raster_qa.csv").open(newline="") as stream:
        qa = list(csv.DictReader(stream))
    assert qa[0]["image_count"] == "8"
    assert qa[0]["image_min"] == "0"
    assert qa[0]["image_max"] == "127"
    with (root / "raster_metadata.csv").open(newline="") as stream:
        metadata = list(csv.DictReader(stream))
    assert metadata[0]["source_tiff_id"] == "001_20210101_scene"
    assert not any("/" in value for value in metadata[0].values())
    assert json.loads((root / "raster_qa_summary.json").read_text()) == summary


def test_transform_mismatch_is_reported_and_fatal(tmp_path: Path) -> None:
    root, split = _fixture(tmp_path, bad_label_transform=True)
    with pytest.raises(ValidationError, match="failed for 1 pair"):
        validate_merge(root, split)
    with (root / "raster_qa.csv").open(newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["status"] == "error"
    assert "transform mismatch" in row["details"]
    assert "bounds mismatch" in row["details"]


def test_split_metadata_mismatch_stops_before_qa(tmp_path: Path) -> None:
    root, split = _fixture(tmp_path)
    rows = list(csv.DictReader(split.open(newline="")))
    rows[0]["region_id"] = "ca_002"
    with split.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValidationError, match="Split metadata mismatch"):
        validate_merge(root, split)
