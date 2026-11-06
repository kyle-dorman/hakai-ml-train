"""Scientific grid, polygon and installed preparation checks for shore distance."""

import csv
import json
import shutil
from dataclasses import replace
from pathlib import Path

import numpy as np
import pyogrio
import pytest
import rasterio
from pyproj import Transformer
from rasterio import Affine
from shapely import to_wkb
from shapely.geometry import GeometryCollection, LineString, Polygon, box
from shapely.ops import transform

from kelpseg.prepare.shore_distance import (
    geographic_halo,
    land_distance,
    metric_grid,
    polygon_parts,
    read_land,
)
from kelpseg.prepare.shoreline import (
    ShorelineSettings,
    load_settings,
    prepare_shoreline,
    read_sources,
)

CRS = "EPSG:32610"
AFFINE = Affine(3, 0, 500000, 0, -4, 4000000)


def geographic(geometry):
    """Convert a synthetic metre polygon to the global source CRS."""
    project = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True).transform
    return transform(project, geometry)


def write_vectors(path: Path, geometries: list) -> None:
    """Write small real GeoPackages without GeoPandas for offline tests."""
    pyogrio.raw.write(
        path,
        np.array([to_wkb(g) for g in geometries], dtype=object),
        [],
        [],
        layer=path.stem,
        driver="GPKG",
        geometry_type="Unknown",
        crs="EPSG:4326",
    )


def test_straight_coast_non_square_pixel_distances():
    """Raster distance is center-to-center in metres, with exact clipping."""
    land = geographic(box(499900, 3999900, 500006, 4000100))
    mask, distances = land_distance(land, 8, 5, AFFINE, CRS, cap_m=12)
    np.testing.assert_array_equal(mask, np.tile([1, 1, 0, 0, 0, 0, 0, 0], (5, 1)))
    np.testing.assert_allclose(distances, np.tile([0, 0, 3, 6, 9, 12, 12, 12], (5, 1)))
    assert mask.dtype == np.uint8
    assert distances.dtype == np.float32
    # Vector shoreline is 1.5 m from the first water center. Raster EDT gives
    # 3 m, documenting its half-pixel offset on this axis-aligned example.
    assert distances[0, 2] - 1.5 == 1.5


def test_outside_tiff_land_and_empty_ocean():
    """Shore outside an image still sets distance; no nearby land gives the cap."""
    outside = geographic(box(499900, 3999900, 499997, 4000100))
    mask, distances = land_distance(outside, 5, 5, AFFINE, CRS, cap_m=20)
    assert not mask.any()
    np.testing.assert_allclose(distances[2], [6, 9, 12, 15, 18])
    mask, distances = land_distance(Polygon(), 5, 5, AFFINE, CRS, cap_m=20)
    assert not mask.any()
    assert (distances == 20).all()


def test_holes_islands_and_all_land():
    """Interior holes remain water and disjoint islands contribute land."""
    mainland = box(499900, 3999900, 500100, 4000100)
    lake = box(500006, 3999984, 500018, 3999996)
    island = box(500009, 3999988, 500012, 3999992)
    land = geographic(mainland.difference(lake).union(island))
    mask, distance = land_distance(land, 8, 5, AFFINE, CRS, cap_m=20)
    assert mask[2, 3] == 1
    assert mask[2, 4] == 0 and distance[2, 4] == pytest.approx(3)
    assert mask[0, 0] == 1
    mask, distance = land_distance(geographic(mainland), 8, 5, AFFINE, CRS)
    assert mask.all() and not distance.any()


def test_polygon_collection_and_gpkg_union(tmp_path):
    """Polygon members survive mixed collections; source linework is recorded."""
    polygon = geographic(box(499990, 3999990, 500010, 4000010))
    collection = GeometryCollection([polygon, LineString([(-123, 36), (-123, 37)])])
    parts, discarded = polygon_parts(collection)
    assert len(parts) == 1 and discarded == 1
    paths = [
        tmp_path / f"{name}.gpkg"
        for name in ("mainlands", "big_islands", "small_islands")
    ]
    write_vectors(paths[0], [collection])
    write_vectors(paths[1], [geographic(box(500012, 3999988, 500015, 3999992))])
    write_vectors(paths[2], [box(-10, 10, -9, 11)])
    footprint = geographic_halo(8, 5, AFFINE, CRS, 20)
    land, records = read_land(paths, footprint)
    assert not land.is_empty
    assert records[0]["discarded_non_area_parts"] == 1
    assert records[2]["selected_features"] == 0


