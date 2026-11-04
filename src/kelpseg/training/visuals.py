"""Small epoch samples from existing predictions, sent through native W&B logging."""

import numpy as np

from kelpseg.preprocessing import BAND_NAMES, MEAN, STD


def fixed_validation_samples(rows):
    """One positive chip per region where possible, then two background chips."""
    ordered = sorted(
        rows,
        key=lambda row: (
            row["region"],
            row["source_id"],
            int(row["row"]),
            int(row["col"]),
        ),
    )
    by_region = {}
    for row in ordered:
        by_region.setdefault(row["region"], []).append(row)
    keys = []
    for candidates in by_region.values():
        selected = candidates[0]
        for row in candidates:
            if int(row["kelp_pixels"]) > 0:
                selected = row
                break
        keys.append(str(selected["payload"]))
    extra_background = 0
    for row in ordered:
        key = str(row["payload"])
        if int(row["kelp_pixels"]) == 0 and key not in keys:
            keys.append(key)
            extra_background += 1
            if extra_background == 2:
                break
    return keys


def prediction_image(image, target, prediction, metadata, band_names, phase, epoch):
    """Display actual model input with aligned label/prediction mask layers."""
    channels = (
        ("red", "green", "blue") if "blue" in band_names else ("nir", "red", "green")
    )
    indices = [band_names.index(name) for name in channels]
    native = [BAND_NAMES.index(name) for name in channels]
    rgb = image[indices].detach().float().cpu().numpy().transpose(1, 2, 0)
    rgb = rgb * np.array(STD)[native] + np.array(MEAN)[native]
    label = target.detach().cpu().numpy().copy()
    pred = prediction.detach().cpu().numpy().copy()
    # W&B image lists require a common canvas. Keep loading padding in the
    # display; ignored targets make it gray and exclude it from both overlays.
    valid = label != -100
    if valid.any():
        low, high = np.percentile(rgb[valid], [2, 98], axis=0)
        rgb = np.clip((rgb - low) / np.maximum(high - low, 1), 0, 1)
    else:
        rgb[:] = 0
    rgb[~valid] = 0.3
    label[~valid] = pred[~valid] = 2
    classes = {0: "background", 1: "kelp", 2: "ignored"}
    caption = (
        f"epoch {epoch + 1} | region {metadata['region']} | "
        f"{metadata['source_id']} | {metadata['acquisition_date']} | "
        f"source window r{metadata['original_row']} c{metadata['original_col']} | "
        f"display {','.join(channels)} (2–98% stretch) | "
        + (
            "augmented training view; current weights"
            if phase == "train"
            else "validation view; validation weights"
        )
    )
    return dict(
        image=(rgb * 255).astype(np.uint8),
        caption=caption,
        masks={
            "label": {"mask_data": label.astype(np.uint8), "class_labels": classes},
            "prediction": {"mask_data": pred.astype(np.uint8), "class_labels": classes},
        },
    )


class EpochImages:
    """Retain only a bounded CPU sample; no extra model pass or random draws."""

    def __init__(self, rows, band_names):
        self.validation_keys = fixed_validation_samples(rows)
        self.band_names = tuple(band_names)
        self.samples = {"train": {}, "val": {}}

    def collect(self, batch, predictions, phase, epoch):
        samples = self.samples[phase]
        for index, metadata in enumerate(batch["metadata"]):
            key = str(metadata["payload"])
            if phase == "train" and len(samples) >= 4:
                break
            if key in samples or (phase == "val" and key not in self.validation_keys):
                continue
            samples[key] = prediction_image(
                batch["image"][index],
                batch["target"][index],
                predictions[index],
                metadata,
                self.band_names,
                phase,
                epoch,
            )

    def log(self, logger, phase, step):
        samples = self.samples[phase]
        keys = self.validation_keys if phase == "val" else list(samples)
        items = [samples[key] for key in keys if key in samples]
        if items:
            logger.log_image(
                key=f"{phase}/predictions",
                images=[item["image"] for item in items],
                caption=[item["caption"] for item in items],
                masks=[item["masks"] for item in items],
                step=step,
            )
        samples.clear()
