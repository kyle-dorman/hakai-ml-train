"""The selected stock pipeline and paired diagnostic views of its real draws."""

import albumentations as A
import numpy as np

from kelpseg.augmentation_trials import value_metrics
from kelpseg.augmentations import apply_augmentation
from kelpseg.preprocessing import cap_raw


def build_training_augmentation(seed: int = 33) -> A.Compose:
    """Always sample D4, then choose two distinct extras in the listed order.

    All eight pool entries are equally eligible; SomeOf samples without
    replacement and applies chosen entries in pool order. The preview applies
    this native-band pipeline before selecting spectral display views.
    Reuse the returned Compose with apply_augmentation during training; its
    default seed=None lets successive calls advance the seeded random state.
    """
    return A.Compose(
        [
            A.D4(p=1),
            A.SomeOf(
                [
                    A.RandomBrightnessContrast(
                        brightness_limit=(-0.0025, 0.005),
                        contrast_limit=(0, 0),
                        brightness_by_max=True,
                        p=1,
                    ),
                    A.RandomBrightnessContrast(
                        brightness_limit=(0, 0), contrast_limit=(-0.2, 0.2), p=1
                    ),
                    A.GaussianBlur(blur_limit=0, sigma_limit=(0.5, 1.5), p=1),
                    A.GaussNoise(
                        std_range=(0, 0.002),
                        mean_range=(0, 0),
                        per_channel=True,
                        noise_scale_factor=1,
                        p=1,
                    ),
                    A.Sharpen(
                        method="gaussian",
                        alpha=(0, 1),
                        kernel_size=5,
                        sigma=1,
                        p=1,
                    ),
                    A.CoarseDropout(
                        num_holes_range=(1, 4),
                        hole_height_range=(0.05, 0.25),
                        hole_width_range=(0.05, 0.25),
                        fill=0,
                        fill_mask=-100,
                        p=1,
                    ),
                    A.AdditiveNoise(
                        noise_type="uniform",
                        spatial_mode="constant",
                        noise_params={"ranges": [(-0.01, 0.01)]},
                        p=1,
                    ),
                    A.ChannelDropout(channel_drop_range=(1, 1), fill=0, p=1),
                ],
                n=2,
                replace=False,
                p=1,
            ),
        ],
        seed=seed,
        save_applied_params=True,
    )


def pipeline_states(sample: dict, seed: int = 33) -> list[dict]:
    """Return source, the same sampled D4 reference, and actual full output.

    Every full draw records the real stock operation order and parameters;
    source and D4 reference explain which changes came from geometry alone.
    """
    image, label, valid = sample["image"], sample["label"], sample["valid"]
    names, crop = sample["band_names"], sample["closeup"]
    full = apply_augmentation(
        build_training_augmentation(seed), image, label, valid, seed
    )
    full_parameters = full[3]
    group = full_parameters["applied"][0][1]["group_element"]
    d4 = A.D4(p=1)
    reference = apply_augmentation(
        d4, image, label, valid, seed, {"group_element": group}
    )
    footprint = np.zeros(label.shape, dtype=np.uint8)
    top, left, bottom, right = crop
    footprint[top:bottom, left:right] = 1
    moved = d4.apply_to_mask(footprint, group_element=group)
    ys, xs = np.where(moved)
    moved_crop = int(ys.min()), int(xs.min()), int(ys.max()) + 1, int(xs.max()) + 1

    trace = []
    for class_name, parameters in full_parameters["applied"]:
        entry = {"class": class_name, "parameters": parameters}
        if class_name == "ChannelDropout":
            entry["dropped_bands"] = [
                names[index] for index in parameters["channels_to_drop"]
            ]
        trace.append(entry)
    full_parameters["operation_trace"] = trace

    def state(title, result, closeup, *, identity=False):
        raw, targets, support, parameters = result
        return dict(
            title=title,
            parameters=parameters,
            image=raw,
            label=targets,
            valid=support,
            display=cap_raw(raw, support),
            metrics=value_metrics(raw, targets, support, names),
            closeup=closeup,
            is_identity=identity,
            preview_default=False,
        )

    original = apply_augmentation(A.NoOp(p=1), image, label, valid, seed)
    return [
        state("Source original", original, crop, identity=True),
        state(f"D4 reference: {group}", reference, moved_crop, identity=group == "e"),
        state("D4 + two sampled extras", full, moved_crop),
    ]
