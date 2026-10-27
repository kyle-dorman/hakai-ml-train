"""Copy declared payloads without changing bytes; verify before atomic publication."""

from __future__ import annotations

import csv
import fcntl
import hashlib
import json
import logging
import os
import time
import zipfile
import zlib
from contextlib import contextmanager
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


def _atomic_json(path: Path, value: object) -> None:
    """Own exactly one deterministic temporary file, refusing unknown leftovers."""
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(_json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _write_control(path: Path, contents: bytes) -> None:
    # A prior interrupted control write is recoverable only if byte-identical.
    if path.exists():
        if path.read_bytes() != contents:
            raise OrganizeError(f"Conflicting existing control file: {path}")
        return
    with path.open("xb") as stream:
        stream.write(contents)
        stream.flush()
        os.fsync(stream.fileno())


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


def _read_provenance_table(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)):
            raise OrganizeError(f"Invalid provenance table columns: {path}")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise OrganizeError(f"Malformed provenance table: {path}")
    return rows


def _verify_provenance(root: Path, plan: OrganizationPlan, files: dict) -> None:
    sources = _read_provenance_table(root / "sources.csv")
    expected_ids = {f"{r['region_code']}_{r['source_key']}" for r in plan.membership}
    if (
        len(sources) != len(plan.membership)
        or {r.get("source_id") for r in sources} != expected_ids
    ):
        raise OrganizeError(
            "Source provenance identities/count differ from declared pairs"
        )
    sources_by_id = {row["source_id"]: row for row in sources}
    deliveries = {row["delivery_id"]: row for row in plan.deliveries}
    primaries = {
        (item.source_id, item.role): item for item in plan.files if not item.asset_id
    }
    for index, member in enumerate(plan.membership, 1):
        source_id = f"{member['region_code']}_{member['source_key']}"
        logger.info(
            "[Headers %d/%d] Checking %s", index, len(plan.membership), source_id
        )
        expected = dict(member, dataset_id=plan.recipe.dataset_id, source_id=source_id)
        for role in ("image", "label"):
            item = primaries[source_id, role]
            metadata = files[item.destination]
            expected.update(
                {
                    f"{role}_path": item.destination,
                    f"{role}_sha256": metadata["sha256"],
                    f"{role}_bytes": str(metadata["bytes"]),
                    f"{role}_delivery_sha256": deliveries[item.delivery_id]["sha256"],
                    f"{role}_header_json": json.dumps(
                        _header(root / item.destination),
                        sort_keys=True,
                        allow_nan=False,
                    ),
                }
            )
        if sources_by_id[source_id] != expected:
            raise OrganizeError(
                f"Source provenance differs from declared inputs/verified bytes: {source_id}"
            )
    for item in plan.files:
        if (
            item.expected_sha256
            and files[item.destination]["sha256"] != item.expected_sha256
        ):
            raise OrganizeError(f"Expected source hash differs for {item.destination}")
        if files[item.destination]["bytes"] != item.bytes:
            raise OrganizeError(f"Expected source size differs for {item.destination}")
    if plan.assets:
        assets = _read_provenance_table(root / "assets.csv")
        expected_keys = {(row["source_id"], row["asset_id"]) for row in plan.assets}
        actual_keys = {(row.get("source_id"), row.get("asset_id")) for row in assets}
        if len(assets) != len(plan.assets) or actual_keys != expected_keys:
            raise OrganizeError(
                "Asset provenance identities/count differ from declared assets"
            )
        assets_by_key = {(row["source_id"], row["asset_id"]): row for row in assets}
        for asset in plan.assets:
            metadata = files[asset["destination"]]
            expected = dict(
                asset,
                sha256=metadata["sha256"],
                bytes=str(metadata["bytes"]),
                delivery_sha256=deliveries[asset["delivery_id"]]["sha256"],
            )
            if assets_by_key[asset["source_id"], asset["asset_id"]] != expected:
                raise OrganizeError(
                    f"Asset provenance differs from declared inputs/verified bytes: {asset['destination']}"
                )
    for name, contents in (
        ("regions.csv", _table_bytes(plan.regions)),
        ("filename_aliases.csv", _csv_bytes(list(plan.aliases), SCHEMAS["aliases"])),
    ):
        if (root / name).read_bytes() != contents:
            raise OrganizeError(
                f"Provenance snapshot differs from declared inputs: {name}"
            )
    expected_recipe = {
        key: getattr(plan.recipe, key)
        for key in (
            "schema_version",
            "dataset_id",
            "release_id",
            "input_catalog",
            "regions",
        )
    }
    if _read_json(root / "recipe.json") != expected_recipe:
        raise OrganizeError("Recipe snapshot differs from declared inputs")


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


