"""Native CPU continuation, with independent model and augmentation RNG streams."""

import random
from dataclasses import asdict, replace
from pathlib import Path

import albumentations as A
import lightning.pytorch as pl
import numpy as np
import pytest
import torch
from lightning.pytorch.callbacks import Callback, ModelCheckpoint
from torch import nn
from torch.utils.data import DataLoader, Dataset

from kelpseg.training.ema import DelayedEMA
from kelpseg.training.loss_settings import DEFAULT_LOSSES, LossTerm
from kelpseg.training.module import TrainingModule
from kelpseg.training.resume import TrainingResume, build_resume_identity, load_resume
from kelpseg.training.run import seed_worker
from kelpseg.training.sampling import RepeatEpochSampler
from kelpseg.training.settings import TrainingSettings


class RandomImages(Dataset):
    def __init__(self, count, include_distance=False):
        self.count = count
        self.include_distance = include_distance
        self.transform = A.Compose([A.RandomBrightnessContrast(p=1)], seed=71)

    def __len__(self):
        return self.count

    def __getitem__(self, index):
        image = np.full((2, 2, 3), (index + 1) / (self.count + 2), np.float32)
        image = self.transform(image=image)["image"]
        image = torch.from_numpy(image.transpose(2, 0, 1).copy())
        image = image + random.random() / 10 + np.random.rand() / 10
        sample = {
            "image": image,
            "target": torch.ones(2, 2, dtype=torch.long),
            "index": index,
        }
        if self.include_distance:
            sample["effective_distance_m"] = torch.tensor(
                [[0.0, 120.0], [-100.0, 500.0]]
            )
        return sample


class StopAfterEpoch(Callback):
    def on_train_epoch_end(self, trainer, pl_module):
        trainer.should_stop = True


