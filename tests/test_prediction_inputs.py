"""Prediction recipe/header validation and complete geometric window coverage."""

import csv
from dataclasses import replace

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine, from_origin

from kelpseg.prediction.settings import PredictionSettings, load_settings, read_sources
from kelpseg.prediction.windows import axis_starts, prediction_windows

NAMES = ("red", "green", "blue")


def make_source(tmp_path, **profile_changes):
    """Write a small cleaned RGB fixture and its image-only declaration."""
    image = tmp_path / "image.tif"
    profile = dict(
        driver="GTiff",
        width=13,
        height=11,
        count=3,
        dtype="uint16",
        nodata=0,
        crs="EPSG:32610",
        transform=from_origin(300000, 4000000, 3, 3),
    )
    profile.update(profile_changes)
    with rasterio.open(image, "w", **profile) as output:
        output.write(np.ones((profile["count"], 11, 13), dtype=profile["dtype"]))
    manifest = tmp_path / "images.csv"
    write_rows(
        manifest,
        [dict(source_key="one", image="image.tif", band_names=";".join(NAMES))],
    )
    return PredictionSettings(
        tmp_path / "model", manifest, tmp_path, tmp_path / "output"
    )


def write_rows(path, rows):
    """Write the supplied declaration rows with their explicit field names."""
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_recipe_paths_and_defaults(tmp_path):
    recipe = tmp_path / "predict.toml"
    recipe.write_text(
        'model="model"\nmanifest="images.csv"\nimage_root="images"\noutput="output"\n'
    )
    settings = load_settings(recipe)
    assert settings.model == tmp_path / "model"
    assert settings.image_root == tmp_path / "images"
    assert settings.manifest == tmp_path / "images.csv"
    assert settings.output == tmp_path / "output"
    assert (
        settings.stride,
        settings.min_valid_fraction,
        settings.batch_size,
        settings.device,
    ) == (256, 0.2, 1, "cpu")


@pytest.mark.parametrize(
    "extra, match",
    [
        ("strdie=256", "Unknown"),
        ("stride=513", "stride"),
        ("stride=true", "stride"),
        ("batch_size=0", "batch_size"),
        ("min_valid_fraction=nan", "min_valid_fraction"),
        ("min_valid_fraction=1.1", "min_valid_fraction"),
        ('device="magic"', "device"),
    ],
)
def test_invalid_recipe_settings(tmp_path, extra, match):
    recipe = tmp_path / "predict.toml"
    recipe.write_text(
        'model="model"\nmanifest="images.csv"\nimage_root="images"\noutput="output"\n'
        + extra
    )
    with pytest.raises(ValueError, match=match):
        load_settings(recipe)


def test_sources_preserve_identity_and_require_model_bands(tmp_path):
    settings = make_source(tmp_path)
    write_rows(
        settings.manifest,
        [
            dict(
                source_key="scene_01",
                image="image.tif",
                band_names="red;green;blue",
                region_id="001",
                acquisition_date="2026-01-01",
                row_offset="12",
            )
        ],
    )
    (source,) = read_sources(settings, NAMES)
    assert source.source_key == "scene_01"
    assert source.image == tmp_path / "image.tif"
    assert source.band_names == NAMES
    assert source.identity["region_id"] == "001"
    assert source.identity["row_offset"] == "12"
    assert source.identity["dataset_id"] == ""
    with pytest.raises(ValueError, match="Unknown band"):
        read_sources(settings, ("nir", "red", "green"))


@pytest.mark.parametrize(
    "profile,match",
    [
        ({"dtype": "float32"}, "uint16"),
        ({"nodata": 65535}, "nodata=0"),
        ({"nodata": None}, "nodata=0"),
        ({"crs": None}, "CRS/transform"),
        ({"transform": Affine.identity()}, "CRS/transform"),
        ({"count": 4}, "every native"),
    ],
)
def test_header_rejection(tmp_path, profile, match):
    settings = make_source(tmp_path, **profile)
    with pytest.raises(ValueError, match=match):
        read_sources(settings, NAMES)


