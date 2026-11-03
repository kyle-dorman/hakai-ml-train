"""Combined previews replay actual affine geometry and follow source close-ups."""

import albumentations as A
import numpy as np
import pytest

from kelpseg.augmentation_debug import pipeline as preview
from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.augmentations import NATIVE_SCALE
from kelpseg.preprocessing import BAND_NAMES


@pytest.mark.parametrize("seed,applied", [(7, True), (33, False)])
def test_geometry_reference_replays_sampled_affine_and_moves_closeup(seed, applied):
    image = np.arange(64 * 64 * 8, dtype=np.uint16).reshape(64, 64, 8)
    valid = np.ones((64, 64), dtype=bool)
    valid[:5] = False
    valid[:, -7:] = False
    image[~valid] = 0
    label = np.zeros((64, 64), dtype=np.int8)
    label[~valid] = -100
    label[11:29, 17:37] = 1
    sample = dict(
        image=image,
        label=label,
        valid=valid,
        closeup=(11, 17, 29, 37),
        band_names=BAND_NAMES,
    )
    source, d4_reference, geometry, full = preview.pipeline_states(sample, seed)
    affine_trace = full["parameters"]["operation_trace"][1]
    assert affine_trace["class"] == "Affine"
    assert affine_trace["applied"] is applied

    # Sample stock geometry with the identical seed, but omit photometric extras.
    factory = build_training_augmentation(seed)
    geometry_pipeline = A.Compose(
        factory.transforms[:2], additional_targets={"validity": "mask"}, seed=seed
    )
    expected = geometry_pipeline(
        image=image.astype(np.float32) / NATIVE_SCALE,
        mask=label,
        validity=valid.astype(np.int8),
    )
    support = expected["validity"] == 1
    raw = expected["image"] * NATIVE_SCALE
    raw[~support] = 0
    np.testing.assert_array_equal(geometry["image"], raw)
    np.testing.assert_array_equal(geometry["label"], expected["mask"])
    np.testing.assert_array_equal(geometry["valid"], support)

    # The target rectangle is also the source close-up footprint. Nearest-mask
    # interpolation gives its actual output bounds, including clipped edges.
    ys, xs = np.where(expected["mask"] == 1)
    expected_crop = (ys.min(), xs.min(), ys.max() + 1, xs.max() + 1)
    assert geometry["closeup"] == full["closeup"] == expected_crop
    assert source["closeup"] == sample["closeup"]
    if not applied:
        for key in ("image", "label", "valid"):
            np.testing.assert_array_equal(d4_reference[key], geometry[key])
        assert geometry["closeup"] == d4_reference["closeup"]
    else:
        assert set(affine_trace["center_shift_pixels"]) == {"x", "y"}
        assert geometry["closeup"] != d4_reference["closeup"]
