"""Distance diagnostic figures and bounded source overlays for labeled reports."""

from pathlib import Path
from typing import Any

import numpy as np
from matplotlib.figure import Figure

from kelpseg.reporting.shore_distance import NEARSHORE_CUTOFF_M
from kelpseg.visualization import log_stretch


def shore_plot(path: Path, rows: list[dict[str, Any]]) -> None:
    """Save pooled band metrics and scored labeled/predicted kelp area in a PNG."""
    fig = Figure(figsize=(13, 5), layout="constrained")
    metric_ax, area_ax = fig.subplots(1, 2)
    bands = [row["distance_band"] for row in rows]
    x = np.arange(len(rows))
    for name in ("precision", "recall", "iou", "f1"):
        metric_ax.plot(
            x,
            [np.nan if row[name] is None else row[name] for row in rows],
            marker="o",
            label=name,
        )
    metric_ax.set(ylabel="Agreement with supplied labels", ylim=(0, 1))
    metric_ax.legend()
    area_ax.bar(
        x - 0.2,
        [row["labeled_kelp_area_m2"] / 10000 for row in rows],
        width=0.4,
        label="Labeled",
    )
    area_ax.bar(
        x + 0.2,
        [row["predicted_kelp_area_m2"] / 10000 for row in rows],
        width=0.4,
        label="Predicted",
    )
    area_ax.set(ylabel="Scored kelp area (hectares summed over acquisitions)")
    area_ax.legend()
    for ax in (metric_ax, area_ax):
        ax.set_xticks(x, bands, rotation=35)
        ax.set_xlabel("Distance to mapped land (m); land/unknown separate")
        ax.grid(axis="y", alpha=0.2)
    fig.savefig(path, dpi=140)


def shore_example(
    path: Path,
    canvas: dict[str, Any],
    land: np.ndarray,
    distance: np.ndarray,
    threshold: float,
    cap: float,
) -> str:
    """Save a maximum 512-pixel window with imagery, distance, label and prediction.

    Prefer the first scored nearshore kelp pixel, then scored kelp, then any
    scored pixel. Return its source/window caption; inputs remain unchanged.
    """
    labels, probability = canvas["labels"], canvas["probability"]
    valid = (labels != -100) & np.isfinite(probability)
    candidates = valid & (labels == 1) & (land == 0) & (distance < NEARSHORE_CUTOFF_M)
    if not candidates.any():
        candidates = valid & (labels == 1)
    if not candidates.any():
        candidates = valid
    cy, cx = np.unravel_index(np.argmax(candidates), candidates.shape)
    height, width = min(512, labels.shape[0]), min(512, labels.shape[1])
    top = min(max(int(cy) - height // 2, 0), labels.shape[0] - height)
    left = min(max(int(cx) - width // 2, 0), labels.shape[1] - width)
    window = np.s_[top : top + height, left : left + width]
    bands = canvas["source"]["band_names"].split(";")
    if not {"nir", "red", "green"}.issubset(bands):
        raise ValueError(
            "Shoreline examples require native nir, red and green imagery."
        )
    image = canvas["image"][window][
        ..., [bands.index(name) for name in ("nir", "red", "green")]
    ]
    native_valid = canvas["valid"][window]
    image = log_stretch(image, native_valid)
    fig = Figure(figsize=(15, 4.5), layout="constrained")
    axes = fig.subplots(1, 4)
    axes[0].imshow(image)
    lm = land[window]
    distance_view = axes[1].imshow(
        np.ma.masked_where(lm != 0, distance[window]), cmap="viridis", vmin=0, vmax=cap
    )
    fig.colorbar(
        distance_view,
        ax=axes[1],
        orientation="horizontal",
        label=f"Distance to mapped land (m); ≥{cap:g} capped",
        shrink=0.9,
        pad=0.04,
    )
    axes[2].imshow(
        np.ma.masked_where(~valid[window], labels[window]), cmap="gray", vmin=0, vmax=1
    )
    axes[3].imshow(
        np.ma.masked_where(~valid[window], probability[window] >= threshold),
        cmap="gray",
        vmin=0,
        vmax=1,
    )
    for ax in axes:
        if (lm == 0).any() and (lm == 1).any():
            ax.contour(
                np.ma.masked_where(lm == 255, lm == 1),
                levels=[0.5],
                colors="yellow",
                linewidths=0.8,
            )
    for ax, title in zip(
        axes,
        [
            "Log NIR/red/green; yellow mapped shore",
            f"Ocean distance (0–{cap:g} m; capped)",
            "Supplied labels",
            f"Predicted kelp ≥ {threshold:g}",
        ],
        strict=True,
    ):
        ax.set_title(title, fontsize=9)
        ax.set_facecolor(".3")
        ax.set_xticks([])
        ax.set_yticks([])
    source = canvas["source"]
    caption = f"{source.get('original_source_id') or source['source_key']} | region {source.get('region_id', '')} | r{top + int(source.get('row_offset') or 0)} c{left + int(source.get('col_offset') or 0)}"
    fig.suptitle(caption, fontsize=9)
    fig.savefig(path, dpi=140)
    return caption
