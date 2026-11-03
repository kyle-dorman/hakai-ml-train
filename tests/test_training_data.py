"""Training selection and shared preprocessing preserve scientific input scope."""

import csv
import json

import albumentations as A
import numpy as np
import pytest
import torch

from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.augmentations import apply_augmentation
from kelpseg.bands import resolve_band_indices
from kelpseg.preprocessing import BAND_NAMES, normalize
from kelpseg.training.data import ChipDataset, build_training_inputs
from kelpseg.training.transforms import build_input_transform


def _payload(path, *, height=3, width=4, kelp=True):
    image = np.broadcast_to(
        np.arange(1, 9, dtype=np.uint16) * 1000, (height, width, 8)
    ).copy()
    image[0, 0] = 0
    # Native-valid even though all RGB/NIR channels are zero.
    image[0, 1] = 0
    image[0, 1, 0] = 20
    target = np.zeros((height, width), dtype=np.int8)
    target[1, 0] = 1 if kelp else 0
    target[1, 1] = -100
    np.savez_compressed(path, image=image, label=target)
    return image, target


def _collection(root):
    (root / "recipe.json").write_text(
        json.dumps(dict(source_band_names=BAND_NAMES, chip_size=4))
    )
    sources, rows, assignments = [], [], []
    for index, (role, positive) in enumerate(
        [("train", 1), ("train", 0), ("val", 0), ("val", 1), ("test", 0)]
    ):
        source = dict(
            source_key=str(index),
            source_id=str(index),
            original_tiff=f"{index}.tif",
            dataset_id="fixture",
            release_id="v1",
            region="001",
            acquisition_date=f"2021-01-{index + 1:02d}",
            satellite_id="test",
            row_offset=0,
            col_offset=0,
            height=3,
            width=4,
        )
        sources.append(source)
        assignments.append(
            dict(
                source,
                experiment="baseline",
                variant="augmented",
                split=role,
                reason="fixture",
            )
        )
        rows.append(
            dict(
                source_key=str(index),
                row=0,
                col=0,
                original_row=0,
                original_col=0,
                height=3,
                width=4,
                kelp_pixels=positive,
                disposition="retained",
                payload=f"{index}.npz",
            )
        )
        if role != "test":
            _payload(root / f"{index}.npz", kelp=bool(positive))
    (root / "sources.json").write_text(json.dumps(sources))
    with (root / "windows.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return assignments


def test_manifest_selection_filters_train_only_and_never_reads_test(
    tmp_path, monkeypatch
):
    assignments = _collection(tmp_path)
    original_load = np.load
    opened = []

    def guarded(path, *args, **kwargs):
        assert str(path).endswith(("0.npz", "2.npz", "3.npz"))
        opened.append(str(path))
        return original_load(path, *args, **kwargs)

    monkeypatch.setattr(np, "load", guarded)
    inputs = build_training_inputs(tmp_path, assignments, selection="rgb")
    assert not opened
    assert inputs["counts"] == dict(
        training_candidates=2,
        training_eligible=1,
        training_excluded_zero_kelp=1,
        validation=2,
        test_metadata_only=1,
    )
    assert [row["source_id"] for row in inputs["excluded_training_rows"]] == ["1"]
    assert [row["source_id"] for row in inputs["test_rows"]] == ["4"]
    assert len(inputs["train"]) == 1 and len(inputs["val"]) == 2
    assert inputs["train"][0]["image"].shape == (3, 4, 4)
    assert inputs["val"][0]["target"].eq(1).sum() == 0
    assert inputs["val"][1]["target"].eq(1).sum() == 1
    assert len(opened) == 3
    with pytest.raises(ValueError, match="train/val"):
        ChipDataset(inputs["test_rows"], BAND_NAMES)


@pytest.mark.parametrize("selection", ["all", "rgbnir", "rgb"])
def test_partial_edges_native_validity_physical_order_and_exact_normalization(
    tmp_path, selection
):
    payload = tmp_path / "partial.npz"
    image, target = _payload(payload)
    row = dict(
        split="val",
        payload=payload,
        source_id="scene",
        original_row=71,
        original_col=29,
        region="010",
        acquisition_date="2021-03-01",
    )
    sample = ChipDataset([row], BAND_NAMES, selection, chip_size=4)[0]
    indices = resolve_band_indices(BAND_NAMES, selection)
    names = tuple(BAND_NAMES[i] for i in indices)
    valid = np.any(image != 0, axis=-1)
    expected = normalize(image[:, :, indices], names, valid)
    np.testing.assert_allclose(
        sample["image"][:, :3].numpy(),
        expected.transpose(2, 0, 1),
        rtol=1e-6,
        atol=1e-6,
    )
    assert sample["image"].dtype == torch.float32
    assert sample["target"].dtype == torch.int64
    assert sample["valid_mask"][0, 1]  # Only coastal-blue is nonzero.
    assert sample["target"][0, 0] == -100
    assert sample["target"][1, 1] == -100
    assert not sample["image"][:, 3].any()
    assert (sample["target"][3] == -100).all()
    assert not sample["valid_mask"][3].any()
    metadata = sample["metadata"]
    assert metadata["band_names"] == names and metadata["padding"] == (0, 1, 0, 0)
    assert metadata["true_height"] == 3 and metadata["true_width"] == 4
    assert metadata["source_id"] == "scene" and metadata["original_row"] == 71
    assert (
        metadata["original_col"] == 29 and metadata["acquisition_date"] == "2021-03-01"
    )


@pytest.mark.parametrize("selection", ["all", "rgbnir", "rgb"])
def test_selected_channels_use_approved_shared_pipeline(tmp_path, selection):
    payload = tmp_path / "chip.npz"
    image, label = _payload(payload, height=16, width=16)
    valid = np.any(image != 0, axis=-1)
    label[~valid] = -100
    indices = resolve_band_indices(BAND_NAMES, selection)
    names = tuple(BAND_NAMES[i] for i in indices)
    raw, target, support, _ = apply_augmentation(
        build_training_augmentation(33), image[:, :, indices], label, valid
    )
    expected = normalize(raw, names, support)
    dataset = ChipDataset(
        [dict(split="train", payload=payload)],
        BAND_NAMES,
        selection,
        16,
        build_training_augmentation(33),
    )
    sample = dataset[0]
    np.testing.assert_allclose(
        sample["image"].numpy(), expected.transpose(2, 0, 1), rtol=1e-6, atol=1e-6
    )
    np.testing.assert_array_equal(sample["target"].numpy(), target)
    np.testing.assert_array_equal(sample["valid_mask"].numpy(), support)
    assert not np.array_equal(dataset[0]["image"].numpy(), sample["image"].numpy())


@pytest.mark.parametrize("selection", ["rgbnir", "rgb"])
def test_channel_dropout_can_only_drop_actual_model_inputs(tmp_path, selection):
    payload = tmp_path / "chip.npz"
    image = np.full((4, 4, 8), 1000, dtype=np.uint16)
    np.savez(payload, image=image, label=np.ones((4, 4), dtype=np.int8))
    transform = A.ChannelDropout(channel_drop_range=(1, 1), fill=0, p=1)
    dataset = ChipDataset(
        [dict(split="train", payload=payload)], BAND_NAMES, selection, 4, transform
    )
    dropped = set()
    for seed in range(30):
        transform.set_random_seed(seed)
        sample = dataset[0]
        indices = transform.get_applied_params()["channels_to_drop"]
        assert len(indices) == 1 and 0 <= indices[0] < len(dataset.band_names)
        dropped.add(dataset.band_names[indices[0]])
        assert sample["valid_mask"].all() and sample["target"].eq(1).all()
    assert dropped == set(dataset.band_names)


def test_reject_missing_labels_and_validation_augmentation(tmp_path):
    payload = tmp_path / "unlabeled.npz"
    np.savez(payload, image=np.ones((4, 4, 8), dtype=np.uint16))
    rows = [dict(split="val", payload=payload)]
    with pytest.raises(ValueError, match="requires mapped labels"):
        ChipDataset(rows, BAND_NAMES, chip_size=4)[0]
    with pytest.raises(ValueError, match="training rows only"):
        ChipDataset(rows, BAND_NAMES, augmentation=build_training_augmentation())


@pytest.mark.parametrize("kelp_count", [None, "-1", "invalid"])
def test_bad_training_counts_fail_before_payload_reads(
    tmp_path, monkeypatch, kelp_count
):
    assignments = _collection(tmp_path)
    path = tmp_path / "windows.csv"
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["kelp_pixels"] = kelp_count
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)

    def forbidden(*args, **kwargs):
        raise AssertionError("Selection must not read payloads")

    monkeypatch.setattr(np, "load", forbidden)
    with pytest.raises(ValueError, match="kelp_pixels"):
        build_training_inputs(tmp_path, assignments)


