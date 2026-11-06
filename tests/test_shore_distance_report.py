"""Distance strata reconcile source coverage, land errors and saved report scores."""

import csv
import json
from dataclasses import replace

import numpy as np
import pytest
from rasterio import Affine
from test_reporting import TRANSFORM, crop, csv_file, raster, saved_tiff

from kelpseg.reporting.inputs import load_settings
from kelpseg.reporting.report import report
from kelpseg.reporting.shore_report import pool_shore_rows, shore_source_rows


def shoreline(tmp_path, source, land, distance, transform=TRANSFORM, cap=500):
    """Write aligned small shoreline fixtures with the ordinary manifest schema."""
    root = tmp_path / "shoreline"
    root.mkdir()
    raster(root / "land.tif", np.asarray(land, np.uint8), transform, nodata=255)
    raster(
        root / "distance.tif",
        np.asarray(distance, np.float32),
        transform,
        nodata=np.nan,
    )
    csv_file(
        root / "sources.csv",
        [
            dict(
                source_key=source["source_key"],
                dataset_id=source.get("dataset_id", ""),
                release_id=source.get("release_id", ""),
                original_source_id=source.get("original_source_id", ""),
                region_id=source.get("region_id", ""),
                acquisition_date=source.get("acquisition_date", ""),
                land_mask="land.tif",
                distance="distance.tif",
                cap_m=cap,
            )
        ],
    )
    return root


def test_report_distance_counts_reconcile_land_unknown_and_uncovered(tmp_path):
    probability = np.array([[0.8, 0.9, 0.4, np.nan, np.nan, 0.5]], np.float32)
    labels = np.array([[1, 3, 2, 1, 3, 0]], np.uint8)
    image = np.ones((3, 1, 6), np.uint16)
    image[:, :, 4] = 0
    settings, source = saved_tiff(tmp_path, probability, labels, image)
    root = shoreline(
        tmp_path, source, [[1, 0, 0, 0, 255, 255]], [[0, 30, 60, 500, np.nan, np.nan]]
    )
    report(replace(settings, shoreline=root))
    summary = json.loads((settings.output / "summary.json").read_text())
    rows = summary["shoreline"]["global_bands"]
    assert {k: sum(row[k] for row in rows) for k in ("tp", "fp", "fn", "tn")} == {
        k: summary["global"][k] for k in ("tp", "fp", "fn", "tn")
    }
    indexed = {row["distance_band"]: row for row in rows}
    assert indexed["land"]["tp"] == 1
    assert indexed["unknown"]["fp"] == 1
    assert indexed["unknown"]["nodata_pixels"] == 1
    assert indexed["30-60"]["ignored_valid_pixels"] == 1
    assert indexed["60-120"]["tn"] == 1
    assert indexed["500+"]["uncovered_valid_pixels"] == 1
    assert indexed["500+"]["available_labeled_kelp_pixels"] == 1
    assert indexed["500+"]["labeled_kelp_pixels"] == 0
    assert indexed["500+"]["recall"] is None
    assert sum(row["scoreable_area_m2"] for row in rows) == 27
    assert "Distance to mapped land" in (settings.output / "report.html").read_text()


def test_enabling_shoreline_preserves_global_and_saved_threshold(tmp_path):
    settings, source = saved_tiff(
        tmp_path,
        probability=np.full((12, 12), 0.6),
        labels=np.ones((12, 12)),
        split="test",
    )
    metadata = json.loads((settings.predictions / "settings.json").read_text())
    metadata["model"]["threshold"] = 0.7
    (settings.predictions / "settings.json").write_text(json.dumps(metadata))
    report(settings)
    before = json.loads((settings.output / "summary.json").read_text())
    root = shoreline(tmp_path, source, np.zeros((12, 12)), np.full((12, 12), 30))
    after_settings = replace(
        settings, shoreline=root, output=tmp_path / "shore-report", max_examples=1
    )
    report(after_settings)
    after = json.loads((after_settings.output / "summary.json").read_text())
    assert before["global"] == after["global"]
    assert before["coverage"] == after["coverage"]
    assert after["threshold"] == 0.7
    band = next(
        row
        for row in after["shoreline"]["global_bands"]
        if row["distance_band"] == "30-60"
    )
    assert band["fn"] == 144 and band["tp"] == 0
    assert (after_settings.output / "thresholds.csv").read_text() == ""
    assert (after_settings.output / "examples/shore_00.png").exists()


def test_distance_pooling_counts_before_ratios_and_source_date_support():
    first = crop([[0.9, 0.9]], [[1, 0]])
    second = crop([[0.9, 0.9]], [[1, 1]])
    identity = dict(region="001", acquisition_date="2020-01-01")
    rows = []
    for canvas in (first, second):
        rows.extend(
            shore_source_rows(
                canvas,
                np.zeros((1, 2), np.uint8),
                np.full((1, 2), 10),
                0.5,
                (0, 30, 500),
                identity,
                "chip_disjoint",
                "val",
            )
        )
    band = next(
        row
        for row in pool_shore_rows(rows, by_region=True)
        if row["distance_band"] == "0-30"
    )
    assert band["tp"] == 3 and band["fp"] == 1
    assert band["iou"] == 0.75
    assert band["sources_with_scored_pixels"] == 2
    assert band["dates_with_valid_pixels"] == 1


