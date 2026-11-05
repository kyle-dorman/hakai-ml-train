"""Compare canopy change on the same scoreable pixels at two acquisition dates."""

import numpy as np
from rasterio.errors import WindowError
from rasterio.windows import Window, intersection

from kelpseg.reporting.metrics import ratio


def scoreable(canvas: dict) -> np.ndarray:
    """Return pixels with imagery, labels and saved predictions on the canvas grid."""
    return (
        canvas["footprint"]
        & canvas["valid"]
        & (canvas["labels"] != -100)
        & np.isfinite(canvas["probability"])
    )


def unavailable_pair(status: str) -> dict:
    """Return one stable flat pair record, with unavailable measurements left null."""
    result = dict(status=status, common_pixels=0, common_area_m2=None)
    for side in ("earlier", "later"):
        result[f"{side}_scoreable_pixels"] = None
        result[f"{side}_coverage_fraction"] = None
        result[f"{side}_area_bias_m2"] = None
    for series in ("label", "prediction"):
        for date in ("before", "after"):
            result[f"{series}_{date}_pixels"] = None
            result[f"{series}_{date}_area_m2"] = None
        result[f"{series}_change_pixels"] = None
        result[f"{series}_change_area_m2"] = None
        result[f"{series}_change_pct"] = None
        result[f"{series}_zero_baseline"] = None
        result[f"{series}_small_baseline"] = None
    result.update(
        change_error_pixels=None,
        change_error_area_m2=None,
        change_error_pp=None,
        percentage_status="unavailable",
    )
    return result


def common_windows(earlier: dict, later: dict) -> tuple[Window, Window] | str:
    """Return matching integer windows or the reason their grids cannot be paired.

    Identical pixel bases may be rotated; only an integer translation is allowed.
    Rasterio intersects the extents in the earlier image's pixel coordinate system.
    No pixels are resampled or interpolated.
    """
    if earlier["crs"] != later["crs"]:
        return "incompatible_crs"
    crs = earlier["crs"]
    if crs is None or not crs.is_projected or crs.linear_units != "metre":
        return "unsupported_area_units"
    first, second = earlier["transform"], later["transform"]
    if not np.allclose(
        [first.a, first.b, first.d, first.e],
        [second.a, second.b, second.d, second.e],
        rtol=0,
        atol=1e-9,
    ):
        return "incompatible_pixel_basis"
    col_shift, row_shift = (~first) * (second.c, second.f)
    if not np.allclose(
        [col_shift, row_shift],
        np.rint([col_shift, row_shift]),
        rtol=0,
        atol=1e-6,
    ):
        return "fractional_pixel_offset"
    col_shift, row_shift = int(round(col_shift)), int(round(row_shift))
    first_height, first_width = earlier["labels"].shape
    second_height, second_width = later["labels"].shape
    try:
        first_window = intersection(
            Window(0, 0, first_width, first_height),
            Window(col_shift, row_shift, second_width, second_height),
        )
    except WindowError:
        return "no_geometric_overlap"
    second_window = Window(
        first_window.col_off - col_shift,
        first_window.row_off - row_shift,
        first_window.width,
        first_window.height,
    )
    return first_window, second_window


def compare_pair(
    earlier: dict,
    later: dict,
    threshold: float,
    small_baseline_pixels: int = 10,
) -> dict:
    """Measure proportional canopy change on the common valid labeled footprint.

    Inputs are Task 036 source canvases from one model/scope; the caller validates
    date order and location. Threshold is the saved model threshold. Small positive
    starting counts are flagged, never removed. Return counts, square-metre areas,
    coverage and percentage-point error; zero baselines have undefined percentages.
    Unsupported spatial comparisons return a reason with null measurements.
    Arrays are read without modification, inference or file I/O.
    """
    result = unavailable_pair("supported")
    first_valid, second_valid = scoreable(earlier), scoreable(later)
    result["earlier_scoreable_pixels"] = int(first_valid.sum())
    result["later_scoreable_pixels"] = int(second_valid.sum())
    windows = common_windows(earlier, later)
    if isinstance(windows, str):
        result["status"] = windows
        return result
    first_slice, second_slice = (window.toslices() for window in windows)
    common = first_valid[first_slice] & second_valid[second_slice]
    common_pixels = int(common.sum())
    result["common_pixels"] = common_pixels
    result["earlier_coverage_fraction"] = ratio(
        common_pixels, result["earlier_scoreable_pixels"]
    )
    result["later_coverage_fraction"] = ratio(
        common_pixels, result["later_scoreable_pixels"]
    )
    pixel_area = abs(earlier["transform"].determinant)
    result["common_area_m2"] = common_pixels * pixel_area
    if not common_pixels:
        result["status"] = "no_common_scoreable_pixels"
        return result

    for date, canvas, window_slice in (
        ("before", earlier, first_slice),
        ("after", later, second_slice),
    ):
        label = canvas["labels"][window_slice] == 1
        prediction = canvas["probability"][window_slice] >= threshold
        for series, mask in (("label", label), ("prediction", prediction)):
            count = int((mask & common).sum())
            result[f"{series}_{date}_pixels"] = count
            result[f"{series}_{date}_area_m2"] = count * pixel_area

    for series in ("label", "prediction"):
        before = result[f"{series}_before_pixels"]
        after = result[f"{series}_after_pixels"]
        result[f"{series}_change_pixels"] = after - before
        result[f"{series}_change_area_m2"] = (after - before) * pixel_area
        result[f"{series}_change_pct"] = ratio(100 * (after - before), before)
        result[f"{series}_zero_baseline"] = before == 0
        result[f"{series}_small_baseline"] = 0 < before <= small_baseline_pixels
    error = result["prediction_change_pixels"] - result["label_change_pixels"]
    result["change_error_pixels"] = error
    result["change_error_area_m2"] = error * pixel_area
    for side, date in (("earlier", "before"), ("later", "after")):
        result[f"{side}_area_bias_m2"] = (
            result[f"prediction_{date}_pixels"] - result[f"label_{date}_pixels"]
        ) * pixel_area
    label_zero, prediction_zero = (
        result["label_zero_baseline"],
        result["prediction_zero_baseline"],
    )
    if label_zero and prediction_zero:
        result["percentage_status"] = "both_zero_baseline"
    elif label_zero:
        result["percentage_status"] = "label_zero_baseline"
    elif prediction_zero:
        result["percentage_status"] = "prediction_zero_baseline"
    else:
        result["percentage_status"] = "defined"
        result["change_error_pp"] = (
            result["prediction_change_pct"] - result["label_change_pct"]
        )
    return result
