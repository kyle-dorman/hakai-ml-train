"""Date selection and saved-report CLI integration without model execution."""

import json
from dataclasses import replace

import numpy as np
import pytest
from test_reporting import csv_file, raster, saved_tiff
from typer.testing import CliRunner

from kelpseg.cli import app
from kelpseg.reporting.inputs import read_csv
from kelpseg.reporting.report import report
from kelpseg.reporting.temporal import temporal_report
from kelpseg.reporting.temporal_inputs import (
    TemporalSettings,
    interval_for,
    load_settings,
    select_pairs,
)


def source(key, day, region="001"):
    return dict(
        source_keys=key,
        acquisition_date=day,
        region=region,
        dataset_id="data",
        release_id="v1",
    )


def test_inclusive_day_ranges_and_configurable_boundaries(tmp_path):
    settings = TemporalSettings(tmp_path, tmp_path / "out")
    assert [interval_for(day, settings) for day in (0, 1, 13, 14, 28, 29, 47, 48)] == [
        "same_day",
        "short",
        "short",
        "outside_intervals",
        "outside_intervals",
        "long",
        "long",
        "outside_intervals",
    ]
    assert interval_for(14, replace(settings, short_max_days=14)) == "short"
    for values in [
        dict(short_min_days=0),
        dict(short_max_days=29),
        dict(long_min_days=13),
        dict(long_max_days=28),
        dict(short_max_days=True),
        dict(small_baseline_pixels=-1),
    ]:
        with pytest.raises(ValueError):
            replace(settings, **values)


def test_pairs_are_date_based_not_calendar_month_based(tmp_path):
    settings = TemporalSettings(tmp_path, tmp_path / "out")
    rows = [
        source("a", "2021-02-24"),
        source("b", "2021-04-04"),
        source("c", "2021-04-06"),
        source("d", "2021-04-06"),
        source("other", "2021-04-04", "002"),
        source("unknown", ""),
    ]
    pairs = select_pairs(rows, settings)
    found = {
        (p["earlier_source"], p["later_source"]): (p["days"], p["interval"])
        for p in pairs
    }
    assert found[("a", "b")] == (39, "long")
    assert found[("b", "c")] == (2, "short")
    assert found[("c", "d")] == (0, "same_day")
    assert len(found) == 6


def test_explicit_pair_identity_order_and_exclusions(tmp_path):
    pairfile = tmp_path / "pairs.csv"
    settings = TemporalSettings(tmp_path, tmp_path / "out", pairs=pairfile)
    rows = [
        source("a", "2021-01-01"),
        source("b", "2021-01-20"),
        source("c", "2021-01-20", "002"),
    ]
    csv_file(pairfile, [dict(earlier_source="a", later_source="b")])
    assert select_pairs(rows, settings)[0]["interval"] == "outside_intervals"
    for chosen, match in [
        ([("b", "a")], "reversed"),
        ([("a", "c")], "share dataset"),
        ([("a", "missing")], "known"),
        ([("a", "a")], "distinct"),
        ([("a", "b"), ("a", "b")], "duplicates"),
    ]:
        csv_file(pairfile, [dict(earlier_source=a, later_source=b) for a, b in chosen])
        with pytest.raises(ValueError, match=match):
            select_pairs(rows, settings)


def saved_temporal_fixture(tmp_path):
    """Make real saved raster/report artifacts with known short and long changes."""
    settings, first = saved_tiff(tmp_path)
    sources = []
    labels = []
    windows = []
    for key, day, label_count, predicted_count in [
        ("a", "2021-01-01", 10, 20),
        ("b", "2021-01-10", 11, 22),
        ("c", "2021-02-05", 12, 30),
    ]:
        target = np.zeros((12, 12), np.uint8)
        target.flat[:label_count] = 1
        probability = np.full((12, 12), 0.1, np.float32)
        probability.flat[:predicted_count] = 0.9
        raster(tmp_path / f"{key}-image.tif", np.ones((3, 12, 12), np.uint16))
        raster(tmp_path / f"{key}-label.tif", target)
        raster(settings.predictions / f"{key}.tif", probability, nodata=np.nan)
        sources.append(
            dict(
                first,
                source_key=key,
                original_source_id=key,
                acquisition_date=day,
                image=str(tmp_path / f"{key}-image.tif"),
                probability=f"{key}.tif",
            )
        )
        labels.append(dict(source_key=key, label=f"{key}-label.tif"))
        windows.append(dict(source_key=key, row=0, col=0, height=12, width=12))
    csv_file(settings.predictions / "sources.csv", sources)
    csv_file(settings.predictions / "windows.csv", windows)
    csv_file(settings.labels, labels)
    report(settings)
    return settings.output


