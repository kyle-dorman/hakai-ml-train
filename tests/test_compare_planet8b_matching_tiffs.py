from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.compare_planet8b_matching_tiffs import _coverage_comparison, _publish
from src.evaluation import planet8b_comparison as comparison
from src.evaluation.planet8b import sum_confusion


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _metric_row(
    source: str,
    region: str,
    run_key: str,
    held_out: str,
    fold_hash: str,
    counts: tuple[int, int, int, int],
    *,
    ignored: int = 0,
) -> dict[str, Any]:
    tn, fp, fn, tp = counts
    scored = sum(counts)
    covered = scored + ignored
    base: dict[str, Any] = {
        "source_tiff_id": source,
        "region_id": region,
        "acquisition_date": "2021-01-01",
        "experiment_version": "planet8b-loro-v3",
        "run_key": run_key,
        "wandb_run_id": f"train-{run_key}",
        "fold_id": "baseline_temporal_v1" if not held_out else f"loro_{region}",
        "held_out_region": held_out,
        "checkpoint_sha256": f"checkpoint-{run_key}",
        "fold_manifest_sha256": fold_hash,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
        "ignored_pixel_count": ignored,
        "uncovered_pixel_count": 100 - covered,
        "covered_pixel_count": covered,
        "scored_pixel_count": scored,
        "total_source_pixel_count": 100,
    }
    metrics = sum_confusion([base])
    base.update(
        {key: metrics[key] for key in comparison.ALL_DERIVED_METRICS},
        probability_raster="probability.tif",
        mask_raster="mask.tif",
    )
    return base


