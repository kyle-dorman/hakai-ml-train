"""Bounded CPU checks of native Lightning updates, validation and averaging."""

from types import SimpleNamespace

import lightning.pytorch as pl
import pytest
import torch
from lightning.pytorch.callbacks import Callback, ModelCheckpoint
from torch import nn
from torch.utils.data import DataLoader

from kelpseg.training.ema import DelayedEMA
from kelpseg.training.loss_settings import DEFAULT_LOSSES, DEFAULT_PARAMETERS, LossTerm
from kelpseg.training.module import TrainingModule, parameter_groups
from kelpseg.training.scheduler import LinearWarmupCosineDecayLR


def settings(epochs=2):
    return SimpleNamespace(
        epochs=epochs,
        warmup_epochs=1,
        learning_rate=0.03,
        min_lr=0.003,
        betas=(0.9, 0.95),
        weight_decay=0.01,
        band_names=("nir", "red", "green"),
        encoder_weights=None,
        losses=DEFAULT_LOSSES,
    )


def loader(count=5, ignored=False):
    return DataLoader(
        [
            {
                "image": torch.ones(3, 2, 2),
                "target": torch.full((2, 2), -100 if ignored else 1, dtype=torch.long),
            }
            for _ in range(count)
        ],
        batch_size=1,
    )


class Observe(Callback):
    def __init__(self, ema):
        self.ema = ema
        self.updates = {}
        self.validation_weights = []
        self.average_counts = []

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        self.updates[trainer.global_step] = pl_module.model.weight.detach().clone()

    def on_validation_epoch_start(self, trainer, pl_module):
        self.validation_weights.append(pl_module.model.weight.detach().clone())
        self.average_counts.append(int(self.ema._average_model.n_averaged))


def trainer(tmp_path, callbacks, epochs=2):
    return pl.Trainer(
        accelerator="cpu",
        devices=1,
        precision="32-true",
        max_epochs=epochs,
        accumulate_grad_batches=2,
        logger=False,
        callbacks=callbacks,
        default_root_dir=tmp_path,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
    )


def test_scheduler_matches_retained_endpoints():
    parameter = nn.Parameter(torch.ones(()))
    optimizer = torch.optim.AdamW([parameter], lr=3e-4)
    schedule = LinearWarmupCosineDecayLR(optimizer, 140, 10, 3e-5)
    values = [optimizer.param_groups[0]["lr"]]
    for _ in range(140):
        optimizer.step()
        schedule.step()
        values.append(optimizer.param_groups[0]["lr"])
    from src.schedulers import LinearWarmupCosineDecayLR as RetainedScheduler

    reference_optimizer = torch.optim.AdamW([nn.Parameter(torch.ones(()))], lr=3e-4)
    reference = RetainedScheduler(
        reference_optimizer, total_steps=140, warmup_steps=10, min_lr=3e-5
    )
    reference_values = [reference_optimizer.param_groups[0]["lr"]]
    for _ in range(140):
        reference_optimizer.step()
        reference.step()
        reference_values.append(reference_optimizer.param_groups[0]["lr"])
    assert values == reference_values
    assert values[0] == 0
    assert values[5] == pytest.approx(1.5e-4)
    assert values[10] == pytest.approx(3e-4)
    assert values[-1] == pytest.approx(3e-5)
    assert all(a >= b for a, b in zip(values[10:], values[11:], strict=False))


def test_bias_and_norm_have_no_decay():
    model = nn.Sequential(nn.Conv2d(3, 4, 1), nn.BatchNorm2d(4), nn.LayerNorm(4))
    groups = parameter_groups(model)
    assert {id(p) for p in groups[0]["params"]} == {id(model[0].weight)}
    assert {id(p) for p in groups[1]["params"]} == {
        id(model[0].bias),
        id(model[1].weight),
        id(model[1].bias),
        id(model[2].weight),
        id(model[2].bias),
    }
    assert groups[1]["weight_decay"] == 0


