"""Account for joint-label strata against the unchanged shoreline scored footprint."""

from collections import defaultdict
from typing import Any


def reconcile_joint(
    joint: list[dict[str, Any]],
    shoreline: list[dict[str, Any]],
    global_counts: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reconcile TP/FN by region/distance and return exclusion accounting.

    All observed components partition scored positive labels. Interior-only
    removes full-source truncated components; ocean comparisons additionally
    remove mapped-land/unknown distance. No false positives receive a size class.
    """
    expected: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: dict(tp=0, fn=0, available=0)
    )
    actual: dict[tuple[str, str, str], dict[str, int]] = defaultdict(
        lambda: dict(tp=0, fn=0)
    )
    for row in shoreline:
        counts = expected[row["region"], row["distance_band"]]
        for name in ("tp", "fn"):
            counts[name] += row[name]
        counts["available"] += row["available_labeled_kelp_pixels"]
    for row in joint:
        counts = actual[row["region"], row["distance_band"], row["component_scope"]]
        for name in ("tp", "fn"):
            counts[name] += row[name]
    if {(region, band) for region, band, _ in actual} != set(expected):
        raise ValueError(
            "Joint region/distance identities differ from shoreline counts."
        )
    records: list[dict[str, Any]] = []
    for (region, band), counts in expected.items():
        all_counts = actual[region, band, "all_observed"]
        interior = actual[region, band, "interior_only"]
        truncated = actual[region, band, "truncated_only"]
        for name in ("tp", "fn"):
            if all_counts[name] != counts[name]:
                raise ValueError(
                    f"Joint {name} differs from shoreline in {region}/{band}."
                )
            if interior[name] + truncated[name] != all_counts[name]:
                raise ValueError(
                    f"Joint component scopes do not reconcile in {region}/{band}."
                )
        records.append(
            dict(
                region=region,
                distance_band=band,
                ocean_comparison=band not in ("land", "unknown"),
                available_labeled_kelp_pixels=counts["available"],
                excluded_uncovered_kelp_pixels=counts["available"]
                - counts["tp"]
                - counts["fn"],
                shoreline_tp=counts["tp"],
                shoreline_fn=counts["fn"],
                all_tp=all_counts["tp"],
                all_fn=all_counts["fn"],
                interior_tp=interior["tp"],
                interior_fn=interior["fn"],
                truncated_tp=truncated["tp"],
                truncated_fn=truncated["fn"],
            )
        )
    for name in ("tp", "fn"):
        if sum(row[f"all_{name}"] for row in records) != global_counts[name]:
            raise ValueError(f"Joint {name} differs from global scored counts.")
    summary: dict[str, Any] = dict(
        exact_shoreline_and_global_tp_fn_parity=True,
        unassigned_scored_kelp_pixels=0,
        available_labeled_kelp_pixels=sum(
            r["available_labeled_kelp_pixels"] for r in records
        ),
        excluded_uncovered_kelp_pixels=sum(
            r["excluded_uncovered_kelp_pixels"] for r in records
        ),
    )
    for prefix in ("all", "interior", "truncated"):
        summary[prefix] = {
            name: sum(r[f"{prefix}_{name}"] for r in records) for name in ("tp", "fn")
        }
        summary[f"{prefix}_land_unknown"] = {
            name: sum(
                r[f"{prefix}_{name}"] for r in records if not r["ocean_comparison"]
            )
            for name in ("tp", "fn")
        }
    return records, summary
