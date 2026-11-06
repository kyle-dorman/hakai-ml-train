"""Explicit paths and identity joins for label-only shoreline inventories."""

import json
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

import numpy as np
import rasterio
from rasterio import Affine

from kelpseg.paths import _resolve_path
from kelpseg.prepare.chip import map_labels
from kelpseg.prepare.splits import select_windows
from kelpseg.reporting.inputs import _indexed, read_csv
from kelpseg.reporting.shore_distance import (
    DEFAULT_DISTANCE_EDGES,
    NEARSHORE_CUTOFF_M,
    load_shore_sources,
    pixel_area_m2,
    validate_distance_edges,
)


@dataclass(frozen=True)
class ShoreInventorySettings:
    """Paths, fixed split membership and the training-window eligibility policy."""

    shoreline: Path
    image_root: Path
    labels: Path
    label_root: Path
    chip_root: Path
    assignments: Path
    output: Path
    experiment: str = "baseline"
    variant: str = "augmented"
    distance_edges: tuple[float, ...] = DEFAULT_DISTANCE_EDGES
    training_positive_only: bool = True
    label_mapping: dict[int, int] = field(
        default_factory=lambda: {0: 0, 1: 1, 2: 0, 3: -100, 4: 0}
    )

    def __post_init__(self) -> None:
        """Reject invalid analysis settings without changing source assignments."""
        validate_distance_edges(self.distance_edges)
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.experiment, self.variant)
        ):
            raise ValueError("experiment and variant must name an assignment scope.")
        if type(self.training_positive_only) is not bool:
            raise ValueError("training_positive_only must be true or false.")
        if (
            not isinstance(self.label_mapping, dict)
            or not self.label_mapping
            or any(
                type(k) is not int
                or not 0 <= k <= 255
                or type(v) is not int
                or v not in (-100, 0, 1)
                for k, v in self.label_mapping.items()
            )
        ):
            raise ValueError(
                "label_mapping maps stored uint8 categories to -100, 0 or 1."
            )


def load_settings(recipe: str | Path) -> ShoreInventorySettings:
    """Read one flat TOML recipe, resolving paths relative to the recipe file."""
    recipe = Path(recipe).expanduser().resolve()
    values = tomllib.loads(recipe.read_text())
    unknown = values.keys() - {item.name for item in fields(ShoreInventorySettings)}
    if unknown:
        raise ValueError(
            f"Unknown shore-inventory settings: {', '.join(sorted(unknown))}."
        )
    for name in (
        "shoreline",
        "image_root",
        "labels",
        "label_root",
        "chip_root",
        "assignments",
        "output",
    ):
        value = values.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty path.")
        values[name] = _resolve_path(value, base=recipe.parent, context=name)
    if "distance_edges" in values:
        if not isinstance(values["distance_edges"], list):
            raise ValueError("distance_edges must be an array of metre boundaries.")
        values["distance_edges"] = tuple(values["distance_edges"])
    if "label_mapping" in values:
        if not isinstance(values["label_mapping"], dict):
            raise ValueError("label_mapping must be a table of stored categories.")
        values["label_mapping"] = {
            int(k): v for k, v in values["label_mapping"].items()
        }
    return ShoreInventorySettings(**values)


