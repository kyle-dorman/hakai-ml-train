"""Independent post-training diagnostics for the existing validation chip scope."""

import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from rasterio.crs import CRS

from kelpseg.model_bundle import PortableModel, load_model_bundle
from kelpseg.prepare.splits import select_windows
from kelpseg.training.visuals import fixed_validation_samples
from kelpseg.validation_report.metrics import (
    COUNT_KEYS,
    analyze,
    boundary_scores,
    confusion,
    patch_summary,
    scores,
)
from kelpseg.validation_report.selection import training_sample
from kelpseg.validation_report.views import diagnostic_plot, example, write_html

logger = logging.getLogger(__name__)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write flat records to path with first-row column order; return nothing.

    Rows must share keys. Empty input writes an empty file. The caller owns
    output-directory creation and overwrite checks.
    """
    with path.open("w", newline="") as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def pooled(
    rows: list[dict[str, Any]], group_keys: tuple[str, ...], sum_keys: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Group flat records by group_keys and sum numeric sum_keys fields.

    Return one new record per group in encounter order. Pool counts before
    computing ratios; input rows are not modified.
    """
    groups = {}
    for row in rows:
        key = tuple(row[name] for name in group_keys)
        if key not in groups:
            groups[key] = {name: row[name] for name in group_keys}
            groups[key].update({name: 0 for name in sum_keys})
        for name in sum_keys:
            groups[key][name] += row[name]
    return list(groups.values())


def source_canvas(
    rows: list[dict[str, Any]],
    model: PortableModel,
    bands: list[str],
    output: Path,
    selected: list[str],
    examples: list[dict[str, str]],
) -> tuple[NDArray[np.int8], NDArray[np.float32], int, int, list[dict[str, Any]]]:
    """Predict disjoint windows for one source and join them in source coordinates.

    rows contains selected manifest records; bands names native image channels.
    model predicts each payload. Return labels, probabilities, canvas top/left
    offsets and background-only chip counts. Gaps remain -100/NaN.
    Selected payload paths produce figures under output/examples; their relative
    paths and captions are appended to examples. Input imagery is never changed.
    """
    top = min(int(row["original_row"]) for row in rows)
    left = min(int(row["original_col"]) for row in rows)
    bottom = max(int(row["original_row"]) + int(row["height"]) for row in rows)
    right = max(int(row["original_col"]) + int(row["width"]) for row in rows)
    labels = np.full((bottom - top, right - left), -100, dtype=np.int8)
    probabilities = np.full(labels.shape, np.nan, dtype=np.float32)
    background = []
    for row in rows:
        with np.load(row["payload"]) as arrays:
            image, label = arrays["image"], arrays["label"].copy()
        probability = model.predict_probabilities(image, bands)
        label[~np.isfinite(probability)] = -100
        y, x = int(row["original_row"]) - top, int(row["original_col"]) - left
        h, w = label.shape
        labels[y : y + h, x : x + w] = label
        probabilities[y : y + h, x : x + w] = probability
        valid = label != -100
        if not (label == 1).any():
            background.append(
                dict(
                    source_id=row["source_id"],
                    region=row["region"],
                    payload=str(row["payload"]),
                    original_row=y + top,
                    original_col=x + left,
                    **confusion(label == 1, probability >= 0.5, valid),
                )
            )
        key = str(row["payload"])
        if key in selected:
            filename = f"examples/{selected.index(key):02d}.png"
            caption = f"{row['original_tiff']} | region {row['region']} | {row['acquisition_date']} | r{y + top} c{x + left}"
            example(output / filename, image, bands, label, probability, caption)
            examples.append(dict(file=filename, caption=caption))
    return labels, probabilities, top, left, background