@pytest.mark.parametrize("problem", ["missing", "duplicate", "grid", "cap"])
def test_report_refuses_missing_duplicate_misaligned_or_insufficient_shoreline(
    tmp_path, problem
):
    settings, source = saved_tiff(tmp_path)
    root = shoreline(
        tmp_path,
        source,
        np.zeros((12, 12)),
        np.ones((12, 12)),
        cap=250 if problem == "cap" else 500,
    )
    if problem in ("missing", "duplicate"):
        with (root / "sources.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        if problem == "missing":
            rows[0]["source_key"] = "absent"
        else:
            rows *= 2
        csv_file(root / "sources.csv", rows)
    if problem == "grid":
        raster(
            root / "distance.tif",
            np.ones((12, 12), np.float32),
            TRANSFORM * Affine.translation(0.5, 0),
        )
    with pytest.raises(
        ValueError,
        match={
            "missing": "Missing shoreline",
            "duplicate": "duplicate",
            "grid": "rasters must match",
            "cap": "cap_m",
        }[problem],
    ):
        report(replace(settings, shoreline=root))


def test_report_recipe_distance_settings(tmp_path):
    recipe = tmp_path / "report.toml"
    recipe.write_text(
        'predictions="p"\noutput="r"\nshoreline="s"\ndistance_edges=[0,60,500]\n'
    )
    settings = load_settings(recipe)
    assert settings.shoreline == tmp_path / "s"
    assert settings.distance_edges == (0, 60, 500)
    recipe.write_text('predictions="p"\noutput="r"\ndistance_edges=[0,60,60]\n')
    with pytest.raises(ValueError, match="increasing"):
        load_settings(recipe)


def test_chip_report_joins_canonical_windows_not_generated_prediction_keys(tmp_path):
    labels = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [1, 0, 0, 0]], np.int8)
    settings, source = saved_tiff(tmp_path, np.full(labels.shape, 0.8), labels)
    source["source_key"] = "source_000001"
    source["original_source_id"] = "original.tif"
    csv_file(settings.predictions / "sources.csv", [source])
    payload = tmp_path / "chip.npz"
    np.savez(payload, image=np.ones((*labels.shape, 3), np.uint16), label=labels)
    csv_file(
        settings.predictions / "windows.csv",
        [
            dict(
                source_key="source_000001",
                chip_source_key="canonical",
                source_id="original",
                row=0,
                col=0,
                kelp_pixels=5,
                original_row=0,
                original_col=0,
                height=3,
                width=4,
                payload=str(payload),
                region="001",
                dataset_id="dataset",
                release_id="release",
            )
        ],
    )
    metadata = json.loads((settings.predictions / "settings.json").read_text())
    metadata.update(scope="chip_disjoint", split="val")
    (settings.predictions / "settings.json").write_text(json.dumps(metadata))
    root = shoreline(
        tmp_path,
        dict(source, source_key="canonical", original_source_id="original"),
        np.zeros(labels.shape),
        np.full(labels.shape, 30),
    )
    settings = replace(
        settings, shoreline=root, labels=None, label_root=None, external_scope=""
    )
    report(settings)
    summary = json.loads((settings.output / "summary.json").read_text())
    band = next(
        row
        for row in summary["shoreline"]["global_bands"]
        if row["distance_band"] == "30-60"
    )
    assert band["tp"] == 5 and band["fp"] == 7
    assert band["scope"] == "chip_disjoint"
    assert (
        sum(row["scoreable_pixels"] for row in summary["shoreline"]["global_bands"])
        == 12
    )


def test_source_grid_window_join_uses_declared_offsets_at_utm_coordinates(tmp_path):
    """A cropped canvas reads the exact source window; integer misplacement fails."""
    from kelpseg.reporting.shore_distance import load_shore_sources, read_shore_canvas

    transform = Affine(3, 0, 600000, 0, -3, 5500000)
    canvas = crop([[0.8, 0.8, 0.8]], [[0, 1, 0]])
    canvas["source"].update(source_key="source", row_offset="1", col_offset="2")
    canvas["transform"] = transform * Affine.translation(2, 1)
    distance = np.arange(12, dtype=np.float32).reshape(2, 6)
    root = shoreline(tmp_path, canvas["source"], np.zeros((2, 6)), distance, transform)
    with (root / "sources.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    rows[0].update(
        row_offset="0",
        col_offset="0",
        width="6",
        height="2",
        transform=json.dumps(list(transform)),
    )
    csv_file(root / "sources.csv", rows)
    land, actual_distance = read_shore_canvas(root, load_shore_sources(root), canvas)
    np.testing.assert_array_equal(land, [[0, 0, 0]])
    np.testing.assert_array_equal(actual_distance, [[8, 9, 10]])
    rows[0]["col_offset"] = "1"
    csv_file(root / "sources.csv", rows)
    with pytest.raises(ValueError, match="original offsets"):
        read_shore_canvas(root, load_shore_sources(root), canvas)
