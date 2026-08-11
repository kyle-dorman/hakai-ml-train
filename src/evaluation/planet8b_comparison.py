"""Strict matching-TIFF comparison helpers for the PlanetScope v3 suite."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from src.evaluation.planet8b import (
    SELECTED_NONOVERLAP_SCOPE,
    evaluation_schema_version,
    select_evaluation_rows,
    sum_confusion,
)

REGIONS = ["bc", *(f"ca_{number:03d}" for number in range(1, 12))]
COUNT_FIELDS = [
    "true_negative",
    "false_positive",
    "false_negative",
    "true_positive",
    "ignored_pixel_count",
    "uncovered_pixel_count",
    "covered_pixel_count",
    "scored_pixel_count",
    "total_source_pixel_count",
]
METRIC_FIELDS = ["accuracy", "kelp_precision", "kelp_recall", "kelp_iou"]
ALL_DERIVED_METRICS = [
    "accuracy",
    "kelp_precision",
    "kelp_recall",
    "kelp_f1",
    "kelp_iou",
    "background_iou",
    "macro_iou",
    "dice",
]
TIFF_REQUIRED = {
    "source_tiff_id",
    "region_id",
    "acquisition_date",
    "run_key",
    "wandb_run_id",
    "fold_id",
    "held_out_region",
    "checkpoint_sha256",
    "fold_manifest_sha256",
    *COUNT_FIELDS,
    *ALL_DERIVED_METRICS,
}
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20_260_810
METRIC_TOLERANCE = 1e-12


class ComparisonError(RuntimeError):
    """Raised when suite identity or comparison cardinality is unsafe."""


def read_csv(path: Path, required: set[str] | None = None) -> list[dict[str, str]]:
    """Read a CSV and require its declared analysis schema."""
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            missing = (required or set()) - fields
            if missing:
                raise ComparisonError(f"{path}: missing columns {sorted(missing)}")
            return list(reader)
    except OSError as exc:
        raise ComparisonError(f"Could not read {path}: {exc}") from exc


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object with a comparison-specific error."""
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"Could not read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ComparisonError(f"Expected a JSON object in {path}")
    return value


