from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from package_planet8b_dataset import (
    _write_inventory,
    package_dataset_archive,
    sha256_file,
    verify_dataset_archive,
)

CHIP_COLUMNS = [
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "source_width",
    "source_height",
    "source_crs",
    "chip_index",
    "row_off",
    "col_off",
    "chip_width",
    "chip_height",
    "minx",
    "miny",
    "maxx",
    "maxy",
    "total_pixel_count",
    "class_0_pixel_count",
    "class_1_pixel_count",
    "ignore_pixel_count",
    "nodata_pixel_count",
    "nodata_pct",
    "image_dtype",
    "label_dtype",
]
SELECTION_COLUMNS = [
    "chip_id",
    "source_tiff_id",
    "region_id",
    "class_0_pixel_count",
    "class_1_pixel_count",
    "ignore_pixel_count",
    "nodata_pixel_count",
    "class_presence",
    "selected_for_training",
    "selection_reason",
    "policy",
    "retain_fraction",
    "seed",
]
RASTER_COLUMNS = [
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
RASTER_METADATA_COLUMNS = [
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "width",
    "height",
    "band_count",
    "image_dtype",
    "label_dtype",
    "crs",
    "transform_a",
    "transform_b",
    "transform_c",
    "transform_d",
    "transform_e",
    "transform_f",
    "bounds_left",
    "bounds_bottom",
    "bounds_right",
    "bounds_top",
]
SPLIT_COLUMNS = [
    "image_name_stem",
    "split",
    "dataset",
    "region_id",
    "region_name",
    "acquisition_date",
    "acquisition_year",
]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        assert reader.fieldnames is not None
        return list(reader.fieldnames), list(reader)


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    chip_root = tmp_path / "chips"
    raster_root = tmp_path / "rasters"
    split_path = tmp_path / "planet8b_temporal_image_splits.csv"
    (chip_root / "all").mkdir(parents=True)
    (chip_root / "background_selection/exclude_all").mkdir(parents=True)
    (chip_root / "filter_history/nodata_50").mkdir(parents=True)
    raster_root.mkdir()

    labels = {
        "source_a_chip": np.array([[0, 1], [0, -100]], dtype=np.int64),
        "source_b_chip": np.zeros((2, 2), dtype=np.int64),
    }
    chip_rows: list[dict[str, str]] = []
    selection_rows: list[dict[str, str]] = []
    for index, (chip_id, label) in enumerate(labels.items()):
        image = np.ones((2, 2, 8), dtype=np.uint16)
        np.savez_compressed(
            chip_root / "all" / f"{chip_id}.npz", image=image, label=label
        )
        source_id = f"source_{'a' if index == 0 else 'b'}"
        class_0 = int(np.count_nonzero(label == 0))
        class_1 = int(np.count_nonzero(label == 1))
        ignore = int(np.count_nonzero(label == -100))
        chip_rows.append(
            {
                "chip_id": chip_id,
                "chip_path": f"all/{chip_id}.npz",
                "source_tiff_id": source_id,
                "dataset": "ca",
                "region_id": f"ca_00{index + 1}",
                "region_name": f"region_{index + 1}",
                "acquisition_date": f"2021-01-0{index + 1}",
                "source_width": "2",
                "source_height": "2",
                "source_crs": "EPSG:32611",
                "chip_index": "0",
                "row_off": "0",
                "col_off": "0",
                "chip_width": "2",
                "chip_height": "2",
                "minx": "0",
                "miny": "0",
                "maxx": "2",
                "maxy": "2",
                "total_pixel_count": "4",
                "class_0_pixel_count": str(class_0),
                "class_1_pixel_count": str(class_1),
                "ignore_pixel_count": str(ignore),
                "nodata_pixel_count": "0",
                "nodata_pct": "0",
                "image_dtype": "uint16",
                "label_dtype": "int64",
            }
        )
        positive = class_1 > 0
        selection_rows.append(
            {
                "chip_id": chip_id,
                "source_tiff_id": source_id,
                "region_id": f"ca_00{index + 1}",
                "class_0_pixel_count": str(class_0),
                "class_1_pixel_count": str(class_1),
                "ignore_pixel_count": str(ignore),
                "nodata_pixel_count": "0",
                "class_presence": "positive" if positive else "clean_background_only",
                "selected_for_training": "true" if positive else "false",
                "selection_reason": "positive" if positive else "exclude_all",
                "policy": "exclude_all",
                "retain_fraction": "",
                "seed": "",
            }
        )
    _write_csv(chip_root / "chip_manifest.csv", CHIP_COLUMNS, chip_rows)
    _write_csv(
        chip_root / "background_selection/exclude_all/training_selection.csv",
        SELECTION_COLUMNS,
        selection_rows,
    )
    _write_csv(
        chip_root / "background_selection/exclude_all/selection_summary.csv",
        ["scope", "class_presence", "chip_count", "selected_chip_count", "policy"],
        [
            {
                "scope": "global",
                "class_presence": "positive",
                "chip_count": "1",
                "selected_chip_count": "1",
                "policy": "exclude_all",
            },
            {
                "scope": "global",
                "class_presence": "clean_background_only",
                "chip_count": "1",
                "selected_chip_count": "0",
                "policy": "exclude_all",
            },
        ],
    )

    removal = dict(chip_rows[0])
    removal["chip_id"] = "removed_chip"
    removal["chip_path"] = "all/removed_chip.npz"
    removal["nodata_pixel_count"] = "4"
    removal["nodata_pct"] = "100"
    _write_csv(
        chip_root / "filter_history/nodata_50/removal_manifest.csv",
        CHIP_COLUMNS,
        [removal],
    )
    _write_csv(
        chip_root / "filter_history/nodata_50/post_filter_summary.csv",
        ["scope", "retained_chip_count", "removed_chip_count"],
        [{"scope": "global", "retained_chip_count": "2", "removed_chip_count": "1"}],
    )
    (chip_root / "filter_history/nodata_50/filter_metadata.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "threshold_pct": "50",
                "retained_count": 2,
                "removed_count": 1,
                "nodata_definition": "all eight retained image bands equal zero",
                "schema_version": "nodata-filter-v1",
            }
        )
    )
    (chip_root / "chip_qa_summary.json").write_text(
        json.dumps(
            {
                "parameters": {
                    "chip_size": 2,
                    "stride": 2,
                    "num_bands": 8,
                    "image_dtype": "uint16",
                    "label_dtype": "int64",
                    "ignore_index": -100,
                    "remap": [0, 1, 0, -100, 0],
                }
            }
        )
    )

    raster_rows: list[dict[str, str]] = []
    metadata_rows: list[dict[str, str]] = []
    split_rows: list[dict[str, str]] = []
    for index in range(2):
        source_id = f"source_{'a' if index == 0 else 'b'}"
        region_id = f"ca_00{index + 1}"
        date = f"2021-01-0{index + 1}"
        raster_rows.append(
            {
                "source_tiff_id": source_id,
                "dataset": "ca",
                "region_id": region_id,
                "region_name": f"region_{index + 1}",
                "acquisition_date": date,
                "source_split": "all",
                "source_image": str(tmp_path / "raw" / f"{source_id}.tif"),
                "source_label": str(tmp_path / "raw" / f"{source_id}_label.tif"),
                "merged_image": str(raster_root / "all/images" / f"{source_id}.tif"),
                "merged_label": str(raster_root / "all/labels" / f"{source_id}.tif"),
                "materialization_mode": "copy",
                "label_preparation": "derived_aligned",
            }
        )
        metadata_rows.append(
            {
                "source_tiff_id": source_id,
                "dataset": "ca",
                "region_id": region_id,
                "region_name": f"region_{index + 1}",
                "acquisition_date": date,
                "width": "2",
                "height": "2",
                "band_count": "8",
                "image_dtype": "uint16",
                "label_dtype": "uint8",
                "crs": "EPSG:32611",
                "transform_a": "1",
                "transform_b": "0",
                "transform_c": "0",
                "transform_d": "0",
                "transform_e": "-1",
                "transform_f": "2",
                "bounds_left": "0",
                "bounds_bottom": "0",
                "bounds_right": "2",
                "bounds_top": "2",
            }
        )
        split_rows.append(
            {
                "image_name_stem": source_id,
                "split": "TRAIN" if index == 0 else "VAL",
                "dataset": "ca",
                "region_id": region_id,
                "region_name": f"region_{index + 1}",
                "acquisition_date": date,
                "acquisition_year": "2021",
            }
        )
    _write_csv(raster_root / "raster_manifest.csv", RASTER_COLUMNS, raster_rows)
    _write_csv(
        raster_root / "raster_metadata.csv",
        RASTER_METADATA_COLUMNS,
        metadata_rows,
    )
    (raster_root / "raster_qa_summary.json").write_text(
        json.dumps({"total_pairs": 2, "counts_by_qa_status": {"pass": 2}})
    )
    _write_csv(split_path, SPLIT_COLUMNS, split_rows)
    return chip_root, raster_root, split_path


