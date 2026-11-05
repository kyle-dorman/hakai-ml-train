"""Completed-epoch RNG glue around Lightning's native checkpoint restoration."""

import copy
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
from lightning.pytorch.callbacks import Callback, ModelCheckpoint

from kelpseg.training.loss_settings import DEFAULT_LOSSES


def build_resume_identity(settings, inputs):
    """Compare ordinary settings and selected metadata, allowing root relocation."""
    recipe = asdict(settings)
    for name in ("paths_file", "chips", "assignments"):
        recipe.pop(name)
    memberships = {}
    for split, rows in (
        ("train", inputs["train"].rows),
        ("val", inputs["val"].rows),
        ("test", inputs["test_rows"]),
        ("excluded", inputs["excluded_training_rows"]),
    ):
        memberships[split] = [
            {key: value for key, value in row.items() if key != "payload"}
            for row in rows
        ]
    return {
        "settings": recipe,
        "memberships": memberships,
        "source_band_names": inputs["train"].source_band_names,
        "chip_size": inputs["train"].chip_size,
    }


def load_resume(path: str | Path, identity: dict) -> dict:
    """Read a completed-epoch checkpoint and return its saved resume metadata.

    path identifies last.ckpt; identity contains current settings/memberships.
    Earlier missing loss settings mean the historical BCE/Lovasz default.
    Changed recipes or exhausted epoch budgets raise ValueError; files are not
    modified and restoring model/optimizer state remains Lightning's job.
    """
    checkpoint = torch.load(Path(path), map_location="cpu", weights_only=False)
    saved = checkpoint.get("training_resume")
    if saved is None or not saved["completed_epoch"]:
        raise ValueError("Resume requires a last checkpoint from a completed epoch.")
    # The immediately preceding runner hardcoded deterministic=True. Interpret
    # its missing field that way; earlier GPU smokes have no replay guarantee.
    saved_identity = copy.deepcopy(saved["identity"])
    saved_identity["settings"].setdefault("deterministic", True)
    # Earlier runs used exactly this hardcoded objective. Preserve their resume
    # meaning; a changed configured loss still requires a fresh run.
    saved_identity["settings"].setdefault(
        "losses", tuple(asdict(term) for term in DEFAULT_LOSSES)
    )
    # Old runs did not have early stopping; these defaults preserve that policy.
    for name, default in (
        ("early_stopping_patience", 0),
        ("early_stopping_min_delta", 0.0),
    ):
        if name in identity["settings"]:
            saved_identity["settings"].setdefault(name, default)
    if saved_identity != identity:
        raise ValueError(
            "Resume recipe or selected memberships changed; start a fresh run."
        )
    if checkpoint["epoch"] + 1 >= identity["settings"]["epochs"]:
        raise ValueError("The saved run has already completed its total epoch budget.")
    return saved


def _transform_state(transform):
    if transform is None:
        return None
    return {
        "numpy": copy.deepcopy(transform.random_generator.bit_generator.state),
        "python": transform.py_random.getstate(),
        "children": [_transform_state(t) for t in getattr(transform, "transforms", [])],
    }


def _restore_transform(transform, state):
    if state is None:
        return
    transform.random_generator.bit_generator.state = state["numpy"]
    transform.py_random.setstate(state["python"])
    for child, child_state in zip(
        getattr(transform, "transforms", []), state["children"], strict=True
    ):
        _restore_transform(child, child_state)


class TrainingResume(Callback):
    """Save only missing random state; Lightning owns all training state.

    Worker-process augmentation streams restart on resume. Training state still
    continues from the completed epoch, but worker draws and sample order may
    differ. Zero workers retain the saved augmentation stream for exact replay.
    """

    def __init__(self, run_id, identity, train_loader, val_loader):
        self.run_id = run_id
        self.identity = identity
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.completed_epoch = False
        self.saved = None

    def on_train_epoch_start(self, trainer, pl_module):
        self.completed_epoch = False

    def on_train_epoch_end(self, trainer, pl_module):
        self.completed_epoch = True

    def on_save_checkpoint(self, trainer, pl_module, checkpoint):
        checkpoint["training_resume"] = {
            "run_id": self.run_id,
            "identity": self.identity,
            "completed_epoch": self.completed_epoch,
            "python": random.getstate(),
            "numpy": np.random.get_state(),
            "torch": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            "train_generator": self.train_loader.generator.get_state(),
            "val_generator": self.val_loader.generator.get_state(),
            # With workers, this parent-process transform has not advanced.
            "transform": None
            if self.train_loader.num_workers
            else _transform_state(
                getattr(self.train_loader.dataset, "transform", None)
            ),
        }

    def on_load_checkpoint(self, trainer, pl_module, checkpoint):
        # A copied complete run may live under a new runs_root. Native
        # ModelCheckpoint otherwise drops its best score when dirpath changes.
        for callback in trainer.callbacks:
            if not isinstance(callback, ModelCheckpoint):
                continue
            states = checkpoint.get("callbacks", {})
            # The display-name change must not reset the best validation score.
            if callback.monitor == "val/iou" and callback.state_key not in states:
                for key, saved_state in list(states.items()):
                    if (
                        isinstance(saved_state, dict)
                        and saved_state.get("monitor") == "val_iou"
                    ):
                        saved_state["monitor"] = "val/iou"
                        states[callback.state_key] = states.pop(key)
                        break
            state = states.get(callback.state_key)
            if state is None or state["dirpath"] == callback.dirpath:
                continue
            old_directory = Path(state["dirpath"])
            new_directory = Path(callback.dirpath)

            def relocated(
                path, old_directory=old_directory, new_directory=new_directory
            ):
                if not path:
                    return path
                return str(new_directory / Path(path).relative_to(old_directory))

            for name in ("best_model_path", "kth_best_model_path", "last_model_path"):
                state[name] = relocated(state[name])
            state["best_k_models"] = {
                relocated(path): score for path, score in state["best_k_models"].items()
            }
            state["dirpath"] = callback.dirpath
        self.saved = checkpoint["training_resume"]
        self.train_loader.generator.set_state(self.saved["train_generator"])
        self.val_loader.generator.set_state(self.saved["val_generator"])
        _restore_transform(
            getattr(self.train_loader.dataset, "transform", None),
            self.saved["transform"],
        )

    def on_train_start(self, trainer, pl_module):
        if self.saved is not None:
            random.setstate(self.saved["python"])
            np.random.set_state(self.saved["numpy"])
            torch.set_rng_state(self.saved["torch"])
            if self.saved["cuda"]:
                torch.cuda.set_rng_state_all(self.saved["cuda"])
