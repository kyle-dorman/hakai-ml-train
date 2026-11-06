"""Expected preaugmentation kelp exposure under uniform training-window sampling."""

import numpy as np

from kelpseg.reporting.shore_clusters import CLUSTER_SIZE_BINS
from kelpseg.reporting.shore_distance import NEARSHORE_CUTOFF_M
from kelpseg.reporting.shore_inventory_counts import source_window

ZONES = ("nearshore", "offshore", "land", "unknown")
SIZE_FIELDS = ("1_10", "11_100", "101_1000", "1001_5000", "over_5000")
SMALL_CLUSTER_MAX_PIXELS = 100


def exposure_windows(
    canvas: dict,
    windows: list[dict],
    cluster_ids: np.ndarray,
    clusters: list[dict],
    land: np.ndarray,
    distance: np.ndarray,
    positive_only: bool,
) -> list[dict]:
    """Count each eligible training window separately, retaining overlap exposure.

    Full-source component IDs/sizes precede window extraction. Known kelp only
    contributes; loader padding, nodata and ignored labels do not. Mapped-land
    and unknown-distance kelp remain separate from ocean nearshore/offshore.
    Counts describe inputs before augmentation, not post-transform loss weights.
    """
    if canvas["source"]["split"] != "train":
        return []
    sizes = np.zeros(len(clusters) + 1, dtype=np.int64)
    fragments = np.zeros(len(clusters) + 1, dtype=bool)
    for cluster in clusters:
        sizes[cluster["cluster_id"]] = cluster["pixels"]
        fragments[cluster["cluster_id"]] = cluster["truncated"]
    result = []
    source = canvas["source"]
    for window in windows:
        if window["split"] != "train" or (
            positive_only and int(window["kelp_pixels"]) <= 0
        ):
            continue
        cut = source_window(canvas, window)
        known = (
            canvas["valid"][cut]
            & canvas["footprint"][cut]
            & (canvas["labels"][cut] != -100)
        )
        kelp = known & (canvas["labels"][cut] == 1)
        ids = cluster_ids[cut][kelp]
        component_sizes = sizes[ids]
        truncated = fragments[ids]
        lm, dist = land[cut][kelp], distance[cut][kelp]
        ocean = (lm == 0) & np.isfinite(dist) & (dist >= 0)
        zones = {
            "nearshore": ocean & (dist < NEARSHORE_CUTOFF_M),
            "offshore": ocean & (dist >= NEARSHORE_CUTOFF_M),
            "land": lm == 1,
            "unknown": ~(ocean | (lm == 1)),
        }
        row = dict(
            source_id=source["source_id"],
            source_key=window["source_key"],
            region=source["region_id"],
            acquisition_date=source["acquisition_date"],
            payload=window.get("payload", ""),
            original_row=int(window["original_row"]),
            original_col=int(window["original_col"]),
            height=int(window["height"]),
            width=int(window["width"]),
            known_label_pixels=int(known.sum()),
            kelp_pixels=int(kelp.sum()),
            truncated_kelp_pixels=int(truncated.sum()),
        )
        lower = 0
        for (_, upper), size_field in zip(CLUSTER_SIZE_BINS, SIZE_FIELDS, strict=True):
            size_mask = (component_sizes > lower) & (component_sizes <= upper)
            for zone, zone_mask in zones.items():
                selected = size_mask & zone_mask
                row[f"{zone}_{size_field}_pixels"] = int(selected.sum())
                row[f"{zone}_{size_field}_truncated_pixels"] = int(
                    (selected & truncated).sum()
                )
            lower = upper
        result.append(row)
    return result


def exposure_summary(windows: list[dict], regions: list[str]) -> list[dict]:
    """Summarize uniform draws globally and within every declared training region.

    A full shuffled epoch samples each eligible window once, without replacement
    or drop-last. Global draw denominators include all eligible windows; regional
    conditional means use that region's windows. Repeated pixel appearances in
    overlapping windows contribute repeatedly. Empty support has undefined ratios.
    """
    total_windows = len(windows)
    result = []
    groups = [("global", "", windows)] + [
        ("region", region, [row for row in windows if row["region"] == region])
        for region in sorted(set(regions))
    ]
    categories = [("all", SIZE_FIELDS), ("<=100", SIZE_FIELDS[:2])] + [
        (name, (field,))
        for (name, _), field in zip(CLUSTER_SIZE_BINS, SIZE_FIELDS, strict=True)
    ]
    for level, region, selected in groups:
        n = len(selected)
        all_kelp = sum(row["kelp_pixels"] for row in selected)
        for zone in ("all", *ZONES):
            zone_names = ZONES if zone == "all" else (zone,)
            for size_bin, fields in categories:
                counts = [
                    sum(
                        row[f"{name}_{field}_pixels"]
                        for name in zone_names
                        for field in fields
                    )
                    for row in selected
                ]
                pixels = sum(counts)
                present = sum(value > 0 for value in counts)
                truncated = sum(
                    row[f"{name}_{field}_truncated_pixels"]
                    for row in selected
                    for name in zone_names
                    for field in fields
                )
                result.append(
                    dict(
                        level=level,
                        region=region,
                        shore_zone=zone,
                        size_bin=size_bin,
                        eligible_windows=n,
                        all_eligible_windows=total_windows,
                        region_draw_probability=n / total_windows
                        if total_windows
                        else None,
                        pixel_exposures_per_epoch=pixels,
                        expected_pixels_per_draw=pixels / total_windows
                        if total_windows
                        else None,
                        expected_pixels_per_region_draw=pixels / n if n else None,
                        windows_with_kelp=present,
                        probability_draw_has_kelp=present / total_windows
                        if total_windows
                        else None,
                        probability_region_draw_has_kelp=present / n if n else None,
                        fraction_of_all_kelp_exposure=pixels / all_kelp
                        if all_kelp
                        else None,
                        truncated_pixel_exposures=truncated,
                    )
                )
    return result
