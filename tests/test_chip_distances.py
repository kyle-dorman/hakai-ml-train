"""Derived chip publication on a cropped, partial-edge source grid."""

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from kelpseg.chips import load_chip
from kelpseg.prepare.chip_distances import prepare_chip_distances
from kelpseg.preprocessing import BAND_NAMES
from kelpseg.training.data import ChipDataset
from kelpseg.training.run import collate_chips


def test_derive_and_load_aligned_partial_chip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Check offsets, unknown/land/nodata separation, unchanged arrays and NPZ-only loading."""
    canonical, shore, output = (
        tmp_path / name for name in ("canonical", "shore", "derived")
    )
    (canonical / "chips").mkdir(parents=True)
    shore.mkdir()
    transform = from_origin(600_000, 3_000_000, 3, 3)
    source = dict(
        source_key="crop",
        source_id="full",
        dataset_id="test",
        release_id="v1",
        region="008",
        acquisition_date="2021-01-01",
        row_offset=7,
        col_offset=11,
        width=5,
        height=4,
        crs="EPSG:32610",
        transform=list(transform)[:6],
    )
    grid = dict(
        source,
        original_source_id="full",
        region_id="008",
        transform=json.dumps(source["transform"]),
        cap_m=750,
        land_mask="land.tif",
        distance="distance.tif",
    )
    distance = np.arange(20, dtype=np.float32).reshape(4, 5) + 0.25
    distance[2, 2:5] = [-9999, -9999, 750]
    land = np.zeros((4, 5), dtype=np.uint8)
    land[2, 2:4] = [1, 255]
    for filename, array, nodata in (
        ("distance.tif", distance, -9999),
        ("land.tif", land, 255),
    ):
        with rasterio.open(
            shore / filename,
            "w",
            driver="GTiff",
            width=5,
            height=4,
            count=1,
            crs=source["crs"],
            transform=transform,
            dtype=array.dtype,
            nodata=nodata,
        ) as dataset:
            dataset.write(array, 1)
    row = dict(
        source_key="crop",
        row=2,
        col=2,
        height=2,
        width=3,
        original_row=9,
        original_col=13,
        disposition="retained",
        payload="chips/crop.npz",
    )
    for filename, values in (
        ("sources.json", [source]),
        ("recipe.json", {}),
        ("summary.json", {}),
    ):
        (canonical / filename).write_text(json.dumps(values))
    for path, record in (
        (shore / "sources.csv", grid),
        (canonical / "windows.csv", row),
    ):
        with path.open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(record))
            writer.writeheader()
            writer.writerow(record)
    image = np.full((2, 3, 8), 1000, dtype=np.uint16)
    image[1, 0] = 0
    label = np.array([[1, 1, 0], [-100, 1, 0]], dtype=np.int8)
    np.savez_compressed(canonical / row["payload"], image=image, label=label)
    canonical_bytes = (canonical / row["payload"]).read_bytes()

    assert prepare_chip_distances(canonical, shore, output) == output
    for filename in ("recipe.json", "sources.json", "windows.csv"):
        assert (canonical / filename).read_bytes() == (output / filename).read_bytes()
    assert (canonical / row["payload"]).read_bytes() == canonical_bytes
    assert (
        json.loads((output / "summary.json").read_text())[
            "unknown_distance_positive_window_pixels"
        ]
        == 1
    )
    with np.load(output / row["payload"]) as arrays:
        np.testing.assert_array_equal(arrays["image"], image)
        np.testing.assert_array_equal(arrays["label"], label)
        np.testing.assert_array_equal(arrays["land"], land[2:, 2:])
        np.testing.assert_array_equal(
            arrays["distance_m"], [[np.nan, np.nan, 500], [17.25, 18.25, 19.25]]
        )
    with pytest.raises(ValueError, match="fresh output"):
        prepare_chip_distances(canonical, shore, output)

    # A grid with the right shape and wrong affine must fail before publication.
    with rasterio.open(shore / "land.tif", "r+") as dataset:
        dataset.transform = transform * rasterio.Affine.translation(1, 0)
    with pytest.raises(ValueError, match="does not match the chip source grid"):
        prepare_chip_distances(canonical, shore, tmp_path / "misaligned")
    assert not (tmp_path / "misaligned").exists()

    def forbidden(*args, **kwargs) -> None:
        raise AssertionError("Training must load distance from the chip payload.")

    monkeypatch.setattr(rasterio, "open", forbidden)
    dataset = ChipDataset(
        [dict(row, split="train", payload=output / row["payload"])],
        BAND_NAMES,
        chip_size=4,
        include_distance=True,
    )
    batch = collate_chips([dataset[0]])
    np.testing.assert_array_equal(
        batch["effective_distance_m"][0],
        [[0, -100, 500, -100], [-100, 18.25, 19.25, -100], [-100] * 4, [-100] * 4],
    )
    with pytest.raises(ValueError, match="prepare-chip-distances"):
        load_chip(canonical / row["payload"], BAND_NAMES, include_distance=True)
