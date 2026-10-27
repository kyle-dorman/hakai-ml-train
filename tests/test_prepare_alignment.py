"""Scientific regression fixtures shared with the historical align/repair logic."""

from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from merge_planet8b_regions import derive_aligned_label
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from rasterio.windows import Window
from repair_planet8b_nodata_metadata import _label_audit

from kelpseg.prepare.alignment import (
    aligned_label,
    audit_label_block,
    repair_label_block,
)
from kelpseg.prepare.nodata import declared_nodata_values, nodata_mask


def write_raster(path, data, transform, *, nodata=None, crs="EPSG:32610"):
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[-1],
        height=data.shape[-2],
        count=data.shape[0],
        dtype=data.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as target:
        target.write(data)


def test_package_alignment_matches_legacy_exact_expected_grid(tmp_path):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    image = np.ones((8, 4, 4), dtype=np.uint16)
    image[:, 1, 1] = 0
    write_raster(image_path, image, from_origin(0, 4, 1, 1), nodata=0)
    write_raster(
        label_path,
        np.array([[[0, 1], [1, 0]]], dtype=np.uint8),
        from_origin(1, 3, 1, 1),
        nodata=0,
    )
    legacy_path = tmp_path / "legacy.tif"
    old = derive_aligned_label(image_path, label_path, legacy_path, "fixture")
    with rasterio.open(image_path) as source, rasterio.open(label_path) as labels:
        result = np.empty((4, 4), dtype=np.uint8)
        coverage = np.empty((4, 4), dtype=bool)
        for row in range(0, 4, 2):
            for col in range(0, 4, 2):
                window = Window(col, row, 2, 2)
                block, valid = aligned_label(source, labels, window, (0, 1, 2, 3, 4))
                result[row : row + 2, col : col + 2] = block
                coverage[row : row + 2, col : col + 2] = valid
        original_nodata = nodata_mask(image, (0,) * 8, band_axis=0)
        result = repair_label_block(result, original_nodata, coverage)
    with rasterio.open(legacy_path) as historical:
        np.testing.assert_array_equal(result, historical.read(1))
    assert result.tolist() == [[3, 3, 3, 3], [3, 3, 1, 3], [3, 1, 0, 3], [3, 3, 3, 3]]
    assert int((~coverage).sum()) == old.outside_source_label_pixels == 12
    legacy_audit = _label_audit(
        image_path=image_path,
        label_path=legacy_path,
        dataset="ca",
        nodata_values=(0,) * 8,
    )
    counts = audit_label_block(original_nodata, result)
    for new, previous in (
        ("total", "total_pixel_count"),
        ("image_nodata", "image_nodata_pixel_count"),
        ("tp", "true_positive_count"),
        ("fp", "false_positive_count"),
        ("fn", "false_negative_count"),
        ("tn", "true_negative_count"),
    ):
        assert counts[new] == legacy_audit[previous]
    assert counts["tp"] + counts["fp"] + counts["fn"] + counts["tn"] == counts["total"]


@pytest.mark.parametrize(
    "trace",
    [
        "ordinary_ca",
        "offset_ca",
        "declared_65535_ca",
        "edge_ca",
        "within_bc",
        "outside_bc",
    ],
)
def test_six_trace_behaviors_in_bounded_fixtures(tmp_path, trace):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    image = np.full((8, 4, 4), 9, dtype=np.uint16)
    nodata = 65535 if trace == "declared_65535_ca" else 0
    image[:, 0, 0] = nodata
    image[0, 0, 1] = nodata  # One missing-looking band is still valid imagery.
    transform = from_origin(0, 4, 1, 1)
    smaller = trace in {"offset_ca", "edge_ca", "outside_bc"}
    label_transform = from_origin(1, 3, 1, 1) if smaller else transform
    labels = np.zeros((1, 2 if smaller else 4, 2 if smaller else 4), dtype=np.uint8)
    labels[0, -1, -1] = 1
    if trace == "edge_ca":
        labels[0, 0, 1] = 3
    if trace == "declared_65535_ca":
        labels[0, 0, 0] = 2
    write_raster(image_path, image, transform, nodata=nodata)
    write_raster(label_path, labels, label_transform, nodata=0)
    with rasterio.open(image_path) as source, rasterio.open(label_path) as annotations:
        values = declared_nodata_values(source, retained_bands=8)
        missing = nodata_mask(source.read(), values, band_axis=0)
        raw, coverage = aligned_label(
            source, annotations, Window(0, 0, 4, 4), (0, 1, 2, 3, 4)
        )
    repaired = repair_label_block(raw, missing, coverage)
    assert missing[0, 0] and not missing[0, 1]
    assert repaired[0, 0] == 3
    assert repaired[-2 if smaller else -1, -2 if smaller else -1] == 1
    assert np.all(repaired[~coverage] == 3)
    if trace == "edge_ca":
        assert repaired[1, 2] == 3 and not missing[1, 2]
    if trace in {"ordinary_ca", "within_bc"}:
        assert coverage.all() and repaired[0, 1] == 0
    if trace == "outside_bc":
        historical = tmp_path / "historical.tif"
        derive_aligned_label(
            image_path, label_path, historical, "bc", assign_outside_nodata=False
        )
        with rasterio.open(historical) as old:
            assert np.all(old.read(1)[~coverage & ~missing] == 0)
        assert int(np.count_nonzero(~coverage & ~missing)) == 11


