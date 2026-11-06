"""True-label recall strata using saved full-source component membership."""

from typing import Any, TypedDict

import numpy as np
from numpy.typing import NDArray

from kelpseg.reporting.shore_clusters import CLUSTER_SIZE_BINS, UNKNOWN_CLUSTER
from kelpseg.reporting.shore_distance import bin_masks, pixel_area_m2
from kelpseg.reporting.shore_joint_inputs import ClusterComponent


class JointSourceRow(TypedDict):
    """One complete source/distance/size stratum, including empty support."""

    source_id: str
    region: str
    acquisition_date: str
    component_scope: str
    distance_band: str
    size_bin: str
    labeled_kelp_pixels: int
    labeled_kelp_area_m2: float
    tp: int
    fn: int
    recall: float | None


def joint_source_rows(
    canvas: dict[str, Any],
    ids: NDArray[np.uint32],
    components: dict[int, ClusterComponent],
    land: NDArray,
    distance: NDArray,
    threshold: float,
    edges: tuple[float, ...],
    identity: dict[str, Any],
) -> list[JointSourceRow]:
    """Count recall by distance and saved full-source size on scored kelp only.

    Finite predictions, native validity, footprint and known positive labels
    preserve the existing unique-pixel score support. Background predictions
    never receive a true-cluster size. Original boundary flags produce all,
    interior and truncated-only rows, whose TP/FN counts reconcile exactly.
    """
    labels, probability = canvas["labels"], canvas["probability"]
    if (
        ids.shape != labels.shape
        or land.shape != labels.shape
        or distance.shape != labels.shape
    ):
        raise ValueError(
            "Joint cluster, label and shoreline arrays must share a pixel grid."
        )
    scored_kelp = (
        canvas["valid"] & canvas["footprint"] & (labels == 1) & np.isfinite(probability)
    )
    unique, inverse = np.unique(ids[scored_kelp], return_inverse=True)
    if 0 in unique or UNKNOWN_CLUSTER in unique:
        raise ValueError("Scored labeled kelp has missing full-source cluster IDs.")
    missing = [int(value) for value in unique if int(value) not in components]
    if missing:
        raise ValueError(
            f"Scored labeled kelp references unknown cluster IDs: {missing[:5]}."
        )
    names = [name for name, _ in CLUSTER_SIZE_BINS]
    size_indices = np.array(
        [names.index(components[int(value)].size_bin) for value in unique],
        dtype=np.int8,
    )[inverse]
    truncated = np.array(
        [components[int(value)].truncated for value in unique], dtype=bool
    )[inverse]
    hits = probability[scored_kelp] >= threshold
    scopes = {
        "all_observed": np.ones(hits.shape, dtype=bool),
        "interior_only": ~truncated,
        "truncated_only": truncated,
    }
    area = pixel_area_m2(canvas["crs"], canvas["transform"])
    source = canvas["source"]
    source_id = source.get("original_source_id") or source.get("source_id")
    rows: list[JointSourceRow] = []
    for band, full_mask in bin_masks(land, distance, edges).items():
        mask = full_mask[scored_kelp]
        for scope, accepted in scopes.items():
            selected = mask & accepted
            counts = np.bincount(size_indices[selected], minlength=len(names))
            true_positives = np.bincount(
                size_indices[selected & hits], minlength=len(names)
            )
            for index, name in enumerate(names):
                count = int(counts[index])
                tp = int(true_positives[index])
                rows.append(
                    dict(
                        source_id=str(source_id),
                        region=str(identity.get("region", source.get("region_id", ""))),
                        acquisition_date=str(
                            identity.get(
                                "acquisition_date", source.get("acquisition_date", "")
                            )
                        ),
                        component_scope=scope,
                        distance_band=band,
                        size_bin=name,
                        labeled_kelp_pixels=count,
                        labeled_kelp_area_m2=count * area,
                        tp=tp,
                        fn=count - tp,
                        recall=tp / count if count else None,
                    )
                )
    return rows
