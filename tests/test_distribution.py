"""Prove both distribution paths install without checkout-only dependencies."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

from organize_fixtures import make_fixture


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
            assert "kelpseg/bands.py" in names
            assert "kelpseg/chips.py" in names
            for module in (
                "organize",
                "organize_inputs",
                "legacy_catalog",
                "check",
                "clean_inputs",
                "clean",
                "nodata",
                "alignment",
                "chip_inputs",
                "chip",
            ):
                assert f"kelpseg/prepare/{module}.py" in names
                assert f"kelpseg/{module}.py" not in names
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
            "for name in ('src', 'scripts', 'torch', 'torchgeo', "
            "'wandb')}}))",
            cwd=unrelated,
        )
        identity = json.loads(probe)
        assert Path(identity["file"]).is_relative_to(environment)
        assert identity["version"] == version
        assert not any(identity["legacy"].values()), identity
        assert "check-paths" in run(command, "--help", cwd=unrelated)
        assert version in run(command, "--version", cwd=unrelated)
        assert version in run(python, "-I", "-m", "kelpseg", "--version", cwd=unrelated)

        lazy_probe = """
import importlib.abc
import runpy
import sys

class BlockHeavyImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"numpy", "rasterio", "torch", "wandb"}:
            raise AssertionError("Unexpected eager import: " + fullname)

