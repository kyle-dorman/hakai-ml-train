"""Binary objective and pooled metrics retain ignore and empty-support meaning."""

import pytest
import torch
from segmentation_models_pytorch.losses import LovaszLoss
from torch.nn import functional as F

from kelpseg.training.loss import segmentation_loss
from kelpseg.training.metrics import build_metrics


def test_objective_matches_approved_terms_and_ignores_gradients():
    logits = torch.tensor([[[[-2.0, 1.0, 20.0], [0.5, -1.0, 2.0]]]], requires_grad=True)
    target = torch.tensor([[[0, 1, -100], [1, 0, -100]]])
    valid = target != -100
    expected = 0.7 * F.binary_cross_entropy_with_logits(
        logits[:, 0][valid], target[valid].float() * 0.9 + 0.05
    ) + 0.3 * LovaszLoss(mode="binary", ignore_index=-100)(logits, target)
    actual = segmentation_loss(logits, target)
    torch.testing.assert_close(actual, expected)
    actual.backward()
    assert (logits.grad[:, 0][~valid] == 0).all()
    assert torch.isfinite(logits.grad).all()
    torch.testing.assert_close(actual, segmentation_loss(logits, target[:, None]))


@pytest.mark.parametrize("label", [0, 1, -100])
def test_uniform_targets_have_finite_loss_and_gradients(label):
    logits = torch.zeros((2, 1, 4, 4), requires_grad=True)
    loss = segmentation_loss(logits, torch.full((2, 4, 4), label))
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(logits.grad).all()
    if label == -100:
        assert loss.item() == 0
        assert not logits.grad.any()
    else:
        assert loss.item() > 0 and logits.grad.any()


def test_metrics_pool_pixels_not_chip_ratios_and_ignore():
    metrics = build_metrics()
    logits = torch.tensor([[[[1.0, 0.0, -1.0, -2.0, 10.0]]]])
    metrics.update((logits[:, 0] >= 0).long(), torch.tensor([[[1, 0, 1, 0, -100]]]))
    torch.testing.assert_close(
        metrics.compute()["confusion_matrix"], torch.tensor([[1, 1], [1, 1]])
    )
    metrics.update(
        torch.ones((1, 3, 3), dtype=torch.long), torch.ones((1, 3, 3), dtype=torch.long)
    )
    result = metrics.compute()
    assert result["iou"].item() == pytest.approx(10 / 12)
    assert result["iou"].item() != pytest.approx((1 / 3 + 1) / 2)
    assert result["precision"].item() == pytest.approx(10 / 11)
    assert result["recall"].item() == pytest.approx(10 / 11)
    assert result["f1"].item() == pytest.approx(20 / 22)
    assert result["accuracy"].item() == pytest.approx(11 / 13)
    assert result["confusion_matrix"].sum().item() == 13
    torch.testing.assert_close(
        result["confusion_matrix"], torch.tensor([[1, 1], [1, 10]])
    )

    # Reset prevents previous validation scopes from contaminating the next one.
    metrics.reset()
    metrics.update(
        torch.zeros((1, 5), dtype=torch.long), torch.zeros((1, 5), dtype=torch.long)
    )
    background = metrics.compute()
    assert background["accuracy"].item() == 1
    assert background["confusion_matrix"].sum().item() == 5
    assert all(
        background[key].item() == 0 for key in ("iou", "precision", "recall", "f1")
    )


def test_metrics_all_ignored_have_zero_support_and_library_zero_ratios():
    metrics = build_metrics()
    metrics.update(torch.ones((1, 5), dtype=torch.long), torch.full((1, 5), -100))
    result = metrics.compute()
    assert result["confusion_matrix"].sum().item() == 0
    assert all(
        result[key].item() == 0
        for key in ("iou", "precision", "recall", "f1", "accuracy")
    )


@pytest.mark.parametrize("shape", [(1, 2, 4, 4), (1, 4, 4)])
def test_reject_nonbinary_logits(shape):
    with pytest.raises(ValueError, match="Logits"):
        segmentation_loss(torch.zeros(shape), torch.zeros((1, 4, 4)))


def test_reject_wrong_target_shape_or_categories():
    with pytest.raises(ValueError, match="match logits"):
        segmentation_loss(torch.zeros((1, 1, 4, 4)), torch.zeros((1, 3, 4)))
    with pytest.raises(ValueError, match="only background"):
        segmentation_loss(torch.zeros((1, 1, 4, 4)), torch.full((1, 4, 4), 2))
