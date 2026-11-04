"""Geometric diagnostics and completed-run reporting without test payload access."""

import csv
import json
from types import SimpleNamespace

import numpy as np
from typer.testing import CliRunner

from kelpseg.cli import app
from kelpseg.validation_report import source_canvas
from kelpseg.validation_report.metrics import (
    analyze,
    boundary_counts,
    boundary_scores,
    patch_summary,
)


def test_boundary_tolerance_and_unknown_edges():
    truth = np.zeros((30, 30), dtype=bool)
    truth[8:20, 8:20] = True
    prediction = np.roll(truth, 1, axis=1)
    valid = np.ones_like(truth)
    results = boundary_counts(truth, prediction, valid)
    assert boundary_scores(results[0])["f1"] == 1
    # A line against unknown support must not become an evaluated contour.
    valid[:, :15] = False
    truth[:] = False
    truth[:, 15:] = True
    results = boundary_counts(truth, truth, valid)
    assert all(row["label_boundary_pixels"] == 0 for row in results)


def test_patches_truncation_size_recall_and_probability_counts():
    target = np.zeros((40, 40), dtype=np.int8)
    target[5:7, 5:7] = 1  # complete small patch, missed entirely
    target[15:19, 15:19] = 1  # complete larger patch, half recovered
    target[0:3, 25:28] = 1  # clipped by observation edge
    target[30:33, 30:33] = 1
    target[33:, :] = -100  # another truncated patch at coverage gap
    probability = np.full(target.shape, 0.1, dtype=np.float32)
    probability[15:17, 15:19] = 0.9
    result = analyze(target, probability)
    sizes = patch_summary(result["patches"])
    assert sum(row["truncated"] for row in result["patches"]) == 2
    assert sizes[0]["patches"] == 1 and sizes[0]["fraction_without_overlap"] == 1
    assert sizes[1]["pixel_recall"] == 0.5
    assert sum(row["pixels"] for row in result["histograms"]) == (target != -100).sum()
    at_half = next(row for row in result["sweep"] if row["threshold"] == 0.5)
    assert {k: at_half[k] for k in ("tp", "fp", "fn", "tn")} == result["counts"]
    zones = result["zones"]
    assert (
        sum(sum(row[k] for k in ("tp", "fp", "fn", "tn")) for row in zones)
        < (target != -100).sum()
    )


def test_adjacent_windows_join_without_splitting_patch(tmp_path):
    rows = []
    for index in range(2):
        label = np.zeros((8, 8), dtype=np.int8)
        label[3:5, 6:8] = 1 if index == 0 else 0
        if index == 1:
            label[3:5, :2] = 1
        path = tmp_path / f"{index}.npz"
        np.savez(path, image=np.ones((8, 8, 3), dtype=np.uint16), label=label)
        rows.append(
            dict(
                payload=str(path),
                original_row=10,
                original_col=20 + index * 8,
                height=8,
                width=8,
                source_id="source",
                region="001",
            )
        )
    model = SimpleNamespace(
        predict_probabilities=lambda image, bands: np.full(image.shape[:2], 0.9)
    )
    labels, prob, top, left, _ = source_canvas(
        rows, model, ["nir", "red", "green"], tmp_path, [], []
    )
    patches = analyze(labels, prob)["patches"]
    assert (top, left) == (10, 20)
    assert len(patches) == 1 and patches[0]["pixels"] == 8
    assert not patches[0]["truncated"]


def test_report_command_completed_run_and_test_isolation(tmp_path, monkeypatch):
    import kelpseg.validation_report as report

    chips = tmp_path / "chips"
    chips.mkdir()
    (chips / "recipe.json").write_text(
        json.dumps(dict(source_band_names=["nir", "red", "green"]))
    )
    payload = chips / "val.npz"
    label = np.zeros((20, 20), dtype=np.int8)
    label[6:12, 6:12] = 1
    np.savez(payload, image=np.full((20, 20, 3), 1000, dtype=np.uint16), label=label)
    rows = [
        dict(
            split=split,
            payload=str(payload if split == "val" else chips / "missing-test.npz"),
            dataset_id="data",
            release_id="v1",
            original_tiff="source.tif",
            source_id="source",
            region="001",
            acquisition_date="2021-01-01",
            row=0,
            col=0,
            original_row=0,
            original_col=0,
            height=20,
            width=20,
            kelp_pixels=36,
            crs="EPSG:32611",
            transform=[3, 0, 0, 0, -3, 0],
        )
        for split in ["val", "test"]
    ]
    monkeypatch.setattr(report, "select_windows", lambda *a, **kw: rows)
    # Tiny actual portable model, offline CPU, no pretrained fetch.
    import torch

    from kelpseg.model_bundle import PortableModel

    model = torch.nn.Conv2d(3, 1, 1)
    torch.nn.init.zeros_(model.weight)
    torch.nn.init.constant_(model.bias, -1)
    portable = PortableModel(
        model.eval(),
        dict(input_size=512, band_names=["nir", "red", "green"]),
        torch.device("cpu"),
    )
    monkeypatch.setattr(report, "load_model_bundle", lambda *a, **kw: portable)
    run = tmp_path / "run"
    (run / "model").mkdir(parents=True)
    record = dict(
        status="running",
        run_id="test",
        chips=str(chips),
        assignments="unused",
        experiment="baseline",
        variant="augmented",
    )
    (run / "run.json").write_text(json.dumps(record))
    (run / "model/model.json").write_text(
        json.dumps(dict(run_id="test", checkpoint_epoch=4, weight_kind="ema"))
    )
    output = tmp_path / "report"
    args = ["validation-report", "--run", str(run), "--output", str(output)]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1 and "completed run" in result.output
    assert not output.exists()
    record["status"] = "complete"
    (run / "run.json").write_text(json.dumps(record))
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    summary = json.loads((output / "summary.json").read_text())
    assert summary["global"]["pixels"] == 400
    assert summary["global"]["fn"] == 36
    with (output / "sources.csv").open() as stream:
        source = next(csv.DictReader(stream))
    assert float(source["area_bias_m2"]) == -324
    assert (output / "examples/00.png").exists()
    assert "NIR/red/green" in (output / "report.html").read_text()
    assert CliRunner().invoke(app, args).exit_code == 1


