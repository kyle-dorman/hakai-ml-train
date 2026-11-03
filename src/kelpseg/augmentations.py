"""Small raw-unit adapter around unchanged stock Albumentations transforms."""

import albumentations as A
import numpy as np

NATIVE_SCALE = 65535


def _metadata_value(value, *, parameter_name=None):
    """Keep realized parameters readable without dumping full-image noise maps."""
    if isinstance(value, np.ndarray):
        # Retain small sampler outputs, including the coordinates of 16 holes.
        if value.size <= 64:
            return value.tolist()
        summary = {"shape": list(value.shape), "dtype": str(value.dtype)}
        if parameter_name == "noise_map":
            summary.update(
                empirical_mean=float(np.mean(value, dtype=np.float64)),
                empirical_std=float(np.std(value, dtype=np.float64)),
                domain="library unit-scale field before clipping",
            )
        return summary
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {
            name: _metadata_value(item, parameter_name=name)
            for name, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_metadata_value(item) for item in value]
    return value


def apply_augmentation(
    transform: A.BasicTransform | A.Compose,
    image: np.ndarray,
    label: np.ndarray,
    valid_mask: np.ndarray,
    seed: int | None = None,
    fixed_parameters: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Apply a real library transform or Compose to raw imagery and paired masks.

    Scale the full uint16 range to the library's float32 [0,1] domain, without
    applying the model's 5000 cap early. Stock pixel transforms may clip at zero
    and full scale. Stock filters see original nodata/padding zeros. Afterward,
    restore raw units and zero invalid fill; model preprocessing happens later.

    Establish validity from native bands before selecting spectral views.
    Training then applies transforms to the selected model-input bands, so
    ChannelDropout cannot choose an unused native channel; previews may use
    all eight native bands. Keep ordered band names alongside those arrays.
    Validity is an int8 mask target: D4 moves it,
    CoarseDropout's -100 mask fill removes hole support, and image-only classes
    preserve it. Never redetect nodata from values made zero by augmentation.
    Fixed sampler parameters are only for a named D4 element or a single named
    ChannelDropout band in diagnostic previews; kernels remain library code.
    The default seed=None advances the transform's existing random state.
    This adapter serves previews; training uses its full Albumentations
    normalization/ToTensorV2 Compose. Pass an integer seed when a diagnostic
    preview must replay a particular draw. Compose
    records its operation trace when constructed with save_applied_params=True;
    otherwise the returned applied-parameter list is empty.
    """
    if image.ndim != 3 or image.dtype != np.uint16:
        raise ValueError("Augmentation input must be raw HWC uint16 imagery.")
    if label.shape != image.shape[:2] or label.dtype != np.int8:
        raise ValueError("Labels must be mapped HW int8 matching the image.")
    if valid_mask.shape != image.shape[:2] or valid_mask.dtype != np.bool_:
        raise ValueError("Validity must be a boolean mask matching the image HW shape.")
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError("Augmentation seed must be a nonnegative integer or None.")

    transform.add_targets({"validity": "mask"})
    if seed is not None:
        transform.set_random_seed(seed)
    data = {
        "image": image.astype(np.float32) / NATIVE_SCALE,
        "mask": label.copy(),
        "validity": valid_mask.astype(np.int8),
    }
    if fixed_parameters is None:
        result = transform(**data)
        applied = (
            result.get("applied_transforms", [])
            if isinstance(transform, A.Compose)
            else transform.get_applied_params()
        )
    else:
        if isinstance(transform, A.D4):
            if set(fixed_parameters) != {"group_element"}:
                raise ValueError("Fixed D4 parameters must name one group_element.")
        elif isinstance(transform, A.ChannelDropout):
            channels = fixed_parameters.get("channels_to_drop")
            if (
                set(fixed_parameters) != {"channels_to_drop"}
                or not isinstance(channels, (list, tuple))
                or len(channels) != 1
                or type(channels[0]) is not int
                or not 0 <= channels[0] < image.shape[-1]
            ):
                raise ValueError(
                    "Fixed ChannelDropout must name one valid channel index."
                )
        else:
            raise ValueError(
                "Fixed parameters are only for D4 or ChannelDropout previews."
            )
        applied = transform.update_transform_params(transform.get_params(), data)
        applied.update(transform.get_params_dependent_on_data(applied, data))
        applied.update(fixed_parameters)
        result = transform.apply_with_params(applied, **data)

    valid = result["validity"] == 1
    raw = result["image"].astype(np.float32, copy=True) * NATIVE_SCALE
    raw[~valid] = 0
    kwargs = A.to_dict(transform)["transform"]
    kwargs.pop("__class_fullname__", None)
    metadata = {
        "class": type(transform).__name__,
        "kwargs": _metadata_value(kwargs),
        "applied": _metadata_value(applied),
        "seed": seed,
        "fixed_parameters": _metadata_value(fixed_parameters),
    }
    return raw, result["mask"].copy(), valid, metadata