@pytest.mark.parametrize(
    "crs,affine",
    [
        ("EPSG:4326", AFFINE),
        ("EPSG:2227", AFFINE),
        (CRS, Affine(3, 1, 500000, 0, -3, 4000000)),
    ],
)
def test_unsupported_grids(crs, affine):
    """Degrees, feet and rotated grids fail instead of producing wrong metres."""
    with pytest.raises(ValueError, match="metre|north-up"):
        metric_grid(crs, affine)


def preparation_inputs(tmp_path: Path) -> ShorelineSettings:
    """Build a label-free source and three small global-layer fixtures."""
    image = tmp_path / "image.tif"
    with rasterio.open(
        image,
        "w",
        driver="GTiff",
        width=8,
        height=5,
        count=3,
        dtype="uint16",
        crs=CRS,
        transform=AFFINE,
        nodata=0,
    ) as ds:
        ds.write(np.ones((3, 5, 8), dtype=np.uint16) * 100)
    manifest = tmp_path / "images.csv"
    manifest.write_text(
        "source_key,image,band_names,region_id,original_source_id,row_offset,col_offset\n"
        "scene,image.tif,red;green;blue,001,original,2,3\n"
    )
    paths = []
    for name in ("mainlands", "big_islands", "small_islands"):
        path = tmp_path / f"{name}.gpkg"
        write_vectors(path, [geographic(box(499900, 3999900, 500006, 4000100))])
        paths.append(path)
    return ShorelineSettings(
        manifest,
        tmp_path,
        tmp_path / "output",
        *paths,
        max_distance_m=20,
        max_examples=1,
    )


def test_preparation_outputs_and_overwrite(tmp_path):
    """A real label-free preparation publishes exact grids, identity and previews."""
    settings = preparation_inputs(tmp_path)
    output = prepare_shoreline(settings)
    rows = list(csv.DictReader((output / "sources.csv").open()))
    assert rows[0]["source_key"] == "scene"
    assert rows[0]["image"] == "image.tif"
    assert rows[0]["original_source_id"] == "original"
    assert rows[0]["row_offset"] == "2"
    assert rows[0]["unknown_pixels"] == "0"
    assert rows[0]["coverage"] == "complete"
    for field in ("land_mask", "distance"):
        with rasterio.open(output / rows[0][field]) as ds:
            assert ds.transform == AFFINE and ds.crs == CRS
            assert ds.shape == (5, 8)
    assert (output / "examples/scene.png").exists()
    relocated = tmp_path / "relocated-images"
    relocated.mkdir()
    shutil.copyfile(tmp_path / "image.tif", relocated / "image.tif")
    relocated_sources = read_sources(replace(settings, image_root=relocated))
    assert relocated_sources[0]["image_path"] == relocated / "image.tif"
    assert relocated_sources[0]["metadata"]["image"] == "image.tif"
    assert json.loads((output / "summary.json").read_text())["status"] == "complete"
    with pytest.raises(ValueError, match="already exists"):
        prepare_shoreline(settings)


def test_settings_and_duplicate_source_errors(tmp_path):
    """Reject invalid cap, incomplete coverage claims, unknown keys and IDs."""
    settings = preparation_inputs(tmp_path)
    with settings.manifest.open("a") as stream:
        stream.write("scene,image.tif,red;green;blue,001,original,2,3\n")
    with pytest.raises(ValueError, match="duplicate source_key"):
        read_sources(settings)
    with pytest.raises(ValueError, match="max_distance_m"):
        ShorelineSettings(
            settings.manifest,
            tmp_path,
            tmp_path / "out",
            settings.mainlands,
            settings.big_islands,
            settings.small_islands,
            max_distance_m=float("nan"),
        )
    recipe = tmp_path / "recipe.toml"
    recipe.write_text("unexpected = true\n")
    with pytest.raises(ValueError, match="Unknown shoreline"):
        load_settings(recipe)


def test_preview_uses_declared_nodata_and_keeps_valid_zero(tmp_path, monkeypatch):
    """Nonzero nodata is gray, while valid zero reflectance remains display support."""
    from kelpseg.prepare import shore_preview

    settings = preparation_inputs(tmp_path)
    image = np.ones((3, 5, 8), dtype=np.uint16) * 100
    image[:, 0, 0] = 0
    image[0, 0, 1] = 9999
    with rasterio.open(tmp_path / "image.tif", "r+") as dataset:
        dataset.nodata = 9999
        dataset.write(image)
    captured = []
    stretch = shore_preview.log_stretch

    def capture_valid(values, valid):
        captured.append(valid.copy())
        return stretch(values, valid)

    monkeypatch.setattr(shore_preview, "log_stretch", capture_valid)
    prepare_shoreline(settings)
    assert captured[0][0, 0]
    assert not captured[0][0, 1]
    assert captured[0].sum() == 39
