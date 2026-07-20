from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin
from repair_planet8b_nodata_metadata import _label_audit, _write_repaired_label


def _image(path: Path, *, nodata: int) -> None:
    data = np.ones((8, 4, 4), dtype=np.uint16)
    data[:, 0, 0] = nodata
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=4,
        height=4,
        count=8,
        dtype="uint16",
        crs="EPSG:32611",
        transform=from_origin(0, 4, 1, 1),
        nodata=nodata,
    ) as output:
        output.write(data)


def _label(path: Path, values: np.ndarray, *, nodata: int | None) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=values.shape[1],
        height=values.shape[0],
        count=1,
        dtype="uint8",
        crs="EPSG:32611",
        transform=from_origin(0, 4, 1, 1),
        nodata=nodata,
    ) as output:
        output.write(values, 1)


def test_california_repair_changes_only_declared_nodata_false_negative(
    tmp_path: Path,
) -> None:
    image = tmp_path / "image.tif"
    merged = tmp_path / "merged.tif"
    repaired = tmp_path / "repaired.tif"
    _image(image, nodata=65535)
    values = np.zeros((4, 4), dtype=np.uint8)
    values[0, 0] = 2
    values[1, 1] = 1
    _label(merged, values, nodata=3)

    _write_repaired_label(
        image_path=image,
        source_label=merged,
        original_label=None,
        destination=repaired,
        dataset="ca",
        nodata_values=(65535,) * 8,
    )
    with rasterio.open(repaired) as source:
        actual = source.read(1)
    assert actual[0, 0] == 3
    assert actual[1, 1] == 1
    assert np.count_nonzero(actual != values) == 1


def test_bc_repair_rebuilds_zero_one_label_then_assigns_exact_image_nodata(
    tmp_path: Path,
) -> None:
    image = tmp_path / "image.tif"
    raw = tmp_path / "raw.tif"
    merged = tmp_path / "merged.tif"
    repaired = tmp_path / "repaired.tif"
    _image(image, nodata=0)
    raw_values = np.zeros((4, 4), dtype=np.uint8)
    raw_values[2, 2] = 1
    _label(raw, raw_values, nodata=None)
    contaminated = raw_values.copy()
    contaminated[3, 3] = 3
    _label(merged, contaminated, nodata=3)

    pre = _label_audit(
        image_path=image,
        label_path=merged,
        dataset="bc",
        nodata_values=(0,) * 8,
    )
    assert pre["false_positive_count"] == 1
    _write_repaired_label(
        image_path=image,
        source_label=merged,
        original_label=raw,
        destination=repaired,
        dataset="bc",
        nodata_values=(0,) * 8,
    )
    post = _label_audit(
        image_path=image,
        label_path=repaired,
        dataset="bc",
        nodata_values=(0,) * 8,
    )
    assert post["false_positive_count"] == post["false_negative_count"] == 0
    with rasterio.open(repaired) as source:
        actual = source.read(1)
    assert actual[0, 0] == 3
    assert actual[2, 2] == 1
    assert actual[3, 3] == 0
