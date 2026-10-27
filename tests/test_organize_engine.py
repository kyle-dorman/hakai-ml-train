"""Release provenance must agree with declared inputs and verified payloads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from organize_fixtures import digest, make_fixture, read_csv, write_csv

from kelpseg.prepare.organize import organize_dataset, verify_organized_release
from kelpseg.prepare.organize_inputs import OrganizeError


@pytest.mark.parametrize(
    "table,field,replacement",
    [
        ("sources.csv", "image_path", "images/other.tif"),
        ("sources.csv", "label_member", "other-original-label.tif"),
        ("sources.csv", "image_delivery_id", "other-delivery"),
        ("sources.csv", "label_delivery_sha256", "0" * 64),
        ("sources.csv", "image_sha256", "0" * 64),
        ("sources.csv", "label_bytes", "1"),
        ("sources.csv", "image_header_json", "{}"),
        ("assets.csv", "parent_role", "pair"),
        ("assets.csv", "member_relative_path", "another-sidecar.xml"),
        ("assets.csv", "source_id", "other-owner"),
        ("assets.csv", "sha256", "0" * 64),
        ("assets.csv", "bytes", "1"),
        ("assets.csv", "delivery_sha256", "0" * 64),
        ("filename_aliases.csv", "alias", "invented-alias"),
        ("regions.csv", "region_name", "wrong-region"),
        ("recipe.json", "dataset_id", "different-dataset"),
    ],
)
def test_verifier_checks_provenance_after_manifest_is_recomputed(
    tmp_path: Path, table: str, field: str, replacement: str
):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    release = organize_dataset(plan)
    changed = release / table
    if table.endswith(".csv"):
        rows = read_csv(changed)
        assert rows[0][field] != replacement
        rows[0][field] = replacement
        write_csv(changed, tuple(rows[0]), rows)
    else:
        value = json.loads(changed.read_text())
        value[field] = replacement
        changed.write_text(json.dumps(value))
    manifest_path = release / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    contents = changed.read_bytes()
    manifest["files"][table] = {"sha256": digest(contents), "bytes": len(contents)}
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(OrganizeError, match="[Pp]rovenance|[Rr]ecipe"):
        verify_organized_release(release, plan)
