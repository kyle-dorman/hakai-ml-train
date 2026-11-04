"""Validation diagnostics on observed source pixels; gaps are never background."""

from typing import NotRequired, TypedDict

import cv2
import numpy as np
from numpy.typing import NDArray


class PatchRow(TypedDict):
    """One observed label component, in canvas pixels unless offset by the caller."""

    patch: int
    row: int
    col: int
    height: int
    width: int
    pixels: int
    recovered_pixels: int
    pixel_recall: float
    no_overlap: bool
    truncated: bool
    size_bin: str
    area_m2: NotRequired[float]


class Analysis(TypedDict):
    """Source diagnostic tables before identity columns and aggregation."""

    counts: dict[str, int]
    sweep: list[dict[str, int | float]]
    boundaries: list[dict[str, int]]
    zones: list[dict[str, str | int]]
    patches: list[PatchRow]
    histograms: list[dict[str, str | int | float]]


THRESHOLDS = tuple(value / 10 for value in range(1, 10))
COUNT_KEYS = ("tp", "fp", "fn", "tn")
PATCH_BINS = (
    ("1-10", 10),
    ("11-100", 100),
    ("101-1000", 1000),
    (">1000", float("inf")),
)


def ratio(numerator: int | float, denominator: int | float) -> float | None:
    """Divide two numeric counts; return None when the denominator is zero."""
    return numerator / denominator if denominator else None


def scores(counts: dict[str, int]) -> dict[str, int | float | None]:
    """Return counts plus pixel scores and signed area bias from TP/FP/FN/TN.

    Input counts must describe the same observed support. Ratios with zero
    denominators are None; area bias is predicted minus labeled pixel count.
    """
    tp, fp, fn, tn = (counts[key] for key in COUNT_KEYS)
    return dict(
        **counts,
        pixels=tp + fp + fn + tn,
        error_pixels=fp + fn,
        pixel_error_rate=ratio(fp + fn, tp + fp + fn + tn),
        iou=ratio(tp, tp + fp + fn),
        precision=ratio(tp, tp + fp),
        recall=ratio(tp, tp + fn),
        labeled_kelp_pixels=tp + fn,
        predicted_kelp_pixels=tp + fp,
        area_bias_pixels=fp - fn,
        relative_area_bias=ratio(fp - fn, tp + fn),
        background_false_positive_rate=ratio(fp, fp + tn),
    )


def confusion(
    label: NDArray[np.bool_], predicted: NDArray[np.bool_], valid: NDArray[np.bool_]
) -> dict[str, int]:
    """Count TP/FP/FN/TN from aligned HW masks, excluding valid=False pixels."""
    return dict(
        tp=int((label & predicted & valid).sum()),
        fp=int((~label & predicted & valid).sum()),
        fn=int((label & ~predicted & valid).sum()),
        tn=int((~label & ~predicted & valid).sum()),
    )


def erode(mask: NDArray[np.bool_], radius: int) -> NDArray[np.bool_]:
    """Return an HW mask eroded by a square pixel radius; outside is False."""
    kernel = np.ones((2 * radius + 1, 2 * radius + 1), dtype=np.uint8)
    return cv2.erode(
        mask.astype(np.uint8), kernel, borderType=cv2.BORDER_CONSTANT, borderValue=0
    ).astype(bool)


