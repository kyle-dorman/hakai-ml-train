"""Preserved scientific payloads, independently verified restart and publication."""

from __future__ import annotations

import fcntl
import json
from pathlib import Path

import pytest
import rasterio
from organize_fixtures import (
    ASSET_FIELDS,
    DELIVERY_FIELDS,
    MEMBERSHIP_FIELDS,
    digest,
    inventory,
    make_fixture,
    read_csv,
    write_csv,
)

import kelpseg.prepare.organize as engine
from kelpseg.prepare.organize import organize_dataset, verify_organized_release
from kelpseg.prepare.organize_inputs import OrganizeError


def interrupted(fixture, monkeypatch):
    plan = fixture.plan()
    atomic = engine._atomic_json

    def stop_after_verified_receipt(path, value):
        atomic(path, value)
        if path.parent.name == "receipts":
            raise KeyboardInterrupt("fixture interruption after one verified file")

    with monkeypatch.context() as patch:
        patch.setattr(engine, "_atomic_json", stop_after_verified_receipt)
        with pytest.raises(KeyboardInterrupt):
            organize_dataset(plan)
    stage = plan.destination.with_name(f".{plan.destination.name}.incomplete")
    assert stage.is_dir()
    assert not plan.destination.exists()
    assert not list(stage.rglob("manifest.json"))
    assert len(list((stage / "receipts").glob("*.json"))) == 1
    return plan, stage


@pytest.mark.parametrize(
    "kind,dataset", [("zip", "island"), ("directory", "unrelated_coast")]
)
def test_independent_datasets_preserve_all_bytes_and_metadata(
    tmp_path: Path, kind, dataset
):
    fixture = make_fixture(
        tmp_path / dataset, kind=kind, dataset_id=dataset, multiple=True
    )
    original = inventory(fixture.root)
    plan = fixture.plan()
    release = organize_dataset(plan)
    assert release == plan.destination
    result = verify_organized_release(release, plan)
    assert result.plan_hash == plan.plan_hash
    assert result.file_count == len(plan.files) + 6
    for item in plan.files:
        copied = release / item.destination
        assert copied.read_bytes() == fixture.payloads[item.member_relative_path]
        assert (
            not copied.samefile(fixture.root / "delivery" / item.member_relative_path)
            if kind == "directory"
            else True
        )
    assert "unselected.txt" not in inventory(release)
    rows = read_csv(release / "sources.csv")
    assert len(rows) == 3
    assert all(row["dataset_id"] == dataset for row in rows)
    assert len({row["image_sha256"] for row in rows}) == 1
    assert len({row["label_sha256"] for row in rows}) == 2
    first = next(row for row in rows if row["source_id"] == fixture.source_id)
    image_header = json.loads(first["image_header_json"])
    label_header = json.loads(first["label_header_json"])
    assert (image_header["height"], image_header["width"], image_header["count"]) == (
        8,
        10,
        3 if kind == "directory" else 8,
    )
    assert (label_header["height"], label_header["width"], label_header["count"]) == (
        4,
        5,
        1,
    )
    assert image_header["transform"] != label_header["transform"]
    assert image_header["descriptions"] == (
        ["red", "green", "blue"] if kind == "directory" else [None] * 8
    )
    assert image_header["nodata"] == 65535
    assert label_header["nodata"] == 0
    assert first["image_member"] == "strange/original-image.TIF"
    assert first["image_delivery_sha256"] == plan.deliveries[0]["sha256"]
    with rasterio.open(release / first["label_path"]) as label:
        assert set(label.read(1).ravel()) == {0, 1, 2, 3, 4}
    aliases = read_csv(release / "filename_aliases.csv")
    assert sum(row["alias"] == "Repeated long alias.TIF" for row in aliases) == 3
    assets = read_csv(release / "assets.csv")
    assert len(assets) == 3
    assert (
        next(row for row in assets if row["asset_id"] == "label_aux")["parent_role"]
        == "label"
    )
    for name, value in original.items():
        assert digest((fixture.root / name).read_bytes()) == value
    before = inventory(release)
    mtimes = {
        path: path.stat().st_mtime_ns for path in release.rglob("*") if path.is_file()
    }
    assert organize_dataset(fixture.plan()) == release
    assert organize_dataset(fixture.plan(), resume=True) == release
    assert inventory(release) == before
    assert all(path.stat().st_mtime_ns == value for path, value in mtimes.items())


def test_interrupted_copy_requires_explicit_resume_and_rehashes_outputs(
    tmp_path: Path, monkeypatch
):
    fixture = make_fixture(tmp_path / "input")
    plan, stage = interrupted(fixture, monkeypatch)
    with pytest.raises(OrganizeError, match="resume"):
        organize_dataset(plan)
    released = organize_dataset(fixture.plan(), resume=True)
    assert released.is_dir()
    assert not (stage / "payload").exists()
    verify_organized_release(released)


