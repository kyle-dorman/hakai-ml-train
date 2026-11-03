"""Native CPU continuation, with independent model and augmentation RNG streams."""

import random
from dataclasses import replace

import albumentations as A
import lightning.pytorch as pl
import numpy as np
import pytest
import torch
from lightning.pytorch.callbacks import Callback, ModelCheckpoint
from torch import nn
from torch.utils.data import DataLoader, Dataset

from kelpseg.training.ema import DelayedEMA
from kelpseg.training.module import TrainingModule
from kelpseg.training.resume import TrainingResume, build_resume_identity, load_resume
from kelpseg.training.settings import TrainingSettings


class RandomImages(Dataset):
    def __init__(self, count):
        self.count = count
        self.transform = A.Compose([A.RandomBrightnessContrast(p=1)], seed=71)

    def __len__(self):
        return self.count

    def __getitem__(self, index):
        image = np.full((2, 2, 3), (index + 1) / (self.count + 2), np.float32)
        image = self.transform(image=image)["image"]
        image = torch.from_numpy(image.transpose(2, 0, 1).copy())
        image = image + random.random() / 10 + np.random.rand() / 10
        return {"image": image, "target": torch.ones(2, 2, dtype=torch.long)}


class StopAfterEpoch(Callback):
    def on_train_epoch_end(self, trainer, pl_module):
        trainer.should_stop = True


def fit_run(path, count, stop=False, checkpoint=None):
    pl.seed_everything(42)
    settings = TrainingSettings(
        epochs=2,
        warmup_epochs=1,
        num_workers=0,
        persistent_workers=False,
        accelerator="cpu",
        precision="32-true",
        encoder_weights=None,
    )
    train = DataLoader(
        RandomImages(count), shuffle=True, generator=torch.Generator().manual_seed(42)
    )
    val = DataLoader(RandomImages(1), generator=torch.Generator().manual_seed(43))
    module = TrainingModule(
        settings, nn.Sequential(nn.Dropout2d(0.1), nn.Conv2d(3, 1, 1))
    )
    resume = TrainingResume(
        "saved-name", {"settings": {"num_workers": 0, "epochs": 2}}, train, val
    )
    last = ModelCheckpoint(
        dirpath=path,
        filename="last",
        monitor=None,
        save_top_k=1,
        save_on_train_epoch_end=True,
        enable_version_counter=False,
    )
    callbacks = [DelayedEMA(), resume, last]
    if stop:
        callbacks.append(StopAfterEpoch())
    trainer = pl.Trainer(
        accelerator="cpu",
        devices=1,
        max_epochs=2,
        callbacks=callbacks,
        logger=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
    )
    trainer.fit(module, train, val, ckpt_path=checkpoint, weights_only=False)
    return torch.load(last.best_model_path, weights_only=False)


def assert_equal(left, right):
    if isinstance(left, torch.Tensor):
        torch.testing.assert_close(left, right, rtol=0, atol=0)
    elif isinstance(left, np.ndarray):
        np.testing.assert_array_equal(left, right)
    elif isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            assert_equal(left[key], right[key])
    elif isinstance(left, (list, tuple)):
        assert len(left) == len(right)
        for a, b in zip(left, right, strict=True):
            assert_equal(a, b)
    else:
        assert left == right


@pytest.mark.parametrize("count", [3, 102])
def test_completed_epoch_resume_matches_uninterrupted(tmp_path, count):
    reference = fit_run(tmp_path / "full", count)
    partial = fit_run(tmp_path / "split", count, stop=True)
    assert partial["epoch"] == 0
    assert partial["training_resume"]["completed_epoch"]
    load_resume(tmp_path / "split/last.ckpt", partial["training_resume"]["identity"])
    resumed = fit_run(
        tmp_path / "split", count, checkpoint=tmp_path / "split/last.ckpt"
    )
    for key in (
        "state_dict",
        "current_model_state",
        "averaging_state",
        "optimizer_states",
        "lr_schedulers",
        "global_step",
        "epoch",
        "loops",
    ):
        assert_equal(reference[key], resumed[key])
    for key in (
        "python",
        "numpy",
        "torch",
        "cuda",
        "train_generator",
        "val_generator",
        "transform",
    ):
        assert_equal(reference["training_resume"][key], resumed["training_resume"][key])
    assert_equal(
        reference["callbacks"]["DelayedEMA"], resumed["callbacks"]["DelayedEMA"]
    )
    assert resumed["global_step"] == count * 2
    assert int(resumed["averaging_state"]["n_averaged"]) == max(0, count * 2 - 100)


def test_resume_identity_and_boundary_errors(tmp_path):
    from types import SimpleNamespace

    settings = TrainingSettings(num_workers=0, persistent_workers=False)
    rows = [{"payload": "/old/image.npz", "source_key": "one", "split": "train"}]
    inputs = {
        "train": SimpleNamespace(
            rows=rows, source_band_names=("red", "green", "blue"), chip_size=512
        ),
        "val": SimpleNamespace(rows=[]),
        "test_rows": [],
        "excluded_training_rows": [],
    }
    identity = build_resume_identity(settings, inputs)
    rows[0]["payload"] = "/new/image.npz"
    relocated = replace(
        settings, paths_file="elsewhere", chips="elsewhere", assignments="elsewhere"
    )
    assert build_resume_identity(relocated, inputs) == identity
    checkpoint = tmp_path / "last.ckpt"
    torch.save(
        {
            "epoch": 0,
            "training_resume": {
                "run_id": "same",
                "identity": identity,
                "completed_epoch": True,
            },
        },
        checkpoint,
    )
    assert load_resume(checkpoint, identity)["run_id"] == "same"
    with pytest.raises(ValueError, match="recipe or selected memberships"):
        load_resume(
            checkpoint, build_resume_identity(replace(settings, epochs=71), inputs)
        )
    inputs["train"].source_band_names = ("blue", "green", "red")
    with pytest.raises(ValueError, match="memberships"):
        load_resume(checkpoint, build_resume_identity(settings, inputs))
    inputs["train"].source_band_names = ("red", "green", "blue")
    rows[0]["source_key"] = "different"
    with pytest.raises(ValueError, match="memberships"):
        load_resume(checkpoint, build_resume_identity(settings, inputs))
    torch.save({"training_resume": {"completed_epoch": False}}, checkpoint)
    with pytest.raises(ValueError, match="completed epoch"):
        load_resume(checkpoint, identity)
    torch.save({}, checkpoint)
    with pytest.raises(ValueError, match="completed epoch"):
        load_resume(checkpoint, identity)


def test_resume_rejects_workers_and_exhausted_budget(tmp_path):
    checkpoint = tmp_path / "last.ckpt"
    for workers, epoch, message in ((2, 0, "num_workers"), (0, 1, "already completed")):
        identity = {"settings": {"num_workers": workers, "epochs": 2}}
        torch.save(
            {
                "epoch": epoch,
                "training_resume": {
                    "identity": identity,
                    "completed_epoch": True,
                },
            },
            checkpoint,
        )
        with pytest.raises(ValueError, match=message):
            load_resume(checkpoint, identity)