def test_alignment_ignores_old_source_masks_and_metadata(tmp_path):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    transform = from_origin(0, 2, 1, 1)
    write_raster(image_path, np.ones((8, 2, 2), dtype=np.uint16), transform, nodata=0)
    labels = np.array([[[0, 1], [3, 4]]], dtype=np.uint8)
    write_raster(label_path, labels, transform, nodata=0)
    with (
        rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False),
        rasterio.open(label_path, "r+") as source,
    ):
        source.write_mask(np.zeros((2, 2), dtype=np.uint8))
    assert label_path.with_suffix(".tif.msk").exists()
    label_path.with_suffix(".tif.aux.xml").write_text(
        "<PAMDataset><GeoTransform>900,9,0,900,0,-9</GeoTransform></PAMDataset>"
    )
    with (
        rasterio.Env(GDAL_PAM_ENABLED="NO", GDAL_GEOREF_SOURCES="INTERNAL"),
        rasterio.open(image_path) as image,
        rasterio.open(label_path) as label,
    ):
        actual, coverage = aligned_label(
            image, label, Window(0, 0, 2, 2), (0, 1, 2, 3, 4)
        )
    np.testing.assert_array_equal(actual, labels[0])
    assert coverage.all()


def test_alignment_rejects_different_crs_with_a_clear_error(tmp_path):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    bounds = transform_bounds("EPSG:4326", "EPSG:3857", -124, 49, -123, 50)
    left, bottom, right, top = bounds
    write_raster(
        image_path,
        np.ones((8, 2, 2), dtype=np.uint16),
        from_origin(left, top, (right - left) / 2, (top - bottom) / 2),
        nodata=0,
        crs="EPSG:3857",
    )
    labels = np.array([[[0, 1], [3, 4]]], dtype=np.uint8)
    write_raster(
        label_path, labels, from_origin(-124, 50, 0.5, 0.5), nodata=0, crs="EPSG:4326"
    )
    with (
        rasterio.open(image_path) as image,
        rasterio.open(label_path) as label,
        pytest.raises(ValueError, match="CRS"),
    ):
        aligned_label(image, label, Window(0, 0, 2, 2), (0, 1, 2, 3, 4))


def test_unused_warp_sentinel_is_validated(tmp_path):
    path = tmp_path / "same.tif"
    write_raster(path, np.zeros((1, 2, 2), dtype=np.uint8), from_origin(0, 2, 1, 1))
    with rasterio.open(path) as source, pytest.raises(ValueError, match="255"):
        aligned_label(source, source, Window(0, 0, 2, 2), (0, 255))


def test_alignment_uses_native_categories_instead_of_stale_overviews(tmp_path):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    write_raster(
        image_path,
        np.ones((8, 2, 2), dtype=np.uint16),
        from_origin(0, 16, 8, 8),
        nodata=0,
    )
    write_raster(
        label_path,
        np.zeros((1, 16, 16), dtype=np.uint8),
        from_origin(0, 16, 1, 1),
        nodata=0,
    )
    with rasterio.open(label_path, "r+") as source:
        source.build_overviews([4], Resampling.nearest)
    with rasterio.open(label_path, "r+", OVERVIEW_LEVEL=0) as overview:
        overview.write(np.ones((1, 4, 4), dtype=np.uint8))
    with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
        assert np.all(label.read(1, out_shape=(4, 4)) == 1)
        assert np.all(label.read(1) == 0)
        actual, coverage = aligned_label(image, label, Window(0, 0, 2, 2), (0, 1))
    assert np.all(actual == 0)
    assert coverage.all()


@pytest.mark.parametrize(
    "values,missing",
    [
        ((None, 0), None),
        ((0, 65535), None),
        ((float("nan"),) * 2, None),
        ((float("inf"),) * 2, None),
        ((65536,) * 2, None),
        ((None,) * 2, -1),
    ],
)
def test_invalid_source_declarations_are_explicit(values, missing):
    source = SimpleNamespace(count=2, nodatavals=values, dtypes=("uint16",) * 2)
    with pytest.raises(RuntimeError):
        declared_nodata_values(source, retained_bands=2, missing_value=missing)