def boundary(mask: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """Return the inner eight-neighbor boundary of an HW foreground mask."""
    return mask & ~erode(mask, 1)


def distance_to(mask: NDArray[np.bool_]) -> NDArray[np.float32]:
    """Return HW Euclidean pixel distances to True pixels, or infinity if empty."""
    if not mask.any():
        return np.full(mask.shape, np.inf, dtype=np.float32)
    return cv2.distanceTransform(
        (~mask).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
    )


def boundary_counts(
    label: NDArray[np.bool_], predicted: NDArray[np.bool_], valid: NDArray[np.bool_]
) -> list[dict[str, int]]:
    """Return contour totals and matched counts at 1/2/3-pixel tolerances.

    Inputs are aligned HW boolean masks. Queries exclude unknown support by
    tolerance + 1 pixels; reference contours need an observed 3x3 neighborhood.
    Counts can be summed across sources before calculating boundary scores.
    """
    # Reference contours require a fully observed 3x3 neighborhood.
    observed = erode(valid, 1)
    truth_reference = boundary(label) & observed
    prediction_reference = boundary(predicted) & observed
    truth_distance = distance_to(truth_reference)
    prediction_distance = distance_to(prediction_reference)
    results = []
    for tolerance in (1, 2, 3):
        # Score interior queries, retaining valid matches outside this margin.
        safe = erode(valid, tolerance + 1)
        truth_edge = truth_reference & safe
        predicted_edge = prediction_reference & safe
        results.append(
            dict(
                tolerance_pixels=tolerance,
                eligible_pixels=int(safe.sum()),
                label_boundary_pixels=int(truth_edge.sum()),
                predicted_boundary_pixels=int(predicted_edge.sum()),
                matched_prediction_pixels=int(
                    (predicted_edge & (truth_distance <= tolerance)).sum()
                ),
                matched_label_pixels=int(
                    (truth_edge & (prediction_distance <= tolerance)).sum()
                ),
            )
        )
    return results


def boundary_scores(counts: dict[str, int]) -> dict[str, int | float | None]:
    """Add precision, recall and F1 to one tolerance's pooled boundary counts.

    Input uses boundary_counts fields. Undefined denominators yield None;
    two defined zero scores yield F1=0. The input dictionary is not mutated.
    """
    precision = ratio(
        counts["matched_prediction_pixels"], counts["predicted_boundary_pixels"]
    )
    recall = ratio(counts["matched_label_pixels"], counts["label_boundary_pixels"])
    f1 = (
        None
        if precision is None or recall is None
        else ratio(2 * precision * recall, precision + recall)
    )
    if precision == 0 and recall == 0:
        f1 = 0.0
    return dict(**counts, precision=precision, recall=recall, f1=f1)


def patch_rows(
    label: NDArray[np.bool_], predicted: NDArray[np.bool_], valid: NDArray[np.bool_]
) -> list[PatchRow]:
    """Describe eight-connected label patches from aligned HW boolean masks.

    Return canvas-relative bounding boxes, sizes and recovered label pixels at
    the supplied prediction threshold. Components touching unknown support or
    the canvas edge are flagged as truncated, not discarded.
    """
    count, components, stats, _ = cv2.connectedComponentsWithStats(
        (label & valid).astype(np.uint8), connectivity=8
    )
    hits = np.bincount(components[predicted & valid], minlength=count)
    touches_unknown = np.bincount(components[~erode(valid, 1)], minlength=count)
    rows: list[PatchRow] = []
    for index in range(1, count):
        left, top, width, height, area = (int(value) for value in stats[index])
        for name, maximum in PATCH_BINS:
            if area <= maximum:
                size = name
                break
        rows.append(
            dict(
                patch=index,
                row=top,
                col=left,
                height=height,
                width=width,
                pixels=area,
                recovered_pixels=int(hits[index]),
                pixel_recall=float(hits[index] / area),
                no_overlap=bool(hits[index] == 0),
                truncated=bool(touches_unknown[index] > 0),
                size_bin=size,
            )
        )
    return rows


def patch_summary(rows: list[PatchRow]) -> list[dict[str, str | int | float | None]]:
    """Summarize patch_rows records by size, excluding truncated components.

    Return pixel-weighted recall and the fraction of patches with no predicted
    overlap for each bin. Empty bins have None ratios and zero counts.
    """
    result = []
    for size, _ in PATCH_BINS:
        selected = [
            row for row in rows if row["size_bin"] == size and not row["truncated"]
        ]
        pixels = sum(row["pixels"] for row in selected)
        hits = sum(row["recovered_pixels"] for row in selected)
        missed = sum(row["no_overlap"] for row in selected)
        result.append(
            dict(
                size_bin=size,
                patches=len(selected),
                pixels=pixels,
                recovered_pixels=hits,
                pixel_recall=ratio(hits, pixels),
                patches_without_overlap=missed,
                fraction_without_overlap=ratio(missed, len(selected)),
            )
        )
    return result


def analyze(
    label: NDArray[np.signedinteger], probability: NDArray[np.floating]
) -> Analysis:
    """Return diagnostic counts/tables for one reconstructed source canvas.

    Inputs are aligned HW arrays: labels are 0/1/-100 and probabilities are
    in [0, 1], with NaN for nodata. Ignore labels and nonfinite probabilities
    are excluded. Main scores use threshold 0.5; the sweep is diagnostic only.
    Inputs are not modified and no files are written.
    """
    valid = (label != -100) & np.isfinite(probability)
    truth, predicted = label == 1, probability >= 0.5
    sweep = [
        dict(threshold=t, **confusion(truth, probability >= t, valid))
        for t in THRESHOLDS
    ]
    safe = erode(valid, 4)
    near = distance_to(boundary(truth) & erode(valid, 1)) <= 3
    zones = [
        dict(zone=name, **confusion(truth, predicted, mask))
        for name, mask in [("near_boundary", safe & near), ("interior", safe & ~near)]
    ]
    bins = np.linspace(0, 1, 21)
    histograms = []
    for name, mask in [("kelp", valid & truth), ("background", valid & ~truth)]:
        counts, _ = np.histogram(probability[mask], bins=bins)
        histograms.extend(
            dict(
                label=name,
                lower=float(bins[i]),
                upper=float(bins[i + 1]),
                pixels=int(value),
            )
            for i, value in enumerate(counts)
        )
    return dict(
        counts=confusion(truth, predicted, valid),
        sweep=sweep,
        boundaries=boundary_counts(truth, predicted, valid),
        zones=zones,
        patches=patch_rows(truth, predicted, valid),
        histograms=histograms,
    )
