"""Saved full-source components stratify unique scored pixels without reclustering."""

import csv
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio import Affine

from kelpseg.reporting.shore_clusters import UNKNOWN_CLUSTER
from kelpseg.reporting.shore_distance import DEFAULT_DISTANCE_EDGES
from kelpseg.reporting.shore_joint_counts import joint_source_rows
from kelpseg.reporting.shore_joint_inputs import (
    ClusterComponent,
    load_cluster_inventory,
    read_cluster_canvas,
)


def write_rows(path: Path, rows: list[dict]) -> None:
    """Write ordinary fixture CSV records using the completed inventory schema."""
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def inventory_fixture(root: Path) -> tuple[dict, dict]:
    """Save a 5,000-pixel full-source component and return a small clipped canvas."""
    identity = dict(
        source_id="original-a",
        dataset_id="ca_bc",
        release_id="v1",
        region="004",
        acquisition_date="2021-05-24",
        source_keys="crop-a",
    )
    source = dict(identity, cluster_ids="ids.tif")
    write_rows(root / "cluster_sources.csv", [source])
    component = dict(
        identity, cluster_id=1, pixels=5000, size_bin="1001-5000", truncated=False
    )
    write_rows(root / "clusters.csv", [component])
    ids = np.zeros((80, 110), dtype=np.uint32)
    ids[2:52, 2:102] = 1
    transform = Affine(3, 0, 500000, 0, -3, 5500000)
    crs = rasterio.crs.CRS.from_epsg(32610)
    with rasterio.open(
        root / "ids.tif",
        "w",
        driver="GTiff",
        width=110,
        height=80,
        count=1,
        dtype="uint32",
        crs=crs,
        transform=transform,
        nodata=int(UNKNOWN_CLUSTER),
    ) as dataset:
        dataset.write(ids, 1)
    canvas = dict(
        labels=np.ones((2, 3), dtype=np.int8),
        probability=np.array([[0.5, 0.49, np.nan], [1, 0.2, 0.9]], dtype=np.float32),
        valid=np.array([[True, True, True], [False, True, True]]),
        footprint=np.array([[True, True, True], [True, True, False]]),
        transform=transform * Affine.translation(2, 2),
        crs=crs,
        source=dict(
            original_source_id="original-a",
            source_keys="crop-a",
            dataset_id="ca_bc",
            release_id="v1",
            region_id="004",
            acquisition_date="2021-05-24",
            row_offset=2,
            col_offset=2,
        ),
    )
    return canvas, component


def count_rows(canvas: dict, ids: np.ndarray, components: dict) -> list[dict]:
    """Count a fixture's shore strata with a fixed saved threshold."""
    land = np.zeros(canvas["labels"].shape, dtype=np.uint8)
    distance = np.full(land.shape, 30, dtype=np.float32)
    return joint_source_rows(
        canvas, ids, components, land, distance, 0.5, DEFAULT_DISTANCE_EDGES, {}
    )


def test_saved_size_survives_clipped_coverage_and_integer_offset(
    tmp_path: Path,
) -> None:
    canvas, _ = inventory_fixture(tmp_path)
    inventory = load_cluster_inventory(tmp_path)
    ids, components = read_cluster_canvas(tmp_path, inventory, canvas)
    np.testing.assert_array_equal(ids, np.ones((2, 3), dtype=np.uint32))
    rows = count_rows(canvas, ids, components)
    supported = [
        r
        for r in rows
        if r["component_scope"] == "all_observed" and r["labeled_kelp_pixels"]
    ]
    assert len(supported) == 1
    row = supported[0]
    assert (row["size_bin"], row["tp"], row["fn"]) == ("1001-5000", 1, 2)
    assert row["labeled_kelp_pixels"] == 3 and row["labeled_kelp_area_m2"] == 27
    assert row["recall"] == pytest.approx(1 / 3)
    assert row["source_id"] == "original-a" and row["region"] == "004"
    assert len(rows) == 3 * 8 * 5
    assert all(r["recall"] is None for r in rows if not r["labeled_kelp_pixels"])
    assert (
        components[1].pixels == 5000
    )  # Not the six visible pixels or three scored pixels.


