"""Exact pooled loss arithmetic and distance-mask augmentation checks."""

import albumentations as A
import cv2
import numpy as np
import pytest
import torch
import torch.nn.functional as F

from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.training.loss import BinaryObjective, distance_weights
from kelpseg.training.loss_settings import LossTerm
from kelpseg.training.transforms import build_input_transform


def test_weighted_microbatch_bce_and_alpha_zero_gradients() -> None:
    """Hand-check positive weights, ignored pixels, pooling and ordinary parity."""
    target = torch.tensor([[[1, 1, 1, 1]], [[1, 0, -100, 1]]])
    distance = torch.tensor([[[0, 120, 240, 500]], [[float("nan"), 0, 0, 900]]])
    cap_weight = 1 + 2 * 2 ** (-500 / 120)
    expected = torch.tensor([3, 2, 1.5, cap_weight, 1, 1, 0, cap_weight])
    torch.testing.assert_close(
        distance_weights(target, distance, 2, 120).flatten(), expected
    )
    logits = torch.linspace(-2, 2, 8).reshape(2, 1, 1, 4).requires_grad_()
    bce = BinaryObjective((LossTerm("bce", weight=0.7), LossTerm("dice", weight=0.3)))
    unweighted, reference = bce(logits, target)

    for alpha in (0, 2):
        objective = BinaryObjective(
            (
                LossTerm("distance_bce", weight=0.7, parameters={"alpha": alpha}),
                bce.terms[1],
            )
        )
        with torch.autocast("cpu", dtype=torch.bfloat16):
            loss, terms = objective(logits, target, distance)
        torch.testing.assert_close(terms["distance_bce_unweighted"], reference["bce"])
        torch.testing.assert_close(terms["dice"], reference["dice"], rtol=0, atol=0)
        assert loss.dtype == torch.float32
        if alpha == 0:
            torch.testing.assert_close(loss, unweighted, rtol=0, atol=0)
            (grad,) = torch.autograd.grad(loss, logits)
            (expected_grad,) = torch.autograd.grad(unweighted, logits)
            torch.testing.assert_close(grad, expected_grad, rtol=0, atol=0)
        else:
            valid = target != -100
            per_pixel = F.binary_cross_entropy_with_logits(
                logits[:, 0][valid], target[valid].float(), reduction="none"
            )
            torch.testing.assert_close(
                terms["distance_bce"],
                (per_pixel * expected[expected > 0]).sum() / expected.sum(),
            )
            (grad,) = torch.autograd.grad(loss, logits)
            assert grad[:, 0][~valid].count_nonzero() == 0

    background = torch.zeros_like(target)
    _, terms = objective(logits, background, distance)
    torch.testing.assert_close(terms["distance_bce"], terms["distance_bce_unweighted"])
    ignored, terms = objective(logits, torch.full_like(target, -100), distance)
    assert ignored.item() == 0 and all(value.item() == 0 for value in terms.values())
    assert torch.autograd.grad(ignored, logits)[0].count_nonzero() == 0


@pytest.mark.parametrize(
    "parameters",
    [
        {"alpha": -1},
        {"alpha": float("inf")},
        {"half_distance_m": 0},
        {"per_image": True},
        {"pos_weight": 2},
        {"cap_m": 600},
    ],
)
def test_invalid_distance_bce_settings(parameters: dict) -> None:
    """Reject options incompatible with the weighted mean and fixed policy."""
    with pytest.raises(ValueError, match="distance_bce"):
        LossTerm("distance_bce", parameters=parameters)


def test_spatial_masks_follow_geometry_and_do_not_change_rng() -> None:
    """Compare seeded stock inputs and trace fractional distances through affine."""
    bands = ("nir", "red", "green")
    image = np.full((96, 96, 3), 1000, dtype=np.uint16)
    labels = np.zeros(image.shape[:2], dtype=np.int8)
    labels[16:70, 20:75] = 1
    valid = np.ones_like(labels)
    valid[:7] = 0
    distances = np.where(labels == 1, 22.25, 333.75).astype(np.float32)
    inputs = dict(image=image, mask=labels, validity=valid)
    plain = build_input_transform(bands, build_training_augmentation(42))
    enriched = build_input_transform(bands, build_training_augmentation(42))
    for _ in range(12):
        reference = plain(**inputs)
        result = enriched(**inputs, effective_distance_m=distances)
        for name in ("image", "mask", "validity"):
            torch.testing.assert_close(result[name], reference[name], rtol=0, atol=0)
        target, moved = result["mask"], result["effective_distance_m"]
        assert torch.all(moved[target == 1] == 22.25)
        assert torch.all(moved[target == 0] == 333.75)
        assert torch.all(moved[target == -100] == -100)

    affine = A.Affine(
        translate_px={"x": 3, "y": 2},
        mask_interpolation=cv2.INTER_NEAREST,
        border_mode=cv2.BORDER_CONSTANT,
        fill_mask=-100,
        p=1,
    )
    transform = build_input_transform(bands, A.Compose([affine], seed=42))
    moved = transform(**inputs, effective_distance_m=distances)["effective_distance_m"]
    np.testing.assert_array_equal(moved[9:, 3:], distances[7:-2, :-3])
    assert (moved[:9] == -100).all()
    assert (moved[:, :3] == -100).all()


def test_distance_recipes_match_b0_except_data_name_and_bce() -> None:
    """Keep the three arms matched to each other and the existing B0 settings."""
    from dataclasses import replace

    from kelpseg.training.settings import load_settings

    baseline = load_settings("configs/train/model_size/b0.toml")
    for alpha in (0, 1, 2):
        settings = load_settings(f"configs/train/distance_weighting/alpha{alpha}.toml")
        assert settings.name == f"planet8-cabc-b0-distance-alpha{alpha}-70ep"
        assert settings.chips == "data/chips/ca_bc/v1-distance500"
        weighted, dice = settings.losses
        assert weighted == LossTerm(
            "distance_bce", weight=0.7, parameters={"alpha": alpha}
        )
        assert dice == baseline.losses[1]
        assert (
            replace(
                settings,
                name=baseline.name,
                chips=baseline.chips,
                losses=baseline.losses,
            )
            == baseline
        )
