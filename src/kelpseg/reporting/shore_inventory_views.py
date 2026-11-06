"""Small static figures and a researcher-facing label inventory report."""

from html import escape
from pathlib import Path

import numpy as np
from matplotlib import colormaps
from matplotlib.figure import Figure

from kelpseg.reporting.shore_distance import NEARSHORE_CUTOFF_M
from kelpseg.reporting.shore_exposure_views import exposure_html


def write_inventory_views(
    output: Path,
    regions: list[dict],
    splits: list[dict],
    cumulative_regions: list[dict],
    cumulative_splits: list[dict],
) -> None:
    """Write normalized support, nearshore heatmap and linked cluster diagnostics."""
    scopes = ["full_source", "selected_chips", "training_eligible"]
    colors = {
        "train": "#2471a3",
        "val": "#d35400",
        "test": "#229954",
        "unused": "#888888",
    }
    bands = list(dict.fromkeys(row["band"] for row in splits))
    figure = Figure(figsize=(15, 4), layout="constrained")
    axes = figure.subplots(1, 3)
    for column, scope in enumerate(scopes):
        for split in colors:
            selected = [
                row for row in splits if row["scope"] == scope and row["split"] == split
            ]
            if not selected:
                continue
            lookup = {row["band"]: row for row in selected}
            fractions = [lookup[band]["kelp_fraction"] for band in bands]
            axes[column].plot(
                bands,
                [np.nan if x is None else 100 * x for x in fractions],
                marker="o",
                color=colors[split],
                label=split,
            )
        axes[column].set_title(scope.replace("_", " "))
        axes[column].tick_params(axis="x", rotation=45)
        axes[column].grid(alpha=0.2)
        axes[column].legend()
        axes[column].set_ylabel("Share of labeled kelp (%)")
    figure.savefig(output / "distance_distributions.png", dpi=140)

    region_names = sorted({row["region"] for row in regions})
    split_names = ["train", "val", "test"]
    heatmap = np.full((len(region_names), len(split_names)), np.nan)
    near = [
        row
        for row in cumulative_regions
        if row["scope"] == "full_source" and row["cutoff_m"] == NEARSHORE_CUTOFF_M
    ]
    for row in near:
        if row["split"] in split_names and row["kelp_fraction"] is not None:
            heatmap[
                region_names.index(row["region"]), split_names.index(row["split"])
            ] = 100 * row["kelp_fraction"]
    figure = Figure(figsize=(7, max(3, len(region_names) * 0.4)), layout="constrained")
    axis = figure.subplots()
    cmap = colormaps["viridis"].copy()
    cmap.set_bad("#dddddd")
    image = axis.imshow(
        np.ma.masked_invalid(heatmap), cmap=cmap, vmin=0, vmax=100, aspect="auto"
    )
    axis.set_xticks(range(len(split_names)), split_names)
    axis.set_yticks(range(len(region_names)), region_names)
    axis.set_title(f"Full-source labeled kelp below {NEARSHORE_CUTOFF_M} m from land")
    for y in range(len(region_names)):
        for x in range(len(split_names)):
            value = heatmap[y, x]
            axis.text(
                x,
                y,
                "N/A" if np.isnan(value) else f"{value:.1f}%",
                ha="center",
                va="center",
                color="black" if np.isnan(value) or value > 60 else "white",
            )
    figure.colorbar(image, ax=axis, label="Share of all labeled kelp (%)")
    figure.savefig(output / "nearshore_regions.png", dpi=140)

    lines = [
        "<!doctype html><html><head><meta charset='utf-8'><title>Shore-distance label inventory</title>",
        "<style>body{font:16px system-ui;max-width:1100px;margin:3rem auto;padding:0 1.5rem;color:#202830}h1{font-size:1.8rem}h2{font-size:1.3rem;margin-top:2.5rem}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:.65rem;border-bottom:1px solid #ddd;text-align:right}th:first-child,td:first-child{text-align:left}p{color:#52606d;line-height:1.5}details{margin:1.5rem 0}summary{cursor:pointer;font-weight:600}.scroll{overflow-x:auto}a{color:#17639a}</style></head><body>",
        "<h1>Shore-distance label inventory</h1>",
        f"<p>Nearshore: ocean pixels &lt;{NEARSHORE_CUTOFF_M} m from mapped land. N/A: no labeled kelp.</p>",
        "<h2>Nearshore kelp by region and split</h2><img src='nearshore_regions.png' alt='Nearshore region/split heatmap'>",
        "<p>Percentage of all labeled kelp pixels; full-source labels.</p>",
        "<details><summary>Nearshore area and source counts</summary><p>Area summed across acquisitions.</p><div class='scroll'>",
        f"<table><tr><th>Scope</th><th>Split</th><th>Kelp ha &lt;{NEARSHORE_CUTOFF_M} m</th><th>Share of kelp</th><th>Sources</th></tr>",
    ]
    for row in cumulative_splits:
        if row["cutoff_m"] != NEARSHORE_CUTOFF_M:
            continue
        share = (
            "N/A"
            if row["kelp_fraction"] is None
            else f"{100 * row['kelp_fraction']:.1f}%"
        )
        lines.append(
            f"<tr><td>{escape(row['scope'].replace('_', ' '))}</td><td>{escape(row['split'])}</td><td>{row['kelp_area_ha']:,.1f}</td><td>{share}</td><td>{row['kelp_sources']:,}</td></tr>"
        )
    lines.append("</table></div></details>")
    lines.append(
        "<h2>Kelp distribution by distance</h2><img src='distance_distributions.png' alt='Share of labeled kelp by distance and split'>"
    )
    if (output / "cluster_distance.png").exists():
        lines.extend(
            [
                "<h2>Cluster-size distribution by distance</h2>",
                "<p>Share of labeled kelp pixels in each full-source cluster-size class. Interior clusters only; edge and missing-label fragments excluded.</p>",
                "<img src='cluster_distance.png' alt='Cluster-size composition by distance and split'>",
            ]
        )
    lines.append(exposure_html(output))
    lines.append("<details><summary>Download tables</summary><ul>")
    for name in (
        "source_bands",
        "region_bands",
        "split_bands",
        "source_coverage",
        "cumulative_regions",
        "cumulative_splits",
        "clusters",
        "cluster_correlations",
        "cluster_distance_sources",
        "cluster_distance_regions",
        "cluster_distance_splits",
        "cluster_sources",
    ):
        if (output / f"{name}.csv").is_file():
            lines.append(f"<li><a href='{name}.csv'>{name.replace('_', ' ')}</a></li>")
    lines.append("</ul></details></body></html>")
    (output / "report.html").write_text("\n".join(lines))
