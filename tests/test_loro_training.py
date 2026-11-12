"""Fixed baseline normalization, fold isolation and copied-bundle inference."""

import csv
import json
import shutil
from dataclasses import replace

import numpy as np
import pytest
import torch
from test_training_data import _collection

from kelpseg import model_bundle
from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.splits import validate_loro_assignments
from kelpseg.preprocessing import BAND_NAMES, MEAN, STD
from kelpseg.training.data import build_training_inputs
from kelpseg.training.settings import TrainingSettings


def fold_inputs(root):
    """Make one held-out source and separate train/validation sources."""
    rows = _collection(root)
    for row in rows:
        row["experiment"] = "loro_001"
        row["region"] = "001" if row["split"] == "test" else "002"
    (root / "sources.json").write_text(json.dumps(rows))
    path = root / "assignments.csv"
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return rows, path


def test_fixed_normalization_train_validation_and_copied_fold_bundle(
    tmp_path, monkeypatch
):
    """All folds preserve the exact baseline statistics, including copied inference."""
    rows, _ = fold_inputs(tmp_path)
    settings = TrainingSettings(experiment="loro_001")
    assert settings.mean == MEAN and settings.std == STD
    inputs = build_training_inputs(tmp_path, rows, experiment=settings.experiment)
    assert {r["region"] for r in inputs["test_rows"]} == {"001"}
    assert all(r["region"] != "001" for r in inputs["train"].rows + inputs["val"].rows)
    for dataset in (inputs["train"], inputs["val"]):
        normalize = dataset.transform.transforms[-3]
        assert tuple(normalize.mean) == settings.mean
        assert tuple(normalize.std) == settings.std
    sample = inputs["val"][0]
    with np.load(tmp_path / "2.npz") as payload:
        image = payload["image"]
    valid = np.any(image != 0, axis=-1)
    expected = (np.minimum(image, 5000) - np.array(settings.mean)) / settings.std
    expected[~valid] = 0
    np.testing.assert_allclose(
        sample["image"][:, :3, :4], expected.transpose(2, 0, 1), rtol=1e-5, atol=1e-6
    )
    selected = torch.nn.Conv2d(8, 1, 1).eval()
    checkpoint = tmp_path / "best.ckpt"
    torch.save(
        {
            "state_dict": {f"model.{k}": v for k, v in selected.state_dict().items()},
            "averaging_state": {"n_averaged": 2},
            "epoch": 1,
            "global_step": 102,
        },
        checkpoint,
    )
    original = model_bundle.export_model_bundle(
        checkpoint, tmp_path / "original", settings, run_id="fold-test"
    )
    copied = tmp_path / "copied"
    shutil.copytree(original, copied)
    shutil.rmtree(original)
    checkpoint.unlink()
    monkeypatch.setattr(
        model_bundle,
        "build_model",
        lambda channels, **kwargs: torch.nn.Conv2d(channels, 1, 1),
    )
    loaded = model_bundle.load_model_bundle(copied)
    actual = loaded.predict_probabilities(image, BAND_NAMES)
    with torch.inference_mode():
        expected_probability = (
            selected(sample["image"][None]).sigmoid()[0, 0, :3, :4].numpy()
        )
    expected_probability[~valid] = np.nan
    np.testing.assert_allclose(actual, expected_probability, rtol=1e-6, atol=1e-7)
    assert loaded.metadata["mean"] == list(settings.mean)
    assert loaded.metadata["experiment"] == "loro_001"


@pytest.mark.parametrize(
    "field,value",
    [
        ("mean", None),
        ("mean", (float("nan"),) * 8),
        ("std", (0.0,) * 8),
        ("std", (1.0,) * 7),
        ("experiment", "loro_011"),
    ],
)
def test_bad_fold_settings(field, value):
    values = dict(experiment="loro_001")
    values[field] = value
    with pytest.raises(ValueError):
        TrainingSettings(**values)


def test_all_folds_preserve_baseline_statistics():
    """The ten supported folds use exactly the existing baseline preprocessing."""
    for number in range(1, 11):
        settings = TrainingSettings(experiment=f"loro_{number:03d}")
        assert settings.mean == MEAN and settings.std == STD
        assert settings.clip_value == 5000
    with pytest.raises(ValueError, match="approved"):
        TrainingSettings(experiment="loro_001", mean=(100.0,) * 8)


@pytest.mark.parametrize(
    "mistake",
    ["heldout_train", "other_test", "bc_val", "companion_train", "companion_val"],
)
def test_fold_assignment_mistakes_fail(tmp_path, mistake):
    rows, _ = fold_inputs(tmp_path)
    if mistake == "heldout_train":
        rows[-1]["split"] = "train"
    elif mistake == "other_test":
        rows[0]["split"] = "test"
    elif mistake == "bc_val":
        rows[2]["region"] = "011"
    else:
        rows[0]["acquisition_date"] = rows[-1]["acquisition_date"]
        rows[0]["split"] = mistake.removeprefix("companion_")
    with pytest.raises(PreparationError):
        validate_loro_assignments(rows, "loro_001")


def test_bc_companion_excluded_and_same_spacecraft_other_day_allowed(tmp_path):
    rows, _ = fold_inputs(tmp_path)
    rows[0]["region"] = "011"
    rows[1]["region"] = "012"
    rows[1]["split"] = "unused"
    rows[1]["acquisition_date"] = rows[-1]["acquisition_date"]
    validate_loro_assignments(rows, "loro_001")


def test_fold_training_preview_records_fixed_normalization_scope(tmp_path):
    """The public trainer discloses reuse of baseline statistics for the fold."""
    from test_training_run import _inputs

    from kelpseg.training import run

    settings, paths = _inputs(tmp_path)
    assignments = tmp_path / "assignments.csv"
    with assignments.open() as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["experiment"] = "loro_001"
        row["region"] = "001" if row["split"] == "test" else "002"
    with assignments.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    sources_file = tmp_path / "chips/sources.json"
    sources = json.loads(sources_file.read_text())
    for source, row in zip(sources, rows, strict=True):
        source["region"] = row["region"]
    sources_file.write_text(json.dumps(sources))
    settings = replace(
        settings,
        experiment="loro_001",
        band_names=BAND_NAMES,
        mean=MEAN,
        std=STD,
    )
    report = run.run_training(settings, paths, dry_run=True)
    assert report["held_out_region"] == "001"
    assert report["regions"] == ["002"]
    assert report["normalization_scope"].startswith(
        "fixed kelp-positive with-BC baseline"
    )
    assert "held-out region" in report["normalization_scope"]
    assert report["budget"]["optimizer_updates_total"] == 4
