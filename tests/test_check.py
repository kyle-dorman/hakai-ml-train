"""Independent evidence-level and directory checks for installed preparation."""

from dataclasses import replace

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from typer.testing import CliRunner

from kelpseg.cli.check import check_command
from kelpseg.prepare.check import (
    CheckRecipe,
    PreparationError,
    check_inputs,
    discover_inputs,
    load_check_recipe,
)


@pytest.fixture
def example(tmp_path):
    images, labels = tmp_path / "imagery", tmp_path / "annotations"
    images.mkdir()
    labels.mkdir()
    image = np.ones((3, 5, 7), dtype="uint16") * 17
    image[:, 0, 0] = 0
    categories = np.zeros((5, 7), dtype="uint8")
    categories[0, 0] = 3
    write(images / "new-coast.tif", image, nodata=0)
    write(labels / "new-coast.tiff", categories, nodata=3)
    recipe = CheckRecipe(image_band_counts=(3,), label_values=(0, 1, 3), block_size=2)
    return images, labels, recipe


def write(path, data, *, nodata, crs="EPSG:32610", transform=None):
    if data.ndim == 2:
        data = data[np.newaxis]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[2],
        height=data.shape[1],
        count=data.shape[0],
        dtype=data.dtype,
        nodata=nodata,
        crs=crs,
        transform=transform or from_origin(100, 200, 3, 3),
    ) as target:
        target.write(data)


def test_quick_never_reads_pixels_and_reports_evidence(example, monkeypatch):
    import kelpseg.prepare.check as checker

    images, labels, recipe = example
    original_open = rasterio.open

    class HeadersOnly:
        def __init__(self, *args, **kwargs):
            self.dataset = original_open(*args, **kwargs)

        def __getattr__(self, name):
            if name in {"read", "read_masks", "dataset_mask"}:
                pytest.fail("Quick checks cannot read pixels or masks")
            return getattr(self.dataset, name)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.dataset.close()

    monkeypatch.setattr(rasterio, "open", HeadersOnly)

    def fail_scan(*args, **kwargs):
        pytest.fail("Quick checks cannot scan pixels")

    monkeypatch.setattr(checker, "_scan", fail_scan)
    result = check_inputs(images, labels, recipe)
    assert result.passed
    assert result.level == "quick"
    assert result.scanned_image_pixels == result.scanned_label_pixels == 0
    assert "pixel decodability" in result.skipped_checks
    assert any("physical band" in unknown for unknown in result.unknowns)
    assert "checksum" in " ".join(result.unknowns)


def test_full_covers_every_pixel_in_bounded_windows(example, monkeypatch):
    import kelpseg.prepare.check as checker

    images, labels, recipe = example
    original_windows = checker.windows
    selected = []

    def track_windows(width, height, size):
        for window in original_windows(width, height, size):
            assert window.width <= 2 and window.height <= 2
            selected.extend(
                (row, column)
                for row in range(
                    int(window.row_off), int(window.row_off + window.height)
                )
                for column in range(
                    int(window.col_off), int(window.col_off + window.width)
                )
            )
            yield window

    monkeypatch.setattr(checker, "windows", track_windows)
    result = check_inputs(images, labels, recipe, full=True)
    assert result.passed
    assert result.scanned_image_pixels == result.scanned_label_pixels == 35
    assert len(selected) == len(set(selected)) == 35
    assert result.sources[0]["pixel_counts"]["image_nodata"] == 1
    assert not any("SHA" in value for value in result.passed_checks)


def test_full_scans_large_native_label_even_when_grid_differs(example):
    images, labels, recipe = example
    write(labels / "new-coast.tiff", np.zeros((8, 9), dtype="uint8"), nodata=3)
    result = check_inputs(images, labels, recipe, full=True)
    assert not result.passed
    assert result.scanned_image_pixels == 35
    assert result.scanned_label_pixels == 72
    assert any(item.code == "pair_grid" and item.repairable for item in result.issues)
    assert any("different grids" in check for check in result.skipped_checks)


def test_empty_missing_and_casefolded_pairs_rejected(tmp_path, example):
    images, labels, _ = example
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(PreparationError, match="No image TIFFs"):
        discover_inputs(empty)
    (labels / "new-coast.tiff").rename(labels / "NEW-COAST.tiff")
    with pytest.raises(PreparationError, match="stems must match"):
        discover_inputs(images, labels)
    (images / "NEW-COAST.TIFF").write_bytes(b"collision")
    with pytest.raises(PreparationError, match="case-folded"):
        discover_inputs(images)


def test_nested_relative_stem_pairing_and_symlinks(tmp_path):
    images, labels = tmp_path / "i", tmp_path / "l"
    (images / "nested").mkdir(parents=True)
    (labels / "nested").mkdir(parents=True)
    write(images / "nested/a.TIF", np.ones((3, 2, 3), dtype="uint16"), nodata=0)
    write(labels / "nested/a.tiff", np.zeros((2, 3), dtype="uint8"), nodata=3)
    pair = discover_inputs(images, labels)[0]
    assert pair.key == "nested/a"
    assert pair.image_relative == "nested/a.TIF"
    assert pair.label_relative == "nested/a.tiff"
    (images / "unsafe").symlink_to(labels, target_is_directory=True)
    with pytest.raises(PreparationError, match="symlinks"):
        discover_inputs(images, labels)