def test_partial_accumulation_early_validation_and_earliest_tie(tmp_path):
    pl.seed_everything(42)
    model = nn.Conv2d(3, 1, 1)
    nn.init.constant_(model.weight, 0.2)
    nn.init.zeros_(model.bias)
    initial = model.weight.detach().clone()
    module = TrainingModule(settings(), model)
    ema = DelayedEMA()
    observe = Observe(ema)
    checkpoint = ModelCheckpoint(
        dirpath=tmp_path,
        filename="best",
        monitor="val/iou",
        mode="max",
        save_last=False,
        save_on_train_epoch_end=False,
    )
    last_checkpoint = ModelCheckpoint(
        dirpath=tmp_path,
        filename="last",
        monitor=None,
        save_top_k=1,
        save_last=False,
        save_on_train_epoch_end=True,
        enable_version_counter=False,
    )
    fit = trainer(tmp_path, [ema, observe, checkpoint, last_checkpoint])
    fit.fit(module, loader(), loader(2))
    assert fit.global_step == 6  # ceil(5 / 2) updates per epoch.
    assert module.lr_schedulers().last_epoch == 6
    assert module.lr_schedulers().get_last_lr()[0] == pytest.approx(0.003)
    assert observe.average_counts == [0, 0]
    assert not torch.equal(initial, observe.validation_weights[0])
    for step, weights in zip((3, 6), observe.validation_weights, strict=True):
        torch.testing.assert_close(weights, observe.updates[step])
    best = torch.load(checkpoint.best_model_path, weights_only=False)
    last = torch.load(last_checkpoint.best_model_path, weights_only=False)
    assert best["epoch"] == 0  # Same pooled IoU in both epochs; earliest wins.
    assert last["epoch"] == 1
    torch.testing.assert_close(last["state_dict"]["model.weight"], model.weight)
    torch.testing.assert_close(
        last["current_model_state"]["model.weight"], model.weight
    )
    assert last["averaging_state"]["n_averaged"] == 0


def test_ema_first_copy101_and_separate_saved_states(tmp_path):
    pl.seed_everything(42)
    module = TrainingModule(settings(), nn.Conv2d(3, 1, 1))
    ema = DelayedEMA()
    observe = Observe(ema)
    checkpoint = ModelCheckpoint(
        dirpath=tmp_path,
        monitor="val/iou",
        mode="max",
        save_last=False,
        save_on_train_epoch_end=False,
    )
    last_checkpoint = ModelCheckpoint(
        dirpath=tmp_path,
        filename="last",
        monitor=None,
        save_top_k=1,
        save_last=False,
        save_on_train_epoch_end=True,
        enable_version_counter=False,
    )
    fit = trainer(tmp_path, [ema, observe, checkpoint, last_checkpoint])
    fit.fit(module, loader(102), loader(1))
    assert fit.global_step == 102
    assert observe.average_counts == [0, 2]
    expected = observe.updates[101] * 0.999 + observe.updates[102] * 0.001
    torch.testing.assert_close(observe.validation_weights[1], expected)
    saved = torch.load(last_checkpoint.best_model_path, weights_only=False)
    torch.testing.assert_close(saved["state_dict"]["model.weight"], expected)
    torch.testing.assert_close(
        saved["current_model_state"]["model.weight"], observe.updates[102]
    )
    assert saved["averaging_state"]["n_averaged"].item() == 2
    assert not torch.equal(
        saved["state_dict"]["model.weight"],
        saved["current_model_state"]["model.weight"],
    )
    torch.testing.assert_close(module.model.weight, observe.updates[102])
    assert fit.callback_metrics["val/pixels"] == 4
    assert module.train_metrics["train/iou"].update_count == 0
    assert module.val_metrics["val/iou"].update_count == 0
    assert module.train_loss.update_count == module.val_loss.update_count == 0


def test_zero_validation_support_refuses_selection(tmp_path):
    module = TrainingModule(settings(), nn.Conv2d(3, 1, 1))
    with pytest.raises(ValueError, match="no scored pixels"):
        trainer(tmp_path, [DelayedEMA()]).fit(module, loader(), loader(1, ignored=True))


def test_partial_accumulation_keeps_native_fixed_divisor(tmp_path):
    gradients = []

    class ConstantGradient(TrainingModule):
        def training_step(self, batch, batch_idx):
            return self.model.weight.sum()

        def on_before_optimizer_step(self, optimizer):
            gradients.append(self.model.weight.grad.detach().clone())

    module = ConstantGradient(settings(epochs=1), nn.Conv2d(3, 1, 1))
    trainer(tmp_path, [DelayedEMA()], epochs=1).fit(module, loader(), loader(1))
    assert len(gradients) == 3
    torch.testing.assert_close(gradients[0], torch.ones_like(gradients[0]))
    torch.testing.assert_close(gradients[1], torch.ones_like(gradients[1]))
    torch.testing.assert_close(gradients[2], torch.full_like(gradients[2], 0.5))


