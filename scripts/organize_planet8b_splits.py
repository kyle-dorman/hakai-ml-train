#!/usr/bin/env python3
"""Organize raw PlanetScope 8-band rasters into split folders for chip creation.

The training chip script expects this raw layout:

    raw_root/
      train/images/*.tif
      train/labels/*.tif
      val/images/*.tif
      val/labels/*.tif
      test/images/*.tif
      test/labels/*.tif

This helper builds that layout from the BC and CA source folders using the
split CSV as the canonical file list. It links files by default so the source
GeoTIFFs are not duplicated.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


TIMESTAMP_RE = re.compile(r"(20\d{6}_\d{6})")
TIMESTAMP_SAT_RE = re.compile(r"(20\d{6}_\d{6})(?:_\d{2})?_([0-9a-fA-F]{4})")
RASTER_SUFFIXES = {".tif", ".tiff"}
SPLIT_NAMES = {"train", "val", "test"}


@dataclass(frozen=True)
class SplitRow:
    stem: str
    split: str
    timestamp: str | None
    timestamp_sat: str | None


@dataclass(frozen=True)
class Candidate:
    path: Path
    kind: str
    stem: str
    timestamp: str | None
    timestamp_sat: str | None


@dataclass(frozen=True)
class Match:
    row: SplitRow
    image: Candidate
    label: Candidate
    image_strategy: str
    label_strategy: str


def normalize_split(value: str) -> str:
    split = value.strip().lower()
    if split not in SPLIT_NAMES:
        raise ValueError(f"Unsupported split {value!r}; expected train, val, or test")
    return split


def timestamp_for(stem: str) -> str | None:
    match = TIMESTAMP_RE.search(stem)
    return match.group(1) if match else None


def timestamp_sat_for(stem: str) -> str | None:
    match = TIMESTAMP_SAT_RE.search(stem)
    if not match:
        return None
    return f"{match.group(1)}_{match.group(2).lower()}"


def is_raster_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in RASTER_SUFFIXES


def path_has_component(path: Path, names: set[str]) -> bool:
    return any(part.lower() in names for part in path.parts)


def expand_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def read_split_rows(csv_path: Path) -> list[SplitRow]:
    rows: list[SplitRow] = []
    with csv_path.open(newline="") as file:
        reader = csv.DictReader(file)
        required = {"image_name_stem", "split"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{csv_path} is missing required columns: {sorted(missing)}")

        for line_number, row in enumerate(reader, start=2):
            stem = (row.get("image_name_stem") or "").strip()
            split = (row.get("split") or "").strip()
            if not stem or not split:
                raise ValueError(f"{csv_path}:{line_number} has blank stem or split")
            rows.append(
                SplitRow(
                    stem=stem,
                    split=normalize_split(split),
                    timestamp=timestamp_for(stem),
                    timestamp_sat=timestamp_sat_for(stem),
                )
            )

    duplicates = [stem for stem, count in Counter(row.stem for row in rows).items() if count > 1]
    if duplicates:
        raise ValueError(f"Split CSV contains duplicate image_name_stem values: {duplicates[:10]}")
    return rows


def collect_candidates(
    source_roots: list[Path],
    explicit_image_dirs: list[Path],
    explicit_label_dirs: list[Path],
) -> tuple[list[Candidate], list[Candidate]]:
    images: dict[Path, Candidate] = {}
    labels: dict[Path, Candidate] = {}

    def add_candidate(path: Path, kind: str) -> None:
        candidate = Candidate(
            path=path.resolve(),
            kind=kind,
            stem=path.stem,
            timestamp=timestamp_for(path.stem),
            timestamp_sat=timestamp_sat_for(path.stem),
        )
        if kind == "image":
            images[candidate.path] = candidate
        else:
            labels[candidate.path] = candidate

    def add_from_dir(directory: Path, kind: str) -> None:
        if not directory.exists():
            print(f"warning: {kind} directory does not exist: {directory}", file=sys.stderr)
            return
        for path in directory.rglob("*"):
            if is_raster_file(path):
                add_candidate(path, kind)

    for directory in explicit_image_dirs:
        add_from_dir(directory, "image")
    for directory in explicit_label_dirs:
        add_from_dir(directory, "label")

    for root in source_roots:
        if not root.exists():
            print(f"warning: source root does not exist: {root}", file=sys.stderr)
            continue
        for path in root.rglob("*"):
            if not is_raster_file(path):
                continue
            if path_has_component(path, {"images", "image"}):
                add_candidate(path, "image")
            elif path_has_component(path, {"labels", "label"}):
                add_candidate(path, "label")

    return sorted(images.values(), key=lambda item: str(item.path)), sorted(
        labels.values(), key=lambda item: str(item.path)
    )


def make_indexes(candidates: list[Candidate]) -> dict[str, dict[str, list[Candidate]]]:
    indexes: dict[str, dict[str, list[Candidate]]] = {
        "exact": defaultdict(list),
        "timestamp_sat": defaultdict(list),
        "timestamp": defaultdict(list),
    }
    for candidate in candidates:
        indexes["exact"][candidate.stem.lower()].append(candidate)
        if candidate.timestamp_sat:
            indexes["timestamp_sat"][candidate.timestamp_sat].append(candidate)
        if candidate.timestamp:
            indexes["timestamp"][candidate.timestamp].append(candidate)
    return indexes


def unique_match(
    indexes: dict[str, dict[str, list[Candidate]]],
    keys: list[tuple[str, str | None]],
) -> tuple[Candidate | None, str, list[Candidate]]:
    for strategy, key in keys:
        if not key:
            continue
        candidates = indexes[strategy].get(key.lower() if strategy == "exact" else key, [])
        if len(candidates) == 1:
            return candidates[0], strategy, candidates
        if len(candidates) > 1:
            return None, f"ambiguous_{strategy}", candidates
    return None, "missing", []


def match_rows(
    rows: list[SplitRow],
    images: list[Candidate],
    labels: list[Candidate],
) -> tuple[list[Match], list[dict[str, str]]]:
    image_indexes = make_indexes(images)
    label_indexes = make_indexes(labels)
    matches: list[Match] = []
    issues: list[dict[str, str]] = []

    for row in rows:
        image, image_strategy, image_candidates = unique_match(
            image_indexes,
            [
                ("exact", row.stem),
                ("timestamp_sat", row.timestamp_sat),
                ("timestamp", row.timestamp),
            ],
        )

        label_keys = [
            ("exact", row.stem),
            ("timestamp_sat", row.timestamp_sat),
            ("timestamp", row.timestamp),
        ]
        if image is not None:
            label_keys.insert(1, ("exact", image.stem))

        label, label_strategy, label_candidates = unique_match(label_indexes, label_keys)

        if image is not None and label is not None:
            matches.append(Match(row, image, label, image_strategy, label_strategy))
            continue

        issues.append(
            {
                "image_name_stem": row.stem,
                "split": row.split,
                "timestamp": row.timestamp or "",
                "timestamp_sat": row.timestamp_sat or "",
                "image_status": image_strategy,
                "image_candidates": ";".join(str(item.path) for item in image_candidates),
                "label_status": label_strategy,
                "label_candidates": ";".join(str(item.path) for item in label_candidates),
            }
        )

    reused_paths: set[Path] = set()
    for path, grouped_matches in _group_matches_by_path(matches, "image").items():
        if len(grouped_matches) > 1 and any(
            match.image_strategy != "exact" for match in grouped_matches
        ):
            reused_paths.add(path)
    for path, grouped_matches in _group_matches_by_path(matches, "label").items():
        if len(grouped_matches) > 1 and any(
            match.label_strategy != "exact" for match in grouped_matches
        ):
            reused_paths.add(path)

    if reused_paths:
        filtered_matches: list[Match] = []
        for match in matches:
            if match.image.path in reused_paths or match.label.path in reused_paths:
                issues.append(
                    {
                        "image_name_stem": match.row.stem,
                        "split": match.row.split,
                        "timestamp": match.row.timestamp or "",
                        "timestamp_sat": match.row.timestamp_sat or "",
                        "image_status": "reused_source"
                        if match.image.path in reused_paths
                        else match.image_strategy,
                        "image_candidates": str(match.image.path),
                        "label_status": "reused_source"
                        if match.label.path in reused_paths
                        else match.label_strategy,
                        "label_candidates": str(match.label.path),
                    }
                )
            else:
                filtered_matches.append(match)
        matches = filtered_matches

    return matches, issues


def _group_matches_by_path(matches: list[Match], kind: str) -> dict[Path, list[Match]]:
    grouped: dict[Path, list[Match]] = defaultdict(list)
    for match in matches:
        candidate = match.image if kind == "image" else match.label
        grouped[candidate.path].append(match)
    return grouped


def destination_name(row: SplitRow, source_image: Candidate) -> str:
    return f"{row.stem}{source_image.path.suffix}"


def link_or_copy(source: Path, destination: Path, mode: str, overwrite: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() and destination.resolve() == source.resolve():
            return
        if not overwrite:
            raise FileExistsError(f"Destination exists and points elsewhere: {destination}")
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()

    if mode == "symlink":
        os.symlink(source, destination)
    elif mode == "hardlink":
        os.link(source, destination)
    elif mode == "copy":
        shutil.copy2(source, destination)
    else:
        raise ValueError(f"Unsupported link mode: {mode}")


def sidecar_pairs(source: Path, destination: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    seen_destinations: set[str] = set()
    source_strings = [
        (Path(str(source) + ".aux.xml"), Path(str(destination) + ".aux.xml")),
        (Path(str(source) + ".ovr"), Path(str(destination) + ".ovr")),
        (source.with_suffix(".tfw"), destination.with_suffix(".tfw")),
        (source.with_suffix(".TFW"), destination.with_suffix(".TFW")),
    ]
    for src, dst in source_strings:
        destination_key = str(dst).lower()
        if src.exists() and destination_key not in seen_destinations:
            pairs.append((src, dst))
            seen_destinations.add(destination_key)
    return pairs


def write_manifest(manifest_path: Path, matches: list[Match], output_root: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "image_name_stem",
        "split",
        "image_strategy",
        "label_strategy",
        "source_image",
        "source_label",
        "output_image",
        "output_label",
    ]
    with manifest_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for match in matches:
            name = destination_name(match.row, match.image)
            output_image = output_root / match.row.split / "images" / name
            output_label = output_root / match.row.split / "labels" / name
            writer.writerow(
                {
                    "image_name_stem": match.row.stem,
                    "split": match.row.split,
                    "image_strategy": match.image_strategy,
                    "label_strategy": match.label_strategy,
                    "source_image": match.image.path,
                    "source_label": match.label.path,
                    "output_image": output_image,
                    "output_label": output_label,
                }
            )


def write_issues(issues_path: Path, issues: list[dict[str, str]]) -> None:
    issues_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "image_name_stem",
        "split",
        "timestamp",
        "timestamp_sat",
        "image_status",
        "image_candidates",
        "label_status",
        "label_candidates",
    ]
    with issues_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(issues)


def organize(
    matches: list[Match],
    output_root: Path,
    link_mode: str,
    overwrite: bool,
    include_sidecars: bool,
    dry_run: bool,
) -> None:
    for match in matches:
        name = destination_name(match.row, match.image)
        output_image = output_root / match.row.split / "images" / name
        output_label = output_root / match.row.split / "labels" / name

        if dry_run:
            continue

        link_or_copy(match.image.path, output_image, link_mode, overwrite)
        link_or_copy(match.label.path, output_label, link_mode, overwrite)

        if include_sidecars:
            for source, destination in sidecar_pairs(match.image.path, output_image):
                link_or_copy(source, destination, link_mode, overwrite)
            for source, destination in sidecar_pairs(match.label.path, output_label):
                link_or_copy(source, destination, link_mode, overwrite)


def print_summary(matches: list[Match], issues: list[dict[str, str]]) -> None:
    print(f"matched rows: {len(matches)}")
    print(f"issue rows: {len(issues)}")
    print("matched by split:")
    split_counts = Counter(match.row.split for match in matches)
    for split in ["train", "val", "test"]:
        print(f"  {split}: {split_counts.get(split, 0)}")

    image_strategies = Counter(match.image_strategy for match in matches)
    label_strategies = Counter(match.label_strategy for match in matches)
    print("image match strategies:", dict(sorted(image_strategies.items())))
    print("label match strategies:", dict(sorted(label_strategies.items())))

    if issues:
        print("first issues:")
        for issue in issues[:10]:
            print(
                "  "
                f"{issue['split']} {issue['image_name_stem']}: "
                f"image={issue['image_status']} label={issue['label_status']}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create split image/label folders from PlanetScope 8-band sources."
    )
    parser.add_argument(
        "--split-csv",
        type=Path,
        default=Path("planet8b_image_splits.csv"),
        help="CSV with image_name_stem and split columns.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("~/data/PlanetScope/raw-8b/20250814_cali_bc"),
        help="Raw split tree to create before chip generation.",
    )
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        type=expand_path,
        help="Recursive source root to scan for images/ and labels/ directories. Repeatable.",
    )
    parser.add_argument(
        "--image-dir",
        action="append",
        default=[],
        type=expand_path,
        help="Explicit image directory to scan. Repeatable.",
    )
    parser.add_argument(
        "--label-dir",
        action="append",
        default=[],
        type=expand_path,
        help="Explicit label directory to scan. Repeatable.",
    )
    parser.add_argument(
        "--link-mode",
        choices=["symlink", "hardlink", "copy"],
        default="symlink",
        help="How to materialize files in the output tree.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing output links/files that point elsewhere.",
    )
    parser.add_argument(
        "--no-sidecars",
        action="store_true",
        help="Do not link .aux.xml, .ovr, or .tfw sidecar files.",
    )
    parser.add_argument(
        "--allow-issues",
        action="store_true",
        help="Write matched rows even if some CSV rows are missing or ambiguous.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write reports without creating image/label links.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to write manifest CSV. Defaults to output-root/manifest.csv.",
    )
    parser.add_argument(
        "--issues",
        type=Path,
        default=None,
        help="Path to write issues CSV. Defaults to output-root/issues.csv.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    split_csv = args.split_csv.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()
    manifest_path = (
        args.manifest.expanduser().resolve() if args.manifest else output_root / "manifest.csv"
    )
    issues_path = args.issues.expanduser().resolve() if args.issues else output_root / "issues.csv"

    if not args.source_root and not args.image_dir and not args.label_dir:
        home_data = Path("~/data").expanduser().resolve()
        args.source_root = [
            home_data / "Planet8bSR_BC_Labelled" / "10km_tiles",
        ]
        args.image_dir = [home_data / "images"]
        args.label_dir = [home_data / "labels"]

    rows = read_split_rows(split_csv)
    images, labels = collect_candidates(args.source_root, args.image_dir, args.label_dir)
    print(f"split rows: {len(rows)}")
    print(f"image candidates: {len(images)}")
    print(f"label candidates: {len(labels)}")

    matches, issues = match_rows(rows, images, labels)
    print_summary(matches, issues)

    write_manifest(manifest_path, matches, output_root)
    write_issues(issues_path, issues)
    print(f"manifest: {manifest_path}")
    print(f"issues: {issues_path}")

    if issues and not args.allow_issues:
        print(
            "Refusing to create split tree because some rows are missing or ambiguous. "
            "Inspect the issues CSV path above, add more source dirs, or rerun with --allow-issues.",
            file=sys.stderr,
        )
        return 1

    organize(
        matches=matches,
        output_root=output_root,
        link_mode=args.link_mode,
        overwrite=args.overwrite,
        include_sidecars=not args.no_sidecars,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        print(f"organized raw split tree: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
