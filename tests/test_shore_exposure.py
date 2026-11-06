"""Sampler exposure counts overlapping appearances instead of unique coverage."""

import csv
from pathlib import Path

import numpy as np
import pytest

from kelpseg.reporting.shore_clusters import cluster_source
from kelpseg.reporting.shore_exposure import exposure_summary, exposure_windows
from kelpseg.reporting.shore_exposure_views import exposure_html


def make_canvas(labels: np.ndarray, region: str = "001") -> dict:
    """Return a small source canvas with offsets and known source identity."""
    return dict(
        labels=labels,
        valid=np.ones(labels.shape, dtype=bool),
        footprint=np.ones(labels.shape, dtype=bool),
        source=dict(
            source_id=f"source-{region}",
            region_id=region,
            acquisition_date="2020-01-01",
            split="train",
            row_offset=10,
            col_offset=20,
        ),
    )


def window(row: int, col: int, height: int, width: int, kelp: int = 1) -> dict:
    """Return a selected training window in original-source coordinates."""
    return dict(
        source_key="crop-a",
        split="train",
        payload=f"chip-{row}-{col}.npz",
        original_row=row + 10,
        original_col=col + 20,
        height=height,
        width=width,
        kelp_pixels=kelp,
    )


def observations(
    canvas: dict, windows: list[dict], land: np.ndarray, distance: np.ndarray
) -> list[dict]:
    """Assign full-source components then count selected windows."""
    ids, clusters, _, _ = cluster_source(canvas, land, distance, 9, 500, (0, 120, 500))
    return exposure_windows(canvas, windows, ids, clusters, land, distance, True)


def test_overlap_draw_expectations_region_denominators_and_selection() -> None:
    labels = np.zeros((5, 8), dtype=np.int8)
    labels[2, 1:5] = 1
    canvas = make_canvas(labels)
    land = np.zeros(labels.shape, dtype=np.uint8)
    distance = np.full(labels.shape, 500, dtype=np.float32)
    distance[2, 1:5] = (30, 119, 120, 500)
    selected = [window(2, 1, 1, 3), window(2, 2, 1, 3), window(0, 0, 1, 2, 0)]
    selected.append(dict(window(2, 1, 1, 3), split="val"))
    rows = observations(canvas, selected, land, distance)
    assert len(rows) == 2
    assert sum(row["kelp_pixels"] for row in rows) == 6  # Only four unique kelp pixels.
    assert sum(row["nearshore_1_10_pixels"] for row in rows) == 3
    assert (
        sum(row["offshore_1_10_pixels"] for row in rows) == 3
    )  # Includes exact 120 and cap.
    other = make_canvas(labels, "002")
    rows.extend(observations(other, [window(2, 4, 1, 1)], land, distance))
    summary = exposure_summary(rows, ["001", "002", "003"])
    near = next(
        row
        for row in summary
        if row["level"] == "global"
        and row["shore_zone"] == "nearshore"
        and row["size_bin"] == "all"
    )
    assert near["eligible_windows"] == 3 and near["pixel_exposures_per_epoch"] == 3
    assert near["expected_pixels_per_draw"] == 1
    assert near["probability_draw_has_kelp"] == pytest.approx(2 / 3)
    assert near["fraction_of_all_kelp_exposure"] == pytest.approx(3 / 7)
    region = next(
        row
        for row in summary
        if row["region"] == "001"
        and row["shore_zone"] == "nearshore"
        and row["size_bin"] == "<=100"
    )
    assert region["region_draw_probability"] == pytest.approx(2 / 3)
    assert region["expected_pixels_per_draw"] == 1
    assert region["expected_pixels_per_region_draw"] == 1.5
    assert region["probability_region_draw_has_kelp"] == 1
    absent = next(row for row in summary if row["region"] == "003")
    assert absent["eligible_windows"] == 0
    assert absent["expected_pixels_per_draw"] == 0
    assert absent["expected_pixels_per_region_draw"] is None
    assert absent["fraction_of_all_kelp_exposure"] is None


def test_cluster_size_is_full_source_not_window_and_fragments_stay_in_exposure() -> (
    None
):
    labels = np.zeros((15, 15), dtype=np.int8)
    labels[:11, :11] = 1  # 121-pixel component touches a source edge.
    canvas = make_canvas(labels)
    land = np.zeros(labels.shape, dtype=np.uint8)
    distance = np.full(labels.shape, 30, dtype=np.float32)
    rows = observations(canvas, [window(1, 1, 1, 3)], land, distance)
    assert rows[0]["nearshore_101_1000_pixels"] == 3
    assert rows[0]["nearshore_1_10_pixels"] == 0
    assert rows[0]["nearshore_101_1000_truncated_pixels"] == 3
    assert rows[0]["truncated_kelp_pixels"] == 3
    with pytest.raises(ValueError, match="outside"):
        observations(canvas, [window(14, 14, 3, 3)], land, distance)


def test_land_unknown_ignore_nodata_and_no_training_support() -> None:
    labels = np.array([[1, 1, 1, 1, 1, -100]], dtype=np.int8)
    canvas = make_canvas(labels)
    canvas["valid"][0, 4] = False
    land = np.array([[1, 0, 255, 0, 0, 0]], dtype=np.uint8)
    distance = np.array([[0, np.nan, 30, 60, 30, 30]], dtype=np.float32)
    rows = observations(canvas, [window(0, 0, 1, 6)], land, distance)
    assert rows[0]["known_label_pixels"] == 4
    assert rows[0]["kelp_pixels"] == 4
    assert rows[0]["land_1_10_pixels"] == 1
    assert rows[0]["unknown_1_10_pixels"] == 2
    assert rows[0]["nearshore_1_10_pixels"] == 1
    canvas["source"]["split"] = "val"
    assert observations(canvas, [window(0, 0, 1, 6)], land, distance) == []
    empty = exposure_summary([], ["001"])
    assert all(row["expected_pixels_per_draw"] is None for row in empty)


def test_validation_only_inventory_has_no_training_plot_link(tmp_path: Path) -> None:
    """A supported non-training source subset must not reference an absent plot."""
    rows = exposure_summary([], [])
    with (tmp_path / "exposure_summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    text = exposure_html(tmp_path)
    assert "No training sources" in text
    assert "training_exposure.png" not in text
    assert "N/A" in text
