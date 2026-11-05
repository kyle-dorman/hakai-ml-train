"""Generate shared source-level diagnostics from saved predictions and labels."""

import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from kelpseg.prediction.selection import fixed_validation_samples
from kelpseg.reporting.canvases import canvases, source_groups
from kelpseg.reporting.examples import write_examples
from kelpseg.reporting.inputs import ReportSettings, read_inputs
from kelpseg.reporting.metrics import (
    COUNT_KEYS,
    analyze,
    boundary_scores,
    confusion,
    patch_summary,
    scores,
)
from kelpseg.reporting.views import diagnostic_plot, write_html

logger = logging.getLogger(__name__)


def write_csv(path: Path, rows: list[dict]) -> None:
    """Publish flat records after processing finishes, retaining stable column order."""
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", newline="") as stream:
        if rows:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    temporary.replace(path)


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


def background_chip_counts(
    canvas: dict, windows: list[dict], threshold: float
) -> list[dict]:
    """Score zero-kelp chip windows independently of qualitative figure selection."""
    source = canvas["source"]
    top, left = int(source["row_offset"]), int(source["col_offset"])
    background = []
    for row in windows:
        y, x = int(row["original_row"]) - top, int(row["original_col"]) - left
        height, width = int(row["height"]), int(row["width"])
        region = np.s_[y : y + height, x : x + width]
        labels, probability = canvas["labels"][region], canvas["probability"][region]
        observed = (labels != -100) & np.isfinite(probability)
        if not (labels[observed] == 1).any():
            background.append(
                dict(
                    source_id=row["source_id"],
                    region=row["region"],
                    payload=row["payload"],
                    original_row=y + top,
                    original_col=x + left,
                    **confusion(labels == 1, probability >= threshold, observed),
                )
            )
    return background


