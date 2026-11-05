"""Matched-footprint proportional change uses labels as its reference."""

import numpy as np
import pytest
from rasterio import Affine
from rasterio.crs import CRS

from kelpseg.reporting.temporal_pairs import compare_pair, unavailable_pair

GRID = Affine(3, 0, 300, 0, -3, 600)


def canvas(labels, prediction, transform=GRID, crs="EPSG:32611"):
    labels = np.asarray(labels, dtype=np.int8)
    probability = np.asarray(prediction, dtype=np.float32)
    return dict(
        source={},
        labels=labels,
        probability=probability,
        valid=np.ones(labels.shape, dtype=bool),
        footprint=np.ones(labels.shape, dtype=bool),
        transform=transform,
        crs=CRS.from_string(crs) if crs else None,
    )


def counts_canvas(label_count, prediction_count):
    labels = np.zeros((5, 10), dtype=np.int8)
    probability = np.zeros((5, 10), dtype=np.float32)
    labels.flat[:label_count] = 1
    probability.flat[:prediction_count] = 1
    return canvas(labels, probability)


def test_equal_percentage_changes_despite_multiplicative_bias():
    before, after = counts_canvas(10, 20), counts_canvas(11, 22)
    result = compare_pair(before, after, 0.5)
    assert result["status"] == "supported"
    assert result["label_change_pct"] == result["prediction_change_pct"] == 10
    assert result["change_error_pp"] == 0
    assert result["change_error_pixels"] == 1
    assert result["change_error_area_m2"] == 9
    assert result["earlier_area_bias_m2"] == 90
    assert result["later_area_bias_m2"] == 99
    assert result["label_small_baseline"] is True
    assert result["prediction_small_baseline"] is False
    assert result["common_pixels"] == 50
    assert result["common_area_m2"] == 450
    assert result["earlier_coverage_fraction"] == 1
    assert result["percentage_status"] == "defined"


def test_unequal_changes_use_each_own_baseline_without_clipping():
    result = compare_pair(counts_canvas(1, 2), counts_canvas(11, 12), 0.5, 1)
    assert result["label_change_pct"] == 1000
    assert result["prediction_change_pct"] == 500
    assert result["change_error_pp"] == -500
    assert result["label_small_baseline"] is True
    assert result["prediction_small_baseline"] is False


@pytest.mark.parametrize(
    ("label_before", "prediction_before", "reason"),
    [
        (0, 0, "both_zero_baseline"),
        (0, 4, "label_zero_baseline"),
        (4, 0, "prediction_zero_baseline"),
    ],
)
def test_zero_baselines_are_undefined_not_epsilon_filled(
    label_before, prediction_before, reason
):
    result = compare_pair(
        counts_canvas(label_before, prediction_before), counts_canvas(5, 5), 0.5
    )
    assert result["status"] == "supported"
    assert result["percentage_status"] == reason
    assert result["change_error_pp"] is None
    assert (result["label_change_pct"] is None) == (label_before == 0)
    assert (result["prediction_change_pct"] is None) == (prediction_before == 0)
    assert result["label_change_pixels"] == 5 - label_before
    assert result["prediction_change_pixels"] == 5 - prediction_before
    assert result["label_small_baseline"] == (label_before > 0)


def test_common_footprint_removes_false_change_from_different_extents():
    # Raw label/prediction totals are 4 then 2, but both have two on the shared grid.
    before = canvas([[1, 1, 1, 1]], [[1, 1, 1, 1]])
    after = canvas([[1, 1, 0, 0]], [[1, 1, 0, 0]], GRID * Affine.translation(2, 0))
    result = compare_pair(before, after, 0.5)
    assert result["label_before_pixels"] == result["label_after_pixels"] == 2
    assert result["prediction_before_pixels"] == result["prediction_after_pixels"] == 2
    assert result["label_change_pct"] == result["prediction_change_pct"] == 0
    assert result["common_pixels"] == 2
    assert (
        result["earlier_coverage_fraction"] == result["later_coverage_fraction"] == 0.5
    )


def test_common_mask_excludes_both_dates_unknown_pixels_and_uses_saved_threshold():
    before = canvas([[1, 1, -100, 1, 1, 1]], [[0.7, 0.7, 0.7, 0.7, 0.7, 0.7]])
    after = canvas([[1, 1, 1, 1, 1, 0]], [[np.nan, 0.8, 0.8, 0.8, 0.8, 0.8]])
    before["valid"][0, 1] = False
    after["footprint"][0, 3] = False
    after["labels"][0, 4] = -100
    original = before["labels"].copy()
    result = compare_pair(before, after, 0.8)
    assert result["common_pixels"] == 1
    assert result["label_before_pixels"] == 1
    assert result["label_after_pixels"] == 0
    assert result["prediction_before_pixels"] == 0
    assert result["prediction_after_pixels"] == 1
    assert result["label_change_pct"] == -100
    assert result["prediction_change_pct"] is None
    np.testing.assert_array_equal(before["labels"], original)


@pytest.mark.parametrize(
    ("transform", "crs", "reason"),
    [
        (GRID, "EPSG:32610", "incompatible_crs"),
        (GRID * Affine.scale(2), "EPSG:32611", "incompatible_pixel_basis"),
        (GRID * Affine.translation(0.5, 0), "EPSG:32611", "fractional_pixel_offset"),
        (GRID * Affine.translation(2, 0), "EPSG:32611", "no_geometric_overlap"),
    ],
)
def test_unsupported_grids_return_reasons_with_stable_fields(transform, crs, reason):
    before = canvas([[1, 1]], [[1, 1]])
    after = canvas([[1, 1]], [[1, 1]], transform, crs)
    result = compare_pair(before, after, 0.5)
    assert result["status"] == reason
    assert result.keys() == unavailable_pair(reason).keys()
    assert result["label_before_pixels"] is None
    assert result["change_error_pp"] is None
    assert result["earlier_scoreable_pixels"] == 2


def test_unsupported_area_units_and_empty_common_support():
    before = canvas([[1]], [[1]], crs="EPSG:4326")
    after = canvas([[1]], [[1]], crs="EPSG:4326")
    assert compare_pair(before, after, 0.5)["status"] == "unsupported_area_units"
    before = canvas([[1, -100]], [[1, 1]])
    after = canvas([[-100, 1]], [[1, 1]])
    result = compare_pair(before, after, 0.5)
    assert result["status"] == "no_common_scoreable_pixels"
    assert result["common_pixels"] == result["common_area_m2"] == 0
    assert result["earlier_coverage_fraction"] == result["later_coverage_fraction"] == 0
    assert result["label_change_pct"] is None


def test_identical_rotated_pixel_basis_supports_integer_translation():
    grid = GRID * Affine.rotation(15)
    before = canvas([[1, 1, 0]], [[1, 1, 0]], grid)
    after = canvas([[1, 0, 0]], [[1, 0, 0]], grid * Affine.translation(1, 0))
    result = compare_pair(before, after, 0.5)
    assert result["status"] == "supported"
    assert result["common_pixels"] == 2
    assert result["label_change_pct"] == 0
    assert result["common_area_m2"] == pytest.approx(18)
