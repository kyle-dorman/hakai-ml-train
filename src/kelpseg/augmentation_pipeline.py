"""The approved stock Albumentations training augmentation recipe."""

import albumentations as A


def build_training_augmentation(seed: int = 33) -> A.Compose:
    """Always sample D4, then choose two distinct extras in the listed order.

    All eight pool entries are equally eligible; SomeOf samples without
    replacement and applies chosen entries in pool order.
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
