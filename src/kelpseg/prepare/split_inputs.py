"""Read plain split recipes and source controls without opening imagery."""

from __future__ import annotations

import csv
import json
import logging
import re
import tomllib
from datetime import date
from pathlib import Path

from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.chip_inputs import IDENTITY_COLUMNS

logger = logging.getLogger(__name__)
# The chipper keeps the same identity columns; only splitting needs spacecraft.
COLLECTION_COLUMNS = (*IDENTITY_COLUMNS, "satellite_id")
ORIGINAL_COLUMNS = (
    "dataset_id",
    "release_id",
    "source_id",
    "region",
    "acquisition_date",
    "satellite_id",
)


def original_key(row: dict) -> tuple[str, str, str]:
    return tuple(row[name] for name in ("dataset_id", "release_id", "source_id"))


def _iso_date(value: str) -> str:
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Dates must use YYYY-MM-DD.")
    return value


def load_split_recipe(path: str | Path) -> dict:
    """One flat schema: inclusive cutoffs and optional training regions."""
    logger.info("Reading split recipe: %s", Path(path).resolve())
    try:
        values = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        expected = {"schema_version", "training_only_regions", "regions"}
        unknown, missing = set(values) - expected, expected - set(values)
        if unknown or missing:
            raise ValueError(
                f"Split recipe keys: unknown {sorted(unknown)}; missing {sorted(missing)}."
            )
        if type(values["schema_version"]) is not int or values["schema_version"] != 1:
            raise ValueError("Use split schema_version = 1.")
        optional = values["training_only_regions"]
        if (
            not isinstance(optional, list)
            or any(
                not isinstance(region, str) or not region.strip() for region in optional
            )
            or len(optional) != len(set(optional))
        ):
            raise ValueError("training_only_regions must list distinct region strings.")
        if not isinstance(values["regions"], list):
            raise ValueError("Declare [[regions]] rules.")
        seen = set(optional)
        for number, rule in enumerate(values["regions"], 1):
            if not isinstance(rule, dict):
                raise ValueError(f"Region rule {number} must be a [[regions]] table.")
            context = f"Region rule {number} ({rule.get('region', 'missing region')!r})"
            expected = {"region", "direction", "first_cutoff", "second_cutoff"}
            unknown, missing = set(rule) - expected, expected - set(rule)
            if unknown or missing:
                raise ValueError(
                    f"{context}: unknown {sorted(unknown)}; missing {sorted(missing)}."
                )
            region = rule["region"]
            if not isinstance(region, str) or not region.strip() or region in seen:
                raise ValueError(
                    f"{context}: region must be a nonempty string distinct from other rules and training-only regions."
                )
            seen.add(region)
            if rule["direction"] not in ("forward", "reverse"):
                raise ValueError(f"{context}: direction must be forward or reverse.")
            # ISO dates sort chronologically; both boundaries are inclusive.
            for name in ("first_cutoff", "second_cutoff"):
                try:
                    _iso_date(rule[name])
                except (ValueError, TypeError) as error:
                    raise ValueError(f"{context}, {name}: {error}") from error
            first, second = rule["first_cutoff"], rule["second_cutoff"]
            if first >= second:
                raise ValueError(f"{context}: first_cutoff must precede second_cutoff.")
        logger.info(
            "Split recipe loaded: %d evaluation-region rules; training-only regions %s",
            len(values["regions"]),
            optional,
        )
        return values
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise PreparationError(f"Cannot read split recipe {path}: {error}") from error


def satellite_from_source(
    source_id: str, acquisition_date: str, declared: str = ""
) -> str:
    """Planet original IDs, including subsecond BC names; never parse crop keys."""
    # Optional subsecond and clip tokens belong to BC original IDs. Crop keys
    # are separate metadata and never enter this spacecraft extraction.
    match = re.fullmatch(
        r"\d{3}_(\d{8})_\d{6}(?:_\d{2})?_([0-9a-fA-F]{3,4})(?:_clip\d+)?",
        source_id,
    )
    if match is None and declared:
        return declared
    if match is None:
        raise PreparationError(
            f"{source_id}: supply explicit satellite_id for this source convention."
        )
    if match[1] != acquisition_date.replace("-", ""):
        raise PreparationError(
            f"{source_id}: acquisition_date disagrees with original source ID."
        )
    inferred = match[2].lower()
    if declared and len(inferred) == 4 and declared != inferred:
        raise PreparationError(
            f"{source_id}: satellite_id disagrees with original source ID."
        )
    return declared or inferred


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        unknown = set(columns) - set(COLLECTION_COLUMNS)
        duplicates = {name for name in columns if columns.count(name) > 1}
        if unknown or duplicates:
            raise PreparationError(
                f"Source CSV columns: unknown {sorted(unknown)}; duplicate {sorted(duplicates)}."
            )
        rows = []
        for number, row in enumerate(reader, 2):
            if None in row or None in row.values():
                raise PreparationError(
                    f"Source row {number} ({row.get('source_key', '')!r}): CSV field count differs from the header."
                )
            rows.append(row)
        return rows


