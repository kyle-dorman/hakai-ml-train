#!/usr/bin/env python3
"""Discover and organize paired California and BC PlanetScope 8-band TIFFs."""

from __future__ import annotations

import argparse
import csv
import errno
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

from planet8b_metadata import parse_bc_stem, parse_ca_stem

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
]
ISSUE_FIELDS = [
    "severity",
    "issue_type",
    "dataset",
    "candidate_id",
    "path",
    "details",
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
    ca_root: Path, bc_tiles_root: Path, output_root: Path, mode: str
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
    ca_root: Path, bc_tiles_root: Path, output_root: Path, mode: str
) -> list[ManifestRow]:
    """Return a validated, deterministically ordered planned manifest."""
    rows, issues = _candidate_rows(ca_root, bc_tiles_root, output_root, mode)
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


def materialize(output_root: Path, rows: list[ManifestRow], mode: str) -> None:
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
    try:
        images_dir = staging / "all" / "images"
        labels_dir = staging / "all" / "labels"
        images_dir.mkdir(parents=True)
        labels_dir.mkdir(parents=True)
        for row in rows:
            try:
                transfer(row.source_image, images_dir / f"{row.source_tiff_id}.tif")
                transfer(row.source_label, labels_dir / f"{row.source_tiff_id}.tif")
            except OSError as error:
                if mode == "hardlink" and error.errno == errno.EXDEV:
                    raise RuntimeError(
                        "Hard linking crossed filesystems; rerun with --mode copy"
                    ) from error
                raise
        _atomic_csv(staging / "raster_manifest.csv", MANIFEST_FIELDS, rows)
        _atomic_csv(staging / "merge_issues.csv", ISSUE_FIELDS, [])
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
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rows = discover_inventory(
            args.ca_root, args.bc_tiles_root, args.output_root, args.mode
        )
        if not args.dry_run:
            materialize(args.output_root, rows, args.mode)
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
