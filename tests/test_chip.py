"""Bounded Rasterio fixtures for fixed-grid, one-pass native-band chipping."""

import csv
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from typer.testing import CliRunner

from kelpseg.chips import load_chip
from kelpseg.cli import app
from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.chip import chip_dataset
from kelpseg.prepare.chip_inputs import (
    IDENTITY_COLUMNS,
    ChipRecipe,
    axis_starts,
    build_chip_plan,
    chip_windows,
    load_chip_recipe,
)

NAMES = ("coastal_blue", "blue", "green_i", "green", "yellow", "red", "rededge", "nir")
RECIPE = ChipRecipe(
    source_band_names=NAMES, label_mapping={0: 0, 1: 1, 2: 0, 3: -100, 4: 0}
)
GRID = from_origin(100, 200, 3, 3)


def write_raster(path, values, *, transform=GRID, nodata=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=values.shape[-1],
        height=values.shape[-2],
        count=values.shape[0],
        dtype=values.dtype,
        crs="EPSG:32610",
        transform=transform,
        nodata=nodata,
    ) as output:
        output.write(values)


def fixture(root, *, height=3, width=5, key="scene", labels=True):
    image = np.broadcast_to(
        np.arange(1, 9, dtype=np.uint16)[:, None, None], (8, height, width)
    ).copy()
    target = np.zeros((1, height, width), dtype=np.uint8)
    write_raster(root / "images" / f"{key}.tif", image)
    if labels:
        write_raster(root / "labels" / f"{key}.tif", target)
    return image, target


def plan(root, recipe=RECIPE, *, labels=True, metadata=None, output="result"):
    return build_chip_plan(
        root / "images",
        root / "labels" if labels else None,
        root / output,
        recipe,
        metadata=metadata,
    )


def rows(output):
    with (output / "windows.csv").open(newline="") as stream:
        return list(csv.DictReader(stream))


def metadata_csv(path, records):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=IDENTITY_COLUMNS)
        writer.writeheader()
        writer.writerows(records)
    return path


def recipe_file(path, **changes):
    text = (
        Path(__file__).resolve().parents[1] / "configs/chip/planet8.toml"
    ).read_text()
    for old, new in changes.items():
        text = text.replace(old, new)
    path.write_text(text)
    return path


@pytest.mark.parametrize(
    "length,expected",
    [
        (1, [0]),
        (511, [0]),
        (512, [0]),
        (513, [0, 256]),
        (768, [0, 256]),
        (769, [0, 256, 512]),
        (1024, [0, 256, 512]),
    ],
)
def test_regular_grid_stops_at_first_complete_coverage(length, expected):
    assert axis_starts(length, 512, 256) == expected
    coverage = np.zeros((length, length), dtype=np.uint8)
    for window in chip_windows(length, length, 512, 256):
        row, col = int(window.row_off), int(window.col_off)
        height, width = int(window.height), int(window.width)
        assert row % 256 == col % 256 == 0
        assert height == min(512, length - row) and width == min(512, length - col)
        coverage[row : row + height, col : col + width] += 1
    assert coverage.all()


