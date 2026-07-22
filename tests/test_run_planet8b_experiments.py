from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from run_planet8b_experiments import (
    REGIONS,
    RunnerError,
    _best_metric,
    _resolved_config,
    _run_profile,
    append_event,
    latest_states,
    load_matrix,
    read_events,
    validate_resume_checkpoint,
)


def _matrix(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "model.yaml").write_text(
        "trainer:\n  accumulate_grad_batches: 8\n  callbacks: []\n"
    )
    runs = [
        {
            "run_key": "baseline-temporal-v1",
            "run_type": "baseline_training",
            "fold_id": "baseline_temporal_v1",
            "fold_root": "views/baseline",
            "held_out_region": None,
        }
    ]
    runs.extend(
        {
            "run_key": f"loro-{region}-v1",
            "run_type": "loro_training",
            "fold_id": f"loro_{region}",
            "fold_root": f"views/loro/{region}",
            "held_out_region": region,
        }
        for region in REGIONS
    )
    matrix = {
        "experiment_version": "production",
        "smoke_experiment_version": "smoke-1epoch",
        "dataset_root": str(tmp_path / "dataset"),
        "experiment_root": str(tmp_path / "experiments"),
        "model_config": "model.yaml",
        "smoke_model_config": "model.yaml",
        "seed": 42,
        "max_epochs": 100,
        "smoke_deep_run_keys": ["baseline-temporal-v1", "loro-bc-v1"],
        "smoke_deep_max_epochs": 2,
        "smoke_shallow_max_epochs": 1,
        "smoke_shallow_optimizer_updates": 2,
        "smoke_shallow_limit_val_batches": 2,
        "smoke_shallow_limit_test_batches": 2,
        "execution_mode": "sequential",
        "failure_policy": "continue",
        "runs": runs,
    }
    path = tmp_path / "matrix.yaml"
    path.write_text(yaml.safe_dump(matrix))
    return path, repo


def test_matrix_requires_complete_approved_suite_and_budgets(tmp_path: Path) -> None:
    path, repo = _matrix(tmp_path)
    matrix = load_matrix(path, repo)
    assert len(matrix["runs"]) == 13
    assert matrix["max_epochs"] == 100
    assert matrix["smoke_deep_max_epochs"] == 2
    assert matrix["smoke_shallow_max_epochs"] == 1

    value = yaml.safe_load(path.read_text())
    value["runs"].pop()
    path.write_text(yaml.safe_dump(value))
    with pytest.raises(RunnerError, match="exactly 13"):
        load_matrix(path, repo)