def _cleaned_rows(root: Path, release_id: str) -> list[dict]:
    controls = json.loads((root / "sources.json").read_text(encoding="utf-8"))
    rows = []
    for source in controls["sources"]:
        identity = source["identity"]
        images = [
            name
            for name in source["files"]
            if name.startswith("images/")
            and Path(name).suffix.lower() in (".tif", ".tiff")
        ]
        if len(images) != 1:
            raise PreparationError(
                f"{source['key']}: expected one cleaned image reference."
            )
        # The organizer's shorter source_key is not the chip image key.
        # Use the actual cleaned image reference, retaining its region prefix.
        image = Path(images[0])
        header = source["output_headers"]["image"]
        rows.append(
            dict(
                source_key=image.relative_to("images").with_suffix("").as_posix(),
                source_id=identity["source_id"],
                original_tiff=image.name,
                dataset_id=identity["dataset_id"],
                release_id=release_id,
                region=identity["region_code"],
                acquisition_date=identity["acquisition_date"],
                row_offset=0,
                col_offset=0,
                original_height=header["height"],
                original_width=header["width"],
            )
        )
    return rows


def _normalize_source_row(raw: dict) -> dict:
    """Convert one row; collection-wide duplicate and alias checks run below."""
    # Preserve region strings (including leading zeros) and the chipper's schema.
    row = {name: raw.get(name, "") or "" for name in COLLECTION_COLUMNS}
    for name in (
        "source_key",
        "dataset_id",
        "release_id",
        "source_id",
        "region",
        "acquisition_date",
    ):
        if not isinstance(row[name], str) or not row[name].strip():
            raise PreparationError(f"Source rows need nonempty {name}.")
    for name in ("source_key", "original_tiff"):
        if Path(row[name]).is_absolute():
            raise PreparationError(f"{name} must be a portable relative reference.")
    try:
        _iso_date(row["acquisition_date"])
        for name in (
            "row_offset",
            "col_offset",
            "original_height",
            "original_width",
        ):
            if row[name] != "":
                row[name] = int(row[name])
                if row[name] < (0 if name.endswith("offset") else 1):
                    raise ValueError(f"Invalid {name}.")
        for axis in ("row", "col"):
            row[f"{axis}_offset"] = row[f"{axis}_offset"] or 0
        for axis, dimension in (("row", "height"), ("col", "width")):
            if row[f"{axis}_offset"] and not row[f"original_{dimension}"]:
                raise ValueError(f"Cropped sources need original_{dimension}.")
    except (ValueError, TypeError) as error:
        raise PreparationError(f"{row['source_key']}: {error}") from error
    if not isinstance(row["satellite_id"], str):
        raise PreparationError("satellite_id must be a string.")
    row["satellite_id"] = satellite_from_source(
        row["source_id"],
        row["acquisition_date"],
        row["satellite_id"].strip().lower(),
    )
    return row


def normalize_collection(rows: list[dict]) -> list[dict]:
    """Normalize once; validate keys, shared originals and known declared aliases."""
    logger.info(
        "Normalizing %d source rows and checking original identities", len(rows)
    )
    result, keys, originals, aliases = [], set(), {}, {}
    # Count the header as row 1 so errors point to the researcher's source CSV.
    for number, raw in enumerate(rows, 2):
        identity = raw.get("source_key") or raw.get("source_id") or "missing identity"
        context = f"Source row {number} ({identity!r})"
        try:
            row = _normalize_source_row(raw)
        except (ValueError, TypeError) as error:
            raise PreparationError(f"{context}: {error}") from error
        key = row["source_key"]
        if key in keys:
            raise PreparationError(f"{context}: duplicate source_key {key!r}.")
        keys.add(key)
        original = original_key(row)
        # Different crops may have different offsets, but their original
        # region/date, spacecraft and dimensions must describe the same TIFF.
        metadata = tuple(
            row[name]
            for name in (
                *ORIGINAL_COLUMNS[3:],
                "original_tiff",
                "original_height",
                "original_width",
            )
        )
        if original in originals and originals[original] != metadata:
            raise PreparationError(
                f"{context}: conflicting original identity {original}."
            )
        originals[original] = metadata
        # A repeated original in a second release, or a declared TIFF under two
        # IDs in one release, is a known alias rather than independent imagery.
        references = [(row["dataset_id"], "source_id", row["source_id"])]
        if row["original_tiff"]:
            references.append(
                (row["dataset_id"], row["release_id"], row["original_tiff"])
            )
        for reference in references:
            if reference in aliases and aliases[reference] != original:
                raise PreparationError(f"{context}: known duplicate alias {reference}.")
            aliases[reference] = original
        result.append(row)
        completed = number - 1
        if completed % 100 == 0 or completed == len(rows):
            logger.info(
                "Source rows %d/%d: %s; %d originals",
                completed,
                len(rows),
                key,
                len(originals),
            )
    if not result:
        raise PreparationError("Select at least one source row.")
    logger.info(
        "Collection ready: %d original sources, %d crop rows, %d regions",
        len(originals),
        len(result),
        len({row["region"] for row in result}),
    )
    return sorted(result, key=lambda row: (*original_key(row), row["source_key"]))


def read_collection(*, cleaned=None, release_id=None, sources=None) -> list[dict]:
    """Read trusted cleaned controls OR a declared CSV; no image or label reads."""
    if (cleaned is None) == (sources is None) or (cleaned is not None) != (
        release_id is not None
    ):
        raise PreparationError("Use --cleaned with --release-id, or --sources alone.")
    control = Path(cleaned) / "sources.json" if cleaned is not None else Path(sources)
    try:
        logger.info(
            "Reading source controls: %s (%d bytes)",
            control.resolve(),
            control.stat().st_size,
        )
        rows = (
            _cleaned_rows(Path(cleaned), release_id)
            if cleaned is not None
            else _read_csv(Path(sources))
        )
        logger.info("Read %d source rows from %s", len(rows), control.name)
        return normalize_collection(rows)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, csv.Error) as error:
        raise PreparationError(
            f"Cannot read source controls {control}: {error}"
        ) from error
