"""Pixel-level shoreline strata using the existing scored source footprint."""

from collections import defaultdict
from typing import Any

import numpy as np

from kelpseg.reporting.metrics import COUNT_KEYS, confusion, scores
from kelpseg.reporting.shore_distance import bin_masks, pixel_area_m2

COVERAGE_KEYS = (
    "footprint_pixels",
    "valid_pixels",
    "nodata_pixels",
    "ignored_valid_pixels",
    "uncovered_valid_pixels",
    "scoreable_pixels",
    "available_labeled_kelp_pixels",
)
AREA_KEYS = (
    "scoreable_area_m2",
    "labeled_kelp_area_m2",
    "predicted_kelp_area_m2",
    "available_labeled_kelp_area_m2",
)


def shore_source_rows(
    canvas: dict[str, Any],
    land: np.ndarray,
    distance: np.ndarray,
    threshold: float,
    edges: tuple[float, ...],
    identity: dict[str, Any],
    scope: str,
    split: str,
) -> list[dict[str, Any]]:
    """Return disjoint band counts on one original canvas without changing arrays.

    Coverage uses the existing footprint/native validity; confusion uses finite
    predictions and known labels. Land and unknown remain explicit categories.
    """
    labels, probability = canvas["labels"], canvas["probability"]
    footprint, valid = canvas["footprint"], canvas["valid"]
    known, finite = labels != -100, np.isfinite(probability)
    observed = valid & known & finite
    area = pixel_area_m2(canvas["crs"], canvas["transform"])
    rows = []
    for band, mask in bin_masks(land, distance, edges).items():
        counts = confusion(labels == 1, probability >= threshold, mask & observed)
        available_kelp = int((mask & valid & known & (labels == 1)).sum())
        coverage = dict(
            footprint_pixels=int((mask & footprint).sum()),
            valid_pixels=int((mask & valid).sum()),
            nodata_pixels=int((mask & footprint & ~valid).sum()),
            ignored_valid_pixels=int((mask & valid & ~known).sum()),
            uncovered_valid_pixels=int((mask & valid & ~finite).sum()),
            scoreable_pixels=int((mask & observed).sum()),
            available_labeled_kelp_pixels=available_kelp,
        )
        rows.append(
            dict(
                **identity,
                scope=scope,
                split=split,
                distance_band=band,
                **coverage,
                **scores(counts),
                scoreable_area_m2=coverage["scoreable_pixels"] * area,
                labeled_kelp_area_m2=(counts["tp"] + counts["fn"]) * area,
                predicted_kelp_area_m2=(counts["tp"] + counts["fp"]) * area,
                available_labeled_kelp_area_m2=available_kelp * area,
            )
        )
    return rows


def pool_shore_rows(
    rows: list[dict[str, Any]], *, by_region: bool
) -> list[dict[str, Any]]:
    """Sum source counts/areas per band, then calculate scores and support counts.

    Region grouping is optional; scope and split always remain separate. Source
    and date support count only records contributing native valid pixels.
    """
    keys = ("scope", "split", "distance_band")
    if by_region:
        keys = ("region", *keys)
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    output = []
    for key, members in groups.items():
        values = {name: sum(row[name] for row in members) for name in COVERAGE_KEYS}
        areas = {name: sum(row[name] for row in members) for name in AREA_KEYS}
        counts = {name: sum(row[name] for row in members) for name in COUNT_KEYS}
        supported = [row for row in members if row["valid_pixels"]]
        output.append(
            dict(
                zip(keys, key, strict=True),
                **values,
                **scores(counts),
                **areas,
                sources_with_valid_pixels=len(supported),
                sources_with_scored_pixels=sum(
                    row["scoreable_pixels"] > 0 for row in members
                ),
                dates_with_valid_pixels=len(
                    {row["acquisition_date"] for row in supported}
                ),
            )
        )
    return output


def shoreline_canvas(
    canvas: dict[str, Any], windows: list[dict], scope: str
) -> dict[str, Any]:
    """Use explicit saved chip-to-source identities for a shoreline raster join.

    Chip prediction canvas keys are generated identifiers. Their recorded windows
    retain canonical chip_source_key and assignment source_id; use these without
    deriving identities from filenames. TIFF canvases already use source keys.
    """
    if scope != "chip_disjoint":
        return canvas
    if not windows or any(
        not row.get("chip_source_key") or not row.get("source_id") for row in windows
    ):
        raise ValueError(
            "Shoreline chip reporting requires saved chip_source_key and source_id in windows.csv."
        )
    originals = {row["source_id"] for row in windows}
    if len(originals) != 1:
        raise ValueError(
            "Saved chip windows must identify one original source per shoreline canvas."
        )
    source = dict(
        canvas["source"],
        source_keys=";".join(sorted({row["chip_source_key"] for row in windows})),
        original_source_id=next(iter(originals)),
    )
    return dict(canvas, source=source)
