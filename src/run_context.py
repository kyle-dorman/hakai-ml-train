"""Validated experiment identity and W&B metadata for PlanetScope 8-band runs."""

from __future__ import annotations

import csv
import hashlib
import json
import socket
import subprocess
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

EXPERIMENT_VERSION = "planet8b-loro-v1"
WANDB_ENTITY = "kdorman90-ucla"
WANDB_PROJECT = "kelpseg"
ARCHIVE_SHA256 = "1244ecfe2cc4cee624bb5661087f0126ea239367bda60efd823b4fcb9b7399db"
CONTEXT_SCHEMA_VERSION = 1
REQUIRED_CONTEXT_KEYS = {
    "experiment_version",
    "run_type",
    "fold_id",
    "held_out_region",
    "dataset_version",
    "archive_sha256",
    "chip_manifest_sha256",
    "fold_manifest_sha256",
    "train_tiff_count",
    "val_tiff_count",
    "test_tiff_count",
    "train_chip_count",
    "val_chip_count",
    "test_chip_count",
    "train_regions",
    "val_regions",
    "test_regions",
    "train_date_range",
    "val_date_range",
    "test_date_range",
    "nodata_threshold_pct",
    "background_policy",
    "chip_size",
    "chip_stride",
    "num_bands",
    "image_dtype",
    "label_remap",
    "ignore_index",
    "model_config_path",
    "seed",
    "git_commit",
    "git_dirty",
    "hostname",
}


