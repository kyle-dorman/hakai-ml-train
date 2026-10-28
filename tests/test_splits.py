"""Scientific source assignments and manifest-only joins; no research payloads."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kelpseg.cli import app
from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.chip_inputs import IDENTITY_COLUMNS
from kelpseg.prepare.split_inputs import load_split_recipe, read_collection
from kelpseg.prepare.splits import (
    assign_sources,
    select_windows,
    summarize_assignments,
    validate_assignments,
    write_splits,
)


def source(region, day, satellite="2277", *, source_id=None, **changes):
    source_id = source_id or f"{region}_{day.replace('-', '')}_173136_{satellite}"
    row = dict.fromkeys(IDENTITY_COLUMNS, "")
    row.update(
        source_key=source_id,
        source_id=source_id,
        original_tiff=f"{source_id}.tif",
        dataset_id="fixture",
        release_id="v1",
        region=region,
        acquisition_date=day,
        row_offset="0",
        col_offset="0",
        original_height="1024",
        original_width="1024",
        satellite_id=satellite,
    )
    row.update(changes)
    return row


def write_csv(path, rows, columns=None):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def collection(tmp_path, rows):
    return read_collection(sources=write_csv(tmp_path / "sources.csv", rows))


def recipe(tmp_path, **directions):
    text = 'schema_version = 1\ntraining_only_regions = ["011", "012"]\n'
    for region, direction in directions.items():
        text += (
            f'\n[[regions]]\nregion = "{region}"\ndirection = "{direction}"\n'
            'first_cutoff = "2021-01-31"\nsecond_cutoff = "2021-02-28"\n'
        )
    path = tmp_path / "recipe.toml"
    path.write_text(text)
    return load_split_recipe(path)


def chosen(rows, experiment="baseline", variant="base"):
    return {
        row["source_id"]: row
        for row in rows
        if row["experiment"] == experiment and row["variant"] == variant
    }


@pytest.mark.parametrize(
    ("direction", "expected"),
    [
        ("forward", ["train", "train", "val", "val", "test"]),
        ("reverse", ["test", "test", "val", "val", "train"]),
    ],
)
def test_inclusive_temporal_cutoffs_and_same_spacecraft_different_days(
    tmp_path, direction, expected
):
    days = ["2021-01-30", "2021-01-31", "2021-02-01", "2021-02-28", "2021-03-01"]
    inputs = collection(tmp_path, [source("001", day) for day in days])
    rows = assign_sources(inputs, recipe(tmp_path, **{"001": direction}))
    baseline = chosen(rows)
    assert [baseline[row["source_id"]]["split"] for row in inputs] == expected
    assert {row["satellite_id"] for row in rows} == {"2277"}
    assert {row["region"] for row in rows} == {"001"}
    assert {row["experiment"] for row in rows} == {"baseline", "loro_001"}
    assert {row["split"] for row in chosen(rows, "loro_001").values()} == {"test"}


def test_crops_inherit_one_original_assignment_and_preserve_offsets(tmp_path):
    first = source("001", "2021-03-01", source_key="first_crop", row_offset="7")
    second = {**first, "source_key": "second_crop", "col_offset": "9"}
    inputs = collection(tmp_path, [first, second])
    settings = recipe(tmp_path, **{"001": "reverse"})
    rows = assign_sources(inputs, settings)
    assert len(rows) == 4  # One source x baseline/LORO x base/augmented.
    assert len(chosen(rows)) == 1
    assert list(chosen(rows).values())[0]["split"] == "train"
    output = write_splits(inputs, rows, settings, tmp_path / "splits")
    with (output / "chip_metadata.csv").open() as stream:
        reader = csv.DictReader(stream)
        assert tuple(reader.fieldnames) == IDENTITY_COLUMNS
        exports = list(reader)
    assert {row["source_key"] for row in exports} == {"first_crop", "second_crop"}
    assert {row["source_id"] for row in exports} == {first["source_id"]}
    assert {row["row_offset"] for row in exports} == {"7"}
    assert {row["col_offset"] for row in exports} == {"0", "9"}
    summary = summarize_assignments(inputs, rows)
    assert summary["crop_rows"] == 2
    assert summary["original_sources"] == 1
    assert summary["assignments"]["baseline/base"]["source_counts"]["train"] == 1


def test_cleaned_controls_export_canonical_image_key_without_opening_tiffs(tmp_path):
    canonical = "001_20210301_173136_2277"
    (tmp_path / "sources.json").write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "key": canonical,
                        "identity": {
                            "source_key": "20210301_173136_2277",
                            "source_id": canonical,
                            "dataset_id": "declared_dataset",
                            "region_code": "001",
                            "acquisition_date": "2021-03-01",
                        },
                        "files": {
                            f"images/{canonical}.tif": {},
                            f"labels/{canonical}.tif": {},
                        },
                        "output_headers": {"image": {"height": 1024, "width": 2048}},
                    }
                ]
            }
        )
    )
    inputs = read_collection(cleaned=tmp_path, release_id="release-7")
    assert inputs[0]["source_key"] == canonical
    assert inputs[0]["dataset_id"] == "declared_dataset"
    assert inputs[0]["release_id"] == "release-7"
    assert inputs[0]["original_width"] == 2048
    assert inputs[0]["satellite_id"] == "2277"
    # Only the metadata control exists: no TIFF header or pixel read is possible.
    assert not (tmp_path / "images").exists()


def test_namespaced_originals_from_explicit_combined_collection(tmp_path):
    first = source("001", "2021-03-01", source_id="scene", source_key="coast_a/scene")
    second = {**first, "dataset_id": "other_coast", "source_key": "coast_b/scene"}
    inputs = collection(tmp_path, [first, second])
    assignments = assign_sources(inputs, recipe(tmp_path, **{"001": "reverse"}))
    baseline = [
        row
        for row in assignments
        if row["experiment"] == "baseline" and row["variant"] == "base"
    ]
    assert len(baseline) == 2
    assert {row["dataset_id"] for row in baseline} == {"fixture", "other_coast"}
    root = chip_controls(tmp_path / "chips", inputs)
    selected = select_windows(root, assignments)
    assert len(selected) == 6
    assert {row["dataset_id"] for row in selected} == {"fixture", "other_coast"}


@pytest.mark.parametrize(
    "change",
    [
        {"region": "002"},
        {"acquisition_date": "2021-03-02"},
        {"satellite_id": "2401"},
        {"original_height": "2048"},
        {"original_tiff": "different.tif"},
    ],
)
def test_conflicting_crops_fail(tmp_path, change):
    first = source("001", "2021-03-01", source_key="crop_a")
    second = {**first, "source_key": "crop_b", **change}
    with pytest.raises(PreparationError):
        collection(tmp_path, [first, second])


def test_duplicate_crop_keys_and_known_original_aliases_fail(tmp_path):
    first = source("001", "2021-03-01")
    with pytest.raises(PreparationError):
        collection(tmp_path, [first, first])
    alias = {
        **first,
        "source_key": "renamed_crop",
        "source_id": "renamed_original",
    }
    with pytest.raises(PreparationError):
        collection(tmp_path, [first, alias])


@pytest.mark.parametrize(
    "field", ["dataset_id", "release_id", "source_id", "region", "acquisition_date"]
)
def test_missing_scientific_identity_fails(tmp_path, field):
    row = source("001", "2021-03-01")
    row[field] = ""
    with pytest.raises(PreparationError):
        collection(tmp_path, [row])


def test_planet_satellite_comes_from_original_not_crop_suffix(tmp_path):
    row = source(
        "012",
        "2021-08-11",
        source_id="012_20210811_184459_09_245c_clip4",
        source_key="arbitrary_crop_2401",
    )
    row.pop("satellite_id")
    inputs = collection(tmp_path, [row])
    assert inputs[0]["satellite_id"] == "245c"


def test_explicit_satellite_allows_other_dataset_conventions(tmp_path):
    inputs = collection(
        tmp_path,
        [source("001", "2021-03-01", "spacecraft-a", source_id="survey-7")],
    )
    assert inputs[0]["source_id"] == "survey-7"
    assert inputs[0]["satellite_id"] == "spacecraft-a"


def test_cross_region_same_spacecraft_day_cannot_cross_baseline_partitions(tmp_path):
    inputs = collection(
        tmp_path,
        [source("001", "2021-01-01"), source("002", "2021-01-01")],
    )
    with pytest.raises(PreparationError):
        assign_sources(inputs, recipe(tmp_path, **{"001": "reverse", "002": "forward"}))


def test_region_date_groups_and_cross_region_companions_stay_together(tmp_path):
    inputs = collection(
        tmp_path,
        [
            source("001", "2021-03-01"),
            source("001", "2021-03-01", "2401"),
            source("002", "2021-03-01"),
        ],
    )
    rows = assign_sources(
        inputs, recipe(tmp_path, **{"001": "reverse", "002": "reverse"})
    )
    assert {row["split"] for row in chosen(rows).values()} == {"train"}
    fold = chosen(rows, "loro_001")
    for row in inputs[:2]:
        assert fold[row["source_id"]]["split"] == "test"
    assert fold[inputs[2]["source_id"]]["split"] == "unused"
    assert fold[inputs[2]["source_id"]]["reason"] == "held_out_satellite_day"


def test_region_date_validation_also_isolates_different_spacecraft(tmp_path):
    inputs = collection(
        tmp_path,
        [source("001", "2021-03-01", "2277"), source("001", "2021-03-01", "2401")],
    )
    assignments = list(
        chosen(assign_sources(inputs, recipe(tmp_path, **{"001": "reverse"}))).values()
    )
    assignments[1] = {**assignments[1], "split": "val"}
    with pytest.raises(PreparationError, match="region/date"):
        validate_assignments(assignments)


def test_optional_variants_loro_test_companions_and_other_temporal_test(tmp_path):
    inputs = collection(
        tmp_path,
        [
            source("001", "2021-03-01"),
            source("002", "2021-03-01"),
            source("002", "2021-01-02"),
            source("002", "2021-02-02"),
            source("002", "2021-03-02"),
            source("011", "2021-03-01"),
            source("012", "2021-08-11", "245c"),
        ],
    )
    rows = assign_sources(
        inputs, recipe(tmp_path, **{"001": "reverse", "002": "reverse"})
    )
    assert {row["experiment"] for row in rows} == {"baseline", "loro_001", "loro_002"}
    base, augmented = chosen(rows), chosen(rows, variant="augmented")
    for row in inputs:
        key = row["source_id"]
        if row["region"] in ("011", "012"):
            assert base[key]["split"] == "unused"
            assert base[key]["reason"] == "training_only_excluded"
            assert augmented[key]["split"] == "train"
        else:
            assert base[key]["split"] == augmented[key]["split"]
    fold = chosen(rows, "loro_001", "augmented")
    assert [fold[row["source_id"]]["split"] for row in inputs] == [
        "test",
        "unused",
        "val",
        "unused",
        "train",
        "unused",
        "train",
    ]
    assert fold[inputs[3]["source_id"]]["reason"] == "held_out_satellite_day"
    assert fold[inputs[1]["source_id"]]["reason"] == "nonheldout_temporal_test_unused"
    assert fold[inputs[5]["source_id"]]["reason"] == "held_out_satellite_day"


def test_unresolved_bc_token_is_explicit_only_on_isolated_optional_day(tmp_path):
    rows = [
        source("001", "2021-03-01"),
        source(
            "012", "2021-08-13", "241", source_id="012_20210813_193301_80_241_clip4"
        ),
    ]
    settings = recipe(tmp_path, **{"001": "reverse"})
    inputs = collection(tmp_path, rows)
    assignments = assign_sources(inputs, settings)
    assert (
        chosen(assignments, variant="augmented")[rows[1]["source_id"]]["satellite_id"]
        == "241"
    )
    rows.append(source("001", "2021-08-13", "2419"))
    with pytest.raises(PreparationError):
        assign_sources(collection(tmp_path, rows), settings)


def test_selected_evaluation_region_requires_rule(tmp_path):
    with pytest.raises(PreparationError):
        assign_sources(
            collection(tmp_path, [source("003", "2021-03-01")]),
            recipe(tmp_path, **{"001": "reverse"}),
        )


@pytest.mark.parametrize(
    "text",
    [
        "schema_version = 2\ntraining_only_regions = []\nregions = []\n",
        "schema_version = 1\ntraining_only_regions = []\nunknown = 3\n",
        'schema_version = 1\ntraining_only_regions = "011"\n',
        'schema_version = 1\ntraining_only_regions = ["011", "011"]\n',
        'schema_version = 1\ntraining_only_regions = []\n[[regions]]\nregion="001"\ndirection="future"\nfirst_cutoff="2021-01-31"\nsecond_cutoff="2021-02-28"\n',
        'schema_version = 1\ntraining_only_regions = []\n[[regions]]\nregion="001"\ndirection="forward"\nfirst_cutoff="2021-03-01"\nsecond_cutoff="2021-02-28"\n',
    ],
)
def test_invalid_split_recipe_fails(tmp_path, text):
    path = tmp_path / "bad.toml"
    path.write_text(text)
    with pytest.raises(PreparationError):
        load_split_recipe(path)


def chip_controls(root, inputs):
    root.mkdir()
    (root / "sources.json").write_text(json.dumps(inputs))
    rows = []
    for item in inputs:
        rows.extend(
            [
                dict(
                    source_key=item["source_key"],
                    row="0",
                    col="0",
                    disposition="retained",
                    payload=f"chips/{item['source_key']}/r0_c0.npz",
                    kelp_pixels="0",
                ),
                dict(
                    source_key=item["source_key"],
                    row="0",
                    col="256",
                    disposition="retained",
                    payload=f"chips/{item['source_key']}/r0_c256.npz",
                    kelp_pixels="1",
                ),
                dict(
                    source_key=item["source_key"],
                    row="256",
                    col="0",
                    disposition="omitted_nodata",
                    payload="",
                    kelp_pixels="0",
                ),
            ]
        )
    write_csv(root / "windows.csv", rows)
    return root


def test_window_join_keeps_overlapping_backgrounds_and_omissions_without_payload_reads(
    tmp_path,
):
    inputs = collection(tmp_path, [source("001", "2021-03-01", source_key="crop")])
    settings = recipe(tmp_path, **{"001": "reverse"})
    assignments = assign_sources(inputs, settings)
    root = chip_controls(tmp_path / "chips", inputs)
    rows = select_windows(root, assignments, experiment="baseline", variant="base")
    assert len(rows) == 3
    assert [row["split"] for row in rows] == ["train", "train", "unused"]
    assert rows[2]["reason"] == "omitted_nodata"
    assert rows[2]["payload"] == ""
    assert all(row["source_id"] == inputs[0]["source_id"] for row in rows)
    assert all(Path(row["chip_root"]) == root.resolve() for row in rows)
    assert Path(rows[0]["payload"]) == root / "chips/crop/r0_c0.npz"
    assert rows[0]["kelp_pixels"] == "0"  # Backgrounds are not filtered.
    assert rows[1]["col"] == "256"  # No old non-overlap-grid exclusion.
    # No NPZ was created: the selector joins controls only.
    output = write_splits(inputs, assignments, settings, tmp_path / "splits")
    assert select_windows(root, output / "assignments.csv") == rows


def test_window_join_reports_fold_unused_reason(tmp_path):
    inputs = collection(
        tmp_path,
        [source("001", "2021-03-01"), source("002", "2021-03-01")],
    )
    settings = recipe(tmp_path, **{"001": "reverse", "002": "reverse"})
    root = chip_controls(tmp_path / "chips", inputs)
    rows = select_windows(
        root,
        assign_sources(inputs, settings),
        experiment="loro_001",
        variant="augmented",
    )
    companions = [row for row in rows if row["region"] == "002" and row["payload"]]
    assert len(companions) == 2
    assert {row["split"] for row in companions} == {"unused"}
    assert {row["reason"] for row in companions} == {"held_out_satellite_day"}


def test_window_join_rejects_missing_source_or_original_assignment(tmp_path):
    inputs = collection(tmp_path, [source("001", "2021-03-01")])
    assignments = assign_sources(inputs, recipe(tmp_path, **{"001": "reverse"}))
    root = chip_controls(tmp_path / "chips", inputs)
    with pytest.raises(PreparationError):
        select_windows(root, [])
    (root / "sources.json").write_text("[]")
    with pytest.raises(PreparationError):
        select_windows(root, assignments)


def test_window_identity_rejects_duplicate_source_key_row_col(tmp_path):
    inputs = collection(tmp_path, [source("001", "2021-03-01")])
    assignments = assign_sources(inputs, recipe(tmp_path, **{"001": "reverse"}))
    root = chip_controls(tmp_path / "chips", inputs)
    with (root / "windows.csv").open() as stream:
        windows = list(csv.DictReader(stream))
    write_csv(root / "windows.csv", [*windows, windows[0]])
    with pytest.raises(PreparationError):
        select_windows(root, assignments)


def test_fresh_output_refusal(tmp_path):
    inputs = collection(tmp_path, [source("001", "2021-03-01")])
    settings = recipe(tmp_path, **{"001": "reverse"})
    assignments = assign_sources(inputs, settings)
    output = tmp_path / "splits"
    write_splits(inputs, assignments, settings, output)
    assert {path.name for path in output.iterdir()} == {
        "collection.csv",
        "chip_metadata.csv",
        "assignments.csv",
        "recipe.json",
        "summary.json",
    }
    with pytest.raises(PreparationError):
        write_splits(inputs, assignments, settings, output)


@pytest.mark.parametrize(
    "change", [{"acquisition_date": "2021-03-02"}, {"satellite_id": "2401"}]
)
def test_explicit_planet_metadata_agrees_with_original_name(tmp_path, change):
    row = source("001", "2021-03-01")
    row.update(change)
    with pytest.raises(PreparationError, match="disagrees"):
        collection(tmp_path, [row])


def test_satellite_whitespace_cannot_bypass_group_isolation(tmp_path):
    rows = [source("001", "2021-01-01"), source("002", "2021-01-01")]
    rows[1]["satellite_id"] = "2277 "
    with pytest.raises(PreparationError, match="satellite/day"):
        assign_sources(
            collection(tmp_path, rows),
            recipe(tmp_path, **{"001": "reverse", "002": "forward"}),
        )


@pytest.mark.parametrize("field", ["source_key", "original_tiff"])
def test_collection_references_are_portable(tmp_path, field):
    row = source("001", "2021-03-01")
    row[field] = "/machine/specific/scene.tif"
    with pytest.raises(PreparationError, match="portable relative"):
        collection(tmp_path, [row])


@pytest.mark.parametrize(
    ("text", "details"),
    [
        (
            "schema_version = 1\ntraining_only_regions = []\nregions = []\nstray_setting = true\n",
            ("unknown", "stray_setting"),
        ),
        (
            "schema_version = 1\nregions = []\n",
            ("missing", "training_only_regions"),
        ),
        (
            "schema_version = 1\ntraining_only_regions = []\n"
            '[[regions]]\nregion = "003"\ndirection = "reverse"\n'
            'first_cutof = "2021-01-31"\nsecond_cutoff = "2021-02-28"\n',
            ("003", "first_cutof", "first_cutoff"),
        ),
    ],
)
def test_recipe_errors_locate_unknown_and_missing_settings(tmp_path, text, details):
    path = tmp_path / "recipe.toml"
    path.write_text(text)
    with pytest.raises(PreparationError) as error:
        load_split_recipe(path)
    message = str(error.value).lower()
    assert all(detail in message for detail in details)


def test_source_error_identifies_csv_row_and_source_key(tmp_path):
    valid = source("001", "2021-03-01")
    invalid = source("001", "2021-03-02", source_key="bad_crop", row_offset="oops")
    with pytest.raises(PreparationError) as error:
        collection(tmp_path, [valid, invalid])
    message = str(error.value).lower()
    assert "row 3" in message
    assert "bad_crop" in message


def test_split_library_logs_main_phases_without_printing(tmp_path, caplog, capsys):
    with caplog.at_level(logging.INFO, logger="kelpseg.prepare"):
        inputs = collection(tmp_path, [source("001", "2021-03-01")])
        settings = recipe(tmp_path, **{"001": "reverse"})
        assignments = assign_sources(inputs, settings)
        output = write_splits(inputs, assignments, settings, tmp_path / "splits")
        chips = chip_controls(tmp_path / "chips", inputs)
        selected = select_windows(chips, output / "assignments.csv")
    messages = caplog.text.lower()
    for detail in (
        "recipe",
        "sources.csv",
        "baseline",
        "loro_001",
        "validat",
        "collection.csv",
        "windows.csv",
    ):
        assert detail in messages
    assert len(selected) == 3
    assert capsys.readouterr() == ("", "")


def test_split_cli_dry_run_logs_progress_and_restores_logging(tmp_path):
    source_csv = write_csv(tmp_path / "sources.csv", [source("001", "2021-03-01")])
    recipe(tmp_path, **{"001": "reverse"})
    output = tmp_path / "splits"
    logger = logging.getLogger("kelpseg.prepare")
    previous = logger.level, logger.propagate, tuple(logger.handlers)
    result = CliRunner().invoke(
        app,
        [
            "split",
            "--sources",
            str(source_csv),
            "--recipe",
            str(tmp_path / "recipe.toml"),
            "--output",
            str(output),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "recipe" in result.stderr.lower()
    assert "sources.csv" in result.stderr
    assert "baseline" in result.stderr.lower()
    assert "Dry run valid" in result.stdout
    assert not output.exists()
    assert not output.with_name(f".{output.name}.incomplete").exists()
    assert (logger.level, logger.propagate, tuple(logger.handlers)) == previous
