"""Clean a fresh output in one pass; failed attempts are never resumed.

``clean_dataset`` checks inputs, writes separate rasters, verifies them and
publishes once. ``_write_cleaned_windows`` contains the scientific pixel rules.
An interrupted job leaves its incomplete directory for the researcher to inspect.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import platform
import time
from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import numpy as np
import rasterio

from kelpseg.prepare.alignment import (
    aligned_label,
    audit_label_block,
    repair_label_block,
)
from kelpseg.prepare.check import (
    PreparationError,
    check_inputs,
    discover_inputs,
    same_grid,
    windows,
)
from kelpseg.prepare.clean_inputs import CleanPlan, discover_companions
from kelpseg.prepare.nodata import declared_nodata_values, nodata_mask
from kelpseg.prepare.organize import _hash, _inventory, verify_organized_release

logger = logging.getLogger(__name__)


def _write_record(path: Path, value: object) -> None:
    """Write one new record inside the private, incomplete output directory."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _file_record(path: Path) -> dict:
    """Hash the file bytes and refuse a file that changed while being read."""
    before = path.stat()
    digest, size = _hash(path)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise PreparationError(f"Input changed while hashing: {path}")
    return {"sha256": digest, "bytes": size}


def _raster_header(source) -> dict:
    """Keep the raster grid and declarations needed to explain pixel changes."""
    return {
        "width": source.width,
        "height": source.height,
        "count": source.count,
        "dtypes": list(source.dtypes),
        "crs": source.crs.to_wkt() if source.crs else None,
        "transform": list(source.transform),
        "nodatavals": list(source.nodatavals),
        "band_descriptions": list(source.descriptions),
        "header_scope": "internal_tiff; companions unused",
    }


def _runtime_versions() -> dict:
    """Record the libraries that read, align and write the raster pixels."""
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "rasterio": rasterio.__version__,
        "gdal": rasterio.__gdal_version__,
        "kelpseg": version("kelpseg"),
    }


def _profile(source, *, label: bool = False) -> dict:
    # A new profile deliberately omits old masks, alpha, statistics, overviews,
    # metadata strings and sidecar-dependent georeferencing.
    return {
        "driver": "GTiff",
        "width": source.width,
        "height": source.height,
        "count": 1 if label else source.count,
        "dtype": "uint8" if label else source.dtypes[0],
        "crs": source.crs,
        "transform": source.transform,
        "nodata": 3 if label else 0,
        "compress": "deflate",
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "bigtiff": "IF_SAFER",
    }


