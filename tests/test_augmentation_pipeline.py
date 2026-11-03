"""Actual selected Compose behavior, pairing, and native-scale preprocessing."""

import json
from pathlib import Path

import albumentations as A
import numpy as np
import pytest

from kelpseg.augmentation_debug.pipeline import pipeline_states
from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.augmentations import NATIVE_SCALE, apply_augmentation
from kelpseg.preprocessing import BAND_NAMES, cap_raw


@pytest.fixture
def sample():
    image = (np.arange(64 * 64 * 8).reshape(64, 64, 8) % 7000).astype(np.uint16)
    valid = np.ones((64, 64), dtype=bool)
    valid[:5] = False
    valid[:, -7:] = False
    image[~valid] = 0
    label = np.zeros((64, 64), dtype=np.int8)
    label[~valid] = -100
    label[16:48, 16:48] = 1
    return dict(
        image=image,
        label=label,
        valid=valid,
        band_names=BAND_NAMES,
        closeup=(16, 16, 48, 48),
    )


def test_readable_factory_records_approved_ranges_and_equal_sampling():
    pipeline = build_training_augmentation()
    d4, selector = pipeline.transforms
    assert isinstance(d4, A.D4) and d4.p == 1
    assert isinstance(selector, A.SomeOf)
    assert selector.n == 2 and not selector.replace and selector.p == 1
    pool = selector.transforms
    assert len(pool) == 8 and all(transform.p == 1 for transform in pool)
    assert pool[0].brightness_limit == (-0.0025, 0.005)
    assert pool[0].contrast_limit == (0, 0)
    assert pool[1].brightness_limit == (0, 0)
    assert pool[1].contrast_limit == (-0.2, 0.2)
    assert pool[2].sigma_limit == (0.5, 1.5) and pool[2].blur_limit == (0, 0)
    assert pool[3].std_range == (0, 0.002) and pool[3].per_channel
    assert pool[4].alpha == (0, 1) and pool[4].method == "gaussian"
    assert pool[5].num_holes_range == (1, 4)
    assert pool[5].hole_height_range == pool[5].hole_width_range == (0.05, 0.25)
    assert pool[5].fill == 0 and pool[5].fill_mask == -100
    assert pool[6].spatial_mode == "constant"
    assert pool[6].noise_params["ranges"] == [(-0.01, 0.01)]
    assert pool[7].channel_drop_range == (1, 1) and pool[7].fill == 0


def test_saved_approved_recipe_matches_readable_factory():
    path = Path(__file__).parents[1] / "configs/augment/baseline.json"
    expected = json.loads(json.dumps(A.to_dict(build_training_augmentation(seed=33))))
    assert json.loads(path.read_text()) == expected


@pytest.mark.parametrize("seed", [7, 11, 33])
def test_adapter_and_full_state_match_direct_stock_compose(sample, seed):
    image, label, valid = sample["image"], sample["label"], sample["valid"]
    pipeline = build_training_augmentation(seed)
    pipeline.add_targets({"validity": "mask"})
    expected = pipeline(
        image=image.astype(np.float32) / NATIVE_SCALE,
        mask=label.copy(),
        validity=valid.astype(np.int8),
    )
    expected_valid = expected["validity"] == 1
    expected_image = expected["image"] * NATIVE_SCALE
    expected_image[~expected_valid] = 0
    states = pipeline_states(sample, seed)
    full = states[-1]
    np.testing.assert_array_equal(full["image"], expected_image)
    np.testing.assert_array_equal(full["label"], expected["mask"])
    np.testing.assert_array_equal(full["valid"], expected_valid)
    assert [name for name, _ in full["parameters"]["applied"]] == [
        name for name, _ in expected["applied_transforms"]
    ]
    assert len(full["parameters"]["operation_trace"]) == 3
    json.dumps(full["parameters"])


def test_seed_replay_source_preservation_and_exactly_two_distinct_extras(sample):
    originals = {name: sample[name].copy() for name in ("image", "label", "valid")}
    first, second = pipeline_states(sample, 33), pipeline_states(sample, 33)
    for a, b in zip(first, second, strict=True):
        for name in ("image", "label", "valid"):
            np.testing.assert_array_equal(a[name], b[name])
        assert a["parameters"] == b["parameters"]
    for name, before in originals.items():
        np.testing.assert_array_equal(sample[name], before)
    assert not np.array_equal(
        first[-1]["image"], pipeline_states(sample, 34)[-1]["image"]
    )

    # A fresh stock Compose per draw exposes exactly the selected children.
    # Observe every pool entry across a bounded deterministic set of real draws.
    eligible = set()
    for seed in range(32):
        pipeline = build_training_augmentation(seed)
        result = pipeline(
            image=sample["image"].astype(np.float32) / NATIVE_SCALE,
            mask=sample["label"].copy(),
        )
        selected = [
            index
            for index, child in enumerate(pipeline.transforms[1].transforms)
            if child.get_applied_params()
        ]
        assert len(selected) == 2 and len(set(selected)) == 2
        eligible.update(selected)
        assert len(result["applied_transforms"]) == 3
        assert result["applied_transforms"][0][0] == "D4"
    assert eligible == set(range(8))


