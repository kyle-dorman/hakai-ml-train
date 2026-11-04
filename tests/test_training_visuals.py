"""Prediction media preserve alignment and identities without extra inference."""

from types import SimpleNamespace

import numpy as np
import pytest
import torch

from kelpseg.preprocessing import BAND_NAMES, MEAN, STD
from kelpseg.training.visuals import (
    EpochImages,
    fixed_validation_samples,
    prediction_image,
)


def row(index, region="001", kelp=1):
    return dict(
        payload=str(index),
        region=region,
        kelp_pixels=kelp,
        source_id=f"source-{index}",
        acquisition_date="2021-01-01",
        row=0,
        col=index,
        original_row=10,
        original_col=index + 20,
        true_height=2,
        true_width=2,
    )


def test_fixed_selection_is_order_independent_and_includes_background():
    rows = [row(0, kelp=0), row(1), row(2, "002"), row(3, "002", 0)]
    assert fixed_validation_samples(rows) == ["1", "2", "0", "3"]
    assert fixed_validation_samples(rows[::-1]) == ["1", "2", "0", "3"]


def test_media_uses_actual_augmented_input_and_aligned_ignore_mask():
    raw = torch.arange(8 * 3 * 3).reshape(8, 3, 3).float() * 10
    image = (raw - torch.tensor(MEAN)[:, None, None]) / torch.tensor(STD)[:, None, None]
    target = torch.tensor([[1, 0, -100], [0, 1, -100], [-100, -100, -100]])
    prediction = torch.ones_like(target)
    result = prediction_image(image, target, prediction, row(1), BAND_NAMES, "val", 0)
    assert result["image"].shape == (3, 3, 3)
    np.testing.assert_array_equal(
        result["masks"]["label"]["mask_data"], [[1, 0, 2], [0, 1, 2], [2, 2, 2]]
    )
    training = prediction_image(
        image, target, prediction, row(1), BAND_NAMES, "train", 1
    )
    assert training["image"].shape == (3, 3, 3)
    assert training["masks"]["label"]["mask_data"][0, 2] == 2
    assert training["masks"]["prediction"]["mask_data"][0, 2] == 2
    assert "epoch 2" in training["caption"] and "augmented" in training["caption"]
    assert "r10 c21" in training["caption"]


def test_bounded_samples_reset_for_each_epoch():
    rows = [row(i) for i in range(6)]
    images = EpochImages(rows, BAND_NAMES)
    batch = dict(
        image=torch.zeros(6, 8, 3, 3),
        target=torch.zeros(6, 3, 3, dtype=torch.long),
        metadata=rows,
    )
    predictions = torch.ones(6, 3, 3, dtype=torch.long)
    images.collect(batch, predictions, "train", 0)
    images.collect(batch, predictions, "val", 0)
    assert len(images.samples["train"]) == 4
    assert list(images.samples["val"]) == ["0"]
    calls = []
    images.log(SimpleNamespace(log_image=lambda **kw: calls.append(kw)), "train", 5)
    assert len(calls[0]["images"]) == 4 and calls[0]["step"] == 5
    assert not images.samples["train"]
    images.log(SimpleNamespace(log_image=lambda **kw: calls.append(kw)), "val", 5)
    batch["metadata"] = rows[::-1]
    images.collect(batch, predictions, "train", 1)
    images.collect(batch, predictions, "val", 1)
    assert list(images.samples["train"]) == ["5", "4", "3", "2"]
    assert list(images.samples["val"]) == ["0"]


def test_trainer_uploads_both_epoch_panels_offline(tmp_path, monkeypatch, caplog):
    wandb = pytest.importorskip("wandb")
    from lightning.pytorch import Trainer
    from lightning.pytorch.loggers import WandbLogger
    from torch.utils.data import DataLoader

    from kelpseg.training.module import TrainingModule
    from kelpseg.training.run import collate_chips
    from kelpseg.training.settings import load_settings

    monkeypatch.setenv("WANDB_MODE", "offline")
    monkeypatch.setenv("WANDB_SILENT", "true")
    settings = load_settings("configs/train/tiny_cpu.toml")
    rows = [row(0), dict(row(1, kelp=0), true_height=3, true_width=3)]
    dataset = [
        dict(
            image=torch.ones(3, 3, 3),
            target=torch.full((3, 3), i, dtype=torch.long),
            valid_mask=torch.ones(3, 3, dtype=torch.bool),
            metadata=metadata,
        )
        for i, metadata in zip([1, 0], rows, strict=True)
    ]
    dataset[0]["target"][2, :] = -100
    dataset[0]["target"][:, 2] = -100
    dataset[0]["valid_mask"] = dataset[0]["target"] != -100
    loader = DataLoader(dataset, batch_size=1, collate_fn=collate_chips)
    module = TrainingModule(settings, torch.nn.Conv2d(3, 1, 1))
    module.configure_diagnostics(rows)
    logger = WandbLogger(project="kelpseg-tests", save_dir=str(tmp_path), offline=True)
    logged = []
    original = logger.log_image

    def capture(**kwargs):
        logged.append(kwargs)
        original(**kwargs)

    monkeypatch.setattr(logger, "log_image", capture)
    trainer = Trainer(
        accelerator="cpu",
        devices=1,
        max_epochs=2,
        logger=logger,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
    )
    try:
        trainer.fit(module, loader, loader)
        assert [call["key"] for call in logged] == [
            "val/predictions",
            "train/predictions",
            "val/predictions",
            "train/predictions",
        ]
        assert [call["step"] for call in logged] == [2, 2, 4, 4]
        assert all("epoch 1" in caption for caption in logged[0]["caption"])
        assert all("epoch 2" in caption for caption in logged[2]["caption"])
        assert len(logged[0]["images"]) == len(logged[2]["images"]) == 2
        assert all(
            image.shape == (3, 3, 3) for call in logged for image in call["images"]
        )
        assert "Images sizes do not match" not in caplog.text
        assert logged[0]["masks"][0]["prediction"]["mask_data"][2, 0] == 2
        assert not module.epoch_images.samples["train"]
        assert not module.epoch_images.samples["val"]
        assert logger.experiment.offline
        assert list(tmp_path.rglob("*.png"))
    finally:
        wandb.finish()
