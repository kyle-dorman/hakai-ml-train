"""Temporal grouping preserves observation support and summarizes pair errors."""

import pytest

from kelpseg.reporting.temporal_summary import summarize_pairs, summarize_sources
from kelpseg.reporting.temporal_views import write_temporal_report


def source(key, day, *, region="001", dataset="ca_bc", tp=1, fp=0, fn=0, tn=9):
    """Create one source-report-style CSV row with explicit counts and coverage."""
    pixels = tp + fp + fn + tn
    return dict(
        source_keys=key,
        dataset_id=dataset,
        release_id="v1",
        region=region,
        acquisition_date=day,
        tp=str(tp),
        fp=str(fp),
        fn=str(fn),
        tn=str(tn),
        scoreable_area_m2=str(pixels * 9),
        labeled_area_m2=str((tp + fn) * 9),
        predicted_area_m2=str((tp + fp) * 9),
        area_bias_m2=str((fp - fn) * 9),
        false_positive_area_m2=str(fp * 9),
        false_negative_area_m2=str(fn * 9),
        total_pixels=str(pixels),
        valid_pixels=str(pixels),
        nodata_pixels="0",
        predicted_valid_pixels=str(pixels),
        uncovered_valid_pixels="0",
        ignored_valid_pixels="0",
        scoreable_pixels=str(pixels),
    )


def test_temporal_grouping_pools_counts_and_retains_year_month_support():
    rows = [
        source("a", "2020-01-01", tp=1, fp=1),
        source("b", "2020-01-01", tp=9, fn=1),
        source("c", "2021-01-03", tp=0),
        source("d", "2021-02-03", region="002"),
        source("e", "2021-01-03", dataset="other"),
    ]
    tables = summarize_sources(rows)
    day = tables["dates"][0]
    assert day["source_observations"] == 2
    assert day["tp"] == 10 and day["fp"] == day["fn"] == 1
    assert day["iou"] == 10 / 12
    assert day["labeled_area_m2"] == day["predicted_area_m2"] == 99
    assert day["scoreable_pixels"] == day["pixels"] == 30
    month = tables["months"][0]
    assert month["source_observations"] == 3
    assert month["represented_dates"] == "2020-01-01;2021-01-03"
    assert month["represented_date_count"] == 2
    assert len(tables["years"]) == 4
    assert len(tables["year_months"]) == 4
    assert len(tables["months"]) == 3
    assert not tables["source_exclusions"]
    # Grouping neither changes CSV inputs nor claims the duplicate date is unique area.
    assert rows[0]["tp"] == "1"


def test_missing_identity_exclusions_and_zero_kelp_metrics():
    tables = summarize_sources(
        [
            source("a", "", region="001"),
            source("b", "2020-01-01", region=""),
            source("c", "2020-01-01", tp=0),
        ]
    )
    assert [row["reason"] for row in tables["source_exclusions"]] == [
        "missing_date",
        "missing_region",
    ]
    assert tables["dates"][0]["iou"] is None
    assert tables["dates"][0]["labeled_prevalence"] == 0
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        summarize_sources([source("broken", "not-a-date")])


def test_pair_summaries_do_not_pool_baselines_or_omit_unavailable_pairs():
    rows = []
    for error, status in [
        (0, "supported"),
        (20, "supported"),
        (None, "supported"),
        (None, "incompatible_grid"),
    ]:
        rows.append(
            dict(
                dataset_id="d",
                release_id="v",
                region="001",
                interval="short",
                status=status,
                change_error_pp=error,
            )
        )
    rows.append(dict(rows[0], region="002", change_error_pp=-100))
    result = summarize_pairs(rows)
    first = result[0]
    assert first["pairs"] == 4
    assert first["supported_pairs"] == 3
    assert first["percentage_defined_pairs"] == 2
    assert first["percentage_undefined_pairs"] == 1
    assert first["unavailable_pairs"] == 1
    assert first["median_change_error_pp"] == 10
    assert first["mean_absolute_change_error_pp"] == 10
    assert result[1]["median_change_error_pp"] == -100
    assert result[1]["median_absolute_change_error_pp"] == 100


def test_empty_and_populated_temporal_views(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    write_temporal_report(empty, {}, summarize_sources([]), [], [])
    assert (empty / "changes.png").is_file()
    assert (empty / "observations.png").is_file()
    assert "No observations" in (empty / "report.html").read_text()
    assert "not independent" in (empty / "report.html").read_text()
    full = tmp_path / "full"
    full.mkdir()
    pair = dict(
        dataset_id="ca_bc",
        release_id="v1",
        region="001",
        interval="short",
        status="supported",
        label_change_pct=10,
        prediction_change_pct=10,
        change_error_pp=0,
    )
    write_temporal_report(
        full,
        dict(run_id="run", scope="tiff_tiled", split="val"),
        summarize_sources([source("a", "2020-01-01")]),
        [pair],
        summarize_pairs([pair]),
    )
    assert (full / "changes.png").stat().st_size > 1000
    assert "percentage points" in (full / "report.html").read_text()