def test_validation_loss_weights_batch_objective_by_valid_pixels():
    from kelpseg.training.loss import BinaryObjective

    module = TrainingModule(settings(), nn.Identity())
    recorded = {}
    module.log = lambda name, value, **kwargs: recorded.update({name: value})
    module.on_validation_epoch_start()
    batches = [
        {
            "image": torch.tensor([[[[2.0, -1.0]]]]),
            "target": torch.tensor([[[1, -100]]]),
        },
        {"image": torch.tensor([[[[-2.0, 1.0]]]]), "target": torch.tensor([[[1, 0]]])},
    ]
    batches.append(
        {
            "image": torch.tensor([[[[7.0, 7.0]]]]),
            "target": torch.tensor([[[-100, -100]]]),
        }
    )
    for index, batch in enumerate(batches):
        module.validation_step(batch, index)
    module.on_validation_epoch_end()
    expected = (
        BinaryObjective()(batches[0]["image"], batches[0]["target"])[0]
        + 2 * BinaryObjective()(batches[1]["image"], batches[1]["target"])[0]
    ) / 3
    torch.testing.assert_close(recorded["val/loss"].compute(), expected.double())
    components = [
        BinaryObjective()(batch["image"], batch["target"])[1] for batch in batches
    ]
    for name in ("bce", "lovasz"):
        expected_component = (components[0][name] + 2 * components[1][name]) / 3
        torch.testing.assert_close(
            recorded[f"val/{name}"].compute(), expected_component.double()
        )
        assert components[2][name] == 0
    assert recorded["val/pixels"].compute() == 3
    assert recorded["val/iou"].compute().item() == pytest.approx(1 / 3)


@pytest.mark.parametrize(
    "terms",
    [
        DEFAULT_LOSSES,
        tuple(LossTerm(name, weight=0.2) for name in DEFAULT_PARAMETERS),
        (
            LossTerm("bce", name="metrics", weight=0.5),
            LossTerm(
                "bce",
                name="smooth_bce",
                weight=0.5,
                parameters={"smoothing": 0.2, "per_image": True},
            ),
        ),
    ],
)
def test_native_metric_logging_pools_and_resets_train_and_validation(tmp_path, terms):
    import csv

    from lightning.pytorch.loggers import CSVLogger

    class FlipWeights(Callback):
        def on_train_epoch_start(self, trainer, pl_module):
            with torch.no_grad():
                pl_module.model.weight.fill_(1 if trainer.current_epoch == 0 else -1)
                pl_module.model.bias.zero_()

    run_settings = settings()
    run_settings.learning_rate = run_settings.min_lr = 0.0
    run_settings.losses = terms
    module = TrainingModule(run_settings, nn.Conv2d(3, 1, 1))
    image = torch.tensor([[[1.0, -1.0], [-1.0, -1.0]]]).repeat(3, 1, 1)
    train = DataLoader(
        [
            {"image": image, "target": torch.tensor([[1, -100], [-100, -100]])},
            {"image": image, "target": torch.tensor([[0, 1], [1, 0]])},
        ],
        batch_size=1,
    )
    val = DataLoader(
        [
            {"image": image, "target": torch.ones((2, 2), dtype=torch.long)},
        ],
        batch_size=1,
    )
    logger = CSVLogger(tmp_path, name="native-metrics")
    fit = pl.Trainer(
        accelerator="cpu",
        devices=1,
        precision="32-true",
        max_epochs=2,
        logger=logger,
        callbacks=[DelayedEMA(), FlipWeights()],
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
        log_every_n_steps=1,
    )
    fit.fit(module, train, val)
    with open(logger.log_dir + "/metrics.csv", newline="") as stream:
        records = list(csv.DictReader(stream))
    assert "train/accuracy" not in records[0] and "val/accuracy" not in records[0]
    train_records = [record for record in records if record["train/iou"]]
    val_records = [record for record in records if record["val/iou"]]
    assert [float(record["train/iou"]) for record in train_records] == [0.25, 0.5]
    assert [float(record["val/iou"]) for record in val_records] == [0.25, 0.75]
    for phase, phase_records in (("train", train_records), ("val", val_records)):
        for name in (
            "iou",
            "precision",
            "recall",
            "f1",
            "auroc",
            "calibration_error",
            "loss",
            *(term.name for term in terms),
        ):
            assert all(record[f"{phase}/{name}"] for record in phase_records)
    step_records = [record for record in records if record["train/iou_step"]]
    assert [
        float(record["train/iou_step"]) for record in step_records
    ] == pytest.approx([1.0, 0.0, 0.0, 2 / 3])
    for record in step_records:
        assert float(record["train/loss_step"]) == pytest.approx(
            sum(
                term.weight * float(record[f"train/{term.name}_step"]) for term in terms
            )
        )
    for phase, phase_records in (("train", train_records), ("val", val_records)):
        for record in phase_records:
            assert float(record[f"{phase}/loss"]) == pytest.approx(
                sum(
                    term.weight * float(record[f"{phase}/{term.name}"])
                    for term in terms
                )
            )
        for name in (term.name for term in terms):
            assert module.component_metrics[f"{phase}_{name}"].update_count == 0
    assert all(float(record["val/pixels"]) == 4 for record in val_records)
    assert not any(
        name in records[0] for name in ("val/tn", "val/fp", "val/fn", "val/tp")
    )
    assert module.train_metrics["train/iou"].update_count == 0
    assert module.val_metrics["val/iou"].update_count == 0
    assert module.train_loss.update_count == module.val_loss.update_count == 0
    assert module.val_pixels.update_count == 0
    assert module.train_probability_metrics["train/auroc"].update_count == 0
    assert module.val_probability_metrics["val/calibration_error"].update_count == 0


