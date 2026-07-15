"""Filter canonical NPZ chips from manifest nodata percentages.

Dry runs only write a selection report. Apply runs quarantine rejected chips,
atomically replace the active manifest, preserve versioned evidence, and use a
small transaction record to recover safely from interruptions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

REQUIRED_MANIFEST_COLUMNS = [
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "nodata_pixel_count",
    "total_pixel_count",
    "nodata_pct",
]
REPORT_COLUMNS = [
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "nodata_pixel_count",
    "total_pixel_count",
    "nodata_pct",
    "threshold_pct",
    "action",
    "reason",
]
TRANSACTION_SCHEMA = "nodata-filter-transaction-v1"
METADATA_SCHEMA = "nodata-filter-v1"
POST_COMMIT_PHASES = {
    "manifest_replaced",
    "evidence_published",
    "deleting_quarantine",
    "quarantine_deleted",
}


@dataclass(frozen=True)
class FilterResult:
    """Summary returned by dry-run, apply, and idempotent apply calls."""

    mode: str
    status: str
    threshold_pct: str
    total_count: int
    kept_count: int
    removed_count: int
    report_output: Path
    history_dir: Path | None = None


def parse_threshold(value: str | Decimal | float | int) -> Decimal:
    """Parse one finite percentage in the inclusive range [0, 100]."""
    try:
        threshold = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("--max-nodata-pct must be a number in [0, 100]") from error
    if not threshold.is_finite() or threshold < 0 or threshold > 100:
        raise ValueError("--max-nodata-pct must be a finite percentage in [0, 100]")
    return threshold


def _argparse_threshold(value: str) -> Decimal:
    try:
        return parse_threshold(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _threshold_text(threshold: Decimal) -> str:
    normalized = format(threshold.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _temporary_path(path: Path) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    return Path(name)


def _publish_temporary(temporary: Path, path: Path, *, overwrite: bool) -> None:
    try:
        if path.exists() and not overwrite:
            if _sha256(temporary) == _sha256(path):
                temporary.unlink()
                return
            raise FileExistsError(
                f"Refusing to overwrite existing artifact with different content: {path}"
            )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_csv_atomic(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
    *,
    overwrite: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        with temporary.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())
        _publish_temporary(temporary, path, overwrite=overwrite)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json_atomic(
    path: Path, payload: dict[str, Any], *, overwrite: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        with temporary.open("w") as file:
            json.dump(payload, file, indent=2, sort_keys=True)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        _publish_temporary(temporary, path, overwrite=overwrite)
    finally:
        temporary.unlink(missing_ok=True)


def _copy_atomic(source: Path, destination: Path, *, overwrite: bool = False) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(destination)
    try:
        shutil.copyfile(source, temporary)
        with temporary.open("rb") as file:
            os.fsync(file.fileno())
        _publish_temporary(temporary, destination, overwrite=overwrite)
    finally:
        temporary.unlink(missing_ok=True)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"CSV does not exist: {path}")
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV has no header: {path}")
        fieldnames = reader.fieldnames
        if len(fieldnames) != len(set(fieldnames)):
            raise RuntimeError(f"CSV contains duplicate columns: {path}")
        rows = list(reader)
    if any(None in row for row in rows):
        raise RuntimeError(f"CSV row has more values than columns: {path}")
    return fieldnames, rows


def _chip_path(chip_root: Path, value: str) -> Path:
    if not value or "\\" in value:
        raise RuntimeError(f"chip_path must be a nonempty POSIX path: {value!r}")
    relative = PurePosixPath(value)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise RuntimeError(f"chip_path must stay within the chip root: {value!r}")
    candidate = (chip_root / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(chip_root.resolve())
    except ValueError as error:
        raise RuntimeError(f"chip_path escapes the chip root: {value!r}") from error
    return candidate


def _validate_manifest(
    manifest: Path,
    chip_root: Path,
    *,
    require_files: bool,
) -> tuple[list[str], list[dict[str, str]]]:
    fieldnames, rows = _read_csv(manifest)
    missing_columns = sorted(set(REQUIRED_MANIFEST_COLUMNS) - set(fieldnames))
    if missing_columns:
        raise RuntimeError(
            f"Manifest lacks required columns {missing_columns}: {manifest}"
        )

    chip_ids: set[str] = set()
    chip_paths: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        chip_id = row["chip_id"].strip()
        if not chip_id:
            raise RuntimeError(f"Blank chip_id at manifest line {line_number}")
        folded_id = chip_id.casefold()
        if folded_id in chip_ids:
            raise RuntimeError(
                f"Duplicate chip_id at manifest line {line_number}: {chip_id}"
            )
        chip_ids.add(folded_id)

        relative_path = row["chip_path"]
        folded_path = relative_path.casefold()
        if folded_path in chip_paths:
            raise RuntimeError(
                f"Duplicate chip_path at manifest line {line_number}: {relative_path}"
            )
        chip_paths.add(folded_path)
        path = _chip_path(chip_root, relative_path)
        if require_files and not path.is_file():
            raise FileNotFoundError(
                f"Manifest chip is missing at line {line_number}: {path}"
            )

        try:
            nodata_count = int(row["nodata_pixel_count"])
            total_count = int(row["total_pixel_count"])
            nodata_pct = Decimal(row["nodata_pct"])
        except (InvalidOperation, ValueError) as error:
            raise RuntimeError(
                f"Invalid nodata statistics at manifest line {line_number}"
            ) from error
        if total_count <= 0:
            raise RuntimeError(
                f"total_pixel_count must be positive at manifest line {line_number}"
            )
        if nodata_count < 0 or nodata_count > total_count:
            raise RuntimeError(
                f"nodata_pixel_count is outside [0, total] at line {line_number}"
            )
        if not nodata_pct.is_finite() or nodata_pct < 0 or nodata_pct > 100:
            raise RuntimeError(f"nodata_pct is outside [0, 100] at line {line_number}")
        expected_pct = 100.0 * nodata_count / total_count
        if not math.isclose(
            float(nodata_pct), expected_pct, rel_tol=1e-12, abs_tol=1e-10
        ):
            raise RuntimeError(
                "nodata_pct is inconsistent with nodata_pixel_count and "
                f"total_pixel_count at line {line_number}: "
                f"stored={nodata_pct}, expected={expected_pct}"
            )
    return fieldnames, rows


def _build_report(
    rows: list[dict[str, str]], threshold: Decimal
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    threshold_text = _threshold_text(threshold)
    report_rows: list[dict[str, str]] = []
    kept_rows: list[dict[str, str]] = []
    removed_rows: list[dict[str, str]] = []
    for row in rows:
        remove = Decimal(row["nodata_pct"]) > threshold
        action = "remove" if remove else "keep"
        reason = (
            "nodata_pct_above_threshold"
            if remove
            else "nodata_pct_at_or_below_threshold"
        )
        report_rows.append(
            {
                **{column: row[column] for column in REPORT_COLUMNS[:8]},
                "threshold_pct": threshold_text,
                "action": action,
                "reason": reason,
            }
        )
        (removed_rows if remove else kept_rows).append(row)
    return report_rows, kept_rows, removed_rows


def _ensure_manifest_location(chip_root: Path, manifest: Path) -> Path:
    root = chip_root.resolve()
    resolved = manifest.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError("--manifest must be inside the chip root") from error
    if relative == Path("."):
        raise RuntimeError("--manifest must name a CSV file inside the chip root")
    return relative


def _history_paths(chip_root: Path, threshold: Decimal) -> tuple[Path, Path]:
    name = f"nodata_{_threshold_text(threshold)}"
    return (
        chip_root / "filter_history" / name,
        chip_root / ".nodata_filter_transactions" / name,
    )


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read transaction metadata: {path}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return value


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _row_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["chip_id"]: row for row in rows}


def _validate_reconciliation(
    pre_rows: list[dict[str, str]],
    active_rows: list[dict[str, str]],
    removed_rows: list[dict[str, str]],
) -> None:
    pre = _row_map(pre_rows)
    active = _row_map(active_rows)
    removed = _row_map(removed_rows)
    overlap = set(active) & set(removed)
    if overlap:
        raise RuntimeError(
            f"Active and removal manifests overlap: {sorted(overlap)[:5]}"
        )
    if set(pre) != set(active) | set(removed):
        raise RuntimeError("Active plus removal manifest IDs do not equal the snapshot")
    for chip_id, row in {**active, **removed}.items():
        if row != pre[chip_id]:
            raise RuntimeError(f"Manifest row changed during filtering: {chip_id}")


def _count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(row[key] for row in rows).items()))


def _transaction_metadata(
    *,
    chip_root: Path,
    manifest_relative: Path,
    report_output: Path,
    history_dir: Path,
    threshold: Decimal,
    pre_hash: str,
    post_hash: str,
    report_hash: str,
    pre_count: int,
    kept_count: int,
    removed_count: int,
    producer_command: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": TRANSACTION_SCHEMA,
        "phase": "prepared",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "threshold_pct": _threshold_text(threshold),
        "selection_rule": "keep nodata_pct <= threshold_pct; remove nodata_pct > threshold_pct",
        "chip_root": str(chip_root.resolve()),
        "manifest_path": manifest_relative.as_posix(),
        "report_path": str(report_output.resolve()),
        "history_dir": str(history_dir.resolve()),
        "pre_manifest_sha256": pre_hash,
        "post_manifest_sha256": post_hash,
        "report_sha256": report_hash,
        "pre_filter_count": pre_count,
        "retained_count": kept_count,
        "removed_count": removed_count,
        "producer_command": producer_command,
        "git_commit": _git_commit(),
    }


def _update_phase(transaction_dir: Path, metadata: dict[str, Any], phase: str) -> None:
    metadata["phase"] = phase
    _write_json_atomic(transaction_dir / "transaction.json", metadata, overwrite=True)


def _rollback_transaction(
    *,
    chip_root: Path,
    manifest: Path,
    transaction_dir: Path,
    transaction: dict[str, Any],
) -> None:
    if _sha256(manifest) != transaction["pre_manifest_sha256"]:
        raise RuntimeError(
            "Cannot roll back: active manifest is not the pre-filter manifest"
        )
    removal_manifest = transaction_dir / "removal_manifest.csv"
    _, removed_rows = _read_csv(removal_manifest)
    quarantine = transaction_dir / "quarantine"
    for row in removed_rows:
        active_path = _chip_path(chip_root, row["chip_path"])
        quarantined_path = quarantine / Path(*PurePosixPath(row["chip_path"]).parts)
        if active_path.exists() and quarantined_path.exists():
            raise RuntimeError(
                f"Cannot roll back because chip exists in both locations: {row['chip_path']}"
            )
        if quarantined_path.exists():
            active_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(quarantined_path, active_path)
        elif not active_path.is_file():
            raise RuntimeError(
                f"Cannot roll back because chip is missing in both locations: {row['chip_path']}"
            )
    _validate_manifest(manifest, chip_root, require_files=True)
    shutil.rmtree(transaction_dir)
    with suppress(OSError):
        transaction_dir.parent.rmdir()


def _build_filter_metadata(
    *,
    transaction: dict[str, Any],
    pre_rows: list[dict[str, str]],
    active_rows: list[dict[str, str]],
    removed_rows: list[dict[str, str]],
    snapshot: Path,
    removal_manifest: Path,
) -> dict[str, Any]:
    return {
        "schema_version": METADATA_SCHEMA,
        "status": "complete",
        "started_at_utc": transaction["started_at_utc"],
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "threshold_pct": transaction["threshold_pct"],
        "selection_rule": transaction["selection_rule"],
        "nodata_definition": "a pixel whose retained image bands are all zero",
        "chip_root": transaction["chip_root"],
        "manifest_path": transaction["manifest_path"],
        "report_path": transaction["report_path"],
        "pre_filter_manifest": snapshot.name,
        "removal_manifest": removal_manifest.name,
        "pre_manifest_sha256": transaction["pre_manifest_sha256"],
        "post_manifest_sha256": transaction["post_manifest_sha256"],
        "report_sha256": transaction["report_sha256"],
        "pre_filter_manifest_sha256": _sha256(snapshot),
        "removal_manifest_sha256": _sha256(removal_manifest),
        "pre_filter_count": len(pre_rows),
        "retained_count": len(active_rows),
        "removed_count": len(removed_rows),
        "removed_source_tiff_count": len(
            {row["source_tiff_id"] for row in removed_rows}
        ),
        "pre_count_by_dataset": _count_by(pre_rows, "dataset"),
        "retained_count_by_dataset": _count_by(active_rows, "dataset"),
        "removed_count_by_dataset": _count_by(removed_rows, "dataset"),
        "pre_count_by_region": _count_by(pre_rows, "region_id"),
        "retained_count_by_region": _count_by(active_rows, "region_id"),
        "removed_count_by_region": _count_by(removed_rows, "region_id"),
        "producer_command": transaction["producer_command"],
        "git_commit": transaction["git_commit"],
        "mutation_strategy": (
            "same-root quarantine, atomic active-manifest replacement, "
            "hash-based interruption recovery, quarantine deletion after validation"
        ),
    }


def _finalize_transaction(
    *,
    chip_root: Path,
    manifest: Path,
    history_dir: Path,
    transaction_dir: Path,
    transaction: dict[str, Any],
) -> None:
    if _sha256(manifest) != transaction["post_manifest_sha256"]:
        raise RuntimeError("Cannot finalize: active manifest is not the staged result")
    active_fields, active_rows = _validate_manifest(
        manifest, chip_root, require_files=True
    )
    pre_snapshot = transaction_dir / "pre_filter_manifest.csv"
    removal_staged = transaction_dir / "removal_manifest.csv"
    pre_fields, pre_rows = _validate_manifest(
        pre_snapshot, chip_root, require_files=False
    )
    removal_fields, removed_rows = _validate_manifest(
        removal_staged, chip_root, require_files=False
    )
    if active_fields != pre_fields or removal_fields != pre_fields:
        raise RuntimeError("Snapshot, active, and removal manifest schemas differ")
    _validate_reconciliation(pre_rows, active_rows, removed_rows)

    quarantine = transaction_dir / "quarantine"
    resuming_quarantine_deletion = transaction.get("phase") in (
        POST_COMMIT_PHASES - {"manifest_replaced"}
    )
    for row in removed_rows:
        if _chip_path(chip_root, row["chip_path"]).exists():
            raise RuntimeError(f"Rejected chip remains active: {row['chip_path']}")
        quarantined_path = quarantine / Path(*PurePosixPath(row["chip_path"]).parts)
        if not quarantined_path.is_file() and not resuming_quarantine_deletion:
            raise RuntimeError(
                f"Rejected chip is missing from quarantine: {row['chip_path']}"
            )

    history_dir.mkdir(parents=True, exist_ok=True)
    final_snapshot = history_dir / "pre_filter_manifest.csv"
    final_removal = history_dir / "removal_manifest.csv"
    _copy_atomic(pre_snapshot, final_snapshot)
    _copy_atomic(removal_staged, final_removal)
    _update_phase(transaction_dir, transaction, "evidence_published")
    _update_phase(transaction_dir, transaction, "deleting_quarantine")
    shutil.rmtree(quarantine, ignore_errors=resuming_quarantine_deletion)
    if quarantine.exists():
        raise RuntimeError("Quarantine cleanup did not complete")
    _update_phase(transaction_dir, transaction, "quarantine_deleted")
    metadata = _build_filter_metadata(
        transaction=transaction,
        pre_rows=pre_rows,
        active_rows=active_rows,
        removed_rows=removed_rows,
        snapshot=final_snapshot,
        removal_manifest=final_removal,
    )
    _write_json_atomic(history_dir / "filter_metadata.json", metadata)
    shutil.rmtree(transaction_dir)
    with suppress(OSError):
        transaction_dir.parent.rmdir()


def _verify_completed_application(
    *,
    chip_root: Path,
    manifest: Path,
    report_output: Path,
    history_dir: Path,
    threshold: Decimal,
) -> FilterResult:
    metadata = _load_json(history_dir / "filter_metadata.json")
    if (
        metadata.get("schema_version") != METADATA_SCHEMA
        or metadata.get("status") != "complete"
    ):
        raise RuntimeError(
            f"Filter history is not a completed {METADATA_SCHEMA} application"
        )
    threshold_text = _threshold_text(threshold)
    if metadata.get("threshold_pct") != threshold_text:
        raise RuntimeError("Completed filter history uses a different threshold")
    if _sha256(manifest) != metadata.get("post_manifest_sha256"):
        raise RuntimeError(
            "Active manifest hash does not match completed filter metadata"
        )

    snapshot = history_dir / metadata["pre_filter_manifest"]
    removal_manifest = history_dir / metadata["removal_manifest"]
    pre_fields, pre_rows = _validate_manifest(snapshot, chip_root, require_files=False)
    active_fields, active_rows = _validate_manifest(
        manifest, chip_root, require_files=True
    )
    removal_fields, removed_rows = _validate_manifest(
        removal_manifest, chip_root, require_files=False
    )
    if pre_fields != active_fields or pre_fields != removal_fields:
        raise RuntimeError("Completed filter manifest schemas differ")
    _validate_reconciliation(pre_rows, active_rows, removed_rows)
    for row in removed_rows:
        if _chip_path(chip_root, row["chip_path"]).exists():
            raise RuntimeError(
                f"Removed chip still exists in the active collection: {row['chip_path']}"
            )
    if _sha256(snapshot) != metadata.get("pre_filter_manifest_sha256"):
        raise RuntimeError("Pre-filter snapshot hash does not match filter metadata")
    if _sha256(removal_manifest) != metadata.get("removal_manifest_sha256"):
        raise RuntimeError("Removal manifest hash does not match filter metadata")

    report_rows, kept_rows, selected_removed = _build_report(pre_rows, threshold)
    if _row_map(kept_rows) != _row_map(active_rows) or _row_map(
        selected_removed
    ) != _row_map(removed_rows):
        raise RuntimeError("Completed filter rows do not match threshold selection")
    _write_csv_atomic(report_output, report_rows, REPORT_COLUMNS)
    if _sha256(report_output) != metadata.get("report_sha256"):
        raise RuntimeError("Report hash does not match completed filter metadata")
    return FilterResult(
        mode="apply",
        status="already_applied",
        threshold_pct=threshold_text,
        total_count=len(pre_rows),
        kept_count=len(active_rows),
        removed_count=len(removed_rows),
        report_output=report_output,
        history_dir=history_dir,
    )


def filter_nodata_chips(
    *,
    chip_root: Path,
    manifest: Path,
    max_nodata_pct: str | Decimal | float | int,
    report_output: Path,
    apply: bool,
    failure_hook: Callable[[str], None] | None = None,
    producer_command: str | None = None,
) -> FilterResult:
    """Run a manifest-only selection and optionally apply it transactionally."""
    threshold = parse_threshold(max_nodata_pct)
    threshold_text = _threshold_text(threshold)
    chip_root = chip_root.resolve()
    manifest = manifest.resolve()
    report_output = report_output.resolve()
    if not chip_root.is_dir():
        raise NotADirectoryError(f"Chip root does not exist: {chip_root}")
    manifest_relative = _ensure_manifest_location(chip_root, manifest)
    if report_output == manifest:
        raise RuntimeError("--report-output cannot replace the active manifest")
    history_dir, transaction_dir = _history_paths(chip_root, threshold)
    try:
        report_output.relative_to(transaction_dir.parent)
    except ValueError:
        pass
    else:
        raise RuntimeError("--report-output cannot be inside transaction staging")

    if apply:
        transaction_root = transaction_dir.parent
        if transaction_root.exists():
            other_transactions = sorted(
                path for path in transaction_root.iterdir() if path != transaction_dir
            )
            if other_transactions:
                raise RuntimeError(
                    "Another nodata-filter transaction must be resolved first: "
                    f"{other_transactions[0]}"
                )
        metadata_path = history_dir / "filter_metadata.json"
        if metadata_path.exists():
            result = _verify_completed_application(
                chip_root=chip_root,
                manifest=manifest,
                report_output=report_output,
                history_dir=history_dir,
                threshold=threshold,
            )
            if transaction_dir.exists():
                quarantine = transaction_dir / "quarantine"
                if quarantine.exists() and any(quarantine.rglob("*")):
                    raise RuntimeError(
                        "Completed history exists alongside a nonempty transaction quarantine"
                    )
                shutil.rmtree(transaction_dir)
                with suppress(OSError):
                    transaction_dir.parent.rmdir()
            return result

        if transaction_dir.exists():
            transaction = _load_json(transaction_dir / "transaction.json")
            if transaction.get("schema_version") != TRANSACTION_SCHEMA:
                raise RuntimeError("Unsupported nodata-filter transaction schema")
            if transaction.get("threshold_pct") != threshold_text:
                raise RuntimeError("Pending transaction uses a different threshold")
            if transaction.get("manifest_path") != manifest_relative.as_posix():
                raise RuntimeError("Pending transaction targets a different manifest")
            active_hash = _sha256(manifest)
            if active_hash == transaction["post_manifest_sha256"] and (
                transaction["post_manifest_sha256"]
                != transaction["pre_manifest_sha256"]
                or transaction.get("phase") in POST_COMMIT_PHASES
            ):
                _finalize_transaction(
                    chip_root=chip_root,
                    manifest=manifest,
                    history_dir=history_dir,
                    transaction_dir=transaction_dir,
                    transaction=transaction,
                )
                return _verify_completed_application(
                    chip_root=chip_root,
                    manifest=manifest,
                    report_output=report_output,
                    history_dir=history_dir,
                    threshold=threshold,
                )
            if active_hash == transaction["pre_manifest_sha256"]:
                _rollback_transaction(
                    chip_root=chip_root,
                    manifest=manifest,
                    transaction_dir=transaction_dir,
                    transaction=transaction,
                )
            else:
                raise RuntimeError(
                    "Pending transaction cannot be recovered because the active manifest "
                    "matches neither its pre-filter nor post-filter hash"
                )

        partial_artifacts = [
            history_dir / "pre_filter_manifest.csv",
            history_dir / "removal_manifest.csv",
        ]
        if any(path.exists() for path in partial_artifacts):
            raise RuntimeError(
                f"Incomplete filter history exists without a recoverable transaction: {history_dir}"
            )

    fieldnames, rows = _validate_manifest(manifest, chip_root, require_files=True)
    report_rows, kept_rows, removed_rows = _build_report(rows, threshold)
    _write_csv_atomic(report_output, report_rows, REPORT_COLUMNS)
    if not apply:
        return FilterResult(
            mode="dry-run",
            status="reported",
            threshold_pct=threshold_text,
            total_count=len(rows),
            kept_count=len(kept_rows),
            removed_count=len(removed_rows),
            report_output=report_output,
        )

    transaction_dir.mkdir(parents=True)
    quarantine = transaction_dir / "quarantine"
    quarantine.mkdir()
    pre_snapshot = transaction_dir / "pre_filter_manifest.csv"
    removal_staged = transaction_dir / "removal_manifest.csv"
    post_staged = transaction_dir / "post_filter_manifest.csv"
    _copy_atomic(manifest, pre_snapshot)
    _write_csv_atomic(removal_staged, removed_rows, fieldnames)
    _write_csv_atomic(post_staged, kept_rows, fieldnames)
    transaction = _transaction_metadata(
        chip_root=chip_root,
        manifest_relative=manifest_relative,
        report_output=report_output,
        history_dir=history_dir,
        threshold=threshold,
        pre_hash=_sha256(manifest),
        post_hash=_sha256(post_staged),
        report_hash=_sha256(report_output),
        pre_count=len(rows),
        kept_count=len(kept_rows),
        removed_count=len(removed_rows),
        producer_command=producer_command,
    )
    _write_json_atomic(transaction_dir / "transaction.json", transaction)

    try:
        _update_phase(transaction_dir, transaction, "moving_to_quarantine")
        for row in removed_rows:
            active_path = _chip_path(chip_root, row["chip_path"])
            quarantined_path = quarantine / Path(*PurePosixPath(row["chip_path"]).parts)
            if quarantined_path.exists():
                raise RuntimeError(f"Quarantine collision: {quarantined_path}")
            quarantined_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(active_path, quarantined_path)
        _update_phase(transaction_dir, transaction, "quarantined")
        if failure_hook is not None:
            failure_hook("after_quarantine")
        _copy_atomic(post_staged, manifest, overwrite=True)
        _update_phase(transaction_dir, transaction, "manifest_replaced")
        if failure_hook is not None:
            failure_hook("after_manifest_replace")
        _finalize_transaction(
            chip_root=chip_root,
            manifest=manifest,
            history_dir=history_dir,
            transaction_dir=transaction_dir,
            transaction=transaction,
        )
    except (Exception, KeyboardInterrupt):
        should_roll_back = (
            transaction_dir.exists()
            and _sha256(manifest) == transaction["pre_manifest_sha256"]
            and not (
                transaction["pre_manifest_sha256"]
                == transaction["post_manifest_sha256"]
                and transaction.get("phase") in POST_COMMIT_PHASES
            )
        )
        if should_roll_back:
            _rollback_transaction(
                chip_root=chip_root,
                manifest=manifest,
                transaction_dir=transaction_dir,
                transaction=transaction,
            )
        raise

    return FilterResult(
        mode="apply",
        status="applied",
        threshold_pct=threshold_text,
        total_count=len(rows),
        kept_count=len(kept_rows),
        removed_count=len(removed_rows),
        report_output=report_output,
        history_dir=history_dir,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report or apply a manifest-driven maximum nodata percentage."
    )
    parser.add_argument("chip_root", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--max-nodata-pct",
        type=_argparse_threshold,
        required=True,
        help="Maximum kept nodata percentage in [0, 100]; no default.",
    )
    parser.add_argument("--report-output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    command_args = sys.argv if argv is None else [sys.argv[0], *argv]
    result = filter_nodata_chips(
        chip_root=args.chip_root,
        manifest=args.manifest,
        max_nodata_pct=args.max_nodata_pct,
        report_output=args.report_output,
        apply=args.apply,
        producer_command=shlex.join(command_args),
    )
    print(
        f"Nodata filter {result.status}: mode={result.mode}, "
        f"threshold_pct={result.threshold_pct}, total={result.total_count}, "
        f"kept={result.kept_count}, removed={result.removed_count}"
    )
    print(f"Report: {result.report_output}")
    if result.history_dir is not None:
        print(f"Filter history: {result.history_dir}")


if __name__ == "__main__":
    main()
