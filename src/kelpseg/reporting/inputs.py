"""Read saved predictions and explicit labels without loading a model."""

from __future__ import annotations

import csv
import json
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

import numpy as np
import rasterio
from rasterio import Affine

from kelpseg.paths import _resolve_path
from kelpseg.prepare.chip import map_labels


@dataclass(frozen=True)
class ReportSettings:
    """Flat report paths and declared evaluation scope, resolved before execution."""

    predictions: Path
    output: Path
    labels: Path | None = None
    label_root: Path | None = None
    external_scope: str = ""
    assignments: Path | None = None
    experiment: str = ""
    variant: str = ""
    split: str = ""
    max_examples: int = 12
    label_mapping: dict[int, int] = field(
        default_factory=lambda: {0: 0, 1: 1, 2: 0, 3: -100, 4: 0}
    )

    def __post_init__(self) -> None:
        """Reject ordinary invalid settings for Python and CLI callers."""
        if type(self.max_examples) is not int or self.max_examples < 0:
            raise ValueError("max_examples must be a nonnegative integer.")
        for name in ("external_scope", "experiment", "variant", "split"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be text.")
        if self.split not in ("", "train", "val", "test"):
            raise ValueError("split must be train, val or test.")
        if self.external_scope and self.assignments is not None:
            raise ValueError("Use external_scope or assignments, not both.")
        if not isinstance(self.label_mapping, dict) or not self.label_mapping:
            raise ValueError(
                "label_mapping must be a nonempty table of stored categories."
            )
        if any(
            type(k) is not int
            or not 0 <= k <= 255
            or type(v) is not int
            or v not in (-100, 0, 1)
            for k, v in self.label_mapping.items()
        ):
            raise ValueError("label_mapping maps stored uint8 values to -100, 0 or 1.")


def load_settings(recipe: str | Path) -> ReportSettings:
    """Read one TOML recipe and resolve paths against its directory."""
    recipe = Path(recipe).expanduser().resolve()
    values = tomllib.loads(recipe.read_text())
    unknown = values.keys() - {f.name for f in fields(ReportSettings)}
    if unknown:
        raise ValueError(f"Unknown report settings: {', '.join(sorted(unknown))}.")
    for key in ("predictions", "output", "labels", "label_root", "assignments"):
        value = values.get(key)
        if value is None and key not in ("predictions", "output"):
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a nonempty path.")
        values[key] = _resolve_path(value, base=recipe.parent, context=key)
    if "label_mapping" in values:
        mapping = values["label_mapping"]
        if not isinstance(mapping, dict):
            raise ValueError("label_mapping must be a table of stored categories.")
        try:
            values["label_mapping"] = {
                int(key): target for key, target in mapping.items()
            }
        except ValueError as error:
            raise ValueError(
                "label_mapping keys must be integer stored categories."
            ) from error
    return ReportSettings(**values)


def read_csv(path: Path) -> list[dict]:
    """Read a plain CSV, rejecting duplicate headers and incomplete rows."""
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        names = reader.fieldnames or []
        if len(names) != len(set(names)):
            raise ValueError(f"{path}: duplicate CSV columns.")
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError(f"{path}: row field count differs from header.")
    return rows


def _indexed(rows: list[dict], key: str, context: str) -> dict[str, dict]:
    """Index unique nonempty identities and fail with the input context."""
    result = {}
    for row in rows:
        value = row.get(key, "")
        if not value or value in result:
            raise ValueError(f"{context}: missing or duplicate {key}: {value!r}.")
        result[value] = row
    return result


def read_inputs(settings: ReportSettings) -> tuple[dict, list[dict], list[dict]]:
    """Validate completed prediction metadata and joins; return settings/sources/windows."""
    root = settings.predictions
    summary = json.loads((root / "summary.json").read_text())
    if summary.get("status") != "complete":
        raise ValueError(
            "Report requires completed predictions; rerun inference into a fresh output."
        )
    metadata = json.loads((root / "settings.json").read_text())
    metadata.setdefault("scope", "tiff_tiled")
    if metadata["scope"] not in ("chip_disjoint", "tiff_tiled"):
        raise ValueError("Unsupported prediction scope.")
    threshold = metadata["model"].get("threshold")
    if not isinstance(threshold, (float, int)) or not 0 <= threshold <= 1:
        raise ValueError("Saved model metadata needs a threshold in 0..1.")
    sources = read_csv(root / "sources.csv")
    if not sources:
        raise ValueError("No prediction sources to report.")
    indexed = _indexed(sources, "source_key", "Prediction sources")
    windows = read_csv(root / "windows.csv")
    if any(row.get("source_key") not in indexed for row in windows):
        raise ValueError("Prediction window has no matching source_key.")
    if metadata["scope"] == "chip_disjoint":
        if settings.labels or settings.assignments or settings.external_scope:
            raise ValueError(
                "Chip reports use the saved chip labels and membership; omit TIFF inputs."
            )
        if settings.split and settings.split != metadata["split"]:
            raise ValueError(
                "Report split differs from saved chip prediction selection."
            )
    else:
        if settings.labels is None or settings.label_root is None:
            raise ValueError("TIFF reports require labels CSV and label_root.")
        if not settings.split:
            raise ValueError("TIFF reports require an explicit train/val/test split.")
        if not settings.external_scope and settings.assignments is None:
            raise ValueError(
                "Declare external_scope or assignments for TIFF evaluation membership."
            )
        labels = _indexed(read_csv(settings.labels), "source_key", "Label CSV")
        if set(labels) != set(indexed):
            raise ValueError(
                "Label source_key identities must exactly match prediction sources."
            )
        for row in sources:
            label = labels[row["source_key"]]
            if not label.get("label"):
                raise ValueError(f"{row['source_key']}: label path is missing.")
            row["label"] = str(
                _resolve_path(label["label"], base=settings.label_root, context="label")
            )
            row["source_id"] = label.get("source_id") or row.get(
                "original_source_id", ""
            )
        if settings.assignments is not None:
            check_membership(sources, settings)
        metadata["split"] = settings.split
        metadata["external_scope"] = settings.external_scope
        metadata["assignments"] = (
            str(settings.assignments) if settings.assignments else None
        )
        metadata["experiment"], metadata["variant"] = (
            settings.experiment,
            settings.variant,
        )
    return metadata, sources, windows


def check_membership(sources: list[dict], settings: ReportSettings) -> None:
    """Join explicitly declared source IDs to one assignment scope, without guessing names."""
    if not settings.experiment or not settings.variant:
        raise ValueError("Assignment reports require experiment and variant.")
    selected = {}
    for row in read_csv(settings.assignments):
        if (row["experiment"], row["variant"]) != (
            settings.experiment,
            settings.variant,
        ):
            continue
        key = tuple(row[k] for k in ("dataset_id", "release_id", "source_id"))
        if key in selected:
            raise ValueError(f"Duplicate assignment identity: {key}.")
        selected[key] = row
    for source in sources:
        key = tuple(
            source.get(k, "") for k in ("dataset_id", "release_id", "source_id")
        )
        if not all(key) or key not in selected:
            raise ValueError(
                f"{source['source_key']}: missing assignment; label CSV must declare exact source_id."
            )
        row = selected[key]
        if row["split"] != settings.split:
            raise ValueError(
                f"{source['source_key']}: assignment is {row['split']}, not {settings.split}."
            )
        for left, right in (
            ("region_id", "region"),
            ("acquisition_date", "acquisition_date"),
        ):
            if source.get(left) and source[left] != row[right]:
                raise ValueError(
                    f"{source['source_key']}: conflicting assignment {left}."
                )


def read_probability(path: Path) -> tuple[np.ndarray, Affine, rasterio.crs.CRS]:
    """Read a saved single-band probability raster and its projected-metre grid."""
    with rasterio.open(path) as dataset:
        if dataset.count != 1 or dataset.dtypes != ("float32",):
            raise ValueError(f"{path}: expected single-band float32 probabilities.")
        if (
            dataset.crs is None
            or not dataset.crs.is_projected
            or dataset.crs.linear_units != "metre"
        ):
            raise ValueError(
                "Area reporting requires projected imagery with metre units."
            )
        probability = dataset.read(1)
        return probability, dataset.transform, dataset.crs


def read_tiff(source: dict, settings: ReportSettings) -> dict:
    """Read exact-grid imagery/labels for one saved TIFF prediction; never resample."""
    probability, transform, crs = read_probability(
        settings.predictions / source["probability"]
    )
    with (
        rasterio.open(source["image"]) as image,
        rasterio.open(source["label"]) as label,
    ):
        for dataset in (image, label):
            if (
                dataset.shape != probability.shape
                or dataset.transform != transform
                or dataset.crs != crs
            ):
                raise ValueError(
                    f"{source['source_key']}: image/label/prediction grids differ; run cleanup first."
                )
        if label.count != 1 or label.dtypes != ("uint8",):
            raise ValueError(
                f"{source['source_key']}: labels must be single-band uint8 cleaned TIFFs."
            )
        values = np.moveaxis(image.read(), 0, -1)
        valid = np.any(values != 0, axis=-1)
        labels = map_labels(label.read(1), settings.label_mapping, ~valid)
    if np.any(np.isfinite(probability) & ~valid):
        raise ValueError(
            f"{source['source_key']}: predictions cover native image nodata."
        )
    return dict(
        source=source,
        probability=probability,
        labels=labels,
        image=values,
        valid=valid,
        footprint=np.ones(valid.shape, dtype=bool),
        transform=transform,
        crs=crs,
    )


def read_chips(source: dict, windows: list[dict], settings: ReportSettings) -> dict:
    """Place recorded chip labels/images into the saved disjoint source canvas."""
    probability, transform, crs = read_probability(
        settings.predictions / source["probability"]
    )
    shape = probability.shape
    bands = source["band_names"].split(";")
    labels = np.full(shape, -100, dtype=np.int8)
    image = np.zeros((*shape, len(bands)), dtype=np.uint16)
    footprint = np.zeros(shape, dtype=bool)
    for row in windows:
        y = int(row["original_row"]) - int(source["row_offset"])
        x = int(row["original_col"]) - int(source["col_offset"])
        height, width = int(row["height"]), int(row["width"])
        if y < 0 or x < 0 or y + height > shape[0] or x + width > shape[1]:
            raise ValueError(
                f"{source['source_key']}: chip lies outside saved source canvas."
            )
        region = np.s_[y : y + height, x : x + width]
        if footprint[region].any():
            raise ValueError("Saved chip evaluation windows must be disjoint.")
        with np.load(row["payload"]) as arrays:
            values, target = arrays["image"], arrays["label"]
            if values.shape != (height, width, len(bands)) or target.shape != (
                height,
                width,
            ):
                raise ValueError(
                    f"{row['payload']}: chip dimensions differ from saved window."
                )
            image[region], labels[region] = values, target
        footprint[region] = True
    valid = np.any(image != 0, axis=-1)
    labels[~valid] = -100
    if np.any(np.isfinite(probability) & ~valid):
        raise ValueError(
            f"{source['source_key']}: predictions cover native image nodata."
        )
    return dict(
        source=source,
        probability=probability,
        labels=labels,
        image=image,
        valid=valid,
        footprint=footprint,
        transform=transform,
        crs=crs,
    )
