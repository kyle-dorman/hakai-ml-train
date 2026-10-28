"""Small chipping recipe, exact-key identity joins and header-only planning."""

from __future__ import annotations

import csv
import logging
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import rasterio

from kelpseg.bands import resolve_band_indices
from kelpseg.prepare.check import (
    CheckRecipe,
    InputPair,
    PreparationError,
    _check_image_header,
    discover_inputs,
    same_grid,
)
from kelpseg.prepare.clean_inputs import _check_output_locations, safe_path

logger = logging.getLogger(__name__)
IDENTITY_COLUMNS = (
    "source_key",
    "source_id",
    "original_tiff",
    "dataset_id",
    "release_id",
    "region",
    "acquisition_date",
    "row_offset",
    "col_offset",
    "original_height",
    "original_width",
)


@dataclass(frozen=True)
class ChipRecipe:
    schema_version: int = 1
    chip_size: int = 512
    stride: int = 256
    max_nodata_pct: float = 50.0
    source_band_names: tuple[str, ...] = ()
    label_mapping: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ChipPlan:
    images: Path
    labels: Path | None
    output: Path
    recipe: ChipRecipe
    pairs: tuple[InputPair, ...]
    sources: tuple[dict, ...]
    window_count: int
    source_bytes: int


def validate_chip_recipe(recipe: ChipRecipe) -> ChipRecipe:
    if type(recipe.schema_version) is not int or recipe.schema_version != 1:
        raise PreparationError("Use chip schema_version = 1.")
    if type(recipe.chip_size) is not int or recipe.chip_size < 1:
        raise PreparationError("chip_size must be a positive integer.")
    if type(recipe.stride) is not int or not 1 <= recipe.stride <= recipe.chip_size:
        raise PreparationError("stride must be an integer in 1..chip_size.")
    if (
        type(recipe.max_nodata_pct) not in (int, float)
        or not 0 <= recipe.max_nodata_pct <= 100
    ):
        raise PreparationError("max_nodata_pct must be a number in 0..100.")
    try:
        resolve_band_indices(recipe.source_band_names)
    except ValueError as error:
        raise PreparationError(str(error)) from error
    if len(recipe.source_band_names) not in (3, 4, 8):
        raise PreparationError("Declare the native 3, 4 or 8 source_band_names.")
    if not isinstance(recipe.label_mapping, dict):
        raise PreparationError(
            "label_mapping must be a table of stored category to target."
        )
    for category, target in recipe.label_mapping.items():
        if type(category) is not int or not 0 <= category <= 255:
            raise PreparationError(
                "label_mapping keys must be stored uint8 categories."
            )
        if type(target) is not int or target not in (-100, 0, 1):
            raise PreparationError("label_mapping values must be -100, 0 or 1.")
    return recipe


def load_chip_recipe(path: str | Path) -> ChipRecipe:
    try:
        values = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        unknown = set(values) - set(ChipRecipe.__dataclass_fields__)
        if unknown:
            raise PreparationError(
                f"Unknown chip settings: {', '.join(sorted(unknown))}"
            )
        if not isinstance(values.get("source_band_names"), list):
            raise PreparationError("source_band_names must be an explicit TOML array.")
        values["source_band_names"] = tuple(values["source_band_names"])
        mapping = values.get("label_mapping", {})
        if not isinstance(mapping, dict):
            raise PreparationError(
                "label_mapping must be a table of category to target."
            )
        values["label_mapping"] = {int(key): value for key, value in mapping.items()}
        return validate_chip_recipe(ChipRecipe(**values))
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise PreparationError(f"Cannot read chip recipe {path}: {error}") from error


def axis_starts(length: int, chip_size: int, stride: int) -> list[int]:
    """Fixed starts, stopping at the first window that covers the axis end."""
    if any(
        type(value) is not int or value < 1 for value in (length, chip_size, stride)
    ):
        raise PreparationError(
            "Axis length, chip size and stride must be positive integers."
        )
    if stride > chip_size:
        raise PreparationError("stride must not exceed chip_size.")
    starts = [0]
    while starts[-1] + chip_size < length:
        starts.append(starts[-1] + stride)
    return starts


def chip_windows(width: int, height: int, chip_size: int, stride: int):
    """Yield true-size Rasterio windows without shifting or artificial padding."""
    from rasterio.windows import Window

    rows = axis_starts(height, chip_size, stride)
    cols = axis_starts(width, chip_size, stride)
    for row in rows:
        for col in cols:
            yield Window(
                col, row, min(chip_size, width - col), min(chip_size, height - row)
            )


def read_identities(path: str | Path | None, keys: set[str]) -> dict[str, dict]:
    """One optional CSV schema; joins are exact, never inferred from filenames."""
    if path is None:
        return {key: {} for key in keys}
    records = {}
    try:
        with Path(path).open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames or []
            if (
                "source_key" not in columns
                or len(columns) != len(set(columns))
                or set(columns) - set(IDENTITY_COLUMNS)
            ):
                raise PreparationError(
                    f"Metadata columns must come from {IDENTITY_COLUMNS}."
                )
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise PreparationError("Malformed metadata CSV row.")
                key = row.pop("source_key")
                if not key or key in records:
                    raise PreparationError(
                        f"Missing or duplicate metadata source_key: {key!r}"
                    )
                record = {name: value or None for name, value in row.items()}
                if record.get("acquisition_date"):
                    value = record["acquisition_date"]
                    if date.fromisoformat(value).isoformat() != value:
                        raise PreparationError("acquisition_date must use YYYY-MM-DD.")
                for name in (
                    "row_offset",
                    "col_offset",
                    "original_height",
                    "original_width",
                ):
                    value = record.get(name)
                    if value is not None:
                        record[name] = int(value)
                        minimum = 0 if name.endswith("offset") else 1
                        if record[name] < minimum:
                            raise PreparationError(f"Invalid metadata {name}: {value}")
                records[key] = record
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        raise PreparationError(f"Cannot read identity CSV {path}: {error}") from error
    if records.keys() != keys:
        raise PreparationError(
            "Metadata source_key rows must match selected image keys exactly."
        )
    return records


