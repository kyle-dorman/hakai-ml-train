"""Read cleanup settings and plan a separate output before reading any pixels.

The plan checks names, TIFF headers and safe paths. Actual source hashing,
pixel validation and cleanup happen later in ``clean.clean_dataset``.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path

from kelpseg.prepare.check import (
    CheckRecipe,
    InputPair,
    PreparationError,
    check_inputs,
    discover_inputs,
    validate_recipe,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CleanRecipe:
    """Source expectations plus the two choices for writing cleaned rasters."""

    schema_version: int = 1
    image_band_counts: tuple[int, ...] = (8,)
    image_dtypes: tuple[str, ...] = ("uint16",)
    label_values: tuple[int, ...] = (0, 1, 2, 3, 4)
    missing_image_nodata: int | None = None
    band_names: tuple[str, ...] = ()
    block_size: int = 512
    qa_masks: bool = False
    compression: str = "deflate"

    def check_recipe(self, profile: str = "source") -> CheckRecipe:
        """Use the independent checker with the same format expectations."""
        missing_nodata = self.missing_image_nodata
        if profile == "cleaned":
            # Cleaned output must declare nodata=0; a source fallback is no
            # longer acceptable once we have written corrected metadata.
            missing_nodata = None
        return CheckRecipe(
            schema_version=self.schema_version,
            profile=profile,
            image_band_counts=self.image_band_counts,
            image_dtypes=self.image_dtypes,
            label_values=self.label_values,
            missing_image_nodata=missing_nodata,
            band_names=self.band_names,
            block_size=self.block_size,
        )


@dataclass(frozen=True)
class CleanPlan:
    """Resolved input pairs and output location; not yet a verified dataset."""

    images: Path
    labels: Path | None
    output: Path
    recipe: CleanRecipe
    pairs: tuple[InputPair, ...]
    parent: Path | None
    companions: tuple[Path, ...]
    source_bytes: int


def validate_clean_recipe(recipe: CleanRecipe) -> CleanRecipe:
    """Apply shared source checks, then validate cleanup-only settings."""
    validate_recipe(recipe.check_recipe())
    if type(recipe.qa_masks) is not bool:
        raise PreparationError("qa_masks must be true or false.")
    if recipe.compression != "deflate":
        raise PreparationError('compression must be "deflate" (lossless).')
    if 255 in recipe.label_values:
        raise PreparationError("Category 255 is reserved for temporary warp fill.")
    if 3 not in recipe.label_values:
        raise PreparationError("label_values must include cleaned ignore category 3.")
    return recipe


def load_clean_recipe(path: str | Path) -> CleanRecipe:
    """Read exactly the named flat TOML file, with no automatic fallback."""
    logger.info("Reading cleanup recipe: %s", path)
    try:
        values = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        unknown = set(values) - set(CleanRecipe.__dataclass_fields__)
        if unknown:
            raise PreparationError(
                f"Unknown clean settings: {', '.join(sorted(unknown))}"
            )

        # TOML arrays become tuples so the recipe stays immutable while running.
        for name in ("image_band_counts", "image_dtypes", "label_values", "band_names"):
            if name in values:
                if not isinstance(values[name], list):
                    raise PreparationError(f"{name} must be a TOML array.")
                values[name] = tuple(values[name])
        recipe = validate_clean_recipe(CleanRecipe(**values))
    except (OSError, ValueError, TypeError) as error:
        if isinstance(error, PreparationError):
            raise
        raise PreparationError(f"Cannot read clean recipe {path}: {error}") from error

    logger.info(
        "Cleanup settings: bands %s; image dtypes %s; labels %s; block size %d; QA masks %s",
        recipe.image_band_counts,
        recipe.image_dtypes,
        recipe.label_values,
        recipe.block_size,
        recipe.qa_masks,
    )
    return recipe


def safe_path(path: str | Path) -> Path:
    """Resolve a path only after rejecting symlinks in every path component."""
    path = Path(path).expanduser().absolute()
    for part in (path, *path.parents):
        if part.is_symlink():
            raise PreparationError(f"Symlink paths are not supported: {part}")
    return path.resolve()


def _check_output_locations(inputs: list[Path], output: Path) -> None:
    """Keep both final and incomplete output outside all input directories."""
    work = output.with_name(f".{output.name}.incomplete")
    for source in inputs:
        for target in (output, work):
            if source.is_relative_to(target) or target.is_relative_to(source):
                raise PreparationError(f"Input/output overlap: {source} and {target}")


def discover_companions(roots: list[Path], raster_paths: set[Path]) -> tuple[Path, ...]:
    """List other files for later hashing; never use them as masks or metadata.

    Source masks, overviews, XML and other files are preserved at their original
    locations. They must not become active sidecars beside changed rasters.
    """
    companions = set()
    for root in roots:
        for path in root.rglob("*"):
            if path.is_symlink() or (not path.is_file() and not path.is_dir()):
                raise PreparationError(f"Unsafe input asset: {path}")
            if path.is_file() and path not in raster_paths:
                companions.add(path)
    return tuple(sorted(companions))


def build_clean_plan(
    images: str | Path,
    labels: str | Path | None,
    output: str | Path,
    recipe: CleanRecipe,
    *,
    parent: str | Path | None = None,
) -> CleanPlan:
    """Inspect the complete scope without pixels, hashes or output writes."""
    logger.info("Planning cleanup: checking settings and input/output locations")
    validate_clean_recipe(recipe)
    images = safe_path(images)
    output = safe_path(output)
    if labels is not None:
        labels = safe_path(labels)
    if parent is not None:
        parent = safe_path(parent)

    # Treat labels as an optional whole input mode; never silently skip a
    # missing label in a paired dataset.
    input_roots = [images]
    if labels is not None:
        input_roots.append(labels)
    checked_roots = input_roots.copy()
    if parent is not None:
        checked_roots.append(parent)
    _check_output_locations(checked_roots, output)

    logger.info("Discovering complete image/label scope: %s", images)
    pairs = discover_inputs(images, labels)
    logger.info("Checking source headers before cleanup; no pixels or hashes read")
    result = check_inputs(images, labels, recipe.check_recipe())
    fatal_messages = []
    for issue in result.issues:
        if issue.repairable:
            logger.info("Cleanup will repair %s: %s", issue.path, issue.message)
        else:
            fatal_messages.append(issue.message)
    if fatal_messages:
        raise PreparationError("Unsupported input: " + "; ".join(fatal_messages))

    # Raster pairs are the active source data. Everything else is a provenance
    # reference only, including unknown masks and old TIFF sidecars.
    raster_paths = set()
    for pair in pairs:
        raster_paths.add(pair.image)
        if pair.label is not None:
            raster_paths.add(pair.label)

    companion_roots = input_roots
    if parent is not None:
        if images != parent / "images" or labels != parent / "labels":
            raise PreparationError(
                "--parent requires the entire parent's images and labels directories."
            )
        if not (parent / "manifest.json").is_file():
            raise PreparationError("--parent must name a completed organized release.")
        # Planning only lists the parent. Execution will verify its full
        # manifest and hashes before accepting any supplied scientific identity.
        logger.info(
            "Parent provenance requested: %s; hashes will be verified during cleanup",
            parent,
        )
        companion_roots = [parent]
    companions = discover_companions(companion_roots, raster_paths)

    source_bytes = 0
    for path in raster_paths:
        source_bytes += path.stat().st_size
    for path in companions:
        source_bytes += path.stat().st_size
    logger.info(
        "Retaining %d inactive companion/provenance references", len(companions)
    )
    logger.info(
        "Cleanup plan ready: %d sources, %d bytes; output %s; optional QA masks %s",
        len(pairs),
        source_bytes,
        output,
        recipe.qa_masks,
    )
    return CleanPlan(
        images=images,
        labels=labels,
        output=output,
        recipe=recipe,
        pairs=pairs,
        parent=parent,
        companions=companions,
        source_bytes=source_bytes,
    )
