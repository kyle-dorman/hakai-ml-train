"""Create dissolved region footprints and centroids from source-TIFF bounds."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import rasterio
from rasterio.warp import transform_geom
from shapely import union_all
from shapely.geometry import box, mapping, shape

REQUIRED_COLUMNS = {
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "merged_image",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dissolve the WGS84 bounding-box polygons of canonical source TIFFs "
            "into one polygon and one centroid GeoJSON feature per region."
        )
    )
    parser.add_argument("manifest", type=Path, help="Canonical raster_manifest.csv")
    parser.add_argument("output", type=Path, help="Output GeoJSON path")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output file.",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as manifest_file:
        reader = csv.DictReader(manifest_file)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Manifest is missing required columns: {sorted(missing)}")
        rows = list(reader)

    if not rows:
        raise ValueError("Manifest contains no source TIFF rows")

    source_ids = [row["source_tiff_id"] for row in rows]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Manifest contains duplicate source_tiff_id values")
    return rows


def source_bbox_wgs84(path: Path):
    with rasterio.open(path) as source:
        if source.crs is None:
            raise ValueError(f"Source TIFF has no CRS: {path}")
        native_bbox = mapping(box(*source.bounds))
        return shape(
            transform_geom(
                source.crs,
                "EPSG:4326",
                native_bbox,
                precision=7,
            )
        )


def region_sort_key(region_id: str) -> tuple[bool, str]:
    return (region_id == "bc", region_id)


def build_feature_collection(rows: list[dict[str, str]]) -> dict:
    regions = defaultdict(
        lambda: {
            "dataset": None,
            "region_name": None,
            "source_ids": [],
            "geometries": [],
        }
    )

    for row in rows:
        entry = regions[row["region_id"]]
        if entry["dataset"] not in (None, row["dataset"]):
            raise ValueError(f"Inconsistent dataset for {row['region_id']}")
        if entry["region_name"] not in (None, row["region_name"]):
            raise ValueError(f"Inconsistent region name for {row['region_id']}")

        entry["dataset"] = row["dataset"]
        entry["region_name"] = row["region_name"]
        entry["source_ids"].append(row["source_tiff_id"])
        entry["geometries"].append(source_bbox_wgs84(Path(row["merged_image"])))

    features = []
    for region_id in sorted(regions, key=region_sort_key):
        entry = regions[region_id]
        dissolved = union_all(entry["geometries"])
        if dissolved.geom_type not in {"Polygon", "MultiPolygon"}:
            raise ValueError(
                f"Unexpected geometry type for {region_id}: {dissolved.geom_type}"
            )
        if not dissolved.is_valid:
            raise ValueError(f"Dissolved geometry is invalid for {region_id}")

        region_number = (
            int(region_id.removeprefix("ca_")) if region_id.startswith("ca_") else None
        )
        properties = {
            "region_id": region_id,
            "region_number": region_number,
            "region_name": entry["region_name"],
            "dataset": entry["dataset"],
            "source_tiff_count": len(entry["source_ids"]),
            "geometry_method": "dissolved_source_tiff_bboxes",
        }
        features.extend(
            [
                {
                    "type": "Feature",
                    "properties": {
                        **properties,
                        "feature_type": "region_polygon",
                    },
                    "geometry": mapping(dissolved),
                },
                {
                    "type": "Feature",
                    "properties": {
                        **properties,
                        "feature_type": "region_centroid",
                    },
                    "geometry": mapping(dissolved.centroid),
                },
            ]
        )

    return {
        "type": "FeatureCollection",
        "name": "planet8b_region_footprints",
        "features": features,
    }


def main() -> None:
    args = parse_args()
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(
            f"Output already exists; pass --overwrite to replace it: {args.output}"
        )

    rows = load_manifest(args.manifest)
    collection = build_feature_collection(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(collection, indent=2) + "\n")

    print(f"Wrote {len(collection['features'])} features to {args.output}")
    print(f"Source TIFFs represented: {len(rows)}")


if __name__ == "__main__":
    main()
