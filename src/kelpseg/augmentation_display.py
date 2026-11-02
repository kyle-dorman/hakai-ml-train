"""Export full-resolution display images for the offline comparison viewer."""

import json
from pathlib import Path

import numpy as np
from matplotlib import image as mpl_image

from kelpseg.augmentation_panels import label_overlay, spectral_view


def _save_view(path: Path, pixels: np.ndarray) -> None:
    # Write native pixel dimensions without axes, titles or resampling. The HTML
    # viewer handles labels and paired zoom separately from the scientific data.
    mpl_image.imsave(path, np.round(pixels * 255).astype(np.uint8))


def write_display_views(folder, sample, family, states, limits, originals):
    """Write display pixels; reuse unchanged original views within this sample."""
    names = sample["band_names"]
    band = (
        family.removeprefix("band_dropout_")
        if family.startswith("band_dropout_")
        else None
    )
    assets = []
    for index, state in enumerate(states):
        identity = state["is_identity"]
        image, valid = state["display"], state["valid"]
        views = {}
        # Export each clean view and its label overlay from the same pixels.
        # Identity and unaffected dropout views reuse their source-original pair.
        for view, bands, overlay in (
            ("rgb", ("red", "green", "blue"), "labels"),
            ("false_color", ("nir", "red", "green"), "false_color_labels"),
        ):
            unchanged = identity or (band is not None and band not in bands)
            if unchanged and view in originals:
                views[view] = originals[view]
                views[overlay] = originals[overlay]
                continue
            pixels = spectral_view(image, names, bands, limits, valid)
            for name, display in (
                (view, pixels),
                (overlay, label_overlay(pixels, state["label"], valid)),
            ):
                filename = f"{family}_{index:02d}_{name}.png"
                _save_view(folder / filename, display)
                views[name] = f"{sample['preview_name']}/views/{filename}"
        if index == 0:
            originals.update(
                {
                    key: views[key]
                    for key in ("rgb", "false_color", "labels", "false_color_labels")
                }
            )
        if band:
            original_key = f"band_{band}"
            if identity and original_key in originals:
                views["affected_band"] = originals[original_key]
            else:
                channel = names.index(band)
                low, high = limits[:, channel]
                gray = np.clip((image[:, :, channel] - low) / (high - low), 0, 1)
                gray[~valid] = 0
                filename = f"{family}_{index:02d}_affected.png"
                _save_view(folder / filename, np.repeat(gray[:, :, None], 3, axis=-1))
                views["affected_band"] = f"{sample['preview_name']}/views/{filename}"
                if identity:
                    originals[original_key] = views["affected_band"]
        assets.append(views)
    return assets


def write_viewer(
    output: Path,
    metadata: dict,
    records: list[dict],
    *,
    template_name: str = "augmentation_viewer.html",
) -> None:
    """Embed records so opening index.html works directly from disk offline."""
    data = dict(metadata, samples=records)
    encoded = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    template = Path(__file__).with_name(template_name).read_text(encoding="utf-8")
    (output / "index.html").write_text(
        template.replace("__GALLERY_DATA__", encoded), encoding="utf-8"
    )
