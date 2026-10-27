"""Explicit portable catalogs and complete, read-only organization planning."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import stat
import tomllib
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from kelpseg.paths import PathSettings

logger = logging.getLogger(__name__)


class OrganizeError(ValueError):
    """Invalid organization settings, inputs, or release state."""


@dataclass(frozen=True)
class OrganizeRecipe:
    schema_version: int
    dataset_id: str
    release_id: str
    input_catalog: str
    regions: str
    recipe_file: Path


@dataclass(frozen=True)
class PlannedFile:
    source_id: str
    role: str
    asset_id: str
    delivery_id: str
    member_relative_path: str
    destination: str
    expected_sha256: str
    bytes: int


@dataclass(frozen=True)
class OrganizationPlan:
    recipe: OrganizeRecipe
    paths: PathSettings
    catalog: Path
    destination: Path
    deliveries: tuple[dict[str, str], ...]
    membership: tuple[dict[str, str], ...]
    regions: tuple[dict[str, str], ...]
    aliases: tuple[dict[str, str], ...]
    assets: tuple[dict[str, str], ...]
    files: tuple[PlannedFile, ...]
    plan_hash: str
    logical: dict
    source_stats: dict[str, tuple[int, ...]]
    resolved_deliveries: dict[str, Path]


SCHEMAS = {
    "deliveries": [
        "delivery_id",
        "kind",
        "path",
        "sha256",
        "file_catalog",
        "evidence",
        "verified_bytes",
        "verified_mtime_ns",
    ],
    "membership": [
        "source_key",
        "region_code",
        "acquisition_date",
        "legacy_source_id",
        "image_delivery_id",
        "image_member",
        "label_delivery_id",
        "label_member",
        "image_sha256",
        "label_sha256",
    ],
    "regions": ["region_code", "legacy_region_id", "region_name"],
    "aliases": ["source_id", "asset_id", "role", "alias", "alias_type", "evidence"],
    "assets": [
        "source_id",
        "asset_id",
        "parent_role",
        "kind",
        "delivery_id",
        "member_relative_path",
        "destination",
        "sha256",
    ],
    "file_catalog": ["member_relative_path", "bytes", "sha256"],
}
OPTIONAL = {
    "deliveries": {"file_catalog", "verified_bytes", "verified_mtime_ns"},
    "membership": {"image_sha256", "label_sha256", "legacy_source_id"},
    "aliases": {"asset_id"},
    "assets": {"sha256"},
}
CONTROL_NAMES = {
    "regions.csv",
    "sources.csv",
    "filename_aliases.csv",
    "assets.csv",
    "recipe.json",
    "inputs.json",
    "manifest.json",
}


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stable_stat(path: Path) -> tuple[int, ...]:
    s = path.stat()
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def safe_relative(value: str, context: str = "path") -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise OrganizeError(
            f"{context}: unsafe relative path {value!r}; use plain forward-slash components."
        )
    return value


def _safe_path(root: Path, value: str, context: str) -> Path:
    safe_relative(value, context)
    path = root
    for part in value.split("/"):
        path = path / part
        if path.is_symlink():
            raise OrganizeError(f"{context}: symlinks are not allowed: {path}")
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise OrganizeError(f"{context}: path escapes {root}")
    return resolved


def _identifier(
    value: str, context: str, pattern: str = r"[a-z0-9][a-z0-9_-]*"
) -> None:
    if re.fullmatch(pattern, value) is None:
        raise OrganizeError(
            f"{context}: invalid identifier {value!r}; use lowercase ASCII letters/digits and allowed separators."
        )


def _hash(value: str, context: str, *, optional: bool = False) -> None:
    if optional and not value:
        return
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise OrganizeError(f"{context}: expected a lowercase SHA-256 digest.")


def read_table(
    path: Path, schema: str, *, contents: bytes | None = None
) -> list[dict[str, str]]:
    logger.info("Reading %s table: %s", schema, path)
    try:
        reader = csv.DictReader(
            io.StringIO(
                (path.read_bytes() if contents is None else contents).decode("utf-8"),
                newline="",
            )
        )
        fields = reader.fieldnames
        expected = set(SCHEMAS[schema])
        optional = OPTIONAL.get(schema, set())
        if (
            not fields
            or len(fields) != len(set(fields))
            or set(fields) - expected
            or expected - optional - set(fields)
        ):
            raise OrganizeError(
                f"{path}: invalid {schema} columns; expected {', '.join(SCHEMAS[schema])}."
            )
        rows = []
        for number, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise OrganizeError(f"{path}:{number}: malformed CSV row.")
            if any(not v for k, v in row.items() if k not in optional):
                raise OrganizeError(f"{path}:{number}: missing required value.")
            rows.append({key: row.get(key, "") for key in SCHEMAS[schema]})
        logger.info("Read %s: %d rows", path.name, len(rows))
        return rows
    except (OSError, UnicodeError, csv.Error) as error:
        raise OrganizeError(
            f"{path}: cannot read UTF-8 {schema} CSV ({error})."
        ) from error


def _unique(rows: list[dict], keys: tuple[str, ...], context: str) -> None:
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in keys)
        if key in seen:
            raise OrganizeError(f"{context}: duplicate key {key}.")
        seen.add(key)


def load_organize_recipe(path: str | Path) -> OrganizeRecipe:
    path = Path(path).resolve()
    logger.info("Reading organization recipe: %s", path)
    try:
        values = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise OrganizeError(
            f"{path}: cannot read organization TOML ({error})."
        ) from error
    keys = {"schema_version", "dataset_id", "release_id", "input_catalog", "regions"}
    if (
        set(values) != keys
        or type(values.get("schema_version")) is not int
        or values["schema_version"] != 1
    ):
        raise OrganizeError(
            f"{path}: use schema_version = 1 and exactly {', '.join(sorted(keys))}."
        )
    for key in keys - {"schema_version"}:
        if not isinstance(values[key], str) or not values[key]:
            raise OrganizeError(f"{path}: {key} must be a nonempty string.")
    for key in ("dataset_id", "release_id"):
        _identifier(values[key], key)
    safe_relative(values["input_catalog"], "input_catalog")
    # Tracked region tables may be one directory above a recipe, never absolute.
    region = values["regions"]
    if Path(region).is_absolute() or "\\" in region or ":" in region:
        raise OrganizeError("regions must be a relative recipe-directory path.")
    logger.info(
        "Recipe ready: dataset %s, release %s",
        values["dataset_id"],
        values["release_id"],
    )
    return OrganizeRecipe(**values, recipe_file=path)


def _zip_index(path: Path) -> dict[str, int]:
    entries = {}
    seen = set()
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.orig_filename != info.filename:
                    raise OrganizeError(f"ZIP {path}: unsafe original member spelling.")
                name = info.filename[:-1] if info.is_dir() else info.filename
                safe_relative(name, f"ZIP {path}")
                folded = name.casefold()
                if folded in seen:
                    raise OrganizeError(
                        f"ZIP {path}: duplicate normalized member {name!r}."
                    )
                seen.add(folded)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise OrganizeError(f"ZIP {path}: symlink member {name!r}.")
                if not info.is_dir():
                    entries[name] = info.file_size
    except (OSError, zipfile.BadZipFile) as error:
        raise OrganizeError(f"Cannot read ZIP directory {path}: {error}") from error
    return entries


def build_organization_plan(
    recipe: OrganizeRecipe, paths: PathSettings
) -> OrganizationPlan:
    """Validate the whole declared scope without payload reads or any writes."""
    logger.info("Planning dataset %s, release %s", recipe.dataset_id, recipe.release_id)
    try:
        plan = _build_plan(recipe, paths)
        logger.info(
            "Plan ready: %d pairs, %d companions, %d files, %d bytes",
            len(plan.membership),
            len(plan.assets),
            len(plan.files),
            sum(item.bytes for item in plan.files),
        )
        logger.info("Planned destination: %s", plan.destination)
        return plan
    except (OSError, ValueError) as error:
        if isinstance(error, OrganizeError):
            raise
        raise OrganizeError(f"Cannot plan organization: {error}") from error


def _build_plan(recipe: OrganizeRecipe, paths: PathSettings) -> OrganizationPlan:
    if not paths.data_root.is_dir():
        raise OrganizeError(
            f"Mount or create the intended data_root: {paths.data_root}"
        )
    catalog = _safe_path(paths.data_root, recipe.input_catalog, "input_catalog")
    regions_path = (recipe.recipe_file.parent / recipe.regions).resolve()
    table_bytes = {}

    def load_table(name: str):
        path = catalog / f"{name}.csv"
        if path.is_symlink():
            raise OrganizeError(f"Catalog table symlink is not allowed: {path}")
        data = path.read_bytes()
        table_bytes[f"{name}.csv"] = data
        return read_table(path, name, contents=data)

    tables = {key: load_table(key) for key in ("deliveries", "membership", "aliases")}
    tables["assets"] = load_table("assets") if (catalog / "assets.csv").exists() else []
    tables["regions"] = read_table(regions_path, "regions")
    for key, fields in (
        ("deliveries", ("delivery_id",)),
        ("regions", ("region_code",)),
        ("membership", ("region_code", "source_key")),
        ("assets", ("source_id", "asset_id")),
        ("aliases", ("source_id", "asset_id", "role", "alias_type", "alias")),
    ):
        _unique(tables[key], fields, key)
    if not tables["membership"] or not tables["deliveries"] or not tables["regions"]:
        raise OrganizeError("Declare at least one pair, delivery, and region.")
    destination = _safe_path(
        paths.data_root,
        f"data/2_organized/{recipe.dataset_id}/{recipe.release_id}",
        "destination",
    )
    staging = destination.with_name(f".{destination.name}.incomplete")
    regions = {r["region_code"] for r in tables["regions"]}
    for region in regions:
        _identifier(region, "region_code", r"[a-z0-9]+")
    resolved, stats, indexes, directory_hashes = {}, {}, {}, {}
    for number, delivery in enumerate(tables["deliveries"], start=1):
        did = delivery["delivery_id"]
        logger.info(
            "Checking delivery %d/%d: %s", number, len(tables["deliveries"]), did
        )
        _identifier(did, "delivery_id")
        _hash(delivery["sha256"], f"delivery {did}")
        if delivery["kind"] not in {"zip", "directory"}:
            raise OrganizeError(f"delivery {did}: kind must be zip or directory.")
        source = _safe_path(paths.data_root, delivery["path"], f"delivery {did}")
        for output in (destination, staging):
            if (
                source == output
                or source.is_relative_to(output)
                or output.is_relative_to(source)
            ):
                raise OrganizeError(
                    f"delivery {did}: source/output/staging overlap: {source}"
                )
        resolved[did] = source
        stats[did] = stable_stat(source)
        if delivery["kind"] == "zip":
            if not source.is_file() or delivery["file_catalog"]:
                raise OrganizeError(
                    f"delivery {did}: ZIP needs a regular file and empty file_catalog."
                )
            for key in ("verified_bytes", "verified_mtime_ns"):
                if delivery[key] and (
                    not delivery[key].isdigit() or int(delivery[key]) < 0
                ):
                    raise OrganizeError(f"delivery {did}: invalid {key}.")
            if bool(delivery["verified_bytes"]) != bool(delivery["verified_mtime_ns"]):
                raise OrganizeError(
                    f"delivery {did}: supply both trusted verification stat fields or neither."
                )
            logger.info("Reading ZIP member index: %s (no payload reads)", source)
            indexes[did] = _zip_index(source)
            logger.info(
                "Indexed %d file members for delivery %s", len(indexes[did]), did
            )
        else:
            if not source.is_dir():
                raise OrganizeError(
                    f"delivery {did}: directory does not exist: {source}"
                )
            fp = _safe_path(
                catalog, delivery["file_catalog"], f"delivery {did} file_catalog"
            )
            catalog_bytes = fp.read_bytes()
            if hashlib.sha256(catalog_bytes).hexdigest() != delivery["sha256"]:
                raise OrganizeError(f"delivery {did}: file_catalog SHA-256 mismatch.")
            rows = read_table(fp, "file_catalog", contents=catalog_bytes)
            _unique(rows, ("member_relative_path",), f"delivery {did} file_catalog")
            indexes[did], directory_hashes[did] = {}, {}
            for row in rows:
                member = safe_relative(row["member_relative_path"])
                _hash(row["sha256"], f"delivery {did} member {member}")
                if not row["bytes"].isdigit():
                    raise OrganizeError(
                        f"delivery {did}: invalid byte size for {member}"
                    )
                indexes[did][member] = int(row["bytes"])
                directory_hashes[did][member] = row["sha256"]
    # Neither catalog nor recipe-region input may overlap an output workspace.
    for source in (catalog, regions_path):
        if any(
            source == p or source.is_relative_to(p) or p.is_relative_to(source)
            for p in (destination, staging)
        ):
            raise OrganizeError(f"catalog/output overlap: {source}")
    files = []
    source_ids = set()

    def add_file(
        sid: str, role: str, aid: str, did: str, member: str, dest: str, expected: str
    ):
        safe_relative(member, "member")
        safe_relative(dest, "destination")
        if dest.casefold().endswith((".organize-part", ".tmp")):
            raise OrganizeError(f"Destination uses reserved temporary suffix: {dest}")
        if did not in indexes or member not in indexes[did]:
            raise OrganizeError(
                f"{sid} {role}: missing declared delivery/member {did}:{member}"
            )
        _hash(expected, f"{sid} {role}", optional=True)
        if did in directory_hashes:
            digest = directory_hashes[did][member]
            if expected and expected != digest:
                raise OrganizeError(
                    f"{sid}: expected hash conflicts with file_catalog for {member}"
                )
            expected = digest
            source = _safe_path(resolved[did], member, f"{sid} member")
            if not source.is_file() or source.stat().st_size != indexes[did][member]:
                raise OrganizeError(f"{sid}: missing or changed-size source {source}")
        files.append(
            PlannedFile(
                sid, role, aid, did, member, dest, expected, indexes[did][member]
            )
        )

    for row in tables["membership"]:
        if row["region_code"] not in regions:
            raise OrganizeError(
                f"Unknown region {row['region_code']!r}; declare it in regions.csv."
            )
        key = row["source_key"]
        _identifier(key, "source_key", r"[0-9]{8}(?:_[a-z0-9]+)*")
        try:
            day = date.fromisoformat(row["acquisition_date"])
        except ValueError as error:
            raise OrganizeError(
                f"Invalid acquisition_date {row['acquisition_date']!r}"
            ) from error
        if day.isoformat() != row["acquisition_date"] or not key.startswith(
            day.strftime("%Y%m%d")
        ):
            raise OrganizeError(
                f"source_key {key} must start with acquisition_date YYYYMMDD."
            )
        sid = row["region_code"] + "_" + key
        source_ids.add(sid)
        for role, folder in (("image", "images"), ("label", "labels")):
            add_file(
                sid,
                role,
                "",
                row[f"{role}_delivery_id"],
                row[f"{role}_member"],
                f"{folder}/{sid}.tif",
                row[f"{role}_sha256"],
            )
    asset_ids = {}
    for row in tables["assets"]:
        sid, aid = row["source_id"], row["asset_id"]
        _identifier(aid, "asset_id")
        if sid not in source_ids or row["parent_role"] not in {
            "image",
            "label",
            "pair",
        }:
            raise OrganizeError(f"asset {aid}: dangling source or invalid parent_role.")
        _identifier(row["kind"], "asset kind")
        asset_ids[(sid, aid)] = row["parent_role"]
        add_file(
            sid,
            row["parent_role"],
            aid,
            row["delivery_id"],
            row["member_relative_path"],
            row["destination"],
            row["sha256"],
        )
    for row in tables["aliases"]:
        sid, aid, role = row["source_id"], row["asset_id"], row["role"]
        if (
            sid not in source_ids
            or role not in {"image", "label", "pair"}
            or (aid and asset_ids.get((sid, aid)) != role)
        ):
            raise OrganizeError(
                f"alias {row['alias']!r}: dangling owner or conflicting role."
            )
        _identifier(row["alias_type"], "alias_type")
    destinations = [f.destination.casefold() for f in files]
    if len(destinations) != len(set(destinations)):
        raise OrganizeError(
            "Case-folded destination collision; choose distinct explicit names."
        )
    for dest in destinations:
        if dest.split("/")[0] in CONTROL_NAMES or any(
            other.startswith(dest + "/") for other in destinations
        ):
            raise OrganizeError(
                f"Destination collides with a control file or directory: {dest}"
            )
    normalized = {
        key: sorted(rows, key=lambda r: json.dumps(r, sort_keys=True))
        for key, rows in tables.items()
    }
    # Physical locations/stat evidence are resolution hints, never content identity.
    normalized["deliveries"] = [
        {
            k: v
            for k, v in row.items()
            if k not in {"path", "file_catalog", "verified_bytes", "verified_mtime_ns"}
        }
        for row in sorted(tables["deliveries"], key=lambda r: r["delivery_id"])
    ]
    logical = {
        "recipe": {
            "schema_version": 1,
            "dataset_id": recipe.dataset_id,
            "release_id": recipe.release_id,
            "input_catalog": recipe.input_catalog,
            "regions": recipe.regions,
        },
        **normalized,
    }
    manifest = catalog / "catalog_manifest.json"
    if manifest.exists():
        if manifest.is_symlink():
            raise OrganizeError(f"Catalog provenance cannot be a symlink: {manifest}")
        provenance = json.loads(manifest.read_bytes())
        if (
            not isinstance(provenance, dict)
            or provenance.get("schema_version") != 1
            or not isinstance(provenance.get("tables"), dict)
        ):
            raise OrganizeError(f"Invalid catalog provenance manifest: {manifest}")
        actual_tables = {
            name: hashlib.sha256(data).hexdigest() for name, data in table_bytes.items()
        }
        if actual_tables != provenance["tables"]:
            raise OrganizeError(
                f"Catalog tables differ from their completion provenance: {manifest}"
            )
        # Raw CSV hashes authenticate snapshots; normalized declarations below
        # define identity independently of row order and local resolution hints.
        logical["catalog_provenance"] = {
            key: value for key, value in provenance.items() if key != "tables"
        }
    digest = hashlib.sha256(
        (json.dumps(logical, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    ).hexdigest()
    # Preview can reject known output conflicts without claiming payload verification.
    for output, record_name in (
        (destination, "manifest.json"),
        (staging, "state.json"),
    ):
        if output.exists():
            record_path = output / record_name
            if (
                not output.is_dir()
                or record_path.is_symlink()
                or not record_path.is_file()
            ):
                raise OrganizeError(
                    f"Conflicting output without organizer identity: {output}"
                )
            try:
                record = json.loads(record_path.read_bytes())
            except (ValueError, UnicodeError) as error:
                raise OrganizeError(
                    f"Unreadable output identity {record_path}: {error}"
                ) from error
            if not isinstance(record, dict) or record.get("plan_hash") != digest:
                raise OrganizeError(
                    f"Conflicting output belongs to a different plan: {output}"
                )
            if output == destination and (
                record.get("status") != "complete" or record.get("schema_version") != 1
            ):
                raise OrganizeError(f"Output lacks valid completion identity: {output}")
    return OrganizationPlan(
        recipe=recipe,
        paths=paths,
        catalog=catalog,
        destination=destination,
        deliveries=tuple(
            sorted(tables["deliveries"], key=lambda row: row["delivery_id"])
        ),
        membership=tuple(normalized["membership"]),
        regions=tuple(normalized["regions"]),
        aliases=tuple(normalized["aliases"]),
        assets=tuple(normalized["assets"]),
        files=tuple(sorted(files, key=lambda item: item.destination)),
        plan_hash=digest,
        logical=logical,
        source_stats=stats,
        resolved_deliveries=resolved,
    )
