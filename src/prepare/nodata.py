"""Source-aware nodata handling for the active PlanetScope 8-band workflow."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np


def declared_nodata_values(
    dataset: Any,
    *,
    retained_bands: int,
    missing_value: int | float | None = None,
) -> tuple[int | float, ...]:
    """Return validated per-band nodata values or an explicit missing-data policy."""
    if retained_bands < 1 or dataset.count < retained_bands:
        raise RuntimeError(
            f"Cannot read {retained_bands} retained bands from {dataset.count}-band raster"
        )
    raw_values = tuple(dataset.nodatavals[:retained_bands])
    if len(raw_values) != retained_bands:
        raise RuntimeError("Source raster nodata metadata has the wrong band count")
    missing = [value is None for value in raw_values]
    if any(missing):
        if not all(missing):
            raise RuntimeError("Source raster has partially missing nodata metadata")
        if missing_value is None:
            raise RuntimeError("Source raster has missing nodata metadata")
        raw_values = (missing_value,) * retained_bands
    values: list[int | float] = []
    for band_index, (raw, dtype_name) in enumerate(
        zip(raw_values, dataset.dtypes[:retained_bands], strict=True), start=1
    ):
        value = raw.item() if isinstance(raw, np.generic) else raw
        if isinstance(value, float) and (math.isnan(value) or not math.isfinite(value)):
            raise RuntimeError(f"Band {band_index} has unsupported NaN/inf nodata")
        dtype = np.dtype(dtype_name)
        cast = np.asarray(value, dtype=dtype).item()
        if cast != value:
            raise RuntimeError(
                f"Band {band_index} nodata {value!r} is not exactly representable as {dtype}"
            )
        values.append(cast)
    if len(set(values)) != 1:
        raise RuntimeError(f"Inconsistent per-band nodata declarations: {values}")
    return tuple(values)


def nodata_mask(
    image: np.ndarray,
    nodata_values: Sequence[int | float],
    *,
    band_axis: int,
) -> np.ndarray:
    """Return pixels where every retained band equals its declared nodata value."""
    axis = band_axis % image.ndim
    if image.shape[axis] != len(nodata_values):
        raise ValueError(
            f"Image has {image.shape[axis]} bands on axis {band_axis}, "
            f"but {len(nodata_values)} nodata values were supplied"
        )
    shape = [1] * image.ndim
    shape[axis] = len(nodata_values)
    values = np.asarray(nodata_values, dtype=image.dtype).reshape(shape)
    return np.all(image == values, axis=axis)


def nodata_value_text(nodata_values: Sequence[int | float]) -> str:
    """Return the single validated declaration in a portable form."""
    if not nodata_values or len(set(nodata_values)) != 1:
        raise RuntimeError("A single consistent nodata declaration is required")
    return str(nodata_values[0])
