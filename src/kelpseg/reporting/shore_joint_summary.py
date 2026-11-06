"""Pool saved-cluster recall strata with source/date support and paired evidence."""

from collections import defaultdict
from statistics import median
from typing import Any

Row = dict[str, Any]
NEAR_BANDS = {"0-30", "30-60", "60-120"}
OFFSHORE_BANDS = {"120-250", "250-500", "500+"}


def _ratio(numerator: int, denominator: int) -> float | None:
    """Divide counts, preserving undefined recall for absent positive support."""
    return numerator / denominator if denominator else None


def _gap(near: float | None, offshore: float | None) -> float | None:
    """Return nearshore minus offshore recall only when both are defined."""
    return near - offshore if near is not None and offshore is not None else None


def _totals(rows: list[Row]) -> Row:
    """Pool positive counts and area, then measure distinct source/date support."""
    tp, fn = sum(row["tp"] for row in rows), sum(row["fn"] for row in rows)
    source_pixels: dict[str, int] = defaultdict(int)
    date_pixels: dict[str, int] = defaultdict(int)
    for row in rows:
        pixels = row["labeled_kelp_pixels"]
        if pixels:
            source_pixels[row["source_id"]] += pixels
            date_pixels[row["acquisition_date"]] += pixels
    largest_source = max(source_pixels, key=source_pixels.get) if source_pixels else ""
    largest_date = max(date_pixels, key=date_pixels.get) if date_pixels else ""
    pixels = tp + fn
    return dict(
        labeled_kelp_pixels=pixels,
        labeled_kelp_area_m2=sum(row["labeled_kelp_area_m2"] for row in rows),
        tp=tp,
        fn=fn,
        recall=_ratio(tp, pixels),
        source_count=len(source_pixels),
        date_count=len(date_pixels),
        dominant_source_id=largest_source,
        max_source_kelp_share=_ratio(source_pixels.get(largest_source, 0), pixels),
        dominant_date=largest_date,
        max_date_kelp_share=_ratio(date_pixels.get(largest_date, 0), pixels),
        sparse_pixels=pixels < 100,
        few_dates=len(date_pixels) < 3,
    )