def test_boundary_matching_keeps_observed_references_outside_scoring_margin():
    truth = np.zeros((30, 30), dtype=bool)
    prediction = np.zeros_like(truth)
    truth[10, 1] = True
    prediction[10, 2] = True
    counts = boundary_counts(truth, prediction, np.ones_like(truth))[0]
    assert counts["label_boundary_pixels"] == 0
    assert counts["predicted_boundary_pixels"] == 1
    assert counts["matched_prediction_pixels"] == 1
    assert boundary_scores(counts)["precision"] == 1
    assert boundary_scores(counts)["recall"] is None
    # Reversing labels/predictions must preserve the matching rule.
    reverse = boundary_counts(prediction, truth, np.ones_like(truth))[0]
    assert reverse["matched_label_pixels"] == 1
    assert boundary_scores(reverse)["recall"] == 1


def test_boundary_partial_matches_use_euclidean_distance():
    truth = np.zeros((30, 30), dtype=bool)
    prediction = np.zeros_like(truth)
    truth[8, 8] = truth[20, 20] = True
    prediction[9, 9] = prediction[8, 20] = True
    results = boundary_counts(truth, prediction, np.ones_like(truth))
    assert boundary_scores(results[0])["f1"] == 0
    assert boundary_scores(results[1])["precision"] == 0.5
    assert boundary_scores(results[1])["recall"] == 0.5
    assert boundary_scores(results[1])["f1"] == 0.5


def test_confusion_thresholds_histogram_endpoints_and_undefined_scores():
    from kelpseg.validation_report.metrics import scores

    labels = np.array([[1, 1, 0, 0, -100, 1]], dtype=np.int8)
    probability = np.array([[1, 0, 0.5, 0.49, 1, np.nan]])
    result = analyze(labels, probability)
    assert result["counts"] == dict(tp=1, fp=1, fn=1, tn=1)
    metrics = scores(result["counts"])
    assert metrics["iou"] == 1 / 3
    assert metrics["precision"] == metrics["recall"] == 0.5
    assert metrics["pixel_error_rate"] == 0.5
    assert metrics["area_bias_pixels"] == 0
    assert metrics["background_false_positive_rate"] == 0.5
    at_nine = next(r for r in result["sweep"] if r["threshold"] == 0.9)
    assert at_nine == dict(threshold=0.9, tp=1, fp=0, fn=1, tn=2)
    kelp_bins = [r["pixels"] for r in result["histograms"] if r["label"] == "kelp"]
    assert kelp_bins[0] == kelp_bins[-1] == 1
    assert sum(kelp_bins) == 2
    empty = scores(dict(tp=0, fp=0, fn=0, tn=0))
    assert empty["iou"] is None and empty["pixel_error_rate"] is None
    background = scores(dict(tp=0, fp=0, fn=0, tn=10))
    assert background["iou"] is None and background["pixel_error_rate"] == 0


def test_pooled_metrics_use_counts_not_mean_source_scores():
    from kelpseg.validation_report import pooled
    from kelpseg.validation_report.metrics import COUNT_KEYS, scores

    rows = [
        dict(region="a", tp=1, fp=1, fn=0, tn=8),
        dict(region="a", tp=9, fp=0, fn=1, tn=90),
    ]
    counts = pooled(rows, ("region",), COUNT_KEYS)[0]
    result = scores({key: counts[key] for key in COUNT_KEYS})
    assert result["iou"] == 10 / 12
    assert result["precision"] == result["recall"] == 10 / 11
    assert result["pixels"] == 110
    assert result["iou"] != (0.5 + 0.9) / 2


def test_diagonal_patch_connectivity_and_pixel_weighted_size_recall():
    label = np.zeros((30, 30), dtype=np.int8)
    label[5, 5] = label[6, 6] = 1  # one 8-connected two-pixel patch
    label[15:17, 15:19] = 1  # eight-pixel patch, missed
    probability = np.zeros_like(label, dtype=float)
    probability[5, 5] = probability[6, 6] = 1
    patches = analyze(label, probability)["patches"]
    assert len(patches) == 2
    summary = patch_summary(patches)[0]
    assert summary["patches"] == 2
    assert summary["pixel_recall"] == 2 / 10
    assert summary["fraction_without_overlap"] == 1 / 2
