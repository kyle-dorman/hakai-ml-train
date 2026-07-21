from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest
from jsonargparse import Namespace

from src.run_context import (
    ARCHIVE_SHA256,
    RunContextError,
    build_run_context,
    load_and_validate_run_context,
    sha256_file,
    write_run_context,
)
from trainer import apply_run_context_to_config


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path: Path, *, loro: bool = False) -> dict[str, Path]:
    dataset = tmp_path / "dataset"
    fold = dataset / "views" / ("ca_001" if loro else "baseline")
    for split in ("train", "val", "test"):
        (fold / split).mkdir(parents=True)
    chip_manifest = dataset / "manifests" / "chip_manifest.csv"
    _write_csv(
        chip_manifest,
        [
            {
                "chip_id": "train-chip",
                "source_tiff_id": "train-source",
                "region_id": "ca_002" if loro else "ca_001",
            }
        ],
    )
    metadata = {
        "dataset_version": "planet8b_all_regions_1024_512_v2",
        "manifest_sha256": {"chip_manifest.csv": sha256_file(chip_manifest)},
        "filtering": {"threshold_pct": 50},
        "background_selection": {"policy": "exclude_all"},
        "parameters": {
            "chip_size": 1024,
            "stride": 512,
            "num_bands": 8,
            "image_dtype": "uint16",
            "remap": [0, 1, 0, -100, 0],
            "ignore_index": -100,
        },
    }
    metadata_path = dataset / "metadata" / "dataset_parameters.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(json.dumps(metadata))
    (dataset / "metadata" / "remote_archive_verification.log").write_text(
        json.dumps({"archive_sha256": ARCHIVE_SHA256})
    )

    rows = [
        {
            "chip_id": "train-chip",
            "source_tiff_id": "train-source",
            "region_id": "ca_002" if loro else "ca_001",
            "acquisition_date": "2020-01-01",
            "experiment_split": "train",
            "selected": "true",
            "held_out_region": "ca_001" if loro else "",
        },
        {
            "chip_id": "val-chip",
            "source_tiff_id": "val-source",
            "region_id": "ca_003" if loro else "ca_001",
            "acquisition_date": "2021-01-01",
            "experiment_split": "val",
            "selected": "true",
            "held_out_region": "ca_001" if loro else "",
        },
        {
            "chip_id": "test-chip",
            "source_tiff_id": "test-source",
            "region_id": "ca_001",
            "acquisition_date": "2022-01-01",
            "experiment_split": "test",
            "selected": "true",
            "held_out_region": "ca_001" if loro else "",
        },
        {
            "chip_id": "excluded-chip",
            "source_tiff_id": "excluded-source",
            "region_id": "ca_001",
            "acquisition_date": "2022-01-01",
            "experiment_split": "",
            "selected": "false",
            "held_out_region": "ca_001" if loro else "",
        },
    ]
    _write_csv(fold / "fold_manifest.csv", rows)
    (fold / "fold_summary.json").write_text(
        json.dumps(
            {
                "mode": "loro" if loro else "baseline",
                "selected_chip_counts": {"train": 1, "val": 1, "test": 1},
                "selected_source_tiff_counts": {
                    "train": 1,
                    "val": 1,
                    "test": 1,
                },
            }
        )
    )
    model_config = tmp_path / "model.yaml"
    model_config.write_text("seed_everything: 42\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "tracked.txt").write_text("fixture\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    return {"dataset": dataset, "fold": fold, "model": model_config, "repo": repo}


def _build(paths: dict[str, Path], *, loro: bool = False) -> dict[str, object]:
    return build_run_context(
        dataset_root=paths["dataset"],
        fold_root=paths["fold"],
        model_config_path=paths["model"],
        repo_root=paths["repo"],
        run_type="loro_training" if loro else "baseline_training",
        fold_id="loro_ca_001" if loro else "baseline_temporal_v1",
        held_out_region="ca_001" if loro else None,
        seed=42,
        smoke=True,
        offline=True,
    )


def test_build_and_revalidate_baseline_context(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    context = _build(paths)
    output = tmp_path / "context.json"
    write_run_context(context, output)

    loaded = load_and_validate_run_context(output)

    assert loaded["wandb_entity"] == "kdorman90-ucla"
    assert loaded["wandb_project"] == "kelpseg"
    assert loaded["wandb_group"] == "smoke"
    assert loaded["wandb_name"] == "smoke-baseline-temporal-v1"
    assert loaded["held_out_region"] is None
    assert loaded["train_chip_count"] == 1
    assert loaded["train_date_range"] == {"min": "2020-01-01", "max": "2020-01-01"}
    assert loaded["checkpoint_policy"] == "best_plus_local_last"
    assert loaded["git_dirty"] is False


def test_changed_fold_manifest_fails_revalidation(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    output = tmp_path / "context.json"
    write_run_context(_build(paths), output)
    with (paths["fold"] / "fold_manifest.csv").open("a") as handle:
        handle.write("tampered\n")

    with pytest.raises(RunContextError, match="source hash changed for fold_manifest"):
        load_and_validate_run_context(output)


def test_missing_fold_manifest_hash_fails_revalidation(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    context = _build(paths)
    del context["source_sha256"]["fold_manifest"]
    output = tmp_path / "context.json"
    write_run_context(context, output)

    with pytest.raises(RunContextError, match="missing SHA-256 for fold_manifest"):
        load_and_validate_run_context(output)


def test_inconsistent_counts_fail_generation(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    summary_path = paths["fold"] / "fold_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["selected_chip_counts"]["train"] = 2
    summary_path.write_text(json.dumps(summary))

    with pytest.raises(RunContextError, match="do not match manifest"):
        _build(paths)


def test_loro_requires_and_validates_held_out_region(tmp_path: Path) -> None:
    paths = _fixture(tmp_path, loro=True)
    context = _build(paths, loro=True)
    assert context["held_out_region"] == "ca_001"
    assert context["test_regions"] == ["ca_001"]

    with pytest.raises(RunContextError, match="requires held_out_region"):
        build_run_context(
            dataset_root=paths["dataset"],
            fold_root=paths["fold"],
            model_config_path=paths["model"],
            repo_root=paths["repo"],
            run_type="loro_training",
            fold_id="loro_ca_001",
            held_out_region=None,
            seed=42,
        )


def test_config_injection_keeps_best_and_local_last_offline(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    context = _build(paths)
    config = Namespace(
        seed_everything=42,
        trainer=Namespace(
            default_root_dir="checkpoints",
            logger=[
                Namespace(
                    class_path="lightning.pytorch.loggers.WandbLogger",
                    init_args=Namespace(),
                )
            ],
            callbacks=[
                Namespace(
                    class_path="lightning.pytorch.callbacks.ModelCheckpoint",
                    init_args=Namespace(save_top_k=2, save_last=True),
                )
            ],
        ),
        data=Namespace(init_args=Namespace()),
    )

    apply_run_context_to_config(config, context)

    logger = config.trainer.logger[0].init_args
    checkpoint = config.trainer.callbacks[0].init_args
    assert logger.offline is True
    assert logger.log_model is False
    assert logger.group == "smoke"
    assert checkpoint.save_top_k == 1
    assert checkpoint.save_last is True
    assert config.data.init_args.test_chip_dir == context["data_paths"]["test"]
