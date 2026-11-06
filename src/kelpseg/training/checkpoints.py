"""Retain explicitly requested completed epochs alongside native best/last files."""

from pathlib import Path

from lightning.pytorch import LightningModule, Trainer
from lightning.pytorch.callbacks import Callback


class EpochCheckpoints(Callback):
    """Save selected one-based epochs using Lightning's full checkpoint lifecycle."""

    def __init__(self, directory: Path, epochs: tuple[int, ...]) -> None:
        """Store the output directory and validated one-based epochs; write nothing."""
        self.directory = directory
        self.epochs = epochs

    def on_train_epoch_end(self, trainer: Trainer, pl_module: LightningModule) -> None:
        """Save a requested completed epoch, including EMA and optimizer state.

        Trainer supplies the zero-based epoch. Run after TrainingResume marks
        the epoch complete; native save hooks preserve the validation EMA weights
        and separate current model state. No new validation metrics are computed.
        """
        epoch = trainer.current_epoch + 1
        if epoch in self.epochs:
            trainer.save_checkpoint(self.directory / f"epoch-{epoch:02d}.ckpt")
