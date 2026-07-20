from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.validate_chip_dataset import validate_chip_dataset
from src.prepare.make_chip_dataset import run_manifested_split


def _write_raster(
    path: Path,
    array: np.ndarray,
    *,
    transform=None,
    nodata=0,
) -> None:
    if array.ndim == 2:
        array = array[np.newaxis, ...]
    transform = transform or from_origin(100, 200, 10, 10)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=array.shape[2],
        height=array.shape[1],
        count=array.shape[0],
        dtype=array.dtype,
        crs="EPSG:32610",
        transform=transform,
        nodata=nodata,
    ) as dataset:
        dataset.write(array)


def _write_source_manifest(path: Path, source_id: str = "fixture") -> None:
    fieldnames = [
        "source_tiff_id",
        "dataset",
        "region_id",
        "region_name",
        "acquisition_date",
    ]
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "source_tiff_id": source_id,
                "dataset": "fixture_dataset",
                "region_id": "fixture_region",
                "region_name": "Fixture Region",
                "acquisition_date": "2026-07-15",
            }
        )


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    raw_root = tmp_path / "raw"
    output_root = tmp_path / "chips"
    source_manifest = raw_root / "raster_manifest.csv"
    image = np.full((8, 6, 6), 10, dtype=np.uint16)
    image[:, 0, 0] = 0
    label = np.array(
        [
            [0, 0, 0, 0, 0, 0],
            [0, 1, 1, 0, 0, 0],
            [0, 1, 3, 0, 1, 0],
            [0, 0, 0, 0, 1, 0],
            [1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
        ],
        dtype=np.uint8,
    )
    _write_raster(raw_root / "all" / "images" / "fixture.tif", image)
    _write_raster(raw_root / "all" / "labels" / "fixture.tif", label)
    _write_source_manifest(source_manifest)
    return raw_root, output_root, source_manifest


def _run(
    raw_root: Path,
    output_root: Path,
    source_manifest: Path,
    *,
    resume: bool,
    num_workers: int = 0,
) -> Path:
    manifest = output_root / "chip_manifest.csv"
    run_manifested_split(
        data_dir=raw_root,
        output_dir=output_root,
        split="all",
        source_manifest=source_manifest,
        manifest_output=manifest,
        chip_size=4,
        chip_stride=2,
        num_bands=8,
        band_remapping=(0, 1, 0, -100, 0),
        dtype=np.dtype("uint16"),
        resume=resume,
        num_workers=num_workers,
    )
    return manifest


def test_manifested_chipping_geometry_statistics_resume_and_reconstruction(
    tmp_path: Path,
) -> None:
    raw_root, output_root, source_manifest = _fixture(tmp_path)
    manifest = _run(raw_root, output_root, source_manifest, resume=False, num_workers=2)

    with manifest.open(newline="") as file:
        rows = list(csv.DictReader(file))
        assert file.seekable()
    assert len(rows) == 4
    assert [row["chip_id"] for row in rows] == [
        "fixture__r0_c0_h4_w4",
        "fixture__r0_c2_h4_w4",
        "fixture__r2_c0_h4_w4",
        "fixture__r2_c2_h4_w4",
    ]
    assert [(int(row["row_off"]), int(row["col_off"])) for row in rows] == [
        (0, 0),
        (0, 2),
        (2, 0),
        (2, 2),
    ]
    assert tuple(float(rows[0][key]) for key in ("minx", "miny", "maxx", "maxy")) == (
        100.0,
        160.0,
        140.0,
        200.0,
    )
    assert rows[0]["source_crs"] == "EPSG:32610"
    assert int(rows[0]["class_0_pixel_count"]) == 12
    assert int(rows[0]["class_1_pixel_count"]) == 3
    assert int(rows[0]["ignore_pixel_count"]) == 1
    assert int(rows[0]["nodata_pixel_count"]) == 1
    assert float(rows[0]["nodata_pct"]) == pytest.approx(6.25)

    probability_sum = np.zeros((6, 6), dtype=np.float64)
    coverage = np.zeros((6, 6), dtype=np.uint8)
    truth = np.zeros((6, 6), dtype=np.int64)
    for index, row in enumerate(rows):
        chip_path = output_root / row["chip_path"]
        with np.load(chip_path) as chip:
            image, label = chip["image"], chip["label"]
        assert image.shape == (4, 4, 8)
        assert label.shape == (4, 4)
        assert str(image.dtype) == row["image_dtype"] == "uint16"
        assert str(label.dtype) == row["label_dtype"] == "int64"
        class_total = sum(
            int(value) for key, value in row.items() if key.startswith("class_")
        )
        assert class_total + int(row["ignore_pixel_count"]) == label.size
        row_off, col_off = int(row["row_off"]), int(row["col_off"])
        window = np.s_[row_off : row_off + 4, col_off : col_off + 4]
        probability_sum[window] += 0.2 * (index + 1)
        coverage[window] += 1
        truth[window] = np.where(label == -100, 0, label)

    assert np.array_equal(
        coverage,
        np.array(
            [
                [1, 1, 2, 2, 1, 1],
                [1, 1, 2, 2, 1, 1],
                [2, 2, 4, 4, 2, 2],
                [2, 2, 4, 4, 2, 2],
                [1, 1, 2, 2, 1, 1],
                [1, 1, 2, 2, 1, 1],
            ],
            dtype=np.uint8,
        ),
    )
    averaged = probability_sum / coverage
    prediction = averaged >= 0.5
    valid = coverage > 0
    true_positive = np.count_nonzero(valid & prediction & (truth == 1))
    true_negative = np.count_nonzero(valid & ~prediction & (truth == 0))
    false_positive = np.count_nonzero(valid & prediction & (truth == 0))
    false_negative = np.count_nonzero(valid & ~prediction & (truth == 1))
    assert true_positive + true_negative + false_positive + false_negative == 36

    original_manifest = manifest.read_bytes()
    _run(raw_root, output_root, source_manifest, resume=True)
    assert manifest.read_bytes() == original_manifest
    assert len(list((output_root / "all").glob("*.npz"))) == 4


def test_resume_rejects_corrupt_completed_source(tmp_path: Path) -> None:
    raw_root, output_root, source_manifest = _fixture(tmp_path)
    _run(raw_root, output_root, source_manifest, resume=False)
    chip = next((output_root / "all").glob("*.npz"))
    chip.write_bytes(b"not an npz")

    with pytest.raises(ValueError):
        _run(raw_root, output_root, source_manifest, resume=True)


def test_failed_source_writes_issue_without_fragment(tmp_path: Path) -> None:
    raw_root, output_root, source_manifest = _fixture(tmp_path)
    label_path = raw_root / "all" / "labels" / "fixture.tif"
    label_path.unlink()
    _write_raster(label_path, np.zeros((5, 6), dtype=np.uint8))

    with pytest.raises(RuntimeError, match="dimensions differ"):
        _run(raw_root, output_root, source_manifest, resume=False)

    issue_path = output_root / ".chip_issues" / "all" / "fixture.json"
    assert json.loads(issue_path.read_text())["source_tiff_id"] == "fixture"
    assert not (output_root / "manifest_parts" / "all" / "fixture.csv").exists()
    assert not list((output_root / "all").glob("fixture__*.npz"))


@pytest.mark.parametrize(
    (
        "height",
        "width",
        "expected_shapes",
        "expected_offsets",
        "expected_positive_counts",
    ),
    [
        (3, 6, [(3, 4), (3, 4)], [(0, 0), (0, 2)], [1, 0]),
        (3, 2, [(3, 2)], [(0, 0)], [1]),
    ],
)
def test_sources_smaller_than_chip_use_true_size_windows(
    tmp_path: Path,
    height: int,
    width: int,
    expected_shapes: list[tuple[int, int]],
    expected_offsets: list[tuple[int, int]],
    expected_positive_counts: list[int],
) -> None:
    raw_root = tmp_path / "raw"
    output_root = tmp_path / "chips"
    source_manifest = raw_root / "raster_manifest.csv"
    image = np.full((8, height, width), 10, dtype=np.uint16)
    label = np.zeros((height, width), dtype=np.uint8)
    label[0, 0] = 1
    _write_raster(raw_root / "all" / "images" / "fixture.tif", image)
    _write_raster(raw_root / "all" / "labels" / "fixture.tif", label)
    _write_source_manifest(source_manifest)

    manifest = _run(raw_root, output_root, source_manifest, resume=False)
    with manifest.open(newline="") as file:
        rows = list(csv.DictReader(file))

    assert [
        (int(row["chip_height"]), int(row["chip_width"])) for row in rows
    ] == expected_shapes
    assert [
        (int(row["row_off"]), int(row["col_off"])) for row in rows
    ] == expected_offsets
    for row, shape, positive_count in zip(
        rows, expected_shapes, expected_positive_counts, strict=True
    ):
        assert row["chip_id"].endswith(f"_h{shape[0]}_w{shape[1]}")
        with np.load(output_root / row["chip_path"]) as chip:
            assert chip["image"].shape == (*shape, 8)
            assert chip["label"].shape == shape
        assert int(row["total_pixel_count"]) == shape[0] * shape[1]
        assert int(row["class_1_pixel_count"]) == positive_count
        assert float(row["maxy"]) - float(row["miny"]) == 10 * shape[0]
        assert float(row["maxx"]) - float(row["minx"]) == 10 * shape[1]

    original_manifest = manifest.read_bytes()
    _run(raw_root, output_root, source_manifest, resume=True)
    assert manifest.read_bytes() == original_manifest


def test_validation_writes_required_summaries(tmp_path: Path) -> None:
    raw_root, output_root, source_manifest = _fixture(tmp_path)
    _run(raw_root, output_root, source_manifest, resume=False)

    summary = validate_chip_dataset(
        chip_root=output_root,
        raw_root=raw_root,
        source_manifest=source_manifest,
        chip_size=4,
        chip_stride=2,
    )

    assert summary["inventory"]["manifest_row_count"] == 4
    assert summary["inventory"]["source_count"] == 1
    assert summary["validation"]["manifest_npz_bijection"] is True
    assert (output_root / "chip_qa_summary.json").is_file()
    with (output_root / "chip_counts_by_source.csv").open(newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]["chip_count"] == "4"
