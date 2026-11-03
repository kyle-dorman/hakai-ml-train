"""Small guards around Lightning's native weight averaging lifecycle."""

from lightning.pytorch.callbacks import WeightAveraging
from torch.optim.swa_utils import get_ema_avg_fn


class DelayedEMA(WeightAveraging):
    """First copy after update 101, then EMA with decay 0.999.

    Native WeightAveraging otherwise swaps its initial snapshot into early
    validation. Guard both validation hooks and checkpoint selection until the
    first average exists. Checkpoints retain current_model_state separately
    from the validation-selected state_dict and averaging_state.
    """

    def __init__(self):
        super().__init__(avg_fn=get_ema_avg_fn(decay=0.999))

    @property
    def has_average(self):
        return self._average_model is not None and bool(
            self._average_model.n_averaged > 0
        )

    def should_update(self, step_idx=None, epoch_idx=None):
        return step_idx is not None and step_idx >= 100

    def on_validation_epoch_start(self, trainer, pl_module):
        if self.has_average:
            super().on_validation_epoch_start(trainer, pl_module)

    def on_validation_epoch_end(self, trainer, pl_module):
        if self.has_average:
            super().on_validation_epoch_end(trainer, pl_module)

    def on_train_end(self, trainer, pl_module):
        # Leave ordinary weights intact; the selected checkpoint already holds
        # validation weights. This also avoids copying the initial snapshot.
        pass

    def on_save_checkpoint(self, trainer, pl_module, checkpoint):
        if self.has_average:
            super().on_save_checkpoint(trainer, pl_module, checkpoint)
        else:
            checkpoint["current_model_state"] = checkpoint["state_dict"]
            checkpoint["averaging_state"] = {"n_averaged": 0}
