"""Strict declarations and portable, complete no-write organization plans."""

from __future__ import annotations

import csv
import stat
import zipfile
from pathlib import Path

import pytest
from organize_fixtures import (
    ALIAS_FIELDS,
    ASSET_FIELDS,
    DELIVERY_FIELDS,
    MEMBERSHIP_FIELDS,
    digest,
    inventory,
    make_fixture,
    read_csv,
    write_csv,
)
from typer.testing import CliRunner

from kelpseg.cli import app
from kelpseg.prepare.organize_inputs import OrganizeError, load_organize_recipe


@pytest.mark.parametrize("kind", ["zip", "directory"])
def test_planning_is_complete_portable_and_write_free(tmp_path: Path, kind: str):
    fixture = make_fixture(tmp_path / kind, kind=kind, multiple=True)
    before = inventory(fixture.root)
    plan = fixture.plan()
    assert len(plan.membership) == 3
    assert len(plan.files) == 9
    assert len(plan.assets) == 3
    assert plan.destination == fixture.root / "data/2_organized/island/v1"
    assert {item.destination for item in plan.files} >= {
        f"images/{fixture.source_id}.tif",
        f"labels/{fixture.source_id}.tif",
    }
    assert inventory(fixture.root) == before
    for name in ("membership.csv", "assets.csv", "aliases.csv"):
        path = fixture.catalog / name
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            rows, fields = list(reader), reader.fieldnames
        write_csv(path, fields, list(reversed(rows)))
    assert fixture.plan().plan_hash == plan.plan_hash
    # A machine-root move does not change the portable logical identity.
    moved = tmp_path / "another-machine"
    fixture.root.rename(moved)
    fixture.root = moved
    fixture.catalog = moved / "catalog"
    fixture.recipe = moved / "recipe.toml"
    fixture.settings = moved / "paths.toml"
    assert fixture.plan().plan_hash == plan.plan_hash


@pytest.mark.parametrize(
    "change", ["unknown", "version", "absolute", "escape", "uppercase", "date"]
)
def test_recipe_refuses_invalid_settings(tmp_path: Path, change: str):
    fixture = make_fixture(tmp_path / "input")
    text = fixture.recipe.read_text()
    replacements = {
        "unknown": text + 'hidden = "unexpected"\n',
        "version": text.replace("schema_version = 1", "schema_version = 99"),
        "absolute": text.replace(
            'input_catalog = "catalog"', 'input_catalog = "/catalog"'
        ),
        "escape": text.replace(
            'input_catalog = "catalog"', 'input_catalog = "../catalog"'
        ),
        "uppercase": text.replace('dataset_id = "island"', 'dataset_id = "Island"'),
        "date": text.replace('release_id = "v1"', 'release_id = ""'),
    }
    fixture.recipe.write_text(replacements[change])
    before = inventory(fixture.root)
    with pytest.raises(OrganizeError):
        load_organize_recipe(fixture.recipe)
    assert inventory(fixture.root) == before


