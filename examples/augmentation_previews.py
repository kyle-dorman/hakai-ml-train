"""Explore actual Albumentations classes before selecting a training policy.

Run from the repository: uv run python examples/augmentation_previews.py
Edit the paths below for your machine and choose a fresh output for each run.
Edit the literal native class settings in kelpseg/augmentation_trials.py.
The shared raw-data adapter is kelpseg/augmentations.py; it changes no kernels.
Review the approved combined policy with augmentation_pipeline_preview.py.
"""

import logging
from pathlib import Path

from kelpseg.augmentation_preview import preview_augmentations

DATA_ROOT = Path("/Volumes/x10pro/kelpseg")
OUTPUT = DATA_ROOT / "analyses" / "my-isolated-previews-01"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    gallery = preview_augmentations(
        chips=DATA_ROOT / "data/chips/ca_bc/v1",
        assignments=DATA_ROOT / "data/splits/ca_bc/v1/assignments.csv",
        variant="augmented",
        output=OUTPUT,
        seed=33,
        positive_samples=14,
    )
    print(f"Open in your browser: {gallery / 'index.html'}")