def fit_run(
    path,
    count,
    stop=False,
    checkpoint=None,
    workers=0,
    observed=None,
    losses=DEFAULT_LOSSES,
    draws=None,
    indices=None,
):
    pl.seed_everything(42)
    settings = TrainingSettings(
        epochs=2,
        losses=losses,
        train_draws_per_epoch=draws,
        warmup_epochs=1,
        num_workers=workers,
        persistent_workers=bool(workers),
        accelerator="cpu",
        precision="32-true",
        encoder_weights=None,
    )
    options = dict(
        num_workers=workers,
        persistent_workers=bool(workers),
        worker_init_fn=seed_worker,
    )
    sampler = RepeatEpochSampler(count, draws, settings.seed) if draws else None
    train = DataLoader(
        RandomImages(count, any(term.type == "distance_bce" for term in losses)),
        shuffle=sampler is None,
        sampler=sampler,
        generator=torch.Generator().manual_seed(42),
        **options,
    )
    val = DataLoader(
        RandomImages(1), generator=torch.Generator().manual_seed(43), **options
    )
    module = TrainingModule(
        settings, nn.Sequential(nn.Dropout2d(0.1), nn.Conv2d(3, 1, 1))
    )
    resume = TrainingResume(
        "saved-name",
        {
            "settings": {
                "num_workers": workers,
                "epochs": 2,
                "deterministic": True,
                "early_stopping_patience": 0,
                "losses": tuple(asdict(term) for term in losses),
            }
        },
        train,
        val,
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
    if indices is not None:

        class RecordDraws(Callback):
            def on_train_batch_start(self, trainer, pl_module, batch, batch_idx):
                indices.setdefault(trainer.current_epoch, []).extend(
                    batch["index"].tolist()
                )

        callbacks.append(RecordDraws())
    if stop:
        callbacks.append(StopAfterEpoch())
    if observed is not None:
        saved = torch.load(checkpoint, weights_only=False)

        class CheckRestoredState(Callback):
            def on_train_start(self, trainer, pl_module):
                assert_equal(pl_module.state_dict(), saved["current_model_state"])
                assert_equal(
                    trainer.optimizers[0].state_dict(), saved["optimizer_states"][0]
                )
                assert_equal(
                    trainer.lr_scheduler_configs[0].scheduler.state_dict(),
                    saved["lr_schedulers"][0],
                )
                ema = next(c for c in trainer.callbacks if isinstance(c, DelayedEMA))
                assert_equal(
                    ema._average_model.module.state_dict(), saved["state_dict"]
                )
                assert_equal(
                    ema._average_model.n_averaged,
                    saved["averaging_state"]["n_averaged"],
                )
                assert trainer.global_step == saved["global_step"]
                observed["restored"] = True

        callbacks.append(CheckRestoredState())
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


@pytest.mark.parametrize("workers", [0, 2])
def test_repeat_sampler_resumes_at_next_epoch(tmp_path, workers):
    """Preserve epoch draw order independently of worker augmentation streams."""
    full_draws, split_draws = {}, {}
    full = fit_run(tmp_path / "full", 5, draws=7, workers=workers, indices=full_draws)
    split = tmp_path / "split"
    partial = fit_run(
        split, 5, stop=True, draws=7, workers=workers, indices=split_draws
    )
    resumed = fit_run(
        split,
        5,
        checkpoint=split / "last.ckpt",
        draws=7,
        workers=workers,
        indices=split_draws,
    )
    assert partial["epoch"] == 0 and partial["global_step"] == 7
    assert resumed["epoch"] == 1 and resumed["global_step"] == 14
    assert split_draws == full_draws and full_draws[0] != full_draws[1]
    if workers == 0:
        assert_equal(full["state_dict"], resumed["state_dict"])
        assert_equal(full["optimizer_states"], resumed["optimizer_states"])


def test_weighted_resume_restores_and_checks_alpha(tmp_path: Path) -> None:
    """Resume a weighted run after EMA starts and reject a changed alpha."""
    losses = (
        LossTerm("distance_bce", weight=0.7, parameters={"alpha": 2}),
        LossTerm("dice", weight=0.3),
    )
    count = 102
    reference = fit_run(tmp_path / "full-weighted", count, losses=losses)
    split = tmp_path / "split-weighted"
    partial = fit_run(split, count, stop=True, losses=losses)
    assert int(partial["averaging_state"]["n_averaged"]) == 2
    checkpoint = split / "last.ckpt"
    identity = partial["training_resume"]["identity"]
    load_resume(checkpoint, identity)
    changed = dict(
        identity["settings"],
        losses=(asdict(LossTerm("distance_bce", weight=0.7)), asdict(losses[1])),
    )
    with pytest.raises(ValueError, match="recipe or selected memberships"):
        load_resume(checkpoint, dict(identity, settings=changed))
    resumed = fit_run(split, count, checkpoint=checkpoint, losses=losses)
    assert int(resumed["averaging_state"]["n_averaged"]) == 104
    for name in (
        "state_dict",
        "current_model_state",
        "averaging_state",
        "optimizer_states",
        "lr_schedulers",
        "global_step",
    ):
        assert_equal(reference[name], resumed[name])


def test_persistent_worker_resume_restores_training_state_and_advances(tmp_path):
    partial = fit_run(tmp_path / "workers", 102, stop=True, workers=2)
    assert partial["epoch"] == 0
    assert int(partial["averaging_state"]["n_averaged"]) == 2
    assert partial["training_resume"]["transform"] is None
    checkpoint = tmp_path / "workers/last.ckpt"
    load_resume(checkpoint, partial["training_resume"]["identity"])
    observed = {}
    resumed = fit_run(
        tmp_path / "workers", 102, checkpoint=checkpoint, workers=2, observed=observed
    )
    assert observed["restored"]
    assert resumed["training_resume"]["run_id"] == "saved-name"
    assert resumed["epoch"] == 1
    assert resumed["global_step"] == 204
    assert int(resumed["averaging_state"]["n_averaged"]) == 104


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
            checkpoint,
            build_resume_identity(
                replace(settings, losses=(LossTerm("dice"),)), inputs
            ),
        )
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


def test_resume_rejects_exhausted_budget(tmp_path):
    checkpoint = tmp_path / "last.ckpt"
    for workers in (0, 2):
        identity = {
            "settings": {
                "num_workers": workers,
                "epochs": 2,
                "deterministic": True,
                "early_stopping_patience": 0,
                "losses": tuple(asdict(term) for term in DEFAULT_LOSSES),
            }
        }
        torch.save(
            {
                "epoch": 1,
                "training_resume": {
                    "identity": identity,
                    "completed_epoch": True,
                },
            },
            checkpoint,
        )
        with pytest.raises(ValueError, match="already completed"):
            load_resume(checkpoint, identity)


@pytest.mark.parametrize(
    "missing",
    [
        "deterministic",
        "losses",
        "early_stopping_patience",
        "encoder_name",
        "checkpoint_epochs",
    ],
)
def test_resume_rejects_missing_recipe_fields(tmp_path: Path, missing: str) -> None:
    """Reject incomplete saved recipes instead of guessing historical defaults."""
    identity = {"settings": asdict(TrainingSettings())}
    saved_settings = dict(identity["settings"])
    saved_settings.pop(missing)
    checkpoint = tmp_path / "last.ckpt"
    torch.save(
        {
            "epoch": 0,
            "training_resume": {
                "completed_epoch": True,
                "identity": {"settings": saved_settings},
            },
        },
        checkpoint,
    )
    with pytest.raises(ValueError, match="different schema"):
        load_resume(checkpoint, identity)
