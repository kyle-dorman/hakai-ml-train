"""Overlap-aware PlanetScope chip prediction reconstruction and metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

IGNORE_INDEX = -100
EVALUATION_SCHEMA_VERSION = 1
ALL_RETAINED_EVALUATION_SCHEMA_VERSION = 3
SELECTED_NONOVERLAP_SCOPE = "selected_nonoverlap"
ALL_RETAINED_TEST_SCOPE = "all_retained_test_chips"
EVALUATION_SCOPES = (SELECTED_NONOVERLAP_SCOPE, ALL_RETAINED_TEST_SCOPE)


class EvaluationError(ValueError):
    """Raised when prediction or source-grid identity is invalid."""


def evaluation_schema_version(scope: str) -> int:
    """Return the durable schema version for one explicit evaluation scope."""
    if scope == SELECTED_NONOVERLAP_SCOPE:
        return EVALUATION_SCHEMA_VERSION
    if scope == ALL_RETAINED_TEST_SCOPE:
        return ALL_RETAINED_EVALUATION_SCHEMA_VERSION
    raise EvaluationError(f"Unknown evaluation scope: {scope}")


def select_evaluation_rows(
    rows: list[dict[str, str]],
    *,
    scope: str,
    held_out_region: str | None,
) -> list[dict[str, str]]:
    """Select fold rows for a strict, identity-bearing evaluation scope."""
    evaluation_schema_version(scope)
    if scope == SELECTED_NONOVERLAP_SCOPE:
        return [
            row
            for row in rows
            if row["experiment_split"] == "test" and row["selected"].lower() == "true"
        ]

    selected: list[dict[str, str]] = []
    if held_out_region is None:
        candidates = [row for row in rows if row["source_temporal_split"] == "TEST"]
        allowed = {
            ("test", "true", "selected"),
            ("", "false", "test_overlap_exclusion"),
        }
    else:
        candidates = [row for row in rows if row["region_id"] == held_out_region]
        allowed = {
            ("test", "true", "held_out_region_test"),
            ("", "false", "held_out_region_overlap_exclusion"),
        }
    for row in candidates:
        identity = (
            row["experiment_split"],
            row["selected"].lower(),
            row["selection_reason"],
        )
        if identity not in allowed:
            raise EvaluationError(
                "Unexpected fold row in all-retained test scope: "
                f"chip_id={row['chip_id']} identity={identity}"
            )
        selected.append(row)
    return selected


@dataclass
class SourceAccumulator:
    """Accumulate chip probabilities onto one unique source pixel grid."""

    height: int
    width: int

    def __post_init__(self) -> None:
        if self.height <= 0 or self.width <= 0:
            raise EvaluationError("Source dimensions must be positive")
        self.probability_sum = np.zeros((self.height, self.width), dtype=np.float32)
        self.coverage_count = np.zeros((self.height, self.width), dtype=np.uint16)
        self.label = np.full((self.height, self.width), IGNORE_INDEX, dtype=np.int16)

    def add(
        self,
        probability: np.ndarray,
        label: np.ndarray,
        *,
        row_off: int,
        col_off: int,
    ) -> None:
        """Add one true-size chip and fail if its known labels conflict."""
        if probability.ndim != 2 or label.ndim != 2 or probability.shape != label.shape:
            raise EvaluationError("Probability and label must be matching 2D arrays")
        height, width = probability.shape
        if (
            row_off < 0
            or col_off < 0
            or row_off + height > self.height
            or col_off + width > self.width
        ):
            raise EvaluationError("Chip window falls outside the declared source grid")
        if not np.isfinite(probability).all():
            raise EvaluationError("Prediction probabilities must be finite")
        if (probability < 0).any() or (probability > 1).any():
            raise EvaluationError("Prediction probabilities must be in [0, 1]")
        window = np.s_[row_off : row_off + height, col_off : col_off + width]
        known = self.label[window]
        incoming_known = label != IGNORE_INDEX
        conflict = (known != IGNORE_INDEX) & incoming_known & (known != label)
        if conflict.any():
            raise EvaluationError(
                "Conflicting non-ignore ground-truth labels in overlapping chips"
            )
        replacement = (known == IGNORE_INDEX) & incoming_known
        known[replacement] = label[replacement]
        self.label[window] = known
        self.probability_sum[window] += probability.astype(np.float32, copy=False)
        if np.any(self.coverage_count[window] == np.iinfo(np.uint16).max):
            raise EvaluationError("Coverage count exceeds uint16 capacity")
        self.coverage_count[window] += 1

    def finalize(self, threshold: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return averaged probabilities, thresholded mask, and coverage mask."""
        if not 0 <= threshold <= 1:
            raise EvaluationError("Threshold must be in [0, 1]")
        covered = self.coverage_count > 0
        probability = np.full(self.label.shape, np.nan, dtype=np.float32)
        probability[covered] = (
            self.probability_sum[covered] / self.coverage_count[covered]
        )
        mask = np.zeros(self.label.shape, dtype=np.uint8)
        mask[covered] = (probability[covered] >= threshold).astype(np.uint8)
        return probability, mask, covered


