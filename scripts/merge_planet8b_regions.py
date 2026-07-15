#!/usr/bin/env python3
"""Discover and organize paired California and BC PlanetScope 8-band TIFFs."""

from __future__ import annotations

import argparse
import csv
import errno
import hashlib
import json
import os
import shlex
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import rasterio
from planet8b_metadata import parse_bc_stem, parse_ca_stem
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT

TIFF_SUFFIXES = {".tif", ".tiff"}
MANIFEST_FIELDS = [
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "source_split",
    "source_image",
    "source_label",
    "merged_image",
    "merged_label",
    "materialization_mode",
    "label_preparation",
]
ISSUE_FIELDS = [
    "severity",
    "issue_type",
    "dataset",
    "candidate_id",
    "path",
    "details",
]
ALIGNMENT_FIELDS = [
    "source_tiff_id",
    "source_label",
    "source_label_width",
    "source_label_height",
    "source_label_crs",
    "source_label_transform",
    "source_label_nodata",
    "source_label_values",
    "output_label_width",
    "output_label_height",
    "output_label_crs",
    "output_label_transform",
    "output_label_nodata",
    "output_label_values",
    "resampling",
    "total_pixels",
    "image_nodata_pixels",
    "outside_source_label_pixels",
    "image_nodata_and_outside_label_pixels",
    "assigned_nodata_pixels",
    "outside_source_label_not_nodata_pixels",
]
COPY_VERIFICATION_FIELDS = [
    "source_tiff_id",
    "source_image",
    "copied_image",
    "source_size_bytes",
    "copied_size_bytes",
    "source_sha256",
    "copied_sha256",
    "same_inode",
]


@dataclass(frozen=True)
class Issue:
    severity: str
    issue_type: str
    dataset: str
    candidate_id: str
    path: str
    details: str


@dataclass(frozen=True)
class ManifestRow:
    source_tiff_id: str
    dataset: str
    region_id: str
    region_name: str
    acquisition_date: str
    source_split: str
    source_image: str
    source_label: str
    merged_image: str
    merged_label: str
    materialization_mode: str
    label_preparation: str


@dataclass(frozen=True)
class AlignmentRow:
    source_tiff_id: str
    source_label: str
    source_label_width: int
    source_label_height: int
    source_label_crs: str
    source_label_transform: str
    source_label_nodata: str
    source_label_values: str
    output_label_width: int
    output_label_height: int
    output_label_crs: str
    output_label_transform: str
    output_label_nodata: int
    output_label_values: str
    resampling: str
    total_pixels: int
    image_nodata_pixels: int
    outside_source_label_pixels: int
    image_nodata_and_outside_label_pixels: int
    assigned_nodata_pixels: int
    outside_source_label_not_nodata_pixels: int


@dataclass(frozen=True)
class CopyVerificationRow:
    source_tiff_id: str
    source_image: str
    copied_image: str
    source_size_bytes: int
    copied_size_bytes: int
    source_sha256: str
    copied_sha256: str
    same_inode: bool


class InventoryError(RuntimeError):
    """Raised after inventory validation finds one or more fatal issues."""

    def __init__(self, issues: list[Issue]):
        self.issues = issues
        summary = "; ".join(
            f"{issue.issue_type}: {issue.details}" for issue in issues[:5]
        )
        if len(issues) > 5:
            summary += f"; plus {len(issues) - 5} more"
        super().__init__(
            f"Inventory validation failed ({len(issues)} issue(s)): {summary}"
        )


def _tiff_map(directory: Path, dataset: str, issues: list[Issue]) -> dict[str, Path]:
    if not directory.is_dir():
        issues.append(
            Issue(
                "fatal",
                "missing_directory",
                dataset,
                "",
                str(directory),
                "Required image/label directory does not exist",
            )
        )
        return {}

    files: dict[str, Path] = {}
    for path in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file() or path.suffix.lower() not in TIFF_SUFFIXES:
            continue
        key = path.stem.casefold()
        if key in files:
            issues.append(
                Issue(
                    "fatal",
                    "duplicate_stem",
                    dataset,
                    path.stem,
                    str(path),
                    f"TIFF stem collides case-insensitively with {files[key]}",
                )
            )
            continue
        files[key] = path
    return files


