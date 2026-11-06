"""Label inventories preserve original-pixel coverage and explicit denominators."""

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio import Affine

from kelpseg.reporting.shore_inventory import shore_inventory
from kelpseg.reporting.shore_inventory_counts import (
    band_counts,
    cumulative_counts,
    inventory_footprints,
    pool_inventory,
)
from kelpseg.reporting.shore_inventory_inputs import (
    ShoreInventorySettings,
    load_settings,
    read_label_canvas,
)


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_tiff(path: Path, array: np.ndarray, transform: Affine) -> None:
    if array.ndim == 2:
        array = array[None]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=array.shape[1],
        width=array.shape[2],
        count=array.shape[0],
        dtype=array.dtype,
        crs="EPSG:32610",
        transform=transform,
    ) as ds:
        ds.write(array)


def test_band_counts_and_cumulative_keep_land_unknown_and_ignore() -> None:
    labels = np.array([[1, 1, 0, 1, 1, -100]], dtype=np.int8)
    land = np.array([[1, 0, 0, 0, 255, 0]], dtype=np.uint8)
    distance = np.array([[0, 0, 30, 60, np.nan, 20]], dtype=np.float32)
    rows = band_counts(
        labels, np.ones_like(labels, dtype=bool), land, distance, (0, 30, 60, 500), 9
    )
    assert sum(row["labeled_pixels"] for row in rows) == 5
    assert sum(row["kelp_pixels"] for row in rows) == 4
    assert {row["band"]: row["kelp_pixels"] for row in rows} == {
        "land": 1,
        "0-30": 1,
        "30-60": 0,
        "60-500": 1,
        "500+": 0,
        "unknown": 1,
    }
    cumulative = cumulative_counts(
        labels, np.ones_like(labels, dtype=bool), land, distance, (30, 60, 500), 9
    )
    near = next(row for row in cumulative if row["cutoff_m"] == 60)
    assert near["kelp_pixels"] == 1 and near["all_kelp_pixels"] == 4
    assert near["kelp_area_m2"] == 9
    near120 = next(row for row in cumulative if row["cutoff_m"] == 120)
    assert near120["kelp_pixels"] == 2
    distance[0, 3] = 120
    boundary = cumulative_counts(
        labels, np.ones_like(labels, dtype=bool), land, distance, (30, 60, 500), 9
    )
    assert next(row for row in boundary if row["cutoff_m"] == 120)["kelp_pixels"] == 1


def test_window_unions_deduplicate_overlap_and_training_exclusion() -> None:
    canvas = {
        "labels": np.zeros((3, 4), dtype=np.int8),
        "footprint": np.ones((3, 4), dtype=bool),
        "source": {"split": "train", "row_offset": 10, "col_offset": 20},
    }
    windows = [
        dict(
            split="train",
            original_row=10,
            original_col=20,
            height=2,
            width=3,
            kelp_pixels=1,
        ),
        dict(
            split="train",
            original_row=11,
            original_col=21,
            height=2,
            width=3,
            kelp_pixels=0,
        ),
        dict(
            split="unused",
            original_row=10,
            original_col=20,
            height=3,
            width=4,
            kelp_pixels=0,
        ),
    ]
    masks = inventory_footprints(canvas, windows, True)
    assert masks["full_source"].sum() == 12
    assert masks["selected_chips"].sum() == 10
    assert masks["training_eligible"].sum() == 6
    assert inventory_footprints(canvas, windows, False)["training_eligible"].sum() == 10


