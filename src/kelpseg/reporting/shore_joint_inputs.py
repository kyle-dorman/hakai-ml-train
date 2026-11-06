"""Read saved full-source cluster identities without relabeling validation crops."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from numpy.typing import NDArray
from rasterio import Affine
from rasterio.windows import Window

from kelpseg.reporting.shore_clusters import CLUSTER_SIZE_BINS, UNKNOWN_CLUSTER


@dataclass(frozen=True)
class ClusterComponent:
    """Saved full-source component size and original boundary-truncation flag."""

    pixels: int
    size_bin: str
    truncated: bool


@dataclass(frozen=True)
class ClusterInventory:
    """Explicit original-source manifests and source-local saved component records."""

    sources: dict[str, dict[str, str]]
    components: dict[str, dict[int, ClusterComponent]]


def load_cluster_inventory(root: Path) -> ClusterInventory:
    """Read saved cluster CSVs once, rejecting ambiguous identities or invalid sizes.

    IDs and component sizes are accepted from the completed inventory; no image,
    label or prediction window is used to recompute connected components.
    """
    sources: dict[str, dict[str, str]] = {}
    with (root / "cluster_sources.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            source_id = row.get("source_id", "")
            if not source_id or source_id in sources or not row.get("cluster_ids"):
                raise ValueError(
                    "Cluster inventory needs unique source_id values and cluster_ids paths."
                )
            sources[source_id] = row
    if not sources:
        raise ValueError("Cluster inventory contains no source identities.")
    components: dict[str, dict[int, ClusterComponent]] = {key: {} for key in sources}
    with (root / "clusters.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            source_id = row.get("source_id", "")
            if source_id not in sources:
                raise ValueError(f"Unknown cluster inventory source_id: {source_id}.")
            for name in ("dataset_id", "release_id", "region", "acquisition_date"):
                if row.get(name) != sources[source_id].get(name):
                    raise ValueError(
                        f"{source_id}: cluster {name} differs from source identity."
                    )
            try:
                cluster_id, pixels = int(row["cluster_id"]), int(row["pixels"])
            except (KeyError, ValueError) as error:
                raise ValueError(
                    f"{source_id}: cluster IDs and pixel sizes must be integers."
                ) from error
            if (
                cluster_id <= 0
                or cluster_id >= UNKNOWN_CLUSTER
                or cluster_id in components[source_id]
                or pixels <= 0
            ):
                raise ValueError(
                    f"{source_id}: cluster IDs must be unique and sizes positive."
                )
            size_bin = next(
                name for name, maximum in CLUSTER_SIZE_BINS if pixels <= maximum
            )
            if row.get("size_bin") != size_bin or row.get("truncated") not in (
                "True",
                "False",
            ):
                raise ValueError(
                    f"{source_id}: saved cluster size bin or truncated flag is invalid."
                )
            components[source_id][cluster_id] = ClusterComponent(
                pixels=pixels, size_bin=size_bin, truncated=row["truncated"] == "True"
            )
    return ClusterInventory(sources=sources, components=components)


def read_cluster_canvas(
    root: Path, inventory: ClusterInventory, canvas: dict[str, Any]
) -> tuple[NDArray[np.uint32], dict[int, ClusterComponent]]:
    """Read source-local IDs on an integer-aligned report canvas without resampling.

    The caller supplies a canonical original_source_id and source_keys (chip
    reports normalize these through their saved window mapping). Outside the
    saved raster remains unknown; scored kelp there is rejected by the counter.
    """
    source = canvas["source"]
    source_id = source.get("original_source_id") or source.get("source_id")
    if source_id not in inventory.sources:
        raise ValueError(f"Missing cluster inventory source_id: {source_id}.")
    row = inventory.sources[source_id]
    for inventory_name, canvas_name in (
        ("dataset_id", "dataset_id"),
        ("release_id", "release_id"),
        ("region", "region_id"),
        ("acquisition_date", "acquisition_date"),
    ):
        if source.get(canvas_name) and row.get(inventory_name) != source[canvas_name]:
            raise ValueError(
                f"{source_id}: cluster {inventory_name} differs from report identity."
            )
    keys = set(source.get("source_keys", source.get("source_key", "")).split(";"))
    if (
        not keys
        or "" in keys
        or not keys.issubset(set(row.get("source_keys", "").split(";")))
    ):
        raise ValueError(
            f"{source_id}: report source_keys are missing from the cluster inventory."
        )
    with rasterio.open(root / row["cluster_ids"]) as dataset:
        if (
            dataset.count != 1
            or dataset.dtypes != ("uint32",)
            or dataset.nodata != UNKNOWN_CLUSTER
            or dataset.crs != canvas["crs"]
        ):
            raise ValueError(
                f"{source_id}: cluster raster needs uint32 IDs, explicit nodata and the report CRS."
            )
        offset = ~dataset.transform * canvas["transform"]
        x, y = round(offset.c), round(offset.f)
        if not offset.almost_equals(Affine.translation(x, y), precision=1e-6):
            raise ValueError(
                f"{source_id}: cluster raster is not pixel-aligned with the report canvas."
            )
        height, width = canvas["labels"].shape
        ids = dataset.read(
            1,
            window=Window(x, y, width, height),
            boundless=True,
            fill_value=int(UNKNOWN_CLUSTER),
        )
    return ids, inventory.components[source_id]