def _write_package(
    root: Path,
    run_key: str,
    held_out: str | None,
    fold_hash: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    package = root / "predictions" / run_key
    package.mkdir(parents=True)
    _write_csv(package / "tiff_metrics.csv", rows)
    _write_csv(
        package / "chip_diagnostics.csv",
        [{"chip_id": f"{row['source_tiff_id']}__chip"} for row in rows],
    )
    pooled = sum_confusion(rows)
    region_row = {
        "region_id": held_out or "all",
        "experiment_version": "planet8b-loro-v3",
        "run_key": run_key,
        "wandb_run_id": f"train-{run_key}",
        "fold_id": "baseline_temporal_v1" if held_out is None else f"loro_{held_out}",
        "held_out_region": held_out or "",
        "checkpoint_sha256": f"checkpoint-{run_key}",
        "fold_manifest_sha256": fold_hash,
        **pooled,
        "source_tiff_count": len(rows),
    }
    _write_csv(package / "region_metrics.csv", [region_row])
    (package / "evaluation_metadata.json").write_text(
        json.dumps(
            {
                "checkpoint_sha256": f"checkpoint-{run_key}",
                "evaluation_identity_sha256": f"evaluation-{run_key}",
                "experiment_version": "planet8b-loro-v3",
                "fold_id": region_row["fold_id"],
                "fold_manifest_sha256": fold_hash,
                "held_out_region": held_out,
                "prediction_wandb_run_id": f"prediction-{run_key}",
                "run_key": run_key,
                "schema_version": 1,
                "threshold": 0.5,
                "wandb_run_id": f"train-{run_key}",
            }
        )
    )
    return {
        "run_key": run_key,
        "run_type": "baseline_training" if held_out is None else "loro_training",
        "held_out_region": held_out or "",
        "training_wandb_run_id": f"train-{run_key}",
        "prediction_wandb_run_id": f"prediction-{run_key}",
        "checkpoint_sha256": f"checkpoint-{run_key}",
        "fold_manifest_sha256": fold_hash,
        "status": "verified",
        "test_tiff_count": len(rows),
        "test_chip_count": len(rows),
        "scored_pixel_count": sum(int(row["scored_pixel_count"]) for row in rows),
        "uncovered_pixel_count": sum(int(row["uncovered_pixel_count"]) for row in rows),
        "output_path": str(package),
        "error_summary": "",
    }


def _fold_row(source: str, region: str) -> dict[str, str]:
    return {
        "chip_id": f"{source}__chip",
        "source_tiff_id": source,
        "region_id": region,
        "source_temporal_split": "TEST",
        "experiment_split": "test",
        "selected": "true",
    }


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    monkeypatch.setattr(comparison, "REGIONS", ["r1", "r2"])
    dataset = tmp_path / "dataset"
    baseline_fold = dataset / "views/baseline_temporal_v1/fold_manifest.csv"
    _write_csv(
        baseline_fold,
        [_fold_row("a", "r1"), _fold_row("b", "r1"), _fold_row("c", "r2")],
    )
    loro_folds = {}
    for region, sources in (("r1", ["a"]), ("r2", ["c"])):
        path = dataset / f"views/loro_v1/{region}/fold_manifest.csv"
        _write_csv(path, [_fold_row(source, region) for source in sources])
        loro_folds[region] = path
    baseline_hash = comparison.sha256_file(baseline_fold)
    loro_hashes = {
        region: comparison.sha256_file(path) for region, path in loro_folds.items()
    }
    baseline_rows = [
        _metric_row(
            "a", "r1", "baseline-temporal-v3", "", baseline_hash, (50, 10, 10, 30)
        ),
        _metric_row(
            "b", "r1", "baseline-temporal-v3", "", baseline_hash, (60, 10, 10, 20)
        ),
        _metric_row(
            "c", "r2", "baseline-temporal-v3", "", baseline_hash, (70, 5, 5, 20)
        ),
    ]
    loro_r1 = [
        _metric_row("a", "r1", "loro-r1-v3", "r1", loro_hashes["r1"], (55, 5, 5, 35))
    ]
    # Same source shape and chip grid, but incompatible scored/ignored coverage.
    loro_r2 = [
        _metric_row(
            "c", "r2", "loro-r2-v3", "r2", loro_hashes["r2"], (69, 5, 5, 20), ignored=1
        )
    ]
    inventory = [
        _write_package(
            tmp_path, "baseline-temporal-v3", None, baseline_hash, baseline_rows
        ),
        _write_package(tmp_path, "loro-r1-v3", "r1", loro_hashes["r1"], loro_r1),
        _write_package(tmp_path, "loro-r2-v3", "r2", loro_hashes["r2"], loro_r2),
    ]
    inventory_path = tmp_path / "suite_inventory.csv"
    _write_csv(inventory_path, inventory)
    split_path = tmp_path / "splits.csv"
    _write_csv(
        split_path,
        [
            {
                "image_name_stem": source,
                "split": "TEST",
                "region_id": region,
                "acquisition_date": "2021-01-01",
            }
            for source, region in (("a", "r1"), ("b", "r1"), ("c", "r2"), ("d", "r2"))
        ],
    )
    raster_path = tmp_path / "raster_metadata.csv"
    _write_csv(
        raster_path,
        [
            {
                "source_tiff_id": source,
                "region_id": region,
                "region_name": f"region-{region}",
                "acquisition_date": "2021-01-01",
                "width": 10,
                "height": 10,
            }
            for source, region in (("a", "r1"), ("b", "r1"), ("c", "r2"), ("d", "r2"))
        ],
    )
    return {
        "dataset": dataset,
        "inventory": inventory_path,
        "splits": split_path,
        "rasters": raster_path,
    }


def test_fixture_joins_exclusions_deltas_pooling_and_plots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _fixture(tmp_path, monkeypatch)
    result = comparison.compare_suite(
        inventory_path=paths["inventory"],
        temporal_split_path=paths["splits"],
        raster_metadata_path=paths["rasters"],
        dataset_root=paths["dataset"],
    )
    assert result["expected_tiff_count"] == 4
    assert result["matched_tiff_count"] == 1
    assert result["excluded_tiff_count"] == 3
    reasons = {
        row["source_tiff_id"]: row["exclusion_reasons"]
        for row in result["matched_tiff_exclusions"]
    }
    assert reasons["b"] == "missing_loro_metrics"
    assert "ignored_pixel_count_mismatch" in reasons["c"]
    assert reasons["d"] == "missing_baseline_metrics;missing_loro_metrics"
    matched = result["matched_tiff_metrics"][0]
    assert matched["delta_kelp_iou"] == pytest.approx((35 / 45) - 0.6)
    pooled = next(
        row
        for row in result["pooled_confusion_summary"]
        if row["aggregation"] == "all_pooled_pixels"
    )
    assert pooled["baseline_true_positive"] == 30
    assert pooled["loro_true_positive"] == 35
    coverage = _coverage_comparison(paths["inventory"], paths["inventory"])
    assert all(row["covered_pixel_gain"] == 0 for row in coverage)
    assert all(row["shared_source_coverage_regression_count"] == 0 for row in coverage)
    assert all(row["same_scope_membership_verified"] for row in coverage)

    output = tmp_path / "comparison"
    args = argparse.Namespace(
        inventory=paths["inventory"],
        temporal_splits=paths["splits"],
        raster_metadata=paths["rasters"],
        dataset_root=paths["dataset"],
    )
    _publish(result, output, args)
    assert (output / "figures/baseline_vs_loro_scatter.png").stat().st_size > 0
    assert (output / "figures/paired_delta_by_region.png").stat().st_size > 0
    assert (output / "figures/full_region_loro_metrics.png").stat().st_size > 0


def test_duplicate_tiff_identity_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _fixture(tmp_path, monkeypatch)
    inventory = list(csv.DictReader(paths["inventory"].open()))
    package = Path(inventory[0]["output_path"])
    rows = list(csv.DictReader((package / "tiff_metrics.csv").open()))
    rows.append(rows[0])
    _write_csv(package / "tiff_metrics.csv", rows)
    inventory[0]["test_tiff_count"] = str(len(rows))
    _write_csv(paths["inventory"], inventory)
    with pytest.raises(comparison.ComparisonError, match="Duplicate baseline TIFF"):
        comparison.compare_suite(
            inventory_path=paths["inventory"],
            temporal_split_path=paths["splits"],
            raster_metadata_path=paths["rasters"],
            dataset_root=paths["dataset"],
        )


def test_wrong_held_out_region_row_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _fixture(tmp_path, monkeypatch)
    inventory = list(csv.DictReader(paths["inventory"].open()))
    package = Path(inventory[1]["output_path"])
    rows = list(csv.DictReader((package / "tiff_metrics.csv").open()))
    rows[0]["region_id"] = "r2"
    _write_csv(package / "tiff_metrics.csv", rows)
    with pytest.raises(comparison.ComparisonError, match="wrong-region TIFF row"):
        comparison.compare_suite(
            inventory_path=paths["inventory"],
            temporal_split_path=paths["splits"],
            raster_metadata_path=paths["rasters"],
            dataset_root=paths["dataset"],
        )


def test_undefined_metric_is_preserved_without_dropping_pair() -> None:
    baseline = _metric_row(
        "empty", "r1", "baseline-temporal-v3", "", "baseline-fold", (100, 0, 0, 0)
    )
    loro = _metric_row("empty", "r1", "loro-r1-v3", "r1", "loro-fold", (100, 0, 0, 0))
    expected = {
        "image_name_stem": "empty",
        "region_id": "r1",
        "acquisition_date": "2021-01-01",
    }
    raster = {
        "region_name": "region-r1",
        "width": "10",
        "height": "10",
    }
    row = comparison._matched_row(expected, raster, baseline, loro, 1)
    assert row["baseline_kelp_iou"] is None
    assert row["loro_kelp_iou"] is None
    assert row["delta_kelp_iou"] is None
    summary = comparison.summarize_deltas([row], [])
    assert summary[-1]["matched_tiff_count"] == 1
    assert summary[-1]["delta_kelp_iou_valid_tiff_count"] == 0
