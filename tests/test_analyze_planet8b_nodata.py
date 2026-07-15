from analyze_planet8b_nodata import candidate_rows, distribution_rows


def _row(
    chip_id: str,
    source_id: str,
    region_id: str,
    nodata_pct: float,
    class_1: int,
) -> dict[str, object]:
    return {
        "chip_id": chip_id,
        "chip_path": f"all/{chip_id}.npz",
        "source_tiff_id": source_id,
        "dataset": "ca",
        "region_id": region_id,
        "region_name": region_id,
        "total_pixel_count": 100,
        "class_1_pixel_count": class_1,
        "nodata_pixel_count": round(nodata_pct),
        "nodata_pct": nodata_pct,
    }


def test_candidate_boundary_and_source_elimination() -> None:
    rows = [
        _row("a", "source_a", "region_a", 50, 10),
        _row("b", "source_a", "region_a", 51, 20),
        _row("c", "source_b", "region_b", 75, 30),
    ]

    summary = candidate_rows(rows, (50,))
    global_row = next(row for row in summary if row["scope"] == "global")
    region_b = next(row for row in summary if row["scope"] == "region_b")

    assert global_row["retained_chips"] == 1
    assert global_row["removed_chips"] == 2
    assert global_row["source_tiffs_affected"] == 2
    assert global_row["source_tiffs_eliminated"] == 1
    assert global_row["class_1_pixels_removed"] == 50
    assert region_b["region_eliminated"] is True


def test_distribution_includes_global_and_region_percentiles() -> None:
    rows = [
        _row("a", "source_a", "region_a", 0, 0),
        _row("b", "source_b", "region_a", 100, 0),
    ]

    distribution = distribution_rows(rows)

    assert len(distribution) == 2 * 11
    global_median = next(
        row
        for row in distribution
        if row["scope"] == "global" and row["percentile"] == 50
    )
    assert global_median["nodata_pct"] == 50
