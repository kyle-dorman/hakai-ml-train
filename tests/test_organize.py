"""Preserved source bytes and provenance; one-pass failures never publish or resume."""

from __future__ import annotations

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
    with pytest.raises(OrganizeError, match="already exists"):
        organize_dataset(plan)
    assert inventory(release) == before
    assert all(path.stat().st_mtime_ns == value for path, value in mtimes.items())


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


@pytest.mark.parametrize("change", ["bytes", "extra", "empty-directory", "manifest"])
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
    before = inventory(release)
    with pytest.raises(OrganizeError):
        verify_organized_release(release, plan)
    assert inventory(release) == before


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

    def mutate_after_read(plan, item, temporary, **kwargs):
        nonlocal changed
        receipt = copy(plan, item, temporary, **kwargs)
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


def test_interruption_leaves_only_incomplete_files_and_next_run_refuses_them(
    tmp_path, monkeypatch
):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    original = inventory(fixture.root)
    copy_payload = engine._copy_payload

    def fail_after_copy(*args, **kwargs):
        copy_payload(*args, **kwargs)
        raise RuntimeError("one-pass interruption")

    with monkeypatch.context() as patch:
        patch.setattr(engine, "_copy_payload", fail_after_copy)
        with pytest.raises(OrganizeError, match="interruption"):
            organize_dataset(plan)
    stage = plan.destination.with_name(f".{plan.destination.name}.incomplete")
    assert stage.is_dir() and not plan.destination.exists()
    assert not (stage / "payload").exists()
    assert not (stage / "receipts").exists()
    assert not (stage / "state.json").exists()
    assert not (stage / "manifest.json").exists()
    before = inventory(stage)
    with pytest.raises(OrganizeError, match="incomplete|already exists"):
        organize_dataset(plan)
    assert inventory(stage) == before
    for name, expected in original.items():
        assert digest((fixture.root / name).read_bytes()) == expected


def test_one_pass_stage_prevents_a_competing_writer(tmp_path, monkeypatch):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    copy_payload = engine._copy_payload
    attempted = False

    def try_second_writer(*args, **kwargs):
        nonlocal attempted
        attempted = True
        with pytest.raises(OrganizeError, match="already exists"):
            organize_dataset(plan)
        return copy_payload(*args, **kwargs)

    monkeypatch.setattr(engine, "_copy_payload", try_second_writer)
    release = organize_dataset(plan)
    assert attempted
    verify_organized_release(release, plan)


def test_repeated_member_is_read_from_delivery_once_within_the_run(
    tmp_path, monkeypatch
):
    fixture = make_fixture(tmp_path / "input", multiple=True)
    plan = fixture.plan()
    copy_payload = engine._copy_payload
    reads = []

    def count_read(plan, item, target, **kwargs):
        reads.append((item.delivery_id, item.member_relative_path))
        return copy_payload(plan, item, target, **kwargs)

    monkeypatch.setattr(engine, "_copy_payload", count_read)
    release = organize_dataset(plan)
    assert len(reads) == len(set(reads)) < len(plan.files)
    verify_organized_release(release, plan)
    for item in plan.files:
        assert (release / item.destination).read_bytes() == fixture.payloads[
            item.member_relative_path
        ]


def test_zip_handle_is_opened_once_for_all_selected_members(tmp_path, monkeypatch):
    fixture = make_fixture(tmp_path / "input", multiple=True)
    plan = fixture.plan()
    original_open = engine.zipfile.ZipFile
    paths = []

    def open_once(path, *args, **kwargs):
        paths.append(Path(path))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(engine.zipfile, "ZipFile", open_once)
    organize_dataset(plan)
    assert paths == [fixture.root / "delivery.zip"]


def test_identical_payload_headers_are_read_once_during_provenance(
    tmp_path, monkeypatch
):
    fixture = make_fixture(tmp_path / "input", multiple=True)
    plan = fixture.plan()
    header = engine._header
    read_bytes = []

    def inspect_header(path):
        read_bytes.append(digest(path.read_bytes()))
        return header(path)

    monkeypatch.setattr(engine, "_header", inspect_header)
    organize_dataset(plan)
    assert len(read_bytes) == len(set(read_bytes)) == 3
