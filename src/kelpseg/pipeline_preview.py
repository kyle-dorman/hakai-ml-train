"""Offline review of the selected real training augmentation pipeline."""

import csv
import logging
from pathlib import Path

import albumentations as A

from kelpseg.augmentation_display import write_display_views, write_viewer
from kelpseg.augmentation_panels import display_limits
from kelpseg.augmentation_pipeline import build_training_augmentation, pipeline_states
from kelpseg.augmentation_preview import load_preview_samples, preview_metadata
from kelpseg.prepare.chip import _write_json
from kelpseg.prepare.splits import check_split_output

logger = logging.getLogger(__name__)


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
