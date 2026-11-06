"""Rasterize land and measure capped metric distances on an image's exact grid."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pyogrio
from pyproj import CRS, Transformer
from rasterio import Affine
from rasterio.features import rasterize
from rasterio.warp import transform_bounds
from scipy.ndimage import distance_transform_edt
from shapely import from_wkb, make_valid
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform, unary_union

logger = logging.getLogger(__name__)


def metric_grid(crs: CRS | str, affine: Affine) -> tuple[float, float]:
    """Validate a north-up metre grid and return positive x/y pixel spacing.

    Geographic, rotated and non-metre grids are rejected rather than silently
    treating degrees or feet as metres. Source arrays are never resampled.
    """
    crs = CRS.from_user_input(crs)
    if not crs.is_projected or any(
        axis.unit_conversion_factor != 1 for axis in crs.axis_info[:2]
    ):
        raise ValueError("Shore distance requires a projected CRS with metre units.")
    if (
        not all(math.isfinite(v) for v in affine)
        or affine.b != 0
        or affine.d != 0
        or affine.a <= 0
        or affine.e >= 0
    ):
        raise ValueError("Shore distance requires a north-up grid without rotation.")
    return affine.a, -affine.e


def halo_grid(
    width: int, height: int, affine: Affine, crs: CRS | str, cap_m: float
) -> tuple[tuple[int, int], Affine, tuple[slice, slice]]:
    """Expand a source grid beyond cap_m plus two pixels; return crop slices.

    The halo allows land beyond TIFF edges to determine source-pixel distances.
    Its spacing and pixel alignment are identical to the original source grid.
    """
    dx, dy = metric_grid(crs, affine)
    nx, ny = math.ceil(cap_m / dx) + 2, math.ceil(cap_m / dy) + 2
    shape = height + 2 * ny, width + 2 * nx
    expanded = affine * Affine.translation(-nx, -ny)
    return shape, expanded, (slice(ny, ny + height), slice(nx, nx + width))


def geographic_halo(
    width: int, height: int, affine: Affine, crs: CRS | str, cap_m: float
) -> BaseGeometry:
    """Return a conservative longitude/latitude box around the expanded grid."""
    shape, expanded, _ = halo_grid(width, height, affine, crs, cap_m)
    west, north = expanded * (0, 0)
    east, south = expanded * (shape[1], shape[0])
    bounds = transform_bounds(
        crs, "EPSG:4326", west, south, east, north, densify_pts=41
    )
    if bounds[0] >= bounds[2]:
        raise ValueError(
            "Shore preparation does not support antimeridian-crossing grids."
        )
    return box(*bounds)


def polygon_parts(geometry: BaseGeometry) -> tuple[list[BaseGeometry], int]:
    """Extract polygon leaves, preserving holes; count discarded non-area leaves."""
    polygons, discarded = [], 0
    stack = [geometry]
    while stack:
        item = stack.pop()
        if item.is_empty:
            continue
        if item.geom_type == "Polygon":
            polygons.append(item)
        elif item.geom_type in ("MultiPolygon", "GeometryCollection"):
            stack.extend(item.geoms)
        else:
            discarded += 1
    return polygons, discarded


def read_land(
    paths: Iterable[Path], footprint: BaseGeometry
) -> tuple[BaseGeometry, list[dict]]:
    """Read each global GeoPackage once and clip polygon land to the needed area.

    Inputs must declare EPSG:4326. Bbox filtering limits reads; exact clipping to
    the union of source halos happens before per-source projection. Linework in
    geometry collections is counted and discarded, not treated as filled land.
    Return a polygon union and ordinary source/repair counts for provenance.
    """
    selected, metadata = [], []
    for path in paths:
        logger.info("Reading shoreline %s", path)
        layers = pyogrio.list_layers(path)
        if len(layers) != 1:
            raise ValueError(f"{path}: expected one shoreline layer.")
        layer = str(layers[0, 0])
        info = pyogrio.read_info(path, layer=layer)
        if CRS.from_user_input(info["crs"]) != CRS.from_epsg(4326):
            raise ValueError(f"{path}: shoreline layer must use EPSG:4326.")
        _, _, geometries, _ = pyogrio.raw.read(
            path, layer=layer, bbox=footprint.bounds, columns=[], return_fids=False
        )
        discarded, repaired, kept = 0, 0, 0
        for blob in geometries:
            if blob is None:
                raise ValueError(f"{path}: shoreline feature has no geometry.")
            geometry = from_wkb(blob)
            if not geometry.is_valid:
                geometry = make_valid(geometry)
                repaired += 1
            parts, count = polygon_parts(geometry)
            discarded += count
            for part in parts:
                if part.intersects(footprint):
                    clipped, count = polygon_parts(part.intersection(footprint))
                    selected.extend(clipped)
                    kept += len(clipped)
                    discarded += count
        record = dict(
            path=str(path),
            layer=layer,
            crs="EPSG:4326",
            selected_features=len(geometries),
            polygon_parts=kept,
            repaired_features=repaired,
            discarded_non_area_parts=discarded,
        )
        metadata.append(record)
        logger.info(
            "Shoreline %s: %d features, %d polygon parts, %d repairs, %d non-area parts discarded",
            layer,
            len(geometries),
            kept,
            repaired,
            discarded,
        )
    return unary_union(selected), metadata


def land_distance(
    land: BaseGeometry,
    width: int,
    height: int,
    affine: Affine,
    crs: CRS | str,
    cap_m: float = 500.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return source-grid uint8 land and float32 capped distance in metres.

    Rasterize by pixel center, then measure center-to-center Euclidean distance
    to the nearest land pixel in a halo. This approximates vector shore distance
    at native pixel resolution; it is not subpixel coastline accuracy. Land is
    zero distance, and cap_m means at least cap_m. Complete global shoreline
    coverage is assumed; an empty selection is valid offshore ocean.
    """
    dx, dy = metric_grid(crs, affine)
    shape, expanded, crop = halo_grid(width, height, affine, crs, cap_m)
    footprint = geographic_halo(width, height, affine, crs, cap_m)
    local = land.intersection(footprint)
    project = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
    parts, _ = polygon_parts(transform(project, local))
    mask = np.zeros(shape, dtype=np.uint8)
    if parts:
        rasterize(
            parts,
            out=mask,
            transform=expanded,
            default_value=1,
            all_touched=False,
        )
    if mask.any():
        distance = distance_transform_edt(mask == 0, sampling=(dy, dx))[crop]
        np.minimum(distance, cap_m, out=distance)
        distance = distance.astype(np.float32)
    else:
        distance = np.full((height, width), cap_m, dtype=np.float32)
    return mask[crop].copy(), distance
