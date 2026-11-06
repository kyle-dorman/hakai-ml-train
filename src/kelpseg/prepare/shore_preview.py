"""Small label-independent alignment previews for prepared shoreline rasters."""

from pathlib import Path

import numpy as np
import rasterio
from matplotlib import colormaps
from matplotlib.figure import Figure

from kelpseg.visualization import log_stretch


def write_preview(
    path: Path, source: dict, land: np.ndarray, distance: np.ndarray, cap_m: float
) -> None:
    """Save log imagery/shoreline and distance panels at bounded display size.

    Source masks and nonfinite values are excluded from the display stretch.
    Land/distance data and image values are never modified.
    """
    step = max(1, int(np.ceil(max(land.shape) / 1000)))
    small_land, small_distance = land[::step, ::step], distance[::step, ::step]
    names = source["band_names"].split(";")
    bands = ("nir", "red", "green") if "nir" in names else ("red", "green", "blue")
    with rasterio.open(source["image"]) as dataset:
        indices = (
            [names.index(name) + 1 for name in bands]
            if all(name in names for name in bands)
            else [1, 1, 1]
        )
        image = dataset.read(indices, masked=True)[:, ::step, ::step].transpose(1, 2, 0)
    valid = ~np.ma.getmaskarray(image).any(axis=-1)
    valid &= np.isfinite(image.data).all(axis=-1)
    figure = Figure(figsize=(12, 5), layout="constrained")
    axes = figure.subplots(1, 2)
    axes[0].imshow(log_stretch(image.data, valid))
    if small_land.min() != small_land.max():
        axes[0].contour(small_land, levels=[0.5], colors=["yellow"], linewidths=0.6)
    axes[0].set_title("Log imagery with mapped land boundary (yellow)")
    colors = colormaps["viridis"].copy()
    colors.set_bad("lightgray")
    view = axes[1].imshow(
        np.ma.masked_where(small_land == 1, small_distance),
        vmin=0,
        vmax=cap_m,
        cmap=colors,
    )
    axes[1].set_facecolor("lightgray")
    axes[1].set_title(f"Distance to land; gray = land; {cap_m:g} m = cap")
    figure.colorbar(view, ax=axes[1], label="metres")
    for axis in axes:
        axis.set_axis_off()
    figure.suptitle(source["source_key"])
    figure.savefig(path, dpi=130)