def _paired_tiffs(
    images_dir: Path, labels_dir: Path, dataset: str, issues: list[Issue]
) -> list[tuple[Path, Path]]:
    images = _tiff_map(images_dir, dataset, issues)
    labels = _tiff_map(labels_dir, dataset, issues)
    for key in sorted(set(images) - set(labels)):
        issues.append(
            Issue(
                "fatal",
                "missing_label",
                dataset,
                images[key].stem,
                str(images[key]),
                f"No case-insensitive label match in {labels_dir}",
            )
        )
    for key in sorted(set(labels) - set(images)):
        issues.append(
            Issue(
                "fatal",
                "missing_image",
                dataset,
                labels[key].stem,
                str(labels[key]),
                f"No case-insensitive image match in {images_dir}",
            )
        )
    return [(images[key], labels[key]) for key in sorted(set(images) & set(labels))]


def _candidate_rows(
    ca_root: Path,
    bc_tiles_root: Path,
    output_root: Path,
    mode: str,
    label_preparation: str,
) -> tuple[list[ManifestRow], list[Issue]]:
    issues: list[Issue] = []
    candidates: list[tuple[str, str, Path, Path]] = []
    for image, label in _paired_tiffs(
        ca_root / "images", ca_root / "labels", "ca", issues
    ):
        candidates.append(("ca", "", image, label))

    if not bc_tiles_root.is_dir():
        issues.append(
            Issue(
                "fatal",
                "missing_directory",
                "bc",
                "",
                str(bc_tiles_root),
                "BC tiles root does not exist",
            )
        )
    else:
        split_roots = [
            path
            for path in bc_tiles_root.iterdir()
            if path.is_dir()
            and path.name.casefold() != "full_scenes"
            and ((path / "images").exists() or (path / "labels").exists())
        ]
        if not split_roots:
            issues.append(
                Issue(
                    "fatal",
                    "missing_directory",
                    "bc",
                    "",
                    str(bc_tiles_root),
                    "No historical split directories with images/labels were found",
                )
            )
        for split_root in sorted(split_roots, key=lambda item: item.name.casefold()):
            for image, label in _paired_tiffs(
                split_root / "images", split_root / "labels", "bc", issues
            ):
                candidates.append(("bc", split_root.name, image, label))

    rows: list[ManifestRow] = []
    seen_ids: dict[str, Path] = {}
    for dataset, source_split, image, label in candidates:
        source_tiff_id = image.stem
        key = source_tiff_id.casefold()
        if key in seen_ids:
            issues.append(
                Issue(
                    "fatal",
                    "destination_collision",
                    dataset,
                    source_tiff_id,
                    str(image),
                    f"Source ID collides case-insensitively with {seen_ids[key]}",
                )
            )
            continue
        seen_ids[key] = image
        try:
            metadata = (
                parse_ca_stem(source_tiff_id)
                if dataset == "ca"
                else parse_bc_stem(source_tiff_id)
            )
        except ValueError as error:
            issues.append(
                Issue(
                    "fatal",
                    "unparsable_id",
                    dataset,
                    source_tiff_id,
                    str(image),
                    str(error),
                )
            )
            continue
        rows.append(
            ManifestRow(
                source_tiff_id=source_tiff_id,
                dataset=dataset,
                region_id=metadata.region_id,
                region_name=metadata.region_name,
                acquisition_date=metadata.acquisition_date.isoformat(),
                source_split=source_split,
                source_image=str(image.resolve()),
                source_label=str(label.resolve()),
                merged_image=str(
                    (output_root / "all" / "images" / f"{source_tiff_id}.tif").resolve()
                ),
                merged_label=str(
                    (output_root / "all" / "labels" / f"{source_tiff_id}.tif").resolve()
                ),
                materialization_mode=mode,
                label_preparation=label_preparation,
            )
        )

    rows.sort(
        key=lambda row: (
            row.region_id.casefold(),
            row.acquisition_date,
            row.source_tiff_id.casefold(),
        )
    )
    issues.sort(
        key=lambda issue: (
            issue.dataset,
            issue.issue_type,
            issue.candidate_id.casefold(),
            issue.path.casefold(),
        )
    )
    return rows, issues


def discover_inventory(
    ca_root: Path,
    bc_tiles_root: Path,
    output_root: Path,
    mode: str,
    label_preparation: str = "source",
) -> list[ManifestRow]:
    """Return a validated, deterministically ordered planned manifest."""
    rows, issues = _candidate_rows(
        ca_root, bc_tiles_root, output_root, mode, label_preparation
    )
    if issues:
        raise InventoryError(issues)
    return rows