def _write_cleaned_windows(
    image,
    label,
    image_output,
    label_output,
    qa_outputs,
    nodata_values: tuple,
    block_size: int,
    label_values: tuple,
    source_key: str,
) -> tuple[Counter, Counter, Counter]:
    """Apply the scientific rules one small window at a time.

    Return counts, label class transitions and label QA on the image grid.
    An image-only job has no labels and keeps all valid image pixels.
    """
    counts = Counter({"existing_label_ignore": 0})
    transitions = Counter()
    label_audit = Counter()
    last_progress = time.monotonic()
    for window in windows(image.width, image.height, block_size):
        image_values = image.read(window=window)
        # Detect the ORIGINAL declaration before changing any pixels. A single
        # zero band is valid; all bands must match the effective nodata value.
        original_nodata = nodata_mask(image_values, nodata_values, band_axis=0)
        coverage = np.ones(original_nodata.shape, dtype=bool)
        stored_labels = None
        if label is not None:
            stored_labels, coverage = aligned_label(image, label, window, label_values)

        outside = ~coverage
        excluded = original_nodata | outside
        retained = ~excluded
        if np.any(retained & np.all(image_values == 0, axis=0)):
            raise PreparationError(
                f"{source_key}: retained valid all-band zero pixels collide with cleaned nodata=0. Review the source policy or annotation scope; values were not reclassified."
            )

        # Keep each reason separate so their union and intersection reconcile.
        counts["total_pixels"] += excluded.size
        counts["original_image_nodata"] += int(original_nodata.sum())
        counts["outside_label_footprint"] += int(outside.sum())
        counts["nodata_and_outside"] += int((original_nodata & outside).sum())
        counts["retained_valid_imagery"] += int(retained.sum())
        counts["final_exclusions"] += int(excluded.sum())
        changed_image = excluded & np.any(image_values != 0, axis=0)
        counts["changed_image_pixels"] += int(changed_image.sum())
        image_values[:, excluded] = 0
        image_output.write(image_values, window=window)

        if stored_labels is not None:
            # Annotation class 3 can remain over valid imagery. Only original
            # image nodata or missing geographic coverage blanks the image.
            cleaned_labels = repair_label_block(
                stored_labels, original_nodata, coverage
            )
            counts["existing_label_ignore"] += int(
                ((stored_labels == 3) & coverage).sum()
            )
            counts["changed_label_pixels"] += int(
                np.count_nonzero(stored_labels != cleaned_labels)
            )
            for old_class in np.unique(stored_labels[coverage]):
                class_pixels = coverage & (stored_labels == old_class)
                for new_class in np.unique(cleaned_labels[class_pixels]):
                    changed_to_class = class_pixels & (cleaned_labels == new_class)
                    transition = f"{int(old_class)}->{int(new_class)}"
                    transitions[transition] += int(changed_to_class.sum())
            transitions["outside->3"] += int(outside.sum())
            label_audit.update(audit_label_block(excluded, cleaned_labels))
            label_output.write(cleaned_labels, 1, window=window)

        if qa_outputs:
            # QA is written AFTER the core outputs and never selects their pixels.
            reason = original_nodata.astype(np.uint8) + 2 * outside.astype(np.uint8)
            qa_outputs["coverage"].write(coverage.astype(np.uint8), 1, window=window)
            qa_outputs["image_validity"].write(
                (~original_nodata).astype(np.uint8), 1, window=window
            )
            qa_outputs["reason"].write(reason, 1, window=window)
        if time.monotonic() - last_progress >= 10:
            logger.info(
                "Cleaning %s: %d/%d pixels",
                source_key,
                counts["total_pixels"],
                image.width * image.height,
            )
            last_progress = time.monotonic()
    return counts, transitions, label_audit


def _record_cleaned_source(
    pair,
    payload: Path,
    original_headers: dict,
    nodata_values: tuple,
    counts: Counter,
    transitions: Counter,
    label_audit: Counter,
    qa_paths: dict,
) -> dict:
    """Reopen closed output files and record their actual headers and hashes."""
    rasters = {"image": payload / "images" / pair.image_relative}
    if pair.label is not None:
        rasters["label"] = payload / "labels" / pair.label_relative
    output_headers = {}
    file_hashes = {}
    for role, path in rasters.items():
        logger.info("Verifying written %s headers and bytes: %s", role, path)
        with rasterio.open(path) as source:
            output_headers[role] = _raster_header(source)
        relative = path.relative_to(payload).as_posix()
        file_hashes[relative] = _file_record(path)
    for relative in qa_paths.values():
        file_hashes[relative] = _file_record(payload / relative)
    return {
        "key": pair.key,
        "identity": {
            "region": None,
            "acquisition_date": None,
            "source_id": None,
            "band_identity": "unknown unless established by source header or verified parent",
        },
        "original_headers": original_headers,
        "output_headers": output_headers,
        "effective_original_image_nodata": list(nodata_values),
        "counts": dict(counts),
        "class_transitions_target_grid": dict(sorted(transitions.items())),
        "label_audit": dict(label_audit),
        "qa": qa_paths,
        "files": file_hashes,
        "image_materialization": "fresh lossless raster; no source sidecars or masks copied",
    }


