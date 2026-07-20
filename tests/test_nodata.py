from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.prepare.nodata import declared_nodata_values, nodata_mask


def _raster(path: Path, *, nodata: int | None) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=8,
        dtype="uint16",
        crs="EPSG:32611",
        transform=from_origin(0, 2, 1, 1),
        nodata=nodata,
    ) as output:
        output.write(np.zeros((8, 2, 2), dtype=np.uint16))


@pytest.mark.parametrize(
    ("declared", "expected"),
    [(0, 0), (65535, 65535), (None, 0)],
)
def test_effective_nodata_preserves_uint16_values_and_defaults_missing_to_zero(
    tmp_path: Path, declared: int | None, expected: int
) -> None:
    path = tmp_path / f"nodata_{declared}.tif"
    _raster(path, nodata=declared)
    with rasterio.open(path) as source:
        values = declared_nodata_values(source, retained_bands=8, missing_value=0)
    assert values == (expected,) * 8

    image = np.full((2, 2, 8), 1, dtype=np.uint16)
    image[0, 0] = expected
    image[0, 1, 0] = expected
    mask = nodata_mask(image, values, band_axis=-1)
    assert mask.tolist() == [[True, False], [False, False]]


def test_missing_nodata_requires_an_explicit_policy(tmp_path: Path) -> None:
    path = tmp_path / "missing.tif"
    _raster(path, nodata=None)
    with (
        rasterio.open(path) as source,
        pytest.raises(RuntimeError, match="missing nodata metadata"),
    ):
        declared_nodata_values(source, retained_bands=8)