@pytest.mark.parametrize(
    "change",
    [
        "duplicate-pair",
        "missing-region",
        "invalid-date",
        "date-key-mismatch",
        "unsafe-key",
        "missing-image",
        "unknown-delivery",
        "unknown-column",
        "missing-column",
        "dangling-alias",
        "alias-role",
        "duplicate-asset",
        "dangling-asset",
        "primary-collision",
        "control-collision",
        "file-directory-collision",
        "case-collision",
        "bad-hash",
        "missing-zip-member",
    ],
)
def test_malformed_catalogs_fail_before_output(tmp_path: Path, change: str):
    fixture = make_fixture(tmp_path / "input")
    membership = read_csv(fixture.catalog / "membership.csv")
    aliases = read_csv(fixture.catalog / "aliases.csv")
    assets = read_csv(fixture.catalog / "assets.csv")
    row = membership[0]
    if change == "duplicate-pair":
        membership += [dict(row)]
    elif change == "missing-region":
        row["region_code"] = "absent"
    elif change == "invalid-date":
        row["acquisition_date"] = "2023-02-30"
    elif change == "date-key-mismatch":
        row["acquisition_date"] = "2023-03-05"
    elif change == "unsafe-key":
        row["source_key"] = "20230304_../escape"
    elif change == "missing-image":
        row["image_member"] = ""
    elif change == "unknown-delivery":
        row["image_delivery_id"] = "absent"
    elif change == "unknown-column":
        row["unknown"] = "x"
    elif change == "dangling-alias":
        aliases[0]["source_id"] = "missing"
    elif change == "alias-role":
        aliases[0]["role"] = "bogus"
    elif change == "duplicate-asset":
        assets += [dict(assets[0])]
    elif change == "dangling-asset":
        assets[0]["source_id"] = "missing"
    elif change == "primary-collision":
        assets[0]["destination"] = f"images/{fixture.source_id}.tif"
    elif change == "control-collision":
        assets[0]["destination"] = "manifest.json"
    elif change == "file-directory-collision":
        assets[0]["destination"] = f"images/{fixture.source_id}.tif/aux.xml"
    elif change == "case-collision":
        assets[0]["destination"] = assets[1]["destination"].upper()
    elif change == "bad-hash":
        row["image_sha256"] = "not-sha256"
    elif change == "missing-zip-member":
        row["image_member"] = "missing.tif"
    fields = tuple(MEMBERSHIP_FIELDS)
    if change == "unknown-column":
        fields += ("unknown",)
    if change == "missing-column":
        fields = tuple(field for field in fields if field != "label_member")
        for value in membership:
            value.pop("label_member")
    write_csv(fixture.catalog / "membership.csv", fields, membership)
    write_csv(fixture.catalog / "aliases.csv", ALIAS_FIELDS, aliases)
    write_csv(fixture.catalog / "assets.csv", ASSET_FIELDS, assets)
    before = inventory(fixture.root)
    with pytest.raises(OrganizeError):
        fixture.plan()
    assert inventory(fixture.root) == before
    assert not (fixture.root / "data").exists()


@pytest.mark.parametrize(
    "member",
    [
        "../escape",
        "/absolute",
        "C:/drive",
        "folder/../escape",
        "folder\\escape",
        "folder//escape",
    ],
)
def test_unsafe_archive_spelling_is_rejected(tmp_path: Path, member: str):
    fixture = make_fixture(tmp_path / "input")
    with zipfile.ZipFile(fixture.root / "delivery.zip", "a") as archive:
        archive.writestr(member, b"unselected malicious payload")
    with pytest.raises(OrganizeError):
        fixture.plan()
    assert not (fixture.root / "data").exists()


@pytest.mark.parametrize("kind", ["duplicate", "symlink"])
def test_ambiguous_or_symlink_archive_entries_rejected(tmp_path: Path, kind: str):
    fixture = make_fixture(tmp_path / "input")
    with zipfile.ZipFile(fixture.root / "delivery.zip", "a") as archive:
        if kind == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate"):
                archive.writestr("strange/original-image.TIF", b"duplicate")
        else:
            info = zipfile.ZipInfo("linked")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "elsewhere")
    with pytest.raises(OrganizeError):
        fixture.plan()


