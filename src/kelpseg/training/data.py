"""Manifest-selected training/validation tensors without held-out payload reads."""

import json
import logging
from pathlib import Path

from torch.utils.data import Dataset

from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.bands import resolve_band_indices
from kelpseg.chips import load_chip
from kelpseg.prepare.splits import select_windows
from kelpseg.preprocessing import BAND_NAMES
from kelpseg.training.transforms import build_input_transform

logger = logging.getLogger(__name__)


class ChipDataset(Dataset):
    """Load selected rows; keep source metadata separate from augmented tensors.

    ``metadata`` records the original source window and loading padding. D4 can
    move that padding in a training tensor; ``valid_mask`` follows the transform.
    Validation is unaugmented, so its original bottom/right padding can be
    removed directly using true_height/true_width. No test rows are accepted.
    """

    def __init__(
        self,
        rows: list[dict],
        source_band_names,
        selection="all",
        chip_size: int = 512,
        augmentation=None,
        include_distance: bool = False,
    ):
        if any(row["split"] not in ("train", "val") for row in rows):
            raise ValueError(
                "ChipDataset accepts train/val rows only; keep test metadata separate."
            )
        if augmentation is not None and any(row["split"] != "train" for row in rows):
            raise ValueError("Augmentation is allowed for training rows only.")
        indices = resolve_band_indices(source_band_names, selection)
        self.band_names = tuple(source_band_names[index] for index in indices)
        # Validate fixed normalization availability before any payload is opened.
        resolve_band_indices(BAND_NAMES, self.band_names)
        self.rows = rows
        self.source_band_names = tuple(source_band_names)
        self.chip_size = chip_size
        self.include_distance = include_distance
        self.transform = build_input_transform(self.band_names, augmentation)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        # load_chip establishes validity using every native channel *before*
        # selection. Applying stock transforms to these selected channels makes
        # ChannelDropout uniformly choose an actual model input, never a hidden
        # native band. band_names retains each selected channel's physical identity.
        chip = load_chip(
            row["payload"],
            self.source_band_names,
            self.band_names,
            self.chip_size,
            include_distance=self.include_distance,
        )
        image, target, valid = chip["image"], chip["label"], chip["valid_mask"]
        if target is None:
            raise ValueError(
                f"{row['payload']}: training/validation requires mapped labels."
            )
        inputs = {"image": image, "mask": target, "validity": valid.astype("int8")}
        if self.include_distance:
            inputs["effective_distance_m"] = chip["effective_distance_m"]
        tensors = self.transform(**inputs)
        metadata = dict(row)
        metadata.update(
            band_names=self.band_names,
            true_height=chip["true_height"],
            true_width=chip["true_width"],
            padding=chip["padding"],
        )
        sample = {
            "image": tensors["image"],
            "target": tensors["mask"],
            "valid_mask": tensors["validity"] == 1,
            "metadata": metadata,
        }
        if self.include_distance:
            sample["effective_distance_m"] = tensors["effective_distance_m"]
        return sample


def build_training_inputs(
    chips: str | Path,
    assignments,
    *,
    selection="all",
    experiment: str = "baseline",
    variant: str = "augmented",
    seed: int = 33,
    include_distance: bool = False,
) -> dict:
    """Select positive training chips and representative disjoint validation.

    Read metadata only and request distance arrays for training only. Return test
    identities as rows. Training keeps canonical overlap and filters only
    kelp_pixels > 0. Validation and test retain the selector's declared scope.
    """
    chips = Path(chips).expanduser().resolve()
    recipe = json.loads((chips / "recipe.json").read_text(encoding="utf-8"))
    rows = select_windows(chips, assignments, experiment=experiment, variant=variant)
    training, excluded, validation, test = [], [], [], []
    for row in rows:
        if row["split"] == "train":
            try:
                kelp_pixels = int(row["kelp_pixels"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"{row['payload']}: training selection requires manifest kelp_pixels counts."
                ) from error
            if kelp_pixels < 0:
                raise ValueError(f"{row['payload']}: kelp_pixels must be nonnegative.")
            if kelp_pixels > 0:
                training.append(row)
            else:
                excluded.append(row)
        elif row["split"] == "val":
            validation.append(row)
        elif row["split"] == "test":
            test.append(row)
    if not training:
        raise ValueError(
            "No kelp-positive training windows; check experiment and variant."
        )
    train = ChipDataset(
        training,
        recipe["source_band_names"],
        selection,
        recipe["chip_size"],
        build_training_augmentation(seed),
        include_distance=include_distance,
    )
    val = ChipDataset(
        validation, recipe["source_band_names"], selection, recipe["chip_size"]
    )
    counts = {
        "training_candidates": len(training) + len(excluded),
        "training_eligible": len(training),
        "training_excluded_zero_kelp": len(excluded),
        "validation": len(validation),
        "test_metadata_only": len(test),
    }
    logger.info(
        "Training inputs %s/%s: bands=%s; counts=%s",
        experiment,
        variant,
        train.band_names,
        counts,
    )
    return dict(
        train=train,
        val=val,
        test_rows=test,
        excluded_training_rows=excluded,
        counts=counts,
    )
