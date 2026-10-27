"""Convert the named Task 026/027 historical metadata, never raster payloads.

This one-time converter is independent of the generic organizer. Historical
absolute paths are interpreted against their recorded original root; resulting
catalog locators are portable. The tracked split CSV sits beside ``configs/``
in the checkout containing the explicitly supplied regions CSV.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
from pathlib import Path

from kelpseg.paths import PathSettings
from kelpseg.prepare.organize_inputs import SCHEMAS, OrganizeError

logger = logging.getLogger(__name__)

ARCHIVES = {
    "ca_data.zip": "c51c40bc3fb8a4ec402dc11a4e928114f291fbe24278472c5d9a49dbace26c3b",
    "extra_data.zip": "594b4fb6c4ea8d75f85f0a66b9736fbfa8235a6e8494e685d33653b341fabd25",
    "Planet8bSR_BC_Labelled.zip": "de1bc465f512ce3bb6ae063773cfed7567acc55a47d5997c2bffa6f5fc07955f",
}
DELIVERY_IDS = {
    "ca_data.zip": "ca_data",
    "extra_data.zip": "extra_data",
    "Planet8bSR_BC_Labelled.zip": "bc_labelled",
}
HISTORICAL_ROOT = Path("/Volumes/x10pro/kelpseg")
ARCHIVE_BY_DELIVERY = {delivery: archive for archive, delivery in DELIVERY_IDS.items()}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise OrganizeError(f"Historical catalog: {message}")


def _digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def _rows(contents: bytes) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))
    _require(bool(reader.fieldnames), "missing CSV header")
    _require(
        len(reader.fieldnames) == len(set(reader.fieldnames)), "duplicate CSV header"
    )
    result = list(reader)
    _require(
        all(None not in row and None not in row.values() for row in result),
        "malformed CSV row",
    )
    return result


def _unique(rows: list[dict], key: str, context: str) -> dict:
    result = {row[key]: row for row in rows}
    _require(len(result) == len(rows), f"duplicate {context} {key}")
    return result


def _historical_relative(value: str) -> str:
    try:
        return Path(value).relative_to(HISTORICAL_ROOT).as_posix()
    except ValueError as error:
        raise OrganizeError(
            f"Historical catalog: unexpected original path {value}"
        ) from error


def _source_key(legacy: str, family: str) -> tuple[str, str]:
    """The only dataset-specific filename interpretation in preparation."""
    if family == "ca":
        match = re.fullmatch(r"(00[1-9]|01[01])_(\d{8}_\d{6}_[a-z0-9]+)", legacy)
        _require(match is not None, f"unsupported CA identity {legacy}")
        return match[1], match[2]
    _require(family == "bc", f"unsupported family {family}")
    match = re.fullmatch(
        r"(\d{8}_\d{6}_\d{2}_[a-z0-9]+)_(?:3B_AnalyticMS_SR_8b_harmonized|8_band)_[cC]lip(\d+)",
        legacy,
    )
    _require(match is not None, f"unsupported BC identity {legacy}")
    return "012", f"{match[1]}_clip{match[2]}"


def _membership_rows(current, extra, members, files, regions):
    declarations = []
    originals = {}
    extra_by_id = _unique(extra, "source_id", "extra archive mapping")
    _require(
        len(extra_by_id) == 14, "expected exactly 14 explicit extra archive mappings"
    )
    _unique(current, "source_tiff_id", "current membership")
    for row in current:
        legacy = row["source_tiff_id"]
        region, key = _source_key(legacy, row["dataset"])
        _require(region in regions, f"unknown region {region}")
        _require(
            regions[region]["legacy_region_id"] == row["region_id"],
            f"region disagreement for {legacy}",
        )
        _require(
            regions[region]["region_name"] == row["region_name"],
            f"region name disagreement for {legacy}",
        )
        archive = (
            "Planet8bSR_BC_Labelled.zip"
            if row["dataset"] == "bc"
            else ("extra_data.zip" if legacy in extra_by_id else "ca_data.zip")
        )
        declaration = dict(
            source_key=key,
            region_code=region,
            acquisition_date=row["acquisition_date"],
            legacy_source_id=legacy,
        )
        source_id = f"{region}_{key}"
        _require(source_id not in originals, f"canonical collision {source_id}")
        originals[source_id] = {}
        for role in ("image", "label"):
            original = _historical_relative(row[f"source_{role}"])
            if row["dataset"] == "bc":
                _require(
                    original.startswith("bc/Planet8bSR_BC_Labelled/10km_tiles/"),
                    f"non-tile BC membership {original}",
                )
                member = original.removeprefix("bc/")
            else:
                _require(
                    original == f"ca/{role}s/{legacy}.tif",
                    f"unexpected CA original {original}",
                )
                member = (
                    extra_by_id[legacy][f"{role}_member"]
                    if legacy in extra_by_id
                    else f"{role}s/{legacy}.tif"
                )
            _require(
                (archive, member) in members,
                f"missing archive locator {archive}:{member}",
            )
            _require(original in files, f"missing original inventory row {original}")
            _require(
                files[original]["bytes"] == members[archive, member]["bytes"],
                f"source/member size disagreement for {original}",
            )
            declaration[f"{role}_delivery_id"] = DELIVERY_IDS[archive]
            declaration[f"{role}_member"] = member
            declaration[f"{role}_sha256"] = ""
            originals[source_id][role] = original
        declarations.append(declaration)
    _require(len(declarations) == 369, "expected 369 current pairs")
    _require(
        sum(x["region_code"] == "012" for x in declarations) == 30,
        "expected 30 BC tiles",
    )
    _require(len({x["region_code"] for x in declarations}) == 12, "expected 12 regions")
    _require(
        set(extra_by_id) <= {x["legacy_source_id"] for x in declarations},
        "unselected extra mapping",
    )
    return declarations, originals


def _asset_rows(membership, members):
    """Exact reviewed parent relationships, without using inferred audit IDs."""
    result = []
    for row in membership:
        source_id = f"{row['region_code']}_{row['source_key']}"
        for role in ("image", "label"):
            delivery = row[f"{role}_delivery_id"]
            archive = ARCHIVE_BY_DELIVERY[delivery]
            parent = row[f"{role}_member"]
            # These are reviewed exact parent-relative relationships, not a
            # generic suffix-stripping heuristic for unknown sidecar families.
            candidates = [
                (
                    parent + ".ovr",
                    f"{role}_overview",
                    "overview",
                    f"{role}s/{source_id}.tif.ovr",
                ),
                (
                    parent + ".aux.xml",
                    f"{role}_aux_xml",
                    "aux_xml",
                    f"{role}s/{source_id}.tif.aux.xml",
                ),
            ]
            if role == "image":
                candidates.append(
                    (
                        str(Path(parent).with_suffix(".tfw")),
                        "image_worldfile",
                        "worldfile",
                        f"images/{source_id}.tfw",
                    )
                )
                if delivery == "ca_data":
                    candidates.append(
                        (
                            f"nan_mask/{row['legacy_source_id']}.tif",
                            "nan_mask",
                            "nan_mask_unknown",
                            f"masks/{source_id}.tif",
                        )
                    )
            for member, asset_id, kind, destination in candidates:
                if (archive, member) in members:
                    result.append(
                        dict(
                            source_id=source_id,
                            asset_id=asset_id,
                            parent_role=role,
                            kind=kind,
                            delivery_id=delivery,
                            member_relative_path=member,
                            destination=destination,
                            sha256="",
                        )
                    )
    _require(
        sum(x["asset_id"] == "nan_mask" for x in result) == 325, "expected 325 masks"
    )
    _require(
        sum(
            x["delivery_id"] == "ca_data" and x["asset_id"] == "image_overview"
            for x in result
        )
        == 1,
        "expected one CA overview",
    )
    bc_assets = [x for x in result if x["delivery_id"] == "bc_labelled"]
    _require(len(bc_assets) == 92, "expected 92 BC tile auxiliaries")
    _require(
        sum(x["parent_role"] == "label" for x in bc_assets) == 2,
        "expected two BC label auxiliaries",
    )
    # Every auxiliary within the selected tile or CA archive scope is mapped.
    observed = {
        (DELIVERY_IDS[a], m)
        for a, m in members
        if a in DELIVERY_IDS
        and not m.lower().endswith(".tif")
        and (
            a == "ca_data.zip"
            or (a == "Planet8bSR_BC_Labelled.zip" and "/10km_tiles/" in m)
        )
    }
    mapped = {
        (x["delivery_id"], x["member_relative_path"])
        for x in result
        if x["asset_id"] != "nan_mask"
    }
    _require(observed == mapped, "unmapped or unexpected selected-scope auxiliary")
    return result


def _alias_rows(
    membership, assets, originals, legacy_merge, reconstruction, old_split, evidence
):
    result = []
    by_legacy = {x["legacy_source_id"]: x for x in membership}
    reconstructed = _unique(reconstruction, "source_stem", "reconstruction")
    merged = _unique(legacy_merge, "image_name_stem", "legacy merge")
    split = _unique(old_split, "image_name_stem", "historical split")
    _require(
        len(reconstructed) == 289 and set(reconstructed) == set(merged),
        "legacy merge/reconstruction membership disagreement",
    )
    _require(
        {x["image_name_stem"] for x in reconstruction} == set(split),
        "reconstruction/old split names disagreement",
    )
    _require(set(reconstructed) <= set(by_legacy), "unknown reconstructed source")

    def add(source_id, role, alias, alias_type, reference, asset_id=""):
        result.append(
            dict(
                source_id=source_id,
                asset_id=asset_id,
                role=role,
                alias=alias,
                alias_type=alias_type,
                evidence=f"{reference}#sha256={evidence[reference]}",
            )
        )

    for row in membership:
        legacy = row["legacy_source_id"]
        source_id = f"{row['region_code']}_{row['source_key']}"
        for role in ("image", "label"):
            add(
                source_id,
                role,
                row[f"{role}_member"],
                "archive_member",
                "archive_members",
            )
            add(
                source_id,
                role,
                originals[source_id][role],
                "historical_source_path",
                "current_membership",
            )
            if row["region_code"] == "012":
                add(
                    source_id,
                    role,
                    Path(originals[source_id][role]).name,
                    "long_name",
                    "current_membership",
                )
            if legacy in reconstructed:
                record = reconstructed[legacy]
                merge = merged[legacy]
                _require(
                    _historical_relative(merge[f"source_{role}"])
                    == originals[source_id][role],
                    f"legacy source path disagreement for {legacy}",
                )
                _require(
                    record[f"{role}_archive"]
                    == ARCHIVE_BY_DELIVERY[row[f"{role}_delivery_id"]],
                    f"reconstruction delivery disagreement for {legacy}",
                )
                _require(
                    record[f"{role}_member"] == row[f"{role}_member"],
                    f"reconstruction member disagreement for {legacy}",
                )
                add(
                    source_id,
                    role,
                    _historical_relative(merge[f"output_{role}"]),
                    "legacy_merge_output",
                    "legacy_merge",
                )
                add(
                    source_id,
                    role,
                    _historical_relative(record[f"output_{role}"]),
                    "reconstructed_output",
                    "reconstruction",
                )
                if row["region_code"] != "012":
                    add(
                        source_id,
                        role,
                        Path(record[f"output_{role}"]).name,
                        "long_name",
                        "reconstruction",
                    )
        if legacy in reconstructed:
            add(
                source_id,
                "pair",
                reconstructed[legacy]["image_name_stem"],
                "legacy_split_name",
                "old_split",
            )
    for row in assets:
        add(
            row["source_id"],
            row["parent_role"],
            row["member_relative_path"],
            "archive_member",
            "archive_members",
            row["asset_id"],
        )
    long_owners = {x["source_id"] for x in result if x["alias_type"] == "long_name"}
    _require(
        len(long_owners) == 290, "expected 290 known long-name identities (79 absent)"
    )
    return result


def _split_hygiene_equivalence(contents: bytes, expected_sha256: str) -> bool:
    """Allow only Task 028's recorded line-ending/final-newline hygiene.

    Comparing the exact reconstructed historical bytes protects every parsed
    value, row order, delimiter and quote. This is never a general CSV semantic
    equivalence exception and applies only to the tracked split evidence.
    """
    return (
        b"\r" not in contents
        and contents.endswith(b"\n")
        and _digest(contents.removesuffix(b"\n").replace(b"\n", b"\r\n"))
        == expected_sha256
    )


def _table_bytes(rows, fields):
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(
        sorted(rows, key=lambda row: tuple(row.get(k, "") for k in fields))
    )
    return text.getvalue().encode()


def _publish(destination: Path, documents: dict[str, bytes]) -> Path:
    """Write one fresh catalog and leave any failed attempt for inspection."""
    stage = destination.with_name(f".{destination.name}.incomplete")
    for output in (destination, stage):
        if output.exists() or output.is_symlink():
            raise OrganizeError(
                f"Catalog output or incomplete attempt exists: {output}; choose a fresh destination."
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()
    logger.info("Creating metadata catalog: %s", destination)
    for name, content in documents.items():
        logger.info("Writing metadata file: %s (%d bytes)", name, len(content))
        with (stage / name).open("xb") as stream:
            stream.write(content)
    if destination.exists() or destination.is_symlink():
        raise OrganizeError(
            f"Catalog destination appeared during writing: {destination}"
        )
    stage.rename(destination)
    logger.info("Metadata catalog complete: %s", destination)
    return destination


def build_legacy_ca_bc_catalog(
    paths: PathSettings, regions_csv: Path, destination: Path
) -> Path:
    """Reconstruct only the declared 369-pair metadata catalog.

    No archive member or original TIFF is opened. Changed trusted ZIP stats
    fail this historical conversion; re-establish that affected identity before
    proceeding rather than silently accepting a modified archive.
    """
    # Do not rebuild evidence just to discover that an output already exists.
    destination = Path(destination)
    stage = destination.with_name(f".{destination.name}.incomplete")
    for output in (destination, stage):
        if output.exists() or output.is_symlink():
            raise OrganizeError(
                f"Catalog output or incomplete attempt exists: {output}; choose a fresh destination."
            )
    logger.info("Building historical CA/BC input catalog: %s", destination)
    logger.info("Using metadata evidence under: %s", paths.data_root)
    try:
        return _build_catalog(paths, Path(regions_csv), Path(destination))
    except (OSError, UnicodeError, csv.Error, KeyError, ValueError, TypeError) as error:
        if isinstance(error, OrganizeError):
            raise
        raise OrganizeError(f"Cannot construct historical catalog: {error}") from error


def _build_catalog(paths, regions_csv, destination):
    root = paths.data_root
    audit = root / "audits/task026_originals_v1"
    backup = root / "backups/task027_raw_reference_audit_v1"
    named = {
        "current_membership": root / "merged_all_regions_v1/raster_manifest.csv",
        "archive_members": audit / "archive_members.csv",
        "pairs": audit / "pairs.csv",
        "files": audit / "files.csv",
        "lineage": audit / "lineage_findings.json",
        "legacy_merge": root / "merged_ds/merge_manifest.csv",
        "reconstruction": root / "hakai_match/reconstruction_manifest.csv",
        "old_split": regions_csv.resolve().parent.parent / "planet8b_image_splits.csv",
        "regions": regions_csv,
        "backup_catalog": backup / "payload_manifest.csv",
        "backup_completion": backup / "completion.json",
        "backup_manifest": backup / "manifest.json",
    }
    contents = {}
    for number, (key, path) in enumerate(named.items(), start=1):
        logger.info("Reading evidence %d/%d: %s", number, len(named), path)
        _require(not path.is_symlink(), f"symlink evidence file {path}")
        before = path.stat()
        contents[key] = path.read_bytes()
        after = path.stat()
        _require(
            (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            == (after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            f"evidence changed while reading {path}",
        )
    evidence = {key: _digest(value) for key, value in contents.items()}
    manifest = json.loads(contents["backup_manifest"])
    _require(manifest["status"] == "complete", "Task 027 is incomplete")
    _require(
        manifest["completion_sha256"] == evidence["backup_completion"],
        "Task 027 completion identity mismatch",
    )
    _require(
        manifest["receipt_sha256"]["payload_manifest.csv"]
        == evidence["backup_catalog"],
        "Task 027 frozen catalog identity mismatch",
    )
    lineage = json.loads(contents["lineage"])
    # Reconcile the exact named historical tables with the completed audit.
    evidence_equivalences = {}
    known = lineage["input_hashes_after"]
    for key in (
        "archive_members",
        "pairs",
        "files",
        "legacy_merge",
        "reconstruction",
        "old_split",
        "current_membership",
    ):
        expected = [
            digest
            for path, digest in known.items()
            if Path(path).name == named[key].name
        ]
        _require(len(expected) == 1, f"missing or ambiguous Task 026 evidence {key}")
        if expected[0] != evidence[key]:
            _require(
                key == "old_split"
                and _split_hygiene_equivalence(contents[key], expected[0]),
                f"changed Task 026 evidence {key}",
            )
            evidence_equivalences[key] = {
                "expected_historical_sha256": expected[0],
                "actual_sha256": evidence[key],
                "rule": "Task028 CRLF without final newline to LF with final newline; inverse bytes SHA256 verified",
            }
    regions = _unique(_rows(contents["regions"]), "region_code", "region")
    _require(
        set(regions) == {f"{i:03}" for i in range(1, 13)},
        "expected fixed regions 001–012",
    )
    archive_rows = [
        x
        for x in _rows(contents["archive_members"])
        if x["archive"] in ARCHIVES and x["is_directory"] == "False"
    ]
    members = {(x["archive"], x["member"]): x for x in archive_rows}
    _require(len(members) == len(archive_rows), "duplicate archive member metadata")
    files = {}
    for row in _rows(contents["files"]):
        if row["collection_id"] in ("ca", "bc"):
            relative = _historical_relative(row["absolute_path"])
            _require(relative not in files, f"duplicate inventory path {relative}")
            files[relative] = row
    membership, originals = _membership_rows(
        _rows(contents["current_membership"]),
        lineage["membership"]["extra_archive_mapping"],
        members,
        files,
        regions,
    )
    logger.info("Mapped %d source pairs from historical membership", len(membership))
    assets = _asset_rows(membership, members)
    logger.info("Mapped %d masks and sidecars to their source pairs", len(assets))
    aliases = _alias_rows(
        membership,
        assets,
        originals,
        _rows(contents["legacy_merge"]),
        _rows(contents["reconstruction"]),
        _rows(contents["old_split"]),
        evidence,
    )
    logger.info("Reconciled %d recorded filename aliases", len(aliases))
    pair_rows = _rows(contents["pairs"])
    full_scenes = sorted(
        x["source_id"]
        for x in pair_rows
        if x["collection_id"] == "bc" and "/full_scenes" in x["pairing_context"]
    )
    _require(len(full_scenes) == 6, "expected six excluded BC full scenes")
    deliveries = []
    frozen = [x for x in _rows(contents["backup_catalog"]) if x["group"] == "raw"]
    frozen_by_name = {Path(x["source"]).name: x for x in frozen}
    _require(
        len(frozen) == 3 and set(frozen_by_name) == set(ARCHIVES),
        "unexpected raw archive catalog",
    )
    for archive, sha256 in ARCHIVES.items():
        logger.info("Checking trusted archive identity and stability: %s", archive)
        row = frozen_by_name[archive]
        _require(
            row["sha256"] == sha256, f"verified archive identity changed for {archive}"
        )
        relative = _historical_relative(row["source"])
        local = root / relative
        _require(not local.is_symlink(), f"archive symlink {local}")
        stat = local.stat()
        _require(
            stat.st_size == int(row["size"])
            and stat.st_mtime_ns == int(row["mtime_ns"]),
            f"archive changed since Task 027: {archive}; re-establish its hash before conversion",
        )
        deliveries.append(
            dict(
                delivery_id=DELIVERY_IDS[archive],
                kind="zip",
                path=relative,
                sha256=sha256,
                file_catalog="",
                evidence=f"Task027:backups/task027_raw_reference_audit_v1/payload_manifest.csv#sha256={evidence['backup_catalog']};{row['hash_provenance']}",
                verified_bytes=row["size"],
                verified_mtime_ns=row["mtime_ns"],
            )
        )
    tables = {
        "deliveries.csv": deliveries,
        "membership.csv": membership,
        "aliases.csv": aliases,
        "assets.csv": assets,
    }
    documents = {
        name: _table_bytes(rows, SCHEMAS[Path(name).stem])
        for name, rows in tables.items()
    }
    catalog_manifest = {
        "schema_version": 1,
        "producer": "kelpseg.prepare.legacy_catalog.build_legacy_ca_bc_catalog:v1",
        "producer_sha256": _digest(Path(__file__).read_bytes()),
        "evidence_sha256": evidence,
        "evidence_equivalences": evidence_equivalences,
        "tables": {name: _digest(value) for name, value in documents.items()},
        "counts": {
            "pairs": 369,
            "ca": 339,
            "bc": 30,
            "regions": 12,
            "masks": 325,
            "ca_auxiliaries": 1,
            "bc_auxiliaries": 92,
            "known_long_alias_owners": 290,
            "unverified_long_alias_owners": 79,
        },
        "excluded_bc_full_scene_ids": full_scenes,
        "limits": [
            "archive-member sizes and aliases establish metadata only",
            "member payload SHA256 is established by organization",
            "missing long aliases, mask semantics and untagged physical bands remain unknown",
        ],
    }
    documents["catalog_manifest.json"] = _json(catalog_manifest)
    return _publish(destination, documents)
