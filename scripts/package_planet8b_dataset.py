"""Build and verify the portable canonical PlanetScope 8-band chip archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import stat
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

INVENTORY_PATH = Path("metadata/archive_inventory.csv")
LOCAL_PROVENANCE_PATH = Path("metadata/local_raster_path_provenance.csv")
FORBIDDEN_SUFFIXES = {".ckpt", ".onnx", ".pt", ".pth", ".tif", ".tiff"}
FORBIDDEN_PARTS = {"checkpoints", "lightning_logs", "wandb"}
RUNTIME_RASTER_COLUMNS = [
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "source_split",
    "materialization_mode",
    "label_preparation",
]
LOCAL_RASTER_PATH_COLUMNS = [
    "source_tiff_id",
    "source_image",
    "source_label",
    "merged_image",
    "merged_label",
]
REQUIRED_CHIP_COLUMNS = {
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "chip_width",
    "chip_height",
    "class_0_pixel_count",
    "class_1_pixel_count",
    "ignore_pixel_count",
    "nodata_pixel_count",
    "nodata_pct",
    "image_dtype",
    "label_dtype",
}
REQUIRED_RASTER_METADATA_COLUMNS = {
    "source_tiff_id",
    "width",
    "height",
    "band_count",
    "image_dtype",
    "label_dtype",
    "crs",
    "transform_a",
    "transform_b",
    "transform_c",
    "transform_d",
    "transform_e",
    "transform_f",
    "bounds_left",
    "bounds_bottom",
    "bounds_right",
    "bounds_top",
}
ABSOLUTE_RUNTIME_PATH = re.compile(r"(?:^|[\s,\"'])(?:/[A-Za-z0-9_.-]+|[A-Za-z]:[\\/])")


@dataclass(frozen=True)
class PackageResult:
    archive: Path
    archive_bytes: int
    archive_sha256: str
    checksum_file: Path
    dataset_root_name: str
    inventory_count: int
    inventory_sha256: str
    npz_bytes: int
    npz_count: int
    staging_root: Path


@dataclass(frozen=True)
class VerificationResult:
    archive: Path
    archive_sha256: str
    dataset_root: Path
    inventory_count: int
    npz_bytes: int
    npz_count: int
    sampled_npz_count: int
    source_count: int


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    _require_regular_file(path)
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=fieldnames, extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as file:
        file.write(text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_regular_file(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as error:
        raise RuntimeError(f"Required file is missing: {path}") from error
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise RuntimeError(f"Required input is not a regular file: {path}")


def _require_columns(path: Path, fieldnames: list[str], required: set[str]) -> None:
    missing = sorted(required - set(fieldnames))
    if missing:
        raise RuntimeError(f"Missing columns in {path}: {missing}")


def _unique_by(
    rows: list[dict[str, str]], key: str, *, label: str
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    lower_values: set[str] = set()
    for row in rows:
        value = row.get(key, "")
        if not value:
            raise RuntimeError(f"Empty {key} in {label}")
        if value in result or value.lower() in lower_values:
            raise RuntimeError(f"Duplicate {key} in {label}: {value}")
        result[value] = row
        lower_values.add(value.lower())
    return result


def _portable_path(value: str, *, label: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "" in path.parts:
        raise RuntimeError(f"Nonportable path in {label}: {value}")
    return path


def _chip_archive_path(value: str, *, label: str) -> str:
    path = _portable_path(value, label=label)
    if len(path.parts) != 2 or path.parts[0] != "all" or path.suffix != ".npz":
        raise RuntimeError(f"Unexpected canonical chip path in {label}: {value}")
    return PurePosixPath("chips", *path.parts).as_posix()


def _assert_within(path: Path, root: Path, *, label: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise RuntimeError(f"{label} escapes declared root {root}: {path}") from error


def _link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination, follow_symlinks=False)


def _copy_regular(source: Path, destination: Path) -> None:
    _require_regular_file(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as output, source.open("rb") as input_file:
        shutil.copyfileobj(input_file, output, length=4 * 1024 * 1024)


def _class_presence(row: dict[str, str]) -> str:
    foreground = int(row["class_1_pixel_count"])
    background = int(row["class_0_pixel_count"])
    nodata = int(row["nodata_pixel_count"])
    if foreground > 0:
        return "positive"
    if background > 0 and nodata > 0:
        return "mixed_background_nodata"
    if background > 0:
        return "clean_background_only"
    return "ignore_only"


def _portable_filter_metadata(source: dict[str, Any]) -> dict[str, Any]:
    keep_keys = {
        "completed_at_utc",
        "git_commit",
        "mutation_strategy",
        "nodata_definition",
        "post_manifest_sha256",
        "pre_count_by_dataset",
        "pre_count_by_region",
        "pre_filter_count",
        "pre_filter_manifest_sha256",
        "pre_manifest_sha256",
        "removal_manifest_sha256",
        "removed_count",
        "removed_count_by_dataset",
        "removed_count_by_region",
        "removed_source_tiff_count",
        "report_sha256",
        "retained_count",
        "retained_count_by_dataset",
        "retained_count_by_region",
        "schema_version",
        "selection_rule",
        "status",
        "threshold_pct",
    }
    result = {key: source[key] for key in sorted(keep_keys) if key in source}
    result["active_manifest"] = "manifests/chip_manifest.csv"
    result["removal_manifest"] = "manifests/nodata_removal_manifest.csv"
    result["post_filter_summary"] = "manifests/nodata_post_filter_summary.csv"
    return result


def _validate_source_inputs(
    *,
    chip_root: Path,
    raster_root: Path,
    temporal_split: Path,
) -> dict[str, Any]:
    input_paths = {
        "chip_manifest": chip_root / "chip_manifest.csv",
        "training_selection": chip_root
        / "background_selection/exclude_all/training_selection.csv",
        "selection_summary": chip_root
        / "background_selection/exclude_all/selection_summary.csv",
        "removal_manifest": chip_root / "filter_history/nodata_50/removal_manifest.csv",
        "filter_metadata": chip_root / "filter_history/nodata_50/filter_metadata.json",
        "post_filter_summary": chip_root
        / "filter_history/nodata_50/post_filter_summary.csv",
        "task004_chip_qa": chip_root / "chip_qa_summary.json",
        "raster_manifest": raster_root / "raster_manifest.csv",
        "raster_metadata": raster_root / "raster_metadata.csv",
        "raster_qa": raster_root / "raster_qa_summary.json",
        "temporal_split": temporal_split,
    }
    for path in input_paths.values():
        _require_regular_file(path)

    chip_fields, chips = _read_csv(input_paths["chip_manifest"])
    _require_columns(input_paths["chip_manifest"], chip_fields, REQUIRED_CHIP_COLUMNS)
    chip_by_id = _unique_by(chips, "chip_id", label="active chip manifest")
    if not chips:
        raise RuntimeError("Active chip manifest is empty")

    chip_paths: set[str] = set()
    npz_bytes = 0
    class_presence = Counter()
    by_dataset = Counter()
    by_region = Counter()
    source_ids: set[str] = set()
    partial_count = 0
    for row in chips:
        relative = _portable_path(row["chip_path"], label=row["chip_id"])
        archived = _chip_archive_path(relative.as_posix(), label=row["chip_id"])
        if archived.lower() in {value.lower() for value in chip_paths}:
            raise RuntimeError(f"Duplicate chip path: {archived}")
        chip_paths.add(archived)
        source = chip_root / Path(*relative.parts)
        _assert_within(source, chip_root, label="chip path")
        _require_regular_file(source)
        npz_bytes += source.stat().st_size
        if float(row["nodata_pct"]) > 50.0:
            raise RuntimeError(f"Active chip exceeds 50% nodata: {row['chip_id']}")
        class_presence[_class_presence(row)] += 1
        by_dataset[row["dataset"]] += 1
        by_region[row["region_id"]] += 1
        source_ids.add(row["source_tiff_id"])
        if int(row["chip_width"]) < 1024 or int(row["chip_height"]) < 1024:
            partial_count += 1

    filesystem_npzs = {
        PurePosixPath("chips", "all", path.name).as_posix()
        for path in (chip_root / "all").iterdir()
        if path.is_file() and path.suffix == ".npz"
    }
    if filesystem_npzs != chip_paths:
        missing = sorted(chip_paths - filesystem_npzs)[:3]
        extra = sorted(filesystem_npzs - chip_paths)[:3]
        raise RuntimeError(
            f"Active manifest/NPZ mismatch; missing={missing}, extra={extra}"
        )

    selection_fields, selections = _read_csv(input_paths["training_selection"])
    _require_columns(
        input_paths["training_selection"],
        selection_fields,
        {
            "chip_id",
            "source_tiff_id",
            "region_id",
            "class_presence",
            "selected_for_training",
            "policy",
        },
    )
    selection_by_id = _unique_by(
        selections, "chip_id", label="training-selection manifest"
    )
    if set(selection_by_id) != set(chip_by_id):
        raise RuntimeError(
            "Training selection does not join one-to-one to active chips"
        )
    for chip_id, selection in selection_by_id.items():
        chip = chip_by_id[chip_id]
        if (
            selection["source_tiff_id"] != chip["source_tiff_id"]
            or selection["region_id"] != chip["region_id"]
            or selection["class_presence"] != _class_presence(chip)
            or selection["policy"] != "exclude_all"
        ):
            raise RuntimeError(f"Training-selection identity mismatch: {chip_id}")
        expected = selection["class_presence"] == "positive"
        if (selection["selected_for_training"].lower() == "true") != expected:
            raise RuntimeError(f"Unexpected training selection for {chip_id}")

    raster_fields, rasters = _read_csv(input_paths["raster_manifest"])
    _require_columns(
        input_paths["raster_manifest"],
        raster_fields,
        set(RUNTIME_RASTER_COLUMNS) | set(LOCAL_RASTER_PATH_COLUMNS),
    )
    raster_by_id = _unique_by(rasters, "source_tiff_id", label="raster manifest")

    metadata_fields, metadata = _read_csv(input_paths["raster_metadata"])
    _require_columns(
        input_paths["raster_metadata"],
        metadata_fields,
        REQUIRED_RASTER_METADATA_COLUMNS,
    )
    metadata_by_id = _unique_by(metadata, "source_tiff_id", label="raster metadata")

    split_fields, splits = _read_csv(temporal_split)
    _require_columns(
        temporal_split,
        split_fields,
        {"image_name_stem", "split", "dataset", "region_id"},
    )
    split_by_id = _unique_by(splits, "image_name_stem", label="temporal split")
    if set(raster_by_id) != set(metadata_by_id) or set(raster_by_id) != set(
        split_by_id
    ):
        raise RuntimeError(
            "Raster manifest, raster metadata, and temporal split differ"
        )
    if not source_ids <= set(raster_by_id):
        raise RuntimeError(
            "Active chips do not join to raster metadata and temporal split"
        )
    for source_id in source_ids:
        row = metadata_by_id[source_id]
        if any(not row[column] for column in REQUIRED_RASTER_METADATA_COLUMNS):
            raise RuntimeError(f"Incomplete portable raster metadata: {source_id}")

    with input_paths["filter_metadata"].open() as file:
        filter_metadata = json.load(file)
    if (
        filter_metadata.get("status") != "complete"
        or str(filter_metadata.get("threshold_pct")) != "50"
        or int(filter_metadata.get("retained_count", -1)) != len(chips)
    ):
        raise RuntimeError("Task 007 completion metadata does not match active chips")

    with input_paths["task004_chip_qa"].open() as file:
        task004_chip_qa = json.load(file)
    with input_paths["raster_qa"].open() as file:
        raster_qa = json.load(file)

    return {
        "input_paths": input_paths,
        "chip_fields": chip_fields,
        "chips": chips,
        "selection_fields": selection_fields,
        "selections": selections,
        "raster_fields": raster_fields,
        "rasters": rasters,
        "metadata_fields": metadata_fields,
        "metadata": metadata,
        "split_fields": split_fields,
        "splits": splits,
        "filter_metadata": filter_metadata,
        "task004_chip_qa": task004_chip_qa,
        "raster_qa": raster_qa,
        "npz_bytes": npz_bytes,
        "class_presence": dict(sorted(class_presence.items())),
        "by_dataset": dict(sorted(by_dataset.items())),
        "by_region": dict(sorted(by_region.items())),
        "source_count": len(source_ids),
        "partial_count": partial_count,
    }


def _validate_staged_paths(staging_root: Path) -> None:
    lower_paths: set[str] = set()
    for path in sorted(staging_root.rglob("*")):
        relative = path.relative_to(staging_root)
        lower = relative.as_posix().lower()
        if lower in lower_paths:
            raise RuntimeError(f"Case-insensitive duplicate staged path: {relative}")
        lower_paths.add(lower)
        if path.is_symlink():
            raise RuntimeError(f"Symlink is forbidden in staging: {relative}")
        if path.is_file():
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise RuntimeError(f"Forbidden file type in staging: {relative}")
            if FORBIDDEN_PARTS & {part.lower() for part in relative.parts}:
                raise RuntimeError(f"Forbidden directory in staging: {relative}")
        elif not path.is_dir():
            raise RuntimeError(f"Unsupported staged member: {relative}")

    for path in sorted(staging_root.rglob("*")):
        if not path.is_file() or path == staging_root / LOCAL_PROVENANCE_PATH:
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md", ".txt"}:
            continue
        text = path.read_text(errors="strict")
        if ABSOLUTE_RUNTIME_PATH.search(text):
            raise RuntimeError(f"Absolute path in portable runtime file: {path}")


def _write_inventory(staging_root: Path) -> tuple[int, str]:
    inventory = staging_root / INVENTORY_PATH
    rows: list[dict[str, Any]] = []
    for index, path in enumerate(sorted(staging_root.rglob("*"))):
        if not path.is_file() or path == inventory:
            continue
        relative = path.relative_to(staging_root).as_posix()
        if relative.startswith("chips/all/"):
            kind = "chip"
        elif relative.startswith("manifests/"):
            kind = "manifest"
        else:
            kind = "metadata"
        rows.append(
            {
                "relative_path": relative,
                "byte_size": path.stat().st_size,
                "sha256": sha256_file(path),
                "kind": kind,
            }
        )
        if index and index % 500 == 0:
            print(f"Inventoried {index:,} staged members", flush=True)
    _write_csv(
        inventory,
        rows,
        ["relative_path", "byte_size", "sha256", "kind"],
    )
    return len(rows), sha256_file(inventory)


def _write_archive(staging_root: Path, archive: Path) -> None:
    partial = archive.with_name(f".{archive.name}.partial")
    if partial.exists():
        raise RuntimeError(f"Partial archive already exists: {partial}")
    try:
        with zipfile.ZipFile(
            partial, "x", compression=zipfile.ZIP_STORED, allowZip64=True
        ) as output:
            files = [path for path in sorted(staging_root.rglob("*")) if path.is_file()]
            for index, path in enumerate(files, start=1):
                arcname = PurePosixPath(
                    staging_root.name, *path.relative_to(staging_root).parts
                ).as_posix()
                output.write(path, arcname=arcname)
                if index % 500 == 0:
                    print(f"Archived {index:,}/{len(files):,} members", flush=True)
        os.replace(partial, archive)
    except BaseException:
        print(f"Archive write did not complete; partial file preserved at {partial}")
        raise


def package_dataset_archive(
    *,
    chip_root: Path,
    raster_root: Path,
    temporal_split: Path,
    archive: Path,
    dataset_version: str,
    producer_git_commit: str,
    producer_worktree_dirty: bool = False,
    staging_root: Path | None = None,
) -> PackageResult:
    """Validate canonical inputs, stage them portably, and create one ZIP."""
    chip_root = chip_root.resolve()
    raster_root = raster_root.resolve()
    temporal_split = temporal_split.resolve()
    archive = archive.resolve()
    if archive.suffix.lower() != ".zip":
        raise RuntimeError(f"Archive must use .zip: {archive}")
    if archive.exists() or archive.with_suffix(".zip.sha256").exists():
        raise RuntimeError(f"Refusing to overwrite archive or checksum: {archive}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    staging_root = (
        staging_root.resolve()
        if staging_root is not None
        else archive.parent / "staging" / archive.stem
    )
    if staging_root.name != archive.stem:
        raise RuntimeError("Staging dataset root name must match the archive stem")
    if staging_root.exists():
        raise RuntimeError(f"Refusing to overwrite staging root: {staging_root}")

    print("Validating canonical inputs", flush=True)
    validated = _validate_source_inputs(
        chip_root=chip_root,
        raster_root=raster_root,
        temporal_split=temporal_split,
    )
    required_free = 2 * validated["npz_bytes"] + 1024**3
    free = shutil.disk_usage(archive.parent).free
    if free < required_free:
        raise RuntimeError(
            f"Insufficient free space for archive plus verification extraction: "
            f"need {required_free:,}, found {free:,} bytes"
        )

    staging_root.mkdir(parents=True)
    (staging_root / "chips/all").mkdir(parents=True)
    (staging_root / "manifests").mkdir()
    (staging_root / "metadata").mkdir()

    print(f"Staging {len(validated['chips']):,} canonical chips", flush=True)
    portable_chips: list[dict[str, str]] = []
    for index, row in enumerate(validated["chips"], start=1):
        portable = dict(row)
        portable["chip_path"] = _chip_archive_path(
            row["chip_path"], label=row["chip_id"]
        )
        relative_source = _portable_path(row["chip_path"], label=row["chip_id"])
        source = chip_root / Path(*relative_source.parts)
        destination = staging_root / Path(*PurePosixPath(portable["chip_path"]).parts)
        _link_or_copy(source, destination)
        portable_chips.append(portable)
        if index % 500 == 0:
            print(f"Staged {index:,}/{len(validated['chips']):,} chips", flush=True)
    _write_csv(
        staging_root / "manifests/chip_manifest.csv",
        portable_chips,
        validated["chip_fields"],
    )

    portable_rasters = [
        {column: row[column] for column in RUNTIME_RASTER_COLUMNS}
        for row in validated["rasters"]
    ]
    _write_csv(
        staging_root / "manifests/raster_manifest.csv",
        portable_rasters,
        RUNTIME_RASTER_COLUMNS,
    )
    local_provenance = [
        {column: row[column] for column in LOCAL_RASTER_PATH_COLUMNS}
        for row in validated["rasters"]
    ]
    _write_csv(
        staging_root / LOCAL_PROVENANCE_PATH,
        local_provenance,
        LOCAL_RASTER_PATH_COLUMNS,
    )
    _write_csv(
        staging_root / "manifests/raster_metadata.csv",
        validated["metadata"],
        validated["metadata_fields"],
    )
    _write_csv(
        staging_root / "manifests/planet8b_temporal_image_splits.csv",
        validated["splits"],
        validated["split_fields"],
    )

    removal_fields, removals = _read_csv(validated["input_paths"]["removal_manifest"])
    portable_removals = []
    for row in removals:
        portable = dict(row)
        portable["chip_path"] = _chip_archive_path(
            row["chip_path"], label=f"removed {row['chip_id']}"
        )
        portable_removals.append(portable)
    _write_csv(
        staging_root / "manifests/nodata_removal_manifest.csv",
        portable_removals,
        removal_fields,
    )
    _copy_regular(
        validated["input_paths"]["post_filter_summary"],
        staging_root / "manifests/nodata_post_filter_summary.csv",
    )
    _write_csv(
        staging_root / "manifests/training_selection.csv",
        validated["selections"],
        validated["selection_fields"],
    )
    _copy_regular(
        validated["input_paths"]["selection_summary"],
        staging_root / "manifests/background_selection_summary.csv",
    )

    selected_count = sum(
        row["selected_for_training"].lower() == "true"
        for row in validated["selections"]
    )
    background_policy = {
        "canonical_chip_count": len(validated["chips"]),
        "class_presence_chip_counts": validated["class_presence"],
        "excluded_chip_count": len(validated["chips"]) - selected_count,
        "policy": "exclude_all",
        "scope": "training rows only; validation and test bypass this selector",
        "selected_chip_count": selected_count,
        "selection_manifest": "manifests/training_selection.csv",
        "selection_summary": "manifests/background_selection_summary.csv",
    }
    _write_json(staging_root / "manifests/background_policy.json", background_policy)

    _write_json(
        staging_root / "metadata/nodata_filter_metadata.json",
        _portable_filter_metadata(validated["filter_metadata"]),
    )
    _write_json(
        staging_root / "metadata/raster_qa_summary.json", validated["raster_qa"]
    )
    chip_qa = {
        "active_manifest_sha256": sha256_file(
            validated["input_paths"]["chip_manifest"]
        ),
        "by_dataset": validated["by_dataset"],
        "by_region": validated["by_region"],
        "class_presence_chip_counts": validated["class_presence"],
        "inventory": {
            "chip_count": len(validated["chips"]),
            "partial_chip_count": validated["partial_count"],
            "region_count": len(validated["by_region"]),
            "source_tiff_count": validated["source_count"],
            "total_compressed_npz_bytes": validated["npz_bytes"],
        },
        "parameters": validated["task004_chip_qa"].get("parameters", {}),
        "source_task004_chip_qa_sha256": sha256_file(
            validated["input_paths"]["task004_chip_qa"]
        ),
        "validation": {
            "active_manifest_npz_bijection": True,
            "active_nodata_pct_at_most_50": True,
            "raster_metadata_temporal_split_join": True,
            "training_selection_one_to_one": True,
        },
    }
    _write_json(staging_root / "metadata/chip_qa_summary.json", chip_qa)

    portable_manifest_hashes = {
        path.name: sha256_file(path)
        for path in sorted((staging_root / "manifests").iterdir())
        if path.is_file()
    }
    parameters = validated["task004_chip_qa"].get("parameters", {})
    dataset_parameters = {
        "archive": {
            "compression": "ZIP_STORED (NPZ payloads are already compressed)",
            "dataset_root": archive.stem,
            "format": "ZIP64",
            "inventory_scope": "every payload member except archive_inventory.csv itself",
        },
        "background_selection": background_policy,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_id": archive.stem,
        "dataset_version": dataset_version,
        "filtering": {
            "nodata_definition": validated["filter_metadata"]["nodata_definition"],
            "retained_chip_count": len(validated["chips"]),
            "threshold_pct": 50,
        },
        "manifest_sha256": portable_manifest_hashes,
        "parameters": parameters,
        "producer_git_commit": producer_git_commit,
        "producer_tool": "scripts/package_planet8b_dataset.py package",
        "producer_worktree_dirty": producer_worktree_dirty,
        "source_rasters": {
            "active_source_tiff_count": validated["source_count"],
            "metadata_source_tiff_count": len(validated["metadata"]),
            "raw_tiffs_included": False,
        },
    }
    _write_json(staging_root / "metadata/dataset_parameters.json", dataset_parameters)
    readme = f"""# {archive.stem}

