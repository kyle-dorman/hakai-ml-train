"""Read-only checks for ordinary image directories and optional paired labels.

Start at check_inputs(). It discovers files, checks each source, and collects the
report. Format rules live in the two header functions; pixel rules live in
_scan(). These functions report problems. They never repair or rewrite inputs.
"""

from __future__ import annotations

import json
import logging
import math
import os
import tempfile
import time
import tomllib
from contextlib import ExitStack
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


class PreparationError(ValueError):
    """Invalid preparation inputs or an unsafe output request."""


@dataclass(frozen=True)
class CheckRecipe:
    """Supported format and scan size; source and cleaned policies are explicit."""

    schema_version: int = 1
    profile: Literal["source", "cleaned"] = "source"
    image_band_counts: tuple[int, ...] = (8,)
    image_dtypes: tuple[str, ...] = ("uint16",)
    label_values: tuple[int, ...] = (0, 1, 2, 3, 4)
    missing_image_nodata: int | None = None
    band_names: tuple[str, ...] = ()
    block_size: int = 512


@dataclass(frozen=True)
class InputPair:
    """One relative-stem match; the key does not establish region or date."""

    key: str
    image: Path
    label: Path | None
    image_relative: str
    label_relative: str | None


@dataclass(frozen=True)
class CheckIssue:
    code: str
    path: str
    message: str
    repairable: bool = False