def test_coarse_dropout_preserves_ignored_support(tmp_path):
    payload = tmp_path / "chip.npz"
    image = np.full((8, 8, 8), 1000, dtype=np.uint16)
    label = np.ones((8, 8), dtype=np.int8)
    np.savez(payload, image=image, label=label)
    transform = A.CoarseDropout(
        num_holes_range=(1, 1),
        hole_height_range=(0.5, 0.5),
        hole_width_range=(0.5, 0.5),
        fill=0,
        fill_mask=-100,
        p=1,
    )
    sample = ChipDataset(
        [dict(split="train", payload=payload)], BAND_NAMES, "rgb", 8, transform
    )[0]
    invalid = ~sample["valid_mask"]
    assert invalid.sum() == 16
    assert (sample["target"][invalid] == -100).all()
    assert (sample["image"][:, invalid] == 0).all()


def test_full_pipeline_uses_stock_normalize_and_tensor_conversion():
    from albumentations.pytorch import ToTensorV2

    pipeline = build_input_transform(
        ("red", "green", "blue"), build_training_augmentation(33)
    )
    assert isinstance(pipeline, A.Compose)
    assert isinstance(pipeline.transforms[0], A.ToFloat)
    assert isinstance(pipeline.transforms[-3], A.Normalize)
    assert isinstance(pipeline.transforms[-1], ToTensorV2)
    result = pipeline(
        image=np.full((4, 4, 3), 1000, dtype=np.uint16),
        mask=np.ones((4, 4), dtype=np.int8),
        validity=np.ones((4, 4), dtype=np.int8),
    )
    assert result["image"].shape == (3, 4, 4)
    assert result["image"].dtype == torch.float32
    assert result["mask"].dtype == torch.int64
    assert isinstance(result["validity"], torch.Tensor)


