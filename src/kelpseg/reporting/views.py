"""Static false-color figures and a small browser-readable report."""

import html
from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.figure import Figure
from numpy.typing import NDArray

from kelpseg.visualization import log_stretch


def example(
    path: Path,
    image: NDArray[np.uint16],
    bands: list[str],
    label: NDArray[np.signedinteger],
    probability: NDArray[np.floating],
    caption: str,
    threshold: float = 0.5,
) -> None:
    """Save a five-panel false-color diagnostic PNG at path; return nothing.

    image is native HWC imagery with channel names in bands; label (0/1/-100)
    and probability ([0,1] or NaN) are aligned HW arrays. caption identifies
    the source/window. Show NIR/red/green, labels, saved-threshold predictions,
    probabilities and pixel errors, with excluded pixels gray. Inputs stay intact.
    """
    channels = [bands.index(name) for name in ("nir", "red", "green")]
    valid = (label != -100) & np.isfinite(probability)
    color = log_stretch(image[:, :, channels], valid)
    prediction = probability >= threshold
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
            "Log false color: NIR/red/green",
            "Supplied label",
            f"Prediction ≥ {threshold:g}",
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
    path: Path,
    sweep: list[dict[str, Any]],
    histograms: list[dict[str, Any]],
    threshold: float = 0.5,
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
    axes[0].axvline(threshold, color="gray", linestyle="--")
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
        handles, labels = ax.get_legend_handles_labels()
        if handles:
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


def _score_table(rows: list[dict[str, Any]], group: str | None = None) -> str:
    """Return a compact score table with percentages and labeled-pixel support."""
    compact = []
    for row in rows:
        values = {group.replace("_", " ").title(): row[group]} if group else {}
        for key in ("recall", "precision", "iou"):
            value = row.get(key)
            values[key.title()] = "—" if value is None else f"{value:.1%}"
        for key, label in (
            ("labeled_kelp_pixels", "Labeled kelp pixels"),
            ("tp", "TP"),
            ("fn", "FN"),
            ("fp", "FP"),
        ):
            values[label] = f"{row[key]:,}"
        compact.append(values)
    return table(compact)


def _figures(examples: list[dict[str, str]]) -> str:
    """Return linked figures with source/window captions from saved examples."""
    return "".join(
        f'<figure><a href="{html.escape(item["file"])}">'
        f'<img loading="lazy" src="{html.escape(item["file"])}" '
        f'alt="{html.escape(item["caption"])}"></a>'
        f"<figcaption>{html.escape(item['caption'])}</figcaption></figure>"
        for item in examples
    )


def write_html(
    output: Path,
    summary: dict[str, Any],
    regions: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    zones: list[dict[str, Any]],
    sizes: list[dict[str, Any]],
    examples: list[dict[str, str]],
) -> None:
    """Write a concise report from saved scores and figures without changing data.

    Display primary global, regional and shore-distance scores. Secondary
    diagnostics and full-resolution tables remain available behind links or
    disclosures. Inputs are completed report tables and relative figure paths.
    """
    threshold = summary["threshold"]
    shore = summary.get("shoreline")
    parts = [
        """<!doctype html><html><head><meta charset="utf-8">
<title>Validation report</title><style>
body{font:16px system-ui;margin:2rem auto;max-width:1150px;padding:0 1rem;color:#17202b}
h1{font-size:1.8rem}h2{margin-top:2.5rem;font-size:1.3rem}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px 12px;border-bottom:1px solid #ddd;text-align:right}td:first-child,th:first-child{text-align:left}
.scroll{overflow-x:auto}img{max-width:100%}figure{margin:1.5rem 0}figcaption,.meta{font-size:13px;color:#53606e}details{margin:1.2rem 0}summary{cursor:pointer;padding:.6rem 0}nav{margin:1rem 0}a{color:#175f98}p{line-height:1.5}
</style></head><body>""",
        f"<h1>{html.escape(summary['scope'])} · {html.escape(summary['split'])} evaluation</h1>",
        f'<p class="meta">threshold {threshold:g} · {summary["sources"]} TIFFs · epoch {summary["checkpoint_epoch"]} · — = undefined</p>',
    ]
    if "joint_clusters" in summary:
        parts.append(
            '<nav><a href="joint_report.html">Recall by region, distance and cluster size →</a></nav>'
        )
    parts.extend(
        [
            "<h2>Overall</h2>",
            _score_table([summary["global"]]),
            "<h2>By region</h2>",
            _score_table(regions, "region"),
        ]
    )
    if shore:
        parts.extend(
            [
                "<h2>Distance to mapped land</h2>",
                '<p class="meta">Distance in metres · land and unknown shown separately</p>',
                '<img src="shoreline.png" alt="Recall, precision and labeled support by distance to mapped land">',
                "<details><summary>Distance-band counts</summary>",
                _score_table(shore["global_bands"], "distance_band"),
                "</details><h2>Shoreline examples</h2>",
                '<p class="meta">Log NIR/red/green · yellow = mapped shoreline · selected examples</p>',
                _figures(shore["examples"]),
            ]
        )
    if examples:
        parts.extend(
            [
                "<details><summary>Prediction examples</summary>",
                '<p class="meta">Log NIR/red/green · gray = excluded · selected examples</p>',
                _figures(examples),
                "</details>",
            ]
        )
    parts.extend(
        [
            "<details><summary>Additional diagnostics</summary>",
            '<h2>Threshold and probability</h2><img loading="lazy" src="diagnostics.png" alt="Threshold curves and probability histograms">',
            "<h2>Boundary agreement</h2>",
            table(boundaries),
            "<h2>Boundary and interior errors</h2>",
            table(zones),
            "<h2>Observed patch size</h2>",
            table(sizes),
            "</details>",
            "<details><summary>Data and coverage</summary>",
            f'<p class="meta">{html.escape(summary["run_id"])}</p>',
            table([summary["coverage"]]),
        ]
    )
    links = (
        ("summary.json", "Metadata"),
        ("sources.csv", "TIFF scores"),
        ("regions.csv", "Region scores"),
        ("thresholds.csv", "Thresholds"),
        ("patches.csv", "Patches"),
        ("boundaries.csv", "Boundaries"),
        ("zones.csv", "Error zones"),
        ("probability_histograms.csv", "Probabilities"),
        ("background_chips.csv", "Background chips"),
        ("shoreline_sources.csv", "TIFF × distance"),
        ("shoreline_regions.csv", "Region × distance"),
        ("shoreline_summary.csv", "Distance totals"),
    )
    parts.append(
        "<p>"
        + " · ".join(
            f'<a href="{name}">{label}</a>'
            for name, label in links
            if (output / name).exists()
        )
        + "</p></details></body></html>"
    )
    (output / "report.html").write_text("\n".join(parts))
