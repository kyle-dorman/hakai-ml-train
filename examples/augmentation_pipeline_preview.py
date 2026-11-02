"""Review the agreed stock pipeline: uv run python examples/augmentation_pipeline_preview.py.

Edit paths for your machine and choose a fresh output. The readable actual
training recipe lives in kelpseg/augmentation_pipeline.py, with its approved
native snapshot in configs/augment/baseline.json. This example does not import
a model, open held-out payloads or launch training.
"""

import logging
from pathlib import Path

from kelpseg.pipeline_preview import preview_pipeline

DATA_ROOT = Path("/Volumes/x10pro/kelpseg")
OUTPUT = DATA_ROOT / "analyses" / "my-pipeline-previews-01"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    gallery = preview_pipeline(
        chips=DATA_ROOT / "data/chips/ca_bc/v1",
        assignments=DATA_ROOT / "data/splits/ca_bc/v1/assignments.csv",
        variant="augmented",
        output=OUTPUT,
        seed=33,
        positive_samples=14,
        draws=8,
    )
    print(f"Open in your browser: {gallery / 'index.html'}")
