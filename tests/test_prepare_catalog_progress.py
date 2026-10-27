"""Preparation reports useful progress without changing data identities."""

import logging
from pathlib import Path

import pytest
from organize_fixtures import inventory, make_fixture

from kelpseg.prepare.legacy_catalog import build_legacy_ca_bc_catalog
from kelpseg.prepare.organize_inputs import OrganizeError


@pytest.mark.parametrize("kind", ["zip", "directory"])
def test_plan_logs_inputs_counts_and_destination_without_writing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, kind: str
):
    fixture = make_fixture(tmp_path / "input", kind=kind)
    original = fixture.plan()
    before = inventory(fixture.root)
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        plan = fixture.plan()
    messages = caplog.text
    assert str(fixture.recipe) in messages
    assert str(fixture.catalog / "membership.csv") in messages
    assert "Checking delivery 1/1" in messages
    assert f"{len(plan.files)} files" in messages
    assert f"{sum(item.bytes for item in plan.files)} bytes" in messages
    assert str(plan.destination) in messages
    assert plan.plan_hash == original.plan_hash
    assert inventory(fixture.root) == before


# Reuse the existing synthetic historical-catalog fixture.
pytest_plugins = ("test_legacy_catalog",)


def test_catalog_logs_evidence_mapping_and_one_pass_publication(
    historical_metadata, caplog: pytest.LogCaptureFixture
):
    paths, regions, destination = historical_metadata
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        build_legacy_ca_bc_catalog(paths, regions, destination)
    assert "Reading evidence 1/" in caplog.text
    assert "Mapped 369 source pairs" in caplog.text
    assert "Mapped 418 masks and sidecars" in caplog.text
    assert "Checking trusted archive identity and stability: ca_data.zip" in caplog.text
    assert f"Metadata catalog complete: {destination}" in caplog.text
    caplog.clear()
    with (
        caplog.at_level(logging.INFO, logger="kelpseg.prepare"),
        pytest.raises(OrganizeError, match="fresh destination"),
    ):
        build_legacy_ca_bc_catalog(paths, regions, destination)
    assert "Reading evidence" not in caplog.text
    assert "Writing metadata file" not in caplog.text
