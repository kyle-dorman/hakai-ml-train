#!/usr/bin/env python3
"""Materialize manifest-owned PlanetScope 8-band experiment views."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shlex
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

FOLD_FIELDS = [
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "acquisition_date",
    "source_temporal_split",
    "experiment_split",
    "selected",
    "selection_reason",
    "view_path",
]
REQUIRED_CHIP = {
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "acquisition_date",
    "row_off",
    "col_off",
}
REQUIRED_TEMPORAL = {
    "image_name_stem",
    "split",
    "dataset",
    "region_id",
    "acquisition_date",
}
REQUIRED_SELECTION = {
    "chip_id",
    "source_tiff_id",
    "region_id",
    "selected_for_training",
    "selection_reason",
    "policy",
}


def read_manifest(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            raise ValueError(f"{path}: missing columns: {sorted(missing)}")
        return list(reader)


def unique_by(
    rows: list[dict[str, str]], key: str, label: str
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row[key]
        if not value or value in result:
            raise ValueError(f"{label}: blank or duplicate {key}: {value!r}")
        result[value] = row
    return result


def parse_bool(value: str, context: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"{context}: expected true or false, got {value!r}")
    return normalized == "true"


def build_baseline_rows(
    chip_rows: list[dict[str, str]],
    temporal_rows: list[dict[str, str]],
    selection_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    chips = unique_by(chip_rows, "chip_id", "chip manifest")
    temporal = unique_by(temporal_rows, "image_name_stem", "temporal manifest")
    selections = unique_by(selection_rows, "chip_id", "training selection")
    if set(chips) != set(selections):
        raise ValueError(
            "training selection chip IDs do not match the canonical manifest"
        )
    policies = {row["policy"] for row in selection_rows}
    if policies != {"exclude_all"}:
        raise ValueError(
            f"expected approved background policy exclude_all, got {policies}"
        )

    canonical_sources: dict[str, tuple[str, str, str]] = {}
    for chip in chip_rows:
        source = chip["source_tiff_id"]
        metadata = (chip["dataset"], chip["region_id"], chip["acquisition_date"])
        if source in canonical_sources and canonical_sources[source] != metadata:
            raise ValueError(f"canonical source metadata conflict: {source}")
        canonical_sources[source] = metadata
    missing_sources = set(canonical_sources) - set(temporal)
    if missing_sources:
        raise ValueError(
            f"canonical sources absent from temporal manifest: {sorted(missing_sources)}"
        )

    source_splits: dict[str, str] = {}
    for source, metadata in canonical_sources.items():
        split_row = temporal[source]
        split = split_row["split"].upper()
        if split not in {"TRAIN", "VAL", "TEST"}:
            raise ValueError(f"invalid temporal split for {source}: {split!r}")
        observed = (
            split_row["dataset"],
            split_row["region_id"],
            split_row["acquisition_date"],
        )
        if observed != metadata:
            raise ValueError(
                f"temporal metadata does not match canonical source {source}"
            )
        source_splits[source] = split

    dates: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for source, split in source_splits.items():
        region = canonical_sources[source][1]
        dates[region][canonical_sources[source][2]].add(split)
    for region, region_dates in dates.items():
        if any(len(splits) != 1 for splits in region_dates.values()):
            raise ValueError(f"acquisition-date group crosses splits in {region}")
        ordered = [next(iter(region_dates[date])) for date in sorted(region_dates)]
        ranks = [{"TRAIN": 0, "VAL": 1, "TEST": 2}[split] for split in ordered]
        if ranks != sorted(ranks):
            raise ValueError(f"temporal split date order is invalid in {region}")

    fold_rows: list[dict[str, str]] = []
    for chip_id in sorted(chips):
        chip = chips[chip_id]
        selection = selections[chip_id]
        if (selection["source_tiff_id"], selection["region_id"]) != (
            chip["source_tiff_id"],
            chip["region_id"],
        ):
            raise ValueError(f"training selection identity mismatch for {chip_id}")
        temporal_split = source_splits[chip["source_tiff_id"]]
        experiment_split = ""
        reason = ""
        if temporal_split == "TRAIN":
            if parse_bool(selection["selected_for_training"], chip_id):
                experiment_split, reason = "train", "selected"
            else:
                reason = "background_policy_exclusion"
        elif temporal_split in {"VAL", "TEST"}:
            if int(chip["row_off"]) % 1024 == 0 and int(chip["col_off"]) % 1024 == 0:
                experiment_split, reason = temporal_split.lower(), "selected"
            else:
                reason = (
                    "validation_overlap_exclusion"
                    if temporal_split == "VAL"
                    else "test_overlap_exclusion"
                )
        fold_rows.append(
            {
                "chip_id": chip_id,
                "chip_path": chip["chip_path"],
                "source_tiff_id": chip["source_tiff_id"],
                "dataset": chip["dataset"],
                "region_id": chip["region_id"],
                "acquisition_date": chip["acquisition_date"],
                "source_temporal_split": temporal_split,
                "experiment_split": experiment_split,
                "selected": str(bool(experiment_split)).lower(),
                "selection_reason": reason,
                "view_path": f"{experiment_split}/{chip_id}.npz"
                if experiment_split
                else "",
            }
        )

    selected_sources = {
        split: len(
            {
                row["source_tiff_id"]
                for row in fold_rows
                if row["experiment_split"] == split
            }
        )
        for split in ("train", "val", "test")
    }
    summary: dict[str, object] = {
        "mode": "baseline",
        "canonical_chip_count": len(fold_rows),
        "canonical_source_tiff_count": len(canonical_sources),
        "temporal_manifest_source_tiff_count": len(temporal_rows),
        "selected_chip_counts": dict(
            sorted(
                Counter(
                    row["experiment_split"]
                    for row in fold_rows
                    if row["experiment_split"]
                ).items()
            )
        ),
        "selected_source_tiff_counts": selected_sources,
        "exclusion_counts": dict(
            sorted(
                Counter(
                    row["selection_reason"]
                    for row in fold_rows
                    if not row["experiment_split"]
                ).items()
            )
        ),
        "regions_by_split": {
            split: sorted(
                {
                    row["region_id"]
                    for row in fold_rows
                    if row["experiment_split"] == split
                }
            )
            for split in ("train", "val", "test")
        },
        "evaluation_grid_stride": 1024,
        "background_policy": "exclude_all",
    }
    return fold_rows, summary


def resolve_sources(dataset_root: Path, rows: list[dict[str, str]]) -> dict[str, Path]:
    root = dataset_root.resolve()
    sources: dict[str, Path] = {}
    for row in rows:
        if not row["experiment_split"]:
            continue
        source = (root / row["chip_path"]).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError(
                f"invalid or missing canonical chip path: {row['chip_path']}"
            )
        sources[row["chip_id"]] = source
    return sources


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FOLD_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def materialize(
    output_root: Path,
    rows: list[dict[str, str]],
    summary: dict[str, object],
    sources: dict[str, Path],
    command: str,
) -> None:
    if output_root.exists():
        raise FileExistsError(f"output already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.staging-", dir=output_root.parent)
    )
    try:
        for split in ("train", "val", "test"):
            (stage / split).mkdir()
        for row in rows:
            if not row["experiment_split"]:
                continue
            destination = stage / row["view_path"]
            os.link(sources[row["chip_id"]], destination)
            if os.stat(sources[row["chip_id"]]).st_ino != destination.stat().st_ino:
                raise RuntimeError(f"hard-link inode mismatch: {row['chip_id']}")
        actual = {
            path.relative_to(stage).as_posix()
            for split in ("train", "val", "test")
            for path in (stage / split).glob("*.npz")
        }
        expected = {row["view_path"] for row in rows if row["experiment_split"]}
        if actual != expected:
            raise RuntimeError("selected-row and materialized-link sets differ")
        write_csv(stage / "fold_manifest.csv", rows)
        summary = {
            **summary,
            "hard_link_count": len(actual),
            "hard_links_verified": True,
        }
        (stage / "fold_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (stage / "materialization_command.txt").write_text(
            command + "\n", encoding="utf-8"
        )
        stage.rename(output_root)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    baseline = subparsers.add_parser("baseline")
    baseline.add_argument(
        "--chip-root", type=Path, required=True, help="Extracted dataset root"
    )
    baseline.add_argument("--chip-manifest", type=Path, required=True)
    baseline.add_argument("--temporal-splits", type=Path, required=True)
    baseline.add_argument("--background-selection", type=Path, required=True)
    baseline.add_argument("--output-root", type=Path, required=True)
    baseline.add_argument("--mode", choices=["hardlink"], default="hardlink")
    baseline.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    chip_rows = read_manifest(args.chip_manifest, REQUIRED_CHIP)
    temporal_rows = read_manifest(args.temporal_splits, REQUIRED_TEMPORAL)
    selection_rows = read_manifest(args.background_selection, REQUIRED_SELECTION)
    rows, summary = build_baseline_rows(chip_rows, temporal_rows, selection_rows)
    sources = resolve_sources(args.chip_root, rows)
    if args.output_root.exists():
        raise FileExistsError(f"output already exists: {args.output_root}")
    if args.dry_run:
        print(json.dumps({**summary, "dry_run": True}, indent=2, sort_keys=True))
        return
    materialize(args.output_root, rows, summary, sources, shlex.join(sys.argv))
    print(
        json.dumps(
            {**summary, "output_root": str(args.output_root)}, indent=2, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
