"""Matched unseen-TIFF reporting, equal coverage, and count-based suite pooling."""

import json
import shutil

import numpy as np
import pytest
import rasterio
from test_temporal_report import saved_temporal_fixture

from kelpseg.reporting.inputs import read_csv
from kelpseg.reporting.loro import check_matched_coverage, report_fold
from kelpseg.reporting.loro_summary import (
    matched_pairs,
    pool_segmentation,
    summarize_suite,
)
from kelpseg.reporting.report import write_csv
from kelpseg.reporting.temporal_summary import AREA_KEYS, COVERAGE_KEYS


def fixture(tmp_path):
    """Create three full-region sources, two unseen by the baseline."""
    previous = saved_temporal_fixture(tmp_path)
    settings = json.loads((previous / "settings.json").read_text())
    predictions = tmp_path / "predictions"
    baseline = tmp_path / "baseline"
    shutil.copytree(predictions, baseline)
    for filename in ("sources.csv", "windows.csv"):
        rows = read_csv(baseline / filename)
        write_csv(
            baseline / filename, [r for r in rows if r["source_key"] in {"a", "b"}]
        )
    rows = []
    for source in read_csv(predictions / "sources.csv"):
        for experiment in ("baseline", "loro_001"):
            rows.append(
                dict(
                    dataset_id=source["dataset_id"],
                    release_id=source["release_id"],
                    source_id=source["original_source_id"],
                    region="001",
                    acquisition_date=source["acquisition_date"],
                    satellite_id="test",
                    experiment=experiment,
                    variant="augmented",
                    split="train"
                    if experiment == "baseline" and source["source_key"] == "c"
                    else "test",
                )
            )
    assignments = tmp_path / "assignments.csv"
    write_csv(assignments, rows)
    return dict(
        output=tmp_path / "fold-reports",
        predictions=predictions,
        baseline_predictions=baseline,
        labels=tmp_path / settings["labels"],
        label_root=tmp_path,
        matched_keys={"a", "b"},
        assignments=assignments,
        experiment="loro_001",
    )


def test_full_and_paired_reports_exclude_unmatched_source_and_pool(tmp_path):
    arguments = fixture(tmp_path)
    folder = report_fold(**arguments)
    assert len(read_csv(folder / "full-segmentation/sources.csv")) == 3
    assert {
        r["source_keys"]
        for r in read_csv(folder / "paired-loro-segmentation/sources.csv")
    } == {"a", "b"}
    assert read_csv(folder / "unmatched.csv")[0]["source_key"] == "c"
    summary = summarize_suite([folder], tmp_path / "pooled")
    segmentation = read_csv(summary / "segmentation.csv")
    paired = [
        r for r in segmentation if r["scope"] == "paired" and r["region"] == "all"
    ]
    assert len(paired) == 2
    assert paired[0]["scoreable_pixels"] == paired[1]["scoreable_pixels"]
    temporal = read_csv(summary / "temporal.csv")
    assert all(r["headline_pairs"] == "1" for r in temporal if r["scope"] == "paired")
    assert len(read_csv(summary / "paired-changes.csv")) == 1


def test_finite_coverage_mismatch_stops_pairing(tmp_path):
    arguments = fixture(tmp_path)
    path = arguments["baseline_predictions"] / "a.tif"
    with rasterio.open(path, "r+") as dataset:
        values = dataset.read(1)
        values[5, 5] = np.nan
        dataset.write(values, 1)
    with pytest.raises(ValueError, match="finite-pixel coverage"):
        check_matched_coverage(
            arguments["predictions"], arguments["baseline_predictions"], {"a", "b"}
        )


def test_baseline_selection_and_spacecraft_companions_are_rejected(tmp_path):
    arguments = fixture(tmp_path)
    rows = read_csv(arguments["assignments"])
    baseline_train = next(r for r in rows if r["split"] == "train")
    baseline_train["acquisition_date"] = "2021-01-01"
    write_csv(arguments["assignments"], rows)
    with pytest.raises(ValueError, match="spacecraft/day companion"):
        report_fold(**arguments)


def test_pooling_uses_confusion_counts_not_mean_iou():
    rows = []
    for region, tp, fn in (("001", 1, 0), ("002", 0, 9)):
        rows.append(
            dict(
                scope="full",
                arm="loro",
                region=region,
                tp=tp,
                fn=fn,
                fp=0,
                tn=0,
                **{key: 0 for key in (*AREA_KEYS, *COVERAGE_KEYS)},
            )
        )
    pooled = next(r for r in pool_segmentation(rows) if r["region"] == "all")
    assert pooled["iou"] == 0.1


def test_temporal_undefined_in_either_arm_excluded_from_joint_headline():
    common = dict(
        region="001",
        interval="short",
        earlier_source="a",
        later_source="b",
        status="supported",
        common_pixels="100",
        common_area_m2="900",
        label_before_pixels="10",
        label_after_pixels="12",
        earlier_scoreable_pixels="100",
        later_scoreable_pixels="100",
    )
    result = matched_pairs(
        [dict(common, change_error_pp="20")], [dict(common, change_error_pp="")]
    )
    assert result[0]["jointly_defined"] is False
    with pytest.raises(ValueError, match="coverage or label support"):
        matched_pairs(
            [dict(common, change_error_pp="20")],
            [dict(common, common_pixels="99", change_error_pp="20")],
        )
