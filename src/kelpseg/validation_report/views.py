"""Static false-color figures and a small browser-readable report."""

import html
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray


def example(
    path: Path,
    image: NDArray[np.uint16],
    bands: list[str],
    label: NDArray[np.signedinteger],
    probability: NDArray[np.floating],
    caption: str,
) -> None:
    """Save a five-panel false-color diagnostic PNG at path; return nothing.

    image is native HWC imagery with channel names in bands; label (0/1/-100)
    and probability ([0,1] or NaN) are aligned HW arrays. caption identifies
    the source/window. Show NIR/red/green, labels, threshold-0.5 predictions,
    probabilities and pixel errors, with excluded pixels gray. Inputs stay intact.
    """
    channels = [bands.index(name) for name in ("nir", "red", "green")]
    valid = (label != -100) & np.isfinite(probability)
    color = image[:, :, channels].astype(np.float32)
    if valid.any():
        low, high = np.percentile(color[valid], [2, 98], axis=0)
        color = np.clip((color - low) / np.maximum(high - low, 1), 0, 1)
    color[~valid] = 0.3
    prediction = probability >= 0.5
    error = np.zeros((*label.shape, 3))
    error[(label == 1) & prediction] = [0.2, 0.8, 0.3]
    error[(label == 0) & prediction] = [1, 0.2, 0.2]
    error[(label == 1) & ~prediction] = [0.15, 0.5, 1]
    error[~valid] = 0.3
    fig = Figure(figsize=(15, 3.5), layout="constrained")
    axes = fig.subplots(1, 5)
    axes[0].imshow(color)
    axes[1].imshow(np.ma.masked_where(~valid, label), cmap="gray", vmin=0, vmax=1)
    axes[2].imshow(np.ma.masked_where(~valid, prediction), cmap="gray", vmin=0, vmax=1)
    axes[3].imshow(
        np.ma.masked_where(~valid, probability), cmap="viridis", vmin=0, vmax=1
    )
    axes[4].imshow(error)
    for ax, title in zip(
        axes,
        [
            "False color: NIR/red/green",
            "Supplied label",
            "Prediction ≥ 0.5",
            "Kelp probability (0–1)",
            "Green TP · red FP · blue FN",
        ],
        strict=True,
    ):
        ax.set_title(title, fontsize=9)
        ax.set_facecolor(".3")
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle(caption, fontsize=9)
    fig.savefig(path, dpi=140)


def diagnostic_plot(
    path: Path, sweep: list[dict[str, Any]], histograms: list[dict[str, Any]]
) -> None:
    """Save threshold curves and class-normalized probability histograms to path.

    sweep supplies threshold/IoU/precision/recall records; histograms supplies
    label/lower/upper/pixels records. Undefined scores are omitted from curves.
    Writes one PNG and returns nothing, without modifying either input table.
    """
    fig = Figure(figsize=(11, 4), layout="constrained")
    axes = fig.subplots(1, 2)
    for metric in ("iou", "precision", "recall"):
        axes[0].plot(
            [row["threshold"] for row in sweep],
            [np.nan if row[metric] is None else row[metric] for row in sweep],
            marker=".",
            label=metric,
        )
    axes[0].axvline(0.5, color="gray", linestyle="--")
    axes[0].set(xlabel="Threshold (diagnostic only)", ylabel="Score", ylim=(0, 1))
    for label in ("kelp", "background"):
        rows = [row for row in histograms if row["label"] == label]
        total = sum(row["pixels"] for row in rows)
        if total:
            axes[1].plot(
                [(row["lower"] + row["upper"]) / 2 for row in rows],
                [row["pixels"] / total for row in rows],
                label=f"Labeled {label}",
            )
    axes[1].set(
        xlabel="Predicted kelp probability", ylabel="Fraction within labeled class"
    )
    for ax in axes:
        ax.legend()
        ax.grid(alpha=0.2)
    fig.savefig(path, dpi=140)