def test_partial_edge_round_trip_coordinates_and_padding(tmp_path):
    image, target = fixture(tmp_path, height=511, width=513)
    target[0, 3, 300] = 1
    write_raster(tmp_path / "labels/scene.tif", target)
    metadata = metadata_csv(
        tmp_path / "identity.csv",
        [
            {
                "source_key": "scene",
                "source_id": "original-scene",
                "original_tiff": "original.tif",
                "dataset_id": "ca_bc",
                "release_id": "v1",
                "region": "ca_001",
                "acquisition_date": "2021-07-01",
                "row_offset": 256,
                "col_offset": 512,
                "original_height": 1024,
                "original_width": 1536,
            }
        ],
    )
    output = chip_dataset(plan(tmp_path, metadata=metadata))
    records = rows(output)
    assert [
        (int(row["row"]), int(row["col"]), int(row["height"]), int(row["width"]))
        for row in records
    ] == [(0, 0, 511, 512), (0, 256, 511, 257)]
    restored = np.zeros_like(np.moveaxis(image, 0, -1))
    coverage = np.zeros((511, 513), dtype=np.uint8)
    for row in records:
        r, c, h, w = (int(row[key]) for key in ("row", "col", "height", "width"))
        assert int(row["original_row"]) == 256 + r
        assert int(row["original_col"]) == 512 + c
        loaded = load_chip(output / row["payload"], NAMES)
        assert loaded["padding"] == (0, 512 - h, 0, 512 - w)
        values = loaded["image"][:h, :w]
        np.testing.assert_array_equal(
            values, np.moveaxis(image[:, r : r + h, c : c + w], 0, -1)
        )
        np.testing.assert_array_equal(
            loaded["label"][:h, :w], target[0, r : r + h, c : c + w]
        )
        restored[r : r + h, c : c + w] = values
        coverage[r : r + h, c : c + w] += 1
        assert not loaded["image"][h:].any() and not loaded["image"][:, w:].any()
        assert np.all(loaded["label"][h:] == -100) and np.all(
            loaded["label"][:, w:] == -100
        )
    np.testing.assert_array_equal(restored, np.moveaxis(image, 0, -1))
    assert coverage.all() and coverage.max() == 2
    source = json.loads((output / "sources.json").read_text())[0]
    assert source["transform"] == list(GRID)[:6]
    assert source["crs"] == "EPSG:32610"
    assert (
        source["source_id"] == "original-scene"
        and source["original_tiff"] == "original.tif"
    )
    assert source["region"] == "ca_001" and source["acquisition_date"] == "2021-07-01"
    assert source["height"] == 511 and source["width"] == 513
    assert not output.with_name(f".{output.name}.incomplete").exists()


def test_nodata_threshold_inclusive_no_background_filter_or_omitted_payload(tmp_path):
    # Independent 4x4 source windows: just below, exactly at, and above 50%.
    for count in (7, 8, 9):
        image, _ = fixture(tmp_path, height=4, width=4, key=f"nodata{count}")
        image.reshape(8, -1)[:, :count] = 0
        write_raster(tmp_path / "images" / f"nodata{count}.tif", image)
    output = chip_dataset(plan(tmp_path, replace(RECIPE, chip_size=4, stride=4)))
    records = rows(output)
    assert [row["disposition"] for row in records] == [
        "retained",
        "retained",
        "omitted_nodata",
    ]
    assert [int(row["nodata_pixels"]) for row in records] == [7, 8, 9]
    assert [int(row["background_pixels"]) for row in records] == [9, 8, 7]
    assert all(int(row["kelp_pixels"]) == 0 for row in records)
    assert records[-1]["payload"] == ""
    assert len(list((output / "chips").rglob("*.npz"))) == 2
    for row in records[:2]:
        chip = load_chip(output / row["payload"], NAMES, chip_size=4)
        assert int((chip["label"] == -100).sum()) == int(row["nodata_pixels"])
    summary = json.loads((output / "summary.json").read_text())
    assert (
        summary["candidate_windows"] == 3
        and summary["retained"] == 2
        and summary["omitted_nodata"] == 1
    )


def test_current_labels_map_explicitly_with_source_nodata_and_valid_ignore(tmp_path):
    image, _ = fixture(tmp_path, height=2, width=5)
    image[:, 1, 0] = 0
    # A single zero channel is still valid imagery.
    image[0, 1, 1] = 0
    write_raster(tmp_path / "images/scene.tif", image)
    stored = np.array([[[0, 1, 2, 3, 4], [0, 0, 0, 3, 1]]], dtype=np.uint8)
    write_raster(tmp_path / "labels/scene.tif", stored, nodata=0)
    output = chip_dataset(plan(tmp_path))
    record = rows(output)[0]
    chip = load_chip(output / record["payload"], NAMES)
    np.testing.assert_array_equal(
        chip["label"][:2, :5], [[0, 1, 0, -100, 0], [-100, 0, 0, -100, 1]]
    )
    assert chip["image"].dtype == np.uint16 and chip["label"].dtype == np.int8
    assert (
        int(record["nodata_pixels"]) == 1 and int(record["valid_ignored_pixels"]) == 2
    )
    assert (
        sum(
            int(record[key])
            for key in ("background_pixels", "kelp_pixels", "ignored_pixels")
        )
        == 10
    )
    with rasterio.open(tmp_path / "labels/scene.tif") as source:
        np.testing.assert_array_equal(source.read(), stored)