def _package_fixture(tmp_path: Path):
    chip_root, raster_root, split_path = _fixture(tmp_path)
    archive = tmp_path / "archives/planet8b_fixture_v1.zip"
    return package_dataset_archive(
        chip_root=chip_root,
        raster_root=raster_root,
        temporal_split=split_path,
        archive=archive,
        dataset_version="fixture_v1",
        producer_git_commit="a" * 40,
    )


def test_fixture_archive_is_portable_and_clean_extraction_verifies(
    tmp_path: Path,
) -> None:
    packaged = _package_fixture(tmp_path)

    verified = verify_dataset_archive(
        archive=packaged.archive,
        checksum_file=packaged.checksum_file,
        extraction_parent=tmp_path / "verify",
        sample_count=5,
    )

    assert verified.npz_count == verified.sampled_npz_count == 2
    assert verified.source_count == 2
    assert verified.npz_bytes == packaged.npz_bytes
    assert packaged.inventory_count == 18
    root = verified.dataset_root
    fields, rows = _read_csv(root / "manifests/chip_manifest.csv")
    assert "chip_path" in fields
    assert {row["chip_path"] for row in rows} == {
        "chips/all/source_a_chip.npz",
        "chips/all/source_b_chip.npz",
    }
    raster_fields, _ = _read_csv(root / "manifests/raster_manifest.csv")
    assert "source_image" not in raster_fields
    provenance = (root / "metadata/local_raster_path_provenance.csv").read_text()
    assert str(tmp_path) in provenance
    assert not list(root.rglob("*.tif"))
    inventory_hashes = {
        row["relative_path"]: row["sha256"]
        for row in _read_csv(root / "metadata/archive_inventory.csv")[1]
    }
    assert inventory_hashes["chips/all/source_a_chip.npz"] == sha256_file(
        root / "chips/all/source_a_chip.npz"
    )