def sha256_file(path: Path) -> str:
    """Hash a compact identity-bearing input."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique(rows: list[dict[str, str]], keys: tuple[str, ...], label: str) -> dict:
    indexed: dict[Any, dict[str, str]] = {}
    for row in rows:
        key = row[keys[0]] if len(keys) == 1 else tuple(row[field] for field in keys)
        if key in indexed:
            raise ComparisonError(f"Duplicate {label} key: {key}")
        indexed[key] = row
    return indexed


def _same_float(left: float | None, right: str, tolerance: float) -> bool:
    if left is None:
        return right.strip().lower() in {"", "none", "nan"}
    try:
        return abs(left - float(right)) <= tolerance
    except ValueError:
        return False


def recompute_and_validate(row: dict[str, str], *, label: str) -> dict[str, Any]:
    """Recompute every stored metric from the unique-pixel confusion counts."""
    pooled = sum_confusion([row])
    if int(row["scored_pixel_count"]) != sum(int(row[key]) for key in COUNT_FIELDS[:4]):
        raise ComparisonError(f"{label}: scored pixels do not equal confusion sum")
    if int(row["covered_pixel_count"]) != (
        int(row["scored_pixel_count"]) + int(row["ignored_pixel_count"])
    ):
        raise ComparisonError(f"{label}: covered pixels do not reconcile")
    if int(row["total_source_pixel_count"]) != (
        int(row["covered_pixel_count"]) + int(row["uncovered_pixel_count"])
    ):
        raise ComparisonError(f"{label}: total pixels do not reconcile")
    for metric in ALL_DERIVED_METRICS:
        if not _same_float(pooled[metric], row[metric], METRIC_TOLERANCE):
            raise ComparisonError(
                f"{label}: stored {metric}={row[metric]!r} differs from recomputed "
                f"{pooled[metric]!r}"
            )
    return pooled


def _validated_package(
    inventory: dict[str, str],
    expected_region: str | None,
    evaluation_scope: str,
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, str]]:
    run_key = inventory["run_key"]
    if inventory["status"] != "verified" or inventory["error_summary"]:
        raise ComparisonError(f"Prediction inventory row is not verified: {run_key}")
    root = Path(inventory["output_path"])
    metadata = read_json(root / "evaluation_metadata.json")
    for key in (
        "checkpoint_sha256",
        "fold_manifest_sha256",
        "run_key",
    ):
        if str(metadata.get(key) or "") != inventory[key]:
            raise ComparisonError(f"{run_key}: inventory/metadata mismatch for {key}")
    if metadata.get("schema_version") != evaluation_schema_version(evaluation_scope):
        raise ComparisonError(f"{run_key}: unsupported evaluation schema")
    if metadata.get("evaluation_scope", SELECTED_NONOVERLAP_SCOPE) != evaluation_scope:
        raise ComparisonError(f"{run_key}: evaluation scope mismatch")
    if metadata.get("threshold") != 0.5:
        raise ComparisonError(f"{run_key}: threshold is not the fixed 0.5")
    if metadata.get("held_out_region") != expected_region:
        raise ComparisonError(f"{run_key}: held-out region identity mismatch")
    rows = read_csv(root / "tiff_metrics.csv", TIFF_REQUIRED)
    if len(rows) != int(inventory["test_tiff_count"]):
        raise ComparisonError(f"{run_key}: TIFF row count differs from inventory")
    for row in rows:
        if row["run_key"] != run_key:
            raise ComparisonError(f"{run_key}: foreign run key in TIFF metrics")
        if row["checkpoint_sha256"] != inventory["checkpoint_sha256"]:
            raise ComparisonError(f"{run_key}: foreign checkpoint in TIFF metrics")
        if row["fold_manifest_sha256"] != inventory["fold_manifest_sha256"]:
            raise ComparisonError(f"{run_key}: foreign fold in TIFF metrics")
        if row.get("evaluation_scope", SELECTED_NONOVERLAP_SCOPE) != evaluation_scope:
            raise ComparisonError(
                f"{run_key}: foreign evaluation scope in TIFF metrics"
            )
        if expected_region is not None and (
            row["region_id"] != expected_region
            or row["held_out_region"] != expected_region
        ):
            raise ComparisonError(f"{run_key}: wrong-region TIFF row")
        recompute_and_validate(
            row, label=f"{run_key}/{row['region_id']}/{row['source_tiff_id']}"
        )
    return rows, metadata, inventory


def _evaluation_chips(
    path: Path, *, evaluation_scope: str, held_out_region: str | None
) -> dict[str, set[str]]:
    rows = read_csv(
        path,
        {
            "chip_id",
            "source_tiff_id",
            "region_id",
            "experiment_split",
            "selected",
            *(
                {"source_temporal_split", "selection_reason"}
                if evaluation_scope != SELECTED_NONOVERLAP_SCOPE
                else set()
            ),
        },
    )
    rows = select_evaluation_rows(
        rows,
        scope=evaluation_scope,
        held_out_region=held_out_region,
    )
    selected: dict[str, set[str]] = defaultdict(set)
    seen: set[str] = set()
    for row in rows:
        if row["chip_id"] in seen:
            raise ComparisonError(f"{path}: duplicate selected chip {row['chip_id']}")
        seen.add(row["chip_id"])
        selected[row["source_tiff_id"]].add(row["chip_id"])
    return dict(selected)


def _compatibility_reasons(
    baseline: dict[str, str],
    loro: dict[str, str],
    baseline_chips: set[str],
    loro_chips: set[str],
) -> list[str]:
    reasons = []
    if baseline["acquisition_date"] != loro["acquisition_date"]:
        reasons.append("acquisition_date_mismatch")
    if baseline_chips != loro_chips:
        reasons.append("selected_chip_membership_mismatch")
    for field in COUNT_FIELDS[4:]:
        if baseline[field] != loro[field]:
            reasons.append(f"{field}_mismatch")
    baseline_background = int(baseline["true_negative"]) + int(
        baseline["false_positive"]
    )
    loro_background = int(loro["true_negative"]) + int(loro["false_positive"])
    baseline_kelp = int(baseline["true_positive"]) + int(baseline["false_negative"])
    loro_kelp = int(loro["true_positive"]) + int(loro["false_negative"])
    if baseline_background != loro_background:
        reasons.append("background_truth_count_mismatch")
    if baseline_kelp != loro_kelp:
        reasons.append("kelp_truth_count_mismatch")
    return reasons


def _matched_row(
    expected: dict[str, str],
    raster: dict[str, str],
    baseline: dict[str, str],
    loro: dict[str, str],
    chip_count: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "region_id": expected["region_id"],
        "region_name": raster["region_name"],
        "source_tiff_id": expected["image_name_stem"],
        "acquisition_date": expected["acquisition_date"],
        "source_width": int(raster["width"]),
        "source_height": int(raster["height"]),
        "selected_test_chip_count": chip_count,
        "scored_pixel_count": int(baseline["scored_pixel_count"]),
        "covered_pixel_count": int(baseline["covered_pixel_count"]),
        "uncovered_pixel_count": int(baseline["uncovered_pixel_count"]),
        "ignored_pixel_count": int(baseline["ignored_pixel_count"]),
        "total_source_pixel_count": int(baseline["total_source_pixel_count"]),
        "coverage_fraction": int(baseline["covered_pixel_count"])
        / int(baseline["total_source_pixel_count"]),
    }
    for model, row in (("baseline", baseline), ("loro", loro)):
        for field in COUNT_FIELDS[:4] + METRIC_FIELDS:
            value = row[field]
            result[f"{model}_{field}"] = (
                int(value)
                if field in COUNT_FIELDS
                else (
                    float(value) if value is not None and str(value).strip() else None
                )
            )
        result[f"{model}_run_key"] = row["run_key"]
        result[f"{model}_training_wandb_run_id"] = row["wandb_run_id"]
        result[f"{model}_checkpoint_sha256"] = row["checkpoint_sha256"]
        result[f"{model}_fold_id"] = row["fold_id"]
        result[f"{model}_fold_manifest_sha256"] = row["fold_manifest_sha256"]
    for metric in METRIC_FIELDS:
        baseline_value = result[f"baseline_{metric}"]
        loro_value = result[f"loro_{metric}"]
        result[f"delta_{metric}"] = (
            None
            if baseline_value is None or loro_value is None
            else loro_value - baseline_value
        )
    return result


def bootstrap_interval(
    values: list[float], *, statistic: str, seed: int
) -> tuple[float, float]:
    """Return a deterministic percentile interval from TIFF resamples."""
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, array.size, size=(BOOTSTRAP_REPLICATES, array.size))
    samples = array[indices]
    estimates = (
        samples.mean(axis=1) if statistic == "mean" else np.median(samples, axis=1)
    )
    low, high = np.quantile(estimates, [0.025, 0.975])
    return float(low), float(high)


def summarize_deltas(
    matched: list[dict[str, Any]], exclusions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Summarize paired TIFF deltas by region and once across all TIFFs."""
    active_regions = [
        region
        for region in REGIONS
        if any(row["region_id"] == region for row in matched + exclusions)
    ]
    groups = {
        region: [row for row in matched if row["region_id"] == region]
        for region in active_regions
    }
    groups["all_tiffs"] = matched
    excluded_counts: dict[str, int] = defaultdict(int)
    for row in exclusions:
        excluded_counts[row["region_id"]] += 1
    output = []
    for scope, rows in groups.items():
        summary: dict[str, Any] = {
            "scope": scope,
            "matched_tiff_count": len(rows),
            "excluded_tiff_count": (
                len(exclusions) if scope == "all_tiffs" else excluded_counts[scope]
            ),
            "bootstrap_unit": "tiff",
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_seed": BOOTSTRAP_SEED,
        }
        for metric in METRIC_FIELDS:
            values = [
                float(row[f"delta_{metric}"])
                for row in rows
                if row[f"delta_{metric}"] is not None
            ]
            summary[f"delta_{metric}_valid_tiff_count"] = len(values)
            if not values:
                for name in (
                    "mean",
                    "median",
                    "q1",
                    "q3",
                    "mean_ci_low",
                    "mean_ci_high",
                    "median_ci_low",
                    "median_ci_high",
                ):
                    summary[f"delta_{metric}_{name}"] = None
                continue
            mean_low, mean_high = bootstrap_interval(
                values, statistic="mean", seed=BOOTSTRAP_SEED
            )
            median_low, median_high = bootstrap_interval(
                values, statistic="median", seed=BOOTSTRAP_SEED
            )
            summary.update(
                {
                    f"delta_{metric}_mean": float(np.mean(values)),
                    f"delta_{metric}_median": float(np.median(values)),
                    f"delta_{metric}_q1": float(np.quantile(values, 0.25)),
                    f"delta_{metric}_q3": float(np.quantile(values, 0.75)),
                    f"delta_{metric}_mean_ci_low": mean_low,
                    f"delta_{metric}_mean_ci_high": mean_high,
                    f"delta_{metric}_median_ci_low": median_low,
                    f"delta_{metric}_median_ci_high": median_high,
                }
            )
        output.append(summary)
    return output