sys.meta_path.insert(0, BlockHeavyImports())
sys.argv = ["kelpseg", *sys.argv[1:]]
runpy.run_module("kelpseg", run_name="__main__")
"""
        for arguments in (
            ("--help",),
            ("--version",),
            ("organize", "--help"),
            ("check", "--help"),
            ("clean", "--help"),
            ("chip", "--help"),
        ):
            run(python, "-I", "-c", lazy_probe, *arguments, cwd=unrelated)

        (unrelated / "data with spaces").mkdir()
        (unrelated / "runs").mkdir()
        settings = unrelated / "settings.toml"
        settings.write_text(
            '[paths]\ndata_root = "data with spaces"\nruns_root = "runs"\n'
        )
        output = run(command, "check-paths", "--paths", settings, cwd=tmp_path)
        assert str((unrelated / "data with spaces").resolve()) in output
        assert str((unrelated / "runs").resolve()) in output

        sample = make_fixture(
            unrelated / "organizer sample", dataset_id="external_only"
        )
        arguments = ("organize", "--recipe", sample.recipe, "--paths", sample.settings)
        dry_run = run(command, *arguments, "--dry-run", cwd=tmp_path)
        assert "external_only" in dry_run
        assert not (sample.root / "data").exists()
        output = run(command, *arguments, cwd=tmp_path)
        release = sample.root / "data/2_organized/external_only/v1"
        assert str(release) in output
        assert (release / "manifest.json").is_file()
        for role, member in (
            ("images", "strange/original-image.TIF"),
            ("labels", "different/annotated.tiff"),
        ):
            assert (
                release / role / f"{sample.source_id}.tif"
            ).read_bytes() == sample.payloads[member]
        assert "--resume" not in run(command, "organize", "--help", cwd=unrelated)
        library = run(
            python,
            "-I",
            "-c",
            "import json, sys; from pathlib import Path; "
            "from kelpseg.prepare.organize import verify_organized_release; "
            "result = verify_organized_release(Path(sys.argv[1])); "
            "assert not any(name in sys.modules for name in ('src', 'scripts', 'torch', 'wandb')); "
            "print(json.dumps({'plan_hash': result.plan_hash, 'files': result.file_count}))",
            release,
            cwd=tmp_path,
        )
        result = json.loads(library)
        assert len(result["plan_hash"]) == 64
        assert result["files"] > 5

        # An unrelated directory needs neither a CA/BC name nor an organizer catalog.
        images, labels, source_recipe, cleaned_recipe, clean_recipe = (
            _directory_fixture(unrelated / "other coast")
        )
        directory_arguments = (
            "check",
            "--images",
            images,
            "--labels",
            labels,
            "--recipe",
            source_recipe,
        )
        original_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for root in (images, labels)
            for path in root.rglob("*.tif")
        }
        quick_report = unrelated / "source-quick.json"
        run(command, *directory_arguments, "--report", quick_report, cwd=unrelated)
        quick = json.loads(quick_report.read_text())
        assert quick["level"] == "quick" and quick["passed"]
        assert quick["scanned_image_pixels"] == quick["scanned_label_pixels"] == 0
        source_report = unrelated / "source-full.json"
        run(
            command,
            *directory_arguments,
            "--full",
            "--report",
            source_report,
            cwd=unrelated,
        )
        full = json.loads(source_report.read_text())
        assert full["level"] == "full" and full["passed"]
        assert full["scanned_image_pixels"] == full["scanned_label_pixels"] == 20
        cleaned = unrelated / "paired cleaned"
        clean_arguments = (
            "clean",
            "--images",
            images,
            "--labels",
            labels,
            "--recipe",
            clean_recipe,
            "--output",
            cleaned,
        )
        run(command, *clean_arguments, "--dry-run", cwd=unrelated)
        assert not cleaned.exists()
        run(command, *clean_arguments, cwd=unrelated)
        assert (cleaned / "manifest.json").is_file()
        assert "--resume" not in run(command, "clean", "--help", cwd=unrelated)
        run(
            command,
            "check",
            "--images",
            cleaned / "images",
            "--labels",
            cleaned / "labels",
            "--recipe",
            cleaned_recipe,
            "--full",
            cwd=unrelated,
        )

        image_only = unrelated / "image only cleaned"
        run(
            command,
            "clean",
            "--images",
            images,
            "--recipe",
            clean_recipe,
            "--output",
            image_only,
            cwd=unrelated,
        )
        assert not (image_only / "labels").exists()
        run(
            command,
            "check",
            "--images",
            image_only / "images",
            "--recipe",
            cleaned_recipe,
            "--full",
            cwd=unrelated,
        )
        run(
            python,
            "-I",
            "-c",
            "import sys, numpy as np, rasterio; from pathlib import Path; "
            "p=Path(sys.argv[1]); "
            "a=rasterio.open(p/'images/coast-scene.tif'); "
            "b=rasterio.open(p/'labels/coast-scene.tif'); "
            "x=a.read(); y=b.read(1); "
            "assert a.nodata==0 and b.nodata==3; "
            "assert np.all(x[:,0,0]==0) and y[0,0]==3; "
            "assert x[0,1,1]==0 and np.all(x[1:,1,1]==17); "
            "assert y[1,1]==0 and y[2,2]==1 and y[3,3]==3; "
            "assert np.all(x[:,3,3]==17); "
            "assert not any(n in sys.modules for n in ('src','scripts','torch','wandb'))",
            cleaned,
            cwd=unrelated,
        )
        assert {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in original_hashes
        } == original_hashes

        chip_recipe = unrelated / "chip.toml"
        chip_recipe.write_text(
            'source_band_names = ["red", "green", "blue"]\n'
            "chip_size = 3\nstride = 2\n[label_mapping]\n0 = 0\n1 = 1\n3 = -100\n"
        )
        chips = unrelated / "chips"
        chip_arguments = (
            "chip",
            "--images",
            cleaned / "images",
            "--labels",
            cleaned / "labels",
            "--output",
            chips,
            "--recipe",
            chip_recipe,
        )
        assert "candidate windows: 4" in run(
            command, *chip_arguments, "--dry-run", cwd=unrelated
        )
        assert not chips.exists()
        run(command, *chip_arguments, cwd=unrelated)
        run(
            python,
            "-I",
            "-c",
            "import csv, json, sys; from pathlib import Path; "
            "from kelpseg.chips import load_chip; "
            "p=Path(sys.argv[1]); "
            "assert json.loads((p/'summary.json').read_text())['retained']==4; "
            "rows=list(csv.DictReader((p/'windows.csv').open())); "
            "x=load_chip(p/rows[-1]['payload'], ['red','green','blue'], 'rgb', 3); "
            "assert x['image'].shape==(3,3,3) and x['padding']==(0,1,0,0); "
            "assert (x['label'][2,:]==-100).all(); "
            "assert not any(n in sys.modules for n in ('src','scripts','torch','wandb'))",
            chips,
            cwd=unrelated,
        )


def _directory_fixture(root: Path) -> tuple[Path, Path, Path, Path, Path]:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin

    images, labels = root / "images", root / "labels"
    images.mkdir(parents=True)
    labels.mkdir()
    image = np.full((3, 4, 5), 17, dtype="uint16")
    image[:, 0, 0] = 65535
    image[0, 1, 1] = 0
    label = np.zeros((1, 4, 5), dtype="uint8")
    label[0, 0, 0] = label[0, 3, 3] = 3
    label[0, 2, 2] = 1
    grid = dict(
        driver="GTiff",
        width=5,
        height=4,
        crs="EPSG:32610",
        transform=from_origin(100, 200, 3, 3),
    )
    for directory, values, nodata in ((images, image, 65535), (labels, label, 3)):
        with rasterio.open(
            directory / "coast-scene.tif",
            "w",
            **grid,
            dtype=values.dtype,
            count=values.shape[0],
            nodata=nodata,
        ) as output:
            output.write(values)
    expectations = (
        "schema_version = 1\nimage_band_counts = [3]\n"
        'image_dtypes = ["uint16"]\nlabel_values = [0, 1, 3]\n'
        "block_size = 512\n"
    )
    source_recipe, cleaned_recipe, clean_recipe = (
        root / "source.toml",
        root / "cleaned.toml",
        root / "clean.toml",
    )
    source_recipe.write_text(expectations + 'profile = "source"\n')
    cleaned_recipe.write_text(expectations + 'profile = "cleaned"\n')
    clean_recipe.write_text(
        expectations + 'qa_masks = false\ncompression = "deflate"\n'
    )
    return images, labels, source_recipe, cleaned_recipe, clean_recipe