def test_overlapping_inputs_and_symlink_root_rejected(tmp_path, example):
    images, _, _ = example
    with pytest.raises(PreparationError, match="overlap"):
        discover_inputs(images, images)
    alias = tmp_path / "alias"
    alias.symlink_to(images, target_is_directory=True)
    with pytest.raises(PreparationError, match="symlink"):
        discover_inputs(alias)


def test_report_is_explicit_atomic_fresh_and_outside_inputs(example, tmp_path):
    import json

    images, labels, recipe = example
    original_files = sorted(path for path in tmp_path.rglob("*"))
    check_inputs(images, labels, recipe)
    assert sorted(tmp_path.rglob("*")) == original_files
    report = tmp_path / "evidence.json"
    check_inputs(images, labels, recipe, full=True, report=report)
    data = json.loads(report.read_text())
    assert data["level"] == "full" and data["passed"]
    assert data["scanned_image_pixels"] == 35
    with pytest.raises(PreparationError, match="already exists"):
        check_inputs(images, labels, recipe, report=report)
    with pytest.raises(PreparationError, match="outside input"):
        check_inputs(images, labels, recipe, report=images / "bad.json")
    assert not (images / "bad.json").exists()


def test_bad_bands_dtype_crs_and_misleading_label_metadata(example):
    images, labels, recipe = example
    write(
        images / "new-coast.tif", np.ones((2, 5, 7), dtype="uint8"), nodata=0, crs=None
    )
    write(labels / "new-coast.tiff", np.zeros((5, 7), dtype="uint8"), nodata=0)
    result = check_inputs(images, labels, recipe)
    codes = {issue.code: issue for issue in result.issues}
    assert {
        "image_bands",
        "image_dtype",
        "missing_crs",
        "pair_grid",
        "label_nodata_declaration",
    } <= codes.keys()
    assert codes["label_nodata_declaration"].repairable
    assert not codes["image_bands"].repairable


def test_quick_cannot_claim_vocabulary_full_finds_unexpected_class(example):
    images, labels, recipe = example
    with rasterio.open(labels / "new-coast.tiff", "r+") as label:
        label.write(np.full((1, 5, 7), 9, dtype="uint8"))
    assert check_inputs(images, labels, recipe).passed
    result = check_inputs(images, labels, recipe, full=True)
    assert not result.passed
    assert {"label_values", "paired_nodata"} <= {issue.code for issue in result.issues}


def test_cleaned_checker_independently_finds_broken_nodata_pair(example):
    images, labels, recipe = example
    with rasterio.open(labels / "new-coast.tiff", "r+") as label:
        label.write(np.zeros((1, 5, 7), dtype="uint8"))
    result = check_inputs(images, labels, replace(recipe, profile="cleaned"), full=True)
    assert not result.passed
    assert any(
        issue.code == "paired_nodata" and not issue.repairable
        for issue in result.issues
    )
    with rasterio.open(images / "new-coast.tif", "r+") as image:
        image.nodata = 65535
    result = check_inputs(images, labels, replace(recipe, profile="cleaned"), full=True)
    assert any(issue.code == "cleaned_image_nodata" for issue in result.issues)


def test_source_missing_nodata_requires_explicit_fallback(example):
    images, _, recipe = example
    with rasterio.open(images / "new-coast.tif", "r+") as image:
        image.nodata = None
    assert not check_inputs(images, None, recipe).passed
    result = check_inputs(
        images, None, replace(recipe, missing_image_nodata=0), full=True
    )
    assert result.passed
    assert result.sources[0]["pixel_counts"]["image_nodata"] == 1
    assert result.scanned_label_pixels == 0


def test_unreadable_tiff_is_issue_without_traceback(example, tmp_path):
    import typer

    images, _, recipe = example
    (images / "new-coast.tif").write_bytes(b"not a TIFF")
    result = check_inputs(images, None, recipe, full=True)
    assert not result.passed
    assert result.issues[0].code == "image_read"
    recipe_file = tmp_path / "check.toml"
    recipe_file.write_text(
        'schema_version=1\nprofile="source"\nimage_band_counts=[3]\nimage_dtypes=["uint16"]\nlabel_values=[0,1,3]\n'
    )
    app = typer.Typer()
    app.command()(check_command)
    response = CliRunner().invoke(
        app, ["--images", str(images), "--recipe", str(recipe_file), "--full"]
    )
    assert response.exit_code == 1
    assert "Cannot read" in response.output
    assert "Traceback" not in response.output


