from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).parents[1] / "scripts" / "materialize_planet8b_folds.py"


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_baseline_materialization_selection_links_and_rerun(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    chips_dir = root / "chips" / "all"
    chips_dir.mkdir(parents=True)
    chip_rows: list[dict[str, str]] = []
    temporal_rows: list[dict[str, str]] = []
    selection_rows: list[dict[str, str]] = []
    cases = [
        ("r1", "TRAIN", "positive", "true", 0, 0),
        ("r1", "TRAIN", "clean_background_only", "false", 0, 0),
        ("r2", "VAL", "clean_background_only", "false", 0, 0),
        ("r2", "VAL", "positive", "true", 512, 0),
        ("r3", "TEST", "clean_background_only", "false", 512, 512),
        ("r3", "TEST", "positive", "true", 0, 0),
    ]
    split_dates = {"TRAIN": "2020-01-01", "VAL": "2021-01-01", "TEST": "2022-01-01"}
    for index, (region, split, presence, selected, row_off, col_off) in enumerate(
        cases
    ):
        source = f"source_{index}"
        chip_id = f"chip_{index}"
        chip_path = f"chips/all/{chip_id}.npz"
        np.savez_compressed(
            root / chip_path, image=np.zeros((2, 2, 8)), label=np.zeros((2, 2))
        )
        chip_rows.append(
            {
                "chip_id": chip_id,
                "chip_path": chip_path,
                "source_tiff_id": source,
                "dataset": "fixture",
                "region_id": region,
                "acquisition_date": split_dates[split],
                "row_off": str(row_off),
                "col_off": str(col_off),
            }
        )
        temporal_rows.append(
            {
                "image_name_stem": source,
                "split": split,
                "dataset": "fixture",
                "region_id": region,
                "acquisition_date": split_dates[split],
            }
        )
        selection_rows.append(
            {
                "chip_id": chip_id,
                "source_tiff_id": source,
                "region_id": region,
                "class_presence": presence,
                "selected_for_training": selected,
                "selection_reason": presence,
                "policy": "exclude_all",
            }
        )

    chip_manifest = root / "chips.csv"
    temporal = root / "temporal.csv"
    selection = root / "selection.csv"
    write_csv(chip_manifest, list(chip_rows[0]), chip_rows)
    write_csv(temporal, list(temporal_rows[0]), temporal_rows)
    write_csv(selection, list(selection_rows[0]), selection_rows)
    output = root / "views" / "baseline"
    command = [
        sys.executable,
        str(SCRIPT),
        "baseline",
        "--chip-root",
        str(root),
        "--chip-manifest",
        str(chip_manifest),
        "--temporal-splits",
        str(temporal),
        "--background-selection",
        str(selection),
        "--output-root",
        str(output),
        "--mode",
        "hardlink",
    ]

    subprocess.run([*command, "--dry-run"], check=True, capture_output=True, text=True)
    assert not output.exists()
    subprocess.run(command, check=True, capture_output=True, text=True)

    with (output / "fold_manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = {row["chip_id"]: row for row in csv.DictReader(handle)}
    assert len(rows) == 6
    assert rows["chip_0"]["experiment_split"] == "train"
    assert rows["chip_1"]["selection_reason"] == "background_policy_exclusion"
    assert rows["chip_2"]["experiment_split"] == "val"
    assert rows["chip_3"]["selection_reason"] == "validation_overlap_exclusion"
    assert rows["chip_4"]["selection_reason"] == "test_overlap_exclusion"
    assert rows["chip_5"]["experiment_split"] == "test"
    assert rows["chip_5"]["selected"] == "true"
    for row in rows.values():
        if row["view_path"]:
            assert (root / row["chip_path"]).stat().st_ino == (
                output / row["view_path"]
            ).stat().st_ino
    summary = json.loads((output / "fold_summary.json").read_text())
    assert summary["hard_link_count"] == 3
    rerun = subprocess.run(command, capture_output=True, text=True)
    assert rerun.returncode != 0
    assert "output already exists" in rerun.stderr


def test_loro_materialization_policy_all_folds_and_rerun(tmp_path: Path) -> None:
    root = tmp_path / "dataset"
    chips_dir = root / "chips" / "all"
    chips_dir.mkdir(parents=True)
    cases = [
        ("r1", "TRAIN", "clean_background_only", "false", 0, 0),
        ("r1", "VAL", "positive", "true", 512, 0),
        ("r1", "TEST", "positive", "true", 0, 0),
        ("r2", "TRAIN", "positive", "true", 512, 512),
        ("r2", "TRAIN", "clean_background_only", "false", 0, 0),
        ("r2", "VAL", "clean_background_only", "false", 0, 0),
        ("r2", "VAL", "positive", "true", 512, 0),
        ("r2", "TEST", "positive", "true", 0, 0),
        ("r3", "TRAIN", "positive", "true", 0, 0),
        ("r3", "VAL", "positive", "true", 0, 0),
        ("r3", "TEST", "clean_background_only", "false", 0, 0),
    ]
    split_dates = {"TRAIN": "2020-01-01", "VAL": "2021-01-01", "TEST": "2022-01-01"}
    chip_rows: list[dict[str, str]] = []
    temporal_rows: list[dict[str, str]] = []
    selection_rows: list[dict[str, str]] = []
    for index, (region, split, presence, selected, row_off, col_off) in enumerate(
        cases
    ):
        source = f"source_{index}"
        chip_id = f"chip_{index}"
        chip_path = f"chips/all/{chip_id}.npz"
        np.savez_compressed(
            root / chip_path,
            image=np.zeros((2, 2, 8)),
            label=np.zeros((2, 2)),
        )
        chip_rows.append(
            {
                "chip_id": chip_id,
                "chip_path": chip_path,
                "source_tiff_id": source,
                "dataset": "fixture",
                "region_id": region,
                "acquisition_date": split_dates[split],
                "row_off": str(row_off),
                "col_off": str(col_off),
            }
        )
        temporal_rows.append(
            {
                "image_name_stem": source,
                "split": split,
                "dataset": "fixture",
                "region_id": region,
                "acquisition_date": split_dates[split],
            }
        )
        selection_rows.append(
            {
                "chip_id": chip_id,
                "source_tiff_id": source,
                "region_id": region,
                "class_presence": presence,
                "selected_for_training": selected,
                "selection_reason": presence,
                "policy": "exclude_all",
            }
        )

    chip_manifest = root / "chips.csv"
    temporal = root / "temporal.csv"
    selection = root / "selection.csv"
    write_csv(chip_manifest, list(chip_rows[0]), chip_rows)
    write_csv(temporal, list(temporal_rows[0]), temporal_rows)
    write_csv(selection, list(selection_rows[0]), selection_rows)
    output = root / "views" / "loro"
    command = [
        sys.executable,
        str(SCRIPT),
        "loro",
        "--chip-root",
        str(root),
        "--chip-manifest",
        str(chip_manifest),
        "--temporal-splits",
        str(temporal),
        "--background-selection",
        str(selection),
        "--output-root",
        str(output),
        "--held-out-region",
        "all",
        "--mode",
        "hardlink",
    ]

    dry_run = subprocess.run(
        [*command, "--dry-run"], check=True, capture_output=True, text=True
    )
    assert len(json.loads(dry_run.stdout)["folds"]) == 3
    assert not output.exists()
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert sorted(path.name for path in output.iterdir()) == ["r1", "r2", "r3"]

    with (output / "r1" / "fold_manifest.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = {row["chip_id"]: row for row in csv.DictReader(handle)}
    assert len(rows) == len(cases)
    assert rows["chip_0"]["experiment_split"] == "test"
    assert rows["chip_0"]["selection_reason"] == "held_out_region_test"
    assert rows["chip_1"]["selection_reason"] == ("held_out_region_overlap_exclusion")
    assert rows["chip_2"]["experiment_split"] == "test"
    assert rows["chip_3"]["experiment_split"] == "train"
    assert rows["chip_4"]["selection_reason"] == "training_background_excluded"
    assert rows["chip_5"]["experiment_split"] == "val"
    assert rows["chip_5"]["selection_reason"] == "nonheldout_temporal_val"
    assert rows["chip_6"]["selection_reason"] == (
        "nonheldout_temporal_val_overlap_exclusion"
    )
    assert rows["chip_7"]["selection_reason"] == ("nonheldout_temporal_test_unused")
    assert {row["fold_id"] for row in rows.values()} == {"loro_r1"}
    assert {row["held_out_region"] for row in rows.values()} == {"r1"}
    for row in rows.values():
        if row["view_path"]:
            assert (root / row["chip_path"]).stat().st_ino == (
                output / "r1" / row["view_path"]
            ).stat().st_ino

    summary = json.loads((output / "r1" / "fold_summary.json").read_text())
    assert summary["hard_link_count"] == 6
    assert summary["selected_chip_counts"] == {"test": 2, "train": 2, "val": 2}
    assert summary["regions_by_split"]["test"] == ["r1"]
    assert summary["selected_bytes"] > 0
    assert summary["selected_inventory_by_region"]
    assert summary["selected_inventory_by_source_tiff"]
    assert summary["selected_inventory_by_acquisition_date"]
    assert summary["selected_inventory_by_class_presence"]

    rerun = subprocess.run(command, capture_output=True, text=True)
    assert rerun.returncode != 0
    assert "output already exists" in rerun.stderr
