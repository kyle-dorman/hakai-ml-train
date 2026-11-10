"""Training draw counts and seeded order for the no-BC comparison."""

from collections import Counter

import pytest

from kelpseg.training.sampling import RepeatEpochSampler


def test_matched_no_bc_draw_budget() -> None:
    """Draw all 7,280 indices, repeating exactly 1,238 distinct indices."""
    sampler = RepeatEpochSampler(7280, 8518, 42)
    first = list(sampler)
    counts = Counter(first)
    assert len(sampler) == len(first) == 8518
    assert set(counts) == set(range(7280))
    assert Counter(counts.values()) == {1: 6042, 2: 1238}
    assert first == list(RepeatEpochSampler(7280, 8518, 42))
    sampler.set_epoch(1)
    second = list(sampler)
    assert second != first
    assert Counter(Counter(second).values()) == {1: 6042, 2: 1238}


@pytest.mark.parametrize("draws", [4, 11])
def test_repeat_budget_must_cover_full_pool_at_most_twice(draws: int) -> None:
    """Reject draw counts outside the supported single-repeat policy."""
    with pytest.raises(ValueError, match="between 5 and 10"):
        RepeatEpochSampler(5, draws, 42)
