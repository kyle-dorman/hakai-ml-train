"""Join source-grid shoreline rasters and assign mutually exclusive distance bands."""

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio import Affine
from rasterio.crs import CRS
from rasterio.windows import Window

NEARSHORE_CUTOFF_M = 120
DEFAULT_DISTANCE_EDGES = (0, 30, 60, 120, 250, 500)


def validate_distance_edges(edges: tuple[float, ...]) -> None:
    """Require finite increasing metre boundaries beginning at zero."""
    if (
        not isinstance(edges, (tuple, list))
        or len(edges) < 2
        or any(
            type(value) not in (int, float) or not np.isfinite(value) for value in edges
        )
        or edges[0] != 0
        or any(right <= left for left, right in zip(edges, edges[1:], strict=False))
    ):
        raise ValueError(
            "distance_edges must be increasing finite metre values starting at 0."
        )


def bin_masks(
    land: np.ndarray,
    distance: np.ndarray,
    edges: tuple[float, ...] = DEFAULT_DISTANCE_EDGES,
) -> dict[str, np.ndarray]:
    """Return disjoint land, half-open ocean bands, far ocean and unknown masks.

    Land has values 0 (ocean), 1 (land), or 255 (unknown). Distance is in metres;
    NaN means unavailable. The final band includes capped offshore distances.
    """
    validate_distance_edges(edges)
    if land.shape != distance.shape:
        raise ValueError("Land and distance arrays must share a pixel grid.")
    if np.any(~np.isin(land, (0, 1, 255))) or np.any(
        np.isfinite(distance) & (distance < 0)
    ):
        raise ValueError("Land values must be 0/1/255 and known distances nonnegative.")
    ocean = (land == 0) & np.isfinite(distance)
    result = {"land": land == 1}
    for lower, upper in zip(edges, edges[1:], strict=False):
        result[f"{lower:g}-{upper:g}"] = (
            ocean & (distance >= lower) & (distance < upper)
        )
    result[f"{edges[-1]:g}+"] = ocean & (distance >= edges[-1])
    result["unknown"] = ~((land == 1) | ocean)
    return result


def pixel_area_m2(crs: CRS, transform: Affine) -> float:
    """Return projected pixel area in square metres, rejecting angular/unitless grids."""
    if crs is None or not crs.is_projected or crs.linear_units != "metre":
        raise ValueError(
            "Shore-distance areas require a projected CRS with metre units."
        )
    area = abs(transform.determinant)
    if not np.isfinite(area) or area <= 0:
        raise ValueError(
            "Shore-distance areas require a nonsingular finite pixel grid."
        )
    return float(area)


def load_shore_sources(root: Path) -> dict[str, dict]:
    """Read a prepared source manifest once and require unique explicit identities."""
    from kelpseg.reporting.inputs import _indexed, read_csv

    rows = read_csv(root / "sources.csv")
    if not rows:
        raise ValueError("Shoreline sources.csv contains no sources.")
    sources = _indexed(rows, "source_key", "Shoreline sources")
    for key, row in sources.items():
        if not all(row.get(name) for name in ("land_mask", "distance", "cap_m")):
            raise ValueError(
                f"{key}: shoreline manifest needs land_mask, distance and cap_m."
            )
        try:
            cap = float(row["cap_m"])
        except ValueError as error:
            raise ValueError(
                f"{key}: cap_m must be a positive finite metre distance."
            ) from error
        if not np.isfinite(cap) or cap <= 0:
            raise ValueError(f"{key}: cap_m must be a positive finite metre distance.")
    return sources


def read_shore_canvas(
    root: Path, sources: dict[str, dict], canvas: dict
) -> tuple[np.ndarray, np.ndarray]:
    """Read and place matching shoreline windows on an existing original-source canvas.

    Join source_keys explicitly, use integer grid translations without resampling,
    and merge declared overlapping crops once. Pixels outside supplied source grids
    remain unknown. Labels supply only array shape, never shoreline geometry.
    """
    shape = canvas["labels"].shape
    land = np.full(shape, 255, dtype=np.uint8)
    distance = np.full(shape, np.nan, dtype=np.float32)
    source = canvas["source"]
    keys = source.get("source_keys", source.get("source_key", "")).split(";")
    for key in keys:
        if key not in sources:
            raise ValueError(f"Missing shoreline source_key: {key}.")
        row = sources[key]
        for name in (
            "dataset_id",
            "release_id",
            "original_source_id",
            "region_id",
            "acquisition_date",
        ):
            if source.get(name) and row.get(name) != source[name]:
                raise ValueError(
                    f"{key}: shoreline {name} differs from source identity."
                )
        with (
            rasterio.open(root / row["land_mask"]) as lm,
            rasterio.open(root / row["distance"]) as dm,
        ):
            if (
                lm.count != 1
                or dm.count != 1
                or lm.dtypes != ("uint8",)
                or dm.dtypes != ("float32",)
                or lm.shape != dm.shape
                or lm.crs != dm.crs
                or lm.transform != dm.transform
                or lm.crs != canvas["crs"]
            ):
                raise ValueError(
                    f"{key}: shoreline rasters must match each other and the source CRS."
                )
            if row.get("transform") and not lm.transform.almost_equals(
                Affine(*json.loads(row["transform"])[:6]), precision=1e-6
            ):
                raise ValueError(
                    f"{key}: shoreline raster differs from its declared source grid."
                )
            if row.get("width") and (lm.width, lm.height) != (
                int(row["width"]),
                int(row["height"]),
            ):
                raise ValueError(
                    f"{key}: shoreline raster differs from its declared source dimensions."
                )
            if all(
                row.get(k) not in (None, "") and source.get(k) not in (None, "")
                for k in ("row_offset", "col_offset")
            ):
                expected = canvas["transform"] * Affine.translation(
                    int(row["col_offset"]) - int(source["col_offset"]),
                    int(row["row_offset"]) - int(source["row_offset"]),
                )
                if not lm.transform.almost_equals(expected, precision=1e-6):
                    raise ValueError(
                        f"{key}: shoreline grid conflicts with declared original offsets."
                    )
            offset = ~canvas["transform"] * lm.transform
            x, y = round(offset.c), round(offset.f)
            if not offset.almost_equals(Affine.translation(x, y), precision=1e-6):
                raise ValueError(
                    f"{key}: shoreline grid is not pixel-aligned with the source."
                )
            top, left = max(y, 0), max(x, 0)
            bottom, right = min(y + lm.height, shape[0]), min(x + lm.width, shape[1])
            if top >= bottom or left >= right:
                raise ValueError(
                    f"{key}: shoreline raster does not overlap its source canvas."
                )
            window = Window(left - x, top - y, right - left, bottom - top)
            part_land, part_distance = (
                lm.read(1, window=window),
                dm.read(1, window=window),
            )
        target = np.s_[top:bottom, left:right]
        known = part_land != 255
        overlap = known & (land[target] != 255)
        if np.any(land[target][overlap] != part_land[overlap]) or not np.allclose(
            distance[target][overlap],
            part_distance[overlap],
            atol=1e-4,
            rtol=0,
            equal_nan=True,
        ):
            raise ValueError(
                f"{key}: overlapping shoreline crops disagree on land/distance."
            )
        land[target][known] = part_land[known]
        distance[target][known] = part_distance[known]
    return land, distance
