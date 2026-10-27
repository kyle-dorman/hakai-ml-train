"""Prove both distribution paths install without checkout-only dependencies."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path


def test_wheel_and_sdist_install_outside_checkout(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    uv = shutil.which("uv")
    assert uv is not None, "Install uv before running the distribution check."
    env = os.environ.copy()
    for name in ("PYTHONPATH", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"):
        env.pop(name, None)
    env.update(UV_OFFLINE="1", UV_PYTHON_DOWNLOADS="never", NO_COLOR="1")

    def run(*args: str | Path, cwd: Path = repo) -> str:
        result = subprocess.run(
            [str(arg) for arg in args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    distributions = tmp_path / "distributions"
    run(
        uv,
        "build",
        "--python",
        sys.executable,
        "--no-sources",
        "--out-dir",
        distributions,
    )
    sdist = next(distributions.glob("*.tar.gz"))
    checkout_wheel = next(distributions.glob("*.whl"))
    rebuilt = tmp_path / "rebuilt"
    # Use the frozen dev backend so the sdist check needs no registry access.
    run(
        uv,
        "build",
        sdist,
        "--python",
        sys.executable,
        "--no-build-isolation",
        "--wheel",
        "--out-dir",
        rebuilt,
        cwd=tmp_path,
    )
    sdist_wheel = next(rebuilt.glob("*.whl"))

    requirements = tmp_path / "runtime.txt"
    run(
        uv,
        "export",
        "--frozen",
        "--no-default-groups",
        "--no-emit-project",
        "--output-file",
        requirements,
    )
    version = tomllib.loads((repo / "pyproject.toml").read_text())["project"]["version"]
    for index, wheel in enumerate((checkout_wheel, sdist_wheel)):
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            assert "kelpseg/cli/__init__.py" in names
            assert "kelpseg/paths.py" in names
            assert all(
                name.startswith(("kelpseg/", f"kelpseg-{version}.dist-info/"))
                for name in names
            ), names

        environment = tmp_path / f"installed-{index}"
        run(uv, "venv", "--python", sys.executable, environment)
        python = environment / "bin" / "python"
        command = environment / "bin" / "kelpseg"
        run(
            uv,
            "pip",
            "sync",
            "--python",
            python,
            "--require-hashes",
            requirements,
        )
        run(uv, "pip", "install", "--python", python, "--no-deps", wheel)
        run(uv, "pip", "check", "--python", python)

        unrelated = tmp_path / f"unrelated-{index}"
        unrelated.mkdir()
        probe = run(
            python,
            "-I",
            "-c",
            "import importlib.metadata, importlib.util, json, kelpseg; "
            "print(json.dumps({'file': kelpseg.__file__, "
            "'version': importlib.metadata.version('kelpseg'), "
            "'legacy': {name: importlib.util.find_spec(name) is not None "
            "for name in ('src', 'scripts', 'torch', 'torchgeo', 'rasterio', "
            "'wandb', 'numpy')}}))",
            cwd=unrelated,
        )
        identity = json.loads(probe)
        assert Path(identity["file"]).is_relative_to(environment)
        assert identity["version"] == version
        assert not any(identity["legacy"].values()), identity
        assert "check-paths" in run(command, "--help", cwd=unrelated)
        assert version in run(command, "--version", cwd=unrelated)
        assert version in run(python, "-I", "-m", "kelpseg", "--version", cwd=unrelated)

        (unrelated / "data with spaces").mkdir()
        (unrelated / "runs").mkdir()
        settings = unrelated / "settings.toml"
        settings.write_text(
            '[paths]\ndata_root = "data with spaces"\nruns_root = "runs"\n'
        )
        output = run(command, "check-paths", "--paths", settings, cwd=tmp_path)
        assert str((unrelated / "data with spaces").resolve()) in output
        assert str((unrelated / "runs").resolve()) in output
