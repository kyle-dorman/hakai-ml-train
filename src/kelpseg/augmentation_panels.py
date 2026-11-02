"""Frozen display limits and labeled contact sheets for augmentation review."""

from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

DISPLAY_CEILING = 2000


def display_limits(chips: list[dict]) -> np.ndarray:
    """User-selected 0–2000 display range, separate from the model's 5000 cap."""
    channels = len(chips[0]["band_names"])
    return np.array([[0] * channels, [DISPLAY_CEILING] * channels], dtype=float)


def closeup_window(label: np.ndarray, size: int = 96) -> tuple[int, int, int, int]:
    """Freeze a visible kelp boundary with surrounding context; no resizing."""
    height, width = label.shape
    size = min(size, height, width)
    candidates = []
    tops = sorted({*range(0, height - size + 1, max(1, size // 2)), height - size})
    lefts = sorted({*range(0, width - size + 1, max(1, size // 2)), width - size})
    for top in tops:
        for left in lefts:
            count = np.count_nonzero(label[top : top + size, left : left + size] == 1)
            if count:
                ignored = np.count_nonzero(
                    label[top : top + size, left : left + size] == -100
                )
                score = abs(count / size**2 - 0.5) + ignored / size**2
                candidates.append((score, top, left))
    _, top, left = min(candidates) if candidates else (0, 0, 0)
    return top, left, top + size, left + size


def spectral_view(image, names, bands, limits, valid):
    indices = [names.index(name) for name in bands]
    low, high = limits[:, indices]
    view = np.clip((image[:, :, indices] - low) / (high - low), 0, 1)
    view[~valid] = 0
    return view


def label_overlay(rgb, label, valid):
    view = rgb * 0.65
    view[label == 1] = view[label == 1] * 0.3 + np.array([1, 1, 0]) * 0.7
    view[(label == -100) & valid] = [0.85, 0.1, 0.85]
    view[~valid] = [0.25, 0.05, 0.3]
    return view


def render_panel(path: Path, sample: dict, family: str, states: list[dict], limits):
    """Columns are isolated settings; all use identical display limits."""
    columns = len(states)
    affected_band = (
        family.removeprefix("band_dropout_")
        if family.startswith("band_dropout_")
        else None
    )
    row_count = 5 if affected_band else 4
    figure = Figure(figsize=(2.3 * columns + 0.8, 2.25 * row_count + 1.4), dpi=100)
    FigureCanvasAgg(figure)
    axes = figure.subplots(row_count, columns, squeeze=False)
    row_names = [
        "RGB: red/green/blue",
        "False color: NIR/red/green",
        "Kelp yellow; ignore purple",
        "96px kelp-boundary close-up",
    ]
    if affected_band:
        row_names.append(f"Affected band: {affected_band}")
    names = sample["band_names"]
    top, left, bottom, right = sample["closeup"]
    for column, state in enumerate(states):
        image, label, valid = state["display"], state["label"], state["valid"]
        rgb = spectral_view(image, names, ("red", "green", "blue"), limits, valid)
        false = spectral_view(image, names, ("nir", "red", "green"), limits, valid)
        overlay = label_overlay(rgb, label, valid)
        # Geometry moves the sparse support jointly; its close-up is transformed
        # with the image rather than choosing a different foreground feature.
        crop = state.get("closeup", (top, left, bottom, right))
        y0, x0, y1, x1 = crop
        views = [rgb, false, overlay, overlay[y0:y1, x0:x1]]
        if affected_band:
            channel = names.index(affected_band)
            low, high = limits[:, channel]
            gray = np.clip((image[:, :, channel] - low) / (high - low), 0, 1)
            gray[~valid] = 0
            views.append(np.repeat(gray[:, :, None], 3, axis=-1))
        for row, view in enumerate(views):
            axis = axes[row, column]
            axis.imshow(view, interpolation="nearest")
            axis.set_xticks([])
            axis.set_yticks([])
            if column == 0:
                axis.set_ylabel(row_names[row], fontsize=9)
        stats = state["metrics"]
        axes[0, column].set_title(state["title"], fontsize=9)
        axes[-1, column].set_xlabel(
            f"<0: {stats['below_zero_values']:,} | >5000: {stats['above_cap_values']:,}\n"
            f"valid: {stats['valid_pixels']:,} | kelp: {stats['foreground_pixels']:,}",
            fontsize=8,
        )
    row = sample["row"]
    category = (
        "BACKGROUND CONTROL — diagnostics only"
        if sample["background_control"]
        else "TRAIN — kelp positive"
    )
    figure.suptitle(
        f"TRIALS ONLY • {family} • {sample['preview_name']} • {category}\n"
        f"{row['region']} | {row['acquisition_date']} | {row['source_key']} | r{row['row']} c{row['col']}\n"
        "Stock Albumentations • display 0–2000 • final model cap 5000",
        fontsize=11,
    )
    figure.subplots_adjust(
        left=0.065, right=0.995, bottom=0.065, top=0.88, wspace=0.06, hspace=0.06
    )
    figure.savefig(path)
    figure.clear()
