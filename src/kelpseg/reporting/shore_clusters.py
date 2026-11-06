"""Full-source label components and pixel-level distance/size observations."""

from pathlib import Path

import cv2
import numpy as np
import rasterio

from kelpseg.reporting.metrics import erode
from kelpseg.reporting.shore_distance import bin_masks

CLUSTER_SIZE_BINS = (
    ("1-10", 10),
    ("11-100", 100),
    ("101-1000", 1000),
    ("1001-5000", 5000),
    (">5000", float("inf")),
)

MOMENT_KEYS = ("n", "sum_x", "sum_y", "sum_xx", "sum_yy", "sum_xy")
UNKNOWN_CLUSTER = np.iinfo(np.uint32).max


def moments(distance: np.ndarray, log_area: np.ndarray) -> dict:
    """Return additive Pearson sufficient statistics for equally weighted pairs."""
    x, y = distance.astype(np.float64), log_area.astype(np.float64)
    return dict(
        n=int(x.size),
        sum_x=float(x.sum()),
        sum_y=float(y.sum()),
        sum_xx=float(np.dot(x, x)),
        sum_yy=float(np.dot(y, y)),
        sum_xy=float(np.dot(x, y)),
    )


def pearson(values: dict) -> float | None:
    """Calculate correlation from pooled moments; constants/empty groups are undefined."""
    n = values["n"]
    if n < 2:
        return None
    vx = values["sum_xx"] - values["sum_x"] ** 2 / n
    vy = values["sum_yy"] - values["sum_y"] ** 2 / n
    # Floating cancellation can leave tiny positive variance for constant arrays.
    if vx <= 1e-12 * max(values["sum_xx"], 1) or vy <= 1e-12 * max(values["sum_yy"], 1):
        return None
    covariance = values["sum_xy"] - values["sum_x"] * values["sum_y"] / n
    return float(np.clip(covariance / np.sqrt(vx * vy), -1, 1))


def cluster_source(
    canvas: dict,
    land: np.ndarray,
    distance: np.ndarray,
    area_m2: float,
    cap_m: float,
    edges: tuple[float, ...],
) -> tuple[np.ndarray, list[dict], list[dict], list[dict]]:
    """Assign eight-connected full-source kelp IDs and summarize size versus distance.

    Components include mapped-land kelp and retain their full observed size when
    selecting ocean pixels. IDs are local to this original source; zero denotes
    known background and uint32 max denotes unavailable/ignored labels. Components
    touching unknown support or image edges are flagged as observed fragments.
    Correlations use only uncapped ocean distances, with no significance tests.
    """
    known = canvas["valid"] & canvas["footprint"] & (canvas["labels"] != -100)
    kelp = known & (canvas["labels"] == 1)
    count, ids, stats, _ = cv2.connectedComponentsWithStats(
        kelp.astype(np.uint8), connectivity=8
    )
    sizes = stats[:, cv2.CC_STAT_AREA].astype(np.int64)
    sizes[0] = 0
    truncated = np.bincount(ids[~erode(known, 1)], minlength=count) > 0
    eligible = (
        kelp
        & (land == 0)
        & np.isfinite(distance)
        & (distance >= 0)
        & (distance < cap_m)
    )
    eligible_ids = ids[eligible]
    ocean_counts = np.bincount(eligible_ids, minlength=count)
    ocean_sums = np.bincount(eligible_ids, weights=distance[eligible], minlength=count)
    mean_distances = np.full(count, np.nan)
    np.divide(ocean_sums, ocean_counts, out=mean_distances, where=ocean_counts > 0)
    size_names = np.full(count, "", dtype=object)
    for name, maximum in reversed(CLUSTER_SIZE_BINS):
        size_names[sizes <= maximum] = name
    rows = []
    source = canvas["source"]
    for index in range(1, count):
        left, top, width, height, pixels = (int(value) for value in stats[index])
        rows.append(
            dict(
                cluster_id=index,
                pixels=pixels,
                area_m2=pixels * area_m2,
                size_bin=size_names[index],
                truncated=bool(truncated[index]),
                original_row=top + int(source.get("row_offset", 0)),
                original_col=left + int(source.get("col_offset", 0)),
                height=height,
                width=width,
                uncapped_ocean_pixels=int(ocean_counts[index]),
                mean_uncapped_ocean_distance_m=float(mean_distances[index])
                if ocean_counts[index]
                else None,
            )
        )
    band_rows = []
    correlation_rows = []
    for component_scope in ("all_observed", "interior_only"):
        accepted = kelp if component_scope == "all_observed" else kelp & ~truncated[ids]
        for band, mask in bin_masks(land, distance, edges).items():
            members = ids[mask & accepted]
            for size, _ in CLUSTER_SIZE_BINS:
                selected = members[size_names[members] == size]
                band_rows.append(
                    dict(
                        component_scope=component_scope,
                        distance_band=band,
                        size_bin=size,
                        kelp_pixels=int(selected.size),
                        clusters_present=int(np.unique(selected).size),
                    )
                )
        selected_ocean = eligible & accepted
        selected_ids = ids[selected_ocean]
        for weighting in ("pixel", "cluster"):
            if weighting == "pixel":
                x = distance[selected_ocean]
                y = np.log10(sizes[selected_ids] * area_m2)
            else:
                supported = (ocean_counts > 0) & (np.arange(count) > 0)
                if component_scope == "interior_only":
                    supported &= ~truncated
                x = mean_distances[supported]
                y = np.log10(sizes[supported] * area_m2)
            correlation_rows.append(
                dict(
                    component_scope=component_scope,
                    weighting=weighting,
                    cap_m=cap_m,
                    **moments(x, y),
                )
            )
    raster = ids.astype(np.uint32)
    raster[~known] = UNKNOWN_CLUSTER
    return raster, rows, band_rows, correlation_rows


def write_cluster_ids(path: Path, ids: np.ndarray, canvas: dict) -> None:
    """Write source-aligned component IDs with explicit unknown-label nodata."""
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=ids.shape[1],
        height=ids.shape[0],
        count=1,
        dtype="uint32",
        crs=canvas["crs"],
        transform=canvas["transform"],
        nodata=int(UNKNOWN_CLUSTER),
        compress="deflate",
        tiled=True,
    ) as dataset:
        dataset.write(ids, 1)