def test_smoke_completion_does_not_complete_production_registry_state(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "registry.jsonl"
    base = {
        field: None
        for field in (
            "run_type",
            "fold_id",
            "held_out_region",
            "attempt",
            "command",
            "resolved_config_path",
            "run_context_path",
            "fold_manifest_path",
            "fold_manifest_sha256",
            "git_commit",
            "git_dirty",
            "hostname",
            "runner_pid",
            "runner_pgid",
            "wandb_run_id",
            "checkpoint_path",
            "checkpoint_sha256",
            "best_metric",
            "exit_code",
            "error_summary",
        )
    }
    append_event(
        registry,
        {
            **base,
            "timestamp": "2026-01-01T00:00:00+00:00",
            "experiment_version": "smoke-1epoch",
            "run_key": "baseline-temporal-v1",
            "status": "completed",
        },
    )
    events = read_events(registry)
    assert (
        latest_states(events, "smoke-1epoch")["baseline-temporal-v1"]["status"]
        == "completed"
    )
    assert latest_states(events, "production") == {}
    assert registry.with_suffix(".csv").is_file()


def test_resolved_config_sets_budget_root_and_recovery_checkpoint(
    tmp_path: Path,
) -> None:
    base = tmp_path / "base.yaml"
    base.write_text(
        """
trainer:
  max_epochs: 250
  default_root_dir: old
  callbacks:
    - class_path: lightning.pytorch.callbacks.ModelCheckpoint
      init_args:
        save_top_k: 2
        save_last: false
""".lstrip()
    )
    output = tmp_path / "resolved.yaml"
    run_root = tmp_path / "run"
    _resolved_config(base, output, run_root, 100)
    resolved = yaml.safe_load(output.read_text())
    assert resolved["trainer"]["max_epochs"] == 100
    assert resolved["trainer"]["default_root_dir"] == str(run_root)
    checkpoint = resolved["trainer"]["callbacks"][0]["init_args"]
    assert checkpoint == {"save_top_k": 1, "save_last": True}

    with pytest.raises(RunnerError, match="overwrite"):
        _resolved_config(base, output, run_root, 100)


def test_tiered_smoke_profile_has_deep_and_bounded_entries(tmp_path: Path) -> None:
    path, repo = _matrix(tmp_path)
    matrix = load_matrix(path, repo)
    config = yaml.safe_load(Path(matrix["model_config"]).read_text())
    baseline = matrix["runs"][0]
    bc = next(run for run in matrix["runs"] if run["run_key"] == "loro-bc-v1")
    shallow = next(run for run in matrix["runs"] if run["run_key"] == "loro-ca_001-v1")
    assert _run_profile(matrix, baseline, config, True) == (2, {})
    assert _run_profile(matrix, bc, config, True) == (2, {})
    assert _run_profile(matrix, shallow, config, True) == (
        1,
        {
            "limit_train_batches": 16,
            "limit_val_batches": 2,
            "limit_test_batches": 2,
        },
    )
    assert _run_profile(matrix, shallow, config, False) == (100, {})


def test_pure_resolution_injects_paths_wandb_limits_and_root(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    base = repo / "configs/kelp-ps8b/generalization/segformer_b3_v1.yaml"
    root = tmp_path / "attempt-01"
    context = {
        "data_paths": {
            "train": "/fold/train",
            "val": "/fold/val",
            "test": "/fold/test",
        },
        "wandb_entity": "kdorman90-ucla",
        "wandb_project": "kelpseg",
        "wandb_group": "smoke",
        "wandb_name": "smoke-loro-ca_001-v1",
        "wandb_job_type": "smoke",
        "wandb_tags": ["planet8b-loro-v1", "smoke"],
        "wandb_offline": True,
    }
    limits = {
        "limit_train_batches": 16,
        "limit_val_batches": 2,
        "limit_test_batches": 2,
    }
    resolved = _resolved_config(base, None, root, 1, context=context, limits=limits)
    assert resolved["trainer"]["max_epochs"] == 1
    assert resolved["trainer"]["default_root_dir"] == str(root)
    assert {key: resolved["trainer"][key] for key in limits} == limits
    assert resolved["data"]["init_args"]["train_chip_dir"] == "/fold/train"
    logger = resolved["trainer"]["logger"][0]["init_args"]
    assert (logger["entity"], logger["project"], logger["group"]) == (
        "kdorman90-ucla",
        "kelpseg",
        "smoke",
    )
    assert logger["save_dir"] == str(root)


def test_generalization_config_preserves_recipe_and_safety_contract() -> None:
    repo = Path(__file__).resolve().parents[1]
    config_path = repo / "configs/kelp-ps8b/generalization/segformer_b3_v1.yaml"
    matrix = yaml.safe_load(
        (
            repo / "configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml"
        ).read_text()
    )
    config = yaml.safe_load(config_path.read_text())
    model = config["model"]["init_args"]
    data = config["data"]["init_args"]
    trainer = config["trainer"]

    assert matrix["model_config"] == matrix["smoke_model_config"]
    assert matrix["model_config"].endswith("generalization/segformer_b3_v1.yaml")
    assert model["architecture"] == "Segformer"
    assert model["encoder_name"] == "mit_b3"
    assert model["model_opts"] == {"encoder_weights": "imagenet", "in_channels": 8}
    assert model["optimizer_opts"] == {
        "lr": 0.0003,
        "weight_decay": 0.01,
        "betas": [0.9, 0.95],
    }
    assert model["lr_scheduler_class"] == "src.schedulers.LinearWarmupCosineDecayLR"
    assert model["lr_scheduler_opts"] == {"warmup_epochs": 5, "min_lr": 0.000003}
    assert model["lr_scheduler_interval"] == "step"
    assert model["loss"] == "LabelSmoothingLovasz"
    assert model["loss_opts"] == {
        "mode": "binary",
        "ce_weight": 0.7,
        "lovasz_weight": 0.3,
        "ignore_index": -100,
    }
    assert model["ignore_index"] == -100
    assert data["batch_size"] * trainer["accumulate_grad_batches"] == 24
    assert trainer["max_epochs"] == 100
    callbacks = trainer["callbacks"]
    classes = [callback["class_path"] for callback in callbacks]
    assert classes.count("src.callbacks.EMAWeightAveraging") == 1
    assert "lightning.pytorch.callbacks.EarlyStopping" not in classes
    assert classes.count("lightning.pytorch.callbacks.ModelCheckpoint") == 1
    checkpoint = next(
        callback["init_args"]
        for callback in callbacks
        if callback["class_path"] == "lightning.pytorch.callbacks.ModelCheckpoint"
    )
    assert checkpoint["save_top_k"] == 1
    assert checkpoint["save_last"] is True
    assert len(trainer["logger"]) == 1
    logger = trainer["logger"][0]["init_args"]
    assert (logger["entity"], logger["project"], logger["group"]) == (
        "kdorman90-ucla",
        "kelpseg",
        "planet8b-loro-v1",
    )
    assert logger["log_model"] is False
    mask_transforms = [
        transform
        for group in (data["train_transforms"], data["test_transforms"])
        for transform in group["transform"]["transforms"]
        if "fill_mask" in transform
    ]
    assert {transform["__class_fullname__"] for transform in mask_transforms} == {
        "RandomCrop",
        "CoarseDropout",
        "PadIfNeeded",
    }
    assert all(transform["fill_mask"] == -100 for transform in mask_transforms)


def test_registry_rejects_invalid_jsonl(tmp_path: Path) -> None:
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps({"status": "unknown"}) + "\n")
    with pytest.raises(RunnerError, match="Invalid registry status"):
        read_events(registry)


def test_best_metric_is_read_from_checkpoint_name(tmp_path: Path) -> None:
    checkpoint = tmp_path / "model_epoch-00_val-iou-0.1429.ckpt"
    assert _best_metric(checkpoint) == 0.1429


def test_resume_checkpoint_must_belong_to_interrupted_attempt(tmp_path: Path) -> None:
    attempt = tmp_path / "run" / "attempt-01"
    attempt.mkdir(parents=True)
    checkpoint = attempt / "last.ckpt"
    checkpoint.write_bytes(b"checkpoint")
    state = {
        "status": "interrupted",
        "resolved_config_path": str(attempt / "resolved_config.yaml"),
    }
    assert (
        validate_resume_checkpoint(
            checkpoint, state=state, run_key="baseline-temporal-v1"
        )
        == checkpoint
    )
    foreign = tmp_path / "foreign" / "last.ckpt"
    foreign.parent.mkdir()
    foreign.write_bytes(b"checkpoint")
    with pytest.raises(RunnerError, match="not owned"):
        validate_resume_checkpoint(foreign, state=state, run_key="baseline-temporal-v1")
