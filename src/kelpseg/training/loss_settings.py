"""Typed loss construction settings, independent of training and tensor libraries."""

import math
import re
from dataclasses import dataclass, field
from typing import Any

type LossParameter = int | float | bool | str | None

OVERLAP_PARAMETERS: dict[str, LossParameter] = {
    "smooth": 0.0,
    "eps": 1e-7,
    "log_loss": False,
    "per_image": False,
}
DEFAULT_PARAMETERS: dict[str, dict[str, LossParameter]] = {
    "bce": {
        "smoothing": 0.0,
        "pos_weight": 1.0,
        "reduction": "mean",
        "per_image": False,
    },
    "boundary_bce": {
        "smoothing": 0.0,
        "pos_weight": 1.0,
        "radius": 1,
        "factor": 2.0,
        "normalization": "weights",
        "reduction": "mean",
        "per_image": False,
    },
    "lovasz": {"per_image": False},
    "dice": dict(OVERLAP_PARAMETERS),
    "jaccard": dict(OVERLAP_PARAMETERS),
    "focal": {
        "alpha": None,
        "gamma": 2.0,
        "normalized": False,
        "reduced_threshold": None,
        "reduction": "mean",
        "per_image": False,
    },
    "tversky": {**OVERLAP_PARAMETERS, "alpha": 0.5, "beta": 0.5, "gamma": 1.0},
    "focal_tversky": {**OVERLAP_PARAMETERS, "alpha": 0.5, "beta": 0.5, "gamma": 2.0},
}
# Avoid collisions with existing phase metrics and their step counterparts.
RESERVED_NAMES = {"loss", "iou", "precision", "recall", "f1", "accuracy", "pixels"}


@dataclass(frozen=True)
class LossTerm:
    """A loss implementation type, independent log name, multiplier and parameters."""

    type: str
    name: str | None = None
    weight: float = 1.0
    parameters: dict[str, LossParameter] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Resolve omitted name/default parameters and validate ordinary recipe mistakes."""
        if not isinstance(self.type, str) or self.type not in DEFAULT_PARAMETERS:
            raise ValueError(
                f"Unknown loss type {self.type!r}; choose {', '.join(DEFAULT_PARAMETERS)}."
            )
        name = self.type if self.name is None else self.name
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError(
                "Loss name must use lowercase letters, digits and underscores, starting with a letter."
            )
        if name in RESERVED_NAMES or name.endswith("_step"):
            raise ValueError(
                f"Loss name {name!r} collides with training metrics; choose another name."
            )
        if (
            type(self.weight) not in (int, float)
            or not math.isfinite(self.weight)
            or self.weight <= 0
        ):
            raise ValueError(
                "Loss weight must be finite and positive; omit disabled terms."
            )
        if not isinstance(self.parameters, dict):
            raise ValueError(f"{name}.parameters must be a TOML table.")
        defaults = DEFAULT_PARAMETERS[self.type]
        unknown = self.parameters.keys() - defaults.keys()
        if unknown:
            raise ValueError(
                f"Unknown {self.type} loss parameters: {', '.join(sorted(unknown))}."
            )
        parameters = defaults | self.parameters
        validate_parameters(self.type, parameters)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "parameters", parameters)


def validate_parameters(loss_type: str, parameters: dict[str, LossParameter]) -> None:
    """Validate resolved options for one supported type; return nothing or raise ValueError."""
    for name, value in parameters.items():
        if name in ("per_image", "log_loss", "normalized"):
            if type(value) is not bool:
                raise ValueError(f"{loss_type}.{name} must be true or false.")
            continue
        if name in ("reduction", "normalization"):
            choices = ("mean", "sum") if name == "reduction" else ("weights", "pixels")
            if value not in choices:
                raise ValueError(f"{loss_type}.{name} must be one of {choices}.")
            continue
        if (
            value is None
            and name in ("alpha", "reduced_threshold")
            and loss_type == "focal"
        ):
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{loss_type}.{name} must be a finite nonnegative number.")
        if name == "smoothing" and value >= 1:
            raise ValueError("BCE smoothing must be in [0, 1).")
        if name in ("alpha", "beta") and value > 1:
            raise ValueError(f"{loss_type}.{name} must be in [0, 1].")
        if name in ("eps", "pos_weight", "reduced_threshold") and value <= 0:
            raise ValueError(f"{loss_type}.{name} must be positive.")
        if name == "reduced_threshold" and value >= 1:
            raise ValueError("focal.reduced_threshold must be in (0, 1).")
        if name == "gamma" and loss_type in ("tversky", "focal_tversky") and value <= 0:
            raise ValueError(f"{loss_type}.gamma must be positive.")
        if name == "radius" and (type(value) is not int or value < 1):
            raise ValueError(
                "boundary_bce.radius must be a positive integer in pixels."
            )
        if name == "factor" and value < 1:
            raise ValueError("boundary_bce.factor must be >= 1.")
    if (
        loss_type in ("tversky", "focal_tversky")
        and parameters["alpha"] + parameters["beta"] == 0
    ):
        raise ValueError("Tversky alpha and beta cannot both be zero.")
    if (
        loss_type == "focal"
        and parameters["reduced_threshold"] is not None
        and parameters["reduction"] != "sum"
    ):
        raise ValueError(
            "Reduced focal loss requires reduction = 'sum', following SMP."
        )


DEFAULT_LOSSES = (
    LossTerm("bce", weight=0.7, parameters={"smoothing": 0.1}),
    LossTerm("lovasz", weight=0.3),
)


def validate_losses(terms: tuple[LossTerm, ...]) -> None:
    """Require a nonempty tuple with unique logging names; repeated types are allowed."""
    if (
        not isinstance(terms, tuple)
        or not terms
        or any(not isinstance(term, LossTerm) for term in terms)
    ):
        raise ValueError("losses must contain at least one LossTerm.")
    if len({term.name for term in terms}) != len(terms):
        raise ValueError(
            "Loss names must be unique within a recipe; repeated types need distinct names."
        )


def parse_losses(value: Any) -> tuple[LossTerm, ...]:
    """Parse TOML loss tables with type/name/weight/parameters into resolved terms.

    type is required; name defaults to type and weight to 1. Unknown fields and
    invalid parameters raise ValueError before data loading or training starts.
    """
    if not isinstance(value, list):
        raise ValueError("losses must be TOML [[losses]] tables.")
    terms = []
    for row in value:
        if not isinstance(row, dict) or "type" not in row:
            raise ValueError("Each [[losses]] table requires a type.")
        unknown = row.keys() - {"type", "name", "weight", "parameters"}
        if unknown:
            raise ValueError(f"Unknown loss settings: {', '.join(sorted(unknown))}.")
        terms.append(LossTerm(**row))
    result = tuple(terms)
    validate_losses(result)
    return result