@contextmanager
def _writer_lock(path: Path):
    if path.is_symlink():
        raise OrganizeError(f"Unsafe writer lock symlink: {path}")
    with path.open("a+b") as stream:
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise OrganizeError(
                f"Another organizer is writing this release: {path}"
            ) from error
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


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


def _verify_delivery_identities(plan: OrganizationPlan, prior: dict | None) -> None:
    _check_source_stability(plan)
    for delivery in plan.deliveries:
        if delivery["kind"] != "zip":
            continue
        source = plan.resolved_deliveries[delivery["delivery_id"]]
        current = _stats(source)
        trusted = (
            delivery.get("evidence")
            and delivery.get("verified_bytes") == str(current[2])
            and delivery.get("verified_mtime_ns") == str(current[3])
        )
        if prior is not None:
            trusted = trusted and prior.get(delivery["delivery_id"]) == current
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


def _receipt_name(item: PlannedFile) -> str:
    return hashlib.sha256(item.destination.encode()).hexdigest() + ".json"


def _copy_payload(plan: OrganizationPlan, item: PlannedFile, temporary: Path) -> dict:
    delivery = next(r for r in plan.deliveries if r["delivery_id"] == item.delivery_id)
    source = plan.resolved_deliveries[item.delivery_id]
    before = _stats(source)
    digest = hashlib.sha256()
    size = 0

    def transfer(stream):
        nonlocal size
        last_progress = time.monotonic()
        with temporary.open("xb") as output:
            while block := stream.read(1024 * 1024):
                digest.update(block)
                size += len(block)
                output.write(block)
                now = time.monotonic()
                if now - last_progress >= 10:
                    logger.info(
                        "Still copying %s: %.1f / %.1f MiB",
                        item.destination,
                        size / 1024**2,
                        item.bytes / 1024**2,
                    )
                    last_progress = now
            output.flush()
            os.fsync(output.fileno())

    if delivery["kind"] == "zip":
        with (
            zipfile.ZipFile(source) as archive,
            archive.open(item.member_relative_path) as stream,
        ):
            transfer(stream)
    else:
        selected = source / item.member_relative_path
        _assert_no_symlinks(selected)
        member_before = _stats(selected)
        with selected.open("rb") as stream:
            transfer(stream)
        if _stats(selected) != member_before:
            raise OrganizeError(f"Source file changed while copying: {selected}")
    if _stats(source) != before:
        raise OrganizeError(f"Source delivery changed while copying: {source}")
    value = digest.hexdigest()
    if size != item.bytes or (item.expected_sha256 and value != item.expected_sha256):
        raise OrganizeError(
            f"Source bytes differ from declaration: {item.member_relative_path}"
        )
    logger.info("Independently verifying copied bytes: %s", item.destination)
    if _hash(temporary) != (value, size):
        raise OrganizeError(f"Independent output byte verification failed: {temporary}")
    return {"destination": item.destination, "sha256": value, "bytes": size}


def _verify_receipt(root: Path, item: PlannedFile, receipt: dict) -> None:
    if (
        set(receipt) != {"destination", "sha256", "bytes"}
        or receipt["destination"] != item.destination
    ):
        raise OrganizeError(f"Invalid file receipt for {item.destination}")
    if _hash(root / item.destination) != (receipt["sha256"], receipt["bytes"]):
        raise OrganizeError(f"Completed staged output is corrupt: {item.destination}")
    if receipt["bytes"] != item.bytes or (
        item.expected_sha256 and receipt["sha256"] != item.expected_sha256
    ):
        raise OrganizeError(
            f"Staged output differs from expected source: {item.destination}"
        )


def _write_provenance(root: Path, plan: OrganizationPlan, receipts: dict) -> None:
    deliveries = {row["delivery_id"]: row for row in plan.deliveries}
    by_pair = {
        (item.source_id, item.role): item for item in plan.files if not item.asset_id
    }
    sources = []
    for index, member in enumerate(plan.membership, 1):
        source_id = f"{member['region_code']}_{member['source_key']}"
        logger.info(
            "[Headers %d/%d] Reading internal TIFF metadata: %s",
            index,
            len(plan.membership),
            source_id,
        )
        row = dict(member)
        row.update(dataset_id=plan.recipe.dataset_id, source_id=source_id)
        for role in ("image", "label"):
            item = by_pair[source_id, role]
            receipt = receipts[item.destination]
            row.update(
                {
                    f"{role}_path": item.destination,
                    f"{role}_sha256": receipt["sha256"],
                    f"{role}_bytes": receipt["bytes"],
                    f"{role}_delivery_sha256": deliveries[item.delivery_id]["sha256"],
                    f"{role}_header_json": json.dumps(
                        _header(root / item.destination),
                        sort_keys=True,
                        allow_nan=False,
                    ),
                }
            )
        sources.append(row)
    fields = sorted({key for row in sources for key in row})
    _write_control(root / "sources.csv", _csv_bytes(sources, fields))
    _write_control(root / "regions.csv", _table_bytes(plan.regions))
    _write_control(
        root / "filename_aliases.csv",
        _csv_bytes(list(plan.aliases), SCHEMAS["aliases"]),
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
                    sha256=receipts[item.destination]["sha256"],
                    bytes=receipts[item.destination]["bytes"],
                    delivery_sha256=deliveries[item.delivery_id]["sha256"],
                )
            )
        _write_control(
            root / "assets.csv",
            _csv_bytes(assets, sorted({key for row in assets for key in row})),
        )
    _write_control(root / "inputs.json", _json_bytes(plan.logical))
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
    _write_control(root / "recipe.json", _json_bytes(recipe))