@pytest.mark.parametrize(
    "change", ["corrupt-output", "unknown-file", "recipe", "catalog", "source"]
)
def test_resume_refuses_changed_or_unrecognized_state(
    tmp_path: Path, monkeypatch, change
):
    fixture = make_fixture(tmp_path / "input")
    plan, stage = interrupted(fixture, monkeypatch)
    if change == "corrupt-output":
        path = next(path for path in (stage / "payload").rglob("*") if path.is_file())
        path.write_bytes(b"corrupt verified output")
    elif change == "unknown-file":
        (stage / "unrecognized.txt").write_text("Preserve this evidence")
    elif change == "recipe":
        fixture.recipe.write_text(
            fixture.recipe.read_text().replace(
                'dataset_id = "island"', 'dataset_id = "changed"'
            )
        )
        # The original destination is part of the copied stage's identity.
        changed = fixture.plan()
        from dataclasses import replace

        plan = replace(changed, destination=plan.destination)
    elif change == "catalog":
        rows = read_csv(fixture.catalog / "membership.csv")
        rows[0]["legacy_source_id"] = "changed identity evidence"
        write_csv(fixture.catalog / "membership.csv", MEMBERSHIP_FIELDS, rows)
    else:
        with (fixture.root / "delivery.zip").open("ab") as stream:
            stream.write(b"source was changed")
    before = inventory(stage)
    with pytest.raises(OrganizeError):
        if change == "catalog":
            plan = fixture.plan()
        organize_dataset(plan, resume=True)
    assert not plan.destination.exists()
    assert inventory(stage) == before


