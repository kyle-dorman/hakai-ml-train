"""Native Trainer integration, metadata-only previews and held-out isolation."""

import csv
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

from kelpseg.paths import PathSettings
from kelpseg.training import run
from kelpseg.training.module import TrainingModule
from kelpseg.training.settings import load_settings


def _inputs(tmp_path):
    chips = tmp_path / "chips"
    chips.mkdir()
    sources, windows, assignments = [], [], []
    for index, split in enumerate(("train", "train", "train", "val", "val", "test")):
        source = dict(
            source_key=str(index),
            source_id=str(index),
            original_tiff=f"{index}.tif",
            dataset_id="fixture",
            release_id="v1",
            region="001",
            acquisition_date=f"2021-01-{index + 1:02d}",
            satellite_id="fixture",
            row_offset=0,
            col_offset=0,
            height=32,
            width=32,
        )
        sources.append(source)
        windows.append(
            dict(
                source_key=str(index),
                row=0,
                col=0,
                original_row=0,
                original_col=0,
                height=32,
                width=32,
                kelp_pixels=1024 if index < 4 else 0,
                disposition="retained",
                payload=f"{index}.npz",
            )
        )
        assignments.append(
            dict(
                source,
                experiment="baseline",
                variant="augmented",
                split=split,
                reason="fixture",
            )
        )
        if split != "test":
            np.savez(
                chips / f"{index}.npz",
                image=np.full((32, 32, 8), 1000, dtype=np.uint16),
                label=np.full((32, 32), int(index < 4), dtype=np.int8),
            )
    (chips / "sources.json").write_text(json.dumps(sources))
    from kelpseg.preprocessing import BAND_NAMES

    (chips / "recipe.json").write_text(
        json.dumps(dict(source_band_names=BAND_NAMES, chip_size=512))
    )
    for path, rows in (
        (chips / "windows.csv", windows),
        (tmp_path / "assignments.csv", assignments),
    ):
        with path.open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)
    paths = PathSettings(tmp_path / "paths.toml", tmp_path, tmp_path / "runs")
    paths.runs_root.mkdir()
    settings = replace(
        load_settings("configs/train/tiny_cpu.toml"),
        chips="chips",
        assignments="assignments.csv",
        limit_train_batches=3,
        limit_val_batches=2,
    )
    return settings, paths


