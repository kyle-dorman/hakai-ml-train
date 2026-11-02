"""Parity with actual Albumentations classes and scientific mask/scale checks."""

import json

import albumentations as A
import numpy as np
import pytest

from kelpseg.augmentations import NATIVE_SCALE, apply_augmentation
from kelpseg.preprocessing import cap_raw


@pytest.fixture
def sample():
    image = np.arange(9 * 9 * 8, dtype=np.uint16).reshape(9, 9, 8)
    valid = np.ones((9, 9), dtype=bool)
    valid[0] = False
    valid[:, -1] = False
    image[~valid] = 0
    label = np.zeros((9, 9), dtype=np.int8)
    label[~valid] = -100
    label[2:5, 3:6] = 1
    return image, label, valid


@pytest.mark.parametrize("channels", [8, 4, 3])
@pytest.mark.parametrize(
    "factory",
    [
        lambda: A.NoOp(p=1),
        lambda: A.RandomBrightnessContrast(
            brightness_limit=(0.01, 0.01), contrast_limit=(0.1, 0.1), p=1
        ),
        lambda: A.GaussNoise(std_range=(0.001, 0.001), p=1),
        lambda: A.GaussianBlur(sigma_limit=(0.8, 0.8), p=1),
        lambda: A.Sharpen(alpha=(0.3, 0.3), method="gaussian", p=1),
        lambda: A.AdditiveNoise(
            noise_type="uniform",
            spatial_mode="constant",
            noise_params={"ranges": [(-0.001, 0.001)]},
            p=1,
        ),
    ],
)
def test_direct_stock_parity_and_copied_inputs(sample, channels, factory):
    image, label, valid = sample
    image = image[:, :, :channels].copy()
    originals = (image.copy(), label.copy(), valid.copy())
    transform = factory()
    actual, targets, support, metadata = apply_augmentation(
        transform, image, label, valid, seed=33
    )
    direct = factory()
    direct.add_targets({"validity": "mask"})
    direct.set_random_seed(33)
    expected = direct(
        image=image.astype(np.float32) / NATIVE_SCALE,
        mask=label.copy(),
        validity=valid.astype(np.int8),
    )
    expected_raw = expected["image"] * NATIVE_SCALE
    expected_raw[~valid] = 0
    np.testing.assert_array_equal(actual, expected_raw)
    np.testing.assert_array_equal(targets, expected["mask"])
    np.testing.assert_array_equal(support, expected["validity"] == 1)
    for source, before in zip((image, label, valid), originals, strict=True):
        np.testing.assert_array_equal(source, before)
    assert actual.dtype == np.float32
    assert targets.dtype == np.int8 and support.dtype == bool
    assert not np.shares_memory(actual, image)
    assert not np.shares_memory(targets, label)
    assert metadata["class"] == type(transform).__name__
    assert metadata["kwargs"]["p"] == 1
    assert "__class_fullname__" not in metadata["kwargs"]
    json.dumps(metadata)


def test_full_native_scale_before_final_model_cap():
    image = np.array([[[6000, 100, 65535], [0, 10, 5000]]], dtype=np.uint16)
    valid = np.ones((1, 2), dtype=bool)
    label = np.zeros((1, 2), dtype=np.int8)
    gained, _, support, _ = apply_augmentation(
        A.RandomBrightnessContrast(
            brightness_limit=(0, 0), contrast_limit=(-0.2, -0.2), p=1
        ),
        image,
        label,
        valid,
    )
    assert gained[0, 0, 0] == pytest.approx(4800, abs=0.001)
    assert cap_raw(gained, support)[0, 0, 0] == pytest.approx(4800, abs=0.001)
    assert gained[0, 0, 2] > 5000
    assert cap_raw(gained, support)[0, 0, 2] == 5000
    # Stock zero lower bound does not create new nodata at valid selected zeros.
    darkened, targets, support, _ = apply_augmentation(
        A.RandomBrightnessContrast(
            brightness_limit=(-300 / NATIVE_SCALE, -300 / NATIVE_SCALE),
            contrast_limit=(0, 0),
            p=1,
        ),
        image,
        label,
        valid,
    )
    assert darkened[0, 0, 1] == 0
    assert darkened[0, 1, 0] == 0 and support[0, 1]
    np.testing.assert_array_equal(targets, label)


def test_d4_moves_image_label_native_validity_and_padding_together(sample):
    image, label, valid = sample
    rotated, targets, support, metadata = apply_augmentation(
        A.D4(p=1), image, label, valid, fixed_parameters={"group_element": "r90"}
    )
    np.testing.assert_allclose(rotated, np.rot90(image), atol=0.0001)
    np.testing.assert_array_equal(targets, np.rot90(label))
    np.testing.assert_array_equal(support, np.rot90(valid))
    assert metadata["applied"]["group_element"] == "r90"
    assert metadata["fixed_parameters"] == {"group_element": "r90"}