def test_truncated_land_unknown_and_false_positives_reconcile(tmp_path: Path) -> None:
    canvas, _ = inventory_fixture(tmp_path)
    canvas.update(
        labels=np.array([[1, 1, 1, 0], [1, -100, 1, 1]], dtype=np.int8),
        probability=np.array([[0.5, 0.4, 0.9, 0.9], [np.nan, 0.9, 0.1, 0.8]]),
        valid=np.array([[True, True, True, True], [True, True, False, True]]),
        footprint=np.ones((2, 4), dtype=bool),
    )
    ids = np.array([[1, 2, 2, 0], [1, UNKNOWN_CLUSTER, 2, 2]], dtype=np.uint32)
    components = {
        1: ClusterComponent(5000, "1001-5000", False),
        2: ClusterComponent(5001, ">5000", True),
    }
    land = np.array([[0, 1, 0, 0], [0, 0, 0, 255]], dtype=np.uint8)
    distance = np.array([[119, 0, 120, 500], [30, 30, 30, np.nan]])
    rows = joint_source_rows(
        canvas, ids, components, land, distance, 0.5, DEFAULT_DISTANCE_EDGES, {}
    )
    totals = {}
    for scope in ("all_observed", "interior_only", "truncated_only"):
        selected = [r for r in rows if r["component_scope"] == scope]
        totals[scope] = tuple(sum(r[key] for r in selected) for key in ("tp", "fn"))
    assert totals == {
        "all_observed": (3, 1),
        "interior_only": (1, 0),
        "truncated_only": (2, 1),
    }
    assert all("fp" not in r and "precision" not in r for r in rows)
    for row in (r for r in rows if r["component_scope"] == "all_observed"):
        parts = [
            r
            for r in rows
            if r["component_scope"] != "all_observed"
            and r["distance_band"] == row["distance_band"]
            and r["size_bin"] == row["size_bin"]
        ]
        assert all(
            row[k] == sum(r[k] for r in parts)
            for k in ("tp", "fn", "labeled_kelp_pixels")
        )
    assert (
        sum(
            r["tp"]
            for r in rows
            if r["component_scope"] == "all_observed"
            and r["distance_band"] == "unknown"
        )
        == 1
    )
    assert (
        sum(
            r["fn"]
            for r in rows
            if r["component_scope"] == "all_observed" and r["distance_band"] == "land"
        )
        == 1
    )


@pytest.mark.parametrize("missing", [0, int(UNKNOWN_CLUSTER), 99])
def test_missing_scored_cluster_fails_instead_of_silent_exclusion(
    tmp_path: Path, missing: int
) -> None:
    canvas, _ = inventory_fixture(tmp_path)
    inventory = load_cluster_inventory(tmp_path)
    ids, components = read_cluster_canvas(tmp_path, inventory, canvas)
    ids[0, 0] = missing
    with pytest.raises(ValueError, match="cluster IDs"):
        count_rows(canvas, ids, components)


def test_identity_grid_and_outside_support_are_explicit(tmp_path: Path) -> None:
    canvas, _ = inventory_fixture(tmp_path)
    inventory = load_cluster_inventory(tmp_path)
    shifted = dict(canvas, transform=canvas["transform"] * Affine.translation(0.5, 0))
    with pytest.raises(ValueError, match="pixel-aligned"):
        read_cluster_canvas(tmp_path, inventory, shifted)
    wrong_date = dict(
        canvas, source=dict(canvas["source"], acquisition_date="2021-05-25")
    )
    with pytest.raises(ValueError, match="acquisition_date"):
        read_cluster_canvas(tmp_path, inventory, wrong_date)
    wrong_key = dict(canvas, source=dict(canvas["source"], source_keys="other-crop"))
    with pytest.raises(ValueError, match="source_keys"):
        read_cluster_canvas(tmp_path, inventory, wrong_key)
    outside = dict(canvas, transform=canvas["transform"] * Affine.translation(-5, -5))
    ids, components = read_cluster_canvas(tmp_path, inventory, outside)
    assert np.all(ids == UNKNOWN_CLUSTER)
    with pytest.raises(ValueError, match="missing full-source"):
        count_rows(outside, ids, components)


def test_duplicate_components_and_invalid_size_metadata_fail(tmp_path: Path) -> None:
    _, component = inventory_fixture(tmp_path)
    write_rows(tmp_path / "clusters.csv", [component, component])
    with pytest.raises(ValueError, match="unique"):
        load_cluster_inventory(tmp_path)
    write_rows(tmp_path / "clusters.csv", [dict(component, size_bin=">5000")])
    with pytest.raises(ValueError, match="size bin"):
        load_cluster_inventory(tmp_path)


def test_empty_scored_positive_support_has_undefined_recall(tmp_path: Path) -> None:
    canvas, _ = inventory_fixture(tmp_path)
    canvas["labels"][:] = 0
    rows = count_rows(canvas, np.zeros((2, 3), dtype=np.uint32), {})
    assert len(rows) == 120
    assert all(r["tp"] == r["fn"] == 0 and r["recall"] is None for r in rows)