Portable canonical PlanetScope 8-band kelp-segmentation chips, version
`{dataset_version}`. The dataset contains {len(validated["chips"]):,} active
post-nodata-filter chips from {validated["source_count"]:,} source TIFFs across
{len(validated["by_region"]):,} regions. Raw TIFFs are intentionally absent.

Resolve `chip_path` in `manifests/chip_manifest.csv` relative to this extracted
dataset root. Join chips to raster metadata and temporal assignments through
`source_tiff_id` (`image_name_stem` in the temporal split CSV). Apply
`manifests/training_selection.csv` only to training rows; validation and test
rows remain representative of the canonical post-nodata collection.

`metadata/archive_inventory.csv` records the byte size and SHA-256 of every
payload member, including every NPZ, except the inventory file itself. The
archive-level SHA-256 is stored beside the ZIP. The local raster-path provenance
CSV is optional historical context and is never a runtime dependency.
"""
    _write_text(staging_root / "metadata/README.md", readme)

    print("Hashing every staged member for the portable inventory", flush=True)
    _validate_staged_paths(staging_root)
    inventory_count, inventory_sha256 = _write_inventory(staging_root)
    _validate_staged_paths(staging_root)

    print("Writing ZIP64 archive", flush=True)
    _write_archive(staging_root, archive)
    print("Hashing completed archive", flush=True)
    archive_sha256 = sha256_file(archive)
    checksum_file = archive.with_suffix(".zip.sha256")
    _write_text(checksum_file, f"{archive_sha256}  {archive.name}\n")
    return PackageResult(
        archive=archive,
        archive_bytes=archive.stat().st_size,
        archive_sha256=archive_sha256,
        checksum_file=checksum_file,
        dataset_root_name=archive.stem,
        inventory_count=inventory_count,
        inventory_sha256=inventory_sha256,
        npz_bytes=validated["npz_bytes"],
        npz_count=len(validated["chips"]),
        staging_root=staging_root,
    )


def _expected_checksum(checksum_file: Path, archive: Path) -> str:
    _require_regular_file(checksum_file)
    parts = checksum_file.read_text().strip().split()
    if len(parts) != 2 or parts[1].lstrip("*") != archive.name:
        raise RuntimeError(f"Invalid checksum sidecar: {checksum_file}")
    expected = parts[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise RuntimeError(f"Invalid SHA-256 in {checksum_file}")
    return expected


def _validate_zip_members(archive: Path) -> str:
    lower_names: set[str] = set()
    roots: set[str] = set()
    with zipfile.ZipFile(archive) as input_zip:
        for info in input_zip.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
                raise RuntimeError(f"Unsafe archive member: {info.filename}")
            lower = info.filename.lower()
            if lower in lower_names:
                raise RuntimeError(f"Duplicate archive member: {info.filename}")
            lower_names.add(lower)
            roots.add(path.parts[0])
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"Symlink is forbidden in archive: {info.filename}")
            relative_parts = {part.lower() for part in path.parts[1:]}
            if FORBIDDEN_PARTS & relative_parts:
                raise RuntimeError(f"Forbidden archive directory: {info.filename}")
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise RuntimeError(f"Forbidden archive file: {info.filename}")
    if len(roots) != 1:
        raise RuntimeError(f"Archive must contain one dataset root: {sorted(roots)}")
    return roots.pop()


def _validate_npz_sample(
    dataset_root: Path,
    chips: list[dict[str, str]],
    *,
    sample_count: int,
) -> int:
    if sample_count < 1:
        raise RuntimeError("sample_count must be positive")
    sample_size = min(sample_count, len(chips))
    selected = random.Random(9).sample(chips, sample_size)
    for row in selected:
        path = dataset_root / Path(*PurePosixPath(row["chip_path"]).parts)
        with np.load(path) as chip:
            if set(chip.files) != {"image", "label"}:
                raise RuntimeError(f"Unexpected NPZ keys: {path}")
            image = chip["image"]
            label = chip["label"]
        shape = (int(row["chip_height"]), int(row["chip_width"]))
        if image.shape != (*shape, 8) or label.shape != shape:
            raise RuntimeError(f"NPZ shape mismatch: {path}")
        if (
            str(image.dtype) != row["image_dtype"]
            or str(label.dtype) != row["label_dtype"]
        ):
            raise RuntimeError(f"NPZ dtype mismatch: {path}")
        if int(np.count_nonzero(label == 0)) != int(row["class_0_pixel_count"]):
            raise RuntimeError(f"NPZ class-0 mismatch: {path}")
        if int(np.count_nonzero(label == 1)) != int(row["class_1_pixel_count"]):
            raise RuntimeError(f"NPZ class-1 mismatch: {path}")
        if int(np.count_nonzero(label == -100)) != int(row["ignore_pixel_count"]):
            raise RuntimeError(f"NPZ ignore mismatch: {path}")
        nodata = int(np.count_nonzero(np.all(image == 0, axis=-1)))
        if nodata != int(row["nodata_pixel_count"]):
            raise RuntimeError(f"NPZ nodata mismatch: {path}")
    return sample_size


def _validate_extracted_dataset(
    dataset_root: Path, *, sample_count: int
) -> VerificationResult:
    _validate_staged_paths(dataset_root)
    inventory_path = dataset_root / INVENTORY_PATH
    inventory_fields, inventory = _read_csv(inventory_path)
    _require_columns(
        inventory_path,
        inventory_fields,
        {"relative_path", "byte_size", "sha256", "kind"},
    )
    inventory_by_path = _unique_by(
        inventory, "relative_path", label="archive inventory"
    )
    extracted_files = {
        path.relative_to(dataset_root).as_posix()
        for path in dataset_root.rglob("*")
        if path.is_file() and path != inventory_path
    }
    if extracted_files != set(inventory_by_path):
        missing = sorted(set(inventory_by_path) - extracted_files)[:3]
        extra = sorted(extracted_files - set(inventory_by_path))[:3]
        raise RuntimeError(f"Inventory mismatch; missing={missing}, extra={extra}")
    for index, (relative, row) in enumerate(sorted(inventory_by_path.items()), start=1):
        path = dataset_root / Path(*PurePosixPath(relative).parts)
        if path.stat().st_size != int(row["byte_size"]):
            raise RuntimeError(f"Inventory byte-size mismatch: {relative}")
        if sha256_file(path) != row["sha256"]:
            raise RuntimeError(f"Inventory SHA-256 mismatch: {relative}")
        if index % 500 == 0:
            print(
                f"Verified {index:,}/{len(inventory):,} inventory members", flush=True
            )

    chip_manifest = dataset_root / "manifests/chip_manifest.csv"
    chip_fields, chips = _read_csv(chip_manifest)
    _require_columns(chip_manifest, chip_fields, REQUIRED_CHIP_COLUMNS)
    chip_by_id = _unique_by(chips, "chip_id", label="portable chip manifest")
    chip_paths: set[str] = set()
    npz_bytes = 0
    for row in chips:
        relative = _portable_path(row["chip_path"], label=row["chip_id"])
        if len(relative.parts) != 3 or relative.parts[:2] != ("chips", "all"):
            raise RuntimeError(f"Unexpected portable chip path: {relative}")
        path = dataset_root / Path(*relative.parts)
        _assert_within(path, dataset_root, label="portable chip path")
        _require_regular_file(path)
        chip_paths.add(relative.as_posix())
        npz_bytes += path.stat().st_size
    extracted_npzs = {
        path.relative_to(dataset_root).as_posix()
        for path in (dataset_root / "chips/all").iterdir()
        if path.is_file() and path.suffix == ".npz"
    }
    if extracted_npzs != chip_paths:
        raise RuntimeError(
            "Portable chip manifest does not resolve every extracted NPZ"
        )

    selection_path = dataset_root / "manifests/training_selection.csv"
    _, selections = _read_csv(selection_path)
    selection_by_id = _unique_by(
        selections, "chip_id", label="portable training selection"
    )
    if set(selection_by_id) != set(chip_by_id):
        raise RuntimeError("Portable training selection does not join one-to-one")

    raster_path = dataset_root / "manifests/raster_manifest.csv"
    raster_fields, rasters = _read_csv(raster_path)
    _require_columns(raster_path, raster_fields, set(RUNTIME_RASTER_COLUMNS))
    raster_by_id = _unique_by(rasters, "source_tiff_id", label="portable rasters")

    metadata_path = dataset_root / "manifests/raster_metadata.csv"
    metadata_fields, metadata = _read_csv(metadata_path)
    _require_columns(metadata_path, metadata_fields, REQUIRED_RASTER_METADATA_COLUMNS)
    metadata_by_id = _unique_by(
        metadata, "source_tiff_id", label="portable raster metadata"
    )

    split_path = dataset_root / "manifests/planet8b_temporal_image_splits.csv"
    _, splits = _read_csv(split_path)
    split_by_id = _unique_by(splits, "image_name_stem", label="portable split")
    if set(raster_by_id) != set(metadata_by_id) or set(raster_by_id) != set(
        split_by_id
    ):
        raise RuntimeError("Portable source manifest/metadata/split sets differ")
    chip_source_ids = {row["source_tiff_id"] for row in chips}
    if not chip_source_ids <= set(raster_by_id):
        raise RuntimeError("Portable chips do not join to source metadata and split")
    for source_id in chip_source_ids:
        if any(
            not metadata_by_id[source_id][column]
            for column in REQUIRED_RASTER_METADATA_COLUMNS
        ):
            raise RuntimeError(f"Incomplete extracted raster metadata: {source_id}")

    sampled = _validate_npz_sample(dataset_root, chips, sample_count=sample_count)
    return VerificationResult(
        archive=Path(),
        archive_sha256="",
        dataset_root=dataset_root,
        inventory_count=len(inventory),
        npz_bytes=npz_bytes,
        npz_count=len(chips),
        sampled_npz_count=sampled,
        source_count=len(chip_source_ids),
    )


def _safe_cleanup(path: Path, *, expected_name: str) -> None:
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_dir()
        or path.name != expected_name
        or resolved == Path(resolved.anchor)
    ):
        raise RuntimeError(f"Refusing unsafe cleanup target: {path}")
    shutil.rmtree(path)


def verify_dataset_archive(
    *,
    archive: Path,
    checksum_file: Path,
    extraction_parent: Path,
    sample_count: int = 12,
    staging_root: Path | None = None,
    cleanup_extraction: bool = False,
    cleanup_staging: bool = False,
) -> VerificationResult:
    """Verify checksum, safely extract, and validate every inventoried member."""
    archive = archive.resolve()
    checksum_file = checksum_file.resolve()
    extraction_parent = extraction_parent.resolve()
    _require_regular_file(archive)
    if extraction_parent.exists():
        raise RuntimeError(f"Refusing to reuse extraction parent: {extraction_parent}")

    expected = _expected_checksum(checksum_file, archive)
    print("Verifying archive-level SHA-256", flush=True)
    actual = sha256_file(archive)
    if actual != expected:
        raise RuntimeError(
            f"Archive checksum mismatch: expected {expected}, got {actual}"
        )

    root_name = _validate_zip_members(archive)
    if root_name != archive.stem:
        raise RuntimeError(
            f"Archive root {root_name} does not match archive stem {archive.stem}"
        )
    extraction_parent.mkdir(parents=True)
    print("Extracting archive for clean-root verification", flush=True)
    with zipfile.ZipFile(archive) as input_zip:
        input_zip.extractall(extraction_parent)
    dataset_root = extraction_parent / root_name
    result = _validate_extracted_dataset(dataset_root, sample_count=sample_count)
    result = VerificationResult(
        archive=archive,
        archive_sha256=actual,
        dataset_root=dataset_root,
        inventory_count=result.inventory_count,
        npz_bytes=result.npz_bytes,
        npz_count=result.npz_count,
        sampled_npz_count=result.sampled_npz_count,
        source_count=result.source_count,
    )

    if cleanup_staging:
        if staging_root is None:
            raise RuntimeError("--cleanup-staging requires --staging-root")
        staging_root = staging_root.resolve()
        if staging_root.name != root_name:
            raise RuntimeError(
                "Staging cleanup root does not match archive dataset root"
            )
        _safe_cleanup(staging_root, expected_name=root_name)
    if cleanup_extraction:
        _safe_cleanup(extraction_parent, expected_name=extraction_parent.name)
    return result


def _json_result(result: PackageResult | VerificationResult) -> str:
    payload = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in result.__dict__.items()
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    package = subparsers.add_parser("package", help="Build the portable ZIP")
    package.add_argument("--chip-root", type=Path, required=True)
    package.add_argument("--raster-root", type=Path, required=True)
    package.add_argument("--temporal-split", type=Path, required=True)
    package.add_argument("--archive", type=Path, required=True)
    package.add_argument("--dataset-version", required=True)
    package.add_argument("--producer-git-commit", required=True)
    package.add_argument("--producer-worktree-dirty", action="store_true")
    package.add_argument("--staging-root", type=Path)

    verify = subparsers.add_parser("verify", help="Verify and extract the ZIP")
    verify.add_argument("--archive", type=Path, required=True)
    verify.add_argument("--checksum-file", type=Path, required=True)
    verify.add_argument("--extraction-parent", type=Path, required=True)
    verify.add_argument("--sample-count", type=int, default=12)
    verify.add_argument("--staging-root", type=Path)
    verify.add_argument("--cleanup-extraction", action="store_true")
    verify.add_argument("--cleanup-staging", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "package":
            result = package_dataset_archive(
                chip_root=args.chip_root,
                raster_root=args.raster_root,
                temporal_split=args.temporal_split,
                archive=args.archive,
                dataset_version=args.dataset_version,
                producer_git_commit=args.producer_git_commit,
                producer_worktree_dirty=args.producer_worktree_dirty,
                staging_root=args.staging_root,
            )
        else:
            result = verify_dataset_archive(
                archive=args.archive,
                checksum_file=args.checksum_file,
                extraction_parent=args.extraction_parent,
                sample_count=args.sample_count,
                staging_root=args.staging_root,
                cleanup_extraction=args.cleanup_extraction,
                cleanup_staging=args.cleanup_staging,
            )
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(_json_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
