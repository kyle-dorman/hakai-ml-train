"""Joint recall pools preserve source/date support and diagnose domination."""

from pathlib import Path

import pytest

from kelpseg.reporting.shore_joint_summary import build_joint_tables
from kelpseg.reporting.shore_joint_views import write_joint_views


def observation(
    source: str,
    date: str,
    band: str,
    tp: int,
    fn: int,
    *,
    size: str = "101-1000",
    component_scope: str = "interior_only",
) -> dict:
    """Build one counted source observation at a fixed metric grid area."""
    return dict(
        source_id=source,
        acquisition_date=date,
        region="004",
        component_scope=component_scope,
        distance_band=band,
        size_bin=size,
        labeled_kelp_pixels=tp + fn,
        labeled_kelp_area_m2=(tp + fn) * 9,
        tp=tp,
        fn=fn,
        recall=tp / (tp + fn) if tp + fn else None,
    )


def observations() -> list[dict]:
    """Create repeated-date TIFFs, unmatched sides, and separate land/unknown."""
    return [
        observation("a", "2020-01-01", "0-30", 1, 4),
        observation("a", "2020-01-01", "30-60", 1, 4),
        observation("a", "2020-01-01", "120-250", 24, 6),
        observation("b", "2020-01-01", "60-120", 18, 12),
        observation("b", "2020-01-01", "250-500", 8, 2),
        observation("c", "2020-01-02", "0-30", 42, 18),
        observation("d", "2020-01-03", "500+", 48, 12),
        observation("a", "2020-01-01", "land", 500, 0),
        observation("b", "2020-01-01", "unknown", 0, 400),
    ]


def test_sources_dates_and_paired_comparisons_pool_counts_before_recall() -> None:
    tables = build_joint_tables(observations())
    near = next(
        row
        for row in tables["joint_nearshore_regions"]
        if row["shore_zone"] == "nearshore"
    )
    assert near["labeled_kelp_pixels"] == 100
    assert near["labeled_kelp_area_m2"] == 900
    assert near["tp"] == 62 and near["fn"] == 38
    assert near["recall"] == pytest.approx(0.62)
    assert near["source_count"] == 3 and near["date_count"] == 2
    assert near["dominant_source_id"] == "c"
    assert near["max_source_kelp_share"] == pytest.approx(0.6)
    assert near["dominant_date"] == "2020-01-02"
    source_a = next(
        row
        for row in tables["joint_nearshore_sources"]
        if row["source_id"] == "a" and row["shore_zone"] == "nearshore"
    )
    assert source_a["labeled_kelp_pixels"] == 10
    assert source_a["source_count"] == source_a["date_count"] == 1
    compare = tables["joint_nearshore_comparisons"][0]
    assert compare["recall_gap"] == pytest.approx(-0.18)
    assert compare["paired_source_count"] == 2
    assert compare["paired_source_nearshore_lower_count"] == 2
    assert compare["paired_source_pooled_gap"] == pytest.approx(-0.3)
    assert compare["paired_date_count"] == 1
    assert compare["paired_date_nearshore_lower_count"] == 1
    assert compare["paired_date_pooled_gap"] == pytest.approx(-0.3)
    # Missing offshore for c and nearshore for d remain undefined, never zero recall.
    source_c = next(
        row for row in tables["joint_source_comparisons"] if row["source_id"] == "c"
    )
    assert source_c["offshore_recall"] is None and source_c["recall_gap"] is None
    assert not source_c["paired_support"]


def test_largest_source_date_sensitivity_and_sparse_support() -> None:
    compare = build_joint_tables(observations())["joint_nearshore_comparisons"][0]
    assert compare["largest_ocean_source"] == "c"
    assert compare["largest_ocean_source_share"] == pytest.approx(0.3)
    assert compare["without_largest_source_gap"] == pytest.approx(-0.3)
    assert compare["largest_ocean_date"] == "2020-01-01"
    assert compare["largest_ocean_date_share"] == pytest.approx(0.4)
    assert compare["without_largest_date_gap"] == pytest.approx(-0.1)
    assert "nearshore:one_source>50%" in compare["support_flags"]
    assert "nearshore:<3_dates" in compare["support_flags"]
    assert "nearshore:<100_pixels" not in compare["support_flags"]


def test_empty_groups_and_component_scopes_remain_explicit() -> None:
    rows = [
        observation("a", "2020-01-01", band, 0, 0, size="1-10")
        for band in ("0-30", "120-250")
    ]
    rows += [
        observation("a", "2020-01-01", "0-30", 2, 3, component_scope="all_observed"),
        observation("a", "2020-01-01", "0-30", 1, 1),
        observation("a", "2020-01-01", "0-30", 1, 2, component_scope="truncated_only"),
    ]
    tables = build_joint_tables(rows)
    empty = next(
        row
        for row in tables["joint_nearshore_comparisons"]
        if row["size_bin"] == "1-10"
    )
    assert empty["nearshore_recall"] is None and empty["offshore_recall"] is None
    assert empty["nearshore_source_count"] == empty["nearshore_date_count"] == 0
    assert empty["nearshore_max_source_kelp_share"] is None
    assert empty["paired_source_count"] == 0
    assert empty["paired_date_median_gap"] is None
    assert empty["without_largest_source_gap"] is None
    grouped = {
        row["component_scope"]: row
        for row in tables["joint_regions"]
        if row["size_bin"] == "101-1000"
    }
    assert (
        grouped["all_observed"]["tp"]
        == grouped["interior_only"]["tp"] + grouped["truncated_only"]["tp"]
    )
    assert (
        grouped["all_observed"]["fn"]
        == grouped["interior_only"]["fn"] + grouped["truncated_only"]["fn"]
    )


def test_readable_report_and_plots_preserve_undefined_values(tmp_path: Path) -> None:
    rows = observations()
    rows += [dict(row, component_scope="all_observed") for row in rows]
    tables = build_joint_tables(rows)
    path = write_joint_views(tmp_path, tables)
    text = path.read_text()
    assert "Region 004" in text and "N/A" in text
    assert "False positives have no true label-cluster size" in text
    assert "one source/date supplying over 50%" in text
    assert "joint_reconciliation.csv" in text
    for name in (
        "joint_recall_all.png",
        "joint_recall_interior.png",
        "joint_recall_gaps.png",
    ):
        assert (tmp_path / name).is_file()
