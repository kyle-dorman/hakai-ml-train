"""Saved prediction reporting: coverage, identity joins and shared arithmetic."""

import csv
import json

import numpy as np
import pytest
import rasterio
from rasterio import Affine

from kelpseg.reporting.canvases import merge_crops
from kelpseg.reporting.inputs import (
    ReportSettings,
    load_settings,
    read_chips,
    read_inputs,
    read_tiff,
)
from kelpseg.reporting.metrics import analyze
from kelpseg.reporting.report import report

TRANSFORM = Affine(3, 0, 300, 0, -3, 600)


def csv_file(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def raster(path, values, transform=TRANSFORM, crs="EPSG:32611", nodata=None):
    if values.ndim == 2:
        values = values[None]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        count=len(values),
        height=values.shape[1],
        width=values.shape[2],
        dtype=values.dtype,
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dataset:
        dataset.write(values)


def saved_tiff(tmp_path, probability=None, labels=None, image=None, split="val"):
    root = tmp_path / "predictions"
    root.mkdir()
    probability = (
        np.full((12, 12), 0.7, np.float32)
        if probability is None
        else probability.astype(np.float32)
    )
    labels = (
        np.zeros(probability.shape, np.uint8)
        if labels is None
        else labels.astype(np.uint8)
    )
    image = np.ones((3, *probability.shape), np.uint16) if image is None else image
    raster(tmp_path / "image.tif", image, nodata=0)
    raster(tmp_path / "label.tif", labels, nodata=0)
    raster(root / "probability.tif", probability, nodata=np.nan)
    source = dict(
        source_key="a",
        image=str(tmp_path / "image.tif"),
        probability="probability.tif",
        band_names="nir;red;green",
        dataset_id="dataset",
        release_id="release",
        original_source_id="original",
        region_id="001",
        acquisition_date="2020-01-01",
        row_offset="0",
        col_offset="0",
    )
    csv_file(root / "sources.csv", [source])
    csv_file(
        root / "windows.csv",
        [
            dict(
                source_key="a",
                row=0,
                col=0,
                height=probability.shape[0],
                width=probability.shape[1],
            )
        ],
    )
    (root / "summary.json").write_text(json.dumps(dict(status="complete")))
    (root / "settings.json").write_text(
        json.dumps(
            dict(
                model=dict(
                    threshold=0.5, run_id="run", checkpoint_epoch=2, weight_kind="ema"
                )
            )
        )
    )
    csv_file(tmp_path / "labels.csv", [dict(source_key="a", label="label.tif")])
    settings = ReportSettings(
        root,
        tmp_path / "report",
        labels=tmp_path / "labels.csv",
        label_root=tmp_path,
        external_scope="bounded validation example",
        split=split,
        max_examples=0,
    )
    return settings, source


def test_report_coverage_mapping_zero_background_and_fixed_threshold(tmp_path):
    probability = np.array([[0.8, 0.9, 0.4, np.nan, np.nan, 0.5]], np.float32)
    labels = np.array([[1, 3, 2, 1, 3, 0]], np.uint8)
    image = np.ones((3, 1, 6), np.uint16)
    image[:, :, 4] = 0
    settings, _ = saved_tiff(tmp_path, probability, labels, image)
    output = report(settings)
    assert output.exists()
    summary = json.loads((settings.output / "summary.json").read_text())
    assert summary["global"]["tp"] == 1
    assert summary["global"]["fp"] == 1
    assert summary["global"]["tn"] == 1
    assert summary["global"]["pixels"] == 3
    assert summary["coverage"]["nodata_pixels"] == 1
    assert summary["coverage"]["uncovered_valid_pixels"] == 1
    assert summary["coverage"]["ignored_valid_pixels"] == 1
    assert summary["coverage"]["covered_ignored_pixels"] == 1
    assert summary["global"]["area_bias_m2"] == 9
    assert summary["global"]["f1"] == pytest.approx(2 / 3)
    assert summary["background_chips"] is None
    assert summary["scope"] == "tiff_tiled"
    assert "tiff_tiled" in output.read_text()
    with pytest.raises(ValueError, match="already exists"):
        report(settings)


def test_report_all_skipped_undefined_and_test_sweep_suppression(tmp_path):
    settings, _ = saved_tiff(tmp_path, np.full((10, 10), np.nan), split="test")
    report(settings)
    summary = json.loads((settings.output / "summary.json").read_text())
    assert summary["global"]["iou"] is None
    assert summary["coverage"]["uncovered_valid_pixels"] == 100
    assert (settings.output / "thresholds.csv").read_text() == ""
    assert (settings.output / "source_thresholds.csv").read_text() == ""


def test_saved_threshold_parameter_applies_to_primary_and_patch_diagnostics(tmp_path):
    settings, _ = saved_tiff(tmp_path, np.full((12, 12), 0.6), np.ones((12, 12)))
    metadata = json.loads((settings.predictions / "settings.json").read_text())
    metadata["model"]["threshold"] = 0.7
    (settings.predictions / "settings.json").write_text(json.dumps(metadata))
    report(settings)
    summary = json.loads((settings.output / "summary.json").read_text())
    assert summary["global"]["fn"] == 144 and summary["global"]["tp"] == 0
    assert "threshold 0.7" in (settings.output / "report.html").read_text()


def test_exact_label_grid_and_stored_background_ignores_nodata_metadata(tmp_path):
    settings, source = saved_tiff(tmp_path)
    _, sources, _ = read_inputs(settings)
    canvas = read_tiff(sources[0], settings)
    assert np.all(canvas["labels"] == 0)
    raster(
        tmp_path / "label.tif",
        np.zeros((12, 12), np.uint8),
        transform=TRANSFORM * Affine.translation(1, 0),
    )
    with pytest.raises(ValueError, match="grids differ"):
        read_tiff(sources[0], settings)


def test_unknown_label_category_and_nongeographic_area_rejected(tmp_path):
    settings, source = saved_tiff(tmp_path, labels=np.full((12, 12), 9))
    _, sources, _ = read_inputs(settings)
    with pytest.raises(ValueError, match="Unmapped label"):
        read_tiff(sources[0], settings)
    raster(
        settings.predictions / "probability.tif",
        np.ones((12, 12), np.float32),
        crs="EPSG:4326",
    )
    with pytest.raises(ValueError, match="metre"):
        read_tiff(sources[0], settings)


def test_source_label_join_duplicate_and_missing(tmp_path):
    settings, _ = saved_tiff(tmp_path)
    csv_file(tmp_path / "labels.csv", [dict(source_key="a", label="label.tif")] * 2)
    with pytest.raises(ValueError, match="duplicate"):
        read_inputs(settings)
    csv_file(tmp_path / "labels.csv", [dict(source_key="b", label="label.tif")])
    with pytest.raises(ValueError, match="exactly match"):
        read_inputs(settings)


def test_assignment_exact_join_and_wrong_split(tmp_path):
    settings, _ = saved_tiff(tmp_path)
    assignments = tmp_path / "assignments.csv"
    row = dict(
        dataset_id="dataset",
        release_id="release",
        source_id="original",
        region="001",
        acquisition_date="2020-01-01",
        experiment="baseline",
        variant="augmented",
        split="val",
    )
    csv_file(assignments, [row])
    settings = ReportSettings(
        settings.predictions,
        settings.output,
        labels=settings.labels,
        label_root=tmp_path,
        assignments=assignments,
        experiment="baseline",
        variant="augmented",
        split="val",
        max_examples=0,
    )
    read_inputs(settings)
    row["split"] = "test"
    csv_file(assignments, [row])
    with pytest.raises(ValueError, match="assignment is test"):
        read_inputs(settings)


def crop(probability, labels, offset=0):
    probability = np.asarray(probability, np.float32)
    labels = np.asarray(labels, np.int8)
    return dict(
        source=dict(
            source_key=f"crop{offset}",
            original_source_id="original",
            row_offset="0",
            col_offset=str(offset),
            band_names="nir;red;green",
            region_id="001",
            acquisition_date="2020-01-01",
        ),
        probability=probability,
        labels=labels,
        image=np.ones((*labels.shape, 3), np.uint16),
        valid=np.ones(labels.shape, bool),
        footprint=np.ones(labels.shape, bool),
        transform=TRANSFORM * Affine.translation(offset, 0),
        crs=rasterio.crs.CRS.from_epsg(32611),
    )


def test_crops_average_before_threshold_count_once_and_keep_offsets():
    first = crop([[0.2, 0.2]], [[0, 1]], offset=3)
    second = crop([[0.8, 0.8]], [[1, 0]], offset=4)
    canvas = merge_crops([first, second])
    np.testing.assert_allclose(canvas["probability"], [[0.2, 0.5, 0.8]])
    assert analyze(canvas["labels"], canvas["probability"])["counts"] == dict(
        tp=1, fp=1, fn=0, tn=1
    )
    assert canvas["source"]["source_keys"] == "crop3;crop4"
    assert canvas["source"]["col_offset"] == "3"
    assert canvas["transform"] == TRANSFORM * Affine.translation(3, 0)


def test_crops_reject_conflicting_labels_grids_and_date():
    first = crop([[0.2, 0.2]], [[0, 1]])
    second = crop([[0.8, 0.8]], [[0, 0]], offset=1)
    with pytest.raises(ValueError, match="Conflicting valid labels"):
        merge_crops([first, second])
    second["labels"][0, 0] = 1
    second["transform"] = second["transform"] * Affine.translation(0.5, 0)
    with pytest.raises(ValueError, match="incompatible grids"):
        merge_crops([first, second])
    second["source"]["acquisition_date"] = "2020-01-02"
    with pytest.raises(ValueError, match="acquisition_date"):
        merge_crops([first, second])


def test_adjacent_saved_chips_keep_connected_patch_and_match_direct_arrays(tmp_path):
    root = tmp_path / "predictions"
    root.mkdir()
    target = np.zeros((8, 16), np.int8)
    target[3:5, 6:10] = 1
    probability = np.full((8, 16), 0.9, np.float32)
    raster(
        root / "p.tif", probability, transform=TRANSFORM * Affine.translation(20, 10)
    )
    rows = []
    for index in range(2):
        payload = tmp_path / f"{index}.npz"
        np.savez(
            payload,
            image=np.ones((8, 8, 3), np.uint16),
            label=target[:, index * 8 : (index + 1) * 8],
        )
        rows.append(
            dict(
                payload=str(payload),
                original_row=10,
                original_col=20 + 8 * index,
                height=8,
                width=8,
            )
        )
    source = dict(
        source_key="a",
        probability="p.tif",
        band_names="nir;red;green",
        row_offset="10",
        col_offset="20",
    )
    canvas = read_chips(source, rows, ReportSettings(root, tmp_path / "report"))
    result = analyze(canvas["labels"], canvas["probability"])
    assert result == analyze(target, probability)
    assert len(result["patches"]) == 1 and result["patches"][0]["pixels"] == 8
    assert not result["patches"][0]["truncated"]


def test_recipe_unknown_fields_paths_and_mapping(tmp_path):
    recipe = tmp_path / "report.toml"
    recipe.write_text(
        'predictions="p"\noutput="r"\n[label_mapping]\n0=0\n1=1\n255=-100\n'
    )
    settings = load_settings(recipe)
    assert settings.predictions == tmp_path / "p"
    assert settings.label_mapping == {0: 0, 1: 1, 255: -100}
    recipe.write_text('predictions="p"\noutput="r"\nunknown=true\n')
    with pytest.raises(ValueError, match="Unknown report"):
        load_settings(recipe)


def test_unknown_originals_keep_distinct_source_keys_and_input_references(tmp_path):
    settings, source = saved_tiff(tmp_path)
    first = dict(source, original_source_id="")
    second = dict(first, source_key="b")
    csv_file(settings.predictions / "sources.csv", [first, second])
    csv_file(
        settings.labels, [dict(source_key=key, label="label.tif") for key in ("a", "b")]
    )
    report(settings)
    with (settings.output / "sources.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert [row["source_keys"] for row in rows] == ["a", "b"]
    assert all(row["original_tiff"] == "" for row in rows)
    with (settings.output / "input_sources.csv").open() as stream:
        references = list(csv.DictReader(stream))
    assert [row["source_key"] for row in references] == ["a", "b"]
    assert all(
        row["probability"] == str(settings.predictions / "probability.tif")
        for row in references
    )
    assert all(row["label"] == str(tmp_path / "label.tif") for row in references)
    assert references[0]["band_names"] == "nir;red;green"


@pytest.mark.parametrize(
    "mapping",
    [
        "label_mapping = [0, 1]",
        'label_mapping = "binary"',
        '[label_mapping]\n"0" = false\n"1" = true',
        '[label_mapping]\n"0" = 0.0',
        '[label_mapping]\n"kelp" = 1',
        "[label_mapping]",
    ],
)
def test_recipe_malformed_mapping_has_actionable_error(tmp_path, mapping):
    recipe = tmp_path / "report.toml"
    recipe.write_text('predictions="p"\noutput="r"\n' + mapping + "\n")
    with pytest.raises(ValueError, match="label_mapping"):
        load_settings(recipe)
