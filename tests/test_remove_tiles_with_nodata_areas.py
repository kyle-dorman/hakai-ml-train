from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from src.prepare.remove_tiles_with_nodata_areas import (
    REPORT_COLUMNS,
    filter_nodata_chips,
    parse_threshold,
)

MANIFEST_COLUMNS = [
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "total_pixel_count",
    "nodata_pixel_count",
    "nodata_pct",
    "fixture_note",
]


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _fixture(tmp_path: Path) -> tuple[Path, Path, list[dict[str, str]]]:
    root = tmp_path / "chips"
    chip_dir = root / "all"
    chip_dir.mkdir(parents=True)
    rows: list[dict[str, str]] = []
    for index, nodata_count in enumerate((0, 99, 100, 101)):
        chip_id = f"chip_{index}"
        relative = f"all/{chip_id}.npz"
        image = np.ones((10, 100, 2), dtype=np.uint8)
        image.reshape(-1, 2)[:nodata_count] = 0
        np.savez_compressed(root / relative, image=image, label=np.zeros((10, 100)))
        rows.append(
            {
                "chip_id": chip_id,
                "chip_path": relative,
                "source_tiff_id": f"source_{index // 2}",
                "dataset": "fixture",
                "region_id": f"region_{index % 2}",
                "total_pixel_count": "1000",
                "nodata_pixel_count": str(nodata_count),
                "nodata_pct": str(nodata_count / 10),
                "fixture_note": "preserved",
            }
        )
    manifest = root / "chip_manifest.csv"
    _write_manifest(manifest, rows)
    return root, manifest, rows


def _run(
    root: Path,
    manifest: Path,
    *,
    apply: bool,
    report_name: str = "report.csv",
    failure_hook=None,
):
    return filter_nodata_chips(
        chip_root=root,
        manifest=manifest,
        max_nodata_pct="10",
        report_output=root / report_name,
        apply=apply,
        failure_hook=failure_hook,
        producer_command="fixture command",
    )


def test_dry_run_uses_inclusive_threshold_without_mutation(tmp_path: Path) -> None:
    root, manifest, _ = _fixture(tmp_path)
    manifest_before = manifest.read_bytes()
    chips_before = {
        path: path.read_bytes() for path in sorted((root / "all").glob("*.npz"))
    }

    result = _run(root, manifest, apply=False)

    assert result.status == "reported"
    assert (result.total_count, result.kept_count, result.removed_count) == (4, 3, 1)
    report = _read_csv(root / "report.csv")
    assert list(report[0]) == REPORT_COLUMNS
    assert [row["action"] for row in report] == ["keep", "keep", "keep", "remove"]
    assert report[2]["nodata_pct"] == "10.0"
    assert report[2]["threshold_pct"] == "10"
    assert manifest.read_bytes() == manifest_before
    assert {path: path.read_bytes() for path in chips_before} == chips_before
    assert not (root / "filter_history").exists()
    assert not (root / ".nodata_filter_transactions").exists()


@pytest.mark.parametrize("value", ["-0.1", "100.1", "nan", "inf", "word"])
def test_threshold_must_be_finite_percent(value: str) -> None:
    with pytest.raises(ValueError, match=r"\[0, 100\]"):
        parse_threshold(value)


@pytest.mark.parametrize("duplicate_column", ["chip_id", "chip_path"])
def test_duplicate_identity_is_rejected(tmp_path: Path, duplicate_column: str) -> None:
    root, manifest, rows = _fixture(tmp_path)
    rows[1][duplicate_column] = rows[0][duplicate_column]
    _write_manifest(manifest, rows)

    with pytest.raises(RuntimeError, match=f"Duplicate {duplicate_column}"):
        _run(root, manifest, apply=False)


def test_missing_chip_and_inconsistent_percentage_are_rejected(tmp_path: Path) -> None:
    root, manifest, rows = _fixture(tmp_path)
    (root / rows[0]["chip_path"]).unlink()
    with pytest.raises(FileNotFoundError, match="Manifest chip is missing"):
        _run(root, manifest, apply=False)

    np.savez_compressed(
        root / rows[0]["chip_path"], image=np.ones((1, 1)), label=np.zeros((1, 1))
    )
    rows[1]["nodata_pct"] = "9.8"
    _write_manifest(manifest, rows)
    with pytest.raises(RuntimeError, match="nodata_pct is inconsistent"):
        _run(root, manifest, apply=False)


