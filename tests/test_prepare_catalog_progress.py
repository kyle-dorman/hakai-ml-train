"""Preparation reports useful progress without changing data identities."""

import logging
from pathlib import Path

import pytest
from organize_fixtures import inventory, make_fixture


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