def test_image_only_keeps_unknown_scientific_identity_and_no_target(tmp_path):
    fixture(tmp_path, labels=False)
    output = chip_dataset(plan(tmp_path, labels=False))
    record = rows(output)[0]
    assert record["kelp_pixels"] == record["ignored_pixels"] == ""
    chip = load_chip(output / record["payload"], NAMES)
    assert chip["label"] is None and chip["true_height"] == 3
    source = json.loads((output / "sources.json").read_text())[0]
    assert source["region"] is None and source["acquisition_date"] is None


@pytest.mark.parametrize(
    "kind", ["missing", "extra", "duplicate", "conflict", "crop_exceeds_source"]
)
def test_identity_csv_joins_exactly_and_preserves_one_original_identity(tmp_path, kind):
    fixture(tmp_path, key="a")
    fixture(tmp_path, key="b")
    records = [
        {
            "source_key": key,
            "source_id": "shared",
            "original_tiff": "shared.tif",
            "region": "bc",
        }
        for key in ("a", "b")
    ]
    if kind == "missing":
        records.pop()
    elif kind == "extra":
        records.append({"source_key": "c"})
    elif kind == "duplicate":
        records.append(records[0].copy())
    elif kind == "conflict":
        records[1]["region"] = "ca"
    else:
        records[0].update(row_offset=1, original_height=3)
    metadata = metadata_csv(tmp_path / "identity.csv", records)
    with pytest.raises(PreparationError):
        plan(tmp_path, metadata=metadata)
    assert not (tmp_path / "result").exists()


@pytest.mark.parametrize("kind", ["consistent", "affine", "crs"])
def test_crops_of_one_original_share_the_offset_adjusted_grid(tmp_path, kind):
    fixture(tmp_path, key="a")
    image, target = fixture(tmp_path, key="b")
    shifted = GRID * rasterio.Affine.translation(2, 1)
    if kind == "affine":
        shifted *= rasterio.Affine.translation(1, 0)
    write_raster(tmp_path / "images/b.tif", image, transform=shifted)
    write_raster(tmp_path / "labels/b.tif", target, transform=shifted)
    if kind == "crs":
        for role in ("images", "labels"):
            with rasterio.open(tmp_path / role / "b.tif", "r+") as source:
                source.crs = "EPSG:32611"
    records = [
        {
            "source_key": key,
            "source_id": "shared-original",
            "original_tiff": "shared.tif",
            "row_offset": row,
            "col_offset": col,
            "original_height": 20,
            "original_width": 20,
        }
        for key, row, col in (("a", 0, 0), ("b", 1, 2))
    ]
    metadata = metadata_csv(tmp_path / "identity.csv", records)
    if kind == "consistent":
        proposed = plan(tmp_path, metadata=metadata)
        assert len(proposed.sources) == 2
        assert proposed.sources[1]["transform"] == list(shifted)[:6]
        assert proposed.sources[1]["row_offset"] == 1
        assert proposed.sources[1]["col_offset"] == 2
    else:
        with pytest.raises(PreparationError):
            plan(tmp_path, metadata=metadata)
        assert not (tmp_path / "result").exists()


@pytest.mark.parametrize(
    "kind", ["grid", "missing_label", "duplicate_stem", "band_evidence"]
)
def test_invalid_source_scope_fails_before_output(tmp_path, kind):
    _, target = fixture(tmp_path)
    if kind == "grid":
        write_raster(
            tmp_path / "labels/scene.tif", target, transform=from_origin(101, 200, 3, 3)
        )
    elif kind == "missing_label":
        (tmp_path / "labels/scene.tif").unlink()
    elif kind == "duplicate_stem":
        (tmp_path / "images/scene.tiff").write_bytes(
            (tmp_path / "images/scene.tif").read_bytes()
        )
    else:
        with rasterio.open(tmp_path / "images/scene.tif", "r+") as source:
            source.set_band_description(1, "red")
    with pytest.raises(PreparationError):
        plan(tmp_path)
    assert not (tmp_path / "result").exists()