def test_verification_rejects_changed_checksum_and_changed_member(
    tmp_path: Path,
) -> None:
    packaged = _package_fixture(tmp_path)
    wrong_checksum = tmp_path / "wrong.sha256"
    wrong_checksum.write_text(f"{'0' * 64}  {packaged.archive.name}\n")
    with pytest.raises(RuntimeError, match="Archive checksum mismatch"):
        verify_dataset_archive(
            archive=packaged.archive,
            checksum_file=wrong_checksum,
            extraction_parent=tmp_path / "wrong-checksum-extract",
        )

    tampered_dir = tmp_path / "tampered"
    tampered_dir.mkdir()
    tampered_archive = tampered_dir / packaged.archive.name
    with (
        zipfile.ZipFile(packaged.archive) as source,
        zipfile.ZipFile(
            tampered_archive, "w", compression=zipfile.ZIP_STORED
        ) as target,
    ):
        for info in source.infolist():
            data = source.read(info)
            if info.filename.endswith("metadata/README.md"):
                data += b"\nchanged\n"
            target.writestr(info, data)
    tampered_checksum = tampered_archive.with_suffix(".zip.sha256")
    tampered_checksum.write_text(
        f"{hashlib.sha256(tampered_archive.read_bytes()).hexdigest()}  "
        f"{tampered_archive.name}\n"
    )

    with pytest.raises(RuntimeError, match="Inventory (byte-size|SHA-256) mismatch"):
        verify_dataset_archive(
            archive=tampered_archive,
            checksum_file=tampered_checksum,
            extraction_parent=tmp_path / "tampered-extract",
        )