def test_preview_budget_no_arrays_no_outputs_and_initial_collision(
    tmp_path, monkeypatch
):
    settings, paths = _inputs(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Preview must not open arrays or construct a model")

    monkeypatch.setattr(np, "load", forbidden)
    monkeypatch.setattr(run, "TrainingModule", forbidden)
    report = run.run_training(settings, paths, run_id="preview", dry_run=True)
    assert not (paths.runs_root / "preview").exists()
    assert report["budget"]["optimizer_updates_total"] == 4
    assert report["budget"]["final_accumulation_microbatches"] == 1
    assert report["counts"]["canonical_windows"] == 6
    assert report["counts"]["canonical_retained_payloads"] == 6
    assert report["counts"]["canonical_sources"] == 6
    assert report["counts"]["assigned_training_sources"] == 3
    assert report["counts"]["test_metadata_only"] == 1
    assert report["counts"]["validation"] == 2
    assert report["settings"]["band_names"] == ("nir", "red", "green")
    (paths.runs_root / "preview").mkdir()
    with pytest.raises(ValueError, match="already exists"):
        run.run_training(settings, paths, run_id="preview", dry_run=True)
    with pytest.raises(ValueError, match="simple name"):
        run.run_training(settings, paths, run_id="../escape", dry_run=True)


def test_native_fit_writes_local_checkpoints_and_never_reads_test(
    tmp_path, monkeypatch
):
    settings, paths = _inputs(tmp_path)
    opened = []
    original = np.load

    def guarded(path, *args, **kwargs):
        assert Path(path).name != "5.npz"
        opened.append(Path(path).name)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(np, "load", guarded)
    monkeypatch.setattr(
        run,
        "TrainingModule",
        lambda settings: TrainingModule(settings, torch.nn.Conv2d(3, 1, 1)),
    )
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        report = run.run_training(settings, paths, run_id="fit")
    finally:
        torch.set_num_threads(threads)
    assert report["status"] == "complete"
    assert (
        report["optimizer_updates_actual"]
        == report["budget"]["optimizer_updates_total"]
        == 4
    )
    assert set(opened) == {"0.npz", "1.npz", "2.npz", "3.npz", "4.npz"}
    assert Path(report["best_checkpoint"]).name == "best.ckpt"
    assert Path(report["last_checkpoint"]).name == "last.ckpt"
    state = torch.load(report["last_checkpoint"], weights_only=False)
    assert state["global_step"] == 4
    assert state["averaging_state"]["n_averaged"] == 0
    assert state["current_model_state"].keys() == state["state_dict"].keys()
    assert Path(report["validation_csv"]).is_file()
    saved = json.loads((paths.runs_root / "fit" / "run.json").read_text())
    assert saved["status"] == "complete" and saved["optimizer_updates_actual"] == 4


def test_fractional_batch_budget_matches_lightning():
    assert run._limited_batches(7, 0.5) == 3
    assert run._limited_batches(7, 1.0) == 7
    assert run._limited_batches(7, 2) == 2
    with pytest.raises(ValueError, match="no batches"):
        run._limited_batches(1, 0.5)


def test_recipe_only_cli_resolves_machine_paths_and_previews_auto_id(
    tmp_path, monkeypatch
):
    from datetime import datetime

    from typer.testing import CliRunner

    from kelpseg.cli import app

    _, paths = _inputs(tmp_path)
    (tmp_path / "machine.toml").write_text(
        '[paths]\ndata_root = "."\nruns_root = "runs"\n'
    )
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    recipe = recipe_dir / "smoke.toml"
    text = Path("configs/train/tiny_cpu.toml").read_text()
    text = text.replace('name = "tiny_cpu"', 'name = "coast-check"')
    text = text.replace("../../paths.local.toml", "../machine.toml")
    text = text.replace("data/chips/ca_bc/v1", "chips")
    text = text.replace("data/splits/ca_bc/v1/assignments.csv", "assignments.csv")
    recipe.write_text(text)

    def forbidden(*args, **kwargs):
        raise AssertionError("Dry run must not load arrays or construct a model")

    monkeypatch.setattr(np, "load", forbidden)
    monkeypatch.setattr(run, "TrainingModule", forbidden)
    monkeypatch.chdir(tmp_path.parent)
    result = CliRunner().invoke(app, ["train", "--recipe", str(recipe), "--dry-run"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    datetime.strptime(report["run_id"], "coast-check-%Y%m%dT%H%M%S%fZ")
    assert report["name"] == "coast-check"
    assert report["experiment"] == "baseline"
    assert report["variant"] == "augmented"
    assert report["settings"]["paths_file"] == str(tmp_path / "machine.toml")
    assert report["chips"] == str(tmp_path / "chips")
    assert report["output"] == str(paths.runs_root / report["run_id"])
    assert list(paths.runs_root.iterdir()) == []
    help_result = CliRunner().invoke(app, ["train", "--help"])
    assert help_result.exit_code == 0
    assert "--paths" not in help_result.stdout
    assert "--variant" not in help_result.stdout
    assert "--run-id" not in help_result.stdout


def test_completed_epoch_runner_resume_and_recipe_cli_preview(tmp_path, monkeypatch):
    """Resume the actual runner without new identity or pretrained initialization."""
    from lightning.pytorch.callbacks import Callback
    from typer.testing import CliRunner

    import kelpseg.paths
    import kelpseg.training.settings
    from kelpseg.cli import app

    settings, paths = _inputs(tmp_path)
    native_trainer = run.Trainer
    observed_initialization = []

    def small_model(settings):
        observed_initialization.append(settings.encoder_weights)
        return TrainingModule(settings, torch.nn.Conv2d(3, 1, 1))

    class InterruptAfterEpoch(Callback):
        def on_train_epoch_start(self, trainer, pl_module):
            if trainer.current_epoch == 1:
                raise RuntimeError("simulated interruption after completed epoch")

    def interrupted_trainer(**kwargs):
        kwargs["callbacks"].append(InterruptAfterEpoch())
        return native_trainer(**kwargs)

    monkeypatch.setattr(run, "TrainingModule", small_model)
    monkeypatch.setattr(run, "Trainer", interrupted_trainer)
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        with pytest.raises(RuntimeError, match="simulated interruption"):
            run.run_training(settings, paths, run_id="same-run")
        checkpoint = paths.runs_root / "same-run" / "checkpoints" / "last.ckpt"
        assert checkpoint.is_file()
        assert not (checkpoint.parent.parent / "model").exists()
        with pytest.raises(ValueError, match="recipe or selected memberships"):
            run.run_training(replace(settings, epochs=3), paths, resume=checkpoint)
        with pytest.raises(ValueError, match="saved run ID"):
            run.run_training(settings, paths, resume=checkpoint, run_id="different")

        monkeypatch.setattr(
            kelpseg.training.settings, "load_settings", lambda _: settings
        )
        monkeypatch.setattr(kelpseg.paths, "load_paths", lambda _: paths)
        monkeypatch.setattr(kelpseg.paths, "check_paths", lambda value: value)
        original_load = np.load

        def no_payloads(*args, **kwargs):
            raise AssertionError("Resume preview opened a payload")

        monkeypatch.setattr(np, "load", no_payloads)
        preview = CliRunner().invoke(
            app,
            [
                "train",
                "--recipe",
                "recipe.toml",
                "--resume",
                str(checkpoint),
                "--dry-run",
            ],
        )
        assert preview.exit_code == 0, preview.output
        assert json.loads(preview.stdout)["run_id"] == "same-run"
        assert len(observed_initialization) == 1
        monkeypatch.setattr(np, "load", original_load)
        monkeypatch.setattr(run, "Trainer", native_trainer)
        # Copy the complete run to another machine root and remove its old path.
        import shutil

        old_output = checkpoint.parent.parent
        relocated = tmp_path / "relocated-runs"
        relocated.mkdir()
        shutil.copytree(old_output, relocated / "same-run")
        shutil.rmtree(old_output)
        paths = replace(paths, runs_root=relocated)
        checkpoint = relocated / "same-run" / "checkpoints" / "last.ckpt"
        result = run.run_training(settings, paths, resume=checkpoint)
        assert result["run_id"] == "same-run"
        assert result["status"] == "complete"
        assert result["optimizer_updates_actual"] == 4
        assert observed_initialization[-1] is None
        assert Path(result["model_bundle"], "weights.pt").is_file()
        assert (relocated / "same-run" / "metrics" / "metrics.csv").is_file()
        assert "resume-" in result["validation_csv"]
        assert Path(result["validation_csv"]).is_file()
        assert Path(result["best_checkpoint"]).parent == checkpoint.parent
        resumed = torch.load(checkpoint, weights_only=False)
        assert resumed["epoch"] == 1
        assert resumed["global_step"] == 4
        assert resumed["training_resume"]["run_id"] == "same-run"
    finally:
        torch.set_num_threads(threads)
