#!/usr/bin/env python3
"""Compare temporal-baseline and LORO accuracy on matching source TIFFs."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.planet8b import (  # noqa: E402
    EVALUATION_SCOPES,
    SELECTED_NONOVERLAP_SCOPE,
)
from src.evaluation.planet8b_comparison import (  # noqa: E402
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    ComparisonError,
    compare_suite,
    read_csv,
    sha256_file,
)

DEFAULT_DATASET_ROOT = Path("/home/sky/data/planet8b_all_regions_1024_512_v2")
DEFAULT_INVENTORY = Path(
    "/home/sky/experiments/planet8b-loro-v3/predictions/suite_inventory.csv"
)
DEFAULT_OUTPUT_ROOT = Path(
    "/home/sky/experiments/planet8b-loro-v3/comparisons/matched_tiffs_v1"
)
TABLE_NAMES = [
    "matched_tiff_metrics",
    "matched_tiff_exclusions",
    "paired_region_summary",
    "full_region_loro_summary",
    "pooled_confusion_summary",
]


def _table_names(result: dict[str, Any]) -> list[str]:
    return [
        *TABLE_NAMES,
        *(["coverage_comparison"] if "coverage_comparison" in result else []),
    ]


def _coverage_comparison(
    current_inventory: Path, historical_inventory: Path
) -> list[dict[str, Any]]:
    current = {row["run_key"]: row for row in read_csv(current_inventory)}
    historical = {row["run_key"]: row for row in read_csv(historical_inventory)}
    if set(current) != set(historical):
        raise ComparisonError("Historical/current coverage run keys differ")
    output = []
    for run_key in current:
        current_scope = current[run_key].get(
            "evaluation_scope", SELECTED_NONOVERLAP_SCOPE
        )
        historical_scope = historical[run_key].get(
            "evaluation_scope", SELECTED_NONOVERLAP_SCOPE
        )
        same_scope = current_scope == historical_scope
        current_rows = read_csv(
            Path(current[run_key]["output_path"]) / "tiff_metrics.csv"
        )
        historical_rows = read_csv(
            Path(historical[run_key]["output_path"]) / "tiff_metrics.csv"
        )
        current_by_source = {row["source_tiff_id"]: row for row in current_rows}
        historical_by_source = {row["source_tiff_id"]: row for row in historical_rows}
        if len(current_by_source) != len(current_rows) or len(
            historical_by_source
        ) != len(historical_rows):
            raise ComparisonError(f"{run_key}: duplicate source in coverage comparison")
        shared = set(current_by_source) & set(historical_by_source)
        regressions = [
            source
            for source in shared
            if int(current_by_source[source]["covered_pixel_count"])
            < int(historical_by_source[source]["covered_pixel_count"])
        ]
        if regressions:
            raise ComparisonError(
                f"{run_key}: source coverage regressed: {regressions}"
            )
        if same_scope:
            if set(current_by_source) != set(historical_by_source):
                raise ComparisonError(
                    f"{run_key}: same-scope source membership changed"
                )
            if (
                current[run_key]["test_chip_count"]
                != historical[run_key]["test_chip_count"]
            ):
                raise ComparisonError(f"{run_key}: same-scope chip count changed")
            current_chips = {
                row["chip_id"]
                for row in read_csv(
                    Path(current[run_key]["output_path"]) / "chip_diagnostics.csv",
                    {"chip_id"},
                )
            }
            historical_chips = {
                row["chip_id"]
                for row in read_csv(
                    Path(historical[run_key]["output_path"]) / "chip_diagnostics.csv",
                    {"chip_id"},
                )
            }
            if current_chips != historical_chips:
                raise ComparisonError(f"{run_key}: same-scope chip membership changed")
            stable_fields = (
                "region_id",
                "acquisition_date",
                "ignored_pixel_count",
                "uncovered_pixel_count",
                "covered_pixel_count",
                "scored_pixel_count",
                "total_source_pixel_count",
            )
            for source in current_by_source:
                current_row = current_by_source[source]
                historical_row = historical_by_source[source]
                if (
                    any(
                        current_row[field] != historical_row[field]
                        for field in stable_fields
                    )
                    or (
                        int(current_row["true_positive"])
                        + int(current_row["false_negative"])
                        != int(historical_row["true_positive"])
                        + int(historical_row["false_negative"])
                    )
                    or (
                        int(current_row["true_negative"])
                        + int(current_row["false_positive"])
                        != int(historical_row["true_negative"])
                        + int(historical_row["false_positive"])
                    )
                ):
                    raise ComparisonError(
                        f"{run_key}/{source}: same-scope coverage or label truth changed"
                    )
        old_covered = sum(int(row["covered_pixel_count"]) for row in historical_rows)
        new_covered = sum(int(row["covered_pixel_count"]) for row in current_rows)
        old_total = sum(int(row["total_source_pixel_count"]) for row in historical_rows)
        new_total = sum(int(row["total_source_pixel_count"]) for row in current_rows)
        shared_old = sum(
            int(historical_by_source[source]["covered_pixel_count"])
            for source in shared
        )
        shared_new = sum(
            int(current_by_source[source]["covered_pixel_count"]) for source in shared
        )
        output.append(
            {
                "run_key": run_key,
                "historical_evaluation_scope": historical_scope,
                "current_evaluation_scope": current_scope,
                "same_scope_membership_verified": same_scope,
                "historical_tiff_count": len(historical_rows),
                "current_tiff_count": len(current_rows),
                "added_tiff_count": len(
                    set(current_by_source) - set(historical_by_source)
                ),
                "historical_chip_count": int(historical[run_key]["test_chip_count"]),
                "current_chip_count": int(current[run_key]["test_chip_count"]),
                "added_chip_count": int(current[run_key]["test_chip_count"])
                - int(historical[run_key]["test_chip_count"]),
                "historical_covered_pixel_count": old_covered,
                "current_covered_pixel_count": new_covered,
                "covered_pixel_gain": new_covered - old_covered,
                "historical_coverage_fraction": old_covered / old_total,
                "current_coverage_fraction": new_covered / new_total,
                "shared_tiff_count": len(shared),
                "shared_historical_covered_pixel_count": shared_old,
                "shared_current_covered_pixel_count": shared_new,
                "shared_covered_pixel_gain": shared_new - shared_old,
                "shared_source_coverage_regression_count": 0,
                "current_uncovered_pixel_count": sum(
                    int(row["uncovered_pixel_count"]) for row in current_rows
                ),
            }
        )
    return output


def _write_csv(
    path: Path, rows: list[dict[str, Any]], empty_fields: list[str] | None = None
) -> None:
    """Write one deterministic table into the unpublished staging root."""
    if not rows and empty_fields is None:
        raise ComparisonError(f"Refusing to write an empty required table: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]) if rows else empty_fields,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def _plot_scatter(table: Path, destination: Path) -> None:
    rows = read_csv(table)
    regions = sorted({row["region_id"] for row in rows})
    colors = plt.get_cmap("tab20")(np.linspace(0, 1, len(regions)))
    figure, axis = plt.subplots(figsize=(8, 7))
    for color, region in zip(colors, regions, strict=True):
        selected = [
            row
            for row in rows
            if row["region_id"] == region
            and row["baseline_kelp_iou"].strip()
            and row["loro_kelp_iou"].strip()
        ]
        axis.scatter(
            [float(row["baseline_kelp_iou"]) for row in selected],
            [float(row["loro_kelp_iou"]) for row in selected],
            label=region,
            color=color,
            alpha=0.82,
            edgecolors="white",
            linewidths=0.4,
        )
    axis.plot([0, 1], [0, 1], color="black", linestyle="--", linewidth=1)
    axis.set(
        xlim=(0, 1),
        ylim=(0, 1),
        xlabel="Temporal baseline kelp IoU",
        ylabel="LORO kelp IoU",
    )
    axis.set_title("Matching source-TIFF kelp IoU")
    axis.grid(alpha=0.2)
    axis.legend(ncol=2, fontsize=8, title="Region")
    figure.tight_layout()
    figure.savefig(destination, dpi=180)
    plt.close(figure)


def _plot_deltas(table: Path, destination: Path) -> None:
    rows = read_csv(table)
    regions = sorted(
        {row["region_id"] for row in rows if row["delta_kelp_iou"].strip()}
    )
    values = [
        [
            float(row["delta_kelp_iou"])
            for row in rows
            if row["region_id"] == region and row["delta_kelp_iou"].strip()
        ]
        for region in regions
    ]
    figure, axis = plt.subplots(figsize=(11, 6))
    axis.boxplot(values, tick_labels=regions, showmeans=True)
    for position, region_values in enumerate(values, start=1):
        offsets = np.linspace(-0.08, 0.08, len(region_values))
        axis.scatter(
            position + offsets,
            region_values,
            color="#255f85",
            alpha=0.75,
            s=20,
            zorder=3,
        )
    axis.axhline(0, color="black", linestyle="--", linewidth=1)
    axis.set(xlabel="Held-out region", ylabel="LORO − baseline kelp IoU")
    axis.set_title("Paired source-TIFF kelp IoU differences")
    axis.tick_params(axis="x", rotation=35)
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(destination, dpi=180)
    plt.close(figure)


def _plot_full_region(table: Path, destination: Path) -> None:
    rows = read_csv(table)
    regions = [row["region_id"] for row in rows]
    positions = np.arange(len(rows))
    width = 0.25
    figure, axis = plt.subplots(figsize=(12, 6))
    for offset, metric, label in (
        (-width, "kelp_iou", "Kelp IoU"),
        (0, "kelp_precision", "Kelp precision"),
        (width, "kelp_recall", "Kelp recall"),
    ):
        axis.bar(
            positions + offset,
            [float(row[metric]) for row in rows],
            width,
            label=label,
        )
    axis.set(
        ylim=(0, 1),
        ylabel="Metric",
        xlabel="Held-out region",
        xticks=positions,
        xticklabels=regions,
    )
    axis.set_title("Full held-out-region LORO performance (non-paired)")
    axis.tick_params(axis="x", rotation=35)
    axis.grid(axis="y", alpha=0.2)
    axis.legend()
    figure.tight_layout()
    figure.savefig(destination, dpi=180)
    plt.close(figure)


def _percent(value: str | float) -> str:
    return f"{100 * float(value):+.2f} pp"


def _metric(value: str | float) -> str:
    return f"{float(value):.3f}"


def _report(root: Path, result: dict[str, Any]) -> str:
    matched = read_csv(root / "matched_tiff_metrics.csv")
    regions = read_csv(root / "pooled_confusion_summary.csv")
    full = read_csv(root / "full_region_loro_summary.csv")
    delta_rows = read_csv(root / "paired_region_summary.csv")
    pooled = next(row for row in regions if row["aggregation"] == "all_pooled_pixels")
    equal = next(row for row in regions if row["aggregation"] == "equal_region_mean")
    all_tiffs = next(row for row in delta_rows if row["scope"] == "all_tiffs")
    region_rows = [
        row for row in regions if row["aggregation"] == "region_pooled_pixels"
    ]
    wins = sum(float(row["delta_kelp_iou"]) > 0 for row in region_rows)
    direction = "higher" if float(equal["delta_kelp_iou"]) > 0 else "lower"
    scope_description = (
        "the historical selected non-overlapping chip subset"
        if result["evaluation_scope"] == SELECTED_NONOVERLAP_SCOPE
        else "all retained post-nodata test chips with overlap-averaged reconstruction"
    )
    ranked = sorted(
        (row for row in matched if row["delta_kelp_iou"].strip()),
        key=lambda row: float(row["delta_kelp_iou"]),
    )

    lines = [
        "# PlanetScope v3 matching-TIFF comparison",
        "",
        "## Scope and method",
        "",
        f"Evaluation uses {scope_description}.",
        "",
        f"This report compares {result['matched_tiff_count']} source TIFFs evaluated by both the temporal baseline and the corresponding region-held-out LORO model. "
        f"{result['excluded_tiff_count']} expected temporal-test TIFF is listed explicitly in `matched_tiff_exclusions.csv`. Kelp IoU is primary; precision and recall are diagnostics. Predictions use the fixed pre-test threshold 0.5.",
        "",
        f"TIFF metrics come from unique covered source pixels after overlap reconstruction. Paired deltas are LORO minus baseline. Region-pooled metrics sum TIFF confusion counts before deriving metrics. The equal-region result gives each of the {len(region_rows)} regions one vote, while the pooled-pixel result weights by scored pixels.",
        "",
        "Bootstrap intervals are descriptive percentile intervals from TIFF resampling and do not support independence-heavy p-value claims because imagery may remain spatially and temporally correlated.",
        "",
        "## Headline results",
        "",
        f"- Equal-region mean pooled kelp IoU: baseline {_metric(equal['baseline_kelp_iou'])}, LORO {_metric(equal['loro_kelp_iou'])}, delta {_percent(equal['delta_kelp_iou'])}.",
        f"- Pooled-pixel matched kelp IoU: baseline {_metric(pooled['baseline_kelp_iou'])}, LORO {_metric(pooled['loro_kelp_iou'])}, delta {_percent(pooled['delta_kelp_iou'])}.",
        f"- Mean TIFF-level kelp-IoU delta across {all_tiffs['delta_kelp_iou_valid_tiff_count']} pairs where IoU is defined for both models: {_percent(all_tiffs['delta_kelp_iou_mean'])} (95% descriptive bootstrap CI {_percent(all_tiffs['delta_kelp_iou_mean_ci_low'])} to {_percent(all_tiffs['delta_kelp_iou_mean_ci_high'])}); median {_percent(all_tiffs['delta_kelp_iou_median'])}.",
        f"- LORO pooled kelp IoU exceeds the baseline in {wins} of {len(region_rows)} matched regions.",
        "",
        f"Across these represented matching TIFFs, equal-region LORO kelp IoU is {direction} than the temporal baseline. This supports a bounded geographic-generalization comparison, not a claim about ecological truth or performance beyond the supplied labels, regions, acquisition dates, sensor, preprocessing, and single model seed.",
        "",
        "## Paired region-pooled results",
        "",
        "| Region | TIFFs | Baseline IoU | LORO IoU | Δ IoU | Δ precision | Δ recall |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in region_rows:
        lines.append(
            f"| {row['region_id']} | {row['matched_tiff_count']} | {_metric(row['baseline_kelp_iou'])} | {_metric(row['loro_kelp_iou'])} | {_percent(row['delta_kelp_iou'])} | {_percent(row['delta_kelp_precision'])} | {_percent(row['delta_kelp_recall'])} |"
        )
    lines.extend(
        [
            "",
            "## Full held-out-region LORO results (non-paired)",
            "",
            "These rows use every evaluated TIFF in each held-out region and must not be interpreted as paired baseline comparisons.",
            "",
            "| Region | TIFFs | Kelp IoU | Precision | Recall | Accuracy |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in full:
        lines.append(
            f"| {row['region_id']} | {row['source_tiff_count']} | {_metric(row['kelp_iou'])} | {_metric(row['kelp_precision'])} | {_metric(row['kelp_recall'])} | {_metric(row['accuracy'])} |"
        )
    if "coverage_comparison" in result:
        coverage = read_csv(root / "coverage_comparison.csv")
        baseline_coverage = next(
            row for row in coverage if row["run_key"] == "baseline-temporal-v3"
        )
        same_scope = all(
            row["same_scope_membership_verified"].lower() == "true" for row in coverage
        )
        if same_scope:
            lines.extend(
                [
                    "",
                    "## Coverage and membership identity against superseded v1",
                    "",
                    f"The corrected temporal baseline retains exactly {baseline_coverage['current_chip_count']} chips and {baseline_coverage['current_tiff_count']} TIFFs. All 13 packages preserve exact chip/source membership, coverage, ignore, scored, uncovered, and label-truth accounting from the superseded same-scope v1 evaluation; only prediction-dependent confusion counts and metrics may change.",
                    "",
                    "| Run | Chips v1 → v2 | TIFFs v1 → v2 | Covered-pixel change | Coverage v1 → v2 |",
                    "|---|---:|---:|---:|---:|",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "## Coverage change from historical evaluation",
                    "",
                    f"The temporal baseline grows from {baseline_coverage['historical_chip_count']} to {baseline_coverage['current_chip_count']} chips and from {baseline_coverage['historical_tiff_count']} to {baseline_coverage['current_tiff_count']} TIFFs. Covered source pixels increase by {int(baseline_coverage['covered_pixel_gain']):,}, from {100 * float(baseline_coverage['historical_coverage_fraction']):.1f}% to {100 * float(baseline_coverage['current_coverage_fraction']):.1f}% of the represented source grids.",
                    "",
                    "No shared TIFF loses coverage. Remaining uncovered pixels are outside retained chip footprints, principally trailing source-edge strips or areas represented only by chips removed under the fixed nodata policy.",
                    "",
                    "| Run | Chips old → new | TIFFs old → new | Covered-pixel gain | Coverage old → new |",
                    "|---|---:|---:|---:|---:|",
                ]
            )
        for row in coverage:
            lines.append(
                f"| {row['run_key']} | {row['historical_chip_count']} → {row['current_chip_count']} | {row['historical_tiff_count']} → {row['current_tiff_count']} | {int(row['covered_pixel_gain']):,} | {100 * float(row['historical_coverage_fraction']):.1f}% → {100 * float(row['current_coverage_fraction']):.1f}% |"
            )
    lines.extend(
        [
            "",
            "## Largest matching-TIFF changes",
            "",
            "The extremes below identify candidates for later qualitative review; they were not used for threshold or checkpoint selection.",
            "",
            "| Direction | Region | Source TIFF | Baseline IoU | LORO IoU | Δ IoU |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for direction_label, rows in (
        ("Lowest", ranked[:5]),
        ("Highest", reversed(ranked[-5:])),
    ):
        for row in rows:
            lines.append(
                f"| {direction_label} | {row['region_id']} | `{row['source_tiff_id']}` | {_metric(row['baseline_kelp_iou'])} | {_metric(row['loro_kelp_iou'])} | {_percent(row['delta_kelp_iou'])} |"
            )
    lines.extend(
        [
            "",
            "## Figures and audit tables",
            "",
            "- `figures/baseline_vs_loro_scatter.png`",
            "- `figures/paired_delta_by_region.png`",
            "- `figures/full_region_loro_metrics.png`",
            "- `matched_tiff_metrics.csv`, `matched_tiff_exclusions.csv`, `paired_region_summary.csv`, `full_region_loro_summary.csv`, and `pooled_confusion_summary.csv`",
            "",
            "## Limitations",
            "",
            "TIFFs are treated as the descriptive paired unit but are not asserted to be independent. A TIFF remains paired when a metric is undefined because its denominator is zero; that TIFF is omitted only from the corresponding metric-delta distribution, with valid counts reported. Results measure agreement with supplied segmentation labels. The experiment has one model family/configuration and one production seed; it does not estimate architecture or seed variability. Full-region LORO metrics and matched-TIFF metrics answer different questions and remain separate throughout this report.",
            "",
        ]
    )
    return "\n".join(lines)


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _git_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
    )
    return bool(result.stdout.strip())


def _publish(
    result: dict[str, Any], output_root: Path, args: argparse.Namespace
) -> dict[str, Any]:
    if output_root.exists():
        raise ComparisonError(f"Refusing to overwrite existing output: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = output_root.with_name(f".{output_root.name}.tmp-{uuid.uuid4().hex}")
    try:
        staging.mkdir()
        for name in _table_names(result):
            _write_csv(
                staging / f"{name}.csv",
                result[name],
                [
                    "region_id",
                    "source_tiff_id",
                    "acquisition_date",
                    "baseline_split",
                    "exclusion_reasons",
                ]
                if name == "matched_tiff_exclusions"
                else None,
            )
        figures = staging / "figures"
        figures.mkdir()
        _plot_scatter(
            staging / "matched_tiff_metrics.csv",
            figures / "baseline_vs_loro_scatter.png",
        )
        _plot_deltas(
            staging / "matched_tiff_metrics.csv",
            figures / "paired_delta_by_region.png",
        )
        _plot_full_region(
            staging / "full_region_loro_summary.csv",
            figures / "full_region_loro_metrics.png",
        )
        (staging / "comparison_report.md").write_text(_report(staging, result))
        artifact_paths = [
            *(staging / f"{name}.csv" for name in _table_names(result)),
            *(
                figures / name
                for name in (
                    "baseline_vs_loro_scatter.png",
                    "paired_delta_by_region.png",
                    "full_region_loro_metrics.png",
                )
            ),
            staging / "comparison_report.md",
        ]
        metadata = {
            "schema_version": 1,
            "experiment_version": "planet8b-loro-v3",
            "comparison_id": getattr(args, "comparison_id", "matched_tiffs_v1"),
            "evaluation_scope": result["evaluation_scope"],
            "producer_git_commit": _git_commit(),
            "producer_git_dirty": _git_dirty(),
            "producer_source_sha256": {
                "comparison_module": sha256_file(
                    Path(__file__).resolve().parents[1]
                    / "src/evaluation/planet8b_comparison.py"
                ),
                "comparison_cli": sha256_file(Path(__file__).resolve()),
            },
            "fixed_prediction_threshold": 0.5,
            "primary_metric": "kelp_iou",
            "diagnostic_metrics": ["kelp_precision", "kelp_recall"],
            "bootstrap": {
                "unit": "tiff",
                "replicates": BOOTSTRAP_REPLICATES,
                "seed": BOOTSTRAP_SEED,
                "interval": "percentile_95",
                "p_values": False,
            },
            "input_paths": {
                "suite_inventory": str(args.inventory),
                "temporal_splits": str(args.temporal_splits),
                "raster_metadata": str(args.raster_metadata),
                "dataset_root": str(args.dataset_root),
            },
            "input_sha256": {
                "suite_inventory": sha256_file(args.inventory),
                "temporal_splits": sha256_file(args.temporal_splits),
                "raster_metadata": sha256_file(args.raster_metadata),
            },
            "source_packages": result["source_packages"],
            "regions": result["regions"],
            "expected_tiff_count": result["expected_tiff_count"],
            "matched_tiff_count": result["matched_tiff_count"],
            "excluded_tiff_count": result["excluded_tiff_count"],
            "output_sha256": {
                str(path.relative_to(staging)): sha256_file(path)
                for path in artifact_paths
            },
            "wandb_run_id": None,
        }
        (staging / "comparison_metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )
        os.replace(staging, output_root)
        return metadata
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _validate_saved(root: Path, result: dict[str, Any]) -> None:
    metadata = json.loads((root / "comparison_metadata.json").read_text())
    for name in _table_names(result):
        rows = read_csv(root / f"{name}.csv")
        if len(rows) != len(result[name]):
            raise ComparisonError(f"Saved {name} row count does not reconcile")
    if metadata["matched_tiff_count"] != result["matched_tiff_count"]:
        raise ComparisonError("Saved matched TIFF count does not reconcile")
    for relative, expected_hash in metadata["output_sha256"].items():
        if sha256_file(root / relative) != expected_hash:
            raise ComparisonError(f"Saved artifact hash failed: {relative}")
    for figure in (root / "figures").glob("*.png"):
        if figure.stat().st_size == 0:
            raise ComparisonError(f"Empty figure: {figure}")


def _log_wandb(root: Path, metadata: dict[str, Any], mode: str) -> str | None:
    if mode == "disabled":
        return None
    import wandb

    run = wandb.init(
        entity="kdorman90-ucla",
        project="kelpseg",
        group="planet8b-loro-v3",
        name=f"{metadata['comparison_id'].replace('_', '-')}-comparison",
        job_type="comparison",
        tags=["planet8b-loro-v3", "comparison", "matched-tiffs"],
        config=metadata,
        mode=mode,
    )
    metadata["wandb_run_id"] = run.id
    temporary = root / ".comparison_metadata.json.tmp"
    temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, root / "comparison_metadata.json")
    matched = read_csv(root / "matched_tiff_metrics.csv")
    concise_columns = [
        "region_id",
        "source_tiff_id",
        "baseline_kelp_iou",
        "loro_kelp_iou",
        "delta_kelp_iou",
        "delta_kelp_precision",
        "delta_kelp_recall",
    ]
    run.log(
        {
            "matched_tiff_metrics": wandb.Table(
                columns=concise_columns,
                data=[[row[column] for column in concise_columns] for row in matched],
            ),
            "matched_tiff_count": metadata["matched_tiff_count"],
            "excluded_tiff_count": metadata["excluded_tiff_count"],
        }
    )
    artifact = wandb.Artifact(
        name=f"planet8b-loro-v3-{metadata['comparison_id'].replace('_', '-')}",
        type="planet8b-comparison-results",
        metadata=metadata,
    )
    artifact.add_dir(str(root))
    run.log_artifact(artifact)
    run.finish()
    return run.id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument(
        "--temporal-splits",
        type=Path,
        default=Path("planet8b_temporal_image_splits.csv"),
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--raster-metadata", type=Path)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--region", action="append")
    parser.add_argument(
        "--evaluation-scope",
        choices=EVALUATION_SCOPES,
        default=SELECTED_NONOVERLAP_SCOPE,
    )
    parser.add_argument("--comparison-id", default="matched_tiffs_v1")
    parser.add_argument("--historical-inventory", type=Path)
    parser.add_argument(
        "--wandb-mode", choices=("online", "offline", "disabled"), default="online"
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.raster_metadata is None:
        args.raster_metadata = args.dataset_root / "manifests/raster_metadata.csv"
    result = compare_suite(
        inventory_path=args.inventory,
        temporal_split_path=args.temporal_splits,
        raster_metadata_path=args.raster_metadata,
        dataset_root=args.dataset_root,
        regions=args.region,
        evaluation_scope=args.evaluation_scope,
    )
    if args.historical_inventory is not None:
        result["coverage_comparison"] = _coverage_comparison(
            args.inventory, args.historical_inventory
        )
    if args.validate_only:
        _validate_saved(args.output_root, result)
        print(json.dumps({"status": "verified", "output_root": str(args.output_root)}))
        return 0
    metadata = _publish(result, args.output_root, args)
    _validate_saved(args.output_root, result)
    wandb_run_id = _log_wandb(args.output_root, metadata, args.wandb_mode)
    print(
        json.dumps(
            {
                "status": "completed",
                "output_root": str(args.output_root),
                "matched_tiff_count": result["matched_tiff_count"],
                "excluded_tiff_count": result["excluded_tiff_count"],
                "wandb_run_id": wandb_run_id,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
