"""Small ordinary directory fixtures independent of CA/BC metadata catalogs."""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from kelpseg.prepare.clean_inputs import CleanRecipe, build_clean_plan


def write_tiff(path, values, *, nodata=None, transform=None, crs="EPSG:32611"):
    path.parent.mkdir(parents=True, exist_ok=True)
    if values.ndim == 2:
        values = values[None]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=values.shape[2],
        height=values.shape[1],
        count=values.shape[0],
        dtype=values.dtype,
        nodata=nodata,
        crs=crs,
        transform=transform or from_origin(0, 4, 1, 1),
    ) as output:
        output.write(values)


def sample(root: Path, *, paired=True, qa=False, block_size=2, count=3):
    images, labels = root / "images", root / "labels"
    values = np.full((count, 4, 5), 9, dtype=np.uint16)
    values[:, 0, 0] = 65535
    values[0, 0, 1] = 65535
    write_tiff(images / "cove" / "spring.TIF", values, nodata=65535)
    categories = np.array([[0, 1, 0], [2, 3, 4], [0, 0, 1], [1, 0, 0]], dtype=np.uint8)
    if paired:
        write_tiff(
            labels / "cove" / "spring.tiff",
            categories,
            nodata=0,
            transform=from_origin(1, 4, 1, 1),
        )
    recipe = CleanRecipe(image_band_counts=(count,), qa_masks=qa, block_size=block_size)
    return (
        build_clean_plan(images, labels if paired else None, root / "derived", recipe),
        values,
        categories,
    )