def _resume_workspace(work: Path, plan: OrganizationPlan) -> tuple[Path, dict]:
    inventory = _inventory(work)
    state = _read_json(work / "state.json")
    if state.get("plan_hash") != plan.plan_hash or state.get("logical") != plan.logical:
        raise OrganizeError(
            f"Incomplete output belongs to a changed recipe/catalog: {work}"
        )
    payload = work / "payload"
    allowed = {"state.json", "copying.json"}
    allowed |= {f"receipts/{_receipt_name(item)}" for item in plan.files}
    allowed |= {f"payload/{item.destination}" for item in plan.files}
    allowed |= {f"payload/{name}" for name in _control_names(plan) | {"manifest.json"}}
    copying = None
    if "copying.json" in inventory:
        copying = _read_json(work / "copying.json")
        selected = next(
            (
                item
                for item in plan.files
                if item.destination == copying.get("destination")
            ),
            None,
        )
        if selected is None or copying != {
            "destination": selected.destination,
            "plan_hash": plan.plan_hash,
        }:
            raise OrganizeError(f"Invalid interrupted-copy record: {work}")
        temporary = selected.destination + ".organize-part"
        allowed.add(f"payload/{temporary}")
    unknown = inventory - allowed
    if unknown:
        raise OrganizeError(f"Unexpected staged files: {', '.join(sorted(unknown))}")
    _reject_unexpected_directories(work, allowed)
    receipts = {}
    for index, item in enumerate(plan.files, 1):
        receipt_path = work / "receipts" / _receipt_name(item)
        target = payload / item.destination
        if receipt_path.exists():
            logger.info(
                "[Resume %d/%d] Checking staged file: %s",
                index,
                len(plan.files),
                item.destination,
            )
            receipt = _read_json(receipt_path)
            _verify_receipt(payload, item, receipt)
            receipts[item.destination] = receipt
        elif target.exists() and (
            copying is None or copying["destination"] != item.destination
        ):
            raise OrganizeError(
                f"Staged output has no verified receipt: {target}; retain it for inspection"
            )
    if copying is not None:
        # Only this exact organizer-owned unfinished temporary can be recreated.
        target = payload / (copying["destination"] + ".organize-part")
        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise OrganizeError(f"Unsafe interrupted temporary: {target}")
            logger.info("Recreating identified interrupted temporary: %s", target)
            target.unlink()
    if copying is not None:
        (work / "copying.json").unlink()
    return payload, receipts


