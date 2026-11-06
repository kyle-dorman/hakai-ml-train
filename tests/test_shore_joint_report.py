"""Joint recall reports preserve saved scoring and explicitly reconcile exclusions."""

import csv
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_reporting import csv_file, raster, saved_tiff
from test_shore_distance_report import shoreline

from kelpseg.reporting.inputs import ReportSettings, load_settings
from kelpseg.reporting.report import report
from kelpseg.reporting.shore_clusters import UNKNOWN_CLUSTER


def test_joint_report_preserves_scores_and_accounts_for_exclusions(
    tmp_path: Path,
) -> None:
    probability = np.array([[0.8, 0.2, 0.7, np.nan, 0.9, 0.9]], np.float32)
    labels = np.array([[1, 1, 1, 1, 0, 3]], np.uint8)
    settings, source = saved_tiff(tmp_path, probability, labels)
    shore = shoreline(
        tmp_path, source, [[0, 1, 0, 0, 0, 255]], [[30, 0, 120, 500, 60, np.nan]]
    )
    report(replace(settings, shoreline=shore))
    original = json.loads((settings.output / "summary.json").read_text())
    inventory = tmp_path / "inventory"
    inventory.mkdir()
    identity = dict(
        source_id="original",
        source_keys="a",
        dataset_id="dataset",
        release_id="release",
        region="001",
        acquisition_date="2020-01-01",
    )
    csv_file(inventory / "cluster_sources.csv", [dict(identity, cluster_ids="ids.tif")])
    csv_file(
        inventory / "clusters.csv",
        [
            dict(identity, cluster_id=1, pixels=2, size_bin="1-10", truncated=False),
            dict(identity, cluster_id=2, pixels=2, size_bin="1-10", truncated=True),
        ],
    )
    raster(
        inventory / "ids.tif",
        np.array([[1, 1, 2, 2, 0, UNKNOWN_CLUSTER]], np.uint32),
        nodata=int(UNKNOWN_CLUSTER),
    )
    output = tmp_path / "joint-report"
    report(
        replace(settings, output=output, shoreline=shore, cluster_inventory=inventory)
    )
    result = json.loads((output / "summary.json").read_text())
    assert result["global"] == original["global"]
    assert result["coverage"] == original["coverage"]
    assert result["shoreline"]["global_bands"] == original["shoreline"]["global_bands"]
    accounting = result["joint_clusters"]["reconciliation"]
    assert accounting["all"] == {"tp": 2, "fn": 1}
    assert accounting["interior"] == {"tp": 1, "fn": 1}
    assert accounting["truncated"] == {"tp": 1, "fn": 0}
    assert accounting["all_land_unknown"] == {"tp": 0, "fn": 1}
    assert accounting["full_source_labeled_kelp_pixels"] == 4
    assert accounting["excluded_outside_report_label_footprint"] == 0
    assert accounting["excluded_uncovered_kelp_pixels"] == 1
    assert accounting["unassigned_scored_kelp_pixels"] == 0
    rows = list(csv.DictReader((output / "joint_sources.csv").open()))
    assert all("fp" not in row for row in rows)
    assert any(row["recall"] == "" for row in rows)
    assert (output / "joint_report.html").is_file()
    assert "joint_report.html" in (output / "report.html").read_text()


def test_joint_settings_require_shoreline_and_nearshore_edge(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="shoreline"):
        ReportSettings(
            tmp_path, tmp_path / "out", cluster_inventory=tmp_path / "inventory"
        )
    with pytest.raises(ValueError, match="120 m"):
        ReportSettings(
            tmp_path,
            tmp_path / "out",
            shoreline=tmp_path / "shore",
            cluster_inventory=tmp_path / "inventory",
            distance_edges=(0, 30, 500),
        )
    recipe = tmp_path / "report.toml"
    recipe.write_text(
        'predictions="predictions"\noutput="out"\nshoreline="shore"\ncluster_inventory="inventory"\n'
    )
    assert load_settings(recipe).cluster_inventory == tmp_path / "inventory"
