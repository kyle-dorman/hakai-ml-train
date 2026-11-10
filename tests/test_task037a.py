"""Guard the comparison against mislabeling the validation regions."""

from pathlib import Path

import pytest

from kelpseg.reporting.inputs import read_csv


def test_comparison_geography_matches_region_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check California and Baja labels against the canonical region names."""
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "examples"))
    from task037a_compare import geography

    for row in read_csv(root / "configs/regions.csv"):
        region = row["region_code"]
        if region in ("011", "012"):
            continue
        expected = "Baja" if row["region_name"].startswith("baja_") else "California"
        assert geography(region) == expected
