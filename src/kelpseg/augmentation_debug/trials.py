"""Readable isolated sweeps of the actual Albumentations 2.0.8 classes.

Edit the literal native constructor values below to explore other strengths.
Equal range endpoints fix a class's sampled strength; seeds fix its remaining
random choices. No project-specific augmentation formulas or policy live here.
"""

import albumentations as A
import numpy as np

from kelpseg.augmentations import apply_augmentation
from kelpseg.preprocessing import CLIP_VALUE, cap_raw, normalize


def value_metrics(image, label, valid, names):
    """Report raw values after the stock transform, before the final model cap."""
    capped = cap_raw(image, valid)
    normalized = normalize(image, names, valid)
    bands = {}
    for index, name in enumerate(names):
        values, final = image[:, :, index][valid], capped[:, :, index][valid]
        model = normalized[:, :, index][valid]
        bands[name] = {
            "raw_range": [float(values.min()), float(values.max())]
            if values.size
            else None,
            "capped_range": [float(final.min()), float(final.max())]
            if values.size
            else None,
            "normalized_range": [float(model.min()), float(model.max())]
            if values.size
            else None,
            "below_zero_values": int(np.count_nonzero(values < 0)),
            "above_cap_values": int(np.count_nonzero(values > CLIP_VALUE)),
        }
    return dict(
        valid_pixels=int(valid.sum()),
        foreground_pixels=int(np.count_nonzero((label == 1) & valid)),
        scoreable_pixels=int(np.count_nonzero((label != -100) & valid)),
        ignored_pixels=int(np.count_nonzero(label == -100)),
        below_zero_values=sum(b["below_zero_values"] for b in bands.values()),
        above_cap_values=sum(b["above_cap_values"] for b in bands.values()),
        bands=bands,
    )


