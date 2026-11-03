"""Historical linear warmup/cosine policy, indexed by optimizer updates."""

import math

from torch.optim.lr_scheduler import LRScheduler


class LinearWarmupCosineDecayLR(LRScheduler):
    """Initialize at zero; reach peak at warmup_steps and floor at total_steps.

    Lightning steps this after each optimizer update, including the final
    partial accumulation. Thus the first update uses zero LR, and the floor
    is the LR recorded after the final update, exactly as in the old scheduler.
    """

    def __init__(self, optimizer, total_steps, warmup_steps, min_lr):
        self.total_steps = total_steps
        self.warmup_steps = warmup_steps
        self.min_lr = min_lr
        super().__init__(optimizer)

    def get_lr(self):
        step = self.last_epoch
        if step < self.warmup_steps:
            scale = step / max(1, self.warmup_steps)
            return [lr * scale for lr in self.base_lrs]
        progress = min(
            (step - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps),
            1.0,
        )
        scale = 0.5 * (1 + math.cos(math.pi * progress))
        return [self.min_lr + (lr - self.min_lr) * scale for lr in self.base_lrs]