def test_apply_preserves_evidence_and_is_idempotent(tmp_path: Path) -> None:
    root, manifest, original_rows = _fixture(tmp_path)
    manifest_before = manifest.read_bytes()
    result = _run(root, manifest, apply=True)

    assert result.status == "applied"
    assert (result.total_count, result.kept_count, result.removed_count) == (4, 3, 1)
    assert [row["chip_id"] for row in _read_csv(manifest)] == [
        "chip_0",
        "chip_1",
        "chip_2",
    ]
    assert not (root / original_rows[3]["chip_path"]).exists()
    history = root / "filter_history" / "nodata_10"
    assert (history / "pre_filter_manifest.csv").read_bytes() == manifest_before
    removal = _read_csv(history / "removal_manifest.csv")
    assert removal == [original_rows[3]]
    metadata = json.loads((history / "filter_metadata.json").read_text())
    assert metadata["status"] == "complete"
    assert metadata["threshold_pct"] == "10"
    assert metadata["pre_filter_count"] == 4
    assert metadata["retained_count"] == 3
    assert metadata["removed_count"] == 1
    assert not (root / ".nodata_filter_transactions").exists()

    manifest_after = manifest.read_bytes()
    metadata_after = (history / "filter_metadata.json").read_bytes()
    repeated = _run(root, manifest, apply=True)
    assert repeated.status == "already_applied"
    assert manifest.read_bytes() == manifest_after
    assert (history / "filter_metadata.json").read_bytes() == metadata_after


def test_apply_with_no_rejections_is_idempotent(tmp_path: Path) -> None:
    root, manifest, _ = _fixture(tmp_path)
    report = root / "report_100.csv"

    applied = filter_nodata_chips(
        chip_root=root,
        manifest=manifest,
        max_nodata_pct="100",
        report_output=report,
        apply=True,
    )
    repeated = filter_nodata_chips(
        chip_root=root,
        manifest=manifest,
        max_nodata_pct="100.0",
        report_output=report,
        apply=True,
    )

    assert (applied.status, applied.kept_count, applied.removed_count) == (
        "applied",
        4,
        0,
    )
    assert repeated.status == "already_applied"
    history = root / "filter_history" / "nodata_100"
    assert _read_csv(history / "removal_manifest.csv") == []
    assert len(_read_csv(manifest)) == 4
    assert not (root / ".nodata_filter_transactions").exists()


def test_failure_after_quarantine_rolls_back(tmp_path: Path) -> None:
    root, manifest, rows = _fixture(tmp_path)
    manifest_before = manifest.read_bytes()

    def fail(point: str) -> None:
        if point == "after_quarantine":
            raise RuntimeError("simulated interruption")

    with pytest.raises(RuntimeError, match="simulated interruption"):
        _run(root, manifest, apply=True, failure_hook=fail)

    assert manifest.read_bytes() == manifest_before
    assert all((root / row["chip_path"]).is_file() for row in rows)
    assert not (root / ".nodata_filter_transactions").exists()
    assert not (root / "filter_history").exists()


def test_post_commit_interruption_recovers_on_rerun(tmp_path: Path) -> None:
    root, manifest, rows = _fixture(tmp_path)

    def fail(point: str) -> None:
        if point == "after_manifest_replace":
            raise RuntimeError("simulated post-commit interruption")

    with pytest.raises(RuntimeError, match="simulated post-commit interruption"):
        _run(root, manifest, apply=True, failure_hook=fail)

    assert [row["chip_id"] for row in _read_csv(manifest)] == [
        "chip_0",
        "chip_1",
        "chip_2",
    ]
    transaction_root = root / ".nodata_filter_transactions" / "nodata_10"
    assert (transaction_root / "quarantine" / rows[3]["chip_path"]).is_file()

    recovered = _run(root, manifest, apply=True)
    assert recovered.status == "already_applied"
    assert not (root / ".nodata_filter_transactions").exists()
    assert (root / "filter_history" / "nodata_10" / "filter_metadata.json").is_file()