def individual_trials(sample: dict, seed: int = 33):
    """Yield one native library class at a time, always starting from original data."""
    image, label, valid = sample["image"], sample["label"], sample["valid"]
    names = sample["band_names"]

    def state(title, transform, *, fixed=None, identity=False, preview_default=False):
        raw, targets, support, parameters = apply_augmentation(
            transform, image, label, valid, seed, fixed
        )
        crop = sample["closeup"]
        if isinstance(transform, A.D4):
            # Move the same footprint with the actual library mask operation.
            footprint = np.zeros(label.shape, dtype=np.uint8)
            top, left, bottom, right = crop
            footprint[top:bottom, left:right] = 1
            moved = transform.apply_to_mask(footprint, **parameters["applied"])
            ys, xs = np.where(moved)
            crop = int(ys.min()), int(xs.min()), int(ys.max()) + 1, int(xs.max()) + 1
        return dict(
            title=title,
            parameters=parameters,
            image=raw,
            label=targets,
            valid=support,
            display=cap_raw(raw, support),
            metrics=value_metrics(raw, targets, support, names),
            closeup=crop,
            is_identity=identity,
            preview_default=preview_default,
        )

    original = state("Original", A.NoOp(p=1), identity=True)

    def identity():
        return state("Identity (NoOp)", A.NoOp(p=1), identity=True)

    yield (
        "square_symmetry",
        [
            original,
            *[
                state(
                    f"D4: {element}" + (" (identity)" if element == "e" else ""),
                    A.D4(p=1),
                    fixed={"group_element": element},
                    identity=element == "e",
                )
                for element in ("e", "r90", "r180", "r270", "v", "hvt", "h", "t")
            ],
        ],
    )

    yield (
        "brightness",
        [
            original,
            *[
                state(
                    f"brightness_limit={beta:g}" + (" (identity)" if beta == 0 else ""),
                    A.RandomBrightnessContrast(
                        brightness_limit=(beta, beta),
                        contrast_limit=(0, 0),
                        brightness_by_max=True,
                        p=1,
                    ),
                    identity=beta == 0,
                    preview_default=beta == 0.0025,
                )
                for beta in (
                    -0.2,
                    -0.1,
                    -0.05,
                    -0.02,
                    -0.01,
                    -0.005,
                    -0.0025,
                    0,
                    0.0025,
                    0.005,
                    0.01,
                    0.02,
                    0.05,
                    0.1,
                    0.2,
                )
            ],
        ],
    )

    # In this library contrast-only is multiplication by 1 + contrast_limit.
    # It duplicates global MultiplicativeNoise, so offer one clearly named sweep.
    yield (
        "gain",
        [
            original,
            *[
                state(
                    f"contrast_limit={delta:g}" + (" (identity)" if delta == 0 else ""),
                    A.RandomBrightnessContrast(
                        brightness_limit=(0, 0), contrast_limit=(delta, delta), p=1
                    ),
                    identity=delta == 0,
                    preview_default=delta == 0.1,
                )
                for delta in (-0.2, -0.1, 0, 0.1, 0.2)
            ],
        ],
    )

    # sigma=0 is not a valid GaussianBlur identity in this pinned release.
    yield (
        "blur",
        [
            original,
            identity(),
            *[
                state(
                    f"sigma_limit={sigma:g} px",
                    A.GaussianBlur(blur_limit=0, sigma_limit=(sigma, sigma), p=1),
                    preview_default=sigma == 1.2,
                )
                for sigma in (0.4, 0.5, 0.8, 1.2, 1.5, 2, 3)
            ],
        ],
    )

    yield (
        "noise",
        [
            original,
            *[
                state(
                    f"std_range={std:g}" + (" (identity)" if std == 0 else ""),
                    A.GaussNoise(
                        std_range=(std, std),
                        mean_range=(0, 0),
                        per_channel=True,
                        noise_scale_factor=1,
                        p=1,
                    ),
                    identity=std == 0,
                    preview_default=std == 0.0005,
                )
                for std in (
                    0,
                    0.00015,
                    0.0004,
                    0.0005,
                    0.0008,
                    0.002,
                    0.005,
                    0.01,
                    0.02,
                    0.05,
                    0.1,
                    0.2,
                    0.3,
                    0.44,
                )
            ],
        ],
    )

    yield (
        "sharpness",
        [
            original,
            *[
                state(
                    f"alpha={alpha:g}" + (" (identity)" if alpha == 0 else ""),
                    A.Sharpen(
                        method="gaussian",
                        alpha=(alpha, alpha),
                        kernel_size=5,
                        sigma=1,
                        p=1,
                    ),
                    identity=alpha == 0,
                )
                for alpha in (0, 0.1, 0.25, 0.5, 1)
            ],
        ],
    )

    yield (
        "spatial_dropout",
        [
            original,
            identity(),
            *[
                state(
                    f"holes=4; side={side:g}",
                    A.CoarseDropout(
                        num_holes_range=(4, 4),
                        hole_height_range=(side, side),
                        hole_width_range=(side, side),
                        fill=0,
                        fill_mask=-100,
                        p=1,
                    ),
                    preview_default=side == 0.25,
                )
                for side in (0.05, 0.1, 0.2, 0.25, 0.35, 0.5)
            ],
        ],
    )

    # Change count independently of side length, using the same stock class.
    yield (
        "spatial_dropout_count",
        [
            original,
            identity(),
            *[
                state(
                    f"holes={count}; side=0.25",
                    A.CoarseDropout(
                        num_holes_range=(count, count),
                        hole_height_range=(0.25, 0.25),
                        hole_width_range=(0.25, 0.25),
                        fill=0,
                        fill_mask=-100,
                        p=1,
                    ),
                    preview_default=count == 4,
                )
                for count in (1, 2, 4, 8, 16)
            ],
        ],
    )

    yield (
        "channel_shifts",
        [
            original,
            *[
                state(
                    f"uniform range=±{amplitude:g}"
                    + (" (identity)" if amplitude == 0 else ""),
                    A.AdditiveNoise(
                        noise_type="uniform",
                        spatial_mode="constant",
                        noise_params={"ranges": [(-amplitude, amplitude)]},
                        p=1,
                    ),
                    identity=amplitude == 0,
                    preview_default=amplitude == 0.002,
                )
                for amplitude in (0, 0.0004, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1)
            ],
        ],
    )

    for band in ("red", "nir"):
        yield (
            f"band_dropout_{band}",
            [
                original,
                identity(),
                state(
                    f"{band}: full dropout, fill=0",
                    A.ChannelDropout(channel_drop_range=(1, 1), fill=0, p=1),
                    fixed={"channels_to_drop": [names.index(band)]},
                ),
            ],
        )
