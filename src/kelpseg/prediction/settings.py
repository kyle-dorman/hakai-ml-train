"""Read explicit prediction settings and validate source TIFF headers once."""

from __future__ import annotations

import csv
import math
import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path

import rasterio

from kelpseg.bands import resolve_band_indices
from kelpseg.paths import _resolve_path
from kelpseg.preprocessing import BAND_NAMES

IDENTITY_COLUMNS = (
    "dataset_id",
    "release_id",
    "region_id",
    "acquisition_date",
    "original_source_id",
    "row_offset",
    "col_offset",
)


@dataclass(frozen=True)
class PredictionSettings:
    """Resolved paths and ordinary execution settings for one prediction run."""

    model: Path
    manifest: Path
    image_root: Path
    output: Path
    stride: int = 256
    min_valid_fraction: float = 0.20
    batch_size: int = 1
    device: str = "cpu"

    def __post_init__(self) -> None:
        """Validate ordinary settings for recipe and Python callers alike."""
        if type(self.stride) is not int or not 1 <= self.stride <= 512:
            raise ValueError("stride must be an integer in 1..512.")
        if (
            type(self.min_valid_fraction) not in (int, float)
            or not 0 <= self.min_valid_fraction <= 1
        ):
            raise ValueError("min_valid_fraction must be a number in 0..1.")
        if type(self.batch_size) is not int or self.batch_size < 1:
            raise ValueError("batch_size must be a positive integer.")
        if self.device not in ("cpu", "cuda"):
            raise ValueError("device must be cpu or cuda.")


@dataclass(frozen=True)
class Source:
    """One explicitly named image and its optional scientific identity fields."""

    source_key: str
    image: Path
    band_names: tuple[str, ...]
    identity: dict[str, str]


def load_settings(recipe: str | Path) -> PredictionSettings:
    """Load a flat TOML recipe; resolve paths against its containing directory."""
    recipe = Path(recipe).expanduser().resolve()
    values = tomllib.loads(recipe.read_text(encoding="utf-8"))
    unknown = values.keys() - {field.name for field in fields(PredictionSettings)}
    if unknown:
        raise ValueError(f"Unknown prediction settings: {', '.join(sorted(unknown))}.")
    for key in ("model", "manifest", "image_root", "output"):
        value = values.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a nonempty path in the prediction recipe.")
        values[key] = _resolve_path(value, base=recipe.parent, context=key)
    settings = PredictionSettings(**values)
    return settings


def _check_header(image: Path, names: tuple[str, ...]) -> None:
    """Check cleaned input dtype, nodata and spatial metadata without pixel reads."""
    with rasterio.open(image, GEOREF_SOURCES="INTERNAL") as dataset:
        if dataset.driver != "GTiff" or any(
            dtype != "uint16" for dtype in dataset.dtypes
        ):
            raise ValueError(
                f"{image}: use a cleaned uint16 GeoTIFF; run check/clean first."
            )
        if dataset.count != len(names):
            raise ValueError(
                f"{image}: band_names must declare every native TIFF band."
            )
        if any(value != 0 for value in dataset.nodatavals):
            raise ValueError(
                f"{image}: cleaned imagery must declare nodata=0 (all native bands zero); "
                "run check/clean first."
            )
        transform = dataset.transform
        if (
            dataset.crs is None
            or transform.is_identity
            or not all(math.isfinite(value) for value in transform)
            or transform.determinant == 0
        ):
            raise ValueError(
                f"{image}: provide a TIFF with usable internal CRS/transform."
            )


def read_sources(
    settings: PredictionSettings, model_band_names: Sequence[str]
) -> list[Source]:
    """Read the source CSV, validate identities and headers, and never read labels."""
    sources = []
    keys: dict[str, str] = {}
    images: set[Path] = set()
    required = {"source_key", "image", "band_names"}
    with settings.manifest.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not required.issubset(fields):
            raise ValueError(
                "Prediction CSV needs unique source_key, image and band_names columns."
            )
        unknown = set(fields) - required - set(IDENTITY_COLUMNS)
        if unknown:
            raise ValueError(
                f"Unknown prediction CSV columns: {', '.join(sorted(unknown))}."
            )
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(
                    f"Prediction CSV line {line}: field count differs from header."
                )
            key = row["source_key"].strip()
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", key):
                raise ValueError(
                    f"Invalid source_key {key!r}; use letters, digits, _, - or ."
                )
            if key.casefold() in keys:
                raise ValueError(
                    f"Duplicate source_key: {key!r} conflicts with "
                    f"{keys[key.casefold()]!r}. Keys must be unique ignoring case "
                    "so output filenames remain distinct on every supported machine."
                )
            if not row["image"].strip():
                raise ValueError(f"{key}: image must be a nonempty TIFF path.")
            image = _resolve_path(row["image"], base=settings.image_root, context=key)
            if image in images:
                raise ValueError(f"Duplicate image path: {image}.")
            names = tuple(name.strip() for name in row["band_names"].split(";"))
            try:
                resolve_band_indices(BAND_NAMES, names)
                resolve_band_indices(names, tuple(model_band_names))
            except ValueError as error:
                raise ValueError(
                    f"Prediction CSV line {line}, source {key!r}: {error}"
                ) from error
            identity = {
                column: row.get(column, "").strip() for column in IDENTITY_COLUMNS
            }
            if identity["acquisition_date"]:
                try:
                    date.fromisoformat(identity["acquisition_date"])
                except ValueError as error:
                    raise ValueError(
                        f"Prediction CSV line {line}, source {key!r}: "
                        "acquisition_date must be a valid YYYY-MM-DD date."
                    ) from error
            for column in ("row_offset", "col_offset"):
                if identity[column] and not identity[column].isdigit():
                    raise ValueError(
                        f"{key}: {column} must be a nonnegative integer or blank."
                    )
            _check_header(image, names)
            sources.append(Source(key, image, names, identity))
            keys[key.casefold()] = key
            images.add(image)
    if not sources:
        raise ValueError("Prediction CSV has no sources; add at least one image row.")
    return sources