def validation_report(
    run_directory: str | Path,
    output_directory: str | Path,
    *,
    device: str = "cpu",
    split: str = "val",
    sources_per_region: int = 3,
    seed: int = 42,
) -> Path:
    """Write validation diagnostics for a completed run and return report.html.

    run_directory supplies run.json and the selected model bundle; output_directory
    must not exist. device selects CPU or CUDA inference. Writes HTML, CSV, JSON
    and false-color PNGs. split="train" evaluates a fixed source sample with the
    same disjoint grid and inference; sources_per_region and seed control it.
    The default split="val" reads all validation payloads. No test payloads are read.
    Invalid run identities,
    incomplete runs and unsupported imagery raise ValueError. Does not train,
    alter the run or select a new checkpoint/threshold.
    """
    run_directory, output = Path(run_directory), Path(output_directory)
    if output.exists():
        raise ValueError(
            f"Report output already exists: {output}. Choose a fresh directory."
        )
    run = json.loads((run_directory / "run.json").read_text())
    if run["status"] != "complete":
        raise ValueError(
            "Validation report requires a completed run; leave running training untouched."
        )
    metadata = json.loads((run_directory / "model/model.json").read_text())
    if metadata["run_id"] != run["run_id"]:
        raise ValueError("Model bundle and run.json have different run identities.")
    if split not in ("val", "train"):
        raise ValueError("Report split must be val or train; test is excluded.")
    if split == "train":
        rows = training_sample(run, sources_per_region, seed)
    else:
        rows = [
            row
            for row in select_windows(
                run["chips"],
                run["assignments"],
                experiment=run["experiment"],
                variant=run["variant"],
            )
            if row["split"] == "val"
        ]
    if not rows:
        raise ValueError("No report chips selected.")
    bands = json.loads((Path(run["chips"]) / "recipe.json").read_text())[
        "source_band_names"
    ]
    if not {"nir", "red", "green"}.issubset(bands):
        raise ValueError(
            "False-color reports require native nir, red and green imagery."
        )
    for row in rows:
        crs = CRS.from_string(row["crs"])
        if not crs.is_projected or crs.linear_units != "metre":
            raise ValueError(
                "Area reporting requires projected imagery with metre units."
            )
    model = load_model_bundle(run_directory / "model", device=device)
    output.mkdir(parents=True)
    (output / "examples").mkdir()
    write_csv(
        output / "selected_windows.csv",
        [
            {
                key: row[key]
                for key in (
                    "dataset_id",
                    "release_id",
                    "original_tiff",
                    "region",
                    "acquisition_date",
                    "source_key",
                    "original_row",
                    "original_col",
                    "height",
                    "width",
                    "payload",
                    "split",
                )
            }
            for row in rows
        ],
    )
    selected = fixed_validation_samples(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[(row["dataset_id"], row["release_id"], row["original_tiff"])].append(row)
    sources = []
    patches = []
    sweeps = []
    boundaries = []
    zones = []
    histograms = []
    background = []
    examples = []
    for number, (key, windows) in enumerate(sorted(groups.items()), 1):
        logger.info(
            "Report %s source %d/%d: %s (%d chips)",
            split,
            number,
            len(groups),
            key[2],
            len(windows),
        )
        labels, probabilities, top, left, bg = source_canvas(
            windows, model, bands, output, selected, examples
        )
        result = analyze(labels, probabilities)
        first = windows[0]
        identity = dict(
            dataset_id=key[0],
            release_id=key[1],
            original_tiff=key[2],
            region=first["region"],
            acquisition_date=first["acquisition_date"],
        )
        a, b, _, d, e, _ = first["transform"][:6]
        pixel_area = abs(a * e - b * d)
        counts = result["counts"]
        sources.append(
            dict(
                **identity,
                chips=len(windows),
                retained_window_pixels=sum(
                    int(r["height"]) * int(r["width"]) for r in windows
                ),
                **scores(counts),
                labeled_area_m2=(counts["tp"] + counts["fn"]) * pixel_area,
                predicted_area_m2=(counts["tp"] + counts["fp"]) * pixel_area,
                area_bias_m2=(counts["fp"] - counts["fn"]) * pixel_area,
            )
        )
        for patch in result["patches"]:
            patch.update(
                row=patch["row"] + top,
                col=patch["col"] + left,
                area_m2=patch["pixels"] * pixel_area,
            )
            patches.append(dict(**identity, **patch))
        for target, name in [
            (sweeps, "sweep"),
            (boundaries, "boundaries"),
            (zones, "zones"),
            (histograms, "histograms"),
        ]:
            target.extend(dict(**identity, **item) for item in result[name])
        background.extend(bg)
    area_keys = ("labeled_area_m2", "predicted_area_m2", "area_bias_m2")
    regions = [
        dict(
            region=row["region"],
            **scores({k: row[k] for k in COUNT_KEYS}),
            **{k: row[k] for k in area_keys},
        )
        for row in pooled(sources, ("region",), (*COUNT_KEYS, *area_keys))
    ]
    sweep = [
        dict(threshold=row["threshold"], **scores({k: row[k] for k in COUNT_KEYS}))
        for row in pooled(sweeps, ("threshold",), COUNT_KEYS)
    ]
    boundary_keys = (
        "eligible_pixels",
        "label_boundary_pixels",
        "predicted_boundary_pixels",
        "matched_prediction_pixels",
        "matched_label_pixels",
    )
    boundary_results = [
        boundary_scores(row)
        for row in pooled(boundaries, ("tolerance_pixels",), boundary_keys)
    ]
    zone_results = [
        dict(zone=row["zone"], **scores({k: row[k] for k in COUNT_KEYS}))
        for row in pooled(zones, ("zone",), COUNT_KEYS)
    ]
    sizes = patch_summary(patches)
    summary = dict(
        run_id=run["run_id"],
        model_bundle=str((run_directory / "model").resolve()),
        chip_root=run["chips"],
        assignments=run["assignments"],
        device=device,
        checkpoint_epoch=metadata["checkpoint_epoch"] + 1,
        weight_kind=metadata["weight_kind"],
        inference_precision="float32",
        threshold=0.5,
        sources=len(sources),
        chips=len(rows),
        split=split,
        sample_seed=seed if split == "train" else None,
        sources_per_region=sources_per_region if split == "train" else None,
        scope=f"Observed disjoint {split} windows; not full-TIFF or test scoring",
        retained_window_pixels=sum(r["retained_window_pixels"] for r in sources),
        truncated_patches=sum(r["truncated"] for r in patches),
        patch_connectivity=8,
        boundary_distance="Euclidean pixels",
        global_scores=scores({k: sum(r[k] for r in sources) for k in COUNT_KEYS}),
    )
    summary["global"] = summary.pop("global_scores")
    summary["global"].update({k: sum(row[k] for row in sources) for k in area_keys})
    summary["background_chips"] = dict(
        chips=len(background),
        chips_with_false_positives=sum(row["fp"] > 0 for row in background),
        **scores({k: sum(row[k] for row in background) for k in COUNT_KEYS}),
    )
    histogram_results = pooled(histograms, ("label", "lower", "upper"), ("pixels",))
    diagnostic_plot(output / "diagnostics.png", sweep, histogram_results)
    for name, data in [
        ("sources", sources),
        ("regions", regions),
        ("patches", patches),
        ("patch_sizes", sizes),
        ("thresholds", sweep),
        ("boundaries", boundary_results),
        ("zones", zone_results),
        ("background_chips", background),
        ("source_thresholds", sweeps),
        ("source_boundaries", boundaries),
        ("probability_histograms", histogram_results),
    ]:
        write_csv(output / f"{name}.csv", data)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )
    write_html(
        output,
        summary,
        regions,
        sweep,
        boundary_results,
        zone_results,
        sizes,
        sorted(examples, key=lambda x: x["file"]),
    )
    logger.info("Validation report complete: %s", output / "report.html")
    return output / "report.html"
