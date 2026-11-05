"""Saved chip prediction geometry and label-independent execution."""

import csv
import json
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio
from rasterio import Affine

from kelpseg.prediction.chips import predict_chips


@pytest.fixture
def chip_run(tmp_path, monkeypatch):
    """Make a source crop with two separated chips and no stored label arrays."""
    import kelpseg.prediction.chips as chips

    root = tmp_path / "chips"
    root.mkdir()
    (root / "recipe.json").write_text(
        json.dumps(dict(source_band_names=["nir", "red", "green"]))
    )
    transform = Affine(3, 0, 300, 0, -3, 600)
    rows = []
    for index, col in enumerate((0, 5)):
        image = np.ones((2, 3, 3), dtype=np.uint16) * (index + 1)
        image[:, :, 0] = np.arange(6).reshape(2, 3) + 1 + index
        if index == 0:
            image[0, 0] = 0
        payload = root / f"{index}.npz"
        np.savez(payload, image=image)  # inference must not request a label
        rows.append(
            dict(
                source_key="crop",
                dataset_id="d",
                release_id="v",
                source_id="source",
                original_tiff="original.tif",
                region="001",
                acquisition_date="2020-01-01",
                crs="EPSG:32611",
                transform=list(transform),
                row_offset=10,
                col_offset=20,
                row=1,
                col=col,
                original_row=11,
                original_col=20 + col,
                height=2,
                width=3,
                payload=str(payload),
                split="val",
            )
        )
    run = tmp_path / "run"
    (run / "model").mkdir(parents=True)
    (run / "run.json").write_text(
        json.dumps(
            dict(
                status="complete",
                run_id="run",
                chips=str(root),
                assignments="unused",
                experiment="baseline",
                variant="augmented",
            )
        )
    )
    metadata = dict(
        run_id="run", threshold=0.5, input_size=512, band_names=["nir", "red", "green"]
    )
    (run / "model/model.json").write_text(json.dumps(metadata))
    calls = []

    def predict(image, bands):
        calls.append(image.copy())
        probability = image[:, :, 0].astype(np.float32) / 10
        probability[~np.any(image != 0, axis=-1)] = np.nan
        return probability

    model = SimpleNamespace(metadata=metadata, predict_probabilities=predict)
    monkeypatch.setattr(chips, "load_model_bundle", lambda *args, **kwargs: model)
    monkeypatch.setattr(
        chips,
        "select_windows",
        lambda *args, **kwargs: (
            rows + [dict(rows[0], split="test", payload="must-not-open-test.npz")]
        ),
    )
    return run, rows, calls


def test_saved_chip_geometry_metadata_and_no_labels(chip_run, tmp_path):
    run, rows, calls = chip_run
    output = predict_chips(run, tmp_path / "predictions")
    assert len(calls) == 2
    with rasterio.open(output / "probabilities/source_000001.tif") as source:
        probability = source.read(1)
        assert source.transform == Affine(3, 0, 300, 0, -3, 597)
        assert source.shape == (2, 8)
        assert source.crs.to_epsg() == 32611
    assert np.isnan(probability[:, 3:5]).all()
    assert np.isnan(probability[0, 0])
    assert probability[1, 2] == pytest.approx(0.6)
    assert probability[1, 7] == pytest.approx(0.7)
    with (output / "sources.csv").open() as stream:
        record = next(csv.DictReader(stream))
    assert record["original_source_id"] == "original.tif"
    assert (record["row_offset"], record["col_offset"]) == ("11", "20")
    assert int(record["valid_pixels"]) == 11
    assert int(record["nodata_pixels"]) == 1
    assert int(record["retained_window_pixels"]) == 12
    assert int(record["geometric_gap_pixels"]) == 4
    assert int(record["predicted_valid_pixels"]) == 11
    with (output / "windows.csv").open() as stream:
        windows = list(csv.DictReader(stream))
    assert all(row["source_key"] == "source_000001" for row in windows)
    assert all(row["chip_source_key"] == "crop" for row in windows)
    assert json.loads(windows[0]["transform"]) == rows[0]["transform"]
    settings = json.loads((output / "settings.json").read_text())
    assert settings["scope"] == "chip_disjoint" and settings["split"] == "val"
    assert settings["model"]["threshold"] == 0.5
    assert json.loads((output / "summary.json").read_text())["status"] == "complete"
    with pytest.raises(ValueError, match="already exists"):
        predict_chips(run, output)


def test_training_sample_selection_recorded_without_test_reads(
    chip_run, tmp_path, monkeypatch
):
    import kelpseg.prediction.chips as chips

    run, rows, calls = chip_run
    selections = []

    def sample(run, count, seed):
        selections.append((count, seed))
        return [dict(rows[0], split="train")]

    monkeypatch.setattr(chips, "training_sample", sample)
    output = predict_chips(
        run, tmp_path / "train-predictions", split="train", sources_per_region=2, seed=7
    )
    assert selections == [(2, 7)] and len(calls) == 1
    settings = json.loads((output / "settings.json").read_text())
    assert settings["split"] == "train"
    assert settings["recipe"]["seed"] == 7
    assert settings["recipe"]["sources_per_region"] == 2


@pytest.mark.parametrize(
    "change, error",
    [("running", "completed run"), ("identity", "different run identities")],
)
def test_incomplete_or_mismatched_run_rejected(chip_run, tmp_path, change, error):
    run, _, calls = chip_run
    record = json.loads((run / "run.json").read_text())
    if change == "running":
        record["status"] = "running"
    else:
        record["run_id"] = "other"
    (run / "run.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match=error):
        predict_chips(run, tmp_path / "predictions")
    assert calls == []
    assert not (tmp_path / "predictions").exists()


def test_test_split_rejected_without_inference(chip_run, tmp_path):
    run, _, calls = chip_run
    with pytest.raises(ValueError, match="test is excluded"):
        predict_chips(run, tmp_path / "predictions", split="test")
    assert calls == []
