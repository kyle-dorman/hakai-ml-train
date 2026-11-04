"""Single-model Lightning training with pooled validation agreement."""

import lightning.pytorch as pl
import torch
from lightning.pytorch.loggers import WandbLogger
from torch import nn
from torchmetrics import MeanMetric, SumMetric
from torchmetrics.functional.classification import binary_jaccard_index

from kelpseg.models import build_model
from kelpseg.training.loss import segmentation_loss_components
from kelpseg.training.metrics import build_metrics
from kelpseg.training.scheduler import LinearWarmupCosineDecayLR
from kelpseg.training.visuals import EpochImages


def parameter_groups(model):
    """Exclude biases and normalization parameters from AdamW decay."""
    norm_types = (
        nn.BatchNorm1d,
        nn.BatchNorm2d,
        nn.BatchNorm3d,
        nn.SyncBatchNorm,
        nn.LayerNorm,
        nn.GroupNorm,
        nn.InstanceNorm1d,
        nn.InstanceNorm2d,
        nn.InstanceNorm3d,
    )
    no_decay = set()
    for module in model.modules():
        if isinstance(module, norm_types):
            no_decay.update(id(parameter) for parameter in module.parameters())
        if getattr(module, "bias", None) is not None:
            no_decay.add(id(module.bias))
    return [
        {
            "params": [
                p
                for p in model.parameters()
                if p.requires_grad and id(p) not in no_decay
            ]
        },
        {
            "params": [
                p for p in model.parameters() if p.requires_grad and id(p) in no_decay
            ],
            "weight_decay": 0.0,
        },
    ]


class TrainingModule(pl.LightningModule):
    """Automatic optimization; fixed threshold and validation-only selection."""

    def __init__(self, settings, model=None):
        super().__init__()
        self.settings = settings
        self.model = (
            model
            if model is not None
            else build_model(
                len(settings.band_names), encoder_weights=settings.encoder_weights
            )
        )
        metrics = build_metrics(include_confusion=False)
        self.train_metrics = metrics.clone(prefix="train/")
        self.val_metrics = metrics.clone(prefix="val/")
        # Metric objects let Lightning own epoch computation/reset. Float64
        # preserves pixel-weighted sums over the full validation collection.
        self.train_loss = MeanMetric().set_dtype(torch.float64)
        self.val_loss = MeanMetric().set_dtype(torch.float64)
        self.train_bce = MeanMetric().set_dtype(torch.float64)
        self.val_bce = MeanMetric().set_dtype(torch.float64)
        self.train_lovasz = MeanMetric().set_dtype(torch.float64)
        self.val_lovasz = MeanMetric().set_dtype(torch.float64)
        self.val_pixels = SumMetric().set_dtype(torch.float64)
        self.region_metrics = nn.ModuleDict()
        self.region_pixels = nn.ModuleDict()
        self.epoch_images = None
        self.image_logger = None

    def configure_diagnostics(self, validation_rows):
        """Register only represented regions before Trainer moves metrics to device."""
        regions = sorted({row["region"] for row in validation_rows})
        self.region_metrics = nn.ModuleDict(
            {
                region: build_metrics(include_confusion=False).clone(
                    prefix=f"val_region_{region}/"
                )
                for region in regions
            }
        )
        self.region_pixels = nn.ModuleDict(
            {region: SumMetric().double() for region in regions}
        )
        self.epoch_images = EpochImages(validation_rows, self.settings.band_names)

    def on_fit_start(self):
        self.image_logger = next(
            (logger for logger in self.loggers if isinstance(logger, WandbLogger)), None
        )

    def on_train_epoch_end(self):
        if self.image_logger is not None and self.epoch_images is not None:
            self.epoch_images.log(self.image_logger, "train", self.global_step)

    def forward(self, images):
        return self.model(images)

    def training_step(self, batch, batch_idx):
        loss = self._shared_step(batch, "train")
        self.log("train/loss_step", loss, on_step=True, on_epoch=False)
        return loss

    def validation_step(self, batch, batch_idx):
        return self._shared_step(batch, "val")

    def _shared_step(self, batch, phase):
        logits = self(batch["image"])
        targets = batch["target"]
        # Mixed precision applies to the model only; BCE/Lovasz stay float32.
        with torch.autocast(device_type=logits.device.type, enabled=False):
            bce, lovasz = segmentation_loss_components(logits.float(), targets)
            loss = 0.7 * bce + 0.3 * lovasz
        support = (targets != -100).sum()
        for name, value in (("loss", loss), ("bce", bce), ("lovasz", lovasz)):
            metric = getattr(self, f"{phase}_{name}")
            metric.update(value.detach().double(), weight=support.double())
            self.log(f"{phase}/{name}", metric, on_step=False, on_epoch=True)
            if phase == "train" and name != "loss":
                self.log(
                    f"train/{name}_step", value.detach(), on_step=True, on_epoch=False
                )
        metrics = getattr(self, f"{phase}_metrics")
        predictions = (logits[:, 0] >= 0).long()
        metrics.update(predictions, targets)
        if phase == "train":
            batch_iou = binary_jaccard_index(
                predictions, targets, ignore_index=-100, zero_division=0
            )
            self.log("train/iou_step", batch_iou, on_step=True, on_epoch=False)
        self.log_dict(metrics, on_step=False, on_epoch=True)
        if (
            self.image_logger is not None
            and self.epoch_images is not None
            and not self.trainer.sanity_checking
        ):
            self.epoch_images.collect(batch, predictions, phase, self.current_epoch)
        if phase == "val" and self.region_metrics:
            regions = [row["region"] for row in batch["metadata"]]
            for region in sorted(set(regions)):
                indices = [i for i, value in enumerate(regions) if value == region]
                regional = self.region_metrics[region]
                regional.update(predictions[indices], targets[indices])
                self.log_dict(regional, on_step=False, on_epoch=True)
                pixels = self.region_pixels[region]
                pixels.update((targets[indices] != -100).sum().double())
                self.log(
                    f"val_region_{region}/pixels", pixels, on_step=False, on_epoch=True
                )
        if phase == "val":
            self.val_pixels.update(support.double())
            self.log("val/pixels", self.val_pixels, on_step=False, on_epoch=True)
        return loss

    def on_validation_epoch_end(self):
        if self.val_pixels.compute() == 0:
            raise ValueError("Validation has no scored pixels; cannot select a model.")
        self.log("trainer/optimizer_updates", float(self.global_step))
        if self.image_logger is not None and self.epoch_images is not None:
            self.epoch_images.log(self.image_logger, "val", self.global_step)

    def configure_optimizers(self):
        settings = self.settings
        optimizer = torch.optim.AdamW(
            parameter_groups(self.model),
            lr=settings.learning_rate,
            betas=tuple(settings.betas),
            weight_decay=settings.weight_decay,
        )
        total_steps = int(self.trainer.estimated_stepping_batches)
        steps_per_epoch = total_steps // settings.epochs
        scheduler = LinearWarmupCosineDecayLR(
            optimizer,
            total_steps,
            settings.warmup_epochs * steps_per_epoch,
            settings.min_lr,
        )
        return {
            "optimizer": optimizer,
            "lr_scheduler": {"scheduler": scheduler, "interval": "step"},
        }
