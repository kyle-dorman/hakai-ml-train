"""Read true-size NumPy chips and pad only while loading."""

from collections.abc import Sequence
from pathlib import Path

import numpy as np

from kelpseg.bands import resolve_band_indices
from kelpseg.prepare.nodata import nodata_mask


def load_chip(
    path: str | Path,
    source_band_names: Sequence[str],
    selection: str | Sequence[str] | Sequence[int] = "all",
    chip_size: int = 512,
) -> dict:
    """Load raw HWC uint16 imagery and optional mapped HW int8 targets.

    Padding is ``(top, bottom, left, right)`` with top/left always zero. Remove
    padding with ``array[:true_height, :true_width]`` before source placement.
    The returned nodata mask uses all native bands and is false over padding,
    so source nodata and artificial padding remain distinct. No normalization,
    resizing, target remapping, or augmentation occurs here. Targets are already
    mapped by the chipper; loading does not audit their category values again.
    """
    if type(chip_size) is not int or chip_size < 1:
        raise ValueError("chip_size must be a positive integer.")
    indices = resolve_band_indices(source_band_names, selection)
    with np.load(path, allow_pickle=False) as arrays:
        image = arrays["image"]
        label = arrays.get("label")

    if image.dtype != np.uint16 or image.ndim != 3:
        raise ValueError(f"{path}: image must be HWC uint16.")
    height, width, channels = image.shape
    if channels != len(source_band_names):
        raise ValueError(f"{path}: image channels disagree with source_band_names.")
    if not 1 <= height <= chip_size or not 1 <= width <= chip_size:
        raise ValueError(f"{path}: true chip dimensions must be in 1..{chip_size}.")
    invalid = nodata_mask(image, (0,) * channels, band_axis=-1)
    if label is not None and (label.dtype != np.int8 or label.shape != (height, width)):
        raise ValueError(f"{path}: label must be HW int8 matching the image.")

    bottom, right = chip_size - height, chip_size - width
    image = image[:, :, indices]
    if bottom or right:
        image = np.pad(image, ((0, bottom), (0, right), (0, 0)), constant_values=0)
        if label is not None:
            label = np.pad(label, ((0, bottom), (0, right)), constant_values=-100)
        invalid = np.pad(invalid, ((0, bottom), (0, right)), constant_values=False)
    return {
        "image": image,
        "label": label,
        "true_height": height,
        "true_width": width,
        "padding": (0, bottom, 0, right),
        "nodata_mask": invalid,
        "band_names": tuple(source_band_names[index] for index in indices),
    }
