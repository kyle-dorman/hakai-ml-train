"""Offline review of the selected real training augmentation pipeline."""

import csv
import logging
from pathlib import Path

import albumentations as A
import numpy as np

from kelpseg.augmentation_debug.display import write_display_views, write_viewer
from kelpseg.augmentation_debug.panels import display_limits
from kelpseg.augmentation_debug.preview import load_preview_samples, preview_metadata
from kelpseg.augmentation_debug.trials import value_metrics
from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.augmentations import apply_augmentation
from kelpseg.prepare.chip import _write_json
from kelpseg.prepare.splits import check_split_output
from kelpseg.preprocessing import cap_raw

logger = logging.getLogger(__name__)


def pipeline_states(sample: dict, seed: int = 33) -> list[dict]:
    """Return source, the same sampled D4 reference, and actual full output.

    Every full draw records the real stock operation order and parameters;
    source and D4 reference explain which changes came from geometry alone.
    """
    image, label, valid = sample["image"], sample["label"], sample["valid"]
    names, crop = sample["band_names"], sample["closeup"]
    full = apply_augmentation(
        build_training_augmentation(seed), image, label, valid, seed
    )
    full_parameters = full[3]
    group = full_parameters["applied"][0][1]["group_element"]
    d4 = A.D4(p=1)
    reference = apply_augmentation(
        d4, image, label, valid, seed, {"group_element": group}
    )
    footprint = np.zeros(label.shape, dtype=np.uint8)
    top, left, bottom, right = crop
    footprint[top:bottom, left:right] = 1
    moved = d4.apply_to_mask(footprint, group_element=group)
    ys, xs = np.where(moved)
    moved_crop = int(ys.min()), int(xs.min()), int(ys.max()) + 1, int(xs.max()) + 1

    trace = []
    for class_name, parameters in full_parameters["applied"]:
        entry = {"class": class_name, "parameters": parameters}
        if class_name == "ChannelDropout":
            entry["dropped_bands"] = [
                names[index] for index in parameters["channels_to_drop"]
            ]
        trace.append(entry)
    full_parameters["operation_trace"] = trace

    def state(title, result, closeup, *, identity=False):
        raw, targets, support, parameters = result
        return dict(
            title=title,
            parameters=parameters,
            image=raw,
            label=targets,
            valid=support,
            display=cap_raw(raw, support),
            metrics=value_metrics(raw, targets, support, names),
            closeup=closeup,
            is_identity=identity,
            preview_default=False,
        )

    original = apply_augmentation(A.NoOp(p=1), image, label, valid, seed)
    return [
        state("Source original", original, crop, identity=True),
        state(f"D4 reference: {group}", reference, moved_crop, identity=group == "e"),
        state("D4 + two sampled extras", full, moved_crop),
    ]


def preview_pipeline(
    chips,
    assignments,
    variant,
    output,
    *,
    seed: int = 33,
    positive_samples: int = 14,
    draws: int = 8,
) -> Path:
    """Show seeded real pipeline calls, each beside its same-D4-only reference.

    The stock factory is the recipe; save its native serialized form with the
    gallery. Seeds identify draws for inspection, not representative evaluation
    samples. Future training creates one pipeline and advances its RNG normally.
    """
    output = check_split_output(output)
    if type(draws) is not int or not 1 <= draws <= 32:
        raise ValueError("draws must be an integer in 1..32.")
    chips = Path(chips).expanduser().resolve()
    loaded = load_preview_samples(chips, assignments, variant, positive_samples, seed)
    limits = display_limits(loaded)
    metadata = preview_metadata(
        chips, assignments, variant, seed, positive_samples, limits
    )
    metadata.update(
        purpose="Selected D4 + SomeOf(2) pipeline; combined outputs await user review.",
        pipeline_recipe=A.to_dict(build_training_augmentation(seed=seed)),
        draws_per_example=draws,
        seed_rule="base seed + example index * draws per example + draw index",
        reference="Same sampled D4 only; optional source-original comparison",
    )
    work = output.with_name(f".{output.name}.incomplete")
    work.mkdir()
    _write_json(work / "pipeline.json", metadata["pipeline_recipe"])
    records = []
    for sample_index, sample in enumerate(loaded):
        key = sample["preview_name"]
        folder = work / key
        folder.mkdir()
        views = folder / "views"
        views.mkdir()
        record = {
            "preview_name": key,
            "background_control": sample["background_control"],
            "parameters": f"{key}/parameters.json",
            "window": sample["row"],
            "band_names": sample["band_names"],
            "true_height": sample["true_height"],
            "true_width": sample["true_width"],
            "padding": sample["padding"],
            "closeup": sample["closeup"],
            "native_valid_pixels": int(sample["valid"].sum()),
            "nodata_pixels": int(sample["nodata_mask"].sum()),
            "draws": [],
        }
        originals = {}
        for draw_index in range(draws):
            draw_seed = seed + sample_index * draws + draw_index
            logger.info(
                "Rendering %s / pipeline draw %d (seed %d)",
                key,
                draw_index + 1,
                draw_seed,
            )
            states = pipeline_states(sample, seed=draw_seed)
            assets = write_display_views(
                views, sample, f"draw_{draw_index + 1:02d}", states, limits, originals
            )
            record["draws"].append(
                {
                    "seed": draw_seed,
                    "states": [
                        {
                            "title": state["title"],
                            "parameters": state["parameters"],
                            "metrics": state["metrics"],
                            "assets": asset,
                            "closeup": state["closeup"],
                            "is_identity": state["is_identity"],
                        }
                        for state, asset in zip(states, assets, strict=True)
                    ],
                }
            )
        _write_json(folder / "parameters.json", record)
        metadata["samples"].append(
            {
                "preview_name": key,
                "parameters": record["parameters"],
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
    write_viewer(work, metadata, records, template_name="pipeline_viewer.html")
    work.rename(output)
    logger.info("Complete pipeline gallery: %s", output / "index.html")
    return output
