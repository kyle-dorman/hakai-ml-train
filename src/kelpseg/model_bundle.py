"""Portable selected weights and image-array prediction, without training inputs."""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

from kelpseg.bands import resolve_band_indices
from kelpseg.models import build_model
from kelpseg.preprocessing import BAND_NAMES, CLIP_VALUE, MEAN, STD, native_validity
from kelpseg.training.transforms import build_input_transform


def export_model_bundle(checkpoint_path, output_directory, settings, *, run_id):
    """Export validation-selected weights, never ordinary recovery weights.

    Read only trusted local Lightning checkpoints. The exported weights file
    contains tensors alone and loads with PyTorch's restricted weights loader.
    """
    output = Path(output_directory)
    if output.exists():
        raise ValueError(f"Model bundle already exists: {output}.")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    weights = {
        key.removeprefix("model."): value
        for key, value in checkpoint["state_dict"].items()
        if key.startswith("model.")
    }
    if not weights:
        raise ValueError("Checkpoint has no model weights to export.")
    averaged = int(checkpoint.get("averaging_state", {}).get("n_averaged", 0))
    metadata = {
        "format_version": 1,
        "architecture": "segformer",
        "encoder": "mit_b3",
        "classes": 1,
        "band_names": list(settings.band_names),
        "clip_value": settings.clip_value,
        "mean": list(settings.mean),
        "std": list(settings.std),
        "input_size": 512,
        "input_layout": "HWC native raw uint16",
        "padding": "bottom/right zero; remove before returning probabilities",
        "nodata": "all native bands zero; returned probabilities are NaN",
        "normalized_invalid_fill": 0,
        "threshold": 0.5,
        "run_id": run_id,
        "name": settings.name,
        "experiment": settings.experiment,
        "variant": settings.variant,
        "weight_kind": "ema" if averaged else "current",
        "ema": {"decay": 0.999, "first_optimizer_update": 101, "n_averaged": averaged},
        "checkpoint_epoch": checkpoint["epoch"],
        "optimizer_updates": checkpoint["global_step"],
    }
    output.mkdir(parents=True)
    torch.save(weights, output / "weights.pt")
    (output / "model.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return output


@dataclass
class PortableModel:
    """Loaded inference weights; no optimizer, recipe path or label dependency."""

    model: torch.nn.Module
    metadata: dict
    device: torch.device

    def predict_probabilities(self, image, source_band_names):
        """Predict one native HWC uint16 array no larger than the saved canvas.

        Pass every native band and its physical name so nodata is determined
        before selecting model channels. Returns original-size HW float32 with
        NaN for native nodata. This helper does not tile or read raster files.
        """
        if (
            not isinstance(image, np.ndarray)
            or image.ndim != 3
            or image.dtype != np.uint16
            or image.shape[-1] != len(source_band_names)
        ):
            raise ValueError("Image must be HWC uint16 with named native channels.")
        size = self.metadata["input_size"]
        height, width = image.shape[:2]
        if not (0 < height <= size and 0 < width <= size):
            raise ValueError(f"Image height and width must be between 1 and {size}.")
        indices = resolve_band_indices(source_band_names, self.metadata["band_names"])
        valid = native_validity(image)
        padded = np.zeros((size, size, len(indices)), dtype=np.uint16)
        padded[:height, :width] = image[:, :, indices]
        padded_valid = np.zeros((size, size), dtype=np.int8)
        padded_valid[:height, :width] = valid
        transform = build_input_transform(self.metadata["band_names"])
        tensor = transform(image=padded, validity=padded_valid)["image"]
        with torch.inference_mode():
            probabilities = self.model(tensor[None].to(self.device)).sigmoid()
        result = probabilities[0, 0, :height, :width].cpu().numpy().copy()
        result[~valid] = np.nan
        return result


def load_model_bundle(directory, *, device="cpu"):
    """Construct offline, then load selected weights with no pretrained fetch."""
    directory = Path(directory)
    metadata = json.loads((directory / "model.json").read_text())
    if (
        metadata.get("format_version") != 1
        or metadata.get("architecture") != "segformer"
        or metadata.get("encoder") != "mit_b3"
        or metadata.get("classes") != 1
        or metadata.get("input_size") != 512
        or metadata.get("threshold") != 0.5
    ):
        raise ValueError("Unsupported model bundle architecture or prediction policy.")
    names = metadata["band_names"]
    indices = resolve_band_indices(BAND_NAMES, names)
    if (
        metadata["clip_value"] != CLIP_VALUE
        or metadata["mean"] != [MEAN[index] for index in indices]
        or metadata["std"] != [STD[index] for index in indices]
    ):
        raise ValueError("Bundle normalization differs from the supported baseline.")
    model = build_model(len(names), encoder_weights=None)
    model.load_state_dict(
        torch.load(directory / "weights.pt", map_location="cpu", weights_only=True)
    )
    device = torch.device(device)
    model.to(device).eval()
    return PortableModel(model, metadata, device)
