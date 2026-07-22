#!/usr/bin/env python3
"""Run the validated PlanetScope baseline/LORO experiment matrix."""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.run_context import build_run_context, sha256_file, write_run_context

REGIONS = ["bc", *(f"ca_{index:03d}" for index in range(1, 12))]
STATUSES = {"planned", "running", "completed", "failed", "interrupted", "skipped"}
REGISTRY_FIELDS = [
    "timestamp",
    "experiment_version",
    "run_key",
    "run_type",
    "fold_id",
    "held_out_region",
    "status",
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
]


class RunnerError(RuntimeError):
    """Raised when the experiment matrix or registry is unsafe to execute."""


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text())
    if not isinstance(value, dict):
        raise RunnerError(f"Expected a YAML mapping in {path}")
    return value


def load_matrix(path: Path, repo_root: Path) -> dict[str, Any]:
    matrix = _load_yaml(path)
    required = {
        "experiment_version",
        "smoke_experiment_version",
        "dataset_root",
        "experiment_root",
        "model_config",
        "smoke_model_config",
        "seed",
        "max_epochs",
        "smoke_deep_run_keys",
        "smoke_deep_max_epochs",
        "smoke_shallow_max_epochs",
        "smoke_shallow_optimizer_updates",
        "smoke_shallow_limit_val_batches",
        "smoke_shallow_limit_test_batches",
        "execution_mode",
        "failure_policy",
        "runs",
    }
    missing = sorted(required - set(matrix))
    if missing:
        raise RunnerError(f"Matrix is missing keys: {missing}")
    if matrix["execution_mode"] != "sequential":
        raise RunnerError("Only sequential execution is approved")
    if matrix["failure_policy"] not in {"continue", "stop"}:
        raise RunnerError("failure_policy must be 'continue' or 'stop'")
    if matrix["max_epochs"] != 100:
        raise RunnerError("Approved production budget is 100 epochs")
    if (
        matrix["smoke_deep_run_keys"] != ["baseline-temporal-v1", "loro-bc-v1"]
        or matrix["smoke_deep_max_epochs"] != 2
        or matrix["smoke_shallow_max_epochs"] != 1
        or matrix["smoke_shallow_optimizer_updates"] != 2
        or matrix["smoke_shallow_limit_val_batches"] != 2
        or matrix["smoke_shallow_limit_test_batches"] != 2
    ):
        raise RunnerError("Matrix does not match the approved tiered smoke profile")
    runs = matrix["runs"]
    if not isinstance(runs, list) or len(runs) != 13:
        raise RunnerError("Matrix must contain exactly 13 runs")
    keys = [run.get("run_key") for run in runs]
    if len(set(keys)) != 13:
        raise RunnerError("Matrix run_key values must be unique")
    baselines = [run for run in runs if run.get("run_type") == "baseline_training"]
    loros = [run for run in runs if run.get("run_type") == "loro_training"]
    if len(baselines) != 1 or baselines[0].get("held_out_region") is not None:
        raise RunnerError("Matrix requires one baseline with no held-out region")
    if sorted(run.get("held_out_region") for run in loros) != REGIONS:
        raise RunnerError("Matrix requires exactly one LORO run per approved region")
    for field in ("model_config", "smoke_model_config"):
        resolved = (repo_root / matrix[field]).resolve()
        if not resolved.is_file():
            raise RunnerError(f"Missing {field}: {resolved}")
        matrix[field] = str(resolved)
    if matrix["model_config"] != matrix["smoke_model_config"]:
        raise RunnerError("Smoke and production must use one model config")
    matrix["dataset_root"] = str(Path(matrix["dataset_root"]).resolve())
    matrix["experiment_root"] = str(Path(matrix["experiment_root"]).resolve())
    return matrix