def _clean_pair(plan: CleanPlan, pair, payload: Path) -> dict:
    """Open one image and optional labels, write bounded windows, then record QA.

    ExitStack closes every optional TIFF, including on errors.
    We always use fresh raster profiles so old masks or metadata cannot override
    the pixels and grid that were actually written.
    """
    image_path = payload / "images" / pair.image_relative
    image_path.parent.mkdir(parents=True, exist_ok=True)
    label_path = None
    if pair.label is not None:
        label_path = payload / "labels" / pair.label_relative
        label_path.parent.mkdir(parents=True, exist_ok=True)

    qa_paths = {}
    original_headers = {}
    with (
        rasterio.Env(GDAL_PAM_ENABLED="NO", GDAL_GEOREF_SOURCES="INTERNAL"),
        ExitStack() as stack,
    ):
        image = stack.enter_context(
            rasterio.open(pair.image, GEOREF_SOURCES="INTERNAL")
        )
        original_headers["image"] = _raster_header(image)
        nodata_values = declared_nodata_values(
            image,
            retained_bands=image.count,
            missing_value=plan.recipe.missing_image_nodata,
        )
        logger.info(
            "%s: %d x %d pixels, %d bands; effective original nodata %s",
            pair.key,
            image.width,
            image.height,
            image.count,
            nodata_values[0],
        )
        image_output = stack.enter_context(
            rasterio.open(image_path, "w", **_profile(image))
        )
        image_output.descriptions = image.descriptions

        label = None
        label_output = None
        if pair.label is not None:
            label = stack.enter_context(
                rasterio.open(pair.label, GEOREF_SOURCES="INTERNAL")
            )
            original_headers["label"] = _raster_header(label)
            if same_grid(image, label):
                logger.info(
                    "%s: label grid already matches; reading stored labels directly",
                    pair.key,
                )
            else:
                logger.info(
                    "%s: nearest-aligning stored labels; class 0 remains valid background",
                    pair.key,
                )
            label_output = stack.enter_context(
                rasterio.open(label_path, "w", **_profile(image, label=True))
            )
        else:
            logger.info(
                "%s: image-only; no annotation exclusions or output labels", pair.key
            )

        qa_outputs = {}
        logger.info(
            "%s: detailed QA masks %s",
            pair.key,
            "enabled" if plan.recipe.qa_masks else "disabled",
        )
        if plan.recipe.qa_masks:
            for name in ("coverage", "image_validity", "reason"):
                path = (
                    payload
                    / "qa"
                    / name
                    / Path(pair.image_relative).with_suffix(".tif")
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                qa_profile = _profile(image, label=True)
                qa_profile["nodata"] = None
                qa_outputs[name] = stack.enter_context(
                    rasterio.open(path, "w", **qa_profile)
                )
                qa_paths[name] = path.relative_to(payload).as_posix()
        counts, transitions, label_audit = _write_cleaned_windows(
            image,
            label,
            image_output,
            label_output,
            qa_outputs,
            nodata_values,
            plan.recipe.block_size,
            plan.recipe.label_values,
            pair.key,
        )
    # All writers are closed before hashing or reopening with ordinary GDAL.
    record = _record_cleaned_source(
        pair,
        payload,
        original_headers,
        nodata_values,
        counts,
        transitions,
        label_audit,
        qa_paths,
    )
    _check_source_counts(record, pair)
    logger.info(
        "%s complete: %d pixels; nodata %d; outside labels %d; excluded %d; changed image %d, labels %d",
        pair.key,
        counts["total_pixels"],
        counts["original_image_nodata"],
        counts["outside_label_footprint"],
        counts["final_exclusions"],
        counts["changed_image_pixels"],
        counts.get("changed_label_pixels", 0),
    )
    return record


def _check_source_counts(record: dict, pair) -> None:
    """Check the few count identities that explain which pixels were excluded."""
    counts = record["counts"]
    total = counts["total_pixels"]
    excluded = counts["final_exclusions"]
    union = (
        counts["original_image_nodata"]
        + counts["outside_label_footprint"]
        - counts["nodata_and_outside"]
    )
    if total != counts["retained_valid_imagery"] + excluded or excluded != union:
        raise PreparationError(f"Pixel counts do not reconcile: {pair.key}")
    if pair.label is None:
        return
    transitions = sum(record["class_transitions_target_grid"].values())
    if transitions != total or record["label_audit"]["fn"]:
        raise PreparationError(f"Label counts do not reconcile: {pair.key}")


def _source_files(plan: CleanPlan) -> dict[str, Path]:
    """List the planned inputs again so new/missing files cannot go unnoticed."""
    if discover_inputs(plan.images, plan.labels) != plan.pairs:
        raise PreparationError("Input TIFF scope changed after planning; plan again.")
    paths = {}
    raster_paths = set()
    for pair in plan.pairs:
        paths["images/" + pair.image_relative] = pair.image
        raster_paths.add(pair.image)
        if pair.label is not None:
            paths["labels/" + pair.label_relative] = pair.label
            raster_paths.add(pair.label)
    roots = [plan.images]
    if plan.labels is not None:
        roots.append(plan.labels)
    if plan.parent is not None:
        roots = [plan.parent]
    if discover_companions(roots, raster_paths) != plan.companions:
        raise PreparationError(
            "Input companion inventory changed after planning; plan again."
        )
    for path in plan.companions:
        if plan.parent is not None:
            name = "parent/" + path.relative_to(plan.parent).as_posix()
        elif path.is_relative_to(plan.images):
            name = "image_assets/" + path.relative_to(plan.images).as_posix()
        else:
            name = "label_assets/" + path.relative_to(plan.labels).as_posix()
        paths[name] = path
    return paths


def _snapshot(paths: dict, parent: Path | None) -> dict:
    """Record input locations and hashes, reusing a verified parent's inventory."""
    verified = {}
    if parent is not None:
        verify_organized_release(parent)
        verified = json.loads((parent / "manifest.json").read_bytes())["files"]
    snapshots = {}
    for name, path in paths.items():
        known = None
        if parent is not None:
            known = verified.get(path.relative_to(parent).as_posix())
        if known is None:
            logger.info("Hashing input %s (%d bytes)", name, path.stat().st_size)
            known = _file_record(path)
        else:
            logger.info("Using verified parent file hash: %s", name)
        snapshots[name] = {"path": str(path), **known}
    return snapshots


def _source_stats(paths: dict) -> dict:
    """Notice a file written during this run, even if its old bytes are restored."""
    stats = {}
    for name, path in paths.items():
        info = path.stat()
        stats[name] = (info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    return stats


def _parent_provenance(plan: CleanPlan, stage: Path, records: list) -> None:
    """Keep known parent identities and a small inactive crosswalk snapshot."""
    if plan.parent is None:
        return
    with (plan.parent / "sources.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    identities = {}
    for row in rows:
        identities[row["source_id"]] = row
    keys = set()
    for pair in plan.pairs:
        keys.add(pair.key)
    if len(identities) != len(rows) or set(identities) != keys:
        raise PreparationError(
            "Parent identity rows must uniquely match the entire selected TIFF scope."
        )
    for record in records:
        record["identity"] = identities[record["key"]]
    (stage / "parent").mkdir()
    for name in (
        "manifest.json",
        "sources.csv",
        "regions.csv",
        "filename_aliases.csv",
        "assets.csv",
    ):
        source = plan.parent / name
        if source.is_file():
            with (stage / "parent" / name).open("xb") as stream:
                stream.write(source.read_bytes())


def verify_cleaned_release(path: Path) -> dict:
    """Check completed file bytes without rewriting or resuming any work."""
    try:
        manifest = json.loads((path / "manifest.json").read_bytes())
        if (
            not isinstance(manifest, dict)
            or manifest.get("status") != "complete"
            or not isinstance(manifest.get("files"), dict)
        ):
            raise PreparationError(f"Not a completed cleaned release: {path}")
        expected_names = set(manifest["files"]) | {"manifest.json"}
        if _inventory(path) != expected_names:
            raise PreparationError(f"Unexpected/missing output files: {path}")
        for name, expected in manifest["files"].items():
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise PreparationError(f"Unsafe output path in manifest: {name}")
            logger.info("Verifying completed file bytes: %s", name)
            if _file_record(path / name) != expected:
                raise PreparationError(f"Corrupt/changed output bytes: {name}")
        return manifest
    except (OSError, ValueError, KeyError, TypeError) as error:
        if isinstance(error, PreparationError):
            raise
        raise PreparationError(
            f"Cannot verify cleaned output {path}: {error}"
        ) from error


def _finish_output(
    plan: CleanPlan, stage: Path, records: list, snapshots: dict, checked
) -> Path:
    """Save four compact records, check all file hashes, then publish once."""
    counts = Counter()
    inactive_assets = snapshots.copy()
    for record, pair in zip(records, plan.pairs, strict=True):
        counts.update(record["counts"])
        record["inputs"] = {
            "image": inactive_assets.pop("images/" + pair.image_relative)
        }
        if pair.label is not None:
            record["inputs"]["label"] = inactive_assets.pop(
                "labels/" + pair.label_relative
            )
    for asset in inactive_assets.values():
        asset["disposition"] = "hashed provenance reference; inactive and unused"
    _parent_provenance(plan, stage, records)
    _write_record(stage / "recipe.json", asdict(plan.recipe))
    _write_record(
        stage / "sources.json",
        {
            "sources": records,
            "summary_counts": dict(counts),
            "inactive_assets": inactive_assets,
            "runtime": _runtime_versions(),
        },
    )
    _write_record(stage / "check.json", checked.to_dict())
    # Raster hashes were obtained after their writers closed. Nothing writes
    # those rasters again; hash only the newly written provenance files here.
    files = {}
    for record in records:
        files.update(record["files"])
    for name in sorted(_inventory(stage) - set(files)):
        files[name] = _file_record(stage / name)
    _write_record(
        stage / "manifest.json",
        {"schema_version": 1, "status": "complete", "files": files},
    )
    if plan.output.exists() or plan.output.is_symlink():
        raise PreparationError(
            f"Output appeared during cleanup; publication refused: {plan.output}"
        )
    # The final directory appears only when every file and check has completed.
    os.rename(stage, plan.output)
    logger.info("Complete verified cleaned output: %s", plan.output)
    return plan.output


def clean_dataset(plan: CleanPlan) -> Path:
    """Complete one fresh cleanup attempt. Failed attempts are never reused."""
    stage = plan.output.with_name(f".{plan.output.name}.incomplete")
    try:
        for destination in (plan.output, stage):
            if destination.exists() or destination.is_symlink():
                raise PreparationError(
                    f"Output or incomplete attempt already exists: {destination}. Inspect it and choose a fresh output, or explicitly move/remove the incomplete attempt before rerunning from the beginning."
                )
        if not plan.output.parent.is_dir():
            raise PreparationError(
                f"Create the output parent directory first: {plan.output.parent}"
            )
        # mkdir claims this attempt exclusively. A second run cannot use it;
        # there is no lock, journal, receipt or interrupted-work recovery path.
        stage.mkdir()
        logger.info("Phase 1: hashing original rasters and inactive companions")
        paths = _source_files(plan)
        original_stats = _source_stats(paths)
        snapshots = _snapshot(paths, plan.parent)

        logger.info("Phase 2: full source checks before any pixel changes")
        source_check = check_inputs(
            plan.images, plan.labels, plan.recipe.check_recipe(), full=True
        )
        unsupported = []
        for issue in source_check.issues:
            if not issue.repairable:
                unsupported.append(issue.message)
        if unsupported:
            raise PreparationError(
                "Full source check failed: " + "; ".join(unsupported)
            )

        logger.info("Phase 3: cleaning %d sources into separate files", len(plan.pairs))
        records = []
        for number, pair in enumerate(plan.pairs, 1):
            logger.info("[Clean %d/%d] %s", number, len(plan.pairs), pair.key)
            records.append(_clean_pair(plan, pair, stage))

        logger.info("Phase 4: independently checking outputs and publishing")
        output_labels = stage / "labels" if plan.labels is not None else None
        checked = check_inputs(
            stage / "images",
            output_labels,
            plan.recipe.check_recipe("cleaned"),
            full=True,
        )
        if not checked.passed:
            messages = []
            for issue in checked.issues:
                messages.append(issue.message)
            raise PreparationError(
                "Independent cleaned-output check failed: " + "; ".join(messages)
            )
        if _source_files(plan) != paths or _source_stats(paths) != original_stats:
            raise PreparationError(
                "Inputs changed during cleanup; publication refused."
            )
        return _finish_output(plan, stage, records, snapshots, checked)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        if isinstance(error, PreparationError):
            raise
        raise PreparationError(
            f"Cleanup failed: {error}. Any incomplete attempt is at {stage}; inspect it before rerunning from the beginning."
        ) from error
