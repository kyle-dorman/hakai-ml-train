"""The approved binary objective, with explicit ignored-pixel support."""

import torch
import torch.nn.functional as F
from segmentation_models_pytorch.losses import LovaszLoss


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


def segmentation_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """0.7 BCE (0.1 label smoothing) + 0.3 batch-pooled Lovasz hinge.

    Ignore -100 in both terms. Entirely ignored batches return differentiable
    zero with zero gradients; they contribute no evidence to the objective.
    Lovasz uses hard binary labels, matching the retained baseline objective.
    """
    targets = binary_targets(logits, targets)
    valid = targets != -100
    if not valid.any():
        return logits.sum() * 0
    smoothed = targets[valid].to(logits.dtype) * 0.9 + 0.05
    bce = F.binary_cross_entropy_with_logits(logits[:, 0][valid], smoothed)
    lovasz = LovaszLoss(mode="binary", ignore_index=-100, per_image=False)(
        logits, targets
    )
    return 0.7 * bce + 0.3 * lovasz
