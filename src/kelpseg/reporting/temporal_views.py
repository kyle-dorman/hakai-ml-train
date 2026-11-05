"""Static temporal diagnostics using the existing HTML tables and Matplotlib."""

import html
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from matplotlib.figure import Figure

from kelpseg.reporting.temporal_inputs import LOCATION_KEYS
from kelpseg.reporting.views import table


def _location(row: dict) -> str:
    """Return an explicit dataset/release/region display label without guessing geography."""
    return " / ".join(str(row.get(key) or "unknown") for key in LOCATION_KEYS)


def change_plot(
    path: Path, pairs: list[dict], interval_bounds: dict[str, list[int]]
) -> None:
    """Plot defined label/prediction percentage changes by interval and location."""
    selected = [
        row
        for row in pairs
        if row["status"] == "supported" and row.get("change_error_pp") not in (None, "")
    ]
    present = {row["interval"] for row in selected}
    intervals = [name for name in ("short", "long") if name in present]
    figure = Figure(figsize=(6 * max(1, len(intervals)), 5), layout="constrained")
    axes = figure.subplots(1, max(1, len(intervals)), squeeze=False)[0]
    if not intervals:
        axes[0].text(
            0.5,
            0.5,
            "No pairs with defined percentage changes",
            ha="center",
            va="center",
        )
        axes[0].set_axis_off()
    for axis, interval in zip(axes, intervals, strict=False):
        rows = [row for row in selected if row["interval"] == interval]
        by_location = defaultdict(list)
        for row in rows:
            by_location[_location(row)].append(row)
        values = []
        for location, members in sorted(by_location.items()):
            x = [float(row["label_change_pct"]) for row in members]
            y = [float(row["prediction_change_pct"]) for row in members]
            values.extend(x + y)
            axis.scatter(x, y, label=f"{location} (n={len(members)})", alpha=0.75)
        low, high = min(values), max(values)
        margin = max(1.0, (high - low) * 0.05)
        bounds = (low - margin, high + margin)
        axis.plot(bounds, bounds, linestyle="--", color="gray", label="Matching change")
        bounds_days = interval_bounds.get(interval)
        title = interval.capitalize()
        if bounds_days:
            title += f" ({bounds_days[0]}–{bounds_days[1]} days)"
        axis.set(
            title=title,
            xlabel="Labeled canopy change (%)",
            ylabel="Predicted canopy change (%)",
            xlim=bounds,
            ylim=bounds,
        )
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
    figure.savefig(path, dpi=140)


def source_plot(path: Path, dates: list[dict]) -> None:
    """Show dated observation-area error and scoring coverage separately per region.

    These are descriptive source observation totals, not fixed-footprint change
    estimates. Points are not connected across dates with different footprints.
    """
    groups = defaultdict(list)
    for row in dates:
        groups[_location(row)].append(row)
    figure = Figure(figsize=(11, max(3, 2.8 * len(groups))), layout="constrained")
    axes = figure.subplots(max(1, len(groups)), 2, squeeze=False)
    if not groups:
        for axis in axes[0]:
            axis.text(
                0.5, 0.5, "No dated region observations", ha="center", va="center"
            )
            axis.set_axis_off()
    for axes_row, (location, rows) in zip(axes, sorted(groups.items()), strict=False):
        x = [date.fromisoformat(row["acquisition_date"]) for row in rows]
        for field, label in (
            ("labeled_area_m2", "Labeled canopy"),
            ("area_bias_m2", "Predicted minus labeled"),
            ("false_positive_area_m2", "False positive"),
            ("false_negative_area_m2", "False negative"),
        ):
            axes_row[0].scatter(x, [row[field] / 10000 for row in rows], label=label)
        axes_row[0].axhline(0, color="gray", linewidth=0.7)
        axes_row[0].set(title=location, ylabel="Observation area/error (ha)")
        axes_row[0].legend(fontsize=8)
        coverage = [
            100 * row["scoreable_pixels"] / row["valid_pixels"]
            if row["valid_pixels"]
            else float("nan")
            for row in rows
        ]
        axes_row[1].scatter(x, coverage, label="Scoreable / native valid")
        axes_row[1].set(title=location, ylabel="Scoring coverage (%)", ylim=(0, 105))
        for axis in axes_row:
            axis.grid(alpha=0.2)
            axis.tick_params(axis="x", rotation=25, labelsize=8)
    figure.savefig(path, dpi=140)