def test_cli_report_percentages_and_saved_inputs(tmp_path):
    report_root = saved_temporal_fixture(tmp_path)
    recipe = tmp_path / "temporal.toml"
    recipe.write_text('report="report"\noutput="temporal"\n')
    result = CliRunner().invoke(app, ["temporal-report", "--recipe", str(recipe)])
    assert result.exit_code == 0, result.output
    out = tmp_path / "temporal"
    summary = json.loads((out / "summary.json").read_text())
    assert (
        summary["input_coverage"]
        == json.loads((report_root / "summary.json").read_text())["coverage"]
    )
    assert "Uncovered valid pixels are excluded" in (out / "report.html").read_text()
    assert summary["candidate_pairs"] == summary["supported_pairs"] == 2
    pairs = read_csv(out / "pairs.csv")
    short = next(row for row in pairs if row["interval"] == "short")
    long = next(row for row in pairs if row["interval"] == "long")
    assert (
        float(short["label_change_pct"]) == float(short["prediction_change_pct"]) == 10
    )
    assert float(short["change_error_pp"]) == 0
    assert (
        float(long["label_change_pct"]) == 20
        and float(long["prediction_change_pct"]) == 50
    )
    assert float(long["change_error_pp"]) == 30
    assert (out / "report.html").is_file() and (out / "changes.png").is_file()
    assert (out / "pair_summaries.csv").is_file()
    assert (
        CliRunner().invoke(app, ["temporal-report", "--recipe", str(recipe)]).exit_code
        == 1
    )
    # Reporting can repeat without any training/model files.
    temporal_report(TemporalSettings(report_root, tmp_path / "again"))
    assert read_csv(tmp_path / "again/pairs.csv") == pairs


def test_no_pairs_and_unknown_metadata_need_no_raster_reads(tmp_path):
    root = saved_temporal_fixture(tmp_path)
    rows = read_csv(root / "sources.csv")
    for row in rows:
        row["region"] = ""
    csv_file(root / "sources.csv", rows)
    # Existing referenced rasters can be absent when there are no eligible pairs.
    for path in (tmp_path / "predictions").glob("*.tif"):
        path.unlink()
    temporal_report(TemporalSettings(root, tmp_path / "empty"))
    summary = json.loads((tmp_path / "empty/summary.json").read_text())
    assert summary["candidate_pairs"] == 0 and summary["source_exclusions"] == 3
    assert (tmp_path / "empty/report.html").is_file()


def test_bad_temporal_recipe_and_report_scope(tmp_path):
    recipe = tmp_path / "temporal.toml"
    recipe.write_text('report="r"\noutput="o"\nunknown=1\n')
    with pytest.raises(ValueError, match="Unknown temporal"):
        load_settings(recipe)
    root = saved_temporal_fixture(tmp_path)
    rows = read_csv(root / "sources.csv")
    rows[0]["scope"] = "chip_disjoint"
    csv_file(root / "sources.csv", rows)
    with pytest.raises(ValueError, match="scope/split"):
        temporal_report(TemporalSettings(root, tmp_path / "bad"))


def test_same_day_reversed_duplicates_are_one_observation_pair(tmp_path):
    path = tmp_path / "pairs.csv"
    rows = [source("a", "2021-01-01"), source("b", "2021-01-01")]
    csv_file(
        path,
        [
            dict(earlier_source="a", later_source="b"),
            dict(earlier_source="b", later_source="a"),
        ],
    )
    with pytest.raises(ValueError, match="duplicates"):
        select_pairs(rows, TemporalSettings(tmp_path, tmp_path / "out", pairs=path))
