"""Bounded real B3 updates; no pretrained downloads or production training."""

import gc
from pathlib import Path

import numpy as np
import pytest
import torch

from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.models import build_model
from kelpseg.preprocessing import BAND_NAMES
from kelpseg.training.data import ChipDataset
from kelpseg.training.loss import BinaryObjective


@pytest.mark.parametrize(
    "selection,channels",
    [("all", 8), ("rgbnir", 4), ("rgb", 3), (("nir", "red", "green"), 3)],
)
def test_real_b3_cpu_optimizer_update(tmp_path, selection, channels, monkeypatch):
    # Fail immediately if a no-weights construction ever tries either download path.
    def no_download(*args, **kwargs):
        raise AssertionError("Automated B3 smoke must not download weights")

    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", no_download)
    monkeypatch.setattr(torch.hub, "load_state_dict_from_url", no_download)
    old_threads = torch.get_num_threads()
    torch.set_num_threads(2)
    try:
        torch.manual_seed(33)
        rng = np.random.default_rng(33)
        image = rng.integers(1, 7000, (57, 61, 8), dtype=np.uint16)
        image[0, 0] = 0
        target = np.zeros((57, 61), dtype=np.int8)
        target[10:30, 10:30] = 1
        target[0, 0] = -100
        payload = tmp_path / "train.npz"
        np.savez(payload, image=image, label=target)
        dataset = ChipDataset(
            [{"split": "train", "payload": payload}],
            BAND_NAMES,
            selection=selection,
            chip_size=64,
            augmentation=build_training_augmentation(seed=7),
        )
        sample = dataset[0]
        model = build_model(channels, encoder_weights=None).cpu().float().train()
        assert model.encoder.__class__.__name__ == "MixVisionTransformerEncoder"
        assert model.encoder.patch_embed1.proj.in_channels == channels
        optimizer = torch.optim.SGD(model.parameters(), lr=0.001)
        before = model.encoder.patch_embed1.proj.weight.detach().clone()
        logits = model(sample["image"][None])
        assert logits.shape == (1, 1, 64, 64) and logits.dtype == torch.float32
        loss = BinaryObjective()(logits, sample["target"][None])[0]
        assert torch.isfinite(loss)
        loss.backward()
        for parameter in model.parameters():
            if parameter.grad is not None:
                assert torch.isfinite(parameter.grad).all()
        optimizer.step()
        assert not torch.equal(before, model.encoder.patch_embed1.proj.weight)
        del model, optimizer, logits, loss
    finally:
        torch.set_num_threads(old_threads)
        gc.collect()


@pytest.mark.parametrize("channels", [1, 5, 8.0, True])
def test_reject_unsupported_channels(channels):
    with pytest.raises(ValueError, match="3, 4, or 8"):
        build_model(channels, encoder_weights=None)


def test_reject_unsupported_initialization():
    with pytest.raises(ValueError, match="encoder_weights"):
        build_model(3, encoder_weights="other")


@pytest.mark.parametrize("encoder_name", ["mit_b0", "mit_b1", "mit_b2"])
def test_smaller_encoder_bundle_round_trip(tmp_path: Path, encoder_name: str) -> None:
    """Export/reload actual eight-band models and preserve inference predictions."""
    from dataclasses import replace

    from kelpseg.model_bundle import export_model_bundle, load_model_bundle
    from kelpseg.training.settings import TrainingSettings

    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        settings = replace(TrainingSettings(), encoder_name=encoder_name)
        model = build_model(8, encoder_weights=None, encoder_name=encoder_name).eval()
        x = torch.randn(1, 8, 32, 32)
        with torch.no_grad():
            expected = model(x)
        assert expected.shape == (1, 1, 32, 32)
        checkpoint = tmp_path / "selected.ckpt"
        torch.save(
            {
                "state_dict": {f"model.{k}": v for k, v in model.state_dict().items()},
                "epoch": 3,
                "global_step": 10,
                "averaging_state": {"n_averaged": 0},
            },
            checkpoint,
        )
        del model
        gc.collect()
        bundle = export_model_bundle(
            checkpoint, tmp_path / "model", settings, run_id="size-test"
        )
        loaded = load_model_bundle(bundle)
        assert loaded.metadata["encoder"] == encoder_name
        with torch.no_grad():
            actual = loaded.model(x)
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
        prediction = loaded.predict_probabilities(
            np.full((32, 32, 8), 1000, dtype=np.uint16), settings.band_names
        )
        assert prediction.shape == (32, 32) and np.isfinite(prediction).all()
    finally:
        torch.set_num_threads(threads)