def test_expected_member_hash_failure_never_publishes(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input")
    rows = read_csv(fixture.catalog / "membership.csv")
    rows[0]["image_sha256"] = "a" * 64
    write_csv(fixture.catalog / "membership.csv", MEMBERSHIP_FIELDS, rows)
    plan = fixture.plan()
    with pytest.raises(OrganizeError):
        organize_dataset(plan)
    assert not plan.destination.exists()
    assert not list(plan.destination.parent.rglob("manifest.json"))


def test_archive_parent_identity_is_checked_when_untrusted(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input")
    rows = read_csv(fixture.catalog / "deliveries.csv")
    rows[0]["sha256"] = "b" * 64
    write_csv(fixture.catalog / "deliveries.csv", DELIVERY_FIELDS, rows)
    plan = fixture.plan()
    with pytest.raises(OrganizeError):
        organize_dataset(plan)
    assert not plan.destination.exists()


def test_directory_source_changes_cannot_be_hidden_by_same_size(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input", kind="directory")
    plan = fixture.plan()
    image = fixture.root / "delivery/strange/original-image.TIF"
    data = image.read_bytes()
    image.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
    with pytest.raises(OrganizeError):
        organize_dataset(plan)
    assert not plan.destination.exists()


@pytest.mark.parametrize(
    "change", ["bytes", "extra", "empty-directory", "manifest", "recipe"]
)
def test_completed_release_is_immutable_and_verified(tmp_path: Path, change):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    release = organize_dataset(plan)
    if change == "bytes":
        (release / plan.files[0].destination).write_bytes(b"corrupt")
    elif change == "extra":
        (release / "unexpected").write_text("Do not remove")
    elif change == "empty-directory":
        (release / "unknown-empty-directory").mkdir()
    elif change == "manifest":
        manifest = release / "manifest.json"
        manifest.write_text(manifest.read_text().replace('"complete"', '"incomplete"'))
    else:
        rows = read_csv(fixture.catalog / "membership.csv")
        rows[0]["legacy_source_id"] = "different"
        write_csv(fixture.catalog / "membership.csv", MEMBERSHIP_FIELDS, rows)
    before = inventory(release)
    with pytest.raises(OrganizeError):
        if change == "recipe":
            plan = fixture.plan()
        organize_dataset(plan)
    assert inventory(release) == before


def test_concurrent_writer_is_refused(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    plan.destination.parent.mkdir(parents=True)
    lock = plan.destination.with_name(f".{plan.destination.name}.lock")
    with lock.open("w") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(OrganizeError, match="writing"):
                organize_dataset(plan)
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    assert not plan.destination.exists()


def test_crash_before_receipt_recovers_only_after_rechecking_source(
    tmp_path: Path, monkeypatch
):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    atomic = engine._atomic_json

    def stop_before_receipt(path, value):
        if path.parent.name == "receipts":
            raise KeyboardInterrupt("crash between payload rename and receipt")
        atomic(path, value)

    with monkeypatch.context() as patch:
        patch.setattr(engine, "_atomic_json", stop_before_receipt)
        with pytest.raises(KeyboardInterrupt):
            organize_dataset(plan)
    stage = plan.destination.with_name(f".{plan.destination.name}.incomplete")
    target = next(path for path in (stage / "payload").rglob("*") if path.is_file())
    unchanged = target.stat().st_mtime_ns
    release = organize_dataset(fixture.plan(), resume=True)
    assert (
        release / target.relative_to(stage / "payload")
    ).stat().st_mtime_ns == unchanged
    verify_organized_release(release, plan)


def test_identified_interrupted_temporary_is_recreated_without_touching_originals(
    tmp_path: Path, monkeypatch
):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    copy = engine._copy_payload

    def stop_mid_copy(plan, item, temporary):
        temporary.write_bytes(b"identified interrupted temporary")
        raise KeyboardInterrupt("crash while streaming")

    with monkeypatch.context() as patch:
        patch.setattr(engine, "_copy_payload", stop_mid_copy)
        with pytest.raises(KeyboardInterrupt):
            organize_dataset(plan)
    stage = plan.destination.with_name(f".{plan.destination.name}.incomplete")
    assert len(list(stage.rglob("*.organize-part"))) == 1
    before = digest((fixture.root / "delivery.zip").read_bytes())
    assert copy is engine._copy_payload
    release = organize_dataset(fixture.plan(), resume=True)
    verify_organized_release(release, plan)
    assert digest((fixture.root / "delivery.zip").read_bytes()) == before


def test_unknown_temporary_is_not_deleted_on_resume(tmp_path: Path, monkeypatch):
    fixture = make_fixture(tmp_path / "input")
    plan, stage = interrupted(fixture, monkeypatch)
    unknown = stage / "payload/unidentified.organize-part"
    unknown.write_bytes(b"do not delete")
    before = inventory(stage)
    with pytest.raises(OrganizeError):
        organize_dataset(plan, resume=True)
    assert inventory(stage) == before


@pytest.mark.parametrize("compressed", [False, True])
def test_corrupt_selected_zip_payload_fails_crc_and_never_publishes(
    tmp_path: Path, compressed
):
    import struct
    import zipfile

    fixture = make_fixture(tmp_path / "input")
    archive_path = fixture.root / "delivery.zip"
    # Exercise both CRC failures and invalid compressed streams.
    compression = zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED
    with zipfile.ZipFile(archive_path, "w", compression=compression) as archive:
        for name, contents in fixture.payloads.items():
            archive.writestr(name, contents)
    with zipfile.ZipFile(archive_path) as archive:
        info = archive.getinfo("strange/original-image.TIF")
    with archive_path.open("r+b") as stream:
        stream.seek(info.header_offset)
        header = stream.read(30)
        filename_length, extra_length = struct.unpack_from("<HH", header, 26)
        offset = info.header_offset + 30 + filename_length + extra_length
        stream.seek(offset)
        byte = stream.read(1)
        stream.seek(offset)
        stream.write(bytes([byte[0] ^ 255]))
    rows = read_csv(fixture.catalog / "deliveries.csv")
    # Parent identity reflects the corrupt archive, so member verification must fail.
    rows[0]["sha256"] = digest(archive_path.read_bytes())
    write_csv(fixture.catalog / "deliveries.csv", DELIVERY_FIELDS, rows)
    plan = fixture.plan()
    with pytest.raises(OrganizeError):
        organize_dataset(plan)
    assert not plan.destination.exists()
    assert not list(plan.destination.parent.rglob("manifest.json"))


def test_directory_source_mutation_after_read_prevents_publication(
    tmp_path: Path, monkeypatch
):
    fixture = make_fixture(tmp_path / "input", kind="directory")
    plan = fixture.plan()
    copy = engine._copy_payload
    changed = False

    def mutate_after_read(plan, item, temporary):
        nonlocal changed
        receipt = copy(plan, item, temporary)
        if not changed:
            source = (
                plan.resolved_deliveries[item.delivery_id] / item.member_relative_path
            )
            contents = source.read_bytes()
            source.write_bytes(contents[:-1] + bytes([contents[-1] ^ 1]))
            changed = True
        return receipt

    monkeypatch.setattr(engine, "_copy_payload", mutate_after_read)
    with pytest.raises(OrganizeError):
        organize_dataset(plan)
    assert not plan.destination.exists()


def test_asset_ids_are_scoped_by_pair_owner(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input", multiple=True)
    assets = read_csv(fixture.catalog / "assets.csv")
    membership = read_csv(fixture.catalog / "membership.csv")
    second_id = f"{membership[1]['region_code']}_{membership[1]['source_key']}"
    assets.append(
        dict(
            assets[0],
            source_id=second_id,
            member_relative_path="different/annotated.tiff",
            destination=f"masks/{second_id}.tif",
        )
    )
    write_csv(fixture.catalog / "assets.csv", ASSET_FIELDS, assets)
    release = organize_dataset(fixture.plan())
    rows = read_csv(release / "assets.csv")
    masks = {row["source_id"]: row for row in rows if row["asset_id"] == "mask"}
    assert masks[fixture.source_id]["sha256"] == digest(
        fixture.payloads["support/water.tif"]
    )
    assert masks[second_id]["sha256"] == digest(
        fixture.payloads["different/annotated.tiff"]
    )
