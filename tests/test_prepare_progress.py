"""Researchers can see preparation progress without changing library behavior."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from organize_fixtures import inventory, make_fixture
from typer.testing import CliRunner

import kelpseg.prepare.organize as engine
from kelpseg.cli import app


def test_cli_copy_shows_default_progress_and_restores_logging(tmp_path: Path):
    fixture = make_fixture(tmp_path / "input")
    logger = logging.getLogger("kelpseg.prepare")
    original = logger.level, logger.propagate, tuple(logger.handlers)
    result = CliRunner().invoke(
        app,
        [
            "organize",
            "--recipe",
            str(fixture.recipe),
            "--paths",
            str(fixture.settings),
        ],
    )
    assert result.exit_code == 0, result.output
    progress = result.stderr.lower()
    assert "copy" in progress
    assert "verif" in progress
    assert "published" in progress
    assert "[1/" in progress
    assert fixture.source_id in progress
    assert "Complete verified release:" in result.stdout
    assert (logger.level, logger.propagate, tuple(logger.handlers)) == original


def test_library_progress_has_file_counts_and_never_prints_directly(
    tmp_path: Path, caplog, capsys
):
    fixture = make_fixture(tmp_path / "input")
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        plan = fixture.plan()
        release = engine.organize_dataset(plan)
    messages = caplog.text.lower()
    assert "copy" in messages
    assert "verif" in messages
    assert "published" in messages
    assert f"[1/{len(plan.files)}]" in messages
    assert f"[{len(plan.files)}/{len(plan.files)}]" in messages
    assert str(release).lower() in messages
    for item in plan.files:
        assert item.destination in messages
    assert capsys.readouterr() == ("", "")

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        engine.verify_organized_release(release, plan)
    assert "verif" in caplog.text.lower()
    assert str(release) in caplog.text
    assert capsys.readouterr() == ("", "")


def test_resume_logs_completed_file_checks_and_reuse(
    tmp_path: Path, monkeypatch, caplog
):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    atomic_json = engine._atomic_json

    def stop_after_receipt(path, value):
        atomic_json(path, value)
        if path.parent.name == "receipts":
            raise KeyboardInterrupt("controlled interruption after verified file")

    with monkeypatch.context() as patch:
        patch.setattr(engine, "_atomic_json", stop_after_receipt)
        with pytest.raises(KeyboardInterrupt):
            engine.organize_dataset(plan)
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        release = engine.organize_dataset(fixture.plan(), resume=True)
    progress = caplog.text.lower()
    assert "staged" in progress
    assert "reus" in progress
    assert plan.files[0].destination in progress
    assert "published" in progress
    engine.verify_organized_release(release, plan)


def test_completed_repeat_logs_verification_without_rewriting(tmp_path: Path, caplog):
    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    release = engine.organize_dataset(plan)
    before = inventory(release)
    mtimes = {p: p.stat().st_mtime_ns for p in release.rglob("*") if p.is_file()}
    caplog.clear()
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        assert engine.organize_dataset(plan, resume=True) == release
    progress = caplog.text.lower()
    assert "already exists" in progress
    assert "verif" in progress
    assert "copying" not in progress
    assert inventory(release) == before
    assert all(path.stat().st_mtime_ns == value for path, value in mtimes.items())


def test_cli_dry_run_logs_input_checks_without_copying(tmp_path: Path, monkeypatch):
    fixture = make_fixture(tmp_path / "input")
    before = inventory(fixture.root)

    def unexpected_copy(*args, **kwargs):
        pytest.fail("Dry run tried to copy payload bytes")

    monkeypatch.setattr(engine, "_copy_payload", unexpected_copy)
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
    assert "catalog" in result.stderr.lower()
    assert "delivery" in result.stderr.lower()
    assert "Dry run valid" in result.stdout
    assert inventory(fixture.root) == before


def test_long_verification_reports_bytes_without_changing_hash(
    tmp_path: Path, monkeypatch, caplog
):
    import hashlib
    from types import SimpleNamespace

    payload = b"x" * (2 * 1024 * 1024)
    path = tmp_path / "large-enough-for-two-chunks.bin"
    path.write_bytes(payload)
    ticks = iter([0.0, 11.0, 22.0])
    monkeypatch.setattr(engine, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        digest, size = engine._hash(path)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert size == len(payload)
    progress = caplog.text.lower()
    assert "still verifying" in progress
    assert path.name in progress
    assert "2.0 mib" in progress


def test_long_copy_reports_bytes_and_still_verifies_output(
    tmp_path: Path, monkeypatch, caplog
):
    import itertools
    from types import SimpleNamespace

    fixture = make_fixture(tmp_path / "input")
    plan = fixture.plan()
    item = plan.files[0]
    temporary = tmp_path / "copied.part"
    ticks = itertools.count(start=0, step=11)
    monkeypatch.setattr(engine, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        receipt = engine._copy_payload(plan, item, temporary)
    assert temporary.read_bytes() == fixture.payloads[item.member_relative_path]
    assert receipt["destination"] == item.destination
    assert receipt["bytes"] == item.bytes
    progress = caplog.text.lower()
    assert "still copying" in progress
    assert "independently verifying copied bytes" in progress
    assert item.destination in progress