@dataclass(frozen=True)
class CheckResult:
    """Evidence for the requested level, with unperformed checks kept explicit."""

    level: str
    profile: str
    source_count: int
    payload_bytes: int
    scanned_image_pixels: int
    scanned_label_pixels: int
    issues: tuple[CheckIssue, ...]
    passed_checks: tuple[str, ...]
    skipped_checks: tuple[str, ...]
    unknowns: tuple[str, ...]
    sources: tuple[dict, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict:
        return {"schema_version": 1, "passed": self.passed, **asdict(self)}


def validate_recipe(recipe: CheckRecipe) -> CheckRecipe:
    """Validate the same schema for TOML and direct Python callers."""
    import numpy as np

    if type(recipe.schema_version) is not int or recipe.schema_version != 1:
        raise PreparationError("Use check schema_version = 1.")
    if not isinstance(recipe.profile, str) or recipe.profile not in {
        "source",
        "cleaned",
    }:
        raise PreparationError("profile must be 'source' or 'cleaned'.")
    for name in ("image_band_counts", "image_dtypes", "label_values", "band_names"):
        if not isinstance(getattr(recipe, name), (tuple, list)):
            raise PreparationError(f"{name} must be an explicit list of values.")
    for name in ("image_band_counts", "label_values"):
        values = getattr(recipe, name)
        if not values or any(type(value) is not int for value in values):
            raise PreparationError(f"{name} must be a nonempty list of integers.")
        if len(values) != len(set(values)):
            raise PreparationError(f"{name} must contain unique values.")
    if any(value < 1 for value in recipe.image_band_counts):
        raise PreparationError("image_band_counts must be positive.")
    if any(value < 0 or value > 255 for value in recipe.label_values):
        raise PreparationError("Supported label_values must be in 0..255.")
    if not recipe.image_dtypes or any(
        not isinstance(value, str) for value in recipe.image_dtypes
    ):
        raise PreparationError("image_dtypes must be a nonempty list of dtype names.")
    for value in recipe.image_dtypes:
        try:
            dtype = np.dtype(value)
        except TypeError as error:
            raise PreparationError(f"Unsupported image dtype {value!r}.") from error
        if dtype.kind not in "uif" or dtype.name != value:
            raise PreparationError(f"Use canonical real image dtype names: {value!r}.")
    if (
        recipe.missing_image_nodata is not None
        and type(recipe.missing_image_nodata) is not int
    ):
        raise PreparationError("missing_image_nodata must be an integer or omitted.")
    if type(recipe.block_size) is not int or not 1 <= recipe.block_size <= 4096:
        raise PreparationError("block_size must be an integer in 1..4096.")
    if any(not isinstance(name, str) or not name for name in recipe.band_names):
        raise PreparationError("band_names must contain nonempty strings.")
    if recipe.band_names and len(recipe.band_names) not in recipe.image_band_counts:
        raise PreparationError("band_names length must be a supported band count.")
    return recipe


def load_check_recipe(path: str | Path) -> CheckRecipe:
    path = Path(path).expanduser().resolve()
    try:
        values = tomllib.loads(path.read_text(encoding="utf-8"))
        unknown = set(values) - set(CheckRecipe.__dataclass_fields__)
        if unknown:
            raise PreparationError(
                f"Unknown check settings: {', '.join(sorted(unknown))}."
            )
        for key in (
            "schema_version",
            "profile",
            "image_band_counts",
            "image_dtypes",
            "label_values",
        ):
            if key not in values:
                raise PreparationError(f"Missing check setting: {key}.")
        for key in ("image_band_counts", "image_dtypes", "label_values", "band_names"):
            if key in values:
                if not isinstance(values[key], list):
                    raise PreparationError(f"{key} must be a TOML array.")
                values[key] = tuple(values[key])
        return validate_recipe(CheckRecipe(**values))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise PreparationError(f"Cannot read check recipe {path}: {error}") from error


def _directory(path: str | Path) -> Path:
    path = Path(path).expanduser().absolute()
    for part in (path, *path.parents):
        if part.is_symlink():
            raise PreparationError(f"Input directory cannot contain a symlink: {part}")
    if not path.is_dir():
        raise PreparationError(f"Select an existing input directory: {path}")
    return path.resolve()


def _tiffs(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    folded: dict[str, str] = {}
    for directory, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            path = Path(directory) / name
            if path.is_symlink():
                raise PreparationError(f"Input symlinks are not supported: {path}")
        for name in sorted(names):
            path = Path(directory) / name
            if path.suffix.casefold() not in {".tif", ".tiff"}:
                continue
            key = path.relative_to(root).with_suffix("").as_posix()
            if key.casefold() in folded:
                raise PreparationError(
                    f"Duplicate/case-folded TIFF stem {key!r} and {folded[key.casefold()]!r} in {root}."
                )
            files[key] = path
            folded[key.casefold()] = key
    return files


def discover_inputs(images: Path, labels: Path | None = None) -> tuple[InputPair, ...]:
    """Pair by exact relative TIFF stem; suffix spelling may differ, case may not."""
    image_root = _directory(images)
    label_root = _directory(labels) if labels is not None else None
    if label_root is not None and (
        image_root.is_relative_to(label_root) or label_root.is_relative_to(image_root)
    ):
        raise PreparationError("Image and label directories must not overlap.")
    image_files = _tiffs(image_root)
    label_files = _tiffs(label_root) if label_root is not None else {}
    if not image_files:
        raise PreparationError(f"No image TIFFs found in {image_root}.")
    if label_root is not None and image_files.keys() != label_files.keys():
        missing = sorted(image_files.keys() - label_files.keys())
        extra = sorted(label_files.keys() - image_files.keys())
        raise PreparationError(
            f"Image/label relative TIFF stems must match exactly. Missing labels: {missing[:5]}; extra labels: {extra[:5]}. Omit --labels only for an entirely image-only input."
        )
    pairs = []
    for key, image in sorted(image_files.items()):
        label = label_files.get(key)
        label_relative = None
        if label is not None:
            label_relative = label.relative_to(label_root).as_posix()
        pairs.append(
            InputPair(
                key=key,
                image=image,
                label=label,
                image_relative=image.relative_to(image_root).as_posix(),
                label_relative=label_relative,
            )
        )
    logger.info(
        "Discovered %d image TIFFs and %d paired labels under %s",
        len(pairs),
        len(label_files),
        image_root,
    )
    return tuple(pairs)


def windows(width: int, height: int, block_size: int):
    """Cover every selected pixel once, including partial right/bottom edges."""
    from rasterio.windows import Window

    for row in range(0, height, block_size):
        for column in range(0, width, block_size):
            yield Window(
                column,
                row,
                min(block_size, width - column),
                min(block_size, height - row),
            )


def same_grid(image, label) -> bool:
    return (
        image.width == label.width
        and image.height == label.height
        and image.crs == label.crs
        and image.transform == label.transform
    )


def _header(dataset) -> dict:
    return {
        "width": dataset.width,
        "height": dataset.height,
        "count": dataset.count,
        "dtypes": list(dataset.dtypes),
        "crs": str(dataset.crs) if dataset.crs else None,
        "transform": [
            value if math.isfinite(value) else str(value)
            for value in list(dataset.transform)[:6]
        ],
        "nodata": [
            value if value is None or math.isfinite(value) else str(value)
            for value in dataset.nodatavals
        ],
        "band_names": list(dataset.descriptions),
    }


def _atomic_report(path: Path, result: CheckResult, roots: list[Path]) -> None:
    path = path.expanduser().absolute()
    if any(path.resolve().is_relative_to(root.resolve()) for root in roots):
        raise PreparationError("Place --report outside input directories.")
    if path.exists() or path.is_symlink():
        raise PreparationError(
            f"Report already exists; choose a fresh filename: {path}"
        )
    if not path.parent.is_dir():
        raise PreparationError(f"Report parent must exist: {path.parent}")
    descriptor, filename = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(filename)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(
                result.to_dict(), stream, indent=2, sort_keys=True, allow_nan=False
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # link publishes atomically and refuses a concurrently created destination.
        os.link(temporary, path)
    except OSError as error:
        raise PreparationError(f"Cannot publish report {path}: {error}") from error
    finally:
        temporary.unlink(missing_ok=True)


def check_inputs(
    images: Path,
    labels: Path | None,
    recipe: CheckRecipe,
    *,
    full: bool = False,
    report: Path | None = None,
) -> CheckResult:
    """Check the whole directory scope without changing any input.

    A quick check reads headers only. A full check also reads every native image
    and label pixel. Neither kind calculates file hashes. The source profile
    reports repairable problems as failures; the cleaner decides which repairs
    to apply and independently checks its finished output with the cleaned profile.
    """
    import rasterio

    validate_recipe(recipe)
    pairs = discover_inputs(images, labels)
    roots = [_directory(images)]
    if labels is not None:
        roots.append(_directory(labels))

    # Refuse a report conflict before starting a potentially expensive scan.
    if report is not None:
        destination = Path(report).expanduser().absolute()
        if destination.exists() or destination.is_symlink():
            raise PreparationError(
                f"Report already exists; choose a fresh filename: {destination}"
            )
        if any(destination.resolve().is_relative_to(root) for root in roots):
            raise PreparationError("Place --report outside input directories.")

    payload_bytes = 0
    for pair in pairs:
        payload_bytes += pair.image.stat().st_size
        if pair.label is not None:
            payload_bytes += pair.label.stat().st_size
    logger.info(
        "%s check: %d sources, %d payload bytes; %s",
        "Full" if full else "Quick",
        len(pairs),
        payload_bytes,
        "all native pixels; large mosaics may be expensive"
        if full
        else "headers only; pixels and hashes not checked",
    )

    issues: list[CheckIssue] = []
    unknowns = [
        "Directory names do not establish region or acquisition date.",
        "File checksum identities were not checked.",
    ]
    skipped = []
    if not full:
        skipped = ["pixel decodability", "label vocabulary", "pixel nodata consistency"]
    sources = []
    image_pixels = 0
    label_pixels = 0

    # PAM sidecars must not override the TIFF's own grid or nodata declaration.
    # Each source is opened and closed independently, keeping memory use bounded.
    with rasterio.Env(GDAL_PAM_ENABLED="NO"):
        for number, pair in enumerate(pairs, 1):
            logger.info("Checking %d/%d: %s", number, len(pairs), pair.key)
            before_issues = len(issues)
            record, image_count, label_count = _check_source(
                pair, recipe, full, issues, unknowns, skipped
            )
            sources.append(record)
            image_pixels += image_count
            label_pixels += label_count
            logger.info(
                "Finished %s: %d image pixels and %d label pixels scanned; %d issues",
                pair.key,
                image_count,
                label_count,
                len(issues) - before_issues,
            )
            if full and any(not issue.repairable for issue in issues[before_issues:]):
                # A full scan stops at a failure. Its report states the actual
                # completed scope instead of pretending later files were read.
                if number < len(pairs):
                    skipped.append("remaining sources skipped after failure")
                break

    passed_checks = ["complete directory enumeration and exact relative-stem pairing"]
    if len(sources) == len(pairs) and not any(
        item.code.endswith("read") for item in issues
    ):
        passed_checks.append("all selected raster headers readable")
        if full and all("pixel_counts" in record for record in sources):
            passed_checks.append("all selected native image and label pixels decoded")
    if not issues:
        passed_checks.append(
            f"requested {'full' if full else 'quick'} {recipe.profile} expectations"
        )
    if labels is None:
        skipped.append("paired label/grid/coverage checks (image-only mode)")

    result = CheckResult(
        level="full" if full else "quick",
        profile=recipe.profile,
        source_count=len(pairs),
        payload_bytes=payload_bytes,
        scanned_image_pixels=image_pixels,
        scanned_label_pixels=label_pixels,
        issues=tuple(issues),
        passed_checks=tuple(passed_checks),
        skipped_checks=tuple(skipped),
        unknowns=tuple(unknowns),
        sources=tuple(sources),
    )
    if report is not None:
        _atomic_report(Path(report), result, roots)
        logger.info("Saved check report: %s", Path(report).expanduser().absolute())
    logger.info(
        "Check %s: %d sources; scanned %d image and %d label pixels; %d issues",
        "passed" if result.passed else "failed",
        len(pairs),
        image_pixels,
        label_pixels,
        len(issues),
    )
    return result


def _add_issue(issues, code, path, message, repairable=False):
    """Keep a report finding and explain the same finding in the progress log."""
    issues.append(CheckIssue(code, str(path), message, repairable))
    kind = "Repairable" if repairable else "Unsupported"
    logger.warning("%s: %s: %s", kind, path, message)


def _check_source(pair, recipe, full, issues, unknowns, skipped):
    """Check one source in order. Failed reads are never retried or worked around."""
    import rasterio

    record = {
        "key": pair.key,
        "image": str(pair.image),
        "label": str(pair.label) if pair.label else None,
        "region": None,
        "acquisition_date": None,
    }
    image_count = label_count = 0
    issue_start = len(issues)
    reading, code = pair.image, "image_read"
    with ExitStack() as files:
        try:
            image = files.enter_context(
                rasterio.open(pair.image, GEOREF_SOURCES="INTERNAL")
            )
            record["image_header"] = _header(image)
            nodata_values = _check_image_header(image, pair, recipe, issues, unknowns)
            label = None
            aligned = False
            if pair.label is not None:
                reading, code = pair.label, "label_read"
                label = files.enter_context(
                    rasterio.open(pair.label, GEOREF_SOURCES="INTERNAL")
                )
                record["label_header"] = _header(label)
                aligned = _check_label_header(image, label, pair, recipe, issues)
                if not aligned:
                    skipped.append(
                        f"{pair.key}: paired pixel consistency (different grids)"
                    )
            if full:
                # Header failures make pixel scanning inappropriate. Repairable
                # source metadata/grid findings can still receive a full audit.
                if any(not issue.repairable for issue in issues[issue_start:]):
                    skipped.append(
                        f"{pair.key}: pixel scan skipped after unsupported headers"
                    )
                else:
                    reading, code = pair.image, "pixel_read"
                    image_count, label_count, record["pixel_counts"] = _scan(
                        image, label, nodata_values, aligned, recipe, pair, issues
                    )
        except rasterio.errors.RasterioError as error:
            _add_issue(
                issues,
                code,
                reading,
                f"Cannot read selected source: {error}; restore or replace the source.",
            )
            skipped.append(f"{pair.key}: stopped after read failure; no scan retry")
            if code == "pixel_read":
                skipped.append(
                    f"{pair.key}: partial read counts unavailable; counts cover completed scans only"
                )
    return record, image_count, label_count


def _check_image_header(image, pair, recipe, issues, unknowns):
    """Check bands, grid and original nodata without reading image arrays."""
    from kelpseg.prepare.nodata import declared_nodata_values

    logger.info(
        "Image header: %s; %d x %d pixels, %d bands, dtypes %s",
        pair.image,
        image.width,
        image.height,
        image.count,
        image.dtypes,
    )
    if image.count not in recipe.image_band_counts:
        _add_issue(
            issues,
            "image_bands",
            pair.image,
            f"Expected bands {recipe.image_band_counts}, found {image.count}; select a supported recipe.",
        )
    if any(dtype not in recipe.image_dtypes for dtype in image.dtypes):
        _add_issue(
            issues,
            "image_dtype",
            pair.image,
            f"Expected dtypes {recipe.image_dtypes}, found {image.dtypes}.",
        )
    _check_grid(image, pair.image, issues)

    # Eight channels alone do not prove which physical bands they represent.
    names = image.descriptions
    known_names = all(name and not name.lower().startswith("band_") for name in names)
    if not known_names:
        unknowns.append(
            f"{pair.key}: physical band names/order unestablished; channel count alone is insufficient."
        )
        logger.info(
            "Band identity: %s has no established physical band names", pair.key
        )
    elif recipe.band_names and tuple(names) != recipe.band_names:
        _add_issue(
            issues,
            "band_names",
            pair.image,
            f"Header band names {names} differ from expected {recipe.band_names}.",
        )

    # A missing source declaration may use only the recipe's explicit fallback.
    # Cleaned data must declare zero; they never inherit a source fallback.
    fallback = recipe.missing_image_nodata if recipe.profile == "source" else None
    nodata_values = None
    try:
        nodata_values = declared_nodata_values(
            image, retained_bands=image.count, missing_value=fallback
        )
        if all(value is None for value in image.nodatavals):
            logger.info(
                "Image nodata: %s uses explicit recipe fallback %s", pair.key, fallback
            )
        else:
            logger.info("Image nodata: %s declares %s", pair.key, nodata_values[0])
    except (RuntimeError, ValueError, OverflowError) as error:
        _add_issue(
            issues,
            "image_nodata_declaration",
            pair.image,
            f"{error}. Supply an explicit supported missing-nodata policy if appropriate.",
        )
    if recipe.profile == "cleaned" and image.nodatavals != (0,) * image.count:
        _add_issue(
            issues,
            "cleaned_image_nodata",
            pair.image,
            "Cleaned imagery must declare nodata=0 in every band; rerun clean from unchanged sources.",
        )
    return nodata_values


def _check_label_header(image, label, pair, recipe, issues):
    """Check categorical label metadata and return whether the grids match."""
    import numpy as np

    logger.info(
        "Label header: %s; %d x %d pixels, %d bands, dtypes %s",
        pair.label,
        label.width,
        label.height,
        label.count,
        label.dtypes,
    )
    _check_grid(label, pair.label, issues)
    if label.count != 1:
        _add_issue(
            issues,
            "label_bands",
            pair.label,
            "Categorical labels require exactly one band.",
        )
    if np.dtype(label.dtypes[0]).kind not in "ui":
        _add_issue(
            issues,
            "label_dtype",
            pair.label,
            "Categorical labels require an integer dtype.",
        )
    if recipe.profile == "cleaned" and label.dtypes != ("uint8",):
        _add_issue(
            issues,
            "cleaned_label_dtype",
            pair.label,
            "Cleaned categorical labels must use uint8; rerun clean from unchanged sources.",
        )

    if recipe.profile == "source":
        from kelpseg.prepare.alignment import validate_alignment

        try:
            validate_alignment(image, label)
        except ValueError as error:
            _add_issue(issues, "unsupported_alignment", pair.label, str(error))

    # Alignment and misleading nodata metadata can be repaired for source data.
    # The same findings are unsupported in a supposedly finished cleaned release.
    repairable = recipe.profile == "source"
    aligned = same_grid(image, label)
    if not aligned:
        _add_issue(
            issues,
            "pair_grid",
            pair.label,
            "Label grid differs from image; use clean to nearest-align stored categories.",
            repairable,
        )
    if label.nodatavals != (3,):
        _add_issue(
            issues,
            "label_nodata_declaration",
            pair.label,
            "Label nodata metadata must be 3; stored class 0 is valid background. Use clean to write corrected metadata.",
            repairable,
        )
    return aligned


def _check_grid(dataset, path, issues):
    """Reject unknown or unusable geographic coordinates; never guess a CRS."""
    if dataset.crs is None:
        _add_issue(
            issues,
            "missing_crs",
            path,
            "Raster has no CRS; establish the actual source CRS before preparation.",
        )
    transform = dataset.transform
    if (
        not all(math.isfinite(value) for value in tuple(transform))
        or transform.determinant == 0
    ):
        _add_issue(
            issues,
            "invalid_transform",
            path,
            "Raster affine transform must be finite and invertible.",
        )
    if dataset.width < 1 or dataset.height < 1:
        _add_issue(issues, "empty_grid", path, "Raster dimensions must be positive.")


def _scan(image, label, nodata_values, aligned, recipe, pair, issues):
    """Read every selected native pixel, without applying nodata masks or overviews."""
    import numpy as np

    from kelpseg.prepare.nodata import nodata_mask

    image_pixels = 0
    label_pixels = 0
    logger.info(
        "Scanning image pixels: %s; %d total, windows up to %d x %d",
        pair.image,
        image.width * image.height,
        recipe.block_size,
        recipe.block_size,
    )
    counts = {
        "image_nodata": 0,
        "image_nodata_label_not_ignore": 0,
        "nonfinite_image_values": 0,
    }
    label_values = set()
    last_progress = time.monotonic()
    for window in windows(image.width, image.height, recipe.block_size):
        # Read stored values rather than Rasterio masked arrays. The all-band
        # nodata rule is applied explicitly below; one zero band can still be valid.
        block = image.read(window=window, masked=False)
        image_pixels += int(window.width * window.height)
        # Integer rasters cannot contain NaN/inf. Do not allocate a full-band
        # finite-value mask for the ordinary uint16 Planet imagery.
        if block.dtype.kind == "f":
            counts["nonfinite_image_values"] += int(
                np.count_nonzero(~np.isfinite(block))
            )
        missing = (
            nodata_mask(block, nodata_values, band_axis=0)
            if nodata_values is not None
            else None
        )
        if missing is not None:
            counts["image_nodata"] += int(np.count_nonzero(missing))
        if label is not None and aligned:
            # Stored label zero remains water even when metadata says nodata=0.
            categories = label.read(window=window, masked=False)
            label_pixels += int(window.width * window.height)
            label_values.update(value.item() for value in np.unique(categories))
            if missing is not None and label.count == 1:
                counts["image_nodata_label_not_ignore"] += int(
                    np.count_nonzero(missing & (categories[0] != 3))
                )
        if time.monotonic() - last_progress >= 10:
            logger.info(
                "Scanning %s: %d/%d image pixels",
                pair.key,
                image_pixels,
                image.width * image.height,
            )
            last_progress = time.monotonic()
    if label is not None and not aligned:
        # A mismatched label may be a whole regional mosaic. Scan that native
        # grid completely; do not pretend its image-sized crop is a full check.
        logger.info(
            "Scanning native label pixels: %s; %d total",
            pair.label,
            label.width * label.height,
        )
        for window in windows(label.width, label.height, recipe.block_size):
            categories = label.read(window=window, masked=False)
            label_pixels += int(window.width * window.height)
            label_values.update(value.item() for value in np.unique(categories))
            if time.monotonic() - last_progress >= 10:
                logger.info(
                    "Scanning %s labels: %d/%d pixels",
                    pair.key,
                    label_pixels,
                    label.width * label.height,
                )
                last_progress = time.monotonic()
    if counts["nonfinite_image_values"]:
        _add_issue(
            issues,
            "nonfinite_image",
            pair.image,
            f"Image contains {counts['nonfinite_image_values']} nonfinite values.",
        )
    unsupported = label_values - set(recipe.label_values)
    if unsupported:
        _add_issue(
            issues,
            "label_values",
            pair.label,
            f"Unsupported stored label values {sorted(unsupported)}; establish category meanings and select an explicit supported recipe.",
        )
    if counts["image_nodata_label_not_ignore"]:
        _add_issue(
            issues,
            "paired_nodata",
            pair.label,
            f"{counts['image_nodata_label_not_ignore']} image-nodata pixels have labels other than 3; use clean from source inputs.",
            recipe.profile == "source",
        )
    counts["label_values"] = [
        value if math.isfinite(value) else str(value) for value in sorted(label_values)
    ]
    return image_pixels, label_pixels, counts
