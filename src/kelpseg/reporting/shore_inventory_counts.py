"""Pixel unions, distance-band counts and descriptive support summaries."""

import numpy as np

from kelpseg.reporting.shore_distance import NEARSHORE_CUTOFF_M, bin_masks

SUM_FIELDS = (
    "labeled_pixels",
    "kelp_pixels",
    "labeled_area_m2",
    "kelp_area_m2",
    "all_labeled_pixels",
    "all_kelp_pixels",
    "all_kelp_area_m2",
)


def source_window(canvas: dict, window: dict) -> tuple[slice, slice]:
    """Locate one original-coordinate chip on its source canvas, rejecting overflow."""
    source = canvas["source"]
    y = int(window["original_row"]) - int(source["row_offset"])
    x = int(window["original_col"]) - int(source["col_offset"])
    height, width = int(window["height"]), int(window["width"])
    if (
        min(y, x) < 0
        or y + height > canvas["labels"].shape[0]
        or x + width > canvas["labels"].shape[1]
    ):
        raise ValueError(
            "Selected chip window lies outside its original-source canvas."
        )
    return slice(y, y + height), slice(x, x + width)


def inventory_footprints(
    canvas: dict, windows: list[dict], positive_only: bool
) -> dict[str, np.ndarray]:
    """Return full, selected-window and training-eligible unions without padding.

    Window positions use original coordinates. The eligible scope only exists
    for training sources; overlap is represented by Boolean union, not exposure
    frequency. Nodata and ignored labels are removed later during counting.
    """
    source = canvas["source"]
    masks = {
        "full_source": canvas["footprint"],
        "selected_chips": np.zeros(canvas["labels"].shape, dtype=bool),
    }
    if source["split"] == "train":
        masks["training_eligible"] = np.zeros(canvas["labels"].shape, dtype=bool)
    for window in windows:
        if window["split"] != source["split"] or window["split"] == "unused":
            continue
        region = source_window(canvas, window)
        masks["selected_chips"][region] = True
        if source["split"] == "train" and (
            not positive_only or int(window["kelp_pixels"]) > 0
        ):
            masks["training_eligible"][region] = True
    return masks


def band_counts(
    labels: np.ndarray,
    footprint: np.ndarray,
    land: np.ndarray,
    distance: np.ndarray,
    edges: tuple[float, ...],
    area: float,
) -> list[dict]:
    """Count each distance band and its full-footprint denominators on valid labels."""
    known = footprint & (labels != -100)
    kelp = known & (labels == 1)
    totals = dict(
        all_labeled_pixels=int(known.sum()),
        all_kelp_pixels=int(kelp.sum()),
        all_kelp_area_m2=float(kelp.sum()) * area,
    )
    result = []
    for band, mask in bin_masks(land, distance, edges).items():
        n, k = int((known & mask).sum()), int((kelp & mask).sum())
        result.append(
            dict(
                band=band,
                labeled_pixels=n,
                kelp_pixels=k,
                labeled_area_m2=n * area,
                kelp_area_m2=k * area,
                **totals,
            )
        )
    return result


def add_fractions(row: dict) -> dict:
    """Attach defined ratios and hectare equivalents to one count row."""

    def ratio(a: float, b: float) -> float | None:
        """Return a fraction, leaving empty denominators undefined."""
        return a / b if b else None

    return dict(
        row,
        kelp_prevalence=ratio(row["kelp_pixels"], row["labeled_pixels"]),
        kelp_fraction=ratio(row["kelp_pixels"], row["all_kelp_pixels"]),
        kelp_area_fraction=ratio(row["kelp_area_m2"], row["all_kelp_area_m2"]),
        labeled_area_ha=row["labeled_area_m2"] / 10000,
        kelp_area_ha=row["kelp_area_m2"] / 10000,
    )


def pool_inventory(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    """Pool counts before ratios, retaining distinct source/date support per band."""
    groups = {}
    for row in rows:
        key = tuple(row[name] for name in keys)
        if key not in groups:
            groups[key] = (
                dict(zip(keys, key, strict=True), **dict.fromkeys(SUM_FIELDS, 0)),
                set(),
                set(),
                set(),
            )
        counts, sources, dates, kelp_sources = groups[key]
        for name in SUM_FIELDS:
            counts[name] += row[name]
        if row["labeled_pixels"]:
            sources.add((row["dataset_id"], row["release_id"], row["source_id"]))
            dates.add(row["acquisition_date"])
        if row["kelp_pixels"]:
            kelp_sources.add((row["dataset_id"], row["release_id"], row["source_id"]))
    return [
        add_fractions(
            dict(
                counts,
                sources=len(sources),
                dates=len(dates),
                kelp_sources=len(kelp_sources),
            )
        )
        for counts, sources, dates, kelp_sources in groups.values()
    ]


def empty_region_groups(
    rows: list[dict], sources: list[dict], dimension: str, values: list
) -> list[dict]:
    """Include absent region/split combinations as zero support and undefined ratios."""
    result = list(rows)
    seen = {(row["region"], row["split"], row["scope"], row[dimension]) for row in rows}
    context = {name: rows[0][name] for name in ("experiment", "variant")}
    for region in sorted({source["region_id"] for source in sources}):
        for split in ("train", "val", "test"):
            scopes = (
                ("full_source", "selected_chips", "training_eligible")
                if split == "train"
                else ("full_source", "selected_chips")
            )
            for scope in scopes:
                for value in values:
                    if (region, split, scope, value) not in seen:
                        result.append(
                            add_fractions(
                                dict(
                                    context,
                                    region=region,
                                    split=split,
                                    scope=scope,
                                    **{dimension: value},
                                    **dict.fromkeys(SUM_FIELDS, 0),
                                    sources=0,
                                    dates=0,
                                    kelp_sources=0,
                                )
                            )
                        )
    return result


def cumulative_counts(
    labels: np.ndarray,
    footprint: np.ndarray,
    land: np.ndarray,
    distance: np.ndarray,
    cutoffs: tuple[float, ...],
    area: float,
) -> list[dict]:
    """Count ocean kelp below each cutoff, keeping all labeled kelp as denominator."""
    known = footprint & (labels != -100)
    kelp = known & (labels == 1)
    rows = []
    for cutoff in sorted(set((*cutoffs, NEARSHORE_CUTOFF_M))):
        mask = (
            (land == 0) & np.isfinite(distance) & (distance >= 0) & (distance < cutoff)
        )
        n, k = int((known & mask).sum()), int((kelp & mask).sum())
        rows.append(
            dict(
                cutoff_m=cutoff,
                labeled_pixels=n,
                kelp_pixels=k,
                labeled_area_m2=n * area,
                kelp_area_m2=k * area,
                all_labeled_pixels=int(known.sum()),
                all_kelp_pixels=int(kelp.sum()),
                all_kelp_area_m2=float(kelp.sum()) * area,
            )
        )
    return rows
