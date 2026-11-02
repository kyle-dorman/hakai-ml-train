"""Shared raw-unit preprocessing for the capped with-BC baseline reference."""

from collections.abc import Sequence

import numpy as np

from kelpseg.bands import resolve_band_indices

BAND_NAMES = (
    "coastal_blue",
    "blue",
    "green_i",
    "green",
    "yellow",
    "red",
    "rededge",
    "nir",
)
CLIP_VALUE = 5000
MEAN = (
    323.64878219651854,
    389.5317689154827,
    438.39646268775465,
    465.35795980452735,
    459.9420472595575,
    451.3045100567385,
    536.2606342593172,
    799.2215816851071,
)
STD = (
    294.97881315006885,
    336.1495661091302,
    401.6870189255488,
    459.22170495895057,
    541.9194107884493,
    575.3320083210876,
    637.0868757507536,
    994.5695551762033,
)


def native_validity(
    image: np.ndarray,
    true_height: int | None = None,
    true_width: int | None = None,
) -> np.ndarray:
    """Detect all-native-band zero nodata *before* selection or augmentation.

    Optional true dimensions remove bottom/right loading padding. Keep this
    mask when a transform later makes a valid pixel or selected band zero.
    """
    if image.ndim != 3 or image.shape[-1] == 0:
        raise ValueError("Native image must be HWC with at least one band.")
    height = image.shape[0] if true_height is None else true_height
    width = image.shape[1] if true_width is None else true_width
    if (
        type(height) is not int
        or type(width) is not int
        or not 1 <= height <= image.shape[0]
        or not 1 <= width <= image.shape[1]
    ):
        raise ValueError("True dimensions must fit the image before padding.")
    valid = np.any(image != 0, axis=-1)
    valid[height:, :] = False
    valid[:, width:] = False
    return valid


def cap_raw(image: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    """Apply only the upper cap, preserving negatives and zero invalid fill."""
    if image.ndim != 3 or valid_mask.shape != image.shape[:2]:
        raise ValueError("Image must be HWC and validity must match its HW shape.")
    if valid_mask.dtype != np.bool_:
        raise ValueError("Validity must be a boolean mask.")
    capped = np.minimum(image, CLIP_VALUE).astype(np.float64)
    capped[~valid_mask] = 0
    return capped


def normalize(
    image: np.ndarray,
    band_names: Sequence[str],
    valid_mask: np.ndarray,
) -> np.ndarray:
    """Upper-cap raw values, then standardize by named fixed reference bands.

    Invalid/padding pixels remain normalized zero. Callers preserve the mask;
    they must never redetect nodata from augmented or selected-band values.
    The result is HWC float32; no per-image normalization or lower cap occurs.
    """
    indices = resolve_band_indices(BAND_NAMES, tuple(band_names))
    if image.ndim != 3 or image.shape[-1] != len(indices):
        raise ValueError("Image channels must match the ordered band names.")
    result = cap_raw(image, valid_mask)
    result = (result - np.asarray(MEAN)[list(indices)]) / np.asarray(STD)[list(indices)]
    result[~valid_mask] = 0
    return result.astype(np.float32)
