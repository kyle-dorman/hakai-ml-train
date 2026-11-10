"""Weighted standard binary objectives with one shared ignored-pixel contract."""

import torch
import torch.nn.functional as F
from segmentation_models_pytorch.losses import (
    DiceLoss,
    FocalLoss,
    JaccardLoss,
    LovaszLoss,
    TverskyLoss,
)
from torch import nn

from kelpseg.training.loss_settings import (
    DEFAULT_LOSSES,
    DISTANCE_CAP_M,
    LossTerm,
    validate_losses,
)

BCE_TYPES = ("bce", "boundary_bce", "distance_bce")


def binary_targets(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Check the binary tensor layout and return targets as BHW."""
    if logits.ndim != 4 or logits.shape[1] != 1:
        raise ValueError("Logits must have shape (batch, 1, height, width).")
    if targets.ndim == 4 and targets.shape[1] == 1:
        targets = targets[:, 0]
    if targets.shape != logits[:, 0].shape:
        raise ValueError("Targets must match logits with shape BHW or B1HW.")
    if not torch.all((targets == 0) | (targets == 1) | (targets == -100)):
        raise ValueError("Targets must contain only background 0, kelp 1, or -100.")
    return targets


def boundary_weights(targets: torch.Tensor, radius: int, factor: float) -> torch.Tensor:
    """Return BHW BCE weights emphasizing observed foreground/background transitions.

    targets is BHW with 0/1/-100. Pixels whose square radius neighborhood contains
    both classes get factor; others get 1. Neighborhoods touching ignored pixels
    or image edges receive no boost, so nodata/padding cannot invent boundaries.
    The caller masks ignored pixels and normalizes by the sum of valid weights.
    """
    kernel = 2 * radius + 1
    foreground = (targets == 1).float()[:, None]
    background = (targets == 0).float()[:, None]
    near_foreground = F.max_pool2d(foreground, kernel, stride=1, padding=radius) > 0
    near_background = F.max_pool2d(background, kernel, stride=1, padding=radius) > 0
    unknown = F.pad((targets == -100).float()[:, None], (radius,) * 4, value=1)
    observed = F.max_pool2d(unknown, kernel, stride=1) == 0
    edge = (near_foreground & near_background & observed)[:, 0]
    return 1 + (factor - 1) * edge.float()


def distance_weights(
    targets: torch.Tensor,
    distance_m: torch.Tensor,
    alpha: float,
    half_distance_m: float,
) -> torch.Tensor:
    """Return float32 BCE weights for hard positives with known effective distance.

    Land is already represented by zero; negative and nonfinite distances are
    unknown. Ignore pixels get zero. No input is modified.
    """
    distance = distance_m.float()
    known_positive = (targets == 1) & torch.isfinite(distance) & (distance >= 0)
    safe = torch.where(known_positive, distance.clamp(max=DISTANCE_CAP_M), 0)
    boost = alpha * torch.exp2(-safe / half_distance_m)
    return torch.where(targets == -100, 0, 1 + torch.where(known_positive, boost, 0))


def build_loss(term: LossTerm) -> nn.Module:
    """Construct one PyTorch/SMP loss from its type and library-specific options.

    Shared binary/logit conventions stay fixed. Pooling, BCE weighting and
    Tversky's safe exponent are applied by BinaryObjective, outside the module.
    """
    parameters = dict(term.parameters)
    parameters.pop("per_image")
    if term.type in BCE_TYPES:
        return nn.BCEWithLogitsLoss(
            reduction="none",
            pos_weight=None
            if parameters["pos_weight"] == 1
            else torch.tensor(parameters["pos_weight"]),
        )
    if term.type == "lovasz":
        return LovaszLoss(mode="binary", per_image=False)
    if term.type == "dice":
        return DiceLoss(mode="binary", **parameters)
    if term.type == "jaccard":
        return JaccardLoss(mode="binary", **parameters)
    if term.type == "focal":
        return FocalLoss(mode="binary", **parameters)
    parameters.pop("gamma")
    return TverskyLoss(mode="binary", **parameters)


class BinaryObjective(nn.Module):
    """Weighted scalar losses with independent names and explicit pooling choices."""

    def __init__(self, terms: tuple[LossTerm, ...] = DEFAULT_LOSSES) -> None:
        """Build loss modules once in term order; names are independent log identifiers."""
        super().__init__()
        validate_losses(terms)
        self.terms = terms
        self.components = nn.ModuleList([build_loss(term) for term in terms])

    def _component(
        self,
        term: LossTerm,
        module: nn.Module,
        logits: torch.Tensor,
        targets: torch.Tensor,
        distance_m: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        """Return the reduced term and, for distance BCE, ordinary BCE for logging.

        Inputs retain image geometry until boundary weights are computed. Only
        valid pixels then enter SMP/PyTorch. Caller chooses a whole microbatch
        or one image; no input is modified. Arithmetic is already float32.
        """
        valid = targets != -100
        prediction = logits[valid].reshape(1, 1, 1, -1)
        truth = targets[valid].float().reshape_as(prediction)
        parameters = term.parameters
        target = truth
        if term.type in BCE_TYPES:
            smoothing = parameters["smoothing"]
            target = truth * (1 - smoothing) + smoothing / 2
        value = module(prediction, target)

        if term.type == "distance_bce":
            if distance_m is None:
                raise ValueError("distance_bce requires aligned effective distances.")
            ordinary = value.mean()
            alpha = parameters["alpha"]
            if alpha == 0:
                return ordinary, ordinary.detach()

            weights = distance_weights(
                truth,
                distance_m[valid].reshape_as(value),
                alpha,
                parameters["half_distance_m"],
            )
            return (value * weights).sum() / weights.sum(), ordinary.detach()

        if term.type == "bce":
            return (
                value.mean() if parameters["reduction"] == "mean" else value.sum()
            ), None

        if term.type == "boundary_bce":
            weights = boundary_weights(
                targets, parameters["radius"], parameters["factor"]
            )[valid].reshape_as(value)
            weighted = (value * weights).sum()
            if parameters["reduction"] == "sum":
                return weighted, None
            denominator = (
                weights.sum()
                if parameters["normalization"] == "weights"
                else weights.numel()
            )
            return weighted / denominator, None

        if term.type in ("tversky", "focal_tversky"):
            # SMP uses gamma itself, not 1/gamma. Define zero-loss gradients
            # as zero, including fractional exponents with a singular derivative.
            positive = value > 0
            base = torch.where(positive, value, torch.ones_like(value))
            value = torch.where(positive, base ** parameters["gamma"], value)

        return value, None

    def forward(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        distance_m: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """Return the combined objective and components before term multipliers.

        logits is B1HW; targets is BHW/B1HW with 0/1/-100. Each term either pools
        the whole microbatch or averages separately reduced image losses, excluding
        all-ignored images. Preserve image identity before masking. All arithmetic
        is float32; an entirely ignored batch returns differentiable zero. Loss
        weights are literal multipliers. Distance BCE requires effective distances
        shaped BHW and includes an ordinary BCE component for logging only.
        Inputs are left intact.
        """
        targets = binary_targets(logits, targets)
        if distance_m is not None and distance_m.shape != targets.shape:
            raise ValueError("Effective distances must match BHW targets.")
        with torch.autocast(device_type=logits.device.type, enabled=False):
            values = logits[:, 0].float()
            if not (targets != -100).any():
                zero = values.sum() * 0
                components = {term.name: zero for term in self.terms}
                components.update(
                    {
                        f"{term.name}_unweighted": zero
                        for term in self.terms
                        if term.type == "distance_bce"
                    }
                )
                return zero, components
            components = {}
            for term, module in zip(self.terms, self.components, strict=True):
                if term.parameters["per_image"]:
                    image_losses = [
                        self._component(term, module, image[None], target[None])[0]
                        for image, target in zip(values, targets, strict=True)
                        if (target != -100).any()
                    ]
                    value = torch.stack(image_losses).mean()
                else:
                    value, ordinary = self._component(
                        term, module, values, targets, distance_m
                    )
                    if ordinary is not None:
                        components[f"{term.name}_unweighted"] = ordinary
                components[term.name] = value
            total = sum(term.weight * components[term.name] for term in self.terms)
        return total, components