def _pooled_row(
    aggregation: str, region: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "aggregation": aggregation,
        "region_id": region,
        "matched_tiff_count": len(rows),
    }
    for model in ("baseline", "loro"):
        mapped = [
            {field: row[f"{model}_{field}"] for field in COUNT_FIELDS[:4]}
            | {field: row[field] for field in COUNT_FIELDS[4:]}
            for row in rows
        ]
        pooled = sum_confusion(mapped)
        for field in COUNT_FIELDS + METRIC_FIELDS:
            result[f"{model}_{field}"] = pooled[field]
    for metric in METRIC_FIELDS:
        result[f"delta_{metric}"] = (
            result[f"loro_{metric}"] - result[f"baseline_{metric}"]
        )
    return result


def pooled_summaries(matched: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return region, all-pixel, and equal-region paired summaries."""
    rows = []
    active_regions = [
        region
        for region in REGIONS
        if any(row["region_id"] == region for row in matched)
    ]
    for region in active_regions:
        rows.append(
            _pooled_row(
                "region_pooled_pixels",
                region,
                [row for row in matched if row["region_id"] == region],
            )
        )
    rows.append(_pooled_row("all_pooled_pixels", "all", matched))
    equal: dict[str, Any] = {
        "aggregation": "equal_region_mean",
        "region_id": "all",
        "matched_tiff_count": len(matched),
    }
    region_rows = rows[: len(active_regions)]
    for model in ("baseline", "loro"):
        for field in COUNT_FIELDS:
            equal[f"{model}_{field}"] = None
        for metric in METRIC_FIELDS:
            equal[f"{model}_{metric}"] = float(
                np.mean([row[f"{model}_{metric}"] for row in region_rows])
            )
    for metric in METRIC_FIELDS:
        equal[f"delta_{metric}"] = equal[f"loro_{metric}"] - equal[f"baseline_{metric}"]
    rows.append(equal)
    return rows


def compare_suite(
    *,
    inventory_path: Path,
    temporal_split_path: Path,
    raster_metadata_path: Path,
    dataset_root: Path,
    regions: list[str] | None = None,
    evaluation_scope: str = SELECTED_NONOVERLAP_SCOPE,
) -> dict[str, Any]:
    """Validate suite identities and build every comparison table in memory."""
    selected_regions = regions or REGIONS
    if not selected_regions or not set(selected_regions) <= set(REGIONS):
        raise ComparisonError(f"Invalid region selection: {selected_regions}")
    inventory_rows = read_csv(
        inventory_path,
        {
            "run_key",
            "run_type",
            "held_out_region",
            "checkpoint_sha256",
            "fold_manifest_sha256",
            "status",
            "test_tiff_count",
            "output_path",
            "error_summary",
            "training_wandb_run_id",
            "prediction_wandb_run_id",
        },
    )
    inventory = _unique(inventory_rows, ("run_key",), "inventory")
    expected_runs = {"baseline-temporal-v3", *(f"loro-{r}-v3" for r in REGIONS)}
    if set(inventory) != expected_runs:
        raise ComparisonError(
            f"Suite run keys differ from expected: {sorted(set(inventory) ^ expected_runs)}"
        )
    for row in inventory_rows:
        if row.get("evaluation_scope", SELECTED_NONOVERLAP_SCOPE) != evaluation_scope:
            raise ComparisonError(
                f"{row['run_key']}: inventory evaluation scope mismatch"
            )
    baseline_rows, baseline_meta, baseline_inventory = _validated_package(
        inventory["baseline-temporal-v3"], None, evaluation_scope
    )
    baseline_by_key = _unique(
        baseline_rows, ("region_id", "source_tiff_id"), "baseline TIFF"
    )
    split_rows = read_csv(
        temporal_split_path,
        {"image_name_stem", "split", "region_id", "acquisition_date"},
    )
    split_by_key = _unique(
        split_rows, ("region_id", "image_name_stem"), "temporal split"
    )
    expected = {
        key: row
        for key, row in split_by_key.items()
        if row["split"] == "TEST" and row["region_id"] in selected_regions
    }
    unexpected_baseline = set(baseline_by_key) - {
        key for key, row in split_by_key.items() if row["split"] == "TEST"
    }
    if unexpected_baseline:
        raise ComparisonError(
            f"Non-TEST TIFFs found in baseline metrics: {sorted(unexpected_baseline)}"
        )
    raster_rows = read_csv(
        raster_metadata_path,
        {
            "source_tiff_id",
            "region_id",
            "region_name",
            "acquisition_date",
            "width",
            "height",
        },
    )
    raster_by_key = _unique(
        raster_rows, ("region_id", "source_tiff_id"), "raster metadata"
    )
    baseline_fold = dataset_root / "views/baseline_temporal_v1/fold_manifest.csv"
    if sha256_file(baseline_fold) != baseline_inventory["fold_manifest_sha256"]:
        raise ComparisonError("Baseline fold manifest hash differs from inventory")
    baseline_chips = _evaluation_chips(
        baseline_fold,
        evaluation_scope=evaluation_scope,
        held_out_region=None,
    )
    matched: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    full_region: list[dict[str, Any]] = []
    source_packages: list[dict[str, Any]] = [
        {
            "run_key": baseline_inventory["run_key"],
            "training_wandb_run_id": baseline_inventory["training_wandb_run_id"],
            "prediction_wandb_run_id": baseline_inventory["prediction_wandb_run_id"],
            "checkpoint_sha256": baseline_inventory["checkpoint_sha256"],
            "fold_manifest_sha256": baseline_inventory["fold_manifest_sha256"],
            "evaluation_identity_sha256": baseline_meta["evaluation_identity_sha256"],
            "evaluation_scope": evaluation_scope,
        }
    ]
    for region in selected_regions:
        run_key = f"loro-{region}-v3"
        loro_rows, loro_meta, loro_inventory = _validated_package(
            inventory[run_key], region, evaluation_scope
        )
        loro_by_key = _unique(
            loro_rows, ("region_id", "source_tiff_id"), f"{region} LORO TIFF"
        )
        for key, row in loro_by_key.items():
            raster = raster_by_key.get(key)
            if raster is None:
                raise ComparisonError(f"{region}: missing raster metadata for {key[1]}")
            if int(row["total_source_pixel_count"]) != int(raster["width"]) * int(
                raster["height"]
            ):
                raise ComparisonError(f"{region}: source shape mismatch for {key[1]}")
            if row["acquisition_date"] != raster["acquisition_date"]:
                raise ComparisonError(f"{region}: raster date mismatch for {key[1]}")
        loro_fold = dataset_root / f"views/loro_v1/{region}/fold_manifest.csv"
        if sha256_file(loro_fold) != loro_inventory["fold_manifest_sha256"]:
            raise ComparisonError(f"{region}: LORO fold hash differs from inventory")
        loro_chips = _evaluation_chips(
            loro_fold,
            evaluation_scope=evaluation_scope,
            held_out_region=region,
        )
        if set(loro_by_key) != {(region, source) for source in loro_chips}:
            raise ComparisonError(
                f"{region}: LORO TIFF rows differ from test-chip sources"
            )
        pooled = sum_confusion(loro_rows)
        saved_region = read_csv(
            Path(loro_inventory["output_path"]) / "region_metrics.csv",
            TIFF_REQUIRED - {"source_tiff_id", "acquisition_date"}
            | {"source_tiff_count"},
        )
        if len(saved_region) != 1 or saved_region[0]["region_id"] != region:
            raise ComparisonError(f"{region}: invalid full-region summary cardinality")
        for field in COUNT_FIELDS:
            if int(saved_region[0][field]) != pooled[field]:
                raise ComparisonError(
                    f"{region}: full-region {field} does not reconcile"
                )
        for metric in ALL_DERIVED_METRICS:
            if not _same_float(
                pooled[metric], saved_region[0][metric], METRIC_TOLERANCE
            ):
                raise ComparisonError(
                    f"{region}: full-region {metric} does not reconcile"
                )
        full_region.append(
            {
                "region_id": region,
                "comparison_scope": "full_held_out_region_non_paired",
                "source_tiff_count": len(loro_rows),
                **{field: pooled[field] for field in COUNT_FIELDS + METRIC_FIELDS},
                "run_key": run_key,
                "training_wandb_run_id": loro_inventory["training_wandb_run_id"],
                "prediction_wandb_run_id": loro_inventory["prediction_wandb_run_id"],
                "checkpoint_sha256": loro_inventory["checkpoint_sha256"],
                "fold_manifest_sha256": loro_inventory["fold_manifest_sha256"],
            }
        )
        source_packages.append(
            {
                "run_key": run_key,
                "training_wandb_run_id": loro_inventory["training_wandb_run_id"],
                "prediction_wandb_run_id": loro_inventory["prediction_wandb_run_id"],
                "checkpoint_sha256": loro_inventory["checkpoint_sha256"],
                "fold_manifest_sha256": loro_inventory["fold_manifest_sha256"],
                "evaluation_identity_sha256": loro_meta["evaluation_identity_sha256"],
                "evaluation_scope": evaluation_scope,
            }
        )
        for key, expected_row in sorted(expected.items()):
            if key[0] != region:
                continue
            baseline = baseline_by_key.get(key)
            loro = loro_by_key.get(key)
            reasons = []
            if baseline is None:
                reasons.append("missing_baseline_metrics")
            if loro is None:
                reasons.append("missing_loro_metrics")
            raster = raster_by_key.get(key)
            if raster is None:
                reasons.append("missing_raster_metadata")
            if baseline is not None and loro is not None:
                reasons.extend(
                    _compatibility_reasons(
                        baseline,
                        loro,
                        baseline_chips.get(key[1], set()),
                        loro_chips.get(key[1], set()),
                    )
                )
            if raster is not None:
                source_pixels = int(raster["width"]) * int(raster["height"])
                if (
                    baseline is not None
                    and int(baseline["total_source_pixel_count"]) != source_pixels
                ):
                    reasons.append("baseline_source_shape_mismatch")
                if (
                    loro is not None
                    and int(loro["total_source_pixel_count"]) != source_pixels
                ):
                    reasons.append("loro_source_shape_mismatch")
            if reasons:
                exclusions.append(
                    {
                        "region_id": region,
                        "source_tiff_id": key[1],
                        "acquisition_date": expected_row["acquisition_date"],
                        "baseline_split": expected_row["split"],
                        "exclusion_reasons": ";".join(sorted(set(reasons))),
                    }
                )
                continue
            if raster["acquisition_date"] != expected_row["acquisition_date"]:
                raise ComparisonError(f"{key}: split/raster acquisition date mismatch")
            matched.append(
                _matched_row(
                    expected_row,
                    raster,
                    baseline,
                    loro,
                    len(baseline_chips[key[1]]),
                )
            )
    if len(matched) + len(exclusions) != len(expected):
        raise ComparisonError("Expected paired TIFF accounting does not reconcile")
    return {
        "matched_tiff_metrics": matched,
        "matched_tiff_exclusions": exclusions,
        "paired_region_summary": summarize_deltas(matched, exclusions),
        "full_region_loro_summary": full_region,
        "pooled_confusion_summary": pooled_summaries(matched),
        "source_packages": source_packages,
        "expected_tiff_count": len(expected),
        "matched_tiff_count": len(matched),
        "excluded_tiff_count": len(exclusions),
        "regions": selected_regions,
        "evaluation_scope": evaluation_scope,
    }
