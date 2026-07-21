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
    append_event,
    latest_states,
    load_matrix,
    read_events,
    validate_resume_checkpoint,
)


def _matrix(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "production.yaml").write_text("trainer:\n  callbacks: []\n")
    (repo / "smoke.yaml").write_text("trainer:\n  callbacks: []\n")
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
        "model_config": "production.yaml",
        "smoke_model_config": "smoke.yaml",
        "seed": 42,
        "max_epochs": 100,
        "smoke_max_epochs": 1,
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
    assert matrix["smoke_max_epochs"] == 1

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
