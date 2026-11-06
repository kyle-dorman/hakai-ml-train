"""Display-only transformations for native imagery; model inputs stay unchanged."""

import numpy as np
from numpy.typing import NDArray


def log_stretch(image: NDArray, valid: NDArray[np.bool_]) -> NDArray[np.float32]:
    """Return log1p imagery with a per-channel 2–98% stretch and gray invalid pixels.

    Inputs are native HWC values and an aligned HW validity mask. Negative values
    are clipped to zero for display; the caller's imagery is never modified.
    """
    color = np.log1p(np.maximum(image.astype(np.float32), 0))
    if valid.any():
        low, high = np.percentile(color[valid], [2, 98], axis=0)
        color = np.clip((color - low) / np.maximum(high - low, 1e-6), 0, 1)
    color[~valid] = 0.3
    return color.astype(np.float32)
