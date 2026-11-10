"""Embed aligned shoreline windows in a fresh copy of canonical chips."""

import csv
import json
import logging
import shutil
from collections import defaultdict
from collections.abc import Iterator, KeysView
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from kelpseg.reporting.shore_distance import load_shore_sources
from kelpseg.training.loss_settings import DISTANCE_CAP_M

logger = logging.getLogger(__name__)


def _source_grid(source: dict, shore: dict) -> tuple[rasterio.Affine, rasterio.crs.CRS]:
    """Verify the shoreline row describes the same crop and return its grid."""
    key = source["source_key"]
    for chip_field, shore_field in (
        ("source_id", "original_source_id"),
        ("dataset_id", "dataset_id"),
        ("release_id", "release_id"),
        ("region", "region_id"),
        ("acquisition_date", "acquisition_date"),
        ("row_offset", "row_offset"),
        ("col_offset", "col_offset"),
        ("width", "width"),
        ("height", "height"),
    ):
        chip_value = source[chip_field]
        if str(chip_value if chip_value is not None else "") != shore[shore_field]:
            raise ValueError(
                f"{key}: shoreline and chip source disagree on {chip_field}."
            )
    if float(shore["cap_m"]) < DISTANCE_CAP_M:
        raise ValueError(f"{key}: shoreline cap must be at least {DISTANCE_CAP_M:g} m.")
    transform = rasterio.Affine(*source["transform"])
    crs = rasterio.crs.CRS.from_user_input(source["crs"])
    shore_crs = rasterio.crs.CRS.from_user_input(shore["crs"])
    shore_transform = rasterio.Affine(*json.loads(shore["transform"])[:6])
    if shore_crs != crs or not transform.almost_equals(shore_transform, precision=1e-6):
        raise ValueError(
            f"{key}: shoreline manifest grid differs from the chip source."
        )
    return transform, crs


def _copy_source(
    chips: Path,
    shoreline: Path,
    work: Path,
    source: dict,
    shore: dict,
    rows: list[dict],
) -> tuple[int, int, int]:
    """Write one source's retained chips and return count, bytes and unknown kelp."""
    key = source["source_key"]
    transform, crs = _source_grid(source, shore)
    source_shape = source["height"], source["width"]
    row_offset, col_offset = source["row_offset"], source["col_offset"]
    count = size = unknown = 0
    with (
        rasterio.Env(GDAL_PAM_ENABLED="NO"),
        rasterio.open(shoreline / shore["distance"]) as distance_grid,
        rasterio.open(shoreline / shore["land_mask"]) as land_grid,
    ):
        for grid, dtype in ((distance_grid, "float32"), (land_grid, "uint8")):
            if (
                grid.dtypes != (dtype,)
                or grid.crs != crs
                or not grid.transform.almost_equals(transform, precision=1e-6)
                or grid.shape != source_shape
            ):
                raise ValueError(
                    f"{key}: {grid.name} does not match the chip source grid."
                )
        for row in rows:
            top = int(row["original_row"]) - row_offset
            left = int(row["original_col"]) - col_offset
            height, width = int(row["height"]), int(row["width"])
            if (
                top != int(row["row"])
                or left != int(row["col"])
                or min(top, left) < 0
                or min(height, width) < 1
                or top + height > source_shape[0]
                or left + width > source_shape[1]
            ):
                raise ValueError(
                    f"{key}: inconsistent source offsets for {row['payload']}."
                )
            window = Window(left, top, width, height)
            distance = distance_grid.read(1, window=window, masked=True).filled(np.nan)
            distance[~np.isfinite(distance) | (distance < 0)] = np.nan
            np.minimum(distance, DISTANCE_CAP_M, out=distance)
            land = land_grid.read(1, window=window, masked=True).filled(255)
            if not np.isin(land, (0, 1, 255)).all():
                raise ValueError(
                    f"{key}: expected land categories 0, 1 or unknown 255."
                )
            relative = Path(row["payload"])
            with np.load(chips / relative, allow_pickle=False) as arrays:
                image, label = arrays["image"], arrays.get("label")
            if (
                label is None
                or label.shape != (height, width)
                or image.shape[:2] != label.shape
            ):
                raise ValueError(
                    f"{relative}: expected aligned labeled chip matching its window."
                )
            unknown += int(((label == 1) & (land != 1) & np.isnan(distance)).sum())
            destination = work / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                destination,
                image=image,
                label=label,
                distance_m=distance,
                land=land,
            )
            count += 1
            size += destination.stat().st_size
            if count % 100 == 0:
                logger.info("%s: %d chips, %d bytes", key, count, size)
    return count, size, unknown