def report(settings: ReportSettings) -> Path:
    """Write shared labeled reports into a fresh directory without model execution.

    Read one original source at a time, retaining its arrays only for scoring and
    bounded figures. CSV tables and final completion metadata publish after all
    sources succeed. Inputs and referenced prediction artifacts are unchanged.
    """
    output = settings.output
    if output.exists():
        raise ValueError(
            f"Report output already exists: {output}. Choose a fresh directory."
        )
    metadata, rows, windows = read_inputs(settings)
    scope, split = metadata["scope"], metadata["split"]
    threshold = metadata["model"]["threshold"]
    groups = source_groups(rows)
    selected = (
        set(fixed_validation_samples(windows)[: settings.max_examples])
        if scope == "chip_disjoint"
        else set()
    )
    output.mkdir(parents=True)
    (output / "examples").mkdir()
    sources, patches, sweeps, boundaries, zones, histograms = [], [], [], [], [], []
    background, examples = [], []
    seen_regions: set[str] = set()
    background_sources: set[str] = set()
    for index, (canvas, selected_windows) in enumerate(
        canvases(rows, windows, scope, settings), 1
    ):
        source = canvas["source"]
        logger.info(
            "Report %s source %d/%d: %s",
            split,
            index,
            len(groups),
            source.get("original_source_id") or source["source_key"],
        )
        labels, probabilities = canvas["labels"], canvas["probability"]
        result = analyze(
            labels, probabilities, threshold=threshold, include_sweep=split != "test"
        )
        identity = dict(
            source_keys=source["source_keys"],
            band_names=source["band_names"],
            row_offset=source.get("row_offset", ""),
            col_offset=source.get("col_offset", ""),
            dataset_id=source.get("dataset_id", ""),
            release_id=source.get("release_id", ""),
            original_tiff=source.get("original_source_id", ""),
            region=source.get("region_id", ""),
            acquisition_date=source.get("acquisition_date", ""),
        )
        pixel_area = abs(canvas["transform"].determinant)
        counts = result["counts"]
        native_valid, footprint = canvas["valid"], canvas["footprint"]
        finite, known = np.isfinite(probabilities), labels != -100
        coverage = dict(
            total_pixels=int(footprint.sum()),
            canvas_pixels=int(footprint.size),
            geometric_gap_pixels=int((~footprint).sum()),
            valid_pixels=int(native_valid.sum()),
            nodata_pixels=int((footprint & ~native_valid).sum()),
            predicted_valid_pixels=int((native_valid & finite).sum()),
            uncovered_valid_pixels=int((native_valid & ~finite).sum()),
            ignored_valid_pixels=int((native_valid & ~known).sum()),
            covered_ignored_pixels=int((native_valid & finite & ~known).sum()),
            scoreable_pixels=int((native_valid & finite & known).sum()),
        )
        sources.append(
            dict(
                **identity,
                scope=scope,
                split=split,
                chips=len(selected_windows) if scope == "chip_disjoint" else 0,
                retained_window_pixels=int(footprint.sum()),
                **coverage,
                **scores(counts),
                scoreable_area_m2=coverage["scoreable_pixels"] * pixel_area,
                labeled_area_m2=(counts["tp"] + counts["fn"]) * pixel_area,
                predicted_area_m2=(counts["tp"] + counts["fp"]) * pixel_area,
                area_bias_m2=(counts["fp"] - counts["fn"]) * pixel_area,
                false_positive_area_m2=counts["fp"] * pixel_area,
                false_negative_area_m2=counts["fn"] * pixel_area,
            )
        )
        top, left = (
            int(source.get("row_offset") or 0),
            int(source.get("col_offset") or 0),
        )
        for patch in result["patches"]:
            patch.update(
                row=patch["row"] + top,
                col=patch["col"] + left,
                area_m2=patch["pixels"] * pixel_area,
            )
            patches.append(dict(**identity, **patch))
        for target, name in (
            (sweeps, "sweep"),
            (boundaries, "boundaries"),
            (zones, "zones"),
            (histograms, "histograms"),
        ):
            target.extend(dict(**identity, **item) for item in result[name])
        if scope == "chip_disjoint":
            background.extend(
                background_chip_counts(canvas, selected_windows, threshold)
            )
        write_examples(
            canvas,
            selected_windows,
            selected,
            scope,
            output,
            examples,
            threshold,
            settings.max_examples,
            seen_regions,
            background_sources,
        )
    area_keys = (
        "scoreable_area_m2",
        "labeled_area_m2",
        "predicted_area_m2",
        "area_bias_m2",
        "false_positive_area_m2",
        "false_negative_area_m2",
    )
    coverage_keys = tuple(coverage)
    regions = [
        dict(
            region=row["region"],
            **scores({k: row[k] for k in COUNT_KEYS}),
            **{k: row[k] for k in (*area_keys, *coverage_keys)},
        )
        for row in pooled(
            sources, ("region",), (*COUNT_KEYS, *area_keys, *coverage_keys)
        )
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
    model = metadata["model"]
    summary = dict(
        status="complete",
        run_id=model.get("run_id", metadata.get("run_id", "unknown")),
        model=model,
        predictions=str(settings.predictions),
        checkpoint_epoch=model.get("checkpoint_epoch", -1) + 1,
        weight_kind=model.get("weight_kind", "unknown"),
        inference_precision="float32",
        threshold=threshold,
        sources=len(sources),
        chips=len(windows) if scope == "chip_disjoint" else 0,
        split=split,
        scope=scope,
        membership={
            k: metadata.get(k, metadata.get("recipe", {}).get(k))
            for k in ("external_scope", "assignments", "experiment", "variant")
        },
        sample_seed=metadata.get("recipe", {}).get("seed")
        if split == "train"
        else None,
        sources_per_region=metadata.get("recipe", {}).get("sources_per_region")
        if split == "train"
        else None,
        retained_window_pixels=sum(r["retained_window_pixels"] for r in sources),
        truncated_patches=sum(r["truncated"] for r in patches),
        patch_connectivity=8,
        boundary_distance="Euclidean pixels",
        coverage={k: sum(r[k] for r in sources) for k in coverage_keys},
        example_selection="Fixed positive/first chip per region plus up to two background chips"
        if scope == "chip_disjoint"
        else "First source per region plus up to two zero-kelp sources; 512-pixel window centered on first observed kelp pixel, or first observed pixel if no kelp",
        global_scores=scores({k: sum(r[k] for r in sources) for k in COUNT_KEYS}),
    )
    summary["global"] = summary.pop("global_scores")
    summary["global"].update({k: sum(r[k] for r in sources) for k in area_keys})
    summary["background_chips"] = (
        dict(
            chips=len(background),
            chips_with_false_positives=sum(r["fp"] > 0 for r in background),
            **scores({k: sum(r[k] for r in background) for k in COUNT_KEYS}),
        )
        if scope == "chip_disjoint"
        else None
    )
    histogram_results = pooled(histograms, ("label", "lower", "upper"), ("pixels",))
    diagnostic_plot(output / "diagnostics.png", sweep, histogram_results, threshold)
    input_sources = [
        dict(row, probability=str(settings.predictions / row["probability"]))
        for row in rows
    ]
    for name, data in (
        ("input_sources", input_sources),
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
        ("selected_windows", windows),
        ("examples", examples),
    ):
        write_csv(output / f"{name}.csv", data)
    write_html(
        output, summary, regions, sweep, boundary_results, zone_results, sizes, examples
    )
    resolved = {
        k: str(v) if isinstance(v, Path) else v for k, v in asdict(settings).items()
    }
    for name, document in (("settings", resolved), ("summary", summary)):
        temporary = output / f"{name}.tmp"
        temporary.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")
        temporary.replace(output / f"{name}.json")
    logger.info("Report complete: %s", output / "report.html")
    return output / "report.html"