def _group_rows(rows: list[Row], keys: tuple[str, ...]) -> dict[tuple, list[Row]]:
    """Group observations by explicit identity fields, preserving input order."""
    groups: dict[tuple, list[Row]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    return groups


def pool_joint_rows(rows: list[Row], keys: tuple[str, ...]) -> list[Row]:
    """Pool original source observations by keys without averaging recall ratios."""
    return [
        dict(zip(keys, key, strict=True), **_totals(members))
        for key, members in _group_rows(rows, keys).items()
    ]


def _zone(band: str) -> str:
    """Map the existing distance bands to the fixed 120 m comparison zones."""
    if band in NEAR_BANDS:
        return "nearshore"
    if band in OFFSHORE_BANDS:
        return "offshore"
    if band in {"land", "unknown"}:
        return band
    raise ValueError(
        f"Joint nearshore comparison does not recognize distance band {band!r}."
    )


def _comparisons(rows: list[Row], keys: tuple[str, ...]) -> list[Row]:
    """Create one near/off pair per group, retaining zero-support comparisons."""
    groups: dict[tuple, dict[str, Row]] = defaultdict(dict)
    for row in rows:
        if row["shore_zone"] in {"nearshore", "offshore"}:
            groups[tuple(row[key] for key in keys)][row["shore_zone"]] = row
    output = []
    fields = (
        "labeled_kelp_pixels",
        "labeled_kelp_area_m2",
        "tp",
        "fn",
        "recall",
        "source_count",
        "date_count",
        "dominant_source_id",
        "max_source_kelp_share",
        "dominant_date",
        "max_date_kelp_share",
    )
    empty = _totals([])
    for key, zones in groups.items():
        near = zones.get("nearshore", empty)
        offshore = zones.get("offshore", empty)
        row = dict(zip(keys, key, strict=True))
        flags = []
        for prefix, values in (("nearshore", near), ("offshore", offshore)):
            row.update({f"{prefix}_{field}": values[field] for field in fields})
            if not values["labeled_kelp_pixels"]:
                flags.append(f"{prefix}:no_support")
            elif values["labeled_kelp_pixels"] < 100:
                flags.append(f"{prefix}:<100_pixels")
            if values["date_count"] < 3:
                flags.append(f"{prefix}:<3_dates")
            if (values["max_source_kelp_share"] or 0) > 0.5:
                flags.append(f"{prefix}:one_source>50%")
            if (values["max_date_kelp_share"] or 0) > 0.5:
                flags.append(f"{prefix}:one_date>50%")
        row.update(
            recall_gap=_gap(near["recall"], offshore["recall"]),
            paired_support=near["labeled_kelp_pixels"] > 0
            and offshore["labeled_kelp_pixels"] > 0,
            support_flags=";".join(flags),
        )
        output.append(row)
    return output


def _paired_evidence(pairs: list[Row], prefix: str) -> Row:
    """Summarize matched-source/date comparisons without pixel-independence claims."""
    paired = [row for row in pairs if row["paired_support"]]
    near_tp = sum(row["nearshore_tp"] for row in paired)
    near_n = sum(row["nearshore_labeled_kelp_pixels"] for row in paired)
    off_tp = sum(row["offshore_tp"] for row in paired)
    off_n = sum(row["offshore_labeled_kelp_pixels"] for row in paired)
    gaps = [row["recall_gap"] for row in paired]
    near_recall, off_recall = _ratio(near_tp, near_n), _ratio(off_tp, off_n)
    return {
        f"paired_{prefix}_count": len(paired),
        f"paired_{prefix}_nearshore_lower_count": sum(gap < 0 for gap in gaps),
        f"paired_{prefix}_nearshore_higher_count": sum(gap > 0 for gap in gaps),
        f"paired_{prefix}_equal_count": sum(gap == 0 for gap in gaps),
        f"paired_{prefix}_median_gap": median(gaps) if gaps else None,
        f"paired_{prefix}_nearshore_pixels": near_n,
        f"paired_{prefix}_offshore_pixels": off_n,
        f"paired_{prefix}_nearshore_recall": near_recall,
        f"paired_{prefix}_offshore_recall": off_recall,
        f"paired_{prefix}_pooled_gap": _gap(near_recall, off_recall),
    }


def _leave_largest_out(rows: list[Row], key: str, label: str) -> Row:
    """Measure the gap after removing the source/date with most ocean kelp support."""
    ocean = [row for row in rows if row["shore_zone"] in {"nearshore", "offshore"}]
    support: dict[str, int] = defaultdict(int)
    for row in ocean:
        support[row[key]] += row["labeled_kelp_pixels"]
    total = sum(support.values())
    largest = max(support, key=support.get) if total else ""
    kept = [row for row in ocean if row[key] != largest]
    near = _totals([row for row in kept if row["shore_zone"] == "nearshore"])
    offshore = _totals([row for row in kept if row["shore_zone"] == "offshore"])
    return {
        f"largest_ocean_{label}": largest,
        f"largest_ocean_{label}_share": _ratio(support.get(largest, 0), total),
        f"without_largest_{label}_nearshore_pixels": near["labeled_kelp_pixels"],
        f"without_largest_{label}_offshore_pixels": offshore["labeled_kelp_pixels"],
        f"without_largest_{label}_gap": _gap(near["recall"], offshore["recall"]),
    }


def build_joint_tables(source_rows: list[Row]) -> dict[str, list[Row]]:
    """Build distance and near/off recall tables with source/date robustness evidence.

    Input rows describe original source pixels in disjoint distance/size strata,
    separately for all, interior and truncated components. Never pool across those
    component scopes. Source/date support is recomputed after merging distance bins.
    """
    region_keys = ("region", "component_scope", "size_bin")
    joint_regions = pool_joint_rows(source_rows, (*region_keys, "distance_band"))
    zones = [dict(row, shore_zone=_zone(row["distance_band"])) for row in source_rows]
    source_keys = (
        "region",
        "source_id",
        "acquisition_date",
        "component_scope",
        "size_bin",
    )
    source_zones = pool_joint_rows(zones, (*source_keys, "shore_zone"))
    region_zones = pool_joint_rows(zones, (*region_keys, "shore_zone"))
    dates = pool_joint_rows(
        zones,
        ("region", "acquisition_date", "component_scope", "size_bin", "shore_zone"),
    )
    source_pairs = _comparisons(source_zones, source_keys)
    date_pairs = _comparisons(
        dates, ("region", "acquisition_date", "component_scope", "size_bin")
    )
    comparisons = _comparisons(region_zones, region_keys)
    sources_by_region = _group_rows(source_pairs, region_keys)
    dates_by_region = _group_rows(date_pairs, region_keys)
    zones_by_region = _group_rows(source_zones, region_keys)
    for row in comparisons:
        group = tuple(row[key] for key in region_keys)
        row.update(_paired_evidence(sources_by_region[group], "source"))
        row.update(_paired_evidence(dates_by_region[group], "date"))
        members = zones_by_region[group]
        row.update(_leave_largest_out(members, "source_id", "source"))
        row.update(_leave_largest_out(members, "acquisition_date", "date"))
    return dict(
        joint_regions=joint_regions,
        joint_nearshore_sources=source_zones,
        joint_nearshore_regions=region_zones,
        joint_dates=dates,
        joint_source_comparisons=source_pairs,
        joint_date_comparisons=date_pairs,
        joint_nearshore_comparisons=comparisons,
    )