def safe_ratio(numerator: int, denominator: int) -> float | None:
    """Return an explicitly undefined metric as ``None`` instead of a fake zero."""
    return None if denominator == 0 else numerator / denominator


def binary_metrics(
    label: np.ndarray,
    mask: np.ndarray,
    covered: np.ndarray,
) -> dict[str, int | float | None]:
    """Score unique covered non-ignore pixels and derive binary kelp metrics."""
    if label.shape != mask.shape or label.shape != covered.shape:
        raise EvaluationError(
            "Label, mask, and coverage arrays must have the same shape"
        )
    if not np.isin(mask, (0, 1)).all():
        raise EvaluationError("Binary mask must contain only 0 and 1")
    if np.any((label != 0) & (label != 1) & (label != IGNORE_INDEX)):
        raise EvaluationError("Labels must be 0, 1, or the ignore index")
    valid = label != IGNORE_INDEX
    scored = covered & valid
    truth, prediction = label[scored], mask[scored]
    true_negative = int(np.count_nonzero((truth == 0) & (prediction == 0)))
    false_positive = int(np.count_nonzero((truth == 0) & (prediction == 1)))
    false_negative = int(np.count_nonzero((truth == 1) & (prediction == 0)))
    true_positive = int(np.count_nonzero((truth == 1) & (prediction == 1)))
    # Uncovered pixels are a separate accounting category, even when no label
    # window supplied their truth value.
    ignored = int(np.count_nonzero(covered & ~valid))
    uncovered = int(np.count_nonzero(~covered))
    covered_count = int(np.count_nonzero(covered))
    scored_count = int(np.count_nonzero(scored))
    total = int(label.size)
    kelp_precision = safe_ratio(true_positive, true_positive + false_positive)
    kelp_recall = safe_ratio(true_positive, true_positive + false_negative)
    kelp_f1 = safe_ratio(
        2 * true_positive, 2 * true_positive + false_positive + false_negative
    )
    kelp_iou = safe_ratio(
        true_positive, true_positive + false_positive + false_negative
    )
    background_iou = safe_ratio(
        true_negative, true_negative + false_positive + false_negative
    )
    macro_iou = (
        None
        if kelp_iou is None or background_iou is None
        else (kelp_iou + background_iou) / 2
    )
    return {
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_positive": true_positive,
        "ignored_pixel_count": ignored,
        "uncovered_pixel_count": uncovered,
        "covered_pixel_count": covered_count,
        "scored_pixel_count": scored_count,
        "total_source_pixel_count": total,
        "accuracy": safe_ratio(true_positive + true_negative, scored_count),
        "kelp_precision": kelp_precision,
        "kelp_recall": kelp_recall,
        "kelp_f1": kelp_f1,
        "kelp_iou": kelp_iou,
        "background_iou": background_iou,
        "macro_iou": macro_iou,
        "dice": kelp_f1,
    }


def sum_confusion(rows: list[dict[str, Any]]) -> dict[str, int | float | None]:
    """Pool TIFF metrics by summing unique-pixel counts before deriving metrics."""
    count_keys = (
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
        "ignored_pixel_count",
        "uncovered_pixel_count",
        "covered_pixel_count",
        "scored_pixel_count",
        "total_source_pixel_count",
    )
    totals = {key: sum(int(row[key]) for row in rows) for key in count_keys}
    # Reuse the exact zero-denominator formulas without reconstructing all pixels.
    tn, fp, fn, tp = (totals[key] for key in count_keys[:4])
    kelp_iou = safe_ratio(tp, tp + fp + fn)
    background_iou = safe_ratio(tn, tn + fp + fn)
    totals.update(
        accuracy=safe_ratio(tp + tn, totals["scored_pixel_count"]),
        kelp_precision=safe_ratio(tp, tp + fp),
        kelp_recall=safe_ratio(tp, tp + fn),
        kelp_f1=safe_ratio(2 * tp, 2 * tp + fp + fn),
        kelp_iou=kelp_iou,
        background_iou=background_iou,
        macro_iou=None
        if kelp_iou is None or background_iou is None
        else (kelp_iou + background_iou) / 2,
        dice=safe_ratio(2 * tp, 2 * tp + fp + fn),
    )
    return totals