@pytest.mark.parametrize(
    "change,match",
    [
        ({"source_key": "../escape"}, "Invalid source_key"),
        ({"band_names": "red;red;blue"}, "Duplicate selected band"),
        ({"band_names": "red;green;guess"}, "Unknown band"),
        ({"image": ""}, "nonempty TIFF"),
        ({"row_offset": "-1"}, "nonnegative integer"),
    ],
)
def test_manifest_mistakes(tmp_path, change, match):
    settings = make_source(tmp_path)
    row = dict(source_key="one", image="image.tif", band_names=";".join(NAMES))
    row.update(change)
    write_rows(settings.manifest, [row])
    with pytest.raises(ValueError, match=match):
        read_sources(settings, NAMES)


def test_duplicate_keys_and_resolved_paths(tmp_path):
    settings = make_source(tmp_path)
    row = dict(source_key="one", image="image.tif", band_names=";".join(NAMES))
    write_rows(settings.manifest, [row, row])
    with pytest.raises(ValueError, match="Duplicate source_key"):
        read_sources(settings, NAMES)
    write_rows(
        settings.manifest, [row, dict(row, source_key="two", image="./image.tif")]
    )
    with pytest.raises(ValueError, match="Duplicate image path"):
        read_sources(settings, NAMES)
    with pytest.raises(OSError):
        read_sources(replace(settings, manifest=tmp_path / "missing.csv"), NAMES)


@pytest.mark.parametrize(
    "width,height", [(512, 512), (1000, 701), (13, 17), (13, 701), (1024, 1024)]
)
def test_shifted_windows_cover_source_without_duplicate_starts(width, height):
    windows = list(prediction_windows(width, height, 512, 256))
    assert len({(w.row_off, w.col_off) for w in windows}) == len(windows)
    coverage = np.zeros((height, width), dtype=bool)
    for window in windows:
        row, col = int(window.row_off), int(window.col_off)
        h, w = int(window.height), int(window.width)
        coverage[row : row + h, col : col + w] = True
        assert h == min(height, 512) and w == min(width, 512)
    assert coverage.all()
    assert windows[-1].row_off == max(height - 512, 0)
    assert windows[-1].col_off == max(width - 512, 0)


def test_axis_starts_shift_only_final_window():
    assert axis_starts(1000, 512, 256) == [0, 256, 488]
    assert axis_starts(1024, 512, 256) == [0, 256, 512]
    assert axis_starts(17, 512, 256) == [0]
    with pytest.raises(ValueError, match="stride"):
        axis_starts(1024, 512, 513)


def test_programmatic_settings_validate_the_same_contract(tmp_path):
    settings = make_source(tmp_path)
    with pytest.raises(ValueError, match="batch_size"):
        replace(settings, batch_size=0)
    with pytest.raises(ValueError, match="min_valid_fraction"):
        replace(settings, min_valid_fraction=-0.1)


def test_case_insensitive_output_keys_are_rejected_without_changing_spelling(tmp_path):
    settings = make_source(tmp_path)
    first = dict(source_key="Scene", image="image.tif", band_names=";".join(NAMES))
    write_rows(settings.manifest, [first])
    assert read_sources(settings, NAMES)[0].source_key == "Scene"
    # A different source path must not hide an output-filename collision.
    write_rows(
        settings.manifest, [first, dict(first, source_key="scene", image="other.tif")]
    )
    with pytest.raises(ValueError, match="Duplicate source_key.*scene.*Scene"):
        read_sources(settings, NAMES)


@pytest.mark.parametrize(
    "change, detail",
    [
        ({"band_names": "red;green;unknown"}, "Unknown band"),
        ({"acquisition_date": "2026-02-30"}, "acquisition_date.*YYYY-MM-DD"),
    ],
)
def test_manifest_band_and_date_errors_identify_source_and_line(
    tmp_path, change, detail
):
    settings = make_source(tmp_path)
    row = dict(source_key="scene_bad", image="image.tif", band_names=";".join(NAMES))
    row.update(change)
    write_rows(settings.manifest, [row])
    with pytest.raises(ValueError, match=f"line 2, source 'scene_bad': .*{detail}"):
        read_sources(settings, NAMES)