def test_directory_hash_catalog_is_identity_and_symlinks_are_forbidden(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input", kind="directory")
    catalog = fixture.catalog / "file_catalog.csv"
    original = catalog.read_bytes()
    catalog.write_bytes(original + b"\n")
    with pytest.raises(OrganizeError):
        fixture.plan()
    catalog.write_bytes(original)
    image = fixture.root / "delivery/strange/original-image.TIF"
    image.unlink()
    image.symlink_to(fixture.root / "delivery/different/annotated.tiff")
    with pytest.raises(OrganizeError):
        fixture.plan()


def test_input_output_overlap_is_rejected(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input", kind="directory")
    rows = read_csv(fixture.catalog / "deliveries.csv")
    rows[0]["path"] = "."
    write_csv(fixture.catalog / "deliveries.csv", DELIVERY_FIELDS, rows)
    with pytest.raises(OrganizeError):
        fixture.plan()


def test_cli_dry_run_reports_scope_without_writing(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input")
    before = inventory(fixture.root)
    result = CliRunner().invoke(
        app,
        [
            "organize",
            "--recipe",
            str(fixture.recipe),
            "--paths",
            str(fixture.settings),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert fixture.dataset_id in result.stdout
    assert str(fixture.root / "data/2_organized/island/v1") in result.stdout
    assert inventory(fixture.root) == before
    assert not (fixture.root / "data").exists()


def test_cli_catalog_failure_is_readable_without_traceback(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input")
    (fixture.catalog / "membership.csv").unlink()
    result = CliRunner().invoke(
        app,
        [
            "organize",
            "--recipe",
            str(fixture.recipe),
            "--paths",
            str(fixture.settings),
            "--dry-run",
        ],
    )
    assert result.exit_code != 0
    assert "Error:" in result.stderr
    assert "Traceback" not in result.output


def test_catalog_completion_authenticates_the_parsed_tables(tmp_path: Path):
    import json

    fixture = make_fixture(tmp_path / "input", multiple=True)
    documents = {
        name: (fixture.catalog / f"{name}.csv").read_bytes()
        for name in ("deliveries", "membership", "aliases", "assets")
    }
    provenance = {
        "schema_version": 1,
        "producer": "independent-fixture:v1",
        "tables": {f"{name}.csv": digest(data) for name, data in documents.items()},
    }
    manifest = fixture.catalog / "catalog_manifest.json"
    manifest.write_text(json.dumps(provenance))
    plan = fixture.plan()
    rows = read_csv(fixture.catalog / "membership.csv")
    write_csv(
        fixture.catalog / "membership.csv", MEMBERSHIP_FIELDS, list(reversed(rows))
    )
    with pytest.raises(OrganizeError, match="provenance"):
        fixture.plan()
    # A newly authenticated row ordering preserves logical plan identity.
    provenance["tables"]["membership.csv"] = digest(
        (fixture.catalog / "membership.csv").read_bytes()
    )
    manifest.write_text(json.dumps(provenance))
    assert fixture.plan().plan_hash == plan.plan_hash


def test_directory_catalog_hash_and_parse_share_one_snapshot(
    tmp_path: Path, monkeypatch
):
    fixture = make_fixture(tmp_path / "input", kind="directory")
    catalog = fixture.catalog / "file_catalog.csv"
    read = Path.read_bytes
    calls = 0

    def concurrently_changed(path):
        nonlocal calls
        if path == catalog:
            calls += 1
            if calls > 1:
                return b"untrusted replacement after initial identity check"
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", concurrently_changed)
    plan = fixture.plan()
    assert plan.files
    assert calls == 1


def test_dry_run_never_reads_member_payloads_or_hashes_archives(
    tmp_path: Path, monkeypatch
):
    import kelpseg.prepare.organize as engine

    fixture = make_fixture(tmp_path / "input")
    before = inventory(fixture.root)

    def forbidden(*args, **kwargs):
        raise AssertionError("dry-run must not read/hash raster or archive payloads")

    monkeypatch.setattr(zipfile.ZipFile, "open", forbidden)
    monkeypatch.setattr(engine, "_hash", forbidden)
    result = CliRunner().invoke(
        app,
        [
            "organize",
            "--recipe",
            str(fixture.recipe),
            "--paths",
            str(fixture.settings),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert inventory(fixture.root) == before


@pytest.mark.parametrize(
    "state", ["unknown-directory", "wrong-completed", "wrong-staging"]
)
def test_plan_rejects_known_output_conflicts_without_writing(tmp_path: Path, state):
    import json

    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    output = plan.destination
    if state == "wrong-staging":
        output = output.with_name(f".{output.name}.incomplete")
    output.mkdir(parents=True)
    if state != "unknown-directory":
        record = "state.json" if state == "wrong-staging" else "manifest.json"
        (output / record).write_text(json.dumps({"plan_hash": "different"}))
    before = inventory(fixture.root)
    with pytest.raises(OrganizeError, match="Conflicting output"):
        fixture.plan()
    assert inventory(fixture.root) == before


@pytest.mark.parametrize("incomplete", [False, True])
def test_existing_output_is_refused_even_with_a_matching_plan_identity(
    tmp_path, monkeypatch, incomplete
):
    import json

    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    output = plan.destination
    if incomplete:
        output = output.with_name(f".{output.name}.incomplete")
    output.mkdir(parents=True)
    record = output / ("state.json" if incomplete else "manifest.json")
    record.write_text(
        json.dumps(
            {"schema_version": 1, "status": "complete", "plan_hash": plan.plan_hash}
        )
    )
    before = inventory(fixture.root)

    def forbidden(*args, **kwargs):
        pytest.fail("existing output should be refused before catalog reads")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    with pytest.raises(OrganizeError, match="fresh release"):
        fixture.plan()
    monkeypatch.undo()
    assert inventory(fixture.root) == before
