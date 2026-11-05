"""Bounded-memory probability metrics for full-resolution segmentation epochs."""

import torch
from torch import Tensor
from torchmetrics import Metric, MetricCollection
from torchmetrics.classification import BinaryAUROC


class BinnedBinaryAUROC(BinaryAUROC):
    """Keep TorchMetrics AUROC computation; replace only its threshold-count update.

    The installed library scans large pixel arrays once per threshold. Histogram
    updates avoid that repeated work. Parity tests cover its threshold semantics
    and confusion-state layout; keep those tests when upgrading TorchMetrics.
    """

    def __init__(self) -> None:
        """Use 257 uniform probability thresholds and ignore label -100."""
        super().__init__(thresholds=257, ignore_index=-100)

    def update(self, preds: Tensor, target: Tensor) -> None:
        """Accumulate exact threshold counts from aligned probability/label arrays.

        Inputs are probabilities in [0,1] and 0/1/-100 labels. Each pixel enters
        one histogram bin; cumulative sums recover all >= threshold counts.
        State size is independent of pixel count. No input is modified.
        """
        valid = target != -100
        probability, truth = preds[valid], target[valid]
        index = torch.bucketize(probability.contiguous(), self.thresholds, right=True)
        bins = self.thresholds.numel() + 1
        positive = torch.bincount(index[truth == 1], minlength=bins)
        negative = torch.bincount(index[truth == 0], minlength=bins)
        tp = positive[1:].flip(0).cumsum(0).flip(0)
        fp = negative[1:].flip(0).cumsum(0).flip(0)
        self.confmat += torch.stack(
            (negative.sum() - fp, fp, positive.sum() - tp, tp), dim=1
        ).reshape(-1, 2, 2)


class StreamingBinaryCalibrationError(Metric):
    """L1 BinaryCalibrationError equivalent using fixed sufficient statistics.

    Match TorchMetrics' 15 uniform bins and separate probability=1 endpoint.
    Binary calibration compares mean kelp probability to the foreground fraction
    in each bin. Float64 sums avoid loss of precision over large pixel counts.
    Stock BinaryCalibrationError keeps every probability and label until compute;
    this Metric retains only sufficient statistics for the same L1 definition.
    """

    higher_is_better: bool = False
    is_differentiable: bool = False
    full_state_update: bool = False
    counts: Tensor
    probability_sum: Tensor
    positive_sum: Tensor

    def __init__(self) -> None:
        """Register bin counts, probability sums and label sums; no pixel lists."""
        super().__init__()
        self.register_buffer("boundaries", torch.linspace(0, 1, 16), persistent=False)
        for name in ("counts", "probability_sum", "positive_sum"):
            self.add_state(
                name, default=torch.zeros(16, dtype=torch.float64), dist_reduce_fx="sum"
            )

    def update(self, preds: Tensor, target: Tensor) -> None:
        """Accumulate aligned [0,1] probabilities and 0/1 labels, excluding -100."""
        valid = target != -100
        probability, truth = preds[valid], target[valid]
        index = (
            torch.bucketize(probability.contiguous(), self.boundaries, right=True) - 1
        )
        self.counts += torch.bincount(index, minlength=16)
        self.probability_sum.scatter_add_(0, index, probability.double())
        self.positive_sum.scatter_add_(0, index, truth.double())

    def compute(self) -> Tensor:
        """Return pooled expected calibration error; return NaN for no support."""
        return (
            self.probability_sum - self.positive_sum
        ).abs().sum() / self.counts.sum()


def build_probability_metrics() -> MetricCollection:
    """Return epoch AUROC and L1 calibration metrics for explicit probabilities.

    AUROC is approximated on 257 thresholds; calibration uses 15 bins and exactly
    matches the library bin definition. Never pass hard predictions or logits.
    Lightning owns logging/reset. Undefined calibration support returns NaN;
    AUROC retains TorchMetrics' absent-class convention.
    """
    return MetricCollection(
        {
            "auroc": BinnedBinaryAUROC(),
            "calibration_error": StreamingBinaryCalibrationError(),
        },
        compute_groups=False,
    )
