"""One Albumentations pipeline from raw model bands to normalized tensors."""

import albumentations as A
import numpy as np
from albumentations.pytorch import ToTensorV2

from kelpseg.augmentations import NATIVE_SCALE
from kelpseg.bands import resolve_band_indices
from kelpseg.preprocessing import BAND_NAMES, CLIP_VALUE, MEAN, STD


class _RestoreRawAndCap(A.ImageOnlyTransform):
    """Stock photometric operations use [0,1]; fixed statistics use raw units."""

    def apply(self, image, **params):
        return np.minimum(image * NATIVE_SCALE, CLIP_VALUE)


class _RestoreInvalid(A.DualTransform):
    """Restore normalized zero fill and ignored targets using moved validity."""

    def get_params_dependent_on_data(self, params, data):
        return {"valid": data["validity"] == 1}

    def apply(self, image, valid, **params):
        image = image.copy()
        image[~valid] = 0
        return image

    def apply_to_mask(
        self, mask: np.ndarray, valid: np.ndarray, **params
    ) -> np.ndarray:
        """Ignore invalid pixels, preserving floating-point distance masks."""
        if np.issubdtype(mask.dtype, np.floating):
            mask = mask.copy()
        else:
            mask = mask.astype(np.int64)
        mask[~valid] = -100
        return mask


def build_input_transform(band_names, augmentation=None) -> A.Compose:
    """Compose raw scaling, optional approved augmentation, normalization/tensors.

    Validity must already come from all native bands before selection. It travels
    as an int8 mask through D4 and coarse dropout; augmented zeros never redefine
    nodata. Channel dropout sees only the selected physical model-input bands.
    Validation uses this same pipeline without random augmentation. Stock
    Normalize uses the shared full-precision constants with float32 arithmetic;
    output agrees with the NumPy reference within ordinary float32 tolerance.
    """
    indices = resolve_band_indices(BAND_NAMES, tuple(band_names))
    transforms = [A.ToFloat(max_value=NATIVE_SCALE, p=1)]
    if augmentation is not None:
        transforms.append(augmentation)
    transforms.extend(
        [
            _RestoreRawAndCap(p=1),
            A.Normalize(
                mean=tuple(MEAN[index] for index in indices),
                std=tuple(STD[index] for index in indices),
                max_pixel_value=1,
                p=1,
            ),
            _RestoreInvalid(p=1),
            ToTensorV2(p=1),
        ]
    )
    return A.Compose(
        transforms,
        additional_targets={"validity": "mask", "effective_distance_m": "mask"},
        seed=augmentation.seed if augmentation is not None else None,
    )
