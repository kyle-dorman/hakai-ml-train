"""Prepare standalone land/distance GeoTIFFs from explicit image identities."""

from __future__ import annotations

import csv
import json
import logging
import math
import re
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import numpy as np
import rasterio
from shapely.ops import unary_union

from kelpseg.paths import _resolve_path
from kelpseg.prediction.settings import IDENTITY_COLUMNS
from kelpseg.prepare.shore_distance import (
    geographic_halo,
    land_distance,
    metric_grid,
    read_land,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShorelineSettings:
    """Explicit source/vector paths and simple settings for one fresh preparation."""

    manifest: Path
    image_root: Path
    output: Path
    mainlands: Path
    big_islands: Path
    small_islands: Path
    max_distance_m: float = 500.0
    max_examples: int = 12
    coverage: str = "complete"

    def __post_init__(self) -> None:
        """Reject unsupported settings before opening or writing source arrays."""
        if (
            type(self.max_distance_m) not in (float, int)
            or not math.isfinite(self.max_distance_m)
            or self.max_distance_m <= 0
        ):
            raise ValueError("max_distance_m must be a positive finite number.")
        if type(self.max_examples) is not int or self.max_examples < 0:
            raise ValueError("max_examples must be a nonnegative integer.")
        if self.coverage != "complete":
            raise ValueError(
                "coverage must be complete: supply global shoreline layers or complete source halos."
            )


def load_settings(recipe: str | Path) -> ShorelineSettings:
    """Read a flat TOML recipe and resolve paths relative to its directory."""
    recipe = Path(recipe).expanduser().resolve()
    values = tomllib.loads(recipe.read_text())
    unknown = values.keys() - {f.name for f in fields(ShorelineSettings)}
    if unknown:
        raise ValueError(f"Unknown shoreline settings: {', '.join(sorted(unknown))}.")
    for name in (
        "manifest",
        "image_root",
        "output",
        "mainlands",
        "big_islands",
        "small_islands",
    ):
        if not isinstance(values.get(name), str) or not values[name].strip():
            raise ValueError(f"{name} must be a nonempty path.")
        values[name] = _resolve_path(values[name], base=recipe.parent, context=name)
    return ShorelineSettings(**values)


def read_sources(settings: ShorelineSettings) -> list[dict]:
    """Read image headers; preserve declared paths and resolve separate read paths.

    Relative image paths remain portable with image_root. Explicit absolute
    image paths stay absolute; no label content is read.
    """
    with settings.manifest.open(newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        allowed = {"source_key", "image", "band_names", *IDENTITY_COLUMNS}
        if (
            len(columns) != len(set(columns))
            or not {"source_key", "image"}.issubset(columns)
            or set(columns) - allowed
        ):
            raise ValueError(
                "Shoreline source CSV needs unique source_key/image columns and optional prediction identity columns."
            )
        rows = list(reader)
    if not rows:
        raise ValueError("Shoreline source CSV has no image rows.")
    seen, images, sources = set(), set(), []
    for row in rows:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("Shoreline source CSV has an incomplete row.")
        key = row["source_key"]
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", key)
            or key.casefold() in seen
        ):
            raise ValueError(f"Invalid or duplicate source_key: {key!r}.")
        if not row["image"].strip():
            raise ValueError(f"{key}: image path is missing.")
        image = _resolve_path(row["image"], base=settings.image_root, context=key)
        if image in images:
            raise ValueError(f"Duplicate image path: {image}.")
        with rasterio.open(image) as dataset:
            if dataset.crs is None:
                raise ValueError(f"{image}: a projected metre CRS is required.")
            metric_grid(dataset.crs, dataset.transform)
            grid = dict(
                width=dataset.width,
                height=dataset.height,
                affine=dataset.transform,
                crs=dataset.crs,
            )
        metadata = {
            name: row.get(name, "")
            for name in ("source_key", "band_names", *IDENTITY_COLUMNS)
        }
        metadata["image"] = row["image"]
        sources.append(dict(metadata=metadata, grid=grid, image_path=image))
        seen.add(key.casefold())
        images.add(image)
    return sources


def write_raster(path: Path, array: np.ndarray, grid: dict, nodata: float) -> None:
    """Write one compressed exact-grid raster; input geometry arrays are unchanged."""
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=grid["width"],
        height=grid["height"],
        count=1,
        dtype=array.dtype,
        crs=grid["crs"],
        transform=grid["affine"],
        nodata=nodata,
        compress="deflate",
        tiled=True,
        BIGTIFF="IF_SAFER",
    ) as dataset:
        dataset.write(array, 1)


def prepare_shoreline(settings: ShorelineSettings) -> Path:
    """Write source masks, capped distances, provenance and bounded previews once.

    Read source grids and complete shoreline layers, then process sequentially.
    Existing output directories are refused. Failures stop immediately; final
    manifests appear only when every source has completed successfully.
    """
    if settings.output.exists():
        raise ValueError(
            f"Output already exists: {settings.output}. Choose a fresh directory."
        )
    sources = read_sources(settings)
    footprints = [
        geographic_halo(**source["grid"], cap_m=settings.max_distance_m)
        for source in sources
    ]
    logger.info(
        "Preparing shoreline for %d source TIFFs; output %s",
        len(sources),
        settings.output,
    )
    land, vector_info = read_land(
        (settings.mainlands, settings.big_islands, settings.small_islands),
        unary_union(footprints),
    )
    output = settings.output
    output.mkdir(parents=True)
    for folder in ("land", "distance", "examples"):
        (output / folder).mkdir()
    results, regions = [], set()
    for index, source in enumerate(sources, 1):
        row, grid = source["metadata"], source["grid"]
        key = row["source_key"]
        logger.info(
            "Shoreline %d/%d: %s (%d x %d)",
            index,
            len(sources),
            key,
            grid["width"],
            grid["height"],
        )
        mask, distance = land_distance(land, **grid, cap_m=settings.max_distance_m)
        land_path, distance_path = f"land/{key}.tif", f"distance/{key}.tif"
        write_raster(output / land_path, mask, grid, 255)
        write_raster(output / distance_path, distance, grid, float("nan"))
        result = dict(
            row,
            land_mask=land_path,
            distance=distance_path,
            width=grid["width"],
            height=grid["height"],
            crs=str(grid["crs"]),
            transform=json.dumps(list(grid["affine"])[:6]),
            cap_m=settings.max_distance_m,
            coverage=settings.coverage,
            land_pixels=int(mask.sum()),
            ocean_pixels=int((mask == 0).sum()),
            unknown_pixels=0,
        )
        results.append(result)
        region = row["region_id"] or key
        if len(regions) < settings.max_examples and region not in regions:
            from kelpseg.prepare.shore_preview import write_preview

            write_preview(
                output / "examples" / f"{key}.png",
                dict(row, image=str(source["image_path"])),
                mask,
                distance,
                settings.max_distance_m,
            )
            regions.add(region)
    temporary = output / "sources.csv.tmp"
    with temporary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    temporary.replace(output / "sources.csv")
    metadata = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in asdict(settings).items()
    }
    metadata.update(
        vector_sources=vector_info,
        distance_convention="Native-grid pixel-center to nearest land-pixel-center Euclidean distance; cap is right-censored. Pixel-center land rasterization. Complete supplied shoreline coverage assumed.",
    )
    (output / "settings.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "summary.json").write_text(
        json.dumps(
            dict(status="complete", sources=len(results), examples=len(regions)),
            indent=2,
        )
        + "\n"
    )
    logger.info("Shoreline complete: %d sources", len(results))
    return output
