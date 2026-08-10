#!/usr/bin/env python3
"""Validate and launch the resumable PlanetScope v3 prediction suite."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.run_context import sha256_file

REGIONS = ["bc", *(f"ca_{number:03d}" for number in range(1, 12))]


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


def _test_scope(fold_manifest: Path) -> tuple[int, int]:
    with fold_manifest.open(newline="", encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["experiment_split"] == "test" and row["selected"].lower() == "true"
        ]
    return len(rows), len({row["source_tiff_id"] for row in rows})


def build_plan(
    registry: Path, output_root: Path, *, version: str
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
        chips, tiffs = _test_scope(fold)
        destination = output_root / run_key
        metadata = destination / "evaluation_metadata.json"
        completed = False
        if metadata.is_file():
            saved = json.loads(metadata.read_text())
            completed = (
                saved.get("checkpoint_sha256") == event["checkpoint_sha256"]
                and saved.get("fold_manifest_sha256") == event["fold_manifest_sha256"]
                and saved.get("threshold") == 0.5
                and (destination / "test_summary.json").is_file()
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
                "output_path": str(destination),
                "test_chip_count": chips,
                "test_tiff_count": tiffs,
                "status": "verified" if completed else "pending",
            }
        )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(
            "/home/sky/experiments/planet8b-loro-v3/experiment_registry.jsonl"
        ),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/home/sky/experiments/planet8b-loro-v3/predictions"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = build_plan(args.registry, args.output_root, version="planet8b-loro-v3")
    print(json.dumps(plan, indent=2, sort_keys=True))
    if not args.dry_run:
        raise PredictionRunnerError("Use --dry-run during Task 019 preparation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