def inventory_fixture(tmp_path: Path) -> ShoreInventorySettings:
    image_root, label_root, shoreline, chip_root = (
        tmp_path / name for name in ("images", "labels", "shore", "chips")
    )
    for directory in (image_root, label_root, shoreline, chip_root):
        directory.mkdir()
    sources, chips, assignments, windows, labels = [], [], [], [], []
    transform = Affine(3, 0, 100, 0, -3, 200)
    for key, split, date in (("a", "train", "2020-01-01"), ("b", "val", "2020-02-01")):
        image = np.ones((8, 3, 4), dtype=np.uint16)
        target = np.zeros((3, 4), dtype=np.uint8)
        target[0, :2] = 1
        target[2, 3] = 3
        write_tiff(image_root / f"{key}.tif", image, transform)
        write_tiff(label_root / f"{key}.tif", target, transform)
        write_tiff(
            shoreline / f"{key}_land.tif", np.zeros((3, 4), dtype=np.uint8), transform
        )
        write_tiff(
            shoreline / f"{key}_distance.tif",
            np.tile(np.array([0, 30, 60, 500], dtype=np.float32), (3, 1)),
            transform,
        )
        identity = dict(
            dataset_id="dataset",
            release_id="v1",
            acquisition_date=date,
            row_offset=0,
            col_offset=0,
        )
        sources.append(
            dict(
                source_key=key,
                image=f"{key}.tif",
                band_names="blue;green;red;nir",
                original_source_id=key,
                region_id="001",
                height=3,
                width=4,
                land_mask=f"{key}_land.tif",
                distance=f"{key}_distance.tif",
                cap_m=500,
                **identity,
            )
        )
        chips.append(
            dict(
                source_key=key,
                source_id=key,
                original_tiff=f"{key}.tif",
                region="001",
                height=3,
                width=4,
                **identity,
            )
        )
        assignments.append(
            dict(
                dataset_id="dataset",
                release_id="v1",
                source_id=key,
                region="001",
                acquisition_date=date,
                satellite_id="abcd",
                experiment="baseline",
                variant="augmented",
                split=split,
                reason="fixture",
            )
        )
        windows.append(
            dict(
                source_key=key,
                row=0,
                col=0,
                original_row=0,
                original_col=0,
                height=2,
                width=3,
                kelp_pixels=2,
                disposition="retained",
                payload=f"{key}.npz",
            )
        )
        labels.append(dict(source_key=key, label=f"{key}.tif"))
    write_csv(shoreline / "sources.csv", sources)
    (chip_root / "sources.json").write_text(json.dumps(chips))
    write_csv(chip_root / "windows.csv", windows)
    write_csv(tmp_path / "assignments.csv", assignments)
    write_csv(tmp_path / "labels.csv", labels)
    return ShoreInventorySettings(
        shoreline=shoreline,
        image_root=image_root,
        labels=tmp_path / "labels.csv",
        label_root=label_root,
        chip_root=chip_root,
        assignments=tmp_path / "assignments.csv",
        output=tmp_path / "out",
    )


def test_label_only_inventory_runs_without_predictions_or_chip_payloads(
    tmp_path: Path,
) -> None:
    settings = inventory_fixture(tmp_path)
    result = shore_inventory(settings)
    assert result.is_file()
    assert "&lt;120 m" in result.read_text()
    assert (
        json.loads((settings.output / "summary.json").read_text())["nearshore_cutoff_m"]
        == 120
    )
    rows = list(csv.DictReader((settings.output / "split_bands.csv").open()))
    full = [
        row for row in rows if row["scope"] == "full_source" and row["split"] == "train"
    ]
    assert sum(int(row["labeled_pixels"]) for row in full) == 11
    assert sum(int(row["kelp_pixels"]) for row in full) == 2
    assert not any(
        row["scope"] == "training_eligible" and row["split"] != "train" for row in rows
    )
    near = [
        row
        for row in csv.DictReader((settings.output / "cumulative_splits.csv").open())
        if row["scope"] == "full_source" and float(row["cutoff_m"]) == 60
    ]
    assert all(float(row["kelp_fraction"]) == 1 for row in near)
    with (settings.output / "region_bands.csv").open() as stream:
        absent = [row for row in csv.DictReader(stream) if row["split"] == "test"]
    assert absent and all(
        row["kelp_fraction"] == "" and int(row["sources"]) == 0 for row in absent
    )
    with pytest.raises(ValueError, match="already exists"):
        shore_inventory(settings)


def test_pooling_counts_sources_dates_and_undefined_fractions() -> None:
    common = dict(
        scope="full_source",
        band="land",
        split="train",
        dataset_id="d",
        release_id="v",
        labeled_pixels=0,
        kelp_pixels=0,
        labeled_area_m2=0,
        kelp_area_m2=0,
        all_labeled_pixels=0,
        all_kelp_pixels=0,
        all_kelp_area_m2=0,
    )
    rows = [
        dict(common, source_id="a", acquisition_date="2020-01-01"),
        dict(common, source_id="b", acquisition_date="2020-01-01"),
    ]
    result = pool_inventory(rows, ("split", "scope", "band"))[0]
    assert result["kelp_fraction"] is None and result["kelp_prevalence"] is None
    assert result["sources"] == result["dates"] == 0