def write_temporal_report(
    output: Path,
    summary: dict,
    tables: dict[str, list[dict]],
    pairs: list[dict],
    pair_summaries: list[dict],
) -> None:
    """Write report.html plus two figures from computed tables; never load models or rasters."""
    change_plot(output / "changes.png", pairs, summary.get("intervals", {}))
    source_plot(output / "observations.png", tables["dates"])
    reasons = Counter(row["status"] for row in pairs)
    status_rows = [
        dict(status=key, pairs=value) for key, value in sorted(reasons.items())
    ]
    interval_rows = [
        dict(interval=name, minimum_days=bounds[0], maximum_days=bounds[1])
        for name, bounds in summary.get("intervals", {}).items()
    ]
    support = {
        name: summary.get(name, 0)
        for name in (
            "candidate_pairs",
            "supported_pairs",
            "percentage_defined_pairs",
            "same_day_pairs",
        )
    }
    sections = [
        ("Configured elapsed-day intervals (inclusive)", interval_rows),
        (
            "Input report coverage (all source observations)",
            [summary["input_coverage"]] if summary.get("input_coverage") else [],
        ),
        ("Overall support counts", [support]),
        ("Pair support and unavailable reasons", status_rows),
        ("Percentage-point error by region and interval", pair_summaries),
        ("Sources excluded from temporal grouping", tables["source_exclusions"]),
    ]
    for key, title in (
        ("dates", "Region/date observation totals"),
        ("years", "Represented years"),
        ("year_months", "Represented year-months"),
        ("months", "Calendar months pooled across represented years"),
    ):
        sections.append((title, tables[key]))
    sections_html = "".join(
        f"<h2>{html.escape(title)}</h2>{table(rows)}" for title, rows in sections
    )
    run_id, scope, split = (
        html.escape(str(summary.get(key, "unknown")))
        for key in ("run_id", "scope", "split")
    )
    text = f"""<!doctype html><html><head><meta charset="utf-8"><title>Temporal canopy change</title>
<style>body{{font:16px system-ui;margin:2rem;max-width:1500px}}table{{border-collapse:collapse;font-size:13px}}td,th{{padding:8px;border:1px solid #ddd;text-align:right}}.scroll{{overflow-x:auto}}img{{max-width:100%}}p{{line-height:1.5}}</style></head><body>
<h1>Canopy percentage change relative to labels</h1>
<p>Run: {run_id}. Scope: {scope}; split: {split}. No inference or model selection is performed.</p>
<p>Each pair uses only its common valid labeled and predicted footprint at both dates.
Label and prediction changes each use their own earlier kelp count as the denominator.
Change error is predicted minus labeled percentage change, in percentage points.
Uncovered valid pixels are excluded from scoring and from both dates’ common footprint.
The input coverage table reports these exclusions across all source observations.
Zero starting kelp makes that series' percentage undefined; small baselines are flagged in pairs.csv, never dropped or replaced by an epsilon.</p>
<p>Same-day observations are separate from temporal changes. Repeated source/date pairs are not independent samples.
Pairwise common footprints may differ: these comparisons do not establish a single fixed-footprint trend.
Uneven regional support must not be interpreted as a statewide annual result.</p>
<h2>Predicted versus labeled proportional change</h2><img src="changes.png">
<p>The dashed line represents matching percentage changes. No percentage clipping or baseline smoothing is applied.</p>
{sections_html}
<h2>Dated source observations and coverage</h2><img src="observations.png">
<p>Date/year/month totals sum observation pixels and area; they are not unique coastline area across acquisitions.
Same-day images can overlap, and dated footprints can differ. No unique date-area mosaic is inferred.
These source totals describe support and errors; common-footprint pairs provide the change comparison.</p>
<p>Tables: <a href="pairs.csv">all pairs and reasons</a>, <a href="pair_summaries.csv">regional pair summaries</a>,
<a href="dates.csv">dates</a>, <a href="years.csv">years</a>, <a href="year_months.csv">year-months</a>,
<a href="months.csv">calendar months</a>, <a href="source_exclusions.csv">source exclusions</a>.
See summary.json for the saved model, interval definitions and scope.</p></body></html>"""
    (output / "report.html").write_text(text)
