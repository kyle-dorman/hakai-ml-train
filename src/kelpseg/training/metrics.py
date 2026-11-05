"""Native TorchMetrics accumulation for pooled binary agreement."""

from torchmetrics import MetricCollection
from torchmetrics.classification import (
    BinaryConfusionMatrix,
    BinaryF1Score,
    BinaryJaccardIndex,
    BinaryPrecision,
    BinaryRecall,
)


def build_metrics(*, include_confusion: bool = True) -> MetricCollection:
    """Build stateful metrics that pool pixels across every ``update`` call.

    Pass integer predictions ``(logits[:, 0] >= 0).long()`` and BHW targets
    to ``update``. Explicit predictions preserve the fixed probability >= 0.5
    boundary and avoid the library's automatic logits/probability detection.
    Call ``compute`` once for the full scope, then ``reset`` before reuse.

    All metrics ignore -100. Undefined ratios use the library's zero value;
    inspect confusion_matrix.sum() to distinguish no support from poor scores.
    The unnormalized confusion matrix is [[tn, fp], [fn, tp]]. Set
    include_confusion=False for scalar loggers; Lightning can log that collection
    directly and owns its epoch computation and reset.
    """
    metrics = {
        "iou": BinaryJaccardIndex(ignore_index=-100, zero_division=0),
        "precision": BinaryPrecision(ignore_index=-100),
        "recall": BinaryRecall(ignore_index=-100),
        "f1": BinaryF1Score(ignore_index=-100, zero_division=0),
    }
    if include_confusion:
        metrics["confusion_matrix"] = BinaryConfusionMatrix(ignore_index=-100)
    return MetricCollection(metrics)