def _source_record(pair: InputPair, image, identity: dict) -> dict:
    """Keep crop-local metadata and its declared original TIFF placement."""
    record = dict(identity)
    row_offset = record.get("row_offset") or 0
    col_offset = record.get("col_offset") or 0
    for name, offset, size in (
        ("original_height", row_offset, image.height),
        ("original_width", col_offset, image.width),
    ):
        if offset and record.get(name) is None:
            raise PreparationError(f"{pair.key}: cropped inputs need {name}.")
        if record.get(name) is not None and offset + size > record[name]:
            raise PreparationError(f"{pair.key}: crop exceeds {name}.")
        record[name] = record.get(name) or size
    record.update(
        source_key=pair.key,
        source_id=record.get("source_id") or pair.key,
        original_tiff=record.get("original_tiff") or pair.image_relative,
        row_offset=row_offset,
        col_offset=col_offset,
        image=pair.image_relative,
        label=pair.label_relative,
        height=image.height,
        width=image.width,
        crs=str(image.crs),
        transform=list(image.transform)[:6],
    )
    for name in ("dataset_id", "release_id", "region", "acquisition_date"):
        record.setdefault(name, None)
    return record


def _inspect_source(pair: InputPair, recipe: ChipRecipe, identity: dict) -> dict:
    """Check input headers once without reading or realigning pixels."""
    from contextlib import ExitStack

    expectations = CheckRecipe(
        profile="cleaned",
        image_band_counts=(len(recipe.source_band_names),),
        band_names=recipe.source_band_names,
    )
    with ExitStack() as files:
        image = files.enter_context(
            rasterio.open(pair.image, GEOREF_SOURCES="INTERNAL")
        )
        label = (
            files.enter_context(rasterio.open(pair.label, GEOREF_SOURCES="INTERNAL"))
            if pair.label
            else None
        )
        issues = []
        _check_image_header(image, pair, expectations, issues, [])
        if issues:
            raise PreparationError(
                "; ".join(issue.message for issue in issues) + " Use check/clean first."
            )
        if label is not None and (
            label.count != 1
            or label.dtypes != ("uint8",)
            or not same_grid(image, label)
        ):
            raise PreparationError(
                f"{pair.key}: labels must be single-band uint8 on the exact image grid. Use check/clean first."
            )
        return _source_record(pair, image, identity)


def _check_original_identity(source: dict, originals: dict) -> None:
    """Crops of one original must agree after removing their pixel offsets."""
    key = tuple(source[name] for name in ("dataset_id", "release_id", "source_id"))
    metadata = tuple(
        source[name]
        for name in (
            "region",
            "acquisition_date",
            "original_tiff",
            "original_height",
            "original_width",
            "crs",
        )
    )
    original_grid = rasterio.Affine(*source["transform"]) * rasterio.Affine.translation(
        -source["col_offset"], -source["row_offset"]
    )
    if key in originals:
        previous_metadata, previous_grid = originals[key]
        if metadata != previous_metadata or not original_grid.almost_equals(
            previous_grid
        ):
            raise PreparationError(
                f"Conflicting identity metadata or grid for source {key}."
            )
    else:
        originals[key] = (metadata, original_grid)


def build_chip_plan(
    images, labels, output, recipe: ChipRecipe, *, metadata=None
) -> ChipPlan:
    """Inspect selected TIFF headers only; pixel checks happen during writing."""
    validate_chip_recipe(recipe)
    images, output = safe_path(images), safe_path(output)
    labels = safe_path(labels) if labels is not None else None
    roots = [images] + ([labels] if labels is not None else [])
    _check_output_locations(roots, output)
    targets = (output, output.with_name(f".{output.name}.incomplete"))
    if metadata is not None:
        metadata = safe_path(metadata)
        if any(metadata.is_relative_to(target) for target in targets):
            raise PreparationError("Keep metadata outside output directories.")
    for target in targets:
        if target.exists():
            raise PreparationError(
                f"Output already exists; choose a fresh directory: {target}"
            )
    if not output.parent.is_dir():
        raise PreparationError(f"Output parent must exist: {output.parent}")
    pairs = discover_inputs(images, labels)
    identities = read_identities(metadata, {pair.key for pair in pairs})
    if labels is not None and not recipe.label_mapping:
        raise PreparationError("Paired chipping requires an explicit label_mapping.")
    sources, total_windows, source_bytes = [], 0, 0
    originals = {}
    with rasterio.Env(GDAL_PAM_ENABLED="NO"):
        for pair in pairs:
            source = _inspect_source(pair, recipe, identities[pair.key])
            _check_original_identity(source, originals)
            sources.append(source)
            total_windows += len(
                axis_starts(source["height"], recipe.chip_size, recipe.stride)
            ) * len(axis_starts(source["width"], recipe.chip_size, recipe.stride))
            source_bytes += pair.image.stat().st_size
            if pair.label is not None:
                source_bytes += pair.label.stat().st_size
    logger.info(
        "Chip plan: %d sources, %d windows, %d input bytes; output %s",
        len(pairs),
        total_windows,
        source_bytes,
        output,
    )
    return ChipPlan(
        images,
        labels,
        output,
        recipe,
        pairs,
        tuple(sources),
        total_windows,
        source_bytes,
    )
