"""Bounded training-only galleries; no model imports or production policy."""

import csv
import json
import logging
from pathlib import Path

import albumentations as A

from kelpseg.augmentation_display import write_display_views, write_viewer
from kelpseg.augmentation_inputs import select_preview_windows
from kelpseg.augmentation_panels import (
    DISPLAY_CEILING,
    closeup_window,
    display_limits,
    render_panel,
)
from kelpseg.augmentation_trials import individual_trials
from kelpseg.augmentations import NATIVE_SCALE
from kelpseg.chips import load_chip
from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.chip import _write_json
from kelpseg.prepare.splits import check_split_output
from kelpseg.preprocessing import BAND_NAMES, CLIP_VALUE, MEAN, STD

logger = logging.getLogger(__name__)


def load_preview_samples(chips, assignments, variant, positive_samples, seed):
    """Load only selected native training payloads, with paired frozen close-ups."""
    declaration = json.loads((chips / "recipe.json").read_text())
    names = tuple(declaration["source_band_names"])
    if names != BAND_NAMES:
        raise PreparationError(
            "Preview requires the declared native Planet eight-band collection; select spectral views from that collection."
        )
    rows = select_preview_windows(chips, assignments, variant, positive_samples, seed)
    loaded = []
    for row in rows:
        logger.info(
            "Loading training preview %s: %s", row["preview_name"], row["payload"]
        )
        chip = load_chip(row["payload"], names, chip_size=declaration["chip_size"])
        if chip["label"] is None:
            raise PreparationError(
                f"Preview needs mapped training labels: {row['payload']}"
            )
        valid = chip["valid_mask"]
        loaded.append(
            dict(
                chip,
                row=row,
                valid=valid,
                closeup=closeup_window(chip["label"]),
                preview_name=row["preview_name"],
                background_control=row["background_control"],
            )
        )
    return loaded


def preview_metadata(chips, assignments, variant, seed, positive_samples, limits):
    """Keep input domain, fixed display and exact model preprocessing shared."""
    return {
        "purpose": "Training-only stock Albumentations preview for user review.",
        "scope": "baseline/train; backgrounds are diagnostic controls, ineligible for training",
        "chips": str(chips),
        "assignments": str(Path(assignments).expanduser().resolve()),
        "variant": variant,
        "albumentations_version": A.__version__,
        "seed": seed,
        "positive_samples": positive_samples,
        "augmentation_domain": {
            "input": "native uint16 converted to float32 / 65535",
            "native_scale": NATIVE_SCALE,
            "stock_clipping": "pixel transforms clip to [0,1] where implemented; raw-zero lower clipping",
            "spatial_filters": "stock kernels see zero nodata/padding; no custom mask normalization",
            "output": "restore raw units and zero invalid fill, then final model cap/normalization",
        },
        "normalization": {
            "band_names": BAND_NAMES,
            "mean": MEAN,
            "std": STD,
            "clip_value": CLIP_VALUE,
            "reference": "kelp-positive with-BC training, including overlap",
        },
        "display": {
            "raw_minimum": 0,
            "raw_ceiling": DISPLAY_CEILING,
            "limits": limits.tolist(),
            "origin": "user-requested fixed raw 0–2000 display only; same for every example and trial",
            "display_clips_to_0_1_only": True,
        },
        "samples": [],
    }


def preview_augmentations(
    chips, assignments, variant, output, *, seed: int = 33, positive_samples: int = 14
) -> Path:
    """Render actual stock classes; native trial settings live in augmentation_trials.py."""
    output = check_split_output(output)
    chips = Path(chips).expanduser().resolve()
    loaded = load_preview_samples(chips, assignments, variant, positive_samples, seed)
    limits = display_limits(loaded)
    work = output.with_name(f".{output.name}.incomplete")
    work.mkdir()
    metadata = preview_metadata(
        chips, assignments, variant, seed, positive_samples, limits
    )
    metadata["trial_settings"] = (
        "kelpseg/augmentation_trials.py: literal native library constructors"
    )
    records = []
    for sample in loaded:
        key = sample["preview_name"]
        folder = work / key
        folder.mkdir()
        views_folder = folder / "views"
        views_folder.mkdir()
        record = {
            "preview_name": key,
            "background_control": sample["background_control"],
            "parameters": f"{key}/parameters.json",
            "window": sample["row"],
            "true_height": sample["true_height"],
            "true_width": sample["true_width"],
            "padding": sample["padding"],
            "closeup": sample["closeup"],
            "native_valid_pixels": int(sample["valid"].sum()),
            "nodata_pixels": int(sample["nodata_mask"].sum()),
            "families": [],
        }
        originals = {}
        for family, states in individual_trials(sample, seed):
            logger.info(
                "Rendering %s / %s (%d isolated settings)", key, family, len(states)
            )
            relative = f"{key}/{family}.png"
            render_panel(work / relative, sample, family, states, limits)
            assets = write_display_views(
                views_folder, sample, family, states, limits, originals
            )
            record["families"].append(
                {
                    "family": family,
                    "panel": relative,
                    "states": [
                        {
                            "title": s["title"],
                            "parameters": s["parameters"],
                            "metrics": s["metrics"],
                            "assets": view,
                            "closeup": s["closeup"],
                            "is_identity": s["is_identity"],
                            "preview_default": s["preview_default"],
                        }
                        for s, view in zip(states, assets, strict=True)
                    ],
                }
            )
        _write_json(folder / "parameters.json", record)
        metadata["samples"].append(
            {
                "preview_name": key,
                "parameters": f"{key}/parameters.json",
                "window": sample["row"],
            }
        )
        records.append(record)
    rows = [sample["row"] for sample in loaded]
    with (work / "selected_windows.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _write_json(work / "gallery.json", metadata)
    write_viewer(work, metadata, records)
    work.rename(output)
    logger.info("Complete gallery: %s", output / "index.html")
    return output
