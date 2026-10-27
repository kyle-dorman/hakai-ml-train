"""Optional organized parents enrich directory cleanup only after verification."""

import hashlib
import json

import numpy as np
import pytest
import rasterio
from organize_fixtures import digest, make_fixture, read_csv, write_csv

from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.clean import clean_dataset, verify_cleaned_release
from kelpseg.prepare.clean_inputs import CleanRecipe, build_clean_plan
from kelpseg.prepare.organize import organize_dataset, verify_organized_release


def _organized_parent(tmp_path):
    fixture = make_fixture(tmp_path / "raw", kind="directory", dataset_id="independent")
    # The organizer's generic uint16 image includes valid all-band zeros with
    # declared 65535 nodata. Give this independent cleaning fixture collision-free
    # valid values before organization, and update the declared delivery hashes.
    source = fixture.root / "delivery/strange/original-image.TIF"
    with rasterio.open(source, "r+") as raster:
        values = raster.read()
        values[:, np.all(values == 0, axis=0)] = 9
        raster.write(values)
    # Organization accepts arbitrary TIFF payloads. Cleanup deliberately accepts
    # uint8 categories, so establish that supported fixture before organizing.
    label_path = fixture.root / "delivery/different/annotated.tiff"
    with rasterio.open(label_path) as labels:
        categories = labels.read().astype(np.uint8)
        profile = labels.profile
    profile["dtype"] = "uint8"
    with rasterio.open(label_path, "w", **profile) as labels:
        labels.write(categories)
    catalog_path = fixture.catalog / "file_catalog.csv"
    rows = read_csv(catalog_path)
    for row in rows:
        if row["member_relative_path"] in {
            "strange/original-image.TIF",
            "different/annotated.tiff",
        }:
            changed = fixture.root / "delivery" / row["member_relative_path"]
            row["bytes"] = str(changed.stat().st_size)
            row["sha256"] = digest(changed.read_bytes())
    write_csv(catalog_path, rows[0].keys(), rows)
    deliveries_path = fixture.catalog / "deliveries.csv"
    deliveries = read_csv(deliveries_path)
    deliveries[0]["sha256"] = digest(catalog_path.read_bytes())
    write_csv(deliveries_path, deliveries[0].keys(), deliveries)
    parent = organize_dataset(fixture.plan())
    verify_organized_release(parent)
    plan = build_clean_plan(
        parent / "images",
        parent / "labels",
        tmp_path / "cleaned",
        CleanRecipe(image_band_counts=(3,)),
        parent=parent,
    )
    return fixture, parent, plan


def test_verified_parent_retains_identities_aliases_and_original_bytes(tmp_path):
    fixture, parent, plan = _organized_parent(tmp_path)
    unchanged = {
        path: (path.read_bytes(), path.stat().st_mode)
        for path in parent.rglob("*")
        if path.is_file()
    }
    output = clean_dataset(plan)
    assert verify_cleaned_release(output)["status"] == "complete"
    record = json.loads((output / "sources.json").read_bytes())["sources"][0]
    assert record["identity"]["source_id"] == fixture.source_id
    assert record["identity"]["region_code"] == "nx"
    assert record["identity"]["acquisition_date"] == "2023-03-04"
    assert record["identity"]["dataset_id"] == "independent"
    assert record["identity"]["image_delivery_id"] == "supply"
    assert record["identity"]["image_member"] == "strange/original-image.TIF"
    for name in (
        "sources.csv",
        "filename_aliases.csv",
        "regions.csv",
        "assets.csv",
        "manifest.json",
    ):
        assert (output / "parent" / name).read_bytes() == (parent / name).read_bytes()
    snapshots = json.loads((output / "sources.json").read_bytes())["inactive_assets"]
    assert (
        snapshots["parent/manifest.json"]["sha256"]
        == hashlib.sha256((parent / "manifest.json").read_bytes()).hexdigest()
    )
    assert any("masks/" in name for name in snapshots)
    assert not (output / "masks").exists()
    assert not list((output / "images").rglob("*.tfw"))
    with rasterio.open(output / "images" / f"{fixture.source_id}.tif") as image:
        assert image.count == 3 and image.nodata == 0
    with rasterio.open(output / "labels" / f"{fixture.source_id}.tif") as label:
        assert label.nodata == 3 and {0, 1, 2, 3, 4}.issuperset(np.unique(label.read()))
    assert all(
        (path.read_bytes(), path.stat().st_mode) == expected
        for path, expected in unchanged.items()
    )


def test_changed_parent_asset_fails_hash_verification(tmp_path):
    fixture, parent, plan = _organized_parent(tmp_path)
    companion = parent / "masks" / f"{fixture.source_id}.tif"
    companion.write_bytes(companion.read_bytes() + b"changed-parent-payload")
    with pytest.raises(PreparationError, match="Byte verification failed"):
        clean_dataset(plan)
    assert not plan.output.exists()


def test_parent_duplicate_identities_rejected_even_with_consistent_file_hash(tmp_path):
    _, parent, plan = _organized_parent(tmp_path)
    sources = parent / "sources.csv"
    rows = read_csv(sources)
    write_csv(sources, rows[0].keys(), rows + [rows[0]])
    # Integrity alone cannot establish a unique identity mapping. Authenticate
    # the edited table's bytes so this fixture exercises that separate check.
    manifest_path = parent / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"]["sources.csv"] = {
        "sha256": digest(sources.read_bytes()),
        "bytes": sources.stat().st_size,
    }
    manifest_path.write_text(json.dumps(manifest))
    verify_organized_release(parent)
    with pytest.raises(PreparationError, match="identity rows.*uniquely"):
        clean_dataset(plan)
    assert not plan.output.exists()