def read_events(registry: Path) -> list[dict[str, Any]]:
    if not registry.exists():
        return []
    events = []
    for number, line in enumerate(registry.read_text().splitlines(), start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RunnerError(f"Invalid registry JSONL line {number}: {exc}") from exc
        if event.get("status") not in STATUSES:
            raise RunnerError(f"Invalid registry status on line {number}")
        events.append(event)
    return events


def latest_states(
    events: list[dict[str, Any]], version: str
) -> dict[str, dict[str, Any]]:
    return {
        event["run_key"]: event
        for event in events
        if event.get("experiment_version") == version
    }


def validate_resume_checkpoint(
    checkpoint: Path,
    *,
    state: dict[str, Any] | None,
    run_key: str,
) -> Path:
    resolved = checkpoint.resolve()
    if not resolved.is_file():
        raise RunnerError(f"Resume checkpoint does not exist: {resolved}")
    if resolved.name != "last.ckpt":
        raise RunnerError("Resume requires the prior attempt's local last.ckpt")
    if not state or state.get("status") not in {"failed", "interrupted"}:
        raise RunnerError(f"Run {run_key} has no failed/interrupted attempt to resume")
    config_path = state.get("resolved_config_path")
    if not config_path:
        raise RunnerError(f"Run {run_key} has no recorded attempt root")
    attempt_root = Path(config_path).resolve().parent
    if not resolved.is_relative_to(attempt_root):
        raise RunnerError(
            f"Resume checkpoint is not owned by the prior {run_key} attempt"
        )
    return resolved


@contextmanager
def registry_lock(registry: Path) -> Iterator[None]:
    registry.parent.mkdir(parents=True, exist_ok=True)
    lock_path = registry.with_suffix(registry.suffix + ".lock")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def append_event(registry: Path, event: dict[str, Any]) -> None:
    with registry_lock(registry):
        with registry.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        states: dict[tuple[str, str], dict[str, Any]] = {}
        for row in read_events(registry):
            states[(row["experiment_version"], row["run_key"])] = row
        csv_path = registry.with_suffix(".csv")
        temporary = csv_path.with_name(f".{csv_path.name}.tmp")
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REGISTRY_FIELDS)
            writer.writeheader()
            for row in states.values():
                writer.writerow({field: row.get(field) for field in REGISTRY_FIELDS})
        temporary.replace(csv_path)


def _event(
    context: dict[str, Any], run: dict[str, Any], **values: Any
) -> dict[str, Any]:
    event = {field: None for field in REGISTRY_FIELDS}
    event.update(
        {
            "timestamp": datetime.now(UTC).isoformat(),
            "experiment_version": context["experiment_version"],
            "run_key": run["run_key"],
            "run_type": run["run_type"],
            "fold_id": run["fold_id"],
            "held_out_region": run.get("held_out_region"),
            "fold_manifest_path": context["source_artifacts"]["fold_manifest"],
            "fold_manifest_sha256": context["fold_manifest_sha256"],
            "git_commit": context["git_commit"],
            "git_dirty": context["git_dirty"],
            "hostname": context["hostname"],
        }
    )
    event.update(values)
    return event


def _resolved_config(
    base: Path,
    output: Path | None,
    root: Path,
    epochs: int,
    *,
    context: dict[str, Any] | None = None,
    limits: dict[str, int] | None = None,
) -> dict[str, Any]:
    config = _load_yaml(base)
    config["trainer"]["max_epochs"] = epochs
    config["trainer"]["default_root_dir"] = str(root)
    for key in ("limit_train_batches", "limit_val_batches", "limit_test_batches"):
        config["trainer"].pop(key, None)
    config["trainer"].update(limits or {})
    checkpoint = next(
        callback["init_args"]
        for callback in config["trainer"]["callbacks"]
        if callback["class_path"] == "lightning.pytorch.callbacks.ModelCheckpoint"
    )
    checkpoint["save_top_k"] = 1
    checkpoint["save_last"] = True
    if context is not None:
        config["data"]["init_args"].update(
            train_chip_dir=context["data_paths"]["train"],
            val_chip_dir=context["data_paths"]["val"],
            test_chip_dir=context["data_paths"]["test"],
        )
        logger = config["trainer"]["logger"][0]["init_args"]
        logger.update(
            entity=context["wandb_entity"],
            project=context["wandb_project"],
            group=context["wandb_group"],
            name=context["wandb_name"],
            job_type=context["wandb_job_type"],
            tags=context["wandb_tags"],
            offline=context["wandb_offline"],
            log_model=False,
            save_dir=str(root),
        )
    if output is None:
        return config
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RunnerError(f"Refusing to overwrite resolved config: {output}")
    output.write_text(yaml.safe_dump(config, sort_keys=False))
    return config


def _run_profile(
    matrix: dict[str, Any], run: dict[str, Any], config: dict[str, Any], smoke: bool
) -> tuple[int, dict[str, int]]:
    if not smoke:
        return matrix["max_epochs"], {}
    if run["run_key"] in matrix["smoke_deep_run_keys"]:
        return matrix["smoke_deep_max_epochs"], {}
    accumulation = config["trainer"]["accumulate_grad_batches"]
    return matrix["smoke_shallow_max_epochs"], {
        "limit_train_batches": (
            matrix["smoke_shallow_optimizer_updates"] * accumulation
        ),
        "limit_val_batches": matrix["smoke_shallow_limit_val_batches"],
        "limit_test_batches": matrix["smoke_shallow_limit_test_batches"],
    }


