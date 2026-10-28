"""Scientific channel, nodata, and true-size padding behavior."""

from pathlib import Path

import numpy as np
import pytest

from kelpseg.bands import resolve_band_indices, select_bands
from kelpseg.chips import load_chip

NAMES = (
    "coastal_blue",
    "blue",
    "green_i",
    "green",
    "yellow",
    "red",
    "rededge",
    "nir",
)


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("all", list(range(1, 9))),
        ("rgbnir", [6, 4, 2, 8]),
        ("rgb", [6, 4, 2]),
        ([8, 1], [8, 1]),
        (["nir", "coastal_blue"], [8, 1]),
    ],
)
def test_ordered_band_selection(selection, expected):
    image = np.broadcast_to(np.arange(1, 9, dtype=np.uint16), (2, 3, 8)).copy()
    actual = select_bands(image, NAMES, selection)
    np.testing.assert_array_equal(actual[0, 0], expected)
    assert actual.dtype == np.uint16
    assert resolve_band_indices(NAMES, selection) == tuple(i - 1 for i in expected)


@pytest.mark.parametrize(
    "selection", [[], [0], [9], [True], ["missing"], ["red", 6], "RGB"]
)
def test_invalid_band_selection(selection):
    with pytest.raises(ValueError):
        resolve_band_indices(NAMES, selection)


@pytest.mark.parametrize("names", [(), ("red", "red"), ("red", ""), "rgb"])
def test_invalid_source_names(names):
    with pytest.raises(ValueError, match="source_band_names"):
        resolve_band_indices(names)


def test_band_count_and_native_four_band_selection():
    names = ("blue", "green", "red", "nir")
    assert resolve_band_indices(names, "rgbnir") == (2, 1, 0, 3)
    with pytest.raises(ValueError, match="one channel"):
        select_bands(np.ones((2, 3, 8), dtype=np.uint16), names)


@pytest.mark.parametrize("selection", ["all", "rgbnir", "rgb"])
def test_partial_edge_padding_round_trip_and_native_nodata(tmp_path, selection):
    image = np.broadcast_to(np.arange(1, 9, dtype=np.uint16), (257, 256, 8)).copy()
    image[0, 0] = 0
    # Selected RGB bands are zero, but other native bands prove valid imagery.
    image[0, 1, (5, 3, 1, 7)] = 0
    label = np.zeros(image.shape[:2], dtype=np.int8)
    label[0, 0] = -100
    label[1, 1] = 1
    label[1, 2] = -100
    path = tmp_path / "partial.npz"
    np.savez_compressed(path, image=image, label=label)

    loaded = load_chip(path, NAMES, selection)
    height, width = loaded["true_height"], loaded["true_width"]
    assert (height, width) == (257, 256)
    assert loaded["padding"] == (0, 255, 0, 256)
    assert loaded["image"].shape == (512, 512, len(loaded["band_names"]))
    assert loaded["image"].dtype == np.uint16
    assert loaded["label"].dtype == np.int8
    np.testing.assert_array_equal(
        loaded["image"][:height, :width], select_bands(image, NAMES, selection)
    )
    np.testing.assert_array_equal(loaded["label"][:height, :width], label)
    assert np.all(loaded["image"][height:] == 0)
    assert np.all(loaded["image"][:, width:] == 0)
    assert np.all(loaded["label"][height:] == -100)
    assert np.all(loaded["label"][:, width:] == -100)
    assert loaded["nodata_mask"].sum() == 1
    assert loaded["nodata_mask"][0, 0]
    assert not loaded["nodata_mask"][0, 1]

    # Restore the true crop at its source offset with no padding contribution.
    source = np.zeros((800, 800, loaded["image"].shape[-1]), dtype=np.uint16)
    source[256 : 256 + height, 256 : 256 + width] = loaded["image"][:height, :width]
    np.testing.assert_array_equal(
        source[256 : 256 + height, 256 : 256 + width],
        select_bands(image, NAMES, selection),
    )


def test_image_only_geometry_and_full_size(tmp_path):
    path = tmp_path / "image-only.npz"
    image = np.ones((2, 2, 3), dtype=np.uint16)
    np.savez_compressed(path, image=image)
    loaded = load_chip(path, ("red", "green", "blue"), chip_size=2)
    assert loaded["label"] is None
    assert loaded["padding"] == (0, 0, 0, 0)
    np.testing.assert_array_equal(loaded["image"], image)


@pytest.mark.parametrize(
    ("arrays", "message"),
    [
        ({"image": np.zeros((2, 2, 8), dtype=np.float32)}, "HWC uint16"),
        ({"image": np.zeros((2, 2, 4), dtype=np.uint16)}, "channels disagree"),
        ({"image": np.zeros((0, 2, 8), dtype=np.uint16)}, "dimensions"),
        ({"image": np.zeros((513, 2, 8), dtype=np.uint16)}, "dimensions"),
        (
            {
                "image": np.ones((2, 2, 8), dtype=np.uint16),
                "label": np.zeros((1, 2), dtype=np.int8),
            },
            "label must be HW int8",
        ),
    ],
)
def test_invalid_chip_arrays(tmp_path: Path, arrays, message):
    path = tmp_path / "invalid.npz"
    np.savez_compressed(path, **arrays)
    with pytest.raises(ValueError, match=message):
        load_chip(path, NAMES)


@pytest.mark.parametrize("chip_size", [True, 0, 1.5])
def test_invalid_padding_size(tmp_path, chip_size):
    with pytest.raises(ValueError, match="positive integer"):
        load_chip(tmp_path / "unused.npz", NAMES, chip_size=chip_size)
