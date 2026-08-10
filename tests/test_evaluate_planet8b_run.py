from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio

from scripts.evaluate_planet8b_run import evaluate
from src.evaluation.planet8b import (
    IGNORE_INDEX,
    EvaluationError,
    SourceAccumulator,
    binary_metrics,
    sum_confusion,
)


def test_overlap_averages_before_threshold_and_scores_unique_pixels() -> None:
    accumulator = SourceAccumulator(height=2, width=3)
    accumulator.add(
        np.array([[0.1, 0.9], [0.2, 0.2]], dtype=np.float32),
        np.array([[0, 1], [0, 1]], dtype=np.int16),
        row_off=0,
        col_off=0,
    )
    accumulator.add(
        np.array([[0.3, 0.3], [0.8, 0.8]], dtype=np.float32),
        np.array([[1, 0], [1, 0]], dtype=np.int16),
        row_off=0,
        col_off=1,
    )
    probability, mask, covered = accumulator.finalize(0.5)
    np.testing.assert_allclose(probability, [[0.1, 0.6, 0.3], [0.2, 0.5, 0.8]])
    assert mask.tolist() == [[0, 1, 0], [0, 1, 1]]
    metrics = binary_metrics(accumulator.label, mask, covered)
    assert metrics["scored_pixel_count"] == 6
    assert metrics["true_positive"] == 2
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 0


def test_ignore_and_uncovered_are_separate_accounting_categories() -> None:
    accumulator = SourceAccumulator(height=2, width=3)
    accumulator.add(
        np.array([[0.2, 0.8]], dtype=np.float32),
        np.array([[0, IGNORE_INDEX]], dtype=np.int16),
        row_off=0,
        col_off=0,
    )
    probability, mask, covered = accumulator.finalize(0.5)
    metrics = binary_metrics(accumulator.label, mask, covered)
    assert metrics["scored_pixel_count"] == 1
    assert metrics["ignored_pixel_count"] == 1
    assert metrics["uncovered_pixel_count"] == 4
    assert (
        sum(
            metrics[key]
            for key in (
                "scored_pixel_count",
                "ignored_pixel_count",
                "uncovered_pixel_count",
            )
        )
        == 6
    )
    assert np.isnan(probability[1, 2])


def test_conflicting_overlap_labels_fail() -> None:
    accumulator = SourceAccumulator(height=1, width=2)
    accumulator.add(np.array([[0.2, 0.8]]), np.array([[0, 1]]), row_off=0, col_off=0)
    with pytest.raises(EvaluationError, match="Conflicting"):
        accumulator.add(np.array([[0.2]]), np.array([[0]]), row_off=0, col_off=1)


def test_zero_denominators_are_explicitly_undefined() -> None:
    label = np.full((1, 2), IGNORE_INDEX, dtype=np.int16)
    metrics = binary_metrics(
        label, np.zeros((1, 2), dtype=np.uint8), np.ones((1, 2), dtype=bool)
    )
    assert metrics["accuracy"] is None
    assert metrics["kelp_precision"] is None
    assert metrics["kelp_iou"] is None
    assert metrics["background_iou"] is None


def test_tiff_pooling_sums_confusion_before_metrics() -> None:
    rows = [
        {
            "true_negative": 2,
            "false_positive": 1,
            "false_negative": 0,
            "true_positive": 1,
            "ignored_pixel_count": 0,
            "uncovered_pixel_count": 1,
            "covered_pixel_count": 4,
            "scored_pixel_count": 4,
            "total_source_pixel_count": 5,
        },
        {
            "true_negative": 0,
            "false_positive": 0,
            "false_negative": 1,
            "true_positive": 0,
            "ignored_pixel_count": 0,
            "uncovered_pixel_count": 0,
            "covered_pixel_count": 1,
            "scored_pixel_count": 1,
            "total_source_pixel_count": 1,
        },
    ]
    pooled = sum_confusion(rows)
    assert pooled["true_positive"] == 1
    assert pooled["kelp_iou"] == pytest.approx(1 / 3)


def test_evaluate_writes_aligned_rasters_and_resume_reuses_verified_source(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "dataset"
    (dataset / "all").mkdir(parents=True)
    labels = np.zeros((16, 24), dtype=np.int16)
    labels[:, 8:] = 1
    for chip_id, col_off in (("chip_a", 0), ("chip_b", 8)):
        np.savez_compressed(
            dataset / "all" / f"{chip_id}.npz",
            image=np.ones((16, 16, 8), dtype=np.uint16),
            label=labels[:, col_off : col_off + 16],
        )
    chip_manifest = tmp_path / "chips.csv"
    chip_manifest.write_text(
        "chip_id,chip_path,source_tiff_id,row_off,col_off,chip_width,chip_height\n"
        "chip_a,all/chip_a.npz,source,0,0,16,16\n"
        "chip_b,all/chip_b.npz,source,0,8,16,16\n"
    )
    fold = tmp_path / "fold.csv"
    fold.write_text(
        "chip_id,source_tiff_id,region_id,acquisition_date,experiment_split,selected\n"
        "chip_a,source,r1,2026-01-01,test,true\n"
        "chip_b,source,r1,2026-01-01,test,true\n"
    )
    metadata = tmp_path / "metadata.csv"
    metadata.write_text(
        "source_tiff_id,width,height,crs,transform_a,transform_b,transform_c,transform_d,transform_e,transform_f\n"
        "source,24,16,EPSG:32610,2,0,100,0,-2,200\n"
    )
    calls = 0

    def predictor(image: np.ndarray, label: np.ndarray) -> np.ndarray:
        nonlocal calls
        calls += 1
        return label.astype(np.float32) * 0.8 + 0.1

    common = dict(
        dataset_root=dataset,
        fold_manifest=fold,
        chip_manifest=chip_manifest,
        raster_metadata=metadata,
        output_root=tmp_path / "out",
        run_identity={"run_key": "fixture", "checkpoint_sha256": "a" * 64},
        threshold=0.5,
        predictor=predictor,
        save_rasters=True,
    )
    rows = evaluate(**common, resume=False)
    assert rows[0]["scored_pixel_count"] == 384
    probability_path = Path(rows[0]["probability_raster"])
    with rasterio.open(probability_path) as raster:
        assert raster.shape == (16, 24)
        assert raster.crs.to_string() == "EPSG:32610"
        assert raster.transform.c == 100
        assert raster.dtypes == ("float32",)
        assert raster.is_tiled
    evaluate(**common, resume=True)
    assert calls == 2
    evaluate(**{**common, "threshold": 0.4}, resume=True)
    assert calls == 4
