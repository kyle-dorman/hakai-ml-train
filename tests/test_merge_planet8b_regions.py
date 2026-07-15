from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from merge_planet8b_regions import (
    InventoryError,
    derive_aligned_label,
    discover_inventory,
    materialize,
)
from rasterio.transform import from_origin


def _touch_pair(images: Path, labels: Path, stem: str, suffix: str = ".tif") -> None:
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    (images / f"{stem}{suffix}").write_bytes(f"image-{stem}".encode())
    (labels / f"{stem}{suffix}").write_bytes(f"label-{stem}".encode())


@pytest.fixture
def source_fixture(tmp_path: Path) -> tuple[Path, Path]:
    ca_root = tmp_path / "ca"
    bc_root = tmp_path / "bc"
    _touch_pair(ca_root / "images", ca_root / "labels", "001_20210101_abc", ".TIF")
    _touch_pair(ca_root / "images", ca_root / "labels", "011_20220202_def")
    _touch_pair(
        bc_root / "train" / "images",
        bc_root / "train" / "labels",
        "20210811_scene_clip0",
        ".TIF",
    )
    _touch_pair(
        bc_root / "val" / "images",
        bc_root / "val" / "labels",
        "20220812_scene_clip1",
    )
    return ca_root, bc_root


def test_dry_run_cli_does_not_create_output(
    source_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    ca_root, bc_root = source_fixture
    output_root = tmp_path / "planned"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/merge_planet8b_regions.py",
            "--ca-root",
            str(ca_root),
            "--bc-tiles-root",
            str(bc_root),
            "--output-root",
            str(output_root),
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "2 CA, 2 BC, 4 total, 3 region IDs" in result.stdout
    assert not output_root.exists()


def test_hardlink_materialization_and_manifest(
    source_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    ca_root, bc_root = source_fixture
    output_root = tmp_path / "merged"
    rows = discover_inventory(ca_root, bc_root, output_root, "hardlink")
    materialize(output_root, rows, "hardlink", "uv run python organizer.py")

    assert len(rows) == 4
    for row in rows:
        merged = output_root / "all" / "images" / f"{row.source_tiff_id}.tif"
        assert merged.exists()
        assert os.stat(row.source_image).st_ino == merged.stat().st_ino

    with (output_root / "raster_manifest.csv").open(newline="") as stream:
        manifest = list(csv.DictReader(stream))
    assert [row["source_tiff_id"] for row in manifest] == [
        row.source_tiff_id for row in rows
    ]
    with (output_root / "merge_issues.csv").open(newline="") as stream:
        assert list(csv.DictReader(stream)) == []
    assert (output_root / "creation_command.txt").read_text() == (
        "uv run python organizer.py\n"
    )


def test_duplicate_stem_is_fatal(
    source_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    ca_root, bc_root = source_fixture
    stem = "001_20210101_abc"
    (ca_root / "images" / f"{stem}.tiff").write_bytes(b"duplicate")

    with pytest.raises(InventoryError) as caught:
        discover_inventory(ca_root, bc_root, tmp_path / "out", "hardlink")
    assert "duplicate_stem" in {issue.issue_type for issue in caught.value.issues}


def test_missing_label_is_fatal(
    source_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    ca_root, bc_root = source_fixture
    (ca_root / "labels" / "011_20220202_def.tif").unlink()

    with pytest.raises(InventoryError) as caught:
        discover_inventory(ca_root, bc_root, tmp_path / "out", "hardlink")
    assert "missing_label" in {issue.issue_type for issue in caught.value.issues}


def test_cross_split_destination_collision_is_fatal(
    source_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    ca_root, bc_root = source_fixture
    _touch_pair(
        bc_root / "val" / "images",
        bc_root / "val" / "labels",
        "20210811_scene_clip0",
    )

    with pytest.raises(InventoryError) as caught:
        discover_inventory(ca_root, bc_root, tmp_path / "out", "hardlink")
    assert "destination_collision" in {
        issue.issue_type for issue in caught.value.issues
    }


def test_nonempty_output_is_fatal(
    source_fixture: tuple[Path, Path], tmp_path: Path
) -> None:
    ca_root, bc_root = source_fixture
    output_root = tmp_path / "merged"
    output_root.mkdir()
    (output_root / "keep.txt").write_text("user content")
    rows = discover_inventory(ca_root, bc_root, output_root, "copy")

    with pytest.raises(InventoryError) as caught:
        materialize(output_root, rows, "copy")
    assert caught.value.issues[0].issue_type == "nonempty_output"
    assert (output_root / "keep.txt").read_text() == "user content"


def test_hardlink_cross_filesystem_error_has_copy_guidance(
    source_fixture: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ca_root, bc_root = source_fixture
    output_root = tmp_path / "merged"
    rows = discover_inventory(ca_root, bc_root, output_root, "hardlink")

    def fail_link(_source: str, _destination: str) -> None:
        raise OSError(18, "Invalid cross-device link")

    monkeypatch.setattr("merge_planet8b_regions.os.link", fail_link)
    with pytest.raises(RuntimeError, match="rerun with --mode copy"):
        materialize(output_root, rows, "hardlink")
    assert not output_root.exists()


@pytest.mark.parametrize("family", ["ca", "bc"])
def test_internal_georeferencing_does_not_require_world_file(
    tmp_path: Path, family: str
) -> None:
    source = tmp_path / family / "source.tif"
    source.parent.mkdir(parents=True)
    transform = from_origin(500_000, 5_500_000, 3, 3)
    with rasterio.open(
        source,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="uint8",
        crs="EPSG:32610",
        transform=transform,
    ) as dataset:
        dataset.write(np.ones((1, 2, 2), dtype=np.uint8))
    source.with_suffix(".tfw").write_text("9\n0\n0\n-9\n1\n1\n")

    with_sidecar = tmp_path / f"{family}-with"
    without_sidecar = tmp_path / f"{family}-without"
    with_sidecar.mkdir()
    without_sidecar.mkdir()
    shutil.copy2(source, with_sidecar / source.name)
    shutil.copy2(source.with_suffix(".tfw"), with_sidecar / "source.tfw")
    shutil.copy2(source, without_sidecar / source.name)

    with rasterio.open(with_sidecar / source.name) as with_dataset:
        with_metadata = (with_dataset.crs, with_dataset.transform)
    with rasterio.open(without_sidecar / source.name) as without_dataset:
        without_metadata = (without_dataset.crs, without_dataset.transform)
    assert (
        with_metadata
        == without_metadata
        == (rasterio.crs.CRS.from_epsg(32610), transform)
    )


def test_derived_label_aligns_and_assigns_kate_nodata(tmp_path: Path) -> None:
    image_path = tmp_path / "source" / "image.tif"
    label_path = tmp_path / "source" / "label.tif"
    output_path = tmp_path / "output" / "label.tif"
    image_path.parent.mkdir(parents=True)
    output_path.parent.mkdir(parents=True)
    image = np.ones((8, 4, 4), dtype=np.uint16)
    image[:, 1, 1] = 0
    with rasterio.open(
        image_path,
        "w",
        driver="GTiff",
        width=4,
        height=4,
        count=8,
        dtype="uint16",
        crs="EPSG:32610",
        transform=from_origin(0, 4, 1, 1),
    ) as dataset:
        dataset.write(image)
    with rasterio.open(
        label_path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="uint8",
        crs="EPSG:32610",
        transform=from_origin(1, 3, 1, 1),
        nodata=0,
    ) as dataset:
        dataset.write(np.array([[[0, 1], [1, 0]]], dtype=np.uint8))

    alignment = derive_aligned_label(
        image_path, label_path, output_path, "001_20210101_fixture"
    )

    with rasterio.open(output_path) as output:
        result = output.read(1)
        assert output.shape == (4, 4)
        assert output.transform == from_origin(0, 4, 1, 1)
        assert output.nodata == 3
    assert result.tolist() == [
        [3, 3, 3, 3],
        [3, 3, 1, 3],
        [3, 1, 0, 3],
        [3, 3, 3, 3],
    ]
    assert alignment.source_label_values == "[0, 1]"
    assert alignment.output_label_values == "[0, 1, 3]"
    assert alignment.image_nodata_pixels == 1
    assert alignment.outside_source_label_pixels == 12
    assert alignment.assigned_nodata_pixels == 13
    assert alignment.outside_source_label_not_nodata_pixels == 0
