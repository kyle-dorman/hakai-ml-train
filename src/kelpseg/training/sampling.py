"""Match a training draw budget while visiting the full eligible pool."""

from collections.abc import Iterator

import torch
from torch.utils.data import Sampler


class RepeatEpochSampler(Sampler[int]):
    """Visit the whole pool, then add a subset from one shuffled repeat."""

    def __init__(self, pool_size: int, draws: int, seed: int) -> None:
        """Set the eligible pool size, total draws per epoch and recipe seed."""
        if not 0 < pool_size <= draws <= 2 * pool_size:
            raise ValueError(
                f"train_draws_per_epoch must be between {pool_size} and {2 * pool_size} "
                f"for one full pool plus one repeat; got {draws}."
            )
        self.pool_size = pool_size
        self.draws = draws
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        """Use Lightning's zero-based epoch, including after checkpoint resume."""
        self.epoch = epoch

    def __len__(self) -> int:
        """Return the number of samples the loader will draw this epoch."""
        return self.draws

    def __iter__(self) -> Iterator[int]:
        """Select distinct extras and shuffle the combined draw positions."""
        generator = torch.Generator().manual_seed((self.seed + self.epoch) % 2**64)
        extra_count = self.draws - self.pool_size
        repeat = torch.randperm(self.pool_size, generator=generator)
        indices = torch.cat((torch.arange(self.pool_size), repeat[:extra_count]))
        order = torch.randperm(self.draws, generator=generator)
        return iter(indices[order].tolist())