@pytest.mark.parametrize("selection", ["all", "rgbnir", "rgb"])
def test_affine_translation_moves_image_labels_validity_and_partial_padding(
    tmp_path, selection
):
    import cv2

    payload = tmp_path / "affine.npz"
    image, label = _payload(payload, height=5, width=6)
    affine = A.Affine(
        scale=1,
        translate_px={"x": (2, 2), "y": (-1, -1)},
        rotate=0,
        shear=0,
        keep_ratio=True,
        interpolation=cv2.INTER_LINEAR,
        mask_interpolation=cv2.INTER_NEAREST,
        border_mode=cv2.BORDER_CONSTANT,
        fill=0,
        fill_mask=-100,
        fit_output=False,
        p=1,
    )
    sample = ChipDataset(
        [dict(split="train", payload=payload)], BAND_NAMES, selection, 8, affine
    )[0]
    indices = resolve_band_indices(BAND_NAMES, selection)
    names = tuple(BAND_NAMES[i] for i in indices)
    # Translation +2 columns/-1 row on the fixed padded grid. Native nodata and
    # bottom/right padding move with labels; newly exposed borders are ignored.
    moved = np.zeros((8, 8, len(indices)), dtype=np.uint16)
    moved[:4, 2:] = image[1:, :, indices]
    expected_valid = np.zeros((8, 8), dtype=bool)
    expected_valid[:4, 2:] = np.any(image[1:] != 0, axis=-1)
    expected_target = np.full((8, 8), -100, dtype=np.int64)
    expected_target[:4, 2:] = label[1:]
    expected_target[~expected_valid] = -100
    np.testing.assert_array_equal(sample["target"], expected_target)
    np.testing.assert_array_equal(sample["valid_mask"], expected_valid)
    np.testing.assert_allclose(
        sample["image"],
        normalize(moved, names, expected_valid).transpose(2, 0, 1),
        rtol=1e-6,
        atol=1e-6,
    )
    assert sample["image"].shape == (len(indices), 8, 8)
    assert sample["metadata"]["padding"] == (0, 3, 0, 2)
    assert (sample["image"][:, ~sample["valid_mask"]] == 0).all()


@pytest.mark.parametrize("scale", [0.95, 1.05])
def test_affine_scale_keeps_fixed_shape_and_nearest_mask_categories(tmp_path, scale):
    import cv2

    payload = tmp_path / "scale.npz"
    _payload(payload, height=25, width=27)
    affine = A.Affine(
        scale=scale,
        translate_px=0,
        rotate=0,
        shear=0,
        keep_ratio=True,
        interpolation=cv2.INTER_LINEAR,
        mask_interpolation=cv2.INTER_NEAREST,
        border_mode=cv2.BORDER_CONSTANT,
        fill=0,
        fill_mask=-100,
        fit_output=False,
        p=1,
    )
    sample = ChipDataset(
        [dict(split="train", payload=payload)], BAND_NAMES, "rgb", 32, affine
    )[0]
    assert sample["image"].shape == (3, 32, 32)
    assert sample["target"].shape == sample["valid_mask"].shape == (32, 32)
    assert set(sample["target"].unique().tolist()) <= {-100, 0, 1}
    assert (sample["target"][~sample["valid_mask"]] == -100).all()
    assert (sample["image"][:, ~sample["valid_mask"]] == 0).all()
