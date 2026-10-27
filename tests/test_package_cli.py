import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kelpseg.cli import app

runner = CliRunner()


def test_help_keeps_explicit_subcommand_and_no_future_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "check-paths" in result.stdout
    assert "organize" in result.stdout
    assert "train" not in result.stdout
    assert "--version" in result.stdout
    result = runner.invoke(app, ["check-paths", "--help"])
    assert result.exit_code == 0
    assert "--paths" in result.stdout


def test_version_uses_installed_distribution() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == f"kelpseg {version('kelpseg')}"


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["train"], "No such command"),
        (["--unknown"], "No such option"),
        (["check-paths"], "Missing option"),
        (["check-paths", "--unknown"], "No such option"),
    ],
)
def test_usage_errors_are_stderr_without_traceback(arguments, message) -> None:
    result = runner.invoke(app, arguments)
    assert result.exit_code != 0
    assert message in result.stderr
    assert "Traceback" not in result.output


def test_successful_check_reports_resolved_paths_without_writes(tmp_path: Path) -> None:
    data = tmp_path / "data with spaces"
    runs = data / "runs"
    runs.mkdir(parents=True)
    config = tmp_path / "paths.local.toml"
    config.write_text(
        '[paths]\ndata_root = "data with spaces"\nruns_root = "data with spaces/runs"\n'
    )
    before = sorted(tmp_path.rglob("*"))
    result = runner.invoke(app, ["check-paths", "--paths", str(config)])
    assert result.exit_code == 0
    assert str(config) in result.stdout
    assert str(data) in result.stdout
    assert str(runs) in result.stdout
    assert result.stderr == ""
    assert sorted(tmp_path.rglob("*")) == before


@pytest.mark.parametrize(
    "kind", ["missing", "directory", "invalid-utf8", "bad-root", "malformed", "unknown"]
)
def test_settings_errors_are_actionable_stderr(tmp_path: Path, kind: str) -> None:
    config = tmp_path / "paths.local.toml"
    if kind == "directory":
        config.mkdir()
    elif kind == "invalid-utf8":
        config.write_bytes(b"\xff")
    elif kind == "bad-root":
        config.write_text('[paths]\ndata_root = "absent"\nruns_root = "absent"\n')
    elif kind == "malformed":
        config.write_text("[paths")
    elif kind == "unknown":
        config.write_text('[paths]\ntypo_root = "absent"\n')
    before = sorted(tmp_path.rglob("*"))
    result = runner.invoke(app, ["check-paths", "--paths", str(config)])
    assert result.exit_code == 1
    assert str(config) in result.stderr
    assert "Error:" in result.stderr
    assert result.stdout == ""
    assert "Traceback" not in result.output
    assert sorted(tmp_path.rglob("*")) == before


def test_unreadable_settings_is_expected_cli_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "paths.local.toml"
    config.write_text("[paths]\n")

    def unreadable(*args, **kwargs):
        raise PermissionError("fixture denies reading")

    monkeypatch.setattr(Path, "read_text", unreadable)
    result = runner.invoke(app, ["check-paths", "--paths", str(config)])
    assert result.exit_code == 1
    assert "readable TOML file" in result.stderr
    assert "Traceback" not in result.output


def test_required_paths_never_discovers_a_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "paths.local.toml").write_text("[paths]\n")
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.chdir(child)
    result = runner.invoke(app, ["check-paths"])
    assert result.exit_code != 0
    assert "Missing option" in result.stderr


@pytest.mark.parametrize("argument", ["--help", "--version", "check-paths", "organize"])
def test_module_entry_is_lightweight_in_real_process(
    tmp_path: Path, argument: str
) -> None:
    # A fresh process has no already-imported ML modules to hide eager imports.
    code = """
import importlib.abc
import runpy
import sys

class BlockHeavyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {
            'numpy', 'torch', 'torchvision', 'torchgeo', 'rasterio',
            'lightning', 'wandb', 'transformers', 'huggingface_hub',
        }:
            raise AssertionError('Unexpected heavy import: ' + fullname)

sys.meta_path.insert(0, BlockHeavyImports())
sys.argv = ['kelpseg', *sys.argv[1:]]
runpy.run_module('kelpseg', run_name='__main__')
"""
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    arguments = [argument]
    if argument == "organize":
        arguments += ["--help"]
    if argument == "check-paths":
        roots = tmp_path / "roots"
        roots.mkdir()
        config = tmp_path / "paths.local.toml"
        config.write_text('[paths]\ndata_root = "roots"\nruns_root = "roots"\n')
        arguments += ["--paths", str(config)]
    result = subprocess.run(
        [sys.executable, "-c", code, *arguments],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    if argument == "--help":
        assert "check-paths" in result.stdout
    elif argument == "--version":
        assert result.stdout.strip() == f"kelpseg {version('kelpseg')}"
    elif argument == "organize":
        assert "--recipe" in result.stdout
    else:
        assert "Both roots are existing directories." in result.stdout
