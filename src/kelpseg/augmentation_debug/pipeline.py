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
from kelpseg.augmentations import NATIVE_SCALE, apply_augmentation
from kelpseg.prepare.chip import _write_json
from kelpseg.prepare.splits import check_split_output
from kelpseg.preprocessing import cap_raw

logger = logging.getLogger(__name__)


def pipeline_states(sample: dict, seed: int = 33) -> list[dict]:
    """Return source, sampled D4, sampled D4+Affine, and actual full output.

    Replay the stock geometry with its actual sampled parameters, without a
    second random draw. Move the close-up footprint through those same kernels.
    """
    image, label, valid = sample["image"], sample["label"], sample["valid"]
    names, crop = sample["band_names"], sample["closeup"]
    pipeline = build_training_augmentation(seed)
    full = apply_augmentation(pipeline, image, label, valid, seed)
    full_parameters = full[3]
    d4, affine = pipeline.transforms[:2]
    group = d4.get_applied_params()["group_element"]
    affine_parameters = affine.get_applied_params()

    trace = []
    for class_name, parameters in full_parameters["applied"]:
        entry = {"class": class_name, "parameters": parameters, "applied": True}
        if class_name == "ChannelDropout":
            entry["dropped_bands"] = [
                names[index] for index in parameters["channels_to_drop"]
            ]
        if class_name == "Affine":
            # Stock parameters expose the matrix, not the sampled translation.
            # Its displacement of the image center reports that shift directly.
            height, width = image.shape[:2]
            center = np.array([(width - 1) / 2, (height - 1) / 2, 1])
            shifted = affine_parameters["matrix"] @ center
            entry["center_shift_pixels"] = {
                "x": float(shifted[0] - center[0]),
                "y": float(shifted[1] - center[1]),
            }
        trace.append(entry)
    if not affine_parameters:
        trace.insert(1, {"class": "Affine", "parameters": {}, "applied": False})
    full_parameters["operation_trace"] = trace

    inputs = dict(
        image=image.astype(np.float32) / NATIVE_SCALE,
        mask=label.copy(),
        validity=valid.astype(np.int8),
    )
    d4_result = d4.apply_with_params(d4.get_applied_params(), **inputs)
    geometry_result = (
        affine.apply_with_params(affine_parameters, **d4_result)
        if affine_parameters
        else d4_result
    )

    footprint = np.zeros(label.shape, dtype=np.int8)
    top, left, bottom, right = crop
    footprint[top:bottom, left:right] = 1
    d4_footprint = d4.apply_to_mask(footprint, **d4.get_applied_params())
    geometry_footprint = (
        affine.apply_to_mask(d4_footprint, **affine_parameters)
        if affine_parameters
        else d4_footprint
    )

    def footprint_bounds(footprint):
        ys, xs = np.where(footprint == 1)
        if not len(ys):
            # A crop shifted entirely outside the window has no close-up left.
            return (0, 0, *footprint.shape)
        return int(ys.min()), int(xs.min()), int(ys.max()) + 1, int(xs.max()) + 1

    def geometry_output(result, operations):
        support = result["validity"] == 1
        raw = result["image"].astype(np.float32, copy=True) * NATIVE_SCALE
        raw[~support] = 0
        return raw, result["mask"], support, dict(operation_trace=operations, seed=seed)

    reference = geometry_output(d4_result, trace[:1])
    geometry = geometry_output(geometry_result, trace[:2])
    d4_crop = footprint_bounds(d4_footprint)
    geometry_crop = footprint_bounds(geometry_footprint)

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
        state(f"D4 reference: {group}", reference, d4_crop, identity=group == "e"),
        state(
            "D4 + Affine: " + ("applied" if affine_parameters else "skipped"),
            geometry,
            geometry_crop,
            identity=group == "e" and not affine_parameters,
        ),
        state("D4 + optional Affine + two sampled extras", full, geometry_crop),
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
    """Show actual draws with D4-only and D4+Affine geometry references.

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
        purpose="Selected D4 + Affine(p=0.5) + SomeOf(2) pipeline; geometry and full review.",
        pipeline_recipe=A.to_dict(build_training_augmentation(seed=seed)),
        draws_per_example=draws,
        seed_rule="base seed + example index * draws per example + draw index",
        reference="Source, same D4, same D4+Affine, and full pipeline; no geometry resampling",
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
