"""Check streaming probability metrics against library and hand calculations."""

import pytest
import torch
from torchmetrics.classification import BinaryAUROC, BinaryCalibrationError

from kelpseg.training.probability_metrics import (
    BinnedBinaryAUROC,
    StreamingBinaryCalibrationError,
)


def test_streaming_matches_library_across_unequal_batches_and_endpoints():
    generator = torch.Generator().manual_seed(42)
    probability = torch.cat(
        (
            torch.rand(1000, generator=generator),
            torch.linspace(0, 1, 257),
            torch.linspace(0, 1, 16),
        )
    )
    target = torch.randint(0, 2, probability.shape, generator=generator)
    target[::17] = -100
    auc, calibration = BinnedBinaryAUROC(), StreamingBinaryCalibrationError()
    for start, end in ((0, 7), (7, 100), (100, len(target))):
        auc.update(probability[start:end], target[start:end])
        calibration.update(probability[start:end], target[start:end])
    reference = BinaryAUROC(thresholds=257, ignore_index=-100)
    expected_auc = reference(probability, target)
    torch.testing.assert_close(auc.confmat, reference.confmat)
    torch.testing.assert_close(auc.compute(), expected_auc)
    expected_calibration = BinaryCalibrationError(
        n_bins=15, norm="l1", ignore_index=-100
    )(probability, target)
    torch.testing.assert_close(calibration.compute().float(), expected_calibration)
    assert calibration.counts.numel() == 16 and auc.confmat.numel() == 257 * 4
    auc.reset()
    calibration.reset()
    assert not auc.confmat.any() and not calibration.counts.any()


def test_known_ranking_and_calibration_values():
    probability = torch.tensor([0.1, 0.45, 0.35, 0.8, 0.99])
    target = torch.tensor([0, 0, 1, 1, -100])
    auc = BinnedBinaryAUROC()
    calibration = StreamingBinaryCalibrationError()
    assert auc(probability, target) == pytest.approx(0.75)
    assert calibration(probability, target) == pytest.approx(
        (0.1 + 0.45 + 0.65 + 0.2) / 4
    )


def test_calibration_pools_bins_not_batch_errors():
    metric = StreamingBinaryCalibrationError()
    metric.update(torch.tensor([0.5]), torch.tensor([0]))
    metric.update(torch.tensor([0.5]), torch.tensor([1]))
    assert metric.compute() == 0
    metric.reset()
    metric.update(torch.tensor([0.2]), torch.tensor([-100]))
    assert torch.isnan(metric.compute())


@pytest.mark.parametrize("label", [0, 1])
def test_one_class_auroc_matches_library(label):
    probabilities = torch.tensor([0.0, 0.5, 1.0])
    targets = torch.full((3,), label)
    torch.testing.assert_close(
        BinnedBinaryAUROC()(probabilities, targets),
        BinaryAUROC(thresholds=257)(probabilities, targets),
    )