def test_regional_validation_pools_pixels_and_resets(tmp_path):
    import csv

    from lightning.pytorch.loggers import CSVLogger

    from kelpseg.training.run import collate_chips

    config = settings()
    config.learning_rate = config.min_lr = 0.0
    model = nn.Conv2d(3, 1, 1)
    nn.init.ones_(model.weight)
    nn.init.zeros_(model.bias)
    module = TrainingModule(config, model)
    rows = [
        dict(
            region=region, source_id=str(i), row=0, col=0, kelp_pixels=1, payload=str(i)
        )
        for i, region in enumerate(["001", "001", "002"])
    ]
    module.configure_diagnostics(rows)
    val = DataLoader(
        [
            dict(
                image=torch.ones(3, 2, 2),
                target=target,
                valid_mask=target != -100,
                metadata=metadata,
            )
            for target, metadata in zip(
                [
                    torch.tensor([[1, -100], [-100, -100]]),
                    torch.tensor([[0, 0], [0, -100]]),
                    torch.tensor([[1, 1], [-100, -100]]),
                ],
                rows,
                strict=True,
            )
        ],
        batch_size=2,
        collate_fn=collate_chips,
    )
    logger = CSVLogger(tmp_path, name="regions")
    fit = pl.Trainer(
        accelerator="cpu",
        devices=1,
        max_epochs=2,
        logger=logger,
        enable_checkpointing=False,
        enable_progress_bar=False,
        enable_model_summary=False,
        num_sanity_val_steps=0,
    )
    fit.fit(module, loader(2), val)
    with open(logger.log_dir + "/metrics.csv") as stream:
        records = [r for r in csv.DictReader(stream) if r["val_region_001/iou"]]
    assert len(records) == 2
    for record in records:
        assert float(record["val_region_001/iou"]) == pytest.approx(0.25)
        assert float(record["val_region_002/iou"]) == 1
        assert float(record["val_region_001/pixels"]) == 4
        assert float(record["val_region_002/pixels"]) == 2
        assert float(record["val/iou"]) == pytest.approx(0.5)
        probability = torch.tensor(3.0).sigmoid().item()
        assert float(record["val_region_001/calibration_error"]) == pytest.approx(
            probability - 0.25
        )
        assert float(record["val_region_002/calibration_error"]) == pytest.approx(
            1 - probability
        )
        assert float(record["val_region_001/auroc"]) == pytest.approx(0.5)
    assert module.region_pixels["001"].update_count == 0
    assert module.region_metrics["001"]["val_region_001/iou"].update_count == 0
    assert (
        module.region_probability_metrics["001"]["val_region_001/auroc"].update_count
        == 0
    )
    assert (
        module.region_probability_metrics["002"][
            "val_region_002/calibration_error"
        ].update_count
        == 0
    )
