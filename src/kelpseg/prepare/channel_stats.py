"""Raw per-band statistics from true-size, explicitly selected training chips."""

import json
import logging
import math
import tempfile
import time
from pathlib import Path

import numpy as np

from kelpseg.bands import resolve_band_indices
from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.split_inputs import original_key
from kelpseg.prepare.splits import select_windows

logger = logging.getLogger(__name__)


def compute_channel_stats(
    chips: str | Path,
    assignments: str | Path,
    output: str | Path,
    *,
    experiment: str = "baseline",
    variant: str = "augmented",
    kelp_only: bool = False,
    clip_value: float | None = None,
) -> dict:
    """Stream native-valid raw pixels with float64 moments and sample std.

    Kelp-only selection includes all valid imagery in each manifest-positive
    training chip, not only labeled kelp pixels. Overlap counts as repeated
    chip exposure. Labels, loading-time padding, augmentation and normalization
    are never read or applied. ``payload_bytes_read`` sums selected NPZ file
    sizes for progress reporting, rather than measuring operating-system I/O.
    """
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise PreparationError(
            f"Output already exists; choose a fresh report: {output}"
        )
    if not output.parent.is_dir():
        raise PreparationError(f"Output parent must exist: {output.parent}")
    if type(kelp_only) is not bool:
        raise PreparationError("kelp_only must be true or false.")
    if clip_value is not None and (
        type(clip_value) not in (int, float)
        or not math.isfinite(clip_value)
        or clip_value <= 0
    ):
        raise PreparationError(
            "clip_value must be a finite positive raw value or None."
        )

    started = time.monotonic()
    chips = Path(chips).expanduser().resolve()
    assignments = Path(assignments).expanduser().resolve()
    logger.info("Reading declared bands: %s", chips / "recipe.json")
    try:
        names = json.loads((chips / "recipe.json").read_text(encoding="utf-8"))[
            "source_band_names"
        ]
    except KeyError as error:
        raise PreparationError(
            f"{chips / 'recipe.json'}: missing source_band_names declaration."
        ) from error
    resolve_band_indices(names, "all")
    logger.info("Selecting training windows for %s/%s", experiment, variant)
    windows = select_windows(chips, assignments, experiment=experiment, variant=variant)
    training = [row for row in windows if row["split"] == "train" and row["payload"]]
    selected = training
    if kelp_only:
        selected = []
        for row in training:
            try:
                kelp_pixels = int(row["kelp_pixels"])
            except (KeyError, TypeError, ValueError) as error:
                raise PreparationError(
                    f"{row['payload']}: kelp-only selection needs manifest kelp_pixels counts."
                ) from error
            if kelp_pixels > 0:
                selected.append(row)
    if not selected:
        raise PreparationError(
            "No selected training windows; check experiment, variant and kelp_only."
        )
    logger.info(
        "Computing raw channel statistics: %d/%d training windows, cap=%s, bands=%s",
        len(selected),
        len(training),
        clip_value,
        names,
    )

    pixels = payload_bytes = 0
    mean = np.zeros(len(names), dtype=np.float64)
    central_sum = np.zeros(len(names), dtype=np.float64)
    for index, row in enumerate(selected, start=1):
        payload = Path(row["payload"])
        # Access only the image member; labels may be absent and are irrelevant.
        with np.load(payload, allow_pickle=False) as archive:
            try:
                image = archive["image"]
            except KeyError as error:
                raise PreparationError(f"{payload}: missing image array.") from error
        expected = (int(row["height"]), int(row["width"]), len(names))
        if image.ndim != 3 or image.dtype != np.uint16 or image.shape != expected:
            raise PreparationError(
                f"{payload}: expected true-size HWC uint16 image {expected}; "
                f"found shape {image.shape}, dtype {image.dtype}."
            )
        payload_bytes += payload.stat().st_size
        # Native nodata is established before clipping. A zero in just one band
        # remains a valid observation in that band and every other channel.
        values = image[np.any(image != 0, axis=-1)].astype(np.float64)
        count = len(values)
        if count:
            if clip_value is not None:
                np.minimum(values, clip_value, out=values)
            chip_mean = values.mean(axis=0)
            values -= chip_mean
            chip_central_sum = np.sum(values * values, axis=0, dtype=np.float64)
            combined = pixels + count
            delta = chip_mean - mean
            # Chan's merge combines central moments without subtracting large
            # raw squared sums; memory holds only one chip's pixels at a time.
            central_sum += chip_central_sum + delta**2 * (pixels * count / combined)
            mean += delta * (count / combined)
            pixels = combined
        if index == 1 or index % 100 == 0 or index == len(selected):
            logger.info(
                "Statistics %d/%d: %s; %d valid pixel exposures; %d payload bytes",
                index,
                len(selected),
                payload,
                pixels,
                payload_bytes,
            )

    if pixels < 2:
        raise PreparationError(
            f"Sample standard deviation needs at least two valid pixels; found {pixels}."
        )
    std = np.sqrt(central_sum / (pixels - 1))
    zero_variance = [name for name, value in zip(names, std, strict=True) if value == 0]
    if zero_variance:
        raise PreparationError(
            f"Zero variance in bands {zero_variance}; choose imagery with varying valid values."
        )
    report = dict(
        band_names=names,
        clip_value=clip_value,
        mean=mean.tolist(),
        std_sample=std.tolist(),
        pixels=pixels,
        available_training_windows=len(training),
        selected_training_windows=len(selected),
        excluded_zero_kelp_windows=len(training) - len(selected),
        selected_training_sources=len({original_key(row) for row in selected}),
        payload_bytes_read=payload_bytes,
        elapsed_seconds=time.monotonic() - started,
        chip_root=str(chips),
        assignments=str(assignments),
        experiment=experiment,
        variant=variant,
        kelp_only=kelp_only,
        method="float64 per-chip central moments, Chan merge, sample standard deviation (ddof=1); native all-band-zero nodata excluded; overlap counted by chip exposure",
    )
    logger.info("Writing complete statistics report: %s", output)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(output)
    logger.info("Complete statistics: %d pixel exposures, %s", pixels, output)
    return report
