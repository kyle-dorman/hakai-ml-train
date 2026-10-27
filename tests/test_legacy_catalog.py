"""Historical reconstruction is an explicit metadata conversion, not discovery."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from kelpseg.paths import PathSettings
from kelpseg.prepare.legacy_catalog import (
    ARCHIVES,
    HISTORICAL_ROOT,
    _asset_rows,
    _source_key,
    build_legacy_ca_bc_catalog,
)
from kelpseg.prepare.organize_inputs import OrganizeError


def write_rows(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def historical_metadata(tmp_path):
    root = tmp_path / "external"
    audit = root / "audits/task026_originals_v1"
    backup = root / "backups/task027_raw_reference_audit_v1"
    audit.mkdir(parents=True)
    backup.mkdir(parents=True)
    repo = tmp_path / "checkout"
    regions = repo / "configs/regions.csv"
    regions.parent.mkdir(parents=True)
    regions.write_bytes(
        (Path(__file__).resolve().parents[1] / "configs/regions.csv").read_bytes()
    )
    region_rows = {row["region_code"]: row for row in csv.DictReader(regions.open())}
    current, members, files, extra, reconstruction, merge, split = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )

    def member(archive, name):
        members.append(
            dict(archive=archive, member=name, bytes="17", is_directory="False")
        )

    for index in range(369):
        bc = index >= 339
        region = "012" if bc else f"{index % 11 + 1:03}"
        key = (
            f"20210813_193301_80_241_8_band_Clip{index - 339}"
            if bc
            else f"{region}_20200422_173136_{index:04x}"
        )
        archive = (
            "Planet8bSR_BC_Labelled.zip"
            if bc
            else ("ca_data.zip" if index < 325 else "extra_data.zip")
        )
        row = dict(
            source_tiff_id=key,
            dataset="bc" if bc else "ca",
            region_id=region_rows[region]["legacy_region_id"],
            region_name=region_rows[region]["region_name"],
            acquisition_date="2021-08-13" if bc else "2020-04-22",
        )
        extra_row = dict(source_id=key)
        for role in ("image", "label"):
            relative = (
                f"bc/Planet8bSR_BC_Labelled/10km_tiles/val/{role}s/{key}.TIF"
                if bc
                else f"ca/{role}s/{key}.tif"
            )
            row[f"source_{role}"] = str(HISTORICAL_ROOT / relative)
            path = (
                relative.removeprefix("bc/")
                if bc
                else (
                    f"extra_data/{role}s/long_name_{index}.tif"
                    if index >= 325
                    else f"{role}s/{key}.tif"
                )
            )
            member(archive, path)
            extra_row[f"{role}_member"] = path
            files.append(
                dict(
                    collection_id="bc" if bc else "ca",
                    absolute_path=str(HISTORICAL_ROOT / relative),
                    bytes="17",
                )
            )
            if bc:
                member(archive, path + ".aux.xml")
                member(
                    archive, path + ".ovr"
                ) if role == "image" or index == 342 else None
                # Only one label pair has two exact auxiliaries.
                if role == "label" and index != 342:
                    members.pop()
                if role == "image":
                    member(archive, str(Path(path).with_suffix(".tfw")))
        if not bc and index < 325:
            member(archive, f"nan_mask/{key}.tif")
        if index == 0:
            member(archive, f"images/{key}.tif.ovr")
        if not bc and index >= 325:
            extra.append(extra_row)
        if index < 260 or (bc and index != 368):
            long = (
                key
                if bc
                else f"20200422_173136_01_{index:04x}_3B_AnalyticMS_SR_8b_harmonized_region"
            )
            rec = dict(source_stem=key, image_name_stem=long)
            old = dict(image_name_stem=key)
            for role in ("image", "label"):
                rec[f"{role}_archive"] = archive
                rec[f"{role}_member"] = extra_row[f"{role}_member"]
                rec[f"output_{role}"] = str(
                    HISTORICAL_ROOT / f"hakai_match/raw_data/train/{role}s/{long}.tif"
                )
                old[f"source_{role}"] = row[f"source_{role}"]
                old[f"output_{role}"] = str(
                    HISTORICAL_ROOT / f"merged_ds/train/{role}s/{key}.tif"
                )
            reconstruction.append(rec)
            merge.append(old)
            split.append(dict(image_name_stem=long, split="TRAIN"))
        current.append(row)
    named_rows = {
        root / "merged_all_regions_v1/raster_manifest.csv": current,
        audit / "archive_members.csv": members,
        audit / "files.csv": files,
        audit / "pairs.csv": [
            dict(
                collection_id="bc",
                pairing_context="Planet8bSR_BC_Labelled/full_scenes",
                source_id=f"scene{i}",
            )
            for i in range(6)
        ],
        root / "merged_ds/merge_manifest.csv": merge,
        root / "hakai_match/reconstruction_manifest.csv": reconstruction,
        repo / "planet8b_image_splits.csv": split,
    }
    for path, rows in named_rows.items():
        write_rows(path, rows)
    lineage = dict(
        membership=dict(extra_archive_mapping=extra),
        input_hashes_after={str(path): digest(path) for path in named_rows},
    )
    (audit / "lineage_findings.json").write_text(json.dumps(lineage))
    frozen = []
    for archive, sha in ARCHIVES.items():
        path = root / "zip_archive" / archive
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"not read by metadata conversion")
        stat = path.stat()
        frozen.append(
            dict(
                source=str(HISTORICAL_ROOT / "zip_archive" / archive),
                group="raw",
                sha256=sha,
                size=str(stat.st_size),
                mtime_ns=str(stat.st_mtime_ns),
                hash_provenance="synthetic trusted identity",
            )
        )
    write_rows(backup / "payload_manifest.csv", frozen)
    (backup / "completion.json").write_text('{"status":"complete"}')
    manifest = dict(
        status="complete",
        completion_sha256=digest(backup / "completion.json"),
        receipt_sha256={
            "payload_manifest.csv": digest(backup / "payload_manifest.csv")
        },
    )
    (backup / "manifest.json").write_text(json.dumps(manifest))
    settings = PathSettings(tmp_path / "paths.toml", root, root / "runs")
    return settings, regions, root / "preparation_inputs/ca_bc/v1"


def test_complete_conversion_associations_and_fresh_output_requirement(
    historical_metadata,
):
    paths, regions, destination = historical_metadata
    result = build_legacy_ca_bc_catalog(paths, regions, destination)
    assert result == destination
    manifest = json.loads((destination / "catalog_manifest.json").read_text())
    assert manifest["counts"]["pairs"] == 369
    assert manifest["counts"]["known_long_alias_owners"] == 290
    assert len(manifest["excluded_bc_full_scene_ids"]) == 6
    with (destination / "assets.csv").open() as stream:
        assets = list(csv.DictReader(stream))
    assert len(assets) == 418
    label_assets = [row for row in assets if row["parent_role"] == "label"]
    assert {row["asset_id"] for row in label_assets} == {
        "label_overview",
        "label_aux_xml",
    }
    assert all(row["source_id"].endswith("clip3") for row in label_assets)
    assert all(row["destination"].startswith("labels/") for row in label_assets)
    aliases = list(csv.DictReader((destination / "aliases.csv").open()))
    long_owners = {
        row["source_id"] for row in aliases if row["alias_type"] == "long_name"
    }
    assert len(long_owners) == 290
    assert not any(str(paths.data_root) in row["alias"] for row in aliases)
    before = {path.name: path.stat().st_mtime_ns for path in destination.iterdir()}
    with pytest.raises(OrganizeError, match="fresh destination"):
        build_legacy_ca_bc_catalog(paths, regions, destination)
    assert before == {
        path.name: path.stat().st_mtime_ns for path in destination.iterdir()
    }


def test_changed_archive_stops_before_catalog_write(historical_metadata):
    paths, regions, destination = historical_metadata
    (paths.data_root / "zip_archive/ca_data.zip").write_bytes(b"changed")
    with pytest.raises(OrganizeError, match="changed since Task 027"):
        build_legacy_ca_bc_catalog(paths, regions, destination)
    assert not destination.exists()


def test_changed_audit_stops_before_catalog_write(historical_metadata):
    paths, regions, destination = historical_metadata
    with (paths.data_root / "merged_all_regions_v1/raster_manifest.csv").open(
        "a"
    ) as stream:
        stream.write("unexpected\n")
    with pytest.raises(OrganizeError, match="changed Task 026 evidence"):
        build_legacy_ca_bc_catalog(paths, regions, destination)
    assert not destination.exists()


@pytest.mark.parametrize(
    ("legacy", "family", "expected"),
    [
        ("001_20200422_173136_2277", "ca", ("001", "20200422_173136_2277")),
        (
            "20210812_184548_90_2448_3B_AnalyticMS_SR_8b_harmonized_clip5",
            "bc",
            ("012", "20210812_184548_90_2448_clip5"),
        ),
        (
            "20210813_193301_80_241_8_band_Clip3",
            "bc",
            ("012", "20210813_193301_80_241_clip3"),
        ),
    ],
)
def test_explicit_key_rules(legacy, family, expected):
    assert _source_key(legacy, family) == expected


def test_unreviewed_key_is_not_guessed():
    with pytest.raises(OrganizeError, match="unsupported BC"):
        _source_key("20210813_unknown_clip3", "bc")


def test_asset_count_contradiction_is_not_dropped():
    with pytest.raises(OrganizeError, match="325 masks"):
        _asset_rows([], {})


def test_recorded_split_hygiene_is_accepted_and_documented(historical_metadata):
    paths, regions, destination = historical_metadata
    split_path = regions.parent.parent / "planet8b_image_splits.csv"
    current = split_path.read_bytes()
    historical = current.removesuffix(b"\n").replace(b"\n", b"\r\n")
    lineage_path = paths.data_root / "audits/task026_originals_v1/lineage_findings.json"
    lineage = json.loads(lineage_path.read_text())
    lineage["input_hashes_after"][str(split_path)] = hashlib.sha256(
        historical
    ).hexdigest()
    lineage_path.write_text(json.dumps(lineage))
    build_legacy_ca_bc_catalog(paths, regions, destination)
    manifest = json.loads((destination / "catalog_manifest.json").read_text())
    equivalence = manifest["evidence_equivalences"]["old_split"]
    assert equivalence["actual_sha256"] == digest(split_path)
    assert (
        equivalence["expected_historical_sha256"]
        == hashlib.sha256(historical).hexdigest()
    )
    assert "inverse bytes SHA256 verified" in equivalence["rule"]


def test_split_row_change_does_not_use_hygiene_exception(historical_metadata):
    paths, regions, destination = historical_metadata
    split_path = regions.parent.parent / "planet8b_image_splits.csv"
    original = split_path.read_bytes()
    historical = original.removesuffix(b"\n").replace(b"\n", b"\r\n")
    lineage_path = paths.data_root / "audits/task026_originals_v1/lineage_findings.json"
    lineage = json.loads(lineage_path.read_text())
    lineage["input_hashes_after"][str(split_path)] = hashlib.sha256(
        historical
    ).hexdigest()
    lineage_path.write_text(json.dumps(lineage))
    split_path.write_bytes(original.replace(b"TRAIN", b"TEST", 1))
    with pytest.raises(OrganizeError, match="changed Task 026 evidence old_split"):
        build_legacy_ca_bc_catalog(paths, regions, destination)
    assert not destination.exists()


@pytest.mark.parametrize("incomplete", [False, True])
def test_existing_catalog_attempt_stops_before_evidence_reads(
    historical_metadata, monkeypatch, incomplete
):
    paths, regions, destination = historical_metadata
    output = (
        destination.with_name(f".{destination.name}.incomplete")
        if incomplete
        else destination
    )
    output.mkdir(parents=True)
    evidence = output / "preserve.txt"
    evidence.write_text("Do not reuse or remove this prior attempt.")
    before = evidence.read_bytes(), evidence.stat().st_mtime_ns

    def forbidden(*args, **kwargs):
        pytest.fail("known output conflict should stop before reading evidence")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    with pytest.raises(OrganizeError, match="fresh destination"):
        build_legacy_ca_bc_catalog(paths, regions, destination)
    monkeypatch.undo()
    assert (evidence.read_bytes(), evidence.stat().st_mtime_ns) == before


def test_failed_catalog_write_leaves_incomplete_output_without_recovery(
    tmp_path, monkeypatch
):
    from kelpseg.prepare.legacy_catalog import _publish

    destination = tmp_path / "catalog"
    stage = tmp_path / ".catalog.incomplete"
    original_open = Path.open

    def fail_second_file(path, *args, **kwargs):
        if path == stage / "second.csv":
            raise OSError("fixture write failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_second_file)
    with pytest.raises(OSError, match="fixture write failure"):
        _publish(destination, {"first.csv": b"a,b\n", "second.csv": b"c,d\n"})
    monkeypatch.undo()
    assert not destination.exists()
    assert (stage / "first.csv").read_bytes() == b"a,b\n"
    with pytest.raises(OrganizeError, match="fresh destination"):
        _publish(destination, {"first.csv": b"replacement"})
    assert (stage / "first.csv").read_bytes() == b"a,b\n"
    assert {path.name for path in tmp_path.iterdir()} == {".catalog.incomplete"}