def _read_windows(
    manifest: Path, source_keys: KeysView[str]
) -> tuple[dict[str, list[dict]], int]:
    """Check window identities and group retained rows by source for sequential reads."""
    by_source = defaultdict(list)
    windows, payloads = set(), set()
    with manifest.open(newline="") as stream:
        for row in csv.DictReader(stream):
            key, payload = row["source_key"], row["payload"]
            identity = key, int(row["row"]), int(row["col"])
            if key not in source_keys or identity in windows:
                raise ValueError(
                    f"Unknown source or duplicate chip window: {identity}."
                )
            windows.add(identity)
            if (row["disposition"] == "retained") != bool(payload):
                raise ValueError(
                    f"{identity}: retained chips need payloads and omitted chips must have none."
                )
            if payload:
                relative = Path(payload)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or relative.suffix != ".npz"
                    or relative.parts[0] != "chips"
                ):
                    raise ValueError(
                        f"{identity}: expected a relative NPZ path under chips/."
                    )
                if relative in payloads:
                    raise ValueError(f"{identity}: duplicate chip payload {relative}.")
                payloads.add(relative)
                by_source[key].append(row)
    if not payloads:
        raise ValueError("The chip manifest contains no retained payloads.")
    return by_source, len(payloads)


def _copy_sources(
    chips: Path,
    shoreline: Path,
    work: Path,
    sources: dict[str, dict],
    shores: dict[str, dict],
    windows: dict[str, list[dict]],
    workers: int,
) -> Iterator[tuple[str, tuple[int, int, int]]]:
    """Yield completed source totals, with each process owning its raster handles."""
    if workers == 1:
        for key, rows in windows.items():
            logger.info("Copying %s (%d chips)", key, len(rows))
            yield (
                key,
                _copy_source(chips, shoreline, work, sources[key], shores[key], rows),
            )
        return
    pool = ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn"))
    try:
        jobs = {}
        for key, rows in windows.items():
            job = pool.submit(
                _copy_source, chips, shoreline, work, sources[key], shores[key], rows
            )
            jobs[job] = key
        for job in as_completed(jobs):
            yield jobs[job], job.result()
    finally:
        pool.shutdown(cancel_futures=True)


def prepare_chip_distances(
    chips: Path, shoreline: Path, output: Path, *, workers: int = 1
) -> Path:
    """Copy manifests and embed distance/land arrays once, then publish atomically."""
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be a positive integer.")
    chips, shoreline, output = (
        path.expanduser().resolve() for path in (chips, shoreline, output)
    )
    if output.is_relative_to(chips) or output.is_relative_to(shoreline):
        raise ValueError(
            "Choose an output outside the canonical chips and shoreline directories."
        )
    work = output.with_name(f".{output.name}.incomplete")
    if output.exists() or work.exists():
        raise ValueError(
            f"Output or incomplete directory exists. Choose a fresh output: {output}"
        )
    sources = {}
    for source in json.loads((chips / "sources.json").read_text()):
        key = source["source_key"]
        if not key or key in sources:
            raise ValueError(f"Missing or duplicate chip source key: {key!r}.")
        sources[key] = source
    shores = load_shore_sources(shoreline)
    by_source, total = _read_windows(chips / "windows.csv", sources.keys())
    missing = sources.keys() - shores.keys()
    if missing:
        raise ValueError(f"Missing shoreline sources: {', '.join(sorted(missing))}.")
    summary = json.loads((chips / "summary.json").read_text())
    workers = min(workers, len(by_source))
    logger.info(
        "Deriving %d chips from %d sources with %d workers into %s",
        total,
        len(by_source),
        workers,
        output,
    )
    work.mkdir(parents=True)
    count = size = unknown = 0
    results = _copy_sources(chips, shoreline, work, sources, shores, by_source, workers)
    for index, (key, (copied, written, kelp)) in enumerate(results, 1):
        count += copied
        size += written
        unknown += kelp
        logger.info(
            "Finished %d/%d: %s (%d chips); total %d/%d chips, %d payload bytes",
            index,
            len(by_source),
            key,
            copied,
            count,
            total,
            size,
        )
    for filename in ("recipe.json", "sources.json", "windows.csv"):
        shutil.copyfile(chips / filename, work / filename)
    summary.update(
        payload_bytes=size,
        shoreline=str(shoreline),
        parent_chips=str(chips),
        distance_cap_m=DISTANCE_CAP_M,
        unknown_distance_positive_window_pixels=unknown,
    )
    (work / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    work.rename(output)
    logger.info("Complete: %s; %d chips; %d payload bytes", output, count, size)
    return output