def test_packager_refuses_symlinked_chip_and_existing_output(tmp_path: Path) -> None:
    chip_root, raster_root, split_path = _fixture(tmp_path)
    chip_path = chip_root / "all/source_a_chip.npz"
    real_path = chip_root / "all/source_a_chip.real.npz"
    chip_path.rename(real_path)
    chip_path.symlink_to(real_path.name)
    archive = tmp_path / "archives/planet8b_fixture_v1.zip"

    with pytest.raises(RuntimeError, match="not a regular file"):
        package_dataset_archive(
            chip_root=chip_root,
            raster_root=raster_root,
            temporal_split=split_path,
            archive=archive,
            dataset_version="fixture_v1",
            producer_git_commit="a" * 40,
        )

    chip_path.unlink()
    real_path.rename(chip_path)
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b"existing")
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        package_dataset_archive(
            chip_root=chip_root,
            raster_root=raster_root,
            temporal_split=split_path,
            archive=archive,
            dataset_version="fixture_v1",
            producer_git_commit="a" * 40,
        )


def test_v2_packaging_reuses_prior_chip_hashes_and_hashes_metadata_freshly(
    tmp_path: Path,
) -> None:
    chip_root, raster_root, split_path = _fixture(tmp_path)
    v1 = package_dataset_archive(
        chip_root=chip_root,
        raster_root=raster_root,
        temporal_split=split_path,
        archive=tmp_path / "archives/planet8b_fixture_v1.zip",
        dataset_version="fixture_v1",
        producer_git_commit="a" * 40,
    )
    v2 = package_dataset_archive(
        chip_root=chip_root,
        raster_root=raster_root,
        temporal_split=split_path,
        archive=tmp_path / "archives/planet8b_fixture_v2.zip",
        dataset_version="fixture_v2",
        producer_git_commit="b" * 40,
        prior_archive=v1.archive,
        prior_checksum_file=v1.checksum_file,
    )
    assert v2.reused_hash_count == 2
    assert v2.rejected_reuse_count == 0
    assert v2.freshly_hashed_count > 2
    with zipfile.ZipFile(v2.archive) as archive_file:
        inventory_name = next(
            name
            for name in archive_file.namelist()
            if name.endswith("metadata/archive_inventory.csv")
        )
        rows = list(
            csv.DictReader(archive_file.read(inventory_name).decode().splitlines())
        )
    chip_rows = [row for row in rows if row["kind"] == "chip"]
    metadata_rows = [row for row in rows if row["kind"] == "metadata"]
    assert {row["hash_source"] for row in chip_rows} == {"prior_inventory_reuse"}
    assert {row["hash_source"] for row in metadata_rows} == {"fresh_sha256"}


def test_inventory_forces_rewritten_same_size_chip_to_be_hashed_freshly(
    tmp_path: Path,
) -> None:
    staging = tmp_path / "dataset"
    chip = staging / "chips/all/example.npz"
    chip.parent.mkdir(parents=True)
    chip.write_bytes(b"new!")
    prior = {
        "chips/all/example.npz": {
            "relative_path": "chips/all/example.npz",
            "byte_size": "4",
            "sha256": hashlib.sha256(b"old!").hexdigest(),
            "kind": "chip",
        }
    }
    _, _, reused, fresh, rejected = _write_inventory(
        staging,
        prior_inventory=prior,
        force_fresh_paths={"chips/all/example.npz"},
    )
    assert (reused, fresh, rejected) == (0, 1, 1)
    rows = list(csv.DictReader((staging / "metadata/archive_inventory.csv").open()))
    assert rows[0]["hash_source"] == "fresh_sha256"
    assert rows[0]["sha256"] == hashlib.sha256(b"new!").hexdigest()