def test_cli_header_only_dry_run_reads_no_pixels_and_writes_nothing(
    tmp_path, monkeypatch
):
    fixture(tmp_path)
    recipe = recipe_file(tmp_path / "recipe.toml")
    before = sorted(tmp_path.rglob("*"))
    original_open = rasterio.open

    class HeadersOnly:
        def __init__(self, *args, **kwargs):
            self.source = original_open(*args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.source.close()

        def __getattr__(self, name):
            return getattr(self.source, name)

        def read(self, *args, **kwargs):
            raise AssertionError("Dry run read pixels")

    monkeypatch.setattr(rasterio, "open", HeadersOnly)
    result = CliRunner().invoke(
        app,
        [
            "chip",
            "--images",
            str(tmp_path / "images"),
            "--labels",
            str(tmp_path / "labels"),
            "--output",
            str(tmp_path / "result"),
            "--recipe",
            str(recipe),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "headers only" in result.stdout and "candidate windows: 1" in result.stdout
    assert sorted(tmp_path.rglob("*")) == before


@pytest.mark.parametrize(
    "old,new",
    [
        ("chip_size = 512", "chip_size = true"),
        ("stride = 256", "stride = 513"),
        ("max_nodata_pct = 50", "max_nodata_pct = nan"),
        pytest.param(
            "max_nodata_pct = 50",
            f"max_nodata_pct = {10**500}",
            id="integer-cutoff-overflow",
        ),
        ("schema_version = 1", "schema_version = 1\nmisspelled = 42"),
        ("3 = -100", "3 = 500"),
    ],
)
def test_bad_recipe_fails_with_an_actionable_error(tmp_path, old, new):
    recipe = recipe_file(tmp_path / "bad.toml", **{old: new})
    with pytest.raises(PreparationError, match="chip recipe"):
        load_chip_recipe(recipe)


def test_failed_write_leaves_incomplete_output_and_refuses_reuse(tmp_path, monkeypatch):
    fixture(tmp_path)
    proposed = plan(tmp_path)

    def fail(*args, **kwargs):
        raise OSError("fixture disk write failure")

    monkeypatch.setattr(np, "savez_compressed", fail)
    with pytest.raises(PreparationError, match="fresh output"):
        chip_dataset(proposed)
    assert not proposed.output.exists()
    assert (tmp_path / ".result.incomplete").is_dir()
    assert not (tmp_path / ".result.incomplete/summary.json").exists()
    with pytest.raises(PreparationError, match="exists"):
        chip_dataset(proposed)
    with pytest.raises(PreparationError, match="exists"):
        plan(tmp_path)


def test_completed_output_is_never_overwritten(tmp_path):
    fixture(tmp_path)
    proposed = plan(tmp_path)
    chip_dataset(proposed)
    before = (proposed.output / "windows.csv").read_bytes()
    with pytest.raises(PreparationError, match="exists"):
        chip_dataset(proposed)
    with pytest.raises(PreparationError, match="exists"):
        plan(tmp_path)
    assert (proposed.output / "windows.csv").read_bytes() == before


def test_corrupt_tiff_cli_has_a_useful_error(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "images/broken.tif").write_bytes(b"not a TIFF")
    recipe = recipe_file(tmp_path / "recipe.toml")
    result = CliRunner().invoke(
        app,
        [
            "chip",
            "--images",
            str(tmp_path / "images"),
            "--output",
            str(tmp_path / "result"),
            "--recipe",
            str(recipe),
        ],
    )
    assert result.exit_code == 1
    assert "Error:" in result.stderr and "broken.tif" in result.stderr
    assert "Traceback" not in result.output
    assert not (tmp_path / "result").exists()
