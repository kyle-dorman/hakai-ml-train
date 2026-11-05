"""Image-only TIFF reconstruction, overlap and coverage correctness."""

import csv
import importlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from kelpseg.prediction.settings import PredictionSettings

prediction = importlib.import_module("kelpseg.prediction.predict")
BANDS = ("red", "green", "blue")
GRID = from_origin(423000, 3762000, 3, 3)


class FakeModel:
    """Return known tile probabilities while recording actual batch sizes."""

    metadata = {"input_size": 512, "threshold": 0.5, "band_names": list(BANDS)}

    def __init__(self, mode: str = "coordinates") -> None:
        self.mode = mode
        self.batches: list[list[tuple[int, ...]]] = []

    def predict_batch(self, images, source_band_names):
        """Preserve native nodata and make overlap expectations independent."""
        assert tuple(source_band_names) == BANDS
        self.batches.append([image.shape for image in images])
        probabilities = []
        for image in images:
            if self.mode == "coordinates":
                result = image[:, :, 0].astype(np.float32) / 1000
            else:
                value = 0.9 if image[0, 0, 0] == 1 else 0.05
                result = np.full(image.shape[:2], value, dtype=np.float32)
            result[~np.any(image != 0, axis=-1)] = np.nan
            probabilities.append(result)
        return probabilities


def setup_source(tmp_path: Path, image: np.ndarray, **changes) -> PredictionSettings:
    """Write one cleaned TIFF and an explicit portable image-only manifest."""
    root = tmp_path / "images"
    root.mkdir()
    with rasterio.open(
        root / "scene.tif",
        "w",
        driver="GTiff",
        height=image.shape[0],
        width=image.shape[1],
        count=image.shape[2],
        dtype="uint16",
        crs="EPSG:32610",
        transform=GRID,
        nodata=0,
    ) as dataset:
        dataset.write(image.transpose(2, 0, 1))
    manifest = tmp_path / "images.csv"
    with manifest.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "source_key",
                "image",
                "band_names",
                "region_id",
                "acquisition_date",
                "original_source_id",
                "row_offset",
                "col_offset",
            ],
        )
        writer.writeheader()
        writer.writerow(
            dict(
                source_key="scene",
                image="scene.tif",
                band_names=";".join(BANDS),
                region_id="001",
                acquisition_date="2020-06-01",
                original_source_id="original-acquisition",
                row_offset=100,
                col_offset=200,
            )
        )
    return PredictionSettings(
        model=tmp_path / "copied-model",
        manifest=manifest,
        image_root=root,
        output=tmp_path / "prediction",
        **changes,
    )


def read_rows(path: Path) -> list[dict]:
    """Read ordinary published records for output assertions."""
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def use_model(monkeypatch, model: FakeModel) -> None:
    """Avoid model downloads and heavyweight forwards in geometric fixtures."""
    monkeypatch.setattr(prediction, "load_model_bundle", lambda *a, **kw: model)


def test_coordinates_georeferencing_and_short_final_batch(tmp_path, monkeypatch):
    image = np.ones((513, 769, 3), dtype=np.uint16)
    image[:, :, 0] = np.arange(1, 770, dtype=np.uint16)
    image[10, 20] = 0
    settings = setup_source(tmp_path, image, batch_size=4)
    model = FakeModel()
    use_model(monkeypatch, model)
    output = prediction.predict(settings)
    assert output == settings.output
    assert [len(batch) for batch in model.batches] == [4, 2]
    assert all(shape == (512, 512, 3) for batch in model.batches for shape in batch)
    with rasterio.open(output / "probabilities/scene.tif") as dataset:
        assert dataset.crs == rasterio.crs.CRS.from_epsg(32610)
        assert dataset.transform == GRID
        assert dataset.shape == image.shape[:2]
        assert dataset.dtypes == ("float32",)
        assert np.isnan(dataset.nodata)
        probability = dataset.read(1)
    expected = image[:, :, 0].astype(np.float32) / 1000
    expected[10, 20] = np.nan
    np.testing.assert_allclose(probability, expected, atol=1e-7)
    with rasterio.open(output / "masks/scene.tif") as dataset:
        mask = dataset.read(1)
        assert dataset.transform == GRID
        assert dataset.crs == rasterio.crs.CRS.from_epsg(32610)
        assert dataset.nodata == 255
        assert dataset.dtypes == ("uint8",)
    expected_mask = (expected >= 0.5).astype(np.uint8)
    expected_mask[10, 20] = 255
    np.testing.assert_array_equal(mask, expected_mask)
    assert len(read_rows(output / "windows.csv")) == 6
    record = read_rows(output / "sources.csv")[0]
    assert record["source_key"] == "scene"
    assert record["region_id"] == "001"
    assert record["acquisition_date"] == "2020-06-01"
    assert record["original_source_id"] == "original-acquisition"
    assert record["row_offset"] == "100"
    assert record["col_offset"] == "200"
    assert int(record["uncovered_valid_pixels"]) == 0
    assert int(record["nodata_pixels"]) == 1
    assert int(record["predicted_valid_pixels"]) == 513 * 769 - 1
    for name in ("settings.json", "summary.json"):
        assert isinstance(json.loads((output / name).read_text()), dict)


