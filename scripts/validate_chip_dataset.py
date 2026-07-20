from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import rasterio
from rasterio.windows import Window

from src.prepare.nodata import declared_nodata_values, nodata_mask

IGNORE_INDEX = -100
NODATA_BIN_EDGES = (0, 1, 5, 10, 20, 30, 40, 50, 75, 100)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def _write_csv_atomic(
    path: Path, rows: list[dict[str, Any]], fieldnames: list[str]
) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w") as file:
        json.dump(payload, file, indent=2, sort_keys=True)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _class_presence(row: dict[str, str]) -> str:
    foreground = int(row["class_1_pixel_count"])
    background = int(row["class_0_pixel_count"])
    nodata = int(row["nodata_pixel_count"])
    if foreground > 0:
        return "positive"
    if background > 0 and nodata > 0:
        return "mixed_background_nodata"
    if background > 0:
        return "clean_background_only"
    return "ignore_only"


def _nodata_bin(value: float) -> str:
    if value == 0:
        return "0"
    lower = 0
    for upper in NODATA_BIN_EDGES[1:]:
        if value <= upper:
            return f"({lower},{upper}]"
        lower = upper
    raise RuntimeError(f"nodata_pct outside [0, 100]: {value}")


def _group_summary(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row[key]
        if value not in grouped:
            grouped[value] = {
                "chip_count": 0,
                "source_ids": set(),
                "class_0_pixel_count": 0,
                "class_1_pixel_count": 0,
                "ignore_pixel_count": 0,
                "nodata_pixel_count": 0,
                "class_presence": Counter(),
            }
        item = grouped[value]
        item["chip_count"] += 1
        item["source_ids"].add(row["source_tiff_id"])
        for count_key in (
            "class_0_pixel_count",
            "class_1_pixel_count",
            "ignore_pixel_count",
            "nodata_pixel_count",
        ):
            item[count_key] += int(row[count_key])
        item["class_presence"][_class_presence(row)] += 1
    result: dict[str, dict[str, Any]] = {}
    for value, item in sorted(grouped.items()):
        item["source_count"] = len(item.pop("source_ids"))
        item["class_presence"] = dict(sorted(item["class_presence"].items()))
        result[value] = item
    return result


def _validate_sample(
    *,
    rows: list[dict[str, str]],
    chip_root: Path,
    raw_root: Path,
    chip_size: int,
) -> list[str]:
    selected: dict[str, dict[str, str]] = {}
    for key in ("region_id",):
        first_by_value: dict[str, dict[str, str]] = {}
        for row in rows:
            first_by_value.setdefault(row[key], row)
        selected.update({row["chip_id"]: row for row in first_by_value.values()})
    first_by_bin: dict[str, dict[str, str]] = {}
    first_by_presence: dict[str, dict[str, str]] = {}
    for row in rows:
        first_by_bin.setdefault(_nodata_bin(float(row["nodata_pct"])), row)
        first_by_presence.setdefault(_class_presence(row), row)
        if int(row["chip_width"]) < chip_size or int(row["chip_height"]) < chip_size:
            selected[row["chip_id"]] = row
    selected.update({row["chip_id"]: row for row in first_by_bin.values()})
    selected.update({row["chip_id"]: row for row in first_by_presence.values()})

    for row in selected.values():
        chip_path = chip_root / row["chip_path"]
        with np.load(chip_path) as chip:
            if set(chip.files) != {"image", "label"}:
                raise RuntimeError(f"Unexpected NPZ keys: {chip_path}")
            image = chip["image"]
            label = chip["label"]
        shape = (int(row["chip_height"]), int(row["chip_width"]))
        if image.shape != (*shape, 8) or label.shape != shape:
            raise RuntimeError(f"Sample shape mismatch: {chip_path}")
        if (
            str(image.dtype) != row["image_dtype"]
            or str(label.dtype) != row["label_dtype"]
        ):
            raise RuntimeError(f"Sample dtype mismatch: {chip_path}")
        if np.count_nonzero(label == 0) != int(row["class_0_pixel_count"]):
            raise RuntimeError(f"Sample class-0 mismatch: {chip_path}")
        if np.count_nonzero(label == 1) != int(row["class_1_pixel_count"]):
            raise RuntimeError(f"Sample class-1 mismatch: {chip_path}")
        if np.count_nonzero(label == IGNORE_INDEX) != int(row["ignore_pixel_count"]):
            raise RuntimeError(f"Sample ignore mismatch: {chip_path}")
        source_id = row["source_tiff_id"]
        with rasterio.open(raw_root / "all" / "images" / f"{source_id}.tif") as source:
            source_nodata = declared_nodata_values(
                source, retained_bands=8, missing_value=0
            )
            nodata = int(
                np.count_nonzero(nodata_mask(image, source_nodata, band_axis=-1))
            )
            if nodata != int(row["nodata_pixel_count"]):
                raise RuntimeError(f"Sample nodata mismatch: {chip_path}")
            if source.width != int(row["source_width"]) or source.height != int(
                row["source_height"]
            ):
                raise RuntimeError(f"Sample source shape mismatch: {source_id}")
            if source.crs is None or source.crs.to_string() != row["source_crs"]:
                raise RuntimeError(f"Sample source CRS mismatch: {source_id}")
            window = Window(
                int(row["col_off"]),
                int(row["row_off"]),
                int(row["chip_width"]),
                int(row["chip_height"]),
            )
            expected_bounds = rasterio.windows.bounds(window, source.transform)
        actual_bounds = tuple(
            float(row[key]) for key in ("minx", "miny", "maxx", "maxy")
        )
        if not np.allclose(actual_bounds, expected_bounds):
            raise RuntimeError(f"Sample bounds mismatch: {chip_path}")
    return sorted(selected)


def validate_chip_dataset(
    *,
    chip_root: Path,
    raw_root: Path,
    source_manifest: Path,
    chip_size: int = 1024,
    chip_stride: int = 512,
) -> dict[str, Any]:
    manifest_path = chip_root / "chip_manifest.csv"
    rows = _read_csv(manifest_path)
    sources = _read_csv(source_manifest)
    if not rows or not sources:
        raise RuntimeError("Chip or source manifest is empty")
    source_by_id = {row["source_tiff_id"]: row for row in sources}
    if len(source_by_id) != len(sources):
        raise RuntimeError("Duplicate source IDs in source manifest")

    chip_ids: set[str] = set()
    chip_ids_lower: set[str] = set()
    chip_paths: set[str] = set()
    chip_paths_lower: set[str] = set()
    rows_by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    class_presence = Counter()
    nodata_bins = Counter()
    pixel_totals = Counter()
    partial_chip_count = 0
    total_compressed_bytes = 0

    for row in rows:
        chip_id = row["chip_id"]
        chip_path_text = row["chip_path"]
        chip_path = Path(chip_path_text)
        if chip_id in chip_ids or chip_id.lower() in chip_ids_lower:
            raise RuntimeError(f"Duplicate chip ID: {chip_id}")
        if chip_path_text in chip_paths or chip_path_text.lower() in chip_paths_lower:
            raise RuntimeError(f"Duplicate chip path: {chip_path_text}")
        if chip_path.is_absolute() or ".." in chip_path.parts:
            raise RuntimeError(f"Nonportable chip path: {chip_path_text}")
        chip_ids.add(chip_id)
        chip_ids_lower.add(chip_id.lower())
        chip_paths.add(chip_path_text)
        chip_paths_lower.add(chip_path_text.lower())

        source_id = row["source_tiff_id"]
        source = source_by_id.get(source_id)
        if source is None:
            raise RuntimeError(f"Chip does not join to source manifest: {chip_id}")
        for key in ("dataset", "region_id", "region_name", "acquisition_date"):
            if row[key] != source[key]:
                raise RuntimeError(f"Source identity mismatch for {chip_id}: {key}")
        rows_by_source[source_id].append(row)

        width = int(row["chip_width"])
        height = int(row["chip_height"])
        source_width = int(row["source_width"])
        source_height = int(row["source_height"])
        col_off = int(row["col_off"])
        row_off = int(row["row_off"])
        if (
            col_off < 0
            or row_off < 0
            or col_off + width > source_width
            or row_off + height > source_height
        ):
            raise RuntimeError(f"Chip window outside source: {chip_id}")
        for dimension, source_dimension, offset in (
            (width, source_width, col_off),
            (height, source_height, row_off),
        ):
            if source_dimension < chip_size:
                if dimension != source_dimension or offset != 0:
                    raise RuntimeError(f"Invalid small-source window: {chip_id}")
            elif dimension != chip_size or offset % chip_stride != 0:
                raise RuntimeError(f"Invalid canonical grid window: {chip_id}")
        if width < chip_size or height < chip_size:
            partial_chip_count += 1

        total = int(row["total_pixel_count"])
        if total != width * height:
            raise RuntimeError(f"Total pixel count mismatch: {chip_id}")
        stored = (
            int(row["class_0_pixel_count"])
            + int(row["class_1_pixel_count"])
            + int(row["ignore_pixel_count"])
        )
        if stored != total:
            raise RuntimeError(f"Class counts do not reconcile: {chip_id}")
        nodata = int(row["nodata_pixel_count"])
        expected_pct = 100.0 * nodata / total
        if not np.isclose(expected_pct, float(row["nodata_pct"])):
            raise RuntimeError(f"Nodata percentage mismatch: {chip_id}")

        path = chip_root / chip_path
        if not path.is_file():
            raise RuntimeError(f"Missing NPZ: {path}")
        total_compressed_bytes += path.stat().st_size
        class_presence[_class_presence(row)] += 1
        nodata_bins[_nodata_bin(float(row["nodata_pct"]))] += 1
        for key in (
            "total_pixel_count",
            "class_0_pixel_count",
            "class_1_pixel_count",
            "ignore_pixel_count",
            "nodata_pixel_count",
        ):
            pixel_totals[key] += int(row[key])

    unknown_sources = sorted(set(rows_by_source) - set(source_by_id))
    if unknown_sources:
        raise RuntimeError(f"Chips reference unknown sources: {unknown_sources}")
    sources_without_active_chips = sorted(set(source_by_id) - set(rows_by_source))
    filtered_collection = (
        chip_root / "filter_history/nodata_50/filter_metadata.json"
    ).is_file()
    if sources_without_active_chips and not filtered_collection:
        raise RuntimeError(f"Sources without chips: {sources_without_active_chips}")
    filesystem_paths = {
        path.relative_to(chip_root).as_posix()
        for path in (chip_root / "all").glob("*.npz")
    }
    if filesystem_paths != chip_paths:
        raise RuntimeError(
            "Manifest/filesystem mismatch: "
            f"missing={sorted(chip_paths - filesystem_paths)[:5]}, "
            f"extra={sorted(filesystem_paths - chip_paths)[:5]}"
        )
    fragment_ids = {
        path.stem for path in (chip_root / "manifest_parts" / "all").glob("*.csv")
    }
    if fragment_ids != set(source_by_id):
        raise RuntimeError("Completion fragments do not match source manifest")
    issue_files = list((chip_root / ".chip_issues").glob("**/*.*"))
    staging_files = list((chip_root / ".chip_staging").glob("**/*.*"))
    if issue_files or staging_files:
        raise RuntimeError(
            f"Unresolved issue/staging files: issues={issue_files}, staging={staging_files}"
        )

    sampled_chip_ids = _validate_sample(
        rows=rows,
        chip_root=chip_root,
        raw_root=raw_root,
        chip_size=chip_size,
    )

    source_output_rows: list[dict[str, Any]] = []
    for source_id, source_rows in sorted(rows_by_source.items()):
        first = source_rows[0]
        presence = Counter(_class_presence(row) for row in source_rows)
        source_output_rows.append(
            {
                "source_tiff_id": source_id,
                "dataset": first["dataset"],
                "region_id": first["region_id"],
                "region_name": first["region_name"],
                "acquisition_date": first["acquisition_date"],
                "year": first["acquisition_date"][:4],
                "source_width": first["source_width"],
                "source_height": first["source_height"],
                "chip_count": len(source_rows),
                "partial_chip_count": sum(
                    int(row["chip_width"]) < chip_size
                    or int(row["chip_height"]) < chip_size
                    for row in source_rows
                ),
                "positive_chip_count": presence["positive"],
                "clean_background_only_chip_count": presence["clean_background_only"],
                "mixed_background_nodata_chip_count": presence[
                    "mixed_background_nodata"
                ],
                "ignore_only_chip_count": presence["ignore_only"],
                "total_pixel_count": sum(
                    int(row["total_pixel_count"]) for row in source_rows
                ),
                "class_0_pixel_count": sum(
                    int(row["class_0_pixel_count"]) for row in source_rows
                ),
                "class_1_pixel_count": sum(
                    int(row["class_1_pixel_count"]) for row in source_rows
                ),
                "ignore_pixel_count": sum(
                    int(row["ignore_pixel_count"]) for row in source_rows
                ),
                "nodata_pixel_count": sum(
                    int(row["nodata_pixel_count"]) for row in source_rows
                ),
            }
        )
    counts_path = chip_root / "chip_counts_by_source.csv"
    _write_csv_atomic(counts_path, source_output_rows, list(source_output_rows[0]))

    rows_with_year = [dict(row, year=row["acquisition_date"][:4]) for row in rows]
    summary: dict[str, Any] = {
        "artifact": {
            "chip_root": str(chip_root),
            "raw_root": str(raw_root),
            "source_manifest": str(source_manifest),
            "chip_manifest": str(manifest_path),
            "chip_manifest_sha256": _sha256(manifest_path),
        },
        "parameters": {
            "chip_size": chip_size,
            "stride": chip_stride,
            "num_bands": 8,
            "image_dtype": "uint16",
            "label_dtype": "int64",
            "remap": [0, 1, 0, -100, 0],
            "ignore_index": IGNORE_INDEX,
            "nodata_definition": (
                "all eight retained image bands equal their source TIFF's effective "
                "nodata value, including explicit zero for wholly missing metadata"
            ),
        },
        "inventory": {
            "manifest_row_count": len(rows),
            "npz_file_count": len(filesystem_paths),
            "source_count": len(source_by_id),
            "region_count": len({row["region_id"] for row in rows}),
            "fragment_count": len(fragment_ids),
            "partial_chip_count": partial_chip_count,
            "total_compressed_bytes": total_compressed_bytes,
        },
        "pixel_counts_across_overlapping_chips": dict(pixel_totals),
        "class_presence_chip_counts": dict(sorted(class_presence.items())),
        "nodata_percentage_bin_chip_counts": dict(sorted(nodata_bins.items())),
        "by_dataset": _group_summary(rows, "dataset"),
        "by_region": _group_summary(rows, "region_id"),
        "by_year": _group_summary(rows_with_year, "year"),
        "validation": {
            "all_active_sources_have_chips": True,
            "sources_without_active_chips": sources_without_active_chips,
            "filtered_collection_allows_removed_sources": filtered_collection,
            "manifest_npz_bijection": True,
            "source_manifest_join": True,
            "manifest_counts_reconcile": True,
            "case_insensitive_ids_and_paths_unique": True,
            "canonical_window_grid_valid": True,
            "small_source_windows_are_true_size": True,
            "issue_and_staging_files_absent": True,
            "sampled_npz_count": len(sampled_chip_ids),
            "sampled_chip_ids": sampled_chip_ids,
            "sampled_npz_shapes_dtypes_counts_nodata_and_bounds_match": True,
            "full_npz_validation": (
                "The completed production command revalidated every fragment and NPZ "
                "before atomically consolidating chip_manifest.csv."
            ),
        },
    }
    _write_json_atomic(chip_root / "chip_qa_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("chip_root", type=Path)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--chip-size", type=int, default=1024)
    parser.add_argument("--chip-stride", type=int, default=512)
    args = parser.parse_args()
    summary = validate_chip_dataset(
        chip_root=args.chip_root,
        raw_root=args.raw_root,
        source_manifest=args.source_manifest,
        chip_size=args.chip_size,
        chip_stride=args.chip_stride,
    )
    print(json.dumps(summary["inventory"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
