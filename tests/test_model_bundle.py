"""Copied bundles preserve selected weights and label-free preprocessing."""

import json
import shutil
from dataclasses import replace

import numpy as np
import pytest
import torch

from kelpseg import model_bundle
from kelpseg.preprocessing import BAND_NAMES, MEAN, STD
from kelpseg.training.settings import TrainingSettings
from kelpseg.training.transforms import build_input_transform


@pytest.mark.parametrize(
    "names",
    [
        BAND_NAMES,
        ("red", "green", "blue", "nir"),
        ("nir", "red", "green"),
        ("red", "green", "blue"),
    ],
)
@pytest.mark.parametrize("averaged", [0, 2])
def test_copied_bundle_matches_selected_validation_probabilities(
    tmp_path, monkeypatch, names, averaged
):
    torch.manual_seed(33)
    selected = torch.nn.Conv2d(len(names), 1, 1).eval()
    indices = [BAND_NAMES.index(name) for name in names]
    settings = replace(
        TrainingSettings(),
        band_names=names,
        mean=tuple(MEAN[index] for index in indices),
        std=tuple(STD[index] for index in indices),
        paths_file="/nonexistent/original/recipe/paths.toml",
    )
    checkpoint = tmp_path / "best.ckpt"
    torch.save(
        {
            "state_dict": {
                f"model.{key}": value for key, value in selected.state_dict().items()
            },
            "current_model_state": {
                f"model.{key}": torch.zeros_like(value)
                for key, value in selected.state_dict().items()
            },
            "averaging_state": {"n_averaged": averaged},
            "epoch": 1,
            "global_step": 102 if averaged else 2,
        },
        checkpoint,
    )
    original = model_bundle.export_model_bundle(
        checkpoint, tmp_path / "original" / "model", settings, run_id="saved-run"
    )
    copied = tmp_path / "unrelated" / "model"
    shutil.copytree(original, copied)
    shutil.rmtree(original.parent)
    checkpoint.unlink()

    def offline_model(channels, *, encoder_weights):
        assert encoder_weights is None
        return torch.nn.Conv2d(channels, 1, 1)

    monkeypatch.setattr(model_bundle, "build_model", offline_model)
    loaded = model_bundle.load_model_bundle(copied)
    image = np.full((13, 17, 8), 1000, dtype=np.uint16)
    image[0, 0] = 0
    # Nodata must see native channels, even when all selected channels are zero.
    image[0, 1] = 0
    image[0, 1, 0] = 700
    image[1, 2] = 6000
    padded = np.zeros((512, 512, len(names)), dtype=np.uint16)
    padded[:13, :17] = image[:, :, indices]
    validity = np.zeros((512, 512), dtype=np.int8)
    validity[:13, :17] = np.any(image != 0, axis=-1)
    tensor = build_input_transform(names)(image=padded, validity=validity)["image"]
    with torch.inference_mode():
        expected = selected(tensor[None]).sigmoid()[0, 0, :13, :17].numpy()
    expected[0, 0] = np.nan
    actual = loaded.predict_probabilities(image, BAND_NAMES)
    np.testing.assert_array_equal(actual, expected)
    assert np.isfinite(actual[0, 1])
    assert loaded.metadata["weight_kind"] == ("ema" if averaged else "current")
    assert loaded.metadata["run_id"] == "saved-run"
    assert loaded.metadata["band_names"] == list(names)
    assert "paths_file" not in loaded.metadata
    assert set(path.name for path in copied.iterdir()) == {"weights.pt", "model.json"}
    with pytest.raises(ValueError, match="already exists"):
        model_bundle.export_model_bundle("unused", copied, settings, run_id="other")
    with pytest.raises(ValueError, match="uint16"):
        loaded.predict_probabilities(image.astype(np.float32), BAND_NAMES)
    with pytest.raises(ValueError, match="between"):
        loaded.predict_probabilities(np.ones((513, 1, 8), dtype=np.uint16), BAND_NAMES)


def test_bundle_rejects_unsupported_normalization_before_constructing_model(
    tmp_path, monkeypatch
):
    metadata = dict(
        format_version=1,
        architecture="segformer",
        encoder="mit_b3",
        classes=1,
        input_size=512,
        threshold=0.5,
        band_names=list(BAND_NAMES),
        clip_value=1000,
        mean=list(MEAN),
        std=list(STD),
    )
    (tmp_path / "model.json").write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="normalization"):
        model_bundle.load_model_bundle(tmp_path)