def test_d4_reference_and_final_share_transformed_footprint(sample):
    source, reference, full = pipeline_states(sample, 33)
    group = full["parameters"]["applied"][0][1]["group_element"]
    d4 = A.D4(p=1)
    np.testing.assert_array_equal(
        reference["label"], d4.apply_to_mask(sample["label"], group)
    )
    np.testing.assert_array_equal(
        reference["valid"], d4.apply_to_mask(sample["valid"], group)
    )
    np.testing.assert_array_equal(source["label"], sample["label"])
    assert source["closeup"] == sample["closeup"]
    footprint = np.zeros(sample["valid"].shape, dtype=np.uint8)
    y0, x0, y1, x1 = sample["closeup"]
    footprint[y0:y1, x0:x1] = 1
    moved = d4.apply_to_mask(footprint, group)
    ys, xs = np.where(moved)
    assert (
        reference["closeup"]
        == full["closeup"]
        == (ys.min(), xs.min(), ys.max() + 1, xs.max() + 1)
    )


def test_coarse_ignore_survives_later_photometric_operation(sample):
    # This real seed selects CoarseDropout then AdditiveNoise in pool order.
    _, reference, full = pipeline_states(sample, 7)
    trace = full["parameters"]["operation_trace"]
    assert [entry["class"] for entry in trace] == [
        "D4",
        "CoarseDropout",
        "AdditiveNoise",
    ]
    expected_label, expected_valid = (
        reference["label"].copy(),
        reference["valid"].copy(),
    )
    holes = trace[1]["parameters"]["holes"]
    assert 1 <= len(holes) <= 4
    for x0, y0, x1, y1 in holes:
        expected_label[y0:y1, x0:x1] = -100
        expected_valid[y0:y1, x0:x1] = False
        assert np.all(full["image"][y0:y1, x0:x1] == 0)
    np.testing.assert_array_equal(full["label"], expected_label)
    np.testing.assert_array_equal(full["valid"], expected_valid)
    assert full["metrics"]["ignored_pixels"] >= reference["metrics"]["ignored_pixels"]


def test_named_dropped_band_is_recorded_and_retains_other_bands(sample):
    seed = next(
        seed
        for seed in range(32)
        if any(
            name == "ChannelDropout"
            for name, _ in apply_augmentation(
                build_training_augmentation(seed),
                sample["image"],
                sample["label"],
                sample["valid"],
                seed,
            )[3]["applied"]
        )
    )
    _, _, full = pipeline_states(sample, seed)
    entry = next(
        e
        for e in full["parameters"]["operation_trace"]
        if e["class"] == "ChannelDropout"
    )
    [index] = entry["parameters"]["channels_to_drop"]
    assert entry["dropped_bands"] == [BAND_NAMES[index]]
    assert np.all(full["image"][:, :, index] == 0)
    assert np.any(
        full["image"][full["valid"]][:, [i for i in range(8) if i != index]] != 0
    )


def test_compose_uses_raw_full_scale_before_final_cap():
    image = np.full((8, 8, 8), 6000, dtype=np.uint16)
    valid = np.ones((8, 8), dtype=bool)
    label = np.zeros((8, 8), dtype=np.int8)
    pipeline = A.Compose(
        [
            A.RandomBrightnessContrast(
                brightness_limit=(0, 0), contrast_limit=(-0.2, -0.2), p=1
            )
        ],
        save_applied_params=True,
        seed=33,
    )
    raw, _, support, _ = apply_augmentation(pipeline, image, label, valid)
    np.testing.assert_allclose(raw, 4800, atol=0.001)
    np.testing.assert_allclose(cap_raw(raw, support), 4800, atol=0.001)


def test_default_reuses_rng_and_fresh_factory_replays_the_advancing_sequence(sample):
    def sequence():
        pipeline = build_training_augmentation(seed=33)
        return [
            apply_augmentation(
                pipeline,
                sample["image"],
                sample["label"],
                sample["valid"],
            )
            for _ in range(3)
        ]

    first, replay = sequence(), sequence()
    assert not np.array_equal(first[0][0], first[1][0])
    assert first[0][3]["applied"] != first[1][3]["applied"]
    for actual, expected in zip(first, replay, strict=True):
        for output, reference in zip(actual[:3], expected[:3], strict=True):
            np.testing.assert_array_equal(output, reference)
        assert actual[3] == expected[3]
        assert actual[3]["seed"] is None


def test_explicit_preview_seed_replays_one_draw_from_a_reused_pipeline(sample):
    pipeline = build_training_augmentation(seed=99)
    outputs = [
        apply_augmentation(
            pipeline, sample["image"], sample["label"], sample["valid"], seed=33
        )
        for _ in range(2)
    ]
    for actual, expected in zip(outputs[0][:3], outputs[1][:3], strict=True):
        np.testing.assert_array_equal(actual, expected)
    assert outputs[0][3] == outputs[1][3]


def test_native_serialized_recipe_applies_without_optional_trace_recording(sample):
    factory = build_training_augmentation()
    restored = A.from_dict(A.to_dict(factory))
    # Stock serialization omits the diagnostic save_applied_params option.
    assert not restored.save_applied_params
    direct = apply_augmentation(
        factory, sample["image"], sample["label"], sample["valid"], seed=33
    )
    replay = apply_augmentation(
        restored, sample["image"], sample["label"], sample["valid"], seed=33
    )
    for actual, expected in zip(replay[:3], direct[:3], strict=True):
        np.testing.assert_array_equal(actual, expected)
    assert replay[3]["applied"] == []
    assert len(direct[3]["applied"]) == 3