def test_original_crop_overlap_counts_once_and_rejects_conflicting_labels(
    tmp_path: Path,
) -> None:
    settings = inventory_fixture(tmp_path)
    rows = list(csv.DictReader((settings.shoreline / "sources.csv").open()))
    first = dict(
        rows[0],
        image=str(settings.image_root / "a.tif"),
        label=str(settings.label_root / "a.tif"),
        split="train",
    )
    duplicate = dict(first, source_key="second_crop")
    canvas = read_label_canvas([first, duplicate], settings.label_mapping)
    assert canvas["footprint"].sum() == 12
    assert (canvas["labels"] == 1).sum() == 2
    other = settings.label_root / "different.tif"
    write_tiff(other, np.ones((3, 4), dtype=np.uint8), Affine(3, 0, 100, 0, -3, 200))
    with pytest.raises(ValueError, match="Conflicting valid labels"):
        read_label_canvas(
            [first, dict(duplicate, label=str(other))], settings.label_mapping
        )


def test_missing_label_identity_is_actionable(tmp_path: Path) -> None:
    settings = inventory_fixture(tmp_path)
    settings.labels.write_text("source_key,label\na,a.tif\n")
    with pytest.raises(ValueError, match="exactly match"):
        shore_inventory(settings)


def test_unknown_settings_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("mystery = 4\n")
    with pytest.raises(ValueError, match="Unknown shore-inventory"):
        load_settings(path)


def test_duplicate_assignments_fail_before_writing_output(tmp_path: Path) -> None:
    settings = inventory_fixture(tmp_path)
    with settings.assignments.open() as stream:
        assignments = list(csv.DictReader(stream))
    write_csv(settings.assignments, [*assignments, assignments[0]])
    with pytest.raises(ValueError, match="Duplicate source assignment"):
        shore_inventory(settings)
    assert not settings.output.exists()


def test_label_grid_mismatch_fails_without_resampling(tmp_path: Path) -> None:
    settings = inventory_fixture(tmp_path)
    path = settings.label_root / "a.tif"
    write_tiff(path, np.ones((3, 4), dtype=np.uint8), Affine(3, 0, 101, 0, -3, 200))
    with pytest.raises(ValueError, match="exactly match the image grid"):
        shore_inventory(settings)


def test_pooled_fraction_uses_counts_not_mean_source_fractions() -> None:
    common = dict(
        scope="full_source",
        band="0-30",
        split="train",
        dataset_id="d",
        release_id="v",
        acquisition_date="2020-01-01",
    )
    rows = [
        dict(
            common,
            source_id="a",
            labeled_pixels=2,
            kelp_pixels=1,
            labeled_area_m2=18,
            kelp_area_m2=9,
            all_labeled_pixels=2,
            all_kelp_pixels=1,
            all_kelp_area_m2=9,
        ),
        dict(
            common,
            source_id="b",
            labeled_pixels=10,
            kelp_pixels=1,
            labeled_area_m2=90,
            kelp_area_m2=9,
            all_labeled_pixels=20,
            all_kelp_pixels=9,
            all_kelp_area_m2=81,
        ),
    ]
    result = pool_inventory(rows, ("split", "scope", "band"))[0]
    assert result["kelp_fraction"] == pytest.approx(2 / 10)
    assert result["kelp_prevalence"] == pytest.approx(2 / 12)
    assert result["sources"] == result["kelp_sources"] == 2
    assert result["dates"] == 1


def test_recipe_distance_edges_requires_array(tmp_path):
    paths = (
        "shoreline",
        "image_root",
        "labels",
        "label_root",
        "chip_root",
        "assignments",
        "output",
    )
    recipe = tmp_path / "inventory.toml"
    recipe.write_text(
        "\n".join(f'{name} = "example"' for name in paths) + "\ndistance_edges = 60\n"
    )
    with pytest.raises(ValueError, match="distance_edges must be an array"):
        load_settings(recipe)
