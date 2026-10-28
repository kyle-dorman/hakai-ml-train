"""Select ordered channels from one native-band chip collection."""

from collections.abc import Sequence

import numpy as np


def resolve_band_indices(
    source_band_names: Sequence[str],
    selection: str | Sequence[str] | Sequence[int] = "all",
) -> tuple[int, ...]:
    """Return zero-based indices; explicit integer selections are one-based.

    ``all`` keeps native order. ``rgbnir`` selects red/green/blue/nir, and
    ``rgb`` selects red/green/blue. Explicit names or indices preserve their
    requested order. No physical band order is guessed from channel count.
    """
    if isinstance(source_band_names, str) or not isinstance(
        source_band_names, (list, tuple)
    ):
        raise ValueError("source_band_names must be an ordered list of band names.")
    names = tuple(source_band_names)
    if not names or any(
        not isinstance(name, str) or not name.strip() for name in names
    ):
        raise ValueError("source_band_names must contain nonempty band names.")
    if len(names) != len(set(names)):
        raise ValueError("source_band_names must contain unique band names.")

    if isinstance(selection, str):
        if selection == "all":
            return tuple(range(len(names)))
        if selection == "rgbnir":
            selection = ("red", "green", "blue", "nir")
        elif selection == "rgb":
            selection = ("red", "green", "blue")
        else:
            raise ValueError(
                "Use selection='all', 'rgbnir', 'rgb', or an ordered list."
            )
    if not isinstance(selection, (list, tuple)) or not selection:
        raise ValueError("Band selection must be a nonempty ordered list.")

    indices = []
    for band in selection:
        if type(band) is int:
            if not 1 <= band <= len(names):
                raise ValueError(f"Band index {band} is outside 1..{len(names)}.")
            index = band - 1
        elif isinstance(band, str):
            if band not in names:
                raise ValueError(f"Unknown band {band!r}; available bands: {names}.")
            index = names.index(band)
        else:
            raise ValueError("Select bands by name or one-based integer index.")
        if index in indices:
            raise ValueError(f"Duplicate selected band: {names[index]}.")
        indices.append(index)
    return tuple(indices)


def select_bands(
    image: np.ndarray,
    source_band_names: Sequence[str],
    selection: str | Sequence[str] | Sequence[int] = "all",
) -> np.ndarray:
    """Select channels from an HWC image without changing values or dtype."""
    indices = resolve_band_indices(source_band_names, selection)
    if image.ndim != 3 or image.shape[-1] != len(source_band_names):
        raise ValueError(
            "Image must be HWC with one channel per source_band_names entry."
        )
    return image[:, :, indices]