def test_average_probabilities_before_thresholding(tmp_path, monkeypatch):
    image = np.ones((9, 768, 3), dtype=np.uint16)
    image[:, :, 0] = np.arange(1, 769, dtype=np.uint16)
    settings = setup_source(tmp_path, image, batch_size=2)
    model = FakeModel("tile_constants")
    use_model(monkeypatch, model)
    output = prediction.predict(settings)
    assert model.batches == [[(9, 512, 3), (9, 512, 3)]]
    with rasterio.open(output / "probabilities/scene.tif") as dataset:
        values = dataset.read(1)
    np.testing.assert_allclose(values[:, :256], 0.9)
    np.testing.assert_allclose(values[:, 256:512], 0.475)
    np.testing.assert_allclose(values[:, 512:], 0.05)
    with rasterio.open(output / "masks/scene.tif") as dataset:
        mask = dataset.read(1)
    assert np.all(mask[:, :256] == 1)
    assert np.all(mask[:, 256:] == 0)


def test_skipped_windows_distinguish_uncovered_valid_from_nodata(tmp_path, monkeypatch):
    image = np.zeros((10, 1024, 3), dtype=np.uint16)
    image[:, 0] = 100
    image[:, 512:] = 100
    settings = setup_source(tmp_path, image, stride=512)
    model = FakeModel()
    use_model(monkeypatch, model)
    output = prediction.predict(settings)
    assert model.batches == [[(10, 512, 3)]]
    record = read_rows(output / "sources.csv")[0]
    expected = dict(
        total_pixels=10240,
        valid_pixels=5130,
        nodata_pixels=5110,
        predicted_valid_pixels=5120,
        uncovered_valid_pixels=10,
    )
    assert {key: int(record[key]) for key in expected} == expected
    with rasterio.open(output / "probabilities/scene.tif") as dataset:
        values = dataset.read(1)
    assert np.isnan(values[:, :512]).all()
    np.testing.assert_allclose(values[:, 512:], 0.1)
    with rasterio.open(output / "masks/scene.tif") as dataset:
        assert np.all(dataset.read(1)[:, :512] == 255)


def test_retained_overlap_recovers_valid_pixels_in_skipped_neighbor(
    tmp_path, monkeypatch
):
    image = np.zeros((10, 768, 3), dtype=np.uint16)
    image[:, 300] = 500
    image[:, 665:] = 500
    settings = setup_source(tmp_path, image)
    model = FakeModel()
    use_model(monkeypatch, model)
    output = prediction.predict(settings)
    # The first window has just ten valid pixels and is skipped. The second
    # passes 20% validity and recovers those same pixels in the overlap.
    assert model.batches == [[(10, 512, 3)]]
    windows = read_rows(output / "windows.csv")
    assert [row["disposition"] for row in windows] == ["skipped_nodata", "retained"]
    record = read_rows(output / "sources.csv")[0]
    expected = dict(
        total_pixels=7680,
        valid_pixels=1040,
        nodata_pixels=6640,
        predicted_valid_pixels=1040,
        uncovered_valid_pixels=0,
    )
    assert {key: int(record[key]) for key in expected} == expected
    with rasterio.open(output / "probabilities/scene.tif") as dataset:
        values = dataset.read(1)
    assert np.isfinite(values).sum() == 1040
    np.testing.assert_array_equal(values[:, 300], 0.5)
    assert np.isnan(values[:, :256]).all()


@pytest.mark.parametrize("min_valid_fraction", [0.0, 0.2])
@pytest.mark.parametrize("valid_pixels", [0, 19, 20])
def test_small_source_threshold_excludes_artificial_padding(
    tmp_path, monkeypatch, valid_pixels, min_valid_fraction
):
    image = np.zeros((10, 10, 3), dtype=np.uint16)
    image.reshape(-1, 3)[:valid_pixels] = 500
    settings = setup_source(tmp_path, image, min_valid_fraction=min_valid_fraction)
    model = FakeModel()
    use_model(monkeypatch, model)
    output = prediction.predict(settings)
    retained = valid_pixels > 0 and valid_pixels / 100 >= min_valid_fraction
    assert model.batches == ([[(10, 10, 3)]] if retained else [])
    record = read_rows(output / "sources.csv")[0]
    assert int(record["total_pixels"]) == 100
    assert int(record["valid_pixels"]) == valid_pixels
    assert int(record["predicted_valid_pixels"]) == (valid_pixels if retained else 0)
    assert int(record["uncovered_valid_pixels"]) == (0 if retained else valid_pixels)
    with rasterio.open(output / "probabilities/scene.tif") as dataset:
        values = dataset.read(1)
    assert values.shape == (10, 10)
    assert np.isfinite(values).sum() == (valid_pixels if retained else 0)


def test_existing_output_is_refused_before_prediction(tmp_path, monkeypatch):
    settings = setup_source(tmp_path, np.ones((2, 2, 3), dtype=np.uint16))
    settings.output.mkdir()
    marker = settings.output / "keep.txt"
    marker.write_text("existing result")
    model = FakeModel()
    use_model(monkeypatch, model)
    with pytest.raises((ValueError, FileExistsError), match="exist|fresh|overwrite"):
        prediction.predict(settings)
    assert marker.read_text() == "existing result"
    assert model.batches == []
