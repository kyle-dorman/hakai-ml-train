"""Organize declared source bytes once, then verify and publish the fresh output.

A failed job leaves its incomplete directory for inspection. Nothing resumes,
reuses an older output, or deletes a previous attempt. The read-only verifier
can check completed releases independently of the writing command.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import shutil
import time
import zipfile
import zlib
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from kelpseg.prepare.organize_inputs import (
    SCHEMAS,
    OrganizeError,
    build_organization_plan,
)

if TYPE_CHECKING:
    from kelpseg.prepare.organize_inputs import OrganizationPlan, PlannedFile

logger = logging.getLogger(__name__)
__all__ = [
    "ReleaseVerification",
    "build_organization_plan",
    "organize_dataset",
    "verify_organized_release",
]


@dataclass(frozen=True)
class ReleaseVerification:
    """A completed release whose inventory and all recorded hashes were checked."""

    path: Path
    plan_hash: str
    file_count: int
    total_bytes: int


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def _hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    last_progress = time.monotonic()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
            now = time.monotonic()
            if now - last_progress >= 10:
                logger.info("Still verifying %s: %.1f MiB read", path, size / 1024**2)
                last_progress = now
    return digest.hexdigest(), size


def _stats(path: Path) -> list[int]:
    info = path.stat()
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise OrganizeError(f"Cannot read organizer record {path}: {error}") from error
    if not isinstance(value, dict):
        raise OrganizeError(f"Invalid organizer record: {path}")
    return value


def _write_control(path: Path, contents: bytes) -> dict:
    """Write one fresh record and keep its byte identity for the final manifest."""
    with path.open("xb") as stream:
        stream.write(contents)
    return {"sha256": hashlib.sha256(contents).hexdigest(), "bytes": len(contents)}


def _csv_bytes(rows: list[dict], fields: list[str]) -> bytes:
    import io

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _table_bytes(rows: tuple[dict[str, str], ...]) -> bytes:
    fields = sorted({key for row in rows for key in row})
    return _csv_bytes(list(rows), fields)


def _inventory(root: Path) -> set[str]:
    if root.is_symlink() or not root.is_dir():
        raise OrganizeError(f"Release/workspace must be a real directory: {root}")
    names = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise OrganizeError(f"Symlinks are not allowed in organized output: {path}")
        if path.is_file():
            names.add(path.relative_to(root).as_posix())
        elif not path.is_dir():
            raise OrganizeError(f"Unexpected special file in organized output: {path}")
    return names


def _reject_unexpected_directories(root: Path, allowed_files: set[str]) -> None:
    allowed_dirs = {
        parent.as_posix()
        for name in allowed_files
        for parent in Path(name).parents
        if parent != Path(".")
    }
    actual = {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()
    }
    unknown = actual - allowed_dirs
    if unknown:
        raise OrganizeError(
            f"Unexpected output directories: {', '.join(sorted(unknown))}"
        )


def _safe_manifest_path(root: Path, value: str) -> Path:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in value.split("/"))
        or "\\" in value
        or ":" in value
    ):
        raise OrganizeError(f"Unsafe recorded output path: {value!r}")
    return root / path


def verify_organized_release(
    path: str | Path, plan: OrganizationPlan | None = None
) -> ReleaseVerification:
    """Independently hash every payload/control file in an immutable release.

    ``manifest.json`` covers every other file and does not hash itself. With a
    plan, additionally require its logical identity and exact declared payloads.
    This checks bytes against the recorded manifest; provenance authenticity
    still requires a trusted copy of that manifest or its parent plan.
    """
    root = Path(path)
    logger.info("Verifying release inventory and bytes: %s", root)
    try:
        inventory = _inventory(root)
        manifest = _read_json(root / "manifest.json")
        if (
            manifest.get("schema_version") != 1
            or manifest.get("status") != "complete"
            or not isinstance(manifest.get("files"), dict)
            or not isinstance(manifest.get("plan_hash"), str)
        ):
            raise OrganizeError(f"Invalid completion manifest: {root}")
        files = manifest["files"]
        _reject_unexpected_directories(root, set(files))
        if inventory != set(files) | {"manifest.json"}:
            raise OrganizeError(
                f"Release inventory differs from completion manifest: {root}"
            )
        total = 0
        for index, (name, expected) in enumerate(sorted(files.items()), 1):
            logger.info("[Verify %d/%d] %s", index, len(files), name)
            current = _safe_manifest_path(root, name)
            digest, size = _hash(current)
            if expected != {"sha256": digest, "bytes": size}:
                raise OrganizeError(f"Byte verification failed for {current}")
            total += size
        logical = _read_json(root / "inputs.json")
        logical_hash = hashlib.sha256(_json_bytes(logical)).hexdigest()
        if logical_hash != manifest["plan_hash"]:
            raise OrganizeError(f"Logical input identity differs from manifest: {root}")
        if plan is not None:
            if manifest["plan_hash"] != plan.plan_hash:
                raise OrganizeError(
                    f"Completed release belongs to a different plan: {root}"
                )
            expected_names = _control_names(plan) | {
                item.destination for item in plan.files
            }
            if set(files) != expected_names:
                raise OrganizeError(
                    f"Release does not contain the exact declared files: {root}"
                )
            logger.info(
                "Checking source provenance, companion associations and TIFF headers"
            )
            _verify_provenance(root, plan, files)
        logger.info(
            "Verified release: %d files, %.1f MiB, %s",
            len(files),
            total / 1024**2,
            root,
        )
        return ReleaseVerification(root, manifest["plan_hash"], len(files), total)
    except (OSError, KeyError, TypeError, ValueError, csv.Error) as error:
        if isinstance(error, OrganizeError):
            raise
        raise OrganizeError(
            f"Cannot verify organized release {root}: {error}"
        ) from error


def _verify_provenance(root: Path, plan: OrganizationPlan, files: dict) -> None:
    """Compare the stored tables with the one shared provenance definition."""
    for item in plan.files:
        metadata = files[item.destination]
        if metadata["bytes"] != item.bytes or (
            item.expected_sha256 and metadata["sha256"] != item.expected_sha256
        ):
            raise OrganizeError(
                f"Expected source hash/size differs for {item.destination}"
            )
    for name, expected in _provenance_documents(root, plan, files).items():
        if (root / name).read_bytes() != expected:
            raise OrganizeError(
                f"Provenance snapshot differs from declared inputs: {name}"
            )


def _control_names(plan: OrganizationPlan) -> set[str]:
    names = {
        "sources.csv",
        "filename_aliases.csv",
        "regions.csv",
        "recipe.json",
        "inputs.json",
    }
    if plan.assets:
        names.add("assets.csv")
    return names


def _assert_no_symlinks(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise OrganizeError(f"Source/output path now contains a symlink: {part}")


def _check_source_stability(plan: OrganizationPlan) -> None:
    for delivery_id, path in plan.resolved_deliveries.items():
        _assert_no_symlinks(path)
        if _stats(path) != list(plan.source_stats[delivery_id]):
            raise OrganizeError(
                f"Source changed since planning: {path}; rebuild the plan"
            )


def _directory_member_stats(plan: OrganizationPlan) -> dict[Path, list[int]]:
    directories = {
        row["delivery_id"] for row in plan.deliveries if row["kind"] == "directory"
    }
    selected = {
        plan.resolved_deliveries[item.delivery_id] / item.member_relative_path
        for item in plan.files
        if item.delivery_id in directories
    }
    for path in selected:
        _assert_no_symlinks(path)
    return {path: _stats(path) for path in selected}


def _check_directory_members(snapshot: dict[Path, list[int]]) -> None:
    for path, before in snapshot.items():
        _assert_no_symlinks(path)
        if _stats(path) != before:
            raise OrganizeError(f"Directory source changed during organization: {path}")


def _verify_delivery_identities(plan: OrganizationPlan) -> None:
    _check_source_stability(plan)
    checked = {}
    for delivery in plan.deliveries:
        if delivery["kind"] != "zip":
            continue
        source = plan.resolved_deliveries[delivery["delivery_id"]]
        if source in checked:
            if checked[source] != delivery["sha256"]:
                raise OrganizeError(f"Conflicting archive identities for {source}")
            continue
        checked[source] = delivery["sha256"]
        current = _stats(source)
        trusted = (
            delivery.get("evidence")
            and delivery.get("verified_bytes") == str(current[2])
            and delivery.get("verified_mtime_ns") == str(current[3])
        )
        if trusted:
            logger.info(
                "Reusing verified archive identity: %s; selected member bytes will still be checked",
                source,
            )
        else:
            logger.info(
                "Hashing archive before copying: %s (%.1f MiB); no matching trusted identity",
                source,
                current[2] / 1024**2,
            )
            if _hash(source)[0] != delivery["sha256"]:
                raise OrganizeError(
                    f"Archive SHA-256 differs from declared identity: {source}"
                )
            logger.info("Verified archive identity: %s", source)
    _check_source_stability(plan)


def _header(path: Path) -> dict:
    # Sidecars are copied as bytes, never applied to reinterpret the TIFF header.
    import math

    import rasterio

    def number(value):
        if value is not None and not math.isfinite(value):
            return str(value)
        return value

    try:
        with (
            rasterio.Env(
                GDAL_PAM_ENABLED="NO", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"
            ),
            rasterio.open(path) as raster,
        ):
            return {
                "width": raster.width,
                "height": raster.height,
                "count": raster.count,
                "descriptions": list(raster.descriptions),
                "dtypes": list(raster.dtypes),
                "crs": raster.crs.to_wkt() if raster.crs else None,
                "transform": list(raster.transform),
                "nodata": number(raster.nodata),
                "nodatavals": [number(v) for v in raster.nodatavals],
                "header_scope": "internal_tiff_without_sidecar_interpretation",
            }
    except rasterio.errors.RasterioError as error:
        raise OrganizeError(
            f"Cannot inspect copied raster header {path}: {error}"
        ) from error


def _copy_payload(
    plan: OrganizationPlan, item: PlannedFile, target: Path, archive=None
) -> dict:
    """Stream a selected member once, hashing the same bytes that are written.

    The final verifier independently reads the completed output once. ZIP handles
    are opened once per archive by organize_dataset; direct helper calls may open
    their own handle. Neither path builds a restart record or temporary-copy state.
    """
    source = plan.resolved_deliveries[item.delivery_id]
    delivery = next(
        row for row in plan.deliveries if row["delivery_id"] == item.delivery_id
    )
    before = _stats(source)
    digest = hashlib.sha256()
    size = 0
    with ExitStack() as files:
        if delivery["kind"] == "zip":
            if archive is None:
                archive = files.enter_context(zipfile.ZipFile(source))
            stream = files.enter_context(archive.open(item.member_relative_path))
        else:
            selected = source / item.member_relative_path
            _assert_no_symlinks(selected)
            member_before = _stats(selected)
            stream = files.enter_context(selected.open("rb"))
        last_progress = time.monotonic()
        with target.open("xb") as output:
            while block := stream.read(1024 * 1024):
                digest.update(block)
                size += len(block)
                output.write(block)
                if time.monotonic() - last_progress >= 10:
                    logger.info(
                        "Still copying %s: %.1f / %.1f MiB",
                        item.destination,
                        size / 1024**2,
                        item.bytes / 1024**2,
                    )
                    last_progress = time.monotonic()
        if delivery["kind"] == "directory" and _stats(selected) != member_before:
            raise OrganizeError(f"Source file changed while copying: {selected}")
    if _stats(source) != before:
        raise OrganizeError(f"Source delivery changed while copying: {source}")
    value = digest.hexdigest()
    if size != item.bytes or (item.expected_sha256 and value != item.expected_sha256):
        raise OrganizeError(
            f"Source bytes differ from declaration: {item.member_relative_path}"
        )
    return {"sha256": value, "bytes": size}


def _provenance_documents(root: Path, plan: OrganizationPlan, files: dict) -> dict:
    """Build source/asset/crosswalk records once for writing or explicit audits."""
    documents = {}
    headers = {}
    deliveries = {row["delivery_id"]: row for row in plan.deliveries}
    by_pair = {
        (item.source_id, item.role): item for item in plan.files if not item.asset_id
    }
    sources = []
    for index, member in enumerate(plan.membership, 1):
        source_id = f"{member['region_code']}_{member['source_key']}"
        logger.info(
            "[Headers %d/%d] Recording internal TIFF metadata: %s",
            index,
            len(plan.membership),
            source_id,
        )
        row = dict(member)
        row.update(dataset_id=plan.recipe.dataset_id, source_id=source_id)
        for role in ("image", "label"):
            item = by_pair[source_id, role]
            metadata = files[item.destination]
            if metadata["sha256"] not in headers:
                headers[metadata["sha256"]] = _header(root / item.destination)
            row.update(
                {
                    f"{role}_path": item.destination,
                    f"{role}_sha256": metadata["sha256"],
                    f"{role}_bytes": metadata["bytes"],
                    f"{role}_delivery_sha256": deliveries[item.delivery_id]["sha256"],
                    f"{role}_header_json": json.dumps(
                        headers[metadata["sha256"]],
                        sort_keys=True,
                        allow_nan=False,
                    ),
                }
            )
        sources.append(row)
    fields = sorted({key for row in sources for key in row})
    documents["sources.csv"] = _csv_bytes(sources, fields)
    documents["regions.csv"] = _table_bytes(plan.regions)
    documents["filename_aliases.csv"] = _csv_bytes(
        list(plan.aliases), SCHEMAS["aliases"]
    )
    if plan.assets:
        files_by_asset = {
            (item.source_id, item.asset_id): item
            for item in plan.files
            if item.asset_id
        }
        assets = []
        for asset in plan.assets:
            item = files_by_asset[asset["source_id"], asset["asset_id"]]
            assets.append(
                dict(
                    asset,
                    sha256=files[item.destination]["sha256"],
                    bytes=files[item.destination]["bytes"],
                    delivery_sha256=deliveries[item.delivery_id]["sha256"],
                )
            )
        documents["assets.csv"] = _csv_bytes(
            assets, sorted({key for row in assets for key in row})
        )
    documents["inputs.json"] = _json_bytes(plan.logical)
    recipe = {
        key: getattr(plan.recipe, key)
        for key in (
            "schema_version",
            "dataset_id",
            "release_id",
            "input_catalog",
            "regions",
        )
    }
    documents["recipe.json"] = _json_bytes(recipe)
    return documents


def organize_dataset(plan: OrganizationPlan) -> Path:
    """Copy a fresh declared release in one pass; stop without publishing on failure."""
    destination = plan.destination
    stage = destination.with_name(f".{destination.name}.incomplete")
    try:
        for output in (destination, stage):
            _assert_no_symlinks(output)
            if output.exists():
                raise OrganizeError(
                    f"Output or incomplete attempt already exists: {output}; inspect it and choose a fresh release, or explicitly move/remove the incomplete attempt before rerunning from the beginning."
                )
        destination.parent.mkdir(parents=True, exist_ok=True)
        # The new directory claims this attempt. Existing/failed attempts are
        # never opened, reused or removed, and another writer cannot claim it.
        stage.mkdir()
        logger.info("Phase 1: verifying source identities before copying")
        _verify_delivery_identities(plan)
        member_stats = _directory_member_stats(plan)
        files = {}
        copied_members = {}
        total_bytes = sum(item.bytes for item in plan.files)
        completed_bytes = 0
        logger.info(
            "Phase 2: copying %d selected files (%.1f MiB)",
            len(plan.files),
            total_bytes / 1024**2,
        )
        with ExitStack() as sources:
            archives = {}
            for delivery in plan.deliveries:
                path = plan.resolved_deliveries[delivery["delivery_id"]]
                if delivery["kind"] == "zip" and path not in archives:
                    archives[path] = sources.enter_context(zipfile.ZipFile(path))
            for number, item in enumerate(plan.files, 1):
                logger.info(
                    "[%d/%d] Copying %s (%.1f MiB)",
                    number,
                    len(plan.files),
                    item.destination,
                    item.bytes / 1024**2,
                )
                target = stage / item.destination
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() or target.is_symlink():
                    raise OrganizeError(f"Unexpected existing staged output: {target}")
                member = (item.delivery_id, item.member_relative_path)
                if member in copied_members:
                    # Several identities may intentionally use the same member.
                    # Copy its verified bytes independently; never make hardlinks.
                    first_path, metadata = copied_members[member]
                    logger.info(
                        "Copying repeated member from this run's first copy: %s",
                        item.member_relative_path,
                    )
                    if metadata["bytes"] != item.bytes or (
                        item.expected_sha256
                        and metadata["sha256"] != item.expected_sha256
                    ):
                        raise OrganizeError(
                            f"Conflicting member declarations: {item.member_relative_path}"
                        )
                    shutil.copyfile(first_path, target)
                else:
                    archive = archives.get(plan.resolved_deliveries[item.delivery_id])
                    metadata = _copy_payload(plan, item, target, archive=archive)
                    copied_members[member] = (target, metadata)
                files[item.destination] = metadata
                completed_bytes += metadata["bytes"]
                logger.info(
                    "Copied %d/%d files (%.1f / %.1f MiB)",
                    number,
                    len(plan.files),
                    completed_bytes / 1024**2,
                    total_bytes / 1024**2,
                )
        _check_source_stability(plan)
        _check_directory_members(member_stats)
        logger.info("Phase 3: writing provenance and inspecting copied TIFF headers")
        for name, contents in _provenance_documents(stage, plan, files).items():
            files[name] = _write_control(stage / name, contents)
        expected = _control_names(plan) | {item.destination for item in plan.files}
        if set(files) != expected:
            raise OrganizeError("Staged inventory differs from declared release")
        manifest = {
            "schema_version": 1,
            "status": "complete",
            "plan_hash": plan.plan_hash,
            "files": files,
        }
        _write_control(stage / "manifest.json", _json_bytes(manifest))
        logger.info("Phase 4: independently verifying output bytes before publication")
        verify_organized_release(stage)
        _check_source_stability(plan)
        _check_directory_members(member_stats)
        if destination.exists() or destination.is_symlink():
            raise OrganizeError(f"Output appeared during publication: {destination}")
        os.rename(stage, destination)
        logger.info("Published complete release: %s", destination)
        return destination
    except (
        OSError,
        ValueError,
        zipfile.BadZipFile,
        RuntimeError,
        zlib.error,
        EOFError,
    ) as error:
        if isinstance(error, OrganizeError):
            raise
        raise OrganizeError(
            f"Organization stopped; incomplete attempt retained at {stage}: {error}"
        ) from error