def table(rows: list[dict[str, Any]]) -> str:
    """Render same-key flat records as escaped HTML; return an empty-data note if empty.

    Columns follow first-row key order. Floats use four decimals and None is
    displayed as a dash. This function does not write files or modify rows.
    """
    if not rows:
        return "<p>No observations.</p>"
    keys = list(rows[0])

    def cell(value: object) -> str:
        """Format a scalar table value as text; the caller escapes HTML."""
        if value is None:
            return "—"
        return f"{value:.4f}" if isinstance(value, float) else str(value)

    header = "".join(f"<th>{html.escape(key)}</th>" for key in keys)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(cell(row[key]))}</td>" for key in keys)
        + "</tr>"
        for row in rows
    )
    return f'<div class="scroll"><table><tr>{header}</tr>{body}</table></div>'


def write_html(
    output: Path,
    summary: dict[str, Any],
    regions: list[dict[str, Any]],
    sweep: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    sizes: list[dict[str, Any]],
    examples: list[dict[str, str]],
) -> None:
    """Write output/report.html from completed diagnostic tables; return nothing.

    summary provides run metadata and global/background scores. Remaining tables
    hold region, threshold, boundary, error-zone and patch-size results. examples
    provides relative PNG paths and captions. Referenced plots/CSVs must already
    exist in output. Table text is escaped; no server or training hooks are used.
    """
    sections = [
        ("Global scores at threshold 0.5", [summary["global"]]),
        ("Region scores at threshold 0.5", regions),
        ("Background-only chips at threshold 0.5", [summary["background_chips"]]),
        ("Threshold sweep: diagnostic only", sweep),
        ("Boundary agreement: Euclidean pixel tolerance", boundaries),
        ("Errors within 3 pixels of labeled boundaries versus interiors", zones),
        ("Label-patch size: complete observed components only", sizes),
    ]
    content = "".join(
        f"<h2>{html.escape(title)}</h2>{table(rows)}" for title, rows in sections
    )
    figures = "".join(
        f'<p>{html.escape(item["caption"])}</p><a href="{item["file"]}"><img src="{item["file"]}"></a>'
        for item in examples
    )
    text = f"""<!doctype html><html><head><meta charset="utf-8"><title>Validation report</title>
<style>body{{font:16px system-ui;margin:2rem;max-width:1500px}}table{{border-collapse:collapse;font-size:13px}}td,th{{padding:8px;border:1px solid #ddd;text-align:right}}.scroll{{overflow-x:auto}}img{{max-width:100%}}p{{line-height:1.5}}</style></head><body>
<h1>Post-training validation report</h1>
<p>Run: {html.escape(summary["run_id"])}. Selected checkpoint epoch {summary["checkpoint_epoch"]}.
{summary["sources"]} sources, {summary["chips"]} disjoint validation chips.
Float32 inference; no changes to threshold, model or training. Scores describe agreement
with supplied labels on observed validation pixels, not full-TIFF or held-out test performance.</p>
<p>Adjacent windows are joined in source coordinates. Coverage gaps, nodata and ignored pixels
are excluded. Boundary comparisons exclude a tolerance-plus-one pixel neighborhood of unknown
areas and image edges for scored pixels. Matches may use contours outside that margin
when their immediate 3×3 neighborhood is observed. Near-boundary/interior measurements
exclude a four-pixel neighborhood.
Patch sizes use 8-connected label components; these are not necessarily biological kelp beds.
{summary["truncated_patches"]} coverage-truncated components are excluded from size summaries
but retained in patches.csv. Zero-denominator metrics are shown as —.</p>
<p>Threshold 0.5 remains the primary result. The sweep does not select a new threshold.
Probability distributions are in probability_histograms.csv. Source/region areas use each
source's affine pixel area in square metres; signed bias can cancel errors, so FP/FN counts
are retained separately. Background-only window results are in background_chips.csv.</p>
<h2>Threshold and probability diagnostics</h2><img src="diagnostics.png">
{content}<h2>Fixed false-color examples</h2>
<p>One positive chip per region when available plus up to two background chips; not a random
sample. NIR/red/green with a per-chip 2–98% stretch. Gray indicates excluded pixels.
Click a figure for full size. No RGB imagery is used.</p>{figures}
<p>Tables: <a href="sources.csv">sources</a>, <a href="regions.csv">regions</a>,
<a href="patches.csv">patches</a>, <a href="thresholds.csv">thresholds</a>,
<a href="boundaries.csv">boundaries</a>, <a href="zones.csv">error zones</a>,
<a href="probability_histograms.csv">probability histograms</a>.
See summary.json for coverage and full scope metadata.</p></body></html>"""
    (output / "report.html").write_text(text)
