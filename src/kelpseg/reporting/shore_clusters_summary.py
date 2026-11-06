"""Pool distance/cluster summaries without retaining full collection pixel arrays."""

from collections import defaultdict
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure

from kelpseg.reporting.shore_clusters import CLUSTER_SIZE_BINS, MOMENT_KEYS, pearson


def pool_cluster_bands(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    """Sum source counts by distance/size; grouping keys end with size_bin."""
    groups = {}
    totals = defaultdict(int)
    for row in rows:
        key = tuple(row[name] for name in keys)
        if key not in groups:
            groups[key] = dict(
                zip(keys, key, strict=True), kelp_pixels=0, clusters_present=0
            )
        groups[key]["kelp_pixels"] += row["kelp_pixels"]
        groups[key]["clusters_present"] += row["clusters_present"]
        totals[key[:-1]] += row["kelp_pixels"]
    for key, counts in groups.items():
        denominator = totals[key[:-1]]
        counts["fraction_of_band_kelp"] = (
            counts["kelp_pixels"] / denominator if denominator else None
        )
    return list(groups.values())


def pool_correlations(
    rows: list[dict], keys: tuple[str, ...], level: str
) -> list[dict]:
    """Pool sufficient statistics before calculating Pearson r at one grouping level."""
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    result = []
    for key, members in groups.items():
        # Keep Python's compensated float summation for the correlation moments.
        values = {name: sum(row[name] for row in members) for name in MOMENT_KEYS}
        result.append(
            {
                "level": level,
                "region": "",
                "split": "",
                "source_id": "",
                **dict(zip(keys, key, strict=True)),
                **values,
                "pearson_distance_log10_area": pearson(values),
                "contributing_sources": sum(row["n"] > 0 for row in members),
            }
        )
    return result


def cluster_plot(path: Path, rows: list[dict]) -> None:
    """Plot pixel-weighted component-size composition by distance separately per split."""
    rows = [row for row in rows if row["component_scope"] == "interior_only"]
    splits = [
        split
        for split in ("train", "val", "test", "unused")
        if any(row["split"] == split for row in rows)
    ]
    bands = list(
        dict.fromkeys(
            row["distance_band"]
            for row in rows
            if row["distance_band"] not in ("land", "unknown")
        )
    )
    fig = Figure(figsize=(max(6, 5 * len(splits)), 5), layout="constrained")
    axes = np.atleast_1d(fig.subplots(1, len(splits)))
    colors = ("#996600", "#d95f02", "#1b9e77", "#7570b3", "#0072b2")
    for ax, split in zip(axes, splits, strict=True):
        supported = np.zeros(len(bands), dtype=bool)
        for (size, _), color in zip(CLUSTER_SIZE_BINS, colors, strict=True):
            lookup = {
                row["distance_band"]: row
                for row in rows
                if row["split"] == split and row["size_bin"] == size
            }
            values = np.array(
                [
                    np.nan
                    if lookup[band]["fraction_of_band_kelp"] is None
                    else 100 * lookup[band]["fraction_of_band_kelp"]
                    for band in bands
                ]
            )
            ax.plot(
                np.arange(len(bands)),
                values,
                marker="o",
                linewidth=2,
                label=f"{size} pixels",
                color=color,
            )
            supported |= np.isfinite(values)
        for index, present in enumerate(supported):
            if not present:
                ax.text(
                    index, 50, "N/A", ha="center", va="center", fontsize=8, color="gray"
                )
        ax.set(
            title=split,
            ylabel="Share of labeled kelp pixels (%)",
            ylim=(0, 100),
            xlabel="Ocean distance band (m); 500+ is capped",
        )
        ax.set_xticks(np.arange(len(bands)), bands)
        ax.set_xlim(-0.3, max(len(bands) - 0.7, 0.3))
        ax.grid(axis="y", alpha=0.25)
        ax.tick_params(axis="x", rotation=40)
        ax.legend(title="Full-source cluster size", fontsize=8)
    fig.suptitle(
        "Cluster-size distribution within each shore-distance band · boundary fragments excluded"
    )
    fig.savefig(path, dpi=140)
