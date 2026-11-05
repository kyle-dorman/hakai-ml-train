"""Simple sliding windows with inward-shifted final rows and columns."""

from collections.abc import Iterator

from rasterio.windows import Window


def axis_starts(length: int, size: int, stride: int) -> list[int]:
    """Return unique starts covering an axis, ending with a full window if possible."""
    if length < 1 or size < 1 or not 1 <= stride <= size:
        raise ValueError("Positive length/size and stride in 1..size are required.")
    last = max(length - size, 0)
    starts = list(range(0, last + 1, stride))
    if starts[-1] != last:
        starts.append(last)
    return starts


def prediction_windows(
    width: int, height: int, size: int, stride: int
) -> Iterator[Window]:
    """Yield true source windows in row order; padding is left to the predictor."""
    for row in axis_starts(height, size, stride):
        for col in axis_starts(width, size, stride):
            yield Window(col, row, min(size, width - col), min(size, height - row))
