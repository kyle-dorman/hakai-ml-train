"""Combine declared crops on their original grid using NumPy slices."""

from collections import defaultdict
from collections.abc import Iterator

import numpy as np
from rasterio import Affine

from kelpseg.reporting.inputs import ReportSettings, read_chips, read_tiff


def source_groups(sources: list[dict]) -> list[list[dict]]:
    """Group only explicitly identified common originals, retaining unknown identities."""
    groups = defaultdict(list)
    for source in sources:
        original = source.get("original_source_id", "")
        key = (
            (
                source.get("dataset_id", ""),
                source.get("release_id", ""),
                original,
            )
            if original
            else ("unknown", source["source_key"])
        )
        groups[key].append(source)
    return [groups[key] for key in sorted(groups)]


def merge_crops(crops: list[dict]) -> dict:
    """Average finite crop probabilities once per original pixel and reconcile labels.

    Crops must share an explicit original identity, band order, date and original
    affine grid. Valid overlapping labels must agree. Return one canvas with
    unique native validity/footprint masks; gap pixels remain unknown.
    """
    source_keys = ";".join(sorted(crop["source"]["source_key"] for crop in crops))
    if len(crops) == 1:
        return dict(crops[0], source=dict(crops[0]["source"], source_keys=source_keys))
    first = crops[0]
    reference = first["source"]
    for crop in crops:
        source = crop["source"]
        if any(source.get(k) in ("", None) for k in ("row_offset", "col_offset")):
            raise ValueError(
                "Overlapping original crops require explicit row_offset and col_offset."
            )
        for key in ("band_names", "region_id", "acquisition_date"):
            if source.get(key, "") != reference.get(key, ""):
                raise ValueError(f"Crops of one original disagree on {key}.")
    top = min(int(c["source"]["row_offset"]) for c in crops)
    left = min(int(c["source"]["col_offset"]) for c in crops)
    bottom = max(int(c["source"]["row_offset"]) + c["labels"].shape[0] for c in crops)
    right = max(int(c["source"]["col_offset"]) + c["labels"].shape[1] for c in crops)
    original_transform = first["transform"] * Affine.translation(
        -int(reference["col_offset"]), -int(reference["row_offset"])
    )
    shape = bottom - top, right - left
    sums = np.zeros(shape, dtype=np.float32)
    counts = np.zeros(shape, dtype=np.uint32)
    labels = np.full(shape, -100, dtype=np.int8)
    valid = np.zeros(shape, dtype=bool)
    footprint = np.zeros(shape, dtype=bool)
    image = np.zeros((*shape, first["image"].shape[-1]), dtype=np.uint16)
    for crop in crops:
        source = crop["source"]
        offset_y, offset_x = int(source["row_offset"]), int(source["col_offset"])
        origin = crop["transform"] * Affine.translation(-offset_x, -offset_y)
        if crop["crs"] != first["crs"] or not origin.almost_equals(
            original_transform, precision=1e-7
        ):
            raise ValueError(
                "Crops of one original have incompatible grids/offsets; run cleanup first."
            )
        y, x = offset_y - top, offset_x - left
        height, width = crop["labels"].shape
        region = np.s_[y : y + height, x : x + width]
        target = crop["labels"]
        known = target != -100
        disagreement = known & (labels[region] != -100) & (labels[region] != target)
        if disagreement.any():
            raise ValueError(
                "Conflicting valid labels in overlapping crops of one original."
            )
        labels[region][known] = target[known]
        finite = np.isfinite(crop["probability"])
        sums[region] += np.where(finite, crop["probability"], 0)
        counts[region] += finite
        image[region][crop["valid"]] = crop["image"][crop["valid"]]
        valid[region] |= crop["valid"]
        footprint[region] |= crop["footprint"]
    probability = np.full(shape, np.nan, dtype=np.float32)
    np.divide(sums, counts, out=probability, where=counts > 0)
    source = dict(
        reference, row_offset=str(top), col_offset=str(left), source_keys=source_keys
    )
    return dict(
        source=source,
        probability=probability,
        labels=labels,
        image=image,
        valid=valid,
        footprint=footprint,
        crs=first["crs"],
        transform=original_transform * Affine.translation(left, top),
    )


def canvases(
    sources: list[dict], windows: list[dict], scope: str, settings: ReportSettings
) -> Iterator[tuple[dict, list[dict]]]:
    """Yield one original-source canvas and its selected windows at a time."""
    windows_by_source = defaultdict(list)
    for window in windows:
        windows_by_source[window["source_key"]].append(window)
    for group in source_groups(sources):
        crops, selected = [], []
        for source in group:
            source_windows = windows_by_source[source["source_key"]]
            selected.extend(source_windows)
            if scope == "chip_disjoint":
                crop = read_chips(source, source_windows, settings)
            else:
                crop = read_tiff(source, settings)
            crops.append(crop)
        yield merge_crops(crops), selected
