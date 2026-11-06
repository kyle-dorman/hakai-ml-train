"""Readable recall comparisons by region, shore distance and saved cluster size."""

from html import escape
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.figure import Figure

from kelpseg.reporting.shore_clusters import CLUSTER_SIZE_BINS

FOCUS_REGIONS = ("004", "006", "007", "008")
OCEAN_BANDS = ("0-30", "30-60", "60-120", "120-250", "250-500", "500+")
COLORS = ("#996600", "#d95f02", "#1b9e77", "#7570b3", "#0072b2")
Row = dict[str, Any]


def _percent(value: float | None, *, signed: bool = False) -> str:
    """Format a proportion as percent or signed percentage-point difference."""
    if value is None:
        return "N/A"
    return f"{100 * value:+.1f}" if signed else f"{100 * value:.1f}%"


def _label_support(row: Row, prefix: str) -> str:
    """Display scored label pixels and observed hectares with one denominator."""
    return f"{row[f'{prefix}_labeled_kelp_pixels']:,}<br>({row[f'{prefix}_labeled_kelp_area_m2'] / 10000:.3f} ha)"


def _distance_plot(path: Path, rows: list[Row], regions: list[str], scope: str) -> None:
    """Plot pooled recall by distance for each full-source size class and region."""
    fig = Figure(figsize=(14, 9), layout="constrained")
    axes = np.atleast_1d(fig.subplots(2, 2)).ravel()
    for ax, region in zip(axes, regions, strict=False):
        selected = [
            row
            for row in rows
            if row["region"] == region and row["component_scope"] == scope
        ]
        lookup = {(row["size_bin"], row["distance_band"]): row for row in selected}
        for (size, _), color in zip(CLUSTER_SIZE_BINS, COLORS, strict=True):
            values = [
                lookup.get((size, band), {}).get("recall") for band in OCEAN_BANDS
            ]
            ax.plot(
                range(len(OCEAN_BANDS)),
                [np.nan if value is None else 100 * value for value in values],
                marker="o",
                color=color,
                label=f"{size} px",
            )
        ax.set(
            title=f"Region {region}",
            ylabel="Kelp recall (%)",
            ylim=(0, 100),
            xlabel="Ocean distance band (m); 500+ capped",
        )
        ax.set_xticks(range(len(OCEAN_BANDS)), OCEAN_BANDS, rotation=25)
        ax.grid(alpha=0.2)
        ax.legend(title="Full-source cluster size", fontsize=8)
    for ax in axes[len(regions) :]:
        ax.set_visible(False)
    fig.suptitle(
        f"Recall within region and saved cluster-size class · {scope.replace('_', ' ')}"
    )
    fig.savefig(path, dpi=140)


def _gap_plot(path: Path, rows: list[Row], regions: list[str]) -> None:
    """Compare all-component and interior-only nearshore recall gaps per size."""
    fig = Figure(figsize=(14, 8), layout="constrained")
    axes = np.atleast_1d(fig.subplots(2, 2)).ravel()
    sizes = [size for size, _ in CLUSTER_SIZE_BINS]
    for ax, region in zip(axes, regions, strict=False):
        for scope, color, offset in (
            ("all_observed", "#666666", -0.06),
            ("interior_only", "#0072b2", 0.06),
        ):
            lookup = {
                row["size_bin"]: row
                for row in rows
                if row["region"] == region and row["component_scope"] == scope
            }
            values = [lookup.get(size, {}).get("recall_gap") for size in sizes]
            ax.plot(
                np.arange(len(sizes)) + offset,
                [np.nan if value is None else 100 * value for value in values],
                marker="o",
                label=scope.replace("_", " "),
                color=color,
            )
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set(
            title=f"Region {region}",
            ylabel="Nearshore − offshore recall (pp)",
            ylim=(-100, 100),
        )
        ax.set_xticks(range(len(sizes)), sizes, rotation=25)
        ax.set_xlabel("Saved full-source cluster-size band (pixels)")
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    for ax in axes[len(regions) :]:
        ax.set_visible(False)
    fig.suptitle(
        "Nearshore <120 m versus offshore ≥120 m · negative values indicate a nearshore deficit"
    )
    fig.savefig(path, dpi=140)


def _recall_table(rows: list[Row]) -> str:
    """Render pooled positive counts, area and recall with empty groups explicit."""
    lines = [
        "<div class='scroll'><table><tr><th>Size (px)</th><th>Components</th><th>Near labels<br>pixels (ha)</th><th>Near TP</th><th>Near FN</th><th>Near recall</th><th>Offshore labels<br>pixels (ha)</th><th>Offshore TP</th><th>Offshore FN</th><th>Offshore recall</th><th>Gap (pp)</th></tr>"
    ]
    for row in rows:
        if row["component_scope"] not in {"all_observed", "interior_only"}:
            continue
        cells = [
            escape(row["size_bin"]),
            row["component_scope"].replace("_", " "),
            _label_support(row, "nearshore"),
            f"{row['nearshore_tp']:,}",
            f"{row['nearshore_fn']:,}",
            _percent(row["nearshore_recall"]),
            _label_support(row, "offshore"),
            f"{row['offshore_tp']:,}",
            f"{row['offshore_fn']:,}",
            _percent(row["offshore_recall"]),
            _percent(row["recall_gap"], signed=True),
        ]
        lines.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    return "".join(lines) + "</table></div>"


