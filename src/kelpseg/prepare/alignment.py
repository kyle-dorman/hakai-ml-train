"""Align stored label categories using ordinary Rasterio reads and reprojection.

Only same-CRS, north-up grids and one-band uint8 labels are supported. Each call
returns one image window's categories and annotation footprint as plain arrays.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import Window, bounds, from_bounds, transform

# A native crop is at most 16 MiB of uint8 labels. Smaller processing windows
# can handle finer source grids without loading an entire regional mosaic.
MAX_LABEL_CROP_PIXELS = 16_777_216


def validate_alignment(image, label) -> None:
    """Fail on unsupported paired headers before reading any label pixels."""
    if label.count != 1 or label.dtypes != ("uint8",):
        raise ValueError("Label alignment requires exactly one uint8 band.")
    if image.crs is None or label.crs is None or image.crs != label.crs:
        raise ValueError(
            "Image and label must declare the same CRS; cross-CRS alignment is not supported."
        )
    for source in (image, label):
        grid = source.transform
        if (
            not all(math.isfinite(value) for value in grid)
            or grid.b != 0
            or grid.d != 0
            or grid.a <= 0
            or grid.e >= 0
        ):
            raise ValueError(
                "Label alignment supports only north-up, unrotated image and label grids."
            )


def aligned_label(
    image: rasterio.io.DatasetReader,
    label: rasterio.io.DatasetReader,
    window: Window,
    label_values: Sequence[int],
) -> tuple[np.ndarray, np.ndarray]:
    """Read and nearest-align one image window, preserving stored class zero.

    Input nodata declarations and masks are deliberately ignored for categories.
    Temporary 255 means no annotation; supported labels must never contain it.
    """
    validate_alignment(image, label)
    if not label_values or any(
        type(value) is not int or not 0 <= value < 255 for value in label_values
    ):
        raise ValueError(
            "Supported label categories must be integers 0..254; temporary sentinel 255 must be unused."
        )
    coordinates = (window.col_off, window.row_off, window.width, window.height)
    if (
        any(not math.isfinite(value) or value != int(value) for value in coordinates)
        or window.width <= 0
        or window.height <= 0
        or window.col_off < 0
        or window.row_off < 0
        or window.col_off + window.width > image.width
        or window.row_off + window.height > image.height
    ):
        raise ValueError(
            "Alignment window must use integer pixels and lie inside the image."
        )

    shape = (int(window.height), int(window.width))
    if (
        image.width == label.width
        and image.height == label.height
        and image.transform == label.transform
    ):
        # These stored pixels already occupy the exact image grid. Read them
        # unchanged; masks and nodata=0 metadata must not hide water categories.
        if window.width * window.height > MAX_LABEL_CROP_PIXELS:
            raise ValueError(
                "Native label window exceeds 16,777,216 pixels. Reduce recipe block_size."
            )
        categories = label.read(1, window=window, masked=False)
        if not np.isin(categories, label_values).all():
            raise ValueError(
                "Source label window contains unsupported categories; check the recipe label_values (255 is reserved)."
            )
        return categories, np.ones(shape, dtype=bool)

    # Find just the native label cells that can contribute to this image window.
    # Round outward before clipping, retaining edge pixels for nearest sampling.
    crop = from_bounds(*bounds(window, image.transform), transform=label.transform)
    col_start = max(0, math.floor(crop.col_off))
    row_start = max(0, math.floor(crop.row_off))
    col_stop = min(label.width, math.ceil(crop.col_off + crop.width))
    row_stop = min(label.height, math.ceil(crop.row_off + crop.height))
    if col_stop <= col_start or row_stop <= row_start:
        return np.zeros(shape, dtype=np.uint8), np.zeros(shape, dtype=bool)
    if (col_stop - col_start) * (row_stop - row_start) > MAX_LABEL_CROP_PIXELS:
        raise ValueError(
            "Native label crop exceeds 16,777,216 pixels. Reduce recipe block_size or use a supported source resolution."
        )
    source_window = Window(
        col_start, row_start, col_stop - col_start, row_stop - row_start
    )

    # No out_shape: read original cells, never an overview. A plain ndarray
    # carries no source masks or nodata=0 metadata into reprojection.
    source_values = label.read(1, window=source_window, masked=False)
    if not np.isin(source_values, label_values).all():
        raise ValueError(
            "Source label crop contains unsupported categories; check the recipe label_values (255 is reserved)."
        )
    categories = np.full(shape, 255, dtype=np.uint8)
    reproject(
        source=source_values,
        destination=categories,
        src_transform=transform(source_window, label.transform),
        src_crs=label.crs,
        dst_transform=transform(window, image.transform),
        dst_crs=image.crs,
        src_nodata=None,
        dst_nodata=255,
        resampling=Resampling.nearest,
    )
    # Class 0 is valid water. Only the unused fill value marks missing coverage.
    coverage = categories != 255
    categories[~coverage] = 0
    return categories, coverage


def repair_label_block(
    labels: np.ndarray, original_nodata: np.ndarray, coverage: np.ndarray
) -> np.ndarray:
    """Apply shared image-nodata/outside-footprint exclusion, retaining classes."""
    if labels.shape != original_nodata.shape or labels.shape != coverage.shape:
        raise ValueError(
            "Label, image nodata and footprint windows must share a shape."
        )
    repaired = labels.copy()
    repaired[original_nodata | ~coverage] = 3
    return repaired


def audit_label_block(image_nodata: np.ndarray, labels: np.ndarray) -> dict[str, int]:
    """Count the historical label-repair confusion partition on a target grid."""
    if image_nodata.shape != labels.shape:
        raise ValueError("Image nodata and label windows must share a shape.")
    label_nodata = labels == 3
    return {
        "total": labels.size,
        "image_nodata": int(np.count_nonzero(image_nodata)),
        "tp": int(np.count_nonzero(image_nodata & label_nodata)),
        "fp": int(np.count_nonzero(~image_nodata & label_nodata)),
        "fn": int(np.count_nonzero(image_nodata & ~label_nodata)),
        "tn": int(np.count_nonzero(~image_nodata & ~label_nodata)),
    }