def test_stock_coarse_dropout_int8_mask_fill_erases_targets_and_support(sample):
    image, label, valid = sample
    transform = A.CoarseDropout(
        num_holes_range=(1, 1),
        hole_height_range=(3, 3),
        hole_width_range=(3, 3),
        fill=0,
        fill_mask=-100,
        p=1,
    )
    raw, targets, support, metadata = apply_augmentation(
        transform, image, label, valid, seed=33
    )
    x0, y0, x1, y1 = metadata["applied"]["holes"][0]
    assert (x1 - x0, y1 - y0) == (3, 3)
    assert np.all(raw[y0:y1, x0:x1] == 0)
    assert np.all(targets[y0:y1, x0:x1] == -100)
    assert not support[y0:y1, x0:x1].any()
    outside = np.ones(valid.shape, dtype=bool)
    outside[y0:y1, x0:x1] = False
    np.testing.assert_array_equal(support[outside], valid[outside])
    np.testing.assert_array_equal(targets[outside], label[outside])
    # Verify the stock mask target really carries -100, rather than treating it
    # as true via a boolean cast. The adapter intentionally compares with one.
    direct = A.CoarseDropout(
        num_holes_range=(1, 1),
        hole_height_range=(3, 3),
        hole_width_range=(3, 3),
        fill=0,
        fill_mask=-100,
        p=1,
    )
    direct.add_targets({"validity": "mask"})
    direct.set_random_seed(33)
    result = direct(
        image=image.astype(np.float32) / NATIVE_SCALE,
        mask=label.copy(),
        validity=valid.astype(np.int8),
    )
    assert np.all(result["validity"][y0:y1, x0:x1] == -100)
    np.testing.assert_array_equal(support, result["validity"] == 1)


@pytest.mark.parametrize("channel", [5, 7])
def test_full_named_red_or_nir_dropout_preserves_all_targets_and_validity(
    sample, channel
):
    image, label, valid = sample
    raw, targets, support, metadata = apply_augmentation(
        A.ChannelDropout(channel_drop_range=(1, 1), fill=0, p=1),
        image,
        label,
        valid,
        fixed_parameters={"channels_to_drop": [channel]},
    )
    assert np.all(raw[:, :, channel] == 0)
    np.testing.assert_array_equal(targets, label)
    np.testing.assert_array_equal(support, valid)
    others = [index for index in range(8) if index != channel]
    np.testing.assert_allclose(raw[:, :, others], image[:, :, others], atol=0.0001)
    assert metadata["applied"]["channels_to_drop"] == [channel]


def test_stock_blur_sees_zero_nodata_without_custom_mask_normalization():
    image = np.full((9, 9, 8), 100, dtype=np.uint16)
    valid = np.ones((9, 9), dtype=bool)
    valid[:, 0] = False
    image[:, 0] = 0
    label = np.zeros((9, 9), dtype=np.int8)
    label[:, 0] = -100
    blurred, targets, support, _ = apply_augmentation(
        A.GaussianBlur(sigma_limit=(1, 1), p=1), image, label, valid
    )
    assert 0 < blurred[4, 1, 0] < 100
    assert np.all(blurred[:, 0] == 0)
    np.testing.assert_array_equal(support, valid)
    np.testing.assert_array_equal(targets, label)


def test_stock_probability_respected_and_noise_metadata_compact(sample):
    image, label, valid = sample
    skipped, targets, support, metadata = apply_augmentation(
        A.ChannelDropout(p=0), image, label, valid
    )
    np.testing.assert_allclose(skipped, image, atol=0.0001)
    np.testing.assert_array_equal(targets, label)
    np.testing.assert_array_equal(support, valid)
    assert metadata["applied"] == {}
    transform = A.GaussNoise(p=1)
    _, _, _, metadata = apply_augmentation(transform, image, label, valid)
    noise = metadata["applied"]["noise_map"]
    actual_field = transform.get_applied_params()["noise_map"]
    assert noise["shape"] == [9, 9, 8] and noise["dtype"] == "float32"
    assert noise["empirical_mean"] == pytest.approx(
        np.mean(actual_field, dtype=np.float64)
    )
    assert noise["empirical_std"] == pytest.approx(
        np.std(actual_field, dtype=np.float64)
    )
    assert noise["domain"] == "library unit-scale field before clipping"
    assert len(json.dumps(metadata)) < 1000


def test_stock_channel_dropout_cannot_remove_every_channel(sample):
    image, label, valid = sample
    with pytest.raises(ValueError, match="all channels"):
        apply_augmentation(
            A.ChannelDropout(channel_drop_range=(8, 8), p=1), image, label, valid
        )
    with pytest.raises(ValueError, match="one valid channel"):
        apply_augmentation(
            A.ChannelDropout(p=1),
            image,
            label,
            valid,
            fixed_parameters={"channels_to_drop": list(range(8))},
        )


def test_ordinary_input_errors(sample):
    image, label, valid = sample
    with pytest.raises(ValueError, match="raw HWC uint16"):
        apply_augmentation(A.NoOp(), image.astype(np.float32), label, valid)
    with pytest.raises(ValueError, match="HW int8"):
        apply_augmentation(A.NoOp(), image, label.astype(np.uint8), valid)
    with pytest.raises(ValueError, match="boolean mask"):
        apply_augmentation(A.NoOp(), image, label, valid.astype(np.int8))
    with pytest.raises(ValueError, match="only for D4"):
        apply_augmentation(
            A.GaussianBlur(), image, label, valid, fixed_parameters={"sigma": 1}
        )