def _run_logged(command: list[str], log_path: Path, env: dict[str, str]) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        assert process.stdout is not None
        try:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log.write(line)
                log.flush()
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT)
            process.wait()
            raise
        return process.wait()


def _best_checkpoint(run_root: Path) -> Path:
    candidates = [path for path in run_root.rglob("*.ckpt") if path.name != "last.ckpt"]
    if len(candidates) != 1:
        raise RunnerError(
            f"Expected exactly one best checkpoint beneath {run_root}, found {len(candidates)}"
        )
    return candidates[0]


def _best_metric(checkpoint: Path) -> float | None:
    match = re.search(r"val-iou-([0-9]+(?:\.[0-9]+)?)", checkpoint.name)
    return float(match.group(1)) if match else None


def execute_run(
    matrix: dict[str, Any],
    run: dict[str, Any],
    registry: Path,
    repo_root: Path,
    *,
    smoke: bool,
    offline: bool,
    dry_run: bool,
    resume_checkpoint: Path | None,
) -> bool:
    version = (
        matrix["smoke_experiment_version"] if smoke else matrix["experiment_version"]
    )
    events = read_events(registry)
    states = latest_states(events, version)
    previous = states.get(run["run_key"], {})
    if previous.get("status") == "completed":
        print(f"SKIP completed {version}/{run['run_key']}")
        return True
    if previous.get("status") == "running":
        previous_host = previous.get("hostname")
        previous_pid = previous.get("runner_pid")
        if previous_host != os.uname().nodename:
            raise RunnerError(
                f"Run may still be active on {previous_host}: {run['run_key']}"
            )
        if previous_pid:
            try:
                os.kill(int(previous_pid), 0)
            except ProcessLookupError:
                pass
            else:
                raise RunnerError(
                    f"Run is already active in PID {previous_pid}: {run['run_key']}"
                )
        previous_pgid = previous.get("runner_pgid")
        if previous_pgid:
            try:
                os.killpg(int(previous_pgid), 0)
            except ProcessLookupError:
                pass
            else:
                raise RunnerError(
                    f"Run has an active process group {previous_pgid}: {run['run_key']}"
                )
        recovered = dict(previous)
        recovered.update(
            timestamp=datetime.now(UTC).isoformat(),
            status="interrupted",
            error_summary="recovered stale running entry; prior runner is not active",
        )
        append_event(registry, recovered)
    attempt = 1 + max(
        (
            int(event["attempt"])
            for event in events
            if event.get("experiment_version") == version
            and event.get("run_key") == run["run_key"]
            and event.get("attempt")
        ),
        default=0,
    )
    profile_root = Path(matrix["experiment_root"]) / version
    attempt_root = profile_root / "runs" / run["run_key"] / f"attempt-{attempt:02d}"
    model_config = Path(
        matrix["smoke_model_config"] if smoke else matrix["model_config"]
    )
    fold_root = Path(matrix["dataset_root"]) / run["fold_root"]
    context = build_run_context(
        dataset_root=Path(matrix["dataset_root"]),
        fold_root=fold_root,
        model_config_path=model_config,
        repo_root=repo_root,
        run_type=run["run_type"],
        fold_id=run["fold_id"],
        held_out_region=run.get("held_out_region"),
        seed=matrix["seed"],
        smoke=smoke,
        offline=offline,
    )
    context["experiment_version"] = version
    base_config = _load_yaml(model_config)
    epochs, limits = _run_profile(matrix, run, base_config, smoke)
    context["training_budget_epochs"] = epochs
    context["batch_limits"] = limits
    context["checkpoint_policy"] = "best_plus_local_last"
    resolved = attempt_root / "resolved_config.yaml"
    context_path = attempt_root / "run_context.json"
    resolved_config = _resolved_config(
        model_config,
        None,
        attempt_root,
        epochs,
        context=context,
        limits=limits,
    )
    fit_command = [
        "uv",
        "run",
        "python",
        "trainer.py",
        "fit",
        "--config",
        str(resolved),
        "--run_context",
        str(context_path),
    ]
    if resume_checkpoint:
        fit_command.extend(["--ckpt_path", str(resume_checkpoint.resolve())])
    if dry_run:
        print(
            json.dumps(
                {
                    "experiment_version": version,
                    "run_key": run["run_key"],
                    "epochs": epochs,
                    "fold_root": str(fold_root),
                    "fold_manifest_sha256": context["fold_manifest_sha256"],
                    "model_config_sha256": context["model_config_sha256"],
                    "batch_size": resolved_config["data"]["init_args"]["batch_size"],
                    "accumulate_grad_batches": resolved_config["trainer"][
                        "accumulate_grad_batches"
                    ],
                    "batch_limits": limits,
                    "data_paths": context["data_paths"],
                    "wandb": {
                        key: resolved_config["trainer"]["logger"][0]["init_args"][key]
                        for key in ("entity", "project", "group", "name", "job_type")
                    },
                    "checkpoint_root": str(attempt_root),
                    "fit_command": fit_command,
                },
                sort_keys=True,
            )
        )
        return True
    _resolved_config(
        model_config,
        resolved,
        attempt_root,
        epochs,
        context=context,
        limits=limits,
    )
    write_run_context(context, context_path)
    wandb_run_id = uuid.uuid4().hex[:8]
    common = {
        "attempt": attempt,
        "command": fit_command,
        "resolved_config_path": str(resolved),
        "run_context_path": str(context_path),
        "wandb_run_id": wandb_run_id,
        "runner_pid": os.getpid(),
        "runner_pgid": os.getpgrp(),
    }
    append_event(registry, _event(context, run, status="planned", **common))
    append_event(registry, _event(context, run, status="running", **common))
    env = os.environ.copy()
    env.update({"WANDB_RUN_ID": wandb_run_id, "WANDB_RESUME": "allow"})
    log_path = profile_root / "logs" / f"{run['run_key']}-attempt-{attempt:02d}.log"
    try:
        exit_code = _run_logged(fit_command, log_path, env)
        if exit_code:
            append_event(
                registry,
                _event(
                    context,
                    run,
                    status="failed",
                    exit_code=exit_code,
                    error_summary="fit command failed",
                    **common,
                ),
            )
            return False
        best = _best_checkpoint(attempt_root)
        test_command = [
            "uv",
            "run",
            "python",
            "trainer.py",
            "test",
            "--config",
            str(resolved),
            "--run_context",
            str(context_path),
            "--ckpt_path",
            str(best),
        ]
        test_exit = _run_logged(test_command, log_path, env)
        if test_exit:
            append_event(
                registry,
                _event(
                    context,
                    run,
                    status="failed",
                    exit_code=test_exit,
                    error_summary="test command failed",
                    checkpoint_path=str(best),
                    checkpoint_sha256=sha256_file(best),
                    best_metric=_best_metric(best),
                    **common,
                ),
            )
            return False
        append_event(
            registry,
            _event(
                context,
                run,
                status="completed",
                exit_code=0,
                checkpoint_path=str(best),
                checkpoint_sha256=sha256_file(best),
                best_metric=_best_metric(best),
                **common,
            ),
        )
        return True
    except KeyboardInterrupt:
        append_event(
            registry,
            _event(
                context,
                run,
                status="interrupted",
                error_summary="received keyboard interrupt",
                **common,
            ),
        )
        raise
    except Exception as exc:
        append_event(
            registry,
            _event(context, run, status="failed", error_summary=str(exc), **common),
        )
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--run", action="append", default=[])
    parser.add_argument("--pending", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--resume-checkpoint", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    matrix = load_matrix(args.matrix.resolve(), repo_root)
    registry = (
        args.registry or Path(matrix["experiment_root"]) / "experiment_registry.jsonl"
    ).resolve()
    if bool(args.run) == bool(args.pending):
        raise RunnerError("Select either one or more --run values or --pending")
    version = (
        matrix["smoke_experiment_version"]
        if args.smoke
        else matrix["experiment_version"]
    )
    run_by_key = {run["run_key"]: run for run in matrix["runs"]}
    if args.run:
        unknown = sorted(set(args.run) - set(run_by_key))
        if unknown:
            raise RunnerError(f"Unknown run keys: {unknown}")
        selected = [run_by_key[key] for key in args.run]
    else:
        states = latest_states(read_events(registry), version)
        selected = [
            run
            for run in matrix["runs"]
            if states.get(run["run_key"], {}).get("status") != "completed"
        ]
    if args.resume_checkpoint and len(selected) != 1:
        raise RunnerError("--resume-checkpoint requires exactly one selected run")
    if args.resume_checkpoint:
        states = latest_states(read_events(registry), version)
        args.resume_checkpoint = validate_resume_checkpoint(
            args.resume_checkpoint,
            state=states.get(selected[0]["run_key"]),
            run_key=selected[0]["run_key"],
        )
    failures = 0
    for run in selected:
        succeeded = execute_run(
            matrix,
            run,
            registry,
            repo_root,
            smoke=args.smoke,
            offline=args.offline,
            dry_run=args.dry_run,
            resume_checkpoint=args.resume_checkpoint,
        )
        if not succeeded:
            failures += 1
            if matrix["failure_policy"] == "stop":
                break
    return int(bool(failures))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as exc:
        raise SystemExit(f"error: {exc}") from exc
