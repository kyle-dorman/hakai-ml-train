from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from scripts.run_planet8b_predictions import REGIONS, build_plan, write_inventory


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_plan_only_verifies_complete_compatible_package(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    output_root = tmp_path / "predictions"
    events = []
    expected = ["baseline-temporal-v3", *(f"loro-{region}-v3" for region in REGIONS)]
    for index, run_key in enumerate(expected):
        checkpoint = tmp_path / f"{run_key}.ckpt"
        checkpoint.write_bytes(run_key.encode())
        fold = tmp_path / f"{run_key}.csv"
        fold.write_text(
            "chip_id,source_tiff_id,experiment_split,selected\n"
            f"chip_{index},source_{index},test,true\n"
        )
        events.append(
            {
                "experiment_version": "planet8b-loro-v3",
                "run_key": run_key,
                "run_type": "baseline_training" if index == 0 else "loro_training",
                "held_out_region": None if index == 0 else REGIONS[index - 1],
                "wandb_run_id": f"wandb-{index}",
                "status": "completed",
                "checkpoint_path": str(checkpoint),
                "checkpoint_sha256": _sha256(checkpoint),
                "fold_manifest_path": str(fold),
                "fold_manifest_sha256": _sha256(fold),
            }
        )
    registry.write_text("".join(json.dumps(event) + "\n" for event in events))

    baseline = output_root / "baseline-temporal-v3"
    source_predictions = baseline / "source_predictions"
    source_predictions.mkdir(parents=True)
    for suffix in ("probability.tif", "mask.tif"):
        (source_predictions / f"source_0_{suffix}").write_text("fixture")
    (source_predictions / "source_0.completion.json").write_text("fixture")
    for name in ("chip_diagnostics.csv", "tiff_metrics.csv", "region_metrics.csv"):
        (baseline / name).write_text("fixture")
    identity = events[0]
    (baseline / "evaluation_metadata.json").write_text(
        json.dumps(
            {
                "checkpoint_sha256": identity["checkpoint_sha256"],
                "fold_manifest_sha256": identity["fold_manifest_sha256"],
                "threshold": 0.5,
                "prediction_wandb_run_id": "prediction-0",
            }
        )
    )
    (baseline / "test_summary.json").write_text(
        json.dumps(
            {
                "checkpoint_sha256": identity["checkpoint_sha256"],
                "fold_manifest_sha256": identity["fold_manifest_sha256"],
                "threshold": 0.5,
                "test_chip_count": 1,
                "test_tiff_count": 1,
                "scored_pixel_count": 10,
                "uncovered_pixel_count": 2,
            }
        )
    )

    plan = build_plan(registry, output_root, version="planet8b-loro-v3")

    assert plan[0]["status"] == "verified"
    assert plan[0]["prediction_wandb_run_id"] == "prediction-0"
    assert all(entry["status"] == "pending" for entry in plan[1:])
    inventory = write_inventory(output_root, plan)
    with inventory.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["run_key"] for row in rows] == expected
    assert rows[0]["status"] == "verified"
