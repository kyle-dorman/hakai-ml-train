"""Independent nearest-pixel expectations for the deliberately small alignment API."""

from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.transform import from_origin
from rasterio.windows import Window

from kelpseg.prepare.alignment import aligned_label


def write_raster(path, values, transform, *, crs="EPSG:32610", nodata=None):
    if values.ndim == 2:
        values = values[None]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=values.shape[2],
        height=values.shape[1],
        count=values.shape[0],
        dtype=values.dtype,
        transform=transform,
        crs=crs,
        nodata=nodata,
    ) as target:
        target.write(values)


def expected_nearest(image_transform, label_transform, categories, window):
    """Look up each image pixel center directly, without Rasterio warping."""
    expected = np.zeros((int(window.height), int(window.width)), dtype=np.uint8)
    coverage = np.zeros(expected.shape, dtype=bool)
    for row in range(expected.shape[0]):
        for col in range(expected.shape[1]):
            x, y = image_transform * (
                window.col_off + col + 0.5,
                window.row_off + row + 0.5,
            )
            source_col, source_row = ~label_transform * (x, y)
            native_col = int(np.floor(source_col))
            native_row = int(np.floor(source_row))
            if (
                0 <= native_row < categories.shape[0]
                and 0 <= native_col < categories.shape[1]
            ):
                coverage[row, col] = True
                expected[row, col] = categories[native_row, native_col]
    return expected, coverage


@pytest.mark.parametrize(
    "label_transform",
    [
        from_origin(0, 8, 1, 1),
        from_origin(1.25, 6.75, 1, 1),
        from_origin(-1.25, 9.25, 1, 1),
        from_origin(0.2, 7.8, 0.8, 0.8),
        from_origin(1.2, 6.8, 1.6, 1.6),
    ],
)
@pytest.mark.parametrize("origin", [(0, 0), (557371, 5755856)])
def test_partial_coverage_matches_pixel_centers_and_window_seams(
    tmp_path, label_transform, origin
):
    # Large fractional map coordinates expose rounding and tile-seam errors.
    map_origin = Affine.translation(*origin)
    image_transform = map_origin * from_origin(0, 8, 1, 1)
    label_transform = map_origin * label_transform
    categories = np.array(
        [[0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [1, 0, 3, 4, 2], [2, 4, 0, 3, 1]],
        dtype=np.uint8,
    )
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    write_raster(image_path, np.ones((3, 8, 9), dtype=np.uint16), image_transform)
    write_raster(label_path, categories, label_transform, nodata=0)
    with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
        whole, whole_coverage = aligned_label(
            image, label, Window(0, 0, 9, 8), (0, 1, 2, 3, 4)
        )
        expected, expected_coverage = expected_nearest(
            image_transform, label_transform, categories, Window(0, 0, 9, 8)
        )
        np.testing.assert_array_equal(whole_coverage, expected_coverage)
        np.testing.assert_array_equal(
            whole[whole_coverage], expected[expected_coverage]
        )
        for row in range(0, 8, 3):
            for col in range(0, 9, 4):
                width, height = min(4, 9 - col), min(3, 8 - row)
                window = Window(col, row, width, height)
                actual, coverage = aligned_label(image, label, window, (0, 1, 2, 3, 4))
                np.testing.assert_array_equal(
                    coverage, whole_coverage[row : row + height, col : col + width]
                )
                np.testing.assert_array_equal(
                    actual[coverage],
                    whole[row : row + height, col : col + width][coverage],
                )


def test_no_overlap_returns_an_empty_footprint_with_the_target_window_shape(tmp_path):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    write_raster(
        image_path, np.ones((3, 4, 5), dtype=np.uint16), from_origin(0, 4, 1, 1)
    )
    write_raster(
        label_path,
        np.zeros((2, 2), dtype=np.uint8),
        from_origin(100, 100, 1, 1),
        nodata=0,
    )
    with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
        actual, coverage = aligned_label(
            image, label, Window(1, 1, 3, 2), (0, 1, 2, 3, 4)
        )
    assert actual.shape == coverage.shape == (2, 3)
    assert not coverage.any()


@pytest.mark.parametrize(
    "transform",
    [
        Affine(1, 0.1, 0, 0, -1, 4),
        Affine(1, 0, 0, 0.1, -1, 4),
        Affine(1, 0, 0, 0, 1, 4),
    ],
)
def test_rotated_or_south_up_inputs_fail_clearly(tmp_path, transform):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    write_raster(
        image_path, np.ones((3, 4, 5), dtype=np.uint16), from_origin(0, 4, 1, 1)
    )
    write_raster(label_path, np.zeros((2, 2), dtype=np.uint8), transform)
    with (
        rasterio.open(image_path) as image,
        rasterio.open(label_path) as label,
        pytest.raises(ValueError, match="north|rotat|transform|grid"),
    ):
        aligned_label(image, label, Window(0, 0, 2, 2), (0, 1, 2, 3, 4))


@pytest.mark.parametrize(
    "values", [np.zeros((2, 2, 2), dtype=np.uint8), np.zeros((2, 2), dtype=np.uint16)]
)
def test_unsupported_label_layout_fails_clearly(tmp_path, values):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    transform = from_origin(0, 4, 1, 1)
    write_raster(image_path, np.ones((3, 4, 5), dtype=np.uint16), transform)
    write_raster(label_path, values, transform)
    with (
        rasterio.open(image_path) as image,
        rasterio.open(label_path) as label,
        pytest.raises(ValueError, match="band|uint8|dtype"),
    ):
        aligned_label(image, label, Window(0, 0, 2, 2), (0, 1, 2, 3, 4))


@pytest.mark.parametrize(
    "window",
    [
        Window(0, 0, 0, 2),
        Window(-1, 0, 2, 2),
        Window(0, 0, 99, 2),
        Window(0.5, 0, 2, 2),
        Window(0, 0, 2.5, 2),
    ],
)
def test_invalid_target_window_fails_clearly(tmp_path, window):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    transform = from_origin(0, 4, 1, 1)
    write_raster(image_path, np.ones((3, 4, 5), dtype=np.uint16), transform)
    write_raster(label_path, np.zeros((2, 2), dtype=np.uint8), transform)
    with (
        rasterio.open(image_path) as image,
        rasterio.open(label_path) as label,
        pytest.raises(ValueError, match="window|Window|integer"),
    ):
        aligned_label(image, label, window, (0, 1, 2, 3, 4))


def test_oversized_native_crop_fails_before_reading_source_pixels():
    crs = rasterio.crs.CRS.from_epsg(32610)
    image = SimpleNamespace(
        name="image.tif",
        width=3,
        height=3,
        count=3,
        dtypes=("uint16",) * 3,
        crs=crs,
        transform=from_origin(0, 6000, 2000, 2000),
    )
    label = SimpleNamespace(
        name="label.tif",
        width=6000,
        height=6000,
        count=1,
        dtypes=("uint8",),
        crs=crs,
        transform=from_origin(0, 6000, 1, 1),
        read=lambda *args, **kwargs: pytest.fail("oversized crop was read"),
    )
    with pytest.raises(ValueError, match="block_size|large|crop|pixels"):
        aligned_label(image, label, Window(0, 0, 3, 3), (0, 1, 2, 3, 4))


def test_stored_warp_fill_value_cannot_be_mistaken_for_missing_coverage(tmp_path):
    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    transform = from_origin(0, 2, 1, 1)
    write_raster(image_path, np.ones((3, 2, 2), dtype=np.uint16), transform)
    write_raster(label_path, np.array([[0, 1], [3, 255]], dtype=np.uint8), transform)
    with (
        rasterio.open(image_path) as image,
        rasterio.open(label_path) as label,
        pytest.raises(ValueError, match="255|categor|label"),
    ):
        aligned_label(image, label, Window(0, 0, 2, 2), (0, 1, 2, 3, 4))


@pytest.mark.parametrize("window", [Window(0, 0, 5, 4), Window(1, 1, 3, 2)])
def test_matching_grids_read_stored_labels_without_reprojection(
    tmp_path, monkeypatch, window
):
    from kelpseg.prepare import alignment

    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    grid = from_origin(100, 200, 3, 3)
    categories = np.array(
        [[0, 1, 2, 3, 4], [4, 3, 2, 1, 0], [1, 0, 3, 4, 2], [2, 4, 0, 3, 1]],
        dtype=np.uint8,
    )
    write_raster(image_path, np.ones((3, 4, 5), dtype=np.uint16), grid)
    write_raster(label_path, categories, grid, nodata=0)
    # Even a conflicting source mask must not hide stored water or class 3.
    with (
        rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False),
        rasterio.open(label_path, "r+") as label,
    ):
        label.write_mask(np.zeros(categories.shape, dtype=np.uint8))

    def unexpected_reprojection(*args, **kwargs):
        pytest.fail("Matching grids must read native labels without reprojection")

    monkeypatch.setattr(alignment, "reproject", unexpected_reprojection)
    with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
        actual, coverage = aligned_label(image, label, window, (0, 1, 2, 3, 4))
    row, col = int(window.row_off), int(window.col_off)
    expected = categories[row : row + int(window.height), col : col + int(window.width)]
    np.testing.assert_array_equal(actual, expected)
    assert coverage.all()