def read_inventory_inputs(
    settings: ShoreInventorySettings,
) -> tuple[dict, list[dict], list[dict]]:
    """Join shoreline rows to explicit labels, chip identities and source assignments.

    Return the shoreline index, enriched source rows, and selected window rows.
    A subset of the chip collection is permitted and remains an explicit inventory
    scope. Label rows must exactly match that shoreline subset.
    """
    shore = load_shore_sources(settings.shoreline)
    labels = _indexed(read_csv(settings.labels), "source_key", "Inventory labels")
    if set(labels) != set(shore):
        raise ValueError(
            "Inventory labels must exactly match shoreline source_key identities."
        )
    chips = _indexed(
        json.loads((settings.chip_root / "sources.json").read_text()),
        "source_key",
        "Chip sources",
    )
    selected = {}
    for row in read_csv(settings.assignments):
        if (row["experiment"], row["variant"]) != (
            settings.experiment,
            settings.variant,
        ):
            continue
        key = tuple(row[name] for name in ("dataset_id", "release_id", "source_id"))
        if key in selected:
            raise ValueError(f"Duplicate source assignment: {key}.")
        selected[key] = row
    sources = []
    for key, row in shore.items():
        if key not in chips:
            raise ValueError(f"{key}: missing chip source identity.")
        chip = chips[key]
        original = tuple(
            chip[name] for name in ("dataset_id", "release_id", "source_id")
        )
        if original not in selected:
            raise ValueError(f"{key}: missing source assignment in requested scope.")
        assignment = selected[original]
        if assignment["split"] not in ("train", "val", "test", "unused"):
            raise ValueError(f"{key}: unknown assignment split.")
        for shore_name, chip_name in (
            ("dataset_id", "dataset_id"),
            ("release_id", "release_id"),
            ("original_source_id", "source_id"),
            ("region_id", "region"),
            ("acquisition_date", "acquisition_date"),
        ):
            if not row.get(shore_name) or row[shore_name] != str(chip[chip_name]):
                raise ValueError(f"{key}: shoreline and chip {shore_name} differ.")
        if any(
            str(row.get(name, "")) != str(chip[name])
            for name in ("row_offset", "col_offset")
        ):
            raise ValueError(f"{key}: shoreline and chip crop offsets differ.")
        if max(NEARSHORE_CUTOFF_M, settings.distance_edges[-1]) > float(row["cap_m"]):
            raise ValueError(
                f"{key}: shoreline distance cap must cover all bins and the {NEARSHORE_CUTOFF_M} m summary."
            )
        label = labels[key].get("label", "")
        if not label:
            raise ValueError(f"{key}: label path is missing.")
        sources.append(
            dict(
                row,
                label=str(_resolve_path(label, base=settings.label_root, context=key)),
                image=str(
                    _resolve_path(row["image"], base=settings.image_root, context=key)
                ),
                source_id=chip["source_id"],
                split=assignment["split"],
            )
        )
    windows = select_windows(
        settings.chip_root, settings.assignments, settings.experiment, settings.variant
    )
    return shore, sources, [row for row in windows if row["source_key"] in shore]


def read_label_canvas(sources: list[dict], mapping: dict[int, int]) -> dict:
    """Merge exact-grid cleaned labels and native validity once per original.

    Images are read one band at a time to identify all-band-zero nodata. Declared
    overlapping crops must have matching original grids and agreeing known labels.
    No predictions or chip payloads are read, and input files are never modified.
    """
    first = sources[0]
    top = min(int(row["row_offset"]) for row in sources)
    left = min(int(row["col_offset"]) for row in sources)
    bottom = max(int(row["row_offset"]) + int(row["height"]) for row in sources)
    right = max(int(row["col_offset"]) + int(row["width"]) for row in sources)
    labels = np.full((bottom - top, right - left), -100, dtype=np.int8)
    footprint = np.zeros(labels.shape, dtype=bool)
    valid = np.zeros(labels.shape, dtype=bool)
    original_transform, crs = None, None
    for source in sources:
        for name in (
            "region_id",
            "acquisition_date",
            "split",
            "dataset_id",
            "release_id",
        ):
            if source[name] != first[name]:
                raise ValueError(f"Crops of one original disagree on {name}.")
        with (
            rasterio.open(source["image"]) as image,
            rasterio.open(source["label"]) as label,
        ):
            if (
                label.count != 1
                or image.shape != label.shape
                or image.crs != label.crs
                or image.transform != label.transform
            ):
                raise ValueError(
                    f"{source['source_key']}: labels must exactly match the image grid."
                )
            if image.shape != (int(source["height"]), int(source["width"])):
                raise ValueError(
                    f"{source['source_key']}: image shape differs from shoreline metadata."
                )
            pixel_area_m2(image.crs, image.transform)
            origin = image.transform * Affine.translation(
                -int(source["col_offset"]), -int(source["row_offset"])
            )
            if original_transform is None:
                original_transform, crs = origin, image.crs
            elif crs != image.crs or not original_transform.almost_equals(
                origin, precision=1e-7
            ):
                raise ValueError(
                    "Crops of one original have incompatible grids or offsets."
                )
            native_valid = np.zeros(image.shape, dtype=bool)
            for band in range(1, image.count + 1):
                native_valid |= image.read(band) != 0
            target = map_labels(label.read(1, masked=False), mapping, ~native_valid)
            y, x = int(source["row_offset"]) - top, int(source["col_offset"]) - left
            region = np.s_[y : y + image.height, x : x + image.width]
            known = target != -100
            if np.any(known & (labels[region] != -100) & (labels[region] != target)):
                raise ValueError(
                    "Conflicting valid labels in overlapping crops of one original."
                )
            labels[region][known] = target[known]
            valid[region] |= native_valid
            footprint[region] = True
    source = dict(
        first,
        source_keys=";".join(row["source_key"] for row in sources),
        row_offset=top,
        col_offset=left,
    )
    return dict(
        source=source,
        labels=labels,
        valid=valid,
        footprint=footprint,
        transform=original_transform * Affine.translation(left, top),
        crs=crs,
    )
