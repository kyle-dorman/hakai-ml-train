#!/usr/bin/env python3
"""Validate and launch the resumable PlanetScope v3 prediction suite."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.planet8b import (
    EVALUATION_SCOPES,
    SELECTED_NONOVERLAP_SCOPE,
    evaluation_schema_version,
    select_evaluation_rows,
)
from src.run_context import sha256_file

REGIONS = ["bc", *(f"ca_{number:03d}" for number in range(1, 12))]
DEFAULT_DATASET_ROOT = Path("/home/sky/data/planet8b_all_regions_1024_512_v2")
DEFAULT_OUTPUT_ROOT = Path("/home/sky/experiments/planet8b-loro-v3/predictions")
DEFAULT_REGISTRY = Path(
    "/home/sky/experiments/planet8b-loro-v3/experiment_registry.jsonl"
)
INVENTORY_FIELDS = [
    "run_key",
    "run_type",
    "held_out_region",
    "training_wandb_run_id",
    "prediction_wandb_run_id",
    "checkpoint_sha256",
    "fold_manifest_sha256",
    "evaluation_scope",
    "status",
    "test_tiff_count",
    "test_chip_count",
    "selected_nonoverlap_chip_count",
    "overlap_chip_count",
    "scored_pixel_count",
    "uncovered_pixel_count",
    "output_path",
    "error_summary",
]


class PredictionRunnerError(RuntimeError):
    """Raised when an incomplete or mismatched training run is selected."""


def _latest_states(registry: Path, version: str) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    for line in registry.read_text().splitlines():
        if line:
            event = json.loads(line)
            if event.get("experiment_version") == version:
                states[event["run_key"]] = event
    return states


def _test_scope(
    fold_manifest: Path,
    *,
    evaluation_scope: str = SELECTED_NONOVERLAP_SCOPE,
    held_out_region: str | None = None,
) -> tuple[int, int, int, int]:
    with fold_manifest.open(newline="", encoding="utf-8") as handle:
        rows = select_evaluation_rows(
            list(csv.DictReader(handle)),
            scope=evaluation_scope,
            held_out_region=held_out_region,
        )
    return (
        len(rows),
        len({row["source_tiff_id"] for row in rows}),
        sum(row["selected"].lower() == "true" for row in rows),
        sum(row["selected"].lower() == "false" for row in rows),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PredictionRunnerError(f"Could not read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PredictionRunnerError(f"Expected object in {path}")
    return value


def _verified_summary(
    destination: Path,
    event: dict[str, Any],
    expected_chips: int,
    expected_tiffs: int,
    selected_nonoverlap_chips: int,
    overlap_chips: int,
    evaluation_scope: str,
) -> dict[str, Any] | None:
    """Return a compatible completed summary, otherwise ``None``.

    The evaluator's per-source completions make interrupted work resumable, but a
    package is current only after its consolidated summary has the recorded
    checkpoint/fold identity and the exact manifest-derived test scope.
    """
    metadata_path = destination / "evaluation_metadata.json"
    summary_path = destination / "test_summary.json"
    if not metadata_path.is_file() or not summary_path.is_file():
        return None
    metadata = _read_json(metadata_path)
    summary = _read_json(summary_path)
    if (
        metadata.get("checkpoint_sha256") != event["checkpoint_sha256"]
        or metadata.get("schema_version") != evaluation_schema_version(evaluation_scope)
        or metadata.get("fold_manifest_sha256") != event["fold_manifest_sha256"]
        or metadata.get("threshold") != 0.5
        or summary.get("checkpoint_sha256") != event["checkpoint_sha256"]
        or summary.get("fold_manifest_sha256") != event["fold_manifest_sha256"]
        or summary.get("threshold") != 0.5
        or summary.get("test_chip_count") != expected_chips
        or summary.get("test_tiff_count") != expected_tiffs
        or metadata.get("evaluation_scope", SELECTED_NONOVERLAP_SCOPE)
        != evaluation_scope
        or summary.get("evaluation_scope", SELECTED_NONOVERLAP_SCOPE)
        != evaluation_scope
        or (
            evaluation_scope != SELECTED_NONOVERLAP_SCOPE
            and summary.get("selected_nonoverlap_chip_count")
            != selected_nonoverlap_chips
        )
        or (
            evaluation_scope != SELECTED_NONOVERLAP_SCOPE
            and summary.get("overlap_chip_count") != overlap_chips
        )
    ):
        return None
    source_root = destination / "source_predictions"
    probabilities = list(source_root.glob("*_probability.tif"))
    masks = list(source_root.glob("*_mask.tif"))
    completions = list(source_root.glob("*.completion.json"))
    if not (
        len(probabilities) == len(masks) == len(completions) == expected_tiffs
        and all(
            path.is_file()
            for path in [
                destination / "chip_diagnostics.csv",
                destination / "tiff_metrics.csv",
                destination / "region_metrics.csv",
            ]
        )
    ):
        return None
    return {
        **summary,
        "prediction_wandb_run_id": metadata.get("prediction_wandb_run_id"),
    }


def _atomic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=INVENTORY_FIELDS, extrasaction="raise"
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def build_plan(
    registry: Path,
    output_root: Path,
    *,
    version: str,
    evaluation_scope: str = SELECTED_NONOVERLAP_SCOPE,
) -> list[dict[str, Any]]:
    """Build the only approved baseline-plus-region order from completed runs."""
    states = _latest_states(registry, version)
    expected = ["baseline-temporal-v3", *(f"loro-{region}-v3" for region in REGIONS)]
    if set(states) != set(expected):
        raise PredictionRunnerError(
            f"Registry v3 run keys differ from expected suite: {sorted(set(states) ^ set(expected))}"
        )
    plan = []
    for run_key in expected:
        event = states[run_key]
        if event.get("status") != "completed":
            raise PredictionRunnerError(f"Training run is not completed: {run_key}")
        checkpoint = Path(event.get("checkpoint_path", ""))
        fold = Path(event.get("fold_manifest_path", ""))
        if not checkpoint.is_file() or sha256_file(checkpoint) != event.get(
            "checkpoint_sha256"
        ):
            raise PredictionRunnerError(f"Checkpoint identity failed: {run_key}")
        if not fold.is_file() or sha256_file(fold) != event.get("fold_manifest_sha256"):
            raise PredictionRunnerError(f"Fold identity failed: {run_key}")
        chips, tiffs, selected_chips, overlap_chips = _test_scope(
            fold,
            evaluation_scope=evaluation_scope,
            held_out_region=event.get("held_out_region"),
        )
        destination = output_root / run_key
        summary = _verified_summary(
            destination,
            event,
            chips,
            tiffs,
            selected_chips,
            overlap_chips,
            evaluation_scope,
        )
        plan.append(
            {
                "run_key": run_key,
                "run_type": event["run_type"],
                "held_out_region": event.get("held_out_region"),
                "training_wandb_run_id": event.get("wandb_run_id"),
                "checkpoint_path": str(checkpoint),
                "checkpoint_sha256": event["checkpoint_sha256"],
                "fold_manifest": str(fold),
                "fold_manifest_sha256": event["fold_manifest_sha256"],
                "evaluation_scope": evaluation_scope,
                "output_path": str(destination),
                "test_chip_count": chips,
                "test_tiff_count": tiffs,
                "selected_nonoverlap_chip_count": selected_chips,
                "overlap_chip_count": overlap_chips,
                "status": "verified" if summary else "pending",
                "prediction_wandb_run_id": (
                    summary.get("prediction_wandb_run_id") if summary else None
                ),
                "scored_pixel_count": summary.get("scored_pixel_count")
                if summary
                else None,
                "uncovered_pixel_count": (
                    summary.get("uncovered_pixel_count") if summary else None
                ),
                "error_summary": "",
            }
        )
    return plan


def write_inventory(output_root: Path, plan: list[dict[str, Any]]) -> Path:
    """Write the compact suite join surface without generated rasters in git."""
    path = output_root / "suite_inventory.csv"
    _atomic_csv(path, [{key: row.get(key) for key in INVENTORY_FIELDS} for row in plan])
    return path


def evaluation_command(entry: dict[str, Any], *, args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).with_name("evaluate_planet8b_run.py")),
        "--run-key",
        entry["run_key"],
        "--registry",
        str(args.registry),
        "--dataset-root",
        str(args.dataset_root),
        "--fold-manifest",
        entry["fold_manifest"],
        "--chip-manifest",
        str(args.dataset_root / "manifests/chip_manifest.csv"),
        "--raster-metadata",
        str(args.dataset_root / "manifests/raster_metadata.csv"),
        "--model-config",
        str(args.model_config),
        "--output-root",
        entry["output_path"],
        "--threshold",
        "0.5",
        "--evaluation-scope",
        args.evaluation_scope,
        "--resume",
        "--wandb-mode",
        args.wandb_mode,
        "--device",
        args.device,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument(
        "--model-config",
        type=Path,
        default=Path("configs/kelp-ps8b/generalization/segformer_b3_v3.yaml"),
    )
    parser.add_argument("--run-key", action="append")
    parser.add_argument(
        "--wandb-mode", choices=("online", "offline", "disabled"), default="online"
    )
    parser.add_argument("--device", default="cuda")
    parser.add_argument(
        "--evaluation-scope",
        choices=EVALUATION_SCOPES,
        default=SELECTED_NONOVERLAP_SCOPE,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = build_plan(
        args.registry,
        args.output_root,
        version="planet8b-loro-v3",
        evaluation_scope=args.evaluation_scope,
    )
    print(json.dumps(plan, indent=2, sort_keys=True))
    if args.dry_run:
        return 0
    requested = set(args.run_key or [entry["run_key"] for entry in plan])
    unknown = requested - {entry["run_key"] for entry in plan}
    if unknown:
        raise PredictionRunnerError(f"Unknown run keys: {sorted(unknown)}")
    for entry in plan:
        if entry["run_key"] not in requested or entry["status"] == "verified":
            continue
        command = evaluation_command(entry, args=args)
        result = subprocess.run(command, check=False)
        if result.returncode:
            entry["status"] = "failed"
            entry["error_summary"] = f"evaluator exited {result.returncode}"
            write_inventory(args.output_root, plan)
            return result.returncode
        refreshed = build_plan(
            args.registry,
            args.output_root,
            version="planet8b-loro-v3",
            evaluation_scope=args.evaluation_scope,
        )
        entry.update(
            next(row for row in refreshed if row["run_key"] == entry["run_key"])
        )
        if entry["status"] != "verified":
            entry["status"] = "failed"
            entry["error_summary"] = (
                "evaluator returned success without a verified package"
            )
            write_inventory(args.output_root, plan)
            return 1
        write_inventory(args.output_root, plan)
    write_inventory(args.output_root, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
