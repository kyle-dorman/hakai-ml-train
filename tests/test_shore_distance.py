"""Scientific distance band boundaries and source-grid joins."""

import json

import numpy as np
import pytest
from rasterio import Affine
from rasterio.crs import CRS

from kelpseg.reporting.shore_distance import (
    bin_masks,
    load_shore_sources,
    pixel_area_m2,
    read_shore_canvas,
    validate_distance_edges,
)
from tests.test_reporting import TRANSFORM, csv_file, raster


def test_bands_cover_pixels_once_and_use_half_open_edges():
    land = np.array([[1, 0, 0, 0, 0, 0, 0, 255, 0]], dtype=np.uint8)
    distance = np.array([[0, 0, 30, 60, 120, 250, 500, np.nan, np.nan]])
    masks = bin_masks(land, distance)
    assert list(masks) == [
        "land",
        "0-30",
        "30-60",
        "60-120",
        "120-250",
        "250-500",
        "500+",
        "unknown",
    ]
    np.testing.assert_array_equal(sum(masks.values()), np.ones(land.shape))
    assert masks["unknown"].sum() == 2
    assert masks["500+"][0, 6]
    assert masks["0-30"][0, 1]


@pytest.mark.parametrize(
    "edges", [(1, 30), (0, 30, 30), (0, float("inf")), (0,), (0, True)]
)
def test_bad_distance_edges(edges):
    with pytest.raises(ValueError, match="distance_edges"):
        validate_distance_edges(edges)


def test_area_non_square_metric_grid_and_angular_refusal():
    assert pixel_area_m2(CRS.from_epsg(32611), Affine.scale(3, -6)) == 18
    with pytest.raises(ValueError, match="metre"):
        pixel_area_m2(CRS.from_epsg(4326), Affine.scale(0.01, -0.01))


def shore_rows(tmp_path):
    """Make two overlapping crops with known 3 m land-center distances."""
    rows = []
    for key, start in [("a", 0), ("b", 2)]:
        transform = TRANSFORM * Affine.translation(start, 0)
        land = np.zeros((2, 4), np.uint8)
        distance = np.tile(np.arange(start, start + 4) * 3, (2, 1)).astype(np.float32)
        raster(tmp_path / f"{key}_land.tif", land, transform, nodata=255)
        raster(tmp_path / f"{key}_distance.tif", distance, transform, nodata=np.nan)
        rows.append(
            dict(
                source_key=key,
                land_mask=f"{key}_land.tif",
                distance=f"{key}_distance.tif",
                cap_m=500,
                row_offset=0,
                col_offset=start,
                transform=json.dumps(list(transform)[:6]),
                width=4,
                height=2,
            )
        )
    csv_file(tmp_path / "sources.csv", rows)
    return rows


def test_integer_crop_join_overlap_and_unknown_gaps(tmp_path):
    shore_rows(tmp_path)
    source = dict(source_keys="a;b", row_offset=0, col_offset=0)
    canvas = dict(
        labels=np.zeros((2, 7)),
        source=source,
        transform=TRANSFORM,
        crs=CRS.from_epsg(32611),
    )
    land, distance = read_shore_canvas(tmp_path, load_shore_sources(tmp_path), canvas)
    np.testing.assert_array_equal(distance[:, :6], np.tile(np.arange(6) * 3, (2, 1)))
    assert np.all(land[:, 6] == 255)
    assert np.all(np.isnan(distance[:, 6]))
    canvas["source"]["source_keys"] = "absent"
    with pytest.raises(ValueError, match="Missing shoreline"):
        read_shore_canvas(tmp_path, load_shore_sources(tmp_path), canvas)


def test_manifest_duplicate_and_shifted_grid_refused(tmp_path):
    rows = shore_rows(tmp_path)
    csv_file(tmp_path / "sources.csv", [rows[0], rows[0]])
    with pytest.raises(ValueError, match="duplicate"):
        load_shore_sources(tmp_path)
    csv_file(tmp_path / "sources.csv", rows)
    raster(
        tmp_path / "a_land.tif",
        np.zeros((2, 4), np.uint8),
        TRANSFORM * Affine.translation(1, 0),
        nodata=255,
    )
    canvas = dict(
        labels=np.zeros((2, 4)),
        source=dict(source_key="a"),
        transform=TRANSFORM,
        crs=CRS.from_epsg(32611),
    )
    with pytest.raises(ValueError, match="rasters must match"):
        read_shore_canvas(tmp_path, load_shore_sources(tmp_path), canvas)
