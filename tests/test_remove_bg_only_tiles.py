from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from src.prepare.remove_bg_only_tiles import (
    CLASS_PRESENCE_ORDER,
    SELECTION_COLUMNS,
    build_training_selection,
    main,
    remove_bg_only_tiles,
)

MANIFEST_COLUMNS = [
    "chip_id",
    "source_tiff_id",
    "region_id",
    "total_pixel_count",
    "class_0_pixel_count",
    "class_1_pixel_count",
    "ignore_pixel_count",
    "nodata_pixel_count",
]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "chips"
    chip_dir = root / "all"
    chip_dir.mkdir(parents=True)
    rows: list[dict[str, str]] = []
    count_sets = {
        "positive": (5, 2, 3, 2),
        "clean": (10, 0, 0, 0),
        "mixed": (6, 0, 4, 3),
        "ignore": (0, 0, 10, 8),
    }
    for region_index in range(2):
        region_id = f"region_{region_index}"
        source_id = f"source_{region_index}"
        for category, counts in count_sets.items():
            copies = 1 if category == "positive" else 2
            for copy in range(copies):
                chip_id = f"{source_id}_{category}_{copy}"
                np.savez_compressed(chip_dir / f"{chip_id}.npz", marker=chip_id)
                class_0, class_1, ignore, nodata = counts
                rows.append(
                    {
                        "chip_id": chip_id,
                        "source_tiff_id": source_id,
                        "region_id": region_id,
                        "total_pixel_count": "10",
                        "class_0_pixel_count": str(class_0),
                        "class_1_pixel_count": str(class_1),
                        "ignore_pixel_count": str(ignore),
                        "nodata_pixel_count": str(nodata),
                    }
                )
    manifest = root / "chip_manifest.csv"
    with manifest.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return root, manifest


def _chip_snapshot(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in sorted((root / "all").glob("*.npz"))}


def test_exclude_all_classifies_and_reports_without_npz_mutation(
    tmp_path: Path,
) -> None:
    root, manifest = _fixture(tmp_path)
    before = _chip_snapshot(root)
    output = root / "background_selection" / "training_selection.csv"
    summary = root / "background_selection" / "selection_summary.csv"

    result = build_training_selection(
        manifest,
        policy="exclude_all",
        output_manifest=output,
        summary_output=summary,
    )

    assert (result.total_count, result.selected_count, result.excluded_count) == (
        14,
        2,
        12,
    )
    selections = _read_csv(output)
    assert list(selections[0]) == SELECTION_COLUMNS
    assert len({row["chip_id"] for row in selections}) == len(selections) == 14
    assert {row["class_presence"] for row in selections} == set(CLASS_PRESENCE_ORDER)
    assert all(
        (row["class_presence"] == "positive")
        == (row["selected_for_training"] == "true")
        for row in selections
    )
    assert {row["retain_fraction"] for row in selections} == {""}
    assert {row["seed"] for row in selections} == {""}

    global_rows = [row for row in _read_csv(summary) if row["scope"] == "global"]
    assert [row["class_presence"] for row in global_rows] == CLASS_PRESENCE_ORDER
    assert [int(row["chip_count"]) for row in global_rows] == [2, 4, 4, 4]
    assert [int(row["selected_chip_count"]) for row in global_rows] == [2, 0, 0, 0]
    assert int(global_rows[0]["class_1_pixel_count"]) == 4
    assert int(global_rows[2]["nodata_pixel_count"]) == 12
    assert _chip_snapshot(root) == before

    repeated = build_training_selection(
        manifest,
        policy="exclude_all",
        output_manifest=output,
        summary_output=summary,
    )
    assert repeated == result
    assert _chip_snapshot(root) == before


def test_retain_fraction_is_seeded_and_stratified_by_source_and_category(
    tmp_path: Path,
) -> None:
    root, manifest = _fixture(tmp_path)
    before = _chip_snapshot(root)

    selections = []
    for suffix in ("a", "b"):
        output = root / f"selection_{suffix}.csv"
        build_training_selection(
            manifest,
            policy="retain_fraction",
            retain_fraction="0.5",
            seed=41,
            output_manifest=output,
            summary_output=root / f"summary_{suffix}.csv",
        )
        selections.append(_read_csv(output))

    assert selections[0] == selections[1]
    retained = [
        row
        for row in selections[0]
        if row["class_presence"] != "positive"
        and row["selected_for_training"] == "true"
    ]
    assert len(retained) == 6
    retained_strata = {
        (row["region_id"], row["source_tiff_id"], row["class_presence"])
        for row in retained
    }
    assert len(retained_strata) == 6
    assert sum(row["selected_for_training"] == "true" for row in selections[0]) == 8
    assert {row["retain_fraction"] for row in selections[0]} == {"0.5"}
    assert {row["seed"] for row in selections[0]} == {"41"}
    assert _chip_snapshot(root) == before


def test_report_only_writes_summary_without_selection_manifest(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)
    summary = root / "report_only_summary.csv"

    result = build_training_selection(
        manifest,
        policy="exclude_all",
        output_manifest=None,
        summary_output=summary,
    )

    assert result.output_manifest is None
    assert summary.is_file()
    assert not (root / "training_selection.csv").exists()


def test_destructive_legacy_api_and_cli_fail_before_touching_npz(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _ = _fixture(tmp_path)
    before = _chip_snapshot(root)

    with pytest.raises(RuntimeError, match="Destructive background deletion"):
        remove_bg_only_tiles(root)
    with pytest.raises(SystemExit, match="2"):
        main([str(root)])

    assert _chip_snapshot(root) == before
    assert (
        "positional destructive directory mode was removed" in capsys.readouterr().err
    )


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("class_0_pixel_count", "-1", "nonnegative"),
        ("ignore_pixel_count", "2", "do not equal"),
        ("nodata_pixel_count", "4", "exceeds ignore"),
    ],
)
def test_invalid_manifest_counts_are_rejected(
    tmp_path: Path, column: str, value: str, message: str
) -> None:
    root, manifest = _fixture(tmp_path)
    rows = _read_csv(manifest)
    rows[0][column] = value
    with manifest.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(RuntimeError, match=message):
        build_training_selection(
            manifest,
            policy="exclude_all",
            output_manifest=root / "selection.csv",
            summary_output=root / "summary.csv",
        )


def test_duplicate_ids_and_canonical_overwrite_are_rejected(tmp_path: Path) -> None:
    root, manifest = _fixture(tmp_path)
    rows = _read_csv(manifest)
    rows[1]["chip_id"] = rows[0]["chip_id"].upper()
    with manifest.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(RuntimeError, match="Duplicate chip_id"):
        build_training_selection(
            manifest,
            policy="exclude_all",
            output_manifest=root / "selection.csv",
            summary_output=root / "summary.csv",
        )

    _, clean_manifest = _fixture(tmp_path / "clean")
    with pytest.raises(RuntimeError, match="canonical input manifest"):
        build_training_selection(
            clean_manifest,
            policy="exclude_all",
            output_manifest=clean_manifest,
            summary_output=clean_manifest.parent / "summary.csv",
        )
