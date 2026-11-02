"""Native-pixel exports and offline viewer records match the scientific display."""

import json
import re

import albumentations as A
import numpy as np
import pytest
from matplotlib import image as mpl_image

from kelpseg.augmentation_display import write_display_views, write_viewer
from kelpseg.augmentation_panels import display_limits, label_overlay, spectral_view
from kelpseg.augmentations import apply_augmentation
from kelpseg.preprocessing import BAND_NAMES, CLIP_VALUE, MEAN, STD, cap_raw, normalize


@pytest.fixture
def display_sample(tmp_path):
    image = np.arange(4 * 5 * 8, dtype=np.uint16).reshape(4, 5, 8) + 100
    image[0, 0] = 0
    valid = np.any(image != 0, axis=-1)
    label = np.zeros((4, 5), dtype=np.int8)
    label[1, 2] = 1
    label[0, 0] = -100
    sample = dict(
        image=image,
        label=label,
        valid=valid,
        band_names=BAND_NAMES,
        preview_name="training_01",
    )
    limits = np.array([[0] * 8, [1000] * 8], dtype=float)
    folder = tmp_path / "training_01/views"
    folder.mkdir(parents=True)
    return tmp_path, folder, sample, limits


def _state(sample, transform, *, identity=False, fixed=None):
    image, label, valid, parameters = apply_augmentation(
        transform,
        sample["image"],
        sample["label"],
        sample["valid"],
        seed=33,
        fixed_parameters=fixed,
    )
    return dict(
        parameters=parameters,
        display=cap_raw(image, valid),
        valid=valid,
        label=label,
        is_identity=identity,
    )


def _pixels(root, relative):
    # Matplotlib's PNG reader returns RGBA in 0..1; compare stored RGB bytes.
    return np.round(mpl_image.imread(root / relative)[:, :, :3] * 255).astype(np.uint8)


def test_display_ceiling_2000_does_not_change_model_cap_5000():
    limits = display_limits([dict(band_names=BAND_NAMES)])
    np.testing.assert_array_equal(limits, [[0] * 8, [2000] * 8])
    raw = np.array([[[1800, 2200, 4500, 5500, -25, 2200, 4500, 5500]]], dtype=float)
    valid = np.ones((1, 1), dtype=bool)
    capped = cap_raw(raw, valid)
    assert CLIP_VALUE == 5000
    np.testing.assert_array_equal(
        capped, [[[1800, 2200, 4500, 5000, -25, 2200, 4500, 5000]]]
    )
    expected = (capped - np.asarray(MEAN)) / np.asarray(STD)
    np.testing.assert_allclose(normalize(raw, BAND_NAMES, valid), expected, rtol=1e-7)
    # RGB values above the visual ceiling saturate, while the model retains
    # their distinct values up to its separately approved cap.
    np.testing.assert_array_equal(
        spectral_view(capped, BAND_NAMES, ("red", "green", "blue"), limits, valid),
        np.ones((1, 1, 3)),
    )


def test_native_exports_use_frozen_stretch_and_identity_reuses_original(display_sample):
    root, folder, sample, limits = display_sample
    valid = sample["valid"]
    states = [
        _state(sample, A.NoOp(p=1), identity=True),
        _state(
            sample,
            A.RandomBrightnessContrast(
                brightness_limit=(0, 0), contrast_limit=(0, 0), p=1
            ),
            identity=True,
        ),
        _state(
            sample,
            A.RandomBrightnessContrast(
                brightness_limit=(0.0025, 0.0025), contrast_limit=(0, 0), p=1
            ),
        ),
    ]
    assets = write_display_views(folder, sample, "brightness", states, limits, {})
    assert assets[0] == assets[1]
    assert len(list(folder.glob("*.png"))) == 8
    for index in (0, 2):
        rgb = spectral_view(
            states[index]["display"],
            BAND_NAMES,
            ("red", "green", "blue"),
            limits,
            valid,
        )
        false = spectral_view(
            states[index]["display"], BAND_NAMES, ("nir", "red", "green"), limits, valid
        )
        overlay = label_overlay(rgb, sample["label"], valid)
        for view, expected in (
            ("rgb", rgb),
            ("false_color", false),
            ("labels", overlay),
            ("false_color_labels", label_overlay(false, sample["label"], valid)),
        ):
            pixels = _pixels(root, assets[index][view])
            assert pixels.shape == (4, 5, 3)
            np.testing.assert_array_equal(
                pixels, np.round(expected * 255).astype(np.uint8)
            )


@pytest.mark.parametrize("band", ["red", "nir"])
def test_single_band_dropout_keeps_unaffected_views_and_shows_affected_band(
    display_sample, band
):
    root, folder, sample, limits = display_sample
    states = [
        _state(sample, A.NoOp(p=1), identity=True),
        _state(sample, A.NoOp(p=1), identity=True),
        _state(
            sample,
            A.ChannelDropout(channel_drop_range=(1, 1), fill=0, p=1),
            fixed={"channels_to_drop": [BAND_NAMES.index(band)]},
        ),
    ]
    assets = write_display_views(
        folder, sample, f"band_dropout_{band}", states, limits, {}
    )
    assert assets[0] == assets[1]
    assert states[-1]["parameters"]["class"] == "ChannelDropout"
    assert states[-1]["parameters"]["fixed_parameters"] == {
        "channels_to_drop": [BAND_NAMES.index(band)]
    }
    if band == "nir":
        assert assets[-1]["rgb"] == assets[0]["rgb"]
        assert assets[-1]["labels"] == assets[0]["labels"]
    else:
        assert not np.array_equal(
            _pixels(root, assets[-1]["rgb"]), _pixels(root, assets[0]["rgb"])
        )
    zero = _pixels(root, assets[2]["affected_band"])
    assert not zero.any()
    assert _pixels(root, assets[0]["affected_band"]).any()
    assert not np.array_equal(
        _pixels(root, assets[0]["false_color"]), _pixels(root, assets[2]["false_color"])
    )


def test_viewer_embeds_escaped_json_without_remote_dependencies(tmp_path):
    source = '</script><img src="bad" onerror="alert(1)">'
    records = [
        dict(preview_name="training_01", window=dict(source_key=source), families=[])
    ]
    write_viewer(tmp_path, {"scope": "train only"}, records)
    document = (tmp_path / "index.html").read_text()
    embedded = re.search(
        r'<script type="application/json" id="gallery-data">(.*?)</script>',
        document,
        re.DOTALL,
    )
    assert embedded is not None
    data = json.loads(embedded.group(1))
    assert data["scope"] == "train only"
    assert data["samples"][0]["window"]["source_key"] == source
    assert "<" not in embedded.group(1)
    assert source not in document
    assert "__GALLERY_DATA__" not in document
    assert not re.search(r"<script[^>]+src=|fetch\s*\(|https?://", document)