class RunContextError(ValueError):
    """Raised when run identity or its source artifacts are inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RunContextError(f"Required JSON file does not exist: {path}")
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RunContextError(f"Could not read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RunContextError(f"Expected a JSON object in {path}")
    return value


def _read_json_receipt(path: Path) -> dict[str, Any]:
    """Read a JSON object from a receipt that may have progress lines first."""
    if not path.is_file():
        raise RunContextError(f"Required receipt does not exist: {path}")
    text = path.read_text()
    for offset, character in enumerate(text):
        if character != "{" or (offset and text[offset - 1] != "\n"):
            continue
        try:
            value = json.loads(text[offset:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise RunContextError(f"Could not find a valid JSON receipt in {path}")


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.is_file():
        raise RunContextError(f"Required CSV file does not exist: {path}")
    try:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames or []
            return list(reader), fields
    except OSError as exc:
        raise RunContextError(f"Could not read {path}: {exc}") from exc


def _git_state(repo_root: Path) -> tuple[str, bool]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RunContextError(
            f"Could not inspect git state at {repo_root}: {exc}"
        ) from exc
    return commit, bool(status.strip())


def _strict_selected(value: str, *, chip_id: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RunContextError(f"Invalid selected value {value!r} for chip {chip_id}")


def _date_range(values: set[str]) -> dict[str, str] | None:
    if not values:
        return None
    for value in values:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise RunContextError(
                f"Invalid acquisition_date in fold manifest: {value!r}"
            ) from exc
    return {"min": min(values), "max": max(values)}


def _fold_statistics(
    fold_manifest: Path,
    fold_summary: dict[str, Any],
    *,
    run_type: str,
    held_out_region: str | None,
) -> dict[str, Any]:
    rows, fields = _read_csv(fold_manifest)
    required = {
        "chip_id",
        "source_tiff_id",
        "region_id",
        "acquisition_date",
        "experiment_split",
        "selected",
    }
    missing = sorted(required - set(fields))
    if missing:
        raise RunContextError(f"Fold manifest is missing columns: {missing}")
    if not rows:
        raise RunContextError("Fold manifest is empty")
    chip_ids = [row["chip_id"] for row in rows]
    if len(chip_ids) != len(set(chip_ids)):
        raise RunContextError("Fold manifest contains duplicate chip_id values")

    chips: dict[str, int] = defaultdict(int)
    sources: dict[str, set[str]] = defaultdict(set)
    regions: dict[str, set[str]] = defaultdict(set)
    dates: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if not _strict_selected(row["selected"], chip_id=row["chip_id"]):
            continue
        split = row["experiment_split"]
        if split not in {"train", "val", "test"}:
            raise RunContextError(
                f"Selected chip {row['chip_id']} has invalid experiment_split {split!r}"
            )
        chips[split] += 1
        sources[split].add(row["source_tiff_id"])
        regions[split].add(row["region_id"])
        dates[split].add(row["acquisition_date"])

    expected_chips = fold_summary.get("selected_chip_counts")
    expected_sources = fold_summary.get("selected_source_tiff_counts")
    actual_chips = {split: chips[split] for split in ("train", "val", "test")}
    actual_sources = {split: len(sources[split]) for split in ("train", "val", "test")}
    if expected_chips != actual_chips:
        raise RunContextError(
            f"Fold summary chip counts {expected_chips!r} do not match manifest {actual_chips!r}"
        )
    if expected_sources != actual_sources:
        raise RunContextError(
            "Fold summary source-TIFF counts "
            f"{expected_sources!r} do not match manifest {actual_sources!r}"
        )

    mode = fold_summary.get("mode")
    if run_type == "baseline_training":
        if held_out_region is not None:
            raise RunContextError("Baseline context must not set held_out_region")
        if mode != "baseline":
            raise RunContextError(
                f"Expected baseline fold summary, found mode {mode!r}"
            )
    elif run_type == "loro_training":
        if not held_out_region:
            raise RunContextError("LORO context requires held_out_region")
        if mode != "loro":
            raise RunContextError(f"Expected LORO fold summary, found mode {mode!r}")
        manifest_regions = {row.get("held_out_region", "") for row in rows}
        if manifest_regions != {held_out_region}:
            raise RunContextError(
                "LORO manifest held_out_region values do not match requested region: "
                f"{sorted(manifest_regions)!r}"
            )
        if held_out_region in regions["train"] or held_out_region in regions["val"]:
            raise RunContextError("Held-out LORO region appears in train or validation")
        if regions["test"] != {held_out_region}:
            raise RunContextError(
                "LORO test rows do not belong exclusively to held_out_region"
            )
    else:
        raise RunContextError(f"Unsupported run_type: {run_type!r}")

    result: dict[str, Any] = {}
    for split in ("train", "val", "test"):
        result[f"{split}_chip_count"] = actual_chips[split]
        result[f"{split}_tiff_count"] = actual_sources[split]
        result[f"{split}_regions"] = sorted(regions[split])
        result[f"{split}_date_range"] = _date_range(dates[split])
    return result


def build_run_context(
    *,
    dataset_root: Path,
    fold_root: Path,
    model_config_path: Path,
    repo_root: Path,
    run_type: str,
    fold_id: str,
    held_out_region: str | None,
    seed: int,
    smoke: bool = False,
    offline: bool = False,
) -> dict[str, Any]:
    """Build and validate one immutable run-context record from source files."""
    dataset_root = dataset_root.resolve()
    fold_root = fold_root.resolve()
    model_config_path = model_config_path.resolve()
    repo_root = repo_root.resolve()
    if not fold_id.strip():
        raise RunContextError("fold_id must not be empty")
    if not model_config_path.is_file():
        raise RunContextError(f"Model config does not exist: {model_config_path}")
    for split in ("train", "val", "test"):
        if not (fold_root / split).is_dir():
            raise RunContextError(
                f"Fold split directory does not exist: {fold_root / split}"
            )

    dataset_metadata_path = dataset_root / "metadata" / "dataset_parameters.json"
    chip_manifest_path = dataset_root / "manifests" / "chip_manifest.csv"
    archive_receipt_path = dataset_root / "metadata" / "remote_archive_verification.log"
    fold_manifest_path = fold_root / "fold_manifest.csv"
    fold_summary_path = fold_root / "fold_summary.json"
    dataset_metadata = _read_json(dataset_metadata_path)
    archive_receipt = _read_json_receipt(archive_receipt_path)
    fold_summary = _read_json(fold_summary_path)

    chip_manifest_sha256 = sha256_file(chip_manifest_path)
    recorded_chip_hash = dataset_metadata.get("manifest_sha256", {}).get(
        "chip_manifest.csv"
    )
    if not recorded_chip_hash:
        raise RunContextError("Dataset metadata is missing the chip manifest SHA-256")
    if recorded_chip_hash != chip_manifest_sha256:
        raise RunContextError(
            "Canonical chip manifest hash does not match dataset metadata: "
            f"{chip_manifest_sha256} != {recorded_chip_hash}"
        )
    archive_sha256 = archive_receipt.get("archive_sha256")
    if archive_sha256 != ARCHIVE_SHA256:
        raise RunContextError(
            f"Unexpected archive SHA-256 {archive_sha256!r}; expected {ARCHIVE_SHA256}"
        )

    fold_stats = _fold_statistics(
        fold_manifest_path,
        fold_summary,
        run_type=run_type,
        held_out_region=held_out_region,
    )
    parameters = dataset_metadata.get("parameters", {})
    filtering = dataset_metadata.get("filtering", {})
    background = dataset_metadata.get("background_selection", {})
    git_commit, git_dirty = _git_state(repo_root)
    base_name = (
        "baseline-temporal-v1"
        if run_type == "baseline_training"
        else f"loro-{held_out_region}-v1"
    )

    context: dict[str, Any] = {
        "context_schema_version": CONTEXT_SCHEMA_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "run_type": run_type,
        "fold_id": fold_id,
        "held_out_region": held_out_region,
        "dataset_version": dataset_metadata.get("dataset_version"),
        "archive_sha256": archive_sha256,
        "chip_manifest_sha256": chip_manifest_sha256,
        "fold_manifest_sha256": sha256_file(fold_manifest_path),
        **fold_stats,
        "nodata_threshold_pct": filtering.get("threshold_pct"),
        "background_policy": background.get("policy"),
        "chip_size": parameters.get("chip_size"),
        "chip_stride": parameters.get("stride"),
        "num_bands": parameters.get("num_bands"),
        "image_dtype": parameters.get("image_dtype"),
        "label_remap": parameters.get("remap"),
        "ignore_index": parameters.get("ignore_index"),
        "model_config_path": str(model_config_path),
        "model_config_sha256": sha256_file(model_config_path),
        "seed": seed,
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "hostname": socket.gethostname(),
        "wandb_entity": WANDB_ENTITY,
        "wandb_project": WANDB_PROJECT,
        "wandb_group": "smoke" if smoke else EXPERIMENT_VERSION,
        "wandb_name": f"smoke-{base_name}" if smoke else base_name,
        "wandb_job_type": "smoke" if smoke else "train",
        "wandb_tags": [EXPERIMENT_VERSION, run_type, fold_id]
        + (["smoke"] if smoke else []),
        "wandb_offline": offline,
        "checkpoint_policy": "best_only",
        "source_artifacts": {
            "dataset_metadata": str(dataset_metadata_path),
            "archive_receipt": str(archive_receipt_path),
            "chip_manifest": str(chip_manifest_path),
            "fold_manifest": str(fold_manifest_path),
            "fold_summary": str(fold_summary_path),
            "model_config": str(model_config_path),
        },
        "source_sha256": {
            "dataset_metadata": sha256_file(dataset_metadata_path),
            "archive_receipt": sha256_file(archive_receipt_path),
            "chip_manifest": chip_manifest_sha256,
            "fold_manifest": sha256_file(fold_manifest_path),
            "fold_summary": sha256_file(fold_summary_path),
            "model_config": sha256_file(model_config_path),
        },
        "data_paths": {
            split: str(fold_root / split) for split in ("train", "val", "test")
        },
    }
    nullable_keys = {"held_out_region"} if run_type == "baseline_training" else set()
    missing_values = sorted(
        key for key in REQUIRED_CONTEXT_KEYS - nullable_keys if context.get(key) is None
    )
    if missing_values:
        raise RunContextError(
            f"Required run-context values are missing: {missing_values}"
        )
    return context


def write_run_context(context: dict[str, Any], output_path: Path) -> None:
    """Write a run context atomically without silently replacing an existing file."""
    output_path = output_path.resolve()
    if output_path.exists():
        raise RunContextError(
            f"Refusing to overwrite existing run context: {output_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    temporary.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n")
    temporary.replace(output_path)


def load_and_validate_run_context(path: Path) -> dict[str, Any]:
    """Reload a generated context and verify every identity-bearing source hash."""
    context = _read_json(path.resolve())
    missing = sorted(REQUIRED_CONTEXT_KEYS - set(context))
    if missing:
        raise RunContextError(f"Run context is missing required keys: {missing}")
    if context.get("context_schema_version") != CONTEXT_SCHEMA_VERSION:
        raise RunContextError("Unsupported run-context schema version")
    sources = context.get("source_artifacts")
    hashes = context.get("source_sha256")
    if not isinstance(sources, dict) or not isinstance(hashes, dict):
        raise RunContextError("Run context is missing source artifact hashes")
    for name, raw_path in sources.items():
        expected = hashes.get(name)
        if not expected:
            raise RunContextError(f"Run context is missing SHA-256 for {name}")
        actual = sha256_file(Path(raw_path))
        if actual != expected:
            raise RunContextError(
                f"Run-context source hash changed for {name}: {actual} != {expected}"
            )
    if hashes.get("fold_manifest") != context.get("fold_manifest_sha256"):
        raise RunContextError(
            "fold_manifest_sha256 does not match recorded source hash"
        )
    if hashes.get("chip_manifest") != context.get("chip_manifest_sha256"):
        raise RunContextError(
            "chip_manifest_sha256 does not match recorded source hash"
        )
    return context