@pytest.mark.parametrize(
    "extra",
    [
        "unexpected=1",
        'profile=["source"]',
        "block_size=0",
        'image_dtypes=["str"]',
        "image_band_counts=[true]",
        "label_values=[0,256]",
    ],
)
def test_recipe_rejects_unknown_or_invalid_settings(tmp_path, extra):
    recipe = tmp_path / "recipe.toml"
    values = dict(
        schema_version="1",
        profile='"source"',
        image_band_counts="[3]",
        image_dtypes='["uint16"]',
        label_values="[0,1,3]",
    )
    name, value = extra.split("=", 1)
    values[name] = value
    recipe.write_text("\n".join(f"{key}={value}" for key, value in values.items()))
    with pytest.raises(PreparationError):
        load_check_recipe(recipe)


def test_header_band_names_are_evidence_not_channel_count(example):
    images, _, recipe = example
    with rasterio.open(images / "new-coast.tif", "r+") as image:
        image.descriptions = ("red", "green", "blue")
    result = check_inputs(
        images, None, replace(recipe, band_names=("blue", "green", "red"))
    )
    assert any(issue.code == "band_names" for issue in result.issues)


def test_cleaned_profile_requires_uint8_labels(example):
    images, labels, recipe = example
    write(labels / "new-coast.tiff", np.zeros((5, 7), dtype="uint16"), nodata=3)
    result = check_inputs(images, labels, replace(recipe, profile="cleaned"))
    assert "cleaned_label_dtype" in {issue.code for issue in result.issues}


def test_symlink_ancestor_is_rejected(example, tmp_path):
    images, labels, recipe = example
    linked = tmp_path / "linked-root"
    linked.symlink_to(images.parent, target_is_directory=True)
    with pytest.raises(PreparationError, match="symlink"):
        check_inputs(linked / images.name, None, recipe)


def test_check_progress_explains_requested_work_and_completed_files(
    example, tmp_path, caplog
):
    images, labels, recipe = example
    caplog.set_level("INFO", logger="kelpseg.prepare")
    check_inputs(images, labels, recipe)
    assert "headers only; pixels and hashes not checked" in caplog.text
    assert "Image header:" in caplog.text
    assert "Label header:" in caplog.text
    assert (
        "Finished new-coast: 0 image pixels and 0 label pixels scanned" in caplog.text
    )
    assert "Scanning image pixels" not in caplog.text

    caplog.clear()
    report = tmp_path / "full-report.json"
    check_inputs(images, labels, recipe, full=True, report=report)
    assert "Scanning image pixels:" in caplog.text
    assert (
        "Finished new-coast: 35 image pixels and 35 label pixels scanned" in caplog.text
    )
    assert "Saved check report:" in caplog.text


def test_unreadable_label_stops_before_pixel_scan(example):
    images, labels, recipe = example
    (labels / "new-coast.tiff").write_bytes(b"corrupt label TIFF")
    result = check_inputs(images, labels, recipe, full=True)
    assert not result.passed
    assert result.scanned_image_pixels == 0
    assert result.scanned_label_pixels == 0
    assert any(issue.code == "label_read" for issue in result.issues)
    assert "pixel_counts" not in result.sources[0]
    assert any("no scan retry" in item for item in result.skipped_checks)


def test_failed_pixel_read_is_not_retried(example, monkeypatch):
    import rasterio

    from kelpseg.prepare import check

    images, labels, recipe = example
    calls = []

    def broken_scan(*args):
        calls.append(True)
        raise rasterio.errors.RasterioIOError("fixture decode failure")

    monkeypatch.setattr(check, "_scan", broken_scan)
    result = check_inputs(images, labels, recipe, full=True)
    assert not result.passed and len(calls) == 1
    assert any(issue.code == "pixel_read" for issue in result.issues)
    assert (
        "all selected native image and label pixels decoded" not in result.passed_checks
    )


def test_unsupported_headers_skip_pixels_and_later_sources(example, monkeypatch):
    import shutil

    from kelpseg.prepare import check

    images, labels, recipe = example
    shutil.copyfile(images / "new-coast.tif", images / "later.tif")
    shutil.copyfile(labels / "new-coast.tiff", labels / "later.tiff")
    monkeypatch.setattr(
        check, "_scan", lambda *args: pytest.fail("unsupported headers scanned")
    )
    bad_recipe = replace(recipe, image_band_counts=(8,))
    result = check_inputs(images, labels, bad_recipe, full=True)
    assert not result.passed and result.source_count == 2
    assert len(result.sources) == 1
    assert result.scanned_image_pixels == result.scanned_label_pixels == 0
    assert "remaining sources skipped after failure" in result.skipped_checks


@pytest.mark.parametrize("first_name", ["red", "blue"])
def test_partial_band_descriptions_cannot_contradict_declared_order(
    example, first_name
):
    images, labels, recipe = example
    with rasterio.open(images / "new-coast.tif", "r+") as image:
        image.set_band_description(1, first_name)
    recipe = replace(recipe, band_names=("red", "green", "blue"))
    result = check_inputs(images, labels, recipe)
    assert any(issue.code == "band_names" for issue in result.issues) == (
        first_name != "red"
    )
    assert any("physical band" in unknown for unknown in result.unknowns)
