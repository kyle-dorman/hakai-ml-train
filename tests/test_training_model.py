"""Bounded real B3 updates; no pretrained downloads or production training."""

import gc

import numpy as np
import pytest
import torch

from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.models import build_model
from kelpseg.preprocessing import BAND_NAMES
from kelpseg.training.data import ChipDataset
from kelpseg.training.loss import segmentation_loss


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
        loss = segmentation_loss(logits, sample["target"][None])
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
