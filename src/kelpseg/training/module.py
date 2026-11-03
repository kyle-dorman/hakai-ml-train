"""Single-model Lightning training with pooled validation agreement."""

import lightning.pytorch as pl
import torch
from torch import nn
from torchmetrics import MeanMetric, SumMetric

from kelpseg.models import build_model
from kelpseg.training.loss import segmentation_loss
from kelpseg.training.metrics import build_metrics
from kelpseg.training.scheduler import LinearWarmupCosineDecayLR


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
        self.train_metrics = metrics.clone(prefix="train_")
        self.val_metrics = metrics.clone(prefix="val_")
        # Metric objects let Lightning own epoch computation/reset. Float64
        # preserves pixel-weighted sums over the full validation collection.
        self.train_loss = MeanMetric().set_dtype(torch.float64)
        self.val_loss = MeanMetric().set_dtype(torch.float64)
        self.val_pixels = SumMetric().set_dtype(torch.float64)

    def forward(self, images):
        return self.model(images)

    def training_step(self, batch, batch_idx):
        loss = self._shared_step(batch, "train")
        self.log("train_loss_step", loss, on_step=True, on_epoch=False)
        return loss

    def validation_step(self, batch, batch_idx):
        return self._shared_step(batch, "val")

    def _shared_step(self, batch, phase):
        logits = self(batch["image"])
        targets = batch["target"]
        # Mixed precision applies to the model only; BCE/Lovasz stay float32.
        with torch.autocast(device_type=logits.device.type, enabled=False):
            loss = segmentation_loss(logits.float(), targets)
        support = (targets != -100).sum()
        loss_metric = getattr(self, f"{phase}_loss")
        loss_metric.update(loss.detach().double(), weight=support.double())
        self.log(f"{phase}_loss", loss_metric, on_step=False, on_epoch=True)
        metrics = getattr(self, f"{phase}_metrics")
        metrics.update((logits[:, 0] >= 0).long(), targets)
        self.log_dict(metrics, on_step=False, on_epoch=True)
        if phase == "val":
            self.val_pixels.update(support.double())
            self.log("val_pixels", self.val_pixels, on_step=False, on_epoch=True)
        return loss

    def on_validation_epoch_end(self):
        if self.val_pixels.compute() == 0:
            raise ValueError("Validation has no scored pixels; cannot select a model.")
        self.log("optimizer_updates", float(self.global_step))

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