def organize_dataset(plan: OrganizationPlan, *, resume: bool = False) -> Path:
    """Materialize a complete plan, or explicitly resume its verified staging.

    Completed releases are verified and returned without rewriting. Incomplete
    work uses a sibling workspace; unknown/corrupt files are retained on error.
    A process crash releases the OS lock automatically. Only an identified
    unfinished ``.organize-part`` file may be recreated during explicit resume.
    """
    destination = plan.destination
    total_bytes = sum(item.bytes for item in plan.files)
    logger.info(
        "Organizing %s/%s: %d files, %.1f MiB",
        plan.recipe.dataset_id,
        plan.recipe.release_id,
        len(plan.files),
        total_bytes / 1024**2,
    )
    work = destination.with_name(f".{destination.name}.incomplete")
    lock = destination.with_name(f".{destination.name}.lock")
    try:
        _check_source_stability(plan)
        member_stats = _directory_member_stats(plan)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with _writer_lock(lock):
            if destination.exists() or destination.is_symlink():
                logger.info(
                    "Completed release already exists; verifying without rewriting: %s",
                    destination,
                )
                verify_organized_release(destination, plan)
                return destination
            state = None
            if work.exists() or work.is_symlink():
                if not resume:
                    raise OrganizeError(
                        f"Incomplete work exists: {work}; inspect it and use --resume"
                    )
                logger.info("Resuming incomplete release: %s", work)
                state = _read_json(work / "state.json")
                if state.get("plan_hash") != plan.plan_hash:
                    raise OrganizeError(
                        f"Incomplete output belongs to a changed recipe/catalog: {work}"
                    )
            _verify_delivery_identities(
                plan, state.get("source_stats") if state else None
            )
            if state is None:
                if resume:
                    raise OrganizeError(
                        f"No incomplete work to resume: {work}; omit --resume for a new release"
                    )
                logger.info("Creating incomplete workspace: %s", work)
                work.mkdir()
                (work / "payload").mkdir()
                (work / "receipts").mkdir()
                state = {
                    "plan_hash": plan.plan_hash,
                    "logical": plan.logical,
                    "source_stats": {
                        key: list(value) for key, value in plan.source_stats.items()
                    },
                }
                _atomic_json(work / "state.json", state)
            payload, receipts = _resume_workspace(work, plan)
            completed_bytes = sum(receipt["bytes"] for receipt in receipts.values())
            logger.info(
                "Ready to copy: %d/%d files already verified",
                len(receipts),
                len(plan.files),
            )
            for index, item in enumerate(plan.files, 1):
                if item.destination in receipts:
                    logger.info(
                        "[%d/%d] Reusing verified staged file: %s",
                        index,
                        len(plan.files),
                        item.destination,
                    )
                    # Directory identity is the frozen per-file catalog; a
                    # completed output does not prove its current source bytes.
                    delivery = next(
                        r
                        for r in plan.deliveries
                        if r["delivery_id"] == item.delivery_id
                    )
                    if delivery["kind"] == "directory":
                        selected_source = (
                            plan.resolved_deliveries[item.delivery_id]
                            / item.member_relative_path
                        )
                        _assert_no_symlinks(selected_source)
                        before_source = _stats(selected_source)
                        if (
                            _hash(selected_source) != (item.expected_sha256, item.bytes)
                            or _stats(selected_source) != before_source
                        ):
                            raise OrganizeError(
                                f"Directory source changed: {item.member_relative_path}"
                            )
                    continue
                logger.info(
                    "[%d/%d] Copying %s: %s (%.1f MiB)",
                    index,
                    len(plan.files),
                    "companion" if item.asset_id else item.role,
                    item.destination,
                    item.bytes / 1024**2,
                )
                target = payload / item.destination
                target.parent.mkdir(parents=True, exist_ok=True)
                _atomic_json(
                    work / "copying.json",
                    {"destination": item.destination, "plan_hash": plan.plan_hash},
                )
                temporary = target.with_name(target.name + ".organize-part")
                receipt = _copy_payload(plan, item, temporary)
                if target.exists():
                    # Identified interruption after rename but before receipt:
                    # recopy the source, then verify the existing target in full.
                    if _hash(target) != (receipt["sha256"], receipt["bytes"]):
                        raise OrganizeError(
                            f"Unreceipted staged output is corrupt: {target}"
                        )
                    temporary.unlink()
                else:
                    os.rename(temporary, target)
                _atomic_json(work / "receipts" / _receipt_name(item), receipt)
                (work / "copying.json").unlink()
                receipts[item.destination] = receipt
                completed_bytes += receipt["bytes"]
                logger.info(
                    "Copied and verified %d/%d files (%.1f / %.1f MiB)",
                    len(receipts),
                    len(plan.files),
                    completed_bytes / 1024**2,
                    total_bytes / 1024**2,
                )
            _check_source_stability(plan)
            _check_directory_members(member_stats)
            logger.info("Writing provenance tables and reading original TIFF headers")
            _write_provenance(payload, plan, receipts)
            expected_names = _control_names(plan) | {
                item.destination for item in plan.files
            }
            inventory = _inventory(payload)
            if inventory - {"manifest.json"} != expected_names:
                raise OrganizeError("Staged inventory differs from declared release")
            hashes = {}
            logger.info("Checking final inventory and hashing release files")
            for index, name in enumerate(sorted(expected_names), 1):
                logger.info("[Final hash %d/%d] %s", index, len(expected_names), name)
                digest, size = _hash(payload / name)
                hashes[name] = {"sha256": digest, "bytes": size}
                if name in receipts and hashes[name] != {
                    key: receipts[name][key] for key in ("sha256", "bytes")
                }:
                    raise OrganizeError(f"Payload changed before publication: {name}")
            manifest = {
                "schema_version": 1,
                "status": "complete",
                "plan_hash": plan.plan_hash,
                "files": hashes,
            }
            _write_control(payload / "manifest.json", _json_bytes(manifest))
            verify_organized_release(payload, plan)
            _check_source_stability(plan)
            _check_directory_members(member_stats)
            if destination.exists() or destination.is_symlink():
                raise OrganizeError(
                    f"Output appeared during publication: {destination}"
                )
            logger.info("Publishing verified directory: %s", destination)
            os.rename(payload, destination)
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
            f"Organization stopped; incomplete evidence retained at {work}: {error}"
        ) from error
