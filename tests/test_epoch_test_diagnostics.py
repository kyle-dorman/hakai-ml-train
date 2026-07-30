from __future__ import annotations

from types import MethodType, SimpleNamespace

import lightning.pytorch as pl
import torch

from src.data import DataModule
from src.models.smp import SMPBinarySegmentationModel


class _Metrics:
    def __init__(self, phase: str) -> None:
        self.phase = phase
        self.reset_count = 0

    def compute(self) -> dict[str, torch.Tensor]:
        return {f"{self.phase}/iou": torch.tensor(0.5)}

    def reset(self) -> None:
        self.reset_count += 1


def test_data_module_exposes_test_as_second_fit_evaluation_loader(tmp_path) -> None:
    paths = {}
    for split in ("train", "val", "test"):
        path = tmp_path / split
        path.mkdir()
        paths[split] = str(path)

    data = DataModule(
        train_chip_dir=paths["train"],
        val_chip_dir=paths["val"],
        test_chip_dir=paths["test"],
        batch_size=3,
        num_workers=0,
        test_every_val_epoch=True,
    )
    data.setup("fit")

    loaders = data.val_dataloader()
    assert isinstance(loaders, list)
    assert len(loaders) == 2
    assert loaders[0].dataset is data.ds_val
    assert loaders[1].dataset is data.ds_test


def test_binary_model_routes_second_validation_loader_to_test_metrics() -> None:
    model = object.__new__(SMPBinarySegmentationModel)
    pl.LightningModule.__init__(model)
    model._trainer = SimpleNamespace(sanity_checking=False)
    phases = []

    def phase_step(self, batch, batch_idx, phase, log_prefix=None):
        phases.append((phase, log_prefix))
        return phase

    model._phase_step = MethodType(phase_step, model)
    batch = (torch.tensor([1]), torch.tensor([1]))

    assert model.validation_step(batch, 0, dataloader_idx=0) == "val"
    assert model.validation_step(batch, 0, dataloader_idx=1) == "current_test"
    assert phases == [
        ("val", None),
        ("current_test", "test/current"),
    ]
    assert model._test_during_fit_updated is True


def test_epoch_end_logs_and_resets_test_diagnostics() -> None:
    model = object.__new__(SMPBinarySegmentationModel)
    pl.LightningModule.__init__(model)
    model.val_metrics = _Metrics("val")
    model.current_test_metrics = _Metrics("test/current")
    model._test_during_fit_updated = True
    logged = []
    model.log_dict = lambda values, **kwargs: logged.append((values, kwargs))

    model.on_validation_epoch_end()

    assert [set(values) for values, _ in logged] == [
        {"val/iou_epoch"},
        {"test/current/iou_epoch"},
    ]
    assert model.val_metrics.reset_count == 1
    assert model.current_test_metrics.reset_count == 1
    assert model._test_during_fit_updated is False


def test_final_test_uses_best_checkpoint_namespace() -> None:
    model = object.__new__(SMPBinarySegmentationModel)
    pl.LightningModule.__init__(model)
    model.test_metrics = _Metrics("test/best")
    logged = []
    model.log_dict = lambda values, **kwargs: logged.append((values, kwargs))

    model.on_test_epoch_end()

    assert set(logged[0][0]) == {"test/best/iou_epoch"}
    assert model.test_metrics.reset_count == 1