def test_different_grids_reproject_and_preserve_expected_coverage(
    tmp_path, monkeypatch
):
    from kelpseg.prepare import alignment

    image_path, label_path = tmp_path / "image.tif", tmp_path / "label.tif"
    image_grid = from_origin(0, 4, 1, 1)
    label_grid = from_origin(1.25, 3.75, 1, 1)
    categories = np.array([[0, 1, 2], [3, 4, 0]], dtype=np.uint8)
    write_raster(image_path, np.ones((3, 4, 5), dtype=np.uint16), image_grid)
    write_raster(label_path, categories, label_grid, nodata=0)
    calls = []
    original_reproject = alignment.reproject

    def count_reprojection(**kwargs):
        calls.append(1)
        return original_reproject(**kwargs)

    monkeypatch.setattr(alignment, "reproject", count_reprojection)
    window = Window(0, 0, 5, 4)
    with rasterio.open(image_path) as image, rasterio.open(label_path) as label:
        actual, coverage = aligned_label(image, label, window, (0, 1, 2, 3, 4))
    expected, expected_coverage = expected_nearest(
        image_grid, label_grid, categories, window
    )
    assert len(calls) == 1
    np.testing.assert_array_equal(coverage, expected_coverage)
    np.testing.assert_array_equal(actual[coverage], expected[expected_coverage])


def test_oversized_matching_window_fails_before_reading_source_pixels():
    crs = rasterio.crs.CRS.from_epsg(32610)
    grid = from_origin(0, 6000, 1, 1)
    image = SimpleNamespace(width=6000, height=6000, crs=crs, transform=grid)
    label = SimpleNamespace(
        width=6000,
        height=6000,
        count=1,
        dtypes=("uint8",),
        crs=crs,
        transform=grid,
        read=lambda *args, **kwargs: pytest.fail("oversized matching window was read"),
    )
    with pytest.raises(ValueError, match="block_size|large|crop|pixels"):
        aligned_label(image, label, Window(0, 0, 6000, 6000), (0, 1, 2, 3, 4))
