"""Tiny, independent raw deliveries generated for organizer checks."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

DELIVERY_FIELDS = (
    "delivery_id",
    "kind",
    "path",
    "sha256",
    "file_catalog",
    "evidence",
    "verified_bytes",
    "verified_mtime_ns",
)
MEMBERSHIP_FIELDS = (
    "source_key",
    "region_code",
    "acquisition_date",
    "legacy_source_id",
    "image_delivery_id",
    "image_member",
    "label_delivery_id",
    "label_member",
    "image_sha256",
    "label_sha256",
)
ALIAS_FIELDS = ("source_id", "asset_id", "role", "alias", "alias_type", "evidence")
ASSET_FIELDS = (
    "source_id",
    "asset_id",
    "parent_role",
    "kind",
    "delivery_id",
    "member_relative_path",
    "destination",
    "sha256",
)
REGION_FIELDS = ("region_code", "legacy_region_id", "region_name")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_csv(path: Path, fields, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def raster_bytes(*, bands=1, height=4, width=5, nodata=0, offset=0) -> bytes:
    values = np.arange(bands * height * width, dtype="uint16").reshape(
        bands, height, width
    )
    values %= 5
    with MemoryFile() as memory:
        with memory.open(
            driver="GTiff",
            height=height,
            width=width,
            count=bands,
            dtype="uint16",
            crs="EPSG:32610",
            transform=from_origin(100 + offset, 200, 3, 3),
            nodata=nodata,
        ) as dataset:
            dataset.write(values)
            if bands == 3:
                dataset.descriptions = ("red", "green", "blue")
        return memory.read()


@dataclass
class OrganizerFixture:
    root: Path
    recipe: Path
    settings: Path
    catalog: Path
    payloads: dict[str, bytes]
    source_id: str
    dataset_id: str

    def plan(self):
        from kelpseg.paths import load_paths
        from kelpseg.prepare.organize_inputs import (
            build_organization_plan,
            load_organize_recipe,
        )

        return build_organization_plan(
            load_organize_recipe(self.recipe), load_paths(self.settings)
        )


def make_fixture(root: Path, *, kind="zip", dataset_id="island", multiple=False):
    root.mkdir(parents=True)
    (root / "runs").mkdir()
    catalog = root / "catalog"
    catalog.mkdir()
    region = "nx" if kind == "directory" else "r7"
    source_key = "20230304_scene7_tile2"
    source_id = f"{region}_{source_key}"
    payloads = {
        "strange/original-image.TIF": raster_bytes(
            bands=3 if kind == "directory" else 8, height=8, width=10, nodata=65535
        ),
        "different/annotated.tiff": raster_bytes(height=4, width=5, offset=3),
        "different/second.tiff": raster_bytes(height=4, width=6),
        "support/water.tif": raster_bytes(height=8, width=10),
        "support/world.tfw": b"3\n0\n0\n-3\n101.5\n198.5\n",
        "support/label.TIF.aux.xml": b"<original>annotated.tiff</original>\n",
        "unselected.txt": b"This file is outside the selected scope.\n",
    }
    raw = root / "delivery"
    if kind == "zip":
        raw = raw.with_suffix(".zip")
        with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in payloads.items():
                archive.writestr(name, data)
        identity = digest(raw.read_bytes())
        file_catalog = ""
    else:
        raw.mkdir()
        for name, data in payloads.items():
            target = raw / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        file_catalog = "file_catalog.csv"
        write_csv(
            catalog / file_catalog,
            ("member_relative_path", "bytes", "sha256"),
            [
                {
                    "member_relative_path": name,
                    "bytes": len(data),
                    "sha256": digest(data),
                }
                for name, data in sorted(payloads.items())
            ],
        )
        identity = digest((catalog / file_catalog).read_bytes())
    write_csv(
        catalog / "deliveries.csv",
        DELIVERY_FIELDS,
        [
            {
                "delivery_id": "supply",
                "kind": kind,
                "path": raw.name,
                "sha256": identity,
                "file_catalog": file_catalog,
                "evidence": "fixture",
                "verified_bytes": "",
                "verified_mtime_ns": "",
            }
        ],
    )
    row = {
        "source_key": source_key,
        "region_code": region,
        "acquisition_date": "2023-03-04",
        "legacy_source_id": "Original-Mixed-Case-Name",
        "image_delivery_id": "supply",
        "image_member": "strange/original-image.TIF",
        "label_delivery_id": "supply",
        "label_member": "different/annotated.tiff",
        "image_sha256": "",
        "label_sha256": "",
    }
    rows = [row]
    if multiple:
        rows += [
            dict(
                row,
                source_key="20230304_scene7_tile3",
                label_member="different/second.tiff",
            ),
            dict(row, source_key="20230304_scene7_tile4"),
        ]
    write_csv(catalog / "membership.csv", MEMBERSHIP_FIELDS, rows)
    aliases = []
    for pair in rows:
        owner = f"{region}_{pair['source_key']}"
        aliases += [
            dict(
                source_id=owner,
                asset_id="",
                role="image",
                alias="Repeated long alias.TIF",
                alias_type="recorded_legacy",
                evidence="fixture",
            )
        ]
    aliases += [
        dict(
            source_id=source_id,
            asset_id="label_aux",
            role="label",
            alias="label.TIF.aux.xml",
            alias_type="archive_member",
            evidence="fixture",
        )
    ]
    write_csv(catalog / "aliases.csv", ALIAS_FIELDS, aliases)
    write_csv(
        catalog / "assets.csv",
        ASSET_FIELDS,
        [
            dict(
                source_id=source_id,
                asset_id="mask",
                parent_role="image",
                kind="nan_mask",
                delivery_id="supply",
                member_relative_path="support/water.tif",
                destination=f"masks/{source_id}.tif",
                sha256="",
            ),
            dict(
                source_id=source_id,
                asset_id="world",
                parent_role="image",
                kind="world_file",
                delivery_id="supply",
                member_relative_path="support/world.tfw",
                destination=f"images/{source_id}.tfw",
                sha256="",
            ),
            dict(
                source_id=source_id,
                asset_id="label_aux",
                parent_role="label",
                kind="auxiliary_xml",
                delivery_id="supply",
                member_relative_path="support/label.TIF.aux.xml",
                destination=f"labels/{source_id}.tif.aux.xml",
                sha256="",
            ),
        ],
    )
    write_csv(
        root / "regions.csv",
        REGION_FIELDS,
        [
            dict(
                region_code=region,
                legacy_region_id="Independent Area",
                region_name="Coast",
            )
        ],
    )
    recipe = root / "recipe.toml"
    recipe.write_text(
        f'schema_version = 1\ndataset_id = "{dataset_id}"\nrelease_id = "v1"\ninput_catalog = "catalog"\nregions = "regions.csv"\n'
    )
    settings = root / "paths.toml"
    settings.write_text('[paths]\ndata_root = "."\nruns_root = "runs"\n')
    return OrganizerFixture(
        root, recipe, settings, catalog, payloads, source_id, dataset_id
    )


def inventory(root: Path):
    """Byte content and names make write-free planning observable."""
    return {
        str(path.relative_to(root)): digest(path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    }


def manifest(path: Path):
    return json.loads((path / "manifest.json").read_text())
