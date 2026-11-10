"""Strict training recipes with explicit optional loss terms."""

import math
import re
import tomllib
from dataclasses import dataclass, fields, replace
from pathlib import Path

from kelpseg.models import SUPPORTED_ENCODERS
from kelpseg.preprocessing import BAND_NAMES, CLIP_VALUE, MEAN, STD
from kelpseg.training.loss_settings import (
    DEFAULT_LOSSES,
    LossTerm,
    parse_losses,
    validate_losses,
)


@dataclass(frozen=True)
class TrainingSettings:
    """Machine-adjustable training settings; scientific preprocessing is fixed.

    early_stopping_patience=0 disables stopping; positive values count validation
    checks without a val/iou gain greater than early_stopping_min_delta. Epochs
    still defines the entire LR schedule even when stopping is enabled.
    checkpoint_epochs retains sorted one-based completed epochs in addition
    to best/last; an empty tuple keeps the default best/last-only policy.
    train_draws_per_epoch defaults to one shuffled pass. Set a larger draw
    count to fill the epoch with extra draws from one shuffled repeat.
    """

    name: str = "baseline"
    experiment: str = "baseline"
    paths_file: str = "paths.local.toml"
    variant: str = "augmented"
    band_names: tuple[str, ...] = BAND_NAMES
    mean: tuple[float, ...] = MEAN
    std: tuple[float, ...] = STD
    clip_value: int = CLIP_VALUE
    chips: str = "data/chips/ca_bc/v1"
    assignments: str = "data/splits/ca_bc/v1/assignments.csv"
    epochs: int = 70
    warmup_epochs: int = 5
    early_stopping_patience: int = 0
    early_stopping_min_delta: float = 0.0
    checkpoint_epochs: tuple[int, ...] = ()
    seed: int = 42
    learning_rate: float = 3e-4
    min_lr: float = 3e-5
    betas: tuple[float, float] = (0.9, 0.95)
    weight_decay: float = 0.01
    train_draws_per_epoch: int | None = None
    batch_size: int = 3
    accumulate_grad_batches: int = 8
    gradient_clip_val: float = 0.8
    accelerator: str = "cuda"
    precision: str = "bf16-mixed"
    deterministic: bool = True
    encoder_name: str = "mit_b3"
    encoder_weights: str | None = "imagenet"
    num_workers: int = 8
    pin_memory: bool = True
    persistent_workers: bool = True
    limit_train_batches: int | float = 1.0
    limit_val_batches: int | float = 1.0
    wandb: bool = False
    losses: tuple[LossTerm, ...] = DEFAULT_LOSSES

    def __post_init__(self) -> None:
        """Validate recipe fields and loss terms; raise ValueError on input mistakes."""
        validate_losses(self.losses)
        if not isinstance(self.name, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*", self.name
        ):
            raise ValueError(
                "name must start with a letter or digit and use only letters, digits, '.', '_' or '-'."
            )
        if self.experiment != "baseline":
            raise ValueError(
                "Only experiment = 'baseline' is supported here; LORO requires fold-specific normalization and is not supported by this command yet."
            )
        if self.variant not in ("base", "augmented"):
            raise ValueError("variant must be 'base' or 'augmented'.")
        if (
            not isinstance(self.band_names, tuple)
            or len(self.band_names) not in (3, 4, 8)
            or any(not isinstance(name, str) for name in self.band_names)
            or len(set(self.band_names)) != len(self.band_names)
            or any(name not in BAND_NAMES for name in self.band_names)
        ):
            raise ValueError(
                "band_names must contain 3, 4 or 8 distinct native band names."
            )
        indices = [BAND_NAMES.index(name) for name in self.band_names]
        if (
            self.clip_value != CLIP_VALUE
            or self.mean != tuple(MEAN[index] for index in indices)
            or self.std != tuple(STD[index] for index in indices)
        ):
            raise ValueError(
                "Use the approved clip_value, mean and std in band_names order."
            )
        for name in ("epochs", "batch_size", "accumulate_grad_batches"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
        if self.train_draws_per_epoch is not None and (
            type(self.train_draws_per_epoch) is not int
            or self.train_draws_per_epoch < 1
        ):
            raise ValueError("train_draws_per_epoch must be a positive integer.")
        if (
            not isinstance(self.checkpoint_epochs, tuple)
            or any(
                type(epoch) is not int or not 1 <= epoch <= self.epochs
                for epoch in self.checkpoint_epochs
            )
            or tuple(sorted(set(self.checkpoint_epochs))) != self.checkpoint_epochs
        ):
            raise ValueError(
                "checkpoint_epochs must be sorted, unique epoch numbers in 1..epochs."
            )
        for name in ("warmup_epochs", "num_workers", "seed", "early_stopping_patience"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer.")
        if self.warmup_epochs >= self.epochs:
            raise ValueError("warmup_epochs must be smaller than epochs.")
        for name in (
            "learning_rate",
            "min_lr",
            "weight_decay",
            "gradient_clip_val",
            "early_stopping_min_delta",
        ):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be a finite nonnegative number.")
        if not self.learning_rate > 0 or self.min_lr > self.learning_rate:
            raise ValueError("Require 0 < learning_rate and min_lr <= learning_rate.")
        if (
            not isinstance(self.betas, tuple)
            or len(self.betas) != 2
            or any(type(v) not in (int, float) or not 0 <= v < 1 for v in self.betas)
        ):
            raise ValueError("betas must contain two numbers in [0, 1).")
        for name in ("pin_memory", "persistent_workers", "wandb", "deterministic"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be true or false.")
        if self.persistent_workers and self.num_workers == 0:
            raise ValueError("persistent_workers requires num_workers > 0.")
        if self.accelerator not in ("cpu", "cuda"):
            raise ValueError("accelerator must be 'cpu' or 'cuda'.")
        if self.precision not in ("32-true", "bf16-mixed"):
            raise ValueError("precision must be '32-true' or 'bf16-mixed'.")
        if self.accelerator == "cpu" and self.precision != "32-true":
            raise ValueError("CPU smoke recipes require precision = '32-true'.")
        if self.encoder_name not in SUPPORTED_ENCODERS:
            raise ValueError(f"encoder_name must be one of {SUPPORTED_ENCODERS}.")
        if self.encoder_weights not in (None, "imagenet"):
            raise ValueError("encoder_weights must be 'imagenet' or 'none'.")
        for name in ("limit_train_batches", "limit_val_batches"):
            value = getattr(self, name)
            if not (
                (type(value) is int and value > 0)
                or (type(value) is float and 0 < value <= 1)
            ):
                raise ValueError(
                    f"{name} must be a positive integer or fraction in (0, 1]."
                )
        for name in ("paths_file", "chips", "assignments"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty path string.")


def load_settings(path: str | Path) -> TrainingSettings:
    """Load strict TOML; resolve paths_file relative to this recipe, not the shell."""
    path = Path(path).expanduser()
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"Cannot read training recipe {path}: {error}") from error
    unknown = document.keys() - {field.name for field in fields(TrainingSettings)}
    if unknown:
        raise ValueError(f"Unknown training settings: {', '.join(sorted(unknown))}.")
    for name in ("band_names", "mean", "std", "betas", "checkpoint_epochs"):
        if name in document:
            if not isinstance(document[name], list):
                raise ValueError(f"{name} must be a TOML array.")
            document[name] = tuple(document[name])
    if document.get("encoder_weights") == "none":
        document["encoder_weights"] = None
    if "losses" in document:
        document["losses"] = parse_losses(document["losses"])
    settings = TrainingSettings(**document)
    paths_file = Path(settings.paths_file).expanduser()
    if not paths_file.is_absolute():
        paths_file = path.parent / paths_file
    return replace(settings, paths_file=str(paths_file.resolve()))
