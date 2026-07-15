#!/usr/bin/env python3
"""Create a region-balanced, chronological baseline split manifest.

The splitter treats acquisition dates as indivisible groups, so rasters acquired
on the same day in the same region cannot be divided across train, validation,
and test. It searches all chronological cut points, targets configurable split
fractions, and gives a small preference to cuts that fall on year boundaries.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CA_REGION_NAMES = {
    "001": "baja_islaNavidad",
    "002": "baja_puntaEugenia",
    "003": "sanDiego",
    "004": "palosVerdes",
    "005": "channelIslands",
    "006": "channelIslands",
    "007": "refugioStateBeach",
    "008": "bigSur",
    "009": "monterey",
    "010": "northernCalifornia",
    "011": "calvertIsland",
}

DATE_RE = re.compile(r"^(?P<date>\d{8})_")
CA_RE = re.compile(r"^(?P<region>\d{3})_(?P<date>\d{8})_")


@dataclass(frozen=True)
class RasterRecord:
    image_name_stem: str
    dataset: str
    region_id: str
    region_name: str
    acquisition_date: date
    source_image: Path
    source_label: Path


def parse_date(value: str) -> date:
    return date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}")


def tif_files(directory: Path) -> dict[str, Path]:
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory does not exist: {directory}")

    files: dict[str, Path] = {}
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}:
            key = path.stem.casefold()
            if key in files:
                raise ValueError(f"Duplicate TIFF stem in {directory}: {path.stem}")
            files[key] = path
    return files


def paired_tifs(images_dir: Path, labels_dir: Path) -> list[tuple[Path, Path]]:
    images = tif_files(images_dir)
    labels = tif_files(labels_dir)
    missing_labels = sorted(set(images) - set(labels))
    missing_images = sorted(set(labels) - set(images))
    if missing_labels or missing_images:
        message = []
        if missing_labels:
            message.append(f"{len(missing_labels)} images lack labels")
        if missing_images:
            message.append(f"{len(missing_images)} labels lack images")
        raise ValueError(
            f"Pairing failed for {images_dir} and {labels_dir}: " + "; ".join(message)
        )
    return [(images[key], labels[key]) for key in sorted(images)]


def load_california(ca_root: Path) -> list[RasterRecord]:
    records = []
    for image, label in paired_tifs(ca_root / "images", ca_root / "labels"):
        match = CA_RE.match(image.stem)
        if match is None:
            raise ValueError(f"Cannot parse California region/date: {image.name}")
        region_id = f"ca_{match['region']}"
        records.append(
            RasterRecord(
                image_name_stem=image.stem,
                dataset="ca",
                region_id=region_id,
                region_name=CA_REGION_NAMES.get(
                    match["region"], f"region_{match['region']}"
                ),
                acquisition_date=parse_date(match["date"]),
                source_image=image.resolve(),
                source_label=label.resolve(),
            )
        )
    return records


def load_bc(bc_tiles_root: Path) -> list[RasterRecord]:
    records = []
    seen_stems: set[str] = set()
    for source_split in ("train", "val", "test"):
        split_root = bc_tiles_root / source_split
        if not split_root.exists():
            continue
        for image, label in paired_tifs(split_root / "images", split_root / "labels"):
            stem_key = image.stem.casefold()
            if stem_key in seen_stems:
                raise ValueError(
                    f"Duplicate BC TIFF stem across source splits: {image.stem}"
                )
            seen_stems.add(stem_key)
            match = DATE_RE.match(image.stem)
            if match is None:
                raise ValueError(f"Cannot parse BC acquisition date: {image.name}")
            records.append(
                RasterRecord(
                    image_name_stem=image.stem,
                    dataset="bc",
                    region_id="bc",
                    region_name="british_columbia",
                    acquisition_date=parse_date(match["date"]),
                    source_image=image.resolve(),
                    source_label=label.resolve(),
                )
            )
    return records


def choose_cut_points(
    date_groups: list[tuple[date, list[RasterRecord]]],
    fractions: tuple[float, float, float],
) -> tuple[int, int]:
    """Choose chronological cuts using balance, year boundaries, then date gaps."""
    if len(date_groups) < 3:
        raise ValueError(
            "At least three distinct acquisition dates are required for a "
            "chronological train/val/test split"
        )

    group_sizes = [len(records) for _, records in date_groups]
    total = sum(group_sizes)
    cumulative = [0]
    for size in group_sizes:
        cumulative.append(cumulative[-1] + size)

    best: tuple[tuple[float, float, int, int], tuple[int, int]] | None = None
    for first_cut in range(1, len(date_groups) - 1):
        for second_cut in range(first_cut + 1, len(date_groups)):
            counts = (
                cumulative[first_cut],
                cumulative[second_cut] - cumulative[first_cut],
                total - cumulative[second_cut],
            )
            actual = tuple(count / total for count in counts)
            balance_error = sum(
                abs(observed - target)
                for observed, target in zip(actual, fractions, strict=True)
            )

            boundaries = (
                (first_cut - 1, first_cut),
                (second_cut - 1, second_cut),
            )
            year_boundary_count = sum(
                date_groups[left][0].year != date_groups[right][0].year
                for left, right in boundaries
            )
            gap_days = sum(
                (date_groups[right][0] - date_groups[left][0]).days
                for left, right in boundaries
            )

            # Balance remains the main constraint. A year-boundary cut is worth
            # up to five percentage points of split-fraction error, after which
            # larger chronological gaps break remaining ties.
            score = (
                balance_error - (0.05 * year_boundary_count),
                -float(gap_days),
                first_cut,
                second_cut,
            )
            candidate = (score, (first_cut, second_cut))
            if best is None or candidate < best:
                best = candidate

    assert best is not None
    return best[1]


def assign_splits(
    records: list[RasterRecord], fractions: tuple[float, float, float]
) -> dict[str, str]:
    by_region: dict[str, list[RasterRecord]] = defaultdict(list)
    for record in records:
        by_region[record.region_id].append(record)

    assignments = {}
    for _region_id, region_records in sorted(by_region.items()):
        by_date: dict[date, list[RasterRecord]] = defaultdict(list)
        for record in region_records:
            by_date[record.acquisition_date].append(record)
        date_groups = sorted(by_date.items())
        first_cut, second_cut = choose_cut_points(date_groups, fractions)
        for index, (_, group) in enumerate(date_groups):
            split = "TRAIN" if index < first_cut else "VAL"
            if index >= second_cut:
                split = "TEST"
            for record in group:
                assignments[record.image_name_stem] = split
    return assignments


def write_manifest(
    output: Path, records: list[RasterRecord], assignments: dict[str, str]
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "image_name_stem",
        "split",
        "dataset",
        "region_id",
        "region_name",
        "acquisition_date",
        "acquisition_year",
    ]
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in sorted(
            records,
            key=lambda item: (
                item.region_id,
                item.acquisition_date,
                item.image_name_stem,
            ),
        ):
            writer.writerow(
                {
                    "image_name_stem": record.image_name_stem,
                    "split": assignments[record.image_name_stem],
                    "dataset": record.dataset,
                    "region_id": record.region_id,
                    "region_name": record.region_name,
                    "acquisition_date": record.acquisition_date.isoformat(),
                    "acquisition_year": record.acquisition_date.year,
                }
            )


def print_summary(records: list[RasterRecord], assignments: dict[str, str]) -> None:
    summary: dict[tuple[str, str], list[RasterRecord]] = defaultdict(list)
    for record in records:
        summary[(record.region_id, assignments[record.image_name_stem])].append(record)

    print("region split count first_date last_date years")
    for region_id in sorted({record.region_id for record in records}):
        for split in ("TRAIN", "VAL", "TEST"):
            split_records = summary[(region_id, split)]
            dates = sorted(record.acquisition_date for record in split_records)
            years = sorted({value.year for value in dates})
            print(
                region_id,
                split,
                len(split_records),
                dates[0].isoformat(),
                dates[-1].isoformat(),
                ",".join(map(str, years)),
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca-root", type=Path, required=True)
    parser.add_argument("--bc-tiles-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--val-fraction", type=float, default=0.15)
    parser.add_argument("--test-fraction", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fractions = (args.train_fraction, args.val_fraction, args.test_fraction)
    if any(value <= 0 for value in fractions) or abs(sum(fractions) - 1.0) > 1e-9:
        raise ValueError("Split fractions must be positive and sum to 1.0")

    records = load_california(args.ca_root) + load_bc(args.bc_tiles_root)
    assignments = assign_splits(records, fractions)
    write_manifest(args.output, records, assignments)
    print_summary(records, assignments)
    print(f"Wrote {len(records)} raster assignments to {args.output}")


if __name__ == "__main__":
    main()
