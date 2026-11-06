"""Connected labels retain source-size identity through distance stratification."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio import Affine

from kelpseg.reporting.shore_clusters import (
    UNKNOWN_CLUSTER,
    cluster_source,
    moments,
    pearson,
    write_cluster_ids,
)
from kelpseg.reporting.shore_clusters_summary import (
    pool_cluster_bands,
    pool_correlations,
)


def canvas(labels: np.ndarray) -> dict:
    """Build a metric original-source fixture without predictions or chips."""
    return dict(
        labels=labels,
        valid=np.ones(labels.shape, dtype=bool),
        footprint=np.ones(labels.shape, dtype=bool),
        source=dict(source_id="example", row_offset=10, col_offset=20),
        crs=rasterio.crs.CRS.from_epsg(32610),
        transform=Affine(3, 0, 500000, 0, -3, 5500000),
    )


def test_diagonal_components_full_size_land_unknown_cap_and_id_grid(
    tmp_path: Path,
) -> None:
    labels = np.zeros((10, 10), dtype=np.int8)
    labels[2, 2] = labels[3, 3] = 1
    labels[6, 2:6] = 1
    labels[0, 8] = 1
    labels[9, 9] = -100
    source = canvas(labels)
    land = np.zeros(labels.shape, dtype=np.uint8)
    distance = np.full(labels.shape, 60, dtype=np.float32)
    land[6, 2] = 1
    land[6, 3] = 255
    distance[6, 4] = 500
    ids, components, bands, correlations = cluster_source(
        source, land, distance, 9, 500, (0, 30, 60, 120, 500)
    )
    assert ids[2, 2] == ids[3, 3] != 0
    assert ids[6, 2] == ids[6, 5]
    assert ids[9, 9] == UNKNOWN_CLUSTER
    assert sorted(row["pixels"] for row in components) == [1, 2, 4]
    large = next(row for row in components if row["pixels"] == 4)
    assert large["area_m2"] == 36 and large["uncapped_ocean_pixels"] == 1
    assert large["original_row"] == 16 and large["original_col"] == 22
    assert not large["truncated"]
    assert sum(row["truncated"] for row in components) == 1
    all_pixels = next(
        row
        for row in correlations
        if row["weighting"] == "pixel" and row["component_scope"] == "all_observed"
    )
    interior_pixels = next(
        row
        for row in correlations
        if row["weighting"] == "pixel" and row["component_scope"] == "interior_only"
    )
    assert all_pixels["n"] == 4 and interior_pixels["n"] == 3
    assert (
        sum(
            row["kelp_pixels"]
            for row in bands
            if row["component_scope"] == "all_observed"
        )
        == 7
    )
    assert (
        sum(
            row["kelp_pixels"]
            for row in bands
            if row["component_scope"] == "interior_only"
        )
        == 6
    )
    path = tmp_path / "ids.tif"
    write_cluster_ids(path, ids, source)
    with rasterio.open(path) as ds:
        np.testing.assert_array_equal(ds.read(1), ids)
        assert ds.transform == source["transform"] and ds.crs == source["crs"]
        assert ds.nodata == UNKNOWN_CLUSTER and ds.dtypes == ("uint32",)


def test_pixel_correlation_repeats_full_component_area_and_pooling() -> None:
    labels = np.zeros((12, 12), dtype=np.int8)
    labels[2, 2] = 1
    labels[4, 3:5] = 1
    labels[7, 5:8] = 1
    distances = np.zeros(labels.shape, dtype=np.float32)
    distances[2, 2] = 10
    distances[4, 3:5] = (20, 30)
    distances[7, 5:8] = (40, 50, 60)
    _, _, _, stats = cluster_source(
        canvas(labels), np.zeros_like(labels), distances, 9, 500, (0, 30, 60, 120, 500)
    )
    pixels = next(
        row
        for row in stats
        if row["weighting"] == "pixel" and row["component_scope"] == "interior_only"
    )
    expected = np.corrcoef([10, 20, 30, 40, 50, 60], np.log10([9, 18, 18, 27, 27, 27]))[
        0, 1
    ]
    assert pearson(pixels) == pytest.approx(expected)
    clusters = next(
        row
        for row in stats
        if row["weighting"] == "cluster" and row["component_scope"] == "interior_only"
    )
    assert clusters["n"] == 3
    assert pearson(clusters) == pytest.approx(
        np.corrcoef([10, 25, 50], np.log10([9, 18, 27]))[0, 1]
    )
    # Pool moments, not source correlations (a singleton has no individual r).
    a = dict(
        region="001",
        split="train",
        weighting="pixel",
        **moments(np.array([1.0]), np.array([1.0])),
    )
    b = dict(
        region="001",
        split="train",
        weighting="pixel",
        **moments(np.array([2.0, 3.0]), np.array([2.0, 3.0])),
    )
    pooled = pool_correlations([a, b], ("region", "split", "weighting"), "region_split")
    assert pooled[0]["pearson_distance_log10_area"] == pytest.approx(1)
    assert pooled[0]["n"] == 3 and pooled[0]["contributing_sources"] == 2


def test_no_kelp_constant_support_and_unknown_edges() -> None:
    labels = np.zeros((5, 5), dtype=np.int8)
    source = canvas(labels)
    _, clusters, bands, stats = cluster_source(
        source, np.zeros_like(labels), np.zeros(labels.shape), 9, 500, (0, 120, 500)
    )
    assert not clusters and all(row["kelp_pixels"] == 0 for row in bands)
    assert all(pearson(row) is None for row in stats)
    assert pearson(moments(np.array([1.0, 1.0]), np.array([2.0, 3.0]))) is None
    labels[2, 2] = 1
    labels[1, 1] = -100
    _, clusters, _, _ = cluster_source(
        source, np.zeros_like(labels), np.zeros(labels.shape), 9, 500, (0, 120, 500)
    )
    assert clusters[0]["truncated"]


def test_size_composition_uses_pixel_denominator_per_distance() -> None:
    rows = [
        dict(
            split="train",
            component_scope="interior_only",
            distance_band="0-30",
            size_bin="1-10",
            kelp_pixels=3,
            clusters_present=2,
        ),
        dict(
            split="train",
            component_scope="interior_only",
            distance_band="0-30",
            size_bin="11-100",
            kelp_pixels=9,
            clusters_present=1,
        ),
    ]
    pooled = pool_cluster_bands(
        rows, ("split", "component_scope", "distance_band", "size_bin")
    )
    assert [row["fraction_of_band_kelp"] for row in pooled] == [0.25, 0.75]


def test_five_thousand_pixel_boundary_preserves_cluster_sizes() -> None:
    labels = np.zeros((130, 110), dtype=np.int8)
    labels[2:52, 2:102] = 1
    labels[70:120, 2:102] = 1
    labels[120, 2] = 1
    _, components, bands, _ = cluster_source(
        canvas(labels),
        np.zeros_like(labels),
        np.full(labels.shape, 30),
        9,
        500,
        (0, 30, 60, 120, 500),
    )
    assert {row["pixels"]: row["size_bin"] for row in components} == {
        5000: "1001-5000",
        5001: ">5000",
    }
    interior = [row for row in bands if row["component_scope"] == "interior_only"]
    assert (
        sum(row["kelp_pixels"] for row in interior if row["size_bin"] == "1001-5000")
        == 5000
    )
    assert (
        sum(row["kelp_pixels"] for row in interior if row["size_bin"] == ">5000")
        == 5001
    )