def _atomic_csv(path: Path, fields: list[str], rows: Iterable[object]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(asdict(row))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _materializer(mode: str) -> Callable[[str, str], object]:
    return os.link if mode == "hardlink" else shutil.copy2


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_transform(transform: rasterio.Affine) -> str:
    return json.dumps(tuple(transform)[:6])


def _number(value: np.generic | int | float) -> int | float:
    scalar = value.item() if isinstance(value, np.generic) else value
    return int(scalar) if isinstance(scalar, (int, np.integer)) else float(scalar)


def _source_label_values(label: rasterio.io.DatasetReader) -> list[int | float]:
    values: set[int | float] = set()
    for _, window in label.block_windows(1):
        values.update(
            _number(value) for value in np.unique(label.read(1, window=window))
        )
    return sorted(values)


def derive_aligned_label(
    source_image: Path, source_label: Path, destination: Path, source_tiff_id: str
) -> AlignmentRow:
    """Write a uint8 KATE label on the image grid with class 3 as nodata."""
    with rasterio.open(source_image) as image, rasterio.open(source_label) as label:
        if image.count != 8:
            raise RuntimeError(
                f"{source_tiff_id}: image has {image.count} bands, expected 8"
            )
        if label.count != 1:
            raise RuntimeError(
                f"{source_tiff_id}: label has {label.count} bands, expected 1"
            )
        if image.crs is None or label.crs is None:
            raise RuntimeError(f"{source_tiff_id}: image and label must have a CRS")
        source_values = _source_label_values(label)
        unsupported = sorted(set(source_values) - {0, 1, 2, 3, 4})
        if unsupported:
            raise RuntimeError(
                f"{source_tiff_id}: source label has unsupported KATE values "
                f"{unsupported}"
            )

        profile = {
            "driver": "GTiff",
            "width": image.width,
            "height": image.height,
            "count": 1,
            "dtype": "uint8",
            "crs": image.crs,
            "transform": image.transform,
            "nodata": 3,
            "compress": "deflate",
            "predictor": 2,
            "tiled": True,
            "blockxsize": 512,
            "blockysize": 512,
            "bigtiff": "IF_SAFER",
        }
        totals = {
            "total_pixels": 0,
            "image_nodata_pixels": 0,
            "outside_source_label_pixels": 0,
            "image_nodata_and_outside_label_pixels": 0,
            "assigned_nodata_pixels": 0,
            "outside_source_label_not_nodata_pixels": 0,
        }
        output_values: set[int] = set()
        # The source files declare nodata=0 even though 0 is the KATE water
        # class. Override that metadata with an unused uint8 value so stored
        # zeros participate in nearest-neighbor reprojection. The VRT alpha
        # band separately records geographic source coverage.
        with (
            WarpedVRT(
                label,
                crs=image.crs,
                transform=image.transform,
                width=image.width,
                height=image.height,
                resampling=Resampling.nearest,
                src_nodata=255,
                nodata=3,
                add_alpha=True,
            ) as aligned,
            rasterio.open(destination, "w", **profile) as output,
        ):
            alpha_band = aligned.count
            for _, window in output.block_windows(1):
                image_block = image.read(window=window)
                label_block = aligned.read(1, window=window).astype(np.uint8)
                coverage = aligned.read(alpha_band, window=window) > 0
                image_nodata = np.all(image_block == 0, axis=0)
                outside = ~coverage
                assigned = image_nodata | outside
                label_block[assigned] = 3
                output.write(label_block, 1, window=window)

                totals["total_pixels"] += label_block.size
                totals["image_nodata_pixels"] += int(image_nodata.sum())
                totals["outside_source_label_pixels"] += int(outside.sum())
                totals["image_nodata_and_outside_label_pixels"] += int(
                    (image_nodata & outside).sum()
                )
                totals["assigned_nodata_pixels"] += int(assigned.sum())
                totals["outside_source_label_not_nodata_pixels"] += int(
                    (outside & (label_block != 3)).sum()
                )
                output_values.update(int(value) for value in np.unique(label_block))

        if totals["outside_source_label_not_nodata_pixels"]:
            raise RuntimeError(
                f"{source_tiff_id}: pixels outside label coverage were not set to 3"
            )
        return AlignmentRow(
            source_tiff_id=source_tiff_id,
            source_label=str(source_label.resolve()),
            source_label_width=label.width,
            source_label_height=label.height,
            source_label_crs=str(label.crs),
            source_label_transform=_json_transform(label.transform),
            source_label_nodata=str(label.nodata),
            source_label_values=json.dumps(source_values),
            output_label_width=image.width,
            output_label_height=image.height,
            output_label_crs=str(image.crs),
            output_label_transform=_json_transform(image.transform),
            output_label_nodata=3,
            output_label_values=json.dumps(sorted(output_values)),
            resampling="nearest",
            **totals,
        )


def materialize(
    output_root: Path,
    rows: list[ManifestRow],
    mode: str,
    creation_command: str = "",
    derive_labels: bool = False,
) -> None:
    """Atomically create a complete merge view from a validated manifest."""
    if output_root.exists() and (
        not output_root.is_dir() or any(output_root.iterdir())
    ):
        issue = Issue(
            "fatal",
            "nonempty_output",
            "",
            "",
            str(output_root),
            "Output root must not exist or must be an empty directory",
        )
        raise InventoryError([issue])

    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.staging-", dir=output_root.parent)
    )
    transfer = _materializer(mode)
    alignments: list[AlignmentRow] = []
    copy_verification: list[CopyVerificationRow] = []
    try:
        images_dir = staging / "all" / "images"
        labels_dir = staging / "all" / "labels"
        images_dir.mkdir(parents=True)
        labels_dir.mkdir(parents=True)
        for index, row in enumerate(rows, start=1):
            try:
                staged_image = images_dir / f"{row.source_tiff_id}.tif"
                staged_label = labels_dir / f"{row.source_tiff_id}.tif"
                transfer(row.source_image, staged_image)
                if mode == "copy":
                    source_path = Path(row.source_image)
                    source_hash = _sha256(source_path)
                    copied_hash = _sha256(staged_image)
                    same_inode = os.path.samefile(source_path, staged_image)
                    if source_hash != copied_hash or same_inode:
                        raise RuntimeError(
                            f"{row.source_tiff_id}: copied image checksum or inode "
                            "verification failed"
                        )
                    copy_verification.append(
                        CopyVerificationRow(
                            source_tiff_id=row.source_tiff_id,
                            source_image=str(source_path.resolve()),
                            copied_image=str(Path(row.merged_image).resolve()),
                            source_size_bytes=source_path.stat().st_size,
                            copied_size_bytes=staged_image.stat().st_size,
                            source_sha256=source_hash,
                            copied_sha256=copied_hash,
                            same_inode=same_inode,
                        )
                    )
                if derive_labels:
                    alignments.append(
                        derive_aligned_label(
                            staged_image,
                            Path(row.source_label),
                            staged_label,
                            row.source_tiff_id,
                        )
                    )
                else:
                    transfer(row.source_label, staged_label)
                if index == 1 or index % 25 == 0 or index == len(rows):
                    print(
                        f"Prepared {index}/{len(rows)} pairs: {row.source_tiff_id}",
                        flush=True,
                    )
            except OSError as error:
                if mode == "hardlink" and error.errno == errno.EXDEV:
                    raise RuntimeError(
                        "Hard linking crossed filesystems; rerun with --mode copy"
                    ) from error
                raise
        _atomic_csv(staging / "raster_manifest.csv", MANIFEST_FIELDS, rows)
        _atomic_csv(staging / "merge_issues.csv", ISSUE_FIELDS, [])
        _atomic_csv(staging / "label_alignment.csv", ALIGNMENT_FIELDS, alignments)
        _atomic_csv(
            staging / "copy_verification.csv",
            COPY_VERIFICATION_FIELDS,
            copy_verification,
        )
        command_path = staging / "creation_command.txt"
        command_path.write_text(f"{creation_command}\n")
        if output_root.exists():
            output_root.rmdir()
        os.replace(staging, output_root)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def print_summary(rows: list[ManifestRow], dry_run: bool) -> None:
    ca_count = sum(row.dataset == "ca" for row in rows)
    bc_count = sum(row.dataset == "bc" for row in rows)
    region_count = len({row.region_id for row in rows})
    prefix = "Dry run complete" if dry_run else "Materialization complete"
    print(
        f"{prefix}: {ca_count} CA, {bc_count} BC, {len(rows)} total, "
        f"{region_count} region IDs"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca-root", type=Path, required=True)
    parser.add_argument("--bc-tiles-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("hardlink", "copy"), default="hardlink")
    parser.add_argument(
        "--derive-labels",
        action="store_true",
        help=(
            "Align labels to image grids and assign KATE class 3 where all image "
            "bands are zero or source-label coverage is absent"
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rows = discover_inventory(
            args.ca_root,
            args.bc_tiles_root,
            args.output_root,
            args.mode,
            "derived_aligned" if args.derive_labels else "source",
        )
        if not args.dry_run:
            materialize(
                args.output_root,
                rows,
                args.mode,
                shlex.join(["uv", "run", "python", *sys.argv]),
                args.derive_labels,
            )
        print_summary(rows, args.dry_run)
        return 0
    except InventoryError as error:
        print(error, file=sys.stderr)
        writer = csv.DictWriter(sys.stderr, fieldnames=ISSUE_FIELDS)
        writer.writeheader()
        for issue in error.issues:
            writer.writerow(asdict(issue))
        return 2
    except (OSError, RuntimeError) as error:
        print(f"Materialization failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