def _support_table(rows: list[Row], scope: str) -> str:
    """Show sparse/dominant-source support and matched-date sensitivity."""
    lines = [
        "<div class='scroll'><table><tr><th>Size (px)</th><th>Near sources / dates</th><th>Offshore sources / dates</th><th>Largest near<br>source / date share</th><th>Largest offshore<br>source / date share</th><th>Paired sources<br>near lower / paired</th><th>Paired dates<br>near lower / paired</th><th>Same-date pooled<br>gap (pp)</th><th>Gap without largest<br>source / date (pp)</th><th>Support flags</th></tr>"
    ]
    for row in rows:
        if row["component_scope"] != scope:
            continue
        cells = [
            escape(row["size_bin"]),
            f"{row['nearshore_source_count']} / {row['nearshore_date_count']}",
            f"{row['offshore_source_count']} / {row['offshore_date_count']}",
            f"{_percent(row['nearshore_max_source_kelp_share'])} / {_percent(row['nearshore_max_date_kelp_share'])}",
            f"{_percent(row['offshore_max_source_kelp_share'])} / {_percent(row['offshore_max_date_kelp_share'])}",
            f"{row['paired_source_nearshore_lower_count']} / {row['paired_source_count']}",
            f"{row['paired_date_nearshore_lower_count']} / {row['paired_date_count']}",
            _percent(row["paired_date_pooled_gap"], signed=True),
            f"{_percent(row['without_largest_source_gap'], signed=True)} / {_percent(row['without_largest_date_gap'], signed=True)}",
            escape(row["support_flags"]) or "—",
        ]
        lines.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    return "".join(lines) + "</table></div>"


def _comparison_plot(path: Path, rows: list[Row], regions: list[str]) -> None:
    """Show nearshore and offshore recall on a common scale for interior beds."""
    fig = Figure(figsize=(12, 7), layout="constrained")
    axes = np.atleast_1d(fig.subplots(2, 2)).ravel()
    sizes = [size for size, _ in CLUSTER_SIZE_BINS]
    for ax, region in zip(axes, regions, strict=False):
        lookup = {
            row["size_bin"]: row
            for row in rows
            if row["region"] == region and row["component_scope"] == "interior_only"
        }
        for y, size in enumerate(sizes):
            row = lookup.get(size, {})
            near, offshore = row.get("nearshore_recall"), row.get("offshore_recall")
            if near is not None and offshore is not None:
                ax.plot([100 * near, 100 * offshore], [y, y], color="#cbd5e1", lw=2)
        for side, color, label in (
            ("nearshore", "#d95f02", "Nearshore <120 m"),
            ("offshore", "#0072b2", "Offshore ≥120 m"),
        ):
            values = [lookup.get(size, {}).get(f"{side}_recall") for size in sizes]
            ax.scatter(
                [np.nan if x is None else 100 * x for x in values],
                range(len(sizes)),
                color=color,
                label=label,
                s=45,
                zorder=3,
            )
        ax.set_yticks(range(len(sizes)), sizes)
        ax.invert_yaxis()
        ax.set(
            title=f"Region {region}",
            xlabel="Recall (%)",
            ylabel="Cluster size (pixels)",
            xlim=(0, 100),
        )
        ax.grid(axis="x", alpha=0.2)

    for ax in axes[len(regions) :]:
        ax.set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside upper center", ncol=2, frameon=False)
    fig.savefig(path, dpi=150)


def _compact_table(rows: list[Row]) -> str:
    """Pair recall with its pixel and acquisition support, five rows per region."""
    lines = [
        "<table><tr><th>Cluster size (px)</th><th>Recall %<br>near / off</th><th>Kelp pixels<br>near / off</th><th>Dates<br>near / off</th><th>Largest TIFF share %<br>near / off</th></tr>"
    ]
    for row in rows:
        if row["component_scope"] != "interior_only":
            continue
        cells = [escape(row["size_bin"])]
        for field in (
            "recall",
            "labeled_kelp_pixels",
            "date_count",
            "max_source_kelp_share",
        ):
            values = [row[f"{side}_{field}"] for side in ("nearshore", "offshore")]
            if field in {"recall", "max_source_kelp_share"}:
                cells.append(" / ".join(_percent(value) for value in values))
            else:
                cells.append(" / ".join(f"{value:,}" for value in values))
        lines.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>")
    return "".join(lines) + "</table>"


