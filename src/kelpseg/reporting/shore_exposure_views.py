"""Display expected window-sampler exposure separately from unique-pixel support."""

import csv
from html import escape
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure


def number(value: str, *, percent: bool = False) -> str:
    """Format a CSV numeric value, preserving undefined denominators as N/A."""
    if value == "":
        return "N/A"
    return f"{100 * float(value):.2f}%" if percent else f"{float(value):,.1f}"


def exposure_html(output: Path) -> str:
    """Render saved exposure summaries and a regional plot; return an HTML section.

    Expected counts are before augmentation and use the uniform, once-per-epoch
    eligible-window sampler. Existing inventories without exposure stay readable.
    """
    path = output / "exposure_summary.csv"
    if not path.is_file():
        return ""
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    groups = list(dict.fromkeys((r["level"], r["region"]) for r in rows))
    regions = [region for level, region in groups if level == "region"]
    lookup = {
        (r["level"], r["region"], r["shore_zone"], r["size_bin"]): r for r in rows
    }
    parts = [
        "<h2>Training exposure</h2>",
        "<p>Uniform eligible-window sampler, before augmentation. Small clusters: ≤100 full-source pixels, including boundary fragments. Nearshore: &lt;120 m; offshore: ≥120 m.</p>",
        "<img src='training_exposure.png' alt='Training draw shares and kelp pixels per draw by region'>"
        if regions
        else "<p>No training sources in this inventory.</p>",
        "<details><summary>Pixels per draw and eligible windows</summary><p>Pixel means are conditional on drawing that region.</p><div class='scroll'>",
        "<table><tr><th>Region</th><th>Windows</th><th>Draw share</th><th>Nearshore kelp</th><th>Small nearshore</th><th>Small offshore</th></tr>",
    ]
    for level, region in groups:
        total = lookup[level, region, "all", "all"]
        near = lookup[level, region, "nearshore", "all"]
        small_near = lookup[level, region, "nearshore", "<=100"]
        small_far = lookup[level, region, "offshore", "<=100"]
        parts.append(
            f"<tr><td>{escape(region) if level == 'region' else 'All regions'}</td>"
            f"<td>{total['eligible_windows']}</td>"
            f"<td>{number(total['region_draw_probability'], percent=True)}</td>"
            f"<td>{number(near['expected_pixels_per_region_draw'])}</td>"
            f"<td>{number(small_near['expected_pixels_per_region_draw'])}</td>"
            f"<td>{number(small_far['expected_pixels_per_region_draw'])}</td></tr>"
        )
    parts.append(
        "</table></div><p><a href='exposure_windows.csv'>Per-window counts</a> · <a href='exposure_summary.csv'>All exposure statistics</a></p></details>"
    )
    if regions:
        fig = Figure(figsize=(14, 4), layout="constrained")
        axes = fig.subplots(1, 3)
        x = np.arange(len(regions))
        probability = [
            float(lookup["region", r, "all", "all"]["region_draw_probability"] or 0)
            * 100
            for r in regions
        ]
        axes[0].bar(x, probability)
        axes[0].set_title("Share of all training draws")
        axes[0].set_ylabel("Draw probability (%)")
        for ax, zone, title in zip(
            axes[1:],
            ("nearshore", "offshore"),
            ("Nearshore exposure", "Offshore exposure"),
            strict=True,
        ):
            for offset, size, label in (
                (-0.2, "all", "All kelp"),
                (0.2, "<=100", "Small-cluster kelp"),
            ):
                values = [
                    float(
                        lookup["region", r, zone, size][
                            "expected_pixels_per_region_draw"
                        ]
                        or "nan"
                    )
                    for r in regions
                ]
                ax.bar(x + offset, values, width=0.4, label=label)
            ax.set_title(title)
            ax.set_ylabel("Pixels / draw within region")
            ax.legend(fontsize=8)
        for ax in axes:
            ax.set_xticks(x, regions, rotation=45)
            ax.set_xlabel("Training region")
        fig.savefig(output / "training_exposure.png", dpi=140)
    return "\n".join(parts)