def write_joint_views(
    output: Path,
    tables: dict[str, list[Row]],
    *,
    threshold: float = 0.5,
    accounting: Row | None = None,
) -> Path:
    """Render essential comparisons, with counts and accounting in disclosures.

    Uses completed tables only; does not modify predictions or cluster metadata.
    """
    comparisons = tables["joint_nearshore_comparisons"]
    available = sorted({row["region"] for row in comparisons})
    focus = [region for region in FOCUS_REGIONS if region in available] or available[:4]
    for scope, name in (("interior_only", "interior"), ("all_observed", "all")):
        _distance_plot(
            output / f"joint_recall_{name}.png", tables["joint_regions"], focus, scope
        )
    _gap_plot(output / "joint_recall_gaps.png", comparisons, focus)
    _comparison_plot(output / "joint_recall_comparison.png", comparisons, focus)
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>Recall by shore distance and bed size</title><style>body{font:16px system-ui;color:#17212b;max-width:1100px;margin:40px auto;padding:0 20px}img{max-width:100%}table{border-collapse:collapse;width:100%;font-size:14px;margin:16px 0}th,td{padding:10px;border-bottom:1px solid #ddd;text-align:right}th:first-child,td:first-child{text-align:left}th{color:#52616b}details{margin:22px 0}summary{cursor:pointer}a{color:#17669b}.scroll{overflow-x:auto}h2{margin-top:36px}p{color:#52616b}</style></head><body>",
        "<a href='report.html'>Validation report</a><h1>Recall by shore distance and bed size</h1>",
        f"<p>Nearshore &lt;120 m · Offshore ≥120 m · Threshold {threshold:g}<br>Full-source cluster sizes; boundary-truncated clusters excluded. N/A = no labeled kelp.</p>",
        "<img src='joint_recall_comparison.png' alt='Nearshore and offshore recall within each region and cluster-size band'>",
    ]
    for region in focus + [region for region in available if region not in focus]:
        selected = sorted(
            (row for row in comparisons if row["region"] == region),
            key=lambda row: [size for size, _ in CLUSTER_SIZE_BINS].index(
                row["size_bin"]
            ),
        )
        if region not in focus:
            parts.append(f"<details><summary>Region {escape(region)}</summary>")
        else:
            parts.append(f"<h2>Region {escape(region)}</h2>")
        parts.append("<div class='scroll'>" + _compact_table(selected) + "</div>")
        parts.extend(
            [
                "<details><summary>Counts, boundary comparison and acquisition support</summary>",
                _recall_table(selected),
                "<h3>Interior clusters</h3>",
                _support_table(selected, "interior_only"),
                "<h3>All clusters</h3>",
                _support_table(selected, "all_observed"),
                "</details>",
            ]
        )
        if region not in focus:
            parts.append("</details>")
    parts.extend(
        [
            "<details><summary>Recall by distance band</summary><img src='joint_recall_interior.png' alt='Interior cluster recall by distance band'></details>",
            "<details><summary>Boundary-truncated cluster comparison</summary><img src='joint_recall_gaps.png' alt='Recall gap with and without truncated clusters'><img src='joint_recall_all.png' alt='All cluster recall by distance'></details>",
            "<details><summary>Definitions and data</summary><p>Recall = TP / (TP + FN). Areas sum observed pixels across acquisitions. Land and unknown distance are separate in the CSVs and excluded from the ocean comparison. Interior clusters touch neither missing labels nor source edges.</p>",
            "<p>Support flags: &lt;100 pixels, &lt;3 dates, or one source/date supplying over 50% of labeled pixels. Paired comparisons require kelp on both sides. Largest-contributor removal uses combined nearshore + offshore pixels.</p>",
            "<p>False positives have no true label-cluster size: <a href='shoreline_regions.csv'>FP and precision by region / distance</a>.</p>",
        ]
    )
    if accounting is not None:
        parts.append(
            "<table><tr><th>Scored kelp pixels</th><th>TP</th><th>FN</th></tr>"
        )
        for key, label in (
            ("all", "All clusters"),
            ("interior", "Interior clusters"),
            ("truncated", "Boundary-truncated clusters"),
        ):
            parts.append(
                f"<tr><td>{label}</td><td>{accounting[key]['tp']:,}</td><td>{accounting[key]['fn']:,}</td></tr>"
            )
        parts.append("</table>")
    parts.append(
        "<ul><li><a href='summary.json'>Metadata and exclusion accounting</a></li><li><a href='joint_reconciliation.csv'>Count reconciliation</a></li><li><a href='joint_sources.csv'>Source counts</a></li>"
    )
    for name in tables:
        parts.append(
            f"<li><a href='{escape(name)}.csv'>{escape(name.replace('_', ' '))}</a></li>"
        )
    parts.append("</ul></details></body></html>")
    path = output / "joint_report.html"
    path.write_text("\n".join(parts))
    return path
