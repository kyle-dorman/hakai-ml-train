"""Training-only pipeline galleries expose geometry, real draws and native assets."""

import json
import re
from pathlib import Path

import numpy as np
import pytest
from matplotlib import image as mpl_image
from typer.testing import CliRunner

from kelpseg.augmentation_debug.display import write_viewer
from kelpseg.augmentation_debug.pipeline import preview_pipeline
from kelpseg.cli import app
from kelpseg.prepare.check import PreparationError
from kelpseg.preprocessing import BAND_NAMES, MEAN, STD


@pytest.fixture
def pipeline_inputs(tmp_path, monkeypatch):
    chips = tmp_path / "chips"
    chips.mkdir()
    (chips / "recipe.json").write_text(
        json.dumps(dict(source_band_names=BAND_NAMES, chip_size=16))
    )
    image = np.arange(13 * 14 * 8, dtype=np.uint16).reshape(13, 14, 8) + 100
    image[0, 0] = 0
    rows = []
    for index, (split, foreground, region) in enumerate(
        [
            ("train", True, "001"),
            ("train", False, "012"),
            ("train", False, "002"),
            ("val", True, "003"),
            ("test", True, "004"),
        ]
    ):
        payload = chips / f"{split}_{index}.npz"
        if split == "train":
            label = np.zeros((13, 14), dtype=np.int8)
            label[0, 0] = -100
            if foreground:
                label[4:9, 3:8] = 1
            np.savez_compressed(payload, image=image, label=label)
        rows.append(
            dict(
                source_key=f"source_{index}",
                source_id=f"original_{index}",
                row="0",
                col="0",
                region=region,
                acquisition_date="2022-01-01",
                split=split,
                payload=str(payload),
                kelp_pixels="25" if foreground else "0",
                background_pixels="156" if foreground else "181",
                nodata_pixels="1",
                height="13",
                width="14",
            )
        )

    def selected(chip_root, assignments, experiment, variant):
        assert chip_root == chips
        assert experiment == "baseline" and variant == "augmented"
        return rows

    monkeypatch.setattr("kelpseg.augmentation_debug.inputs.select_windows", selected)
    return chips, rows


def test_gallery_reads_training_only_and_keeps_four_paired_views_per_draw(
    pipeline_inputs, tmp_path, monkeypatch
):
    chips, rows = pipeline_inputs
    before = {path: path.read_bytes() for path in chips.glob("*.npz")}
    real_load, opened = np.load, []

    def training_load(path, *args, **kwargs):
        assert Path(path).name.startswith("train_")
        opened.append(str(path))
        return real_load(path, *args, **kwargs)

    monkeypatch.setattr(np, "load", training_load)
    output = tmp_path / "pipeline gallery"
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "preview-pipeline",
            "--chips",
            str(chips),
            "--assignments",
            "assignments.csv",
            "--output",
            str(output),
            "--seed",
            "33",
            "--positive-samples",
            "1",
            "--draws",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert str(output / "index.html") in result.output
    assert len(opened) == 3
    assert set(opened) == {row["payload"] for row in rows if row["split"] == "train"}
    assert all(path.read_bytes() == data for path, data in before.items())
    metadata = json.loads((output / "gallery.json").read_text())
    assert metadata["draws_per_example"] == 2
    assert metadata["normalization"]["clip_value"] == 5000
    assert metadata["normalization"]["mean"] == list(MEAN)
    assert metadata["normalization"]["std"] == list(STD)
    assert metadata["display"]["raw_ceiling"] == 2000
    assert metadata["augmentation_domain"]["native_scale"] == 65535
    assert len(metadata["samples"]) == 3
    native_recipe = json.loads((output / "pipeline.json").read_text())
    assert native_recipe == metadata["pipeline_recipe"]
    stages = native_recipe["transform"]["transforms"]
    assert [stage["__class_fullname__"] for stage in stages] == [
        "D4",
        "Affine",
        "SomeOf",
    ]
    assert stages[1]["p"] == 0.5
    assert stages[2]["n"] == 2 and stages[2]["replace"] is False
    seeds = []
    for summary in metadata["samples"]:
        assert summary["window"]["split"] == "train"
        record = json.loads((output / summary["parameters"]).read_text())
        assert record["padding"] == [0, 3, 0, 2]
        assert record["native_valid_pixels"] == 181
        assert len(record["draws"]) == 2
        for draw in record["draws"]:
            seeds.append(draw["seed"])
            source, reference, geometry, full = draw["states"]
            assert "source" in source["title"].lower()
            assert "d4" in reference["title"].lower()
            assert "two" in full["title"].lower()
            assert source["parameters"]["class"] == "NoOp"
            assert reference["parameters"]["operation_trace"][0]["class"] == "D4"
            assert "affine" in geometry["title"].lower()
            assert full["parameters"]["class"] == "Compose"
            trace = full["parameters"]["operation_trace"]
            assert len(trace) == 4 and trace[0]["class"] == "D4"
            assert trace[1]["class"] == "Affine"
            assert isinstance(trace[1]["applied"], bool)
            assert (
                reference["parameters"]["operation_trace"][0]["parameters"][
                    "group_element"
                ]
                == trace[0]["parameters"]["group_element"]
            )
            assert (
                reference["metrics"]["valid_pixels"]
                == source["metrics"]["valid_pixels"]
            )
            assert (
                reference["metrics"]["foreground_pixels"]
                == source["metrics"]["foreground_pixels"]
            )
            assert geometry["closeup"] == full["closeup"]
            assert geometry["parameters"]["operation_trace"] == trace[:2]
            for state in draw["states"]:
                assert set(state["assets"]) == {
                    "rgb",
                    "false_color",
                    "labels",
                    "false_color_labels",
                }
                assert state["parameters"]["seed"] == draw["seed"]
                for relative in state["assets"].values():
                    path = output / relative
                    assert path.is_file()
                    assert mpl_image.imread(path).shape[:2] == (16, 16)
                assert len(state["closeup"]) == 4
    assert seeds == list(range(33, 39))
    assert not output.with_name(".pipeline gallery.incomplete").exists()
    assert (output / "selected_windows.csv").is_file()
    html = (output / "index.html").read_text()
    assert "__GALLERY_DATA__" not in html and "background_control_01" in html


def test_existing_output_is_refused_before_payload_reads(tmp_path, monkeypatch):
    output = tmp_path / "existing"
    output.mkdir()

    def no_load(*args, **kwargs):
        pytest.fail("Existing output must be refused before loading any payload")

    monkeypatch.setattr(
        "kelpseg.augmentation_debug.pipeline.load_preview_samples", no_load
    )
    with pytest.raises(PreparationError, match="fresh directory"):
        preview_pipeline(tmp_path / "missing", "missing.csv", "augmented", output)


@pytest.mark.parametrize("draws", [0, True, 33])
def test_invalid_draw_counts_fail_before_inputs_are_opened(
    tmp_path, monkeypatch, draws
):
    def no_load(*args, **kwargs):
        pytest.fail("Invalid draw setting must be refused before inputs are opened")

    monkeypatch.setattr(
        "kelpseg.augmentation_debug.pipeline.load_preview_samples", no_load
    )
    with pytest.raises(ValueError, match="draws must be an integer in 1..32"):
        preview_pipeline(
            tmp_path / "missing",
            "missing.csv",
            "augmented",
            tmp_path / "gallery",
            draws=draws,
        )


def test_missing_training_labels_report_the_payload(pipeline_inputs, tmp_path):
    chips, rows = pipeline_inputs
    path = Path(
        next(
            row["payload"]
            for row in rows
            if int(row["kelp_pixels"]) > 0 and row["split"] == "train"
        )
    )
    with np.load(path) as original:
        image = original["image"].copy()
    np.savez_compressed(path, image=image)
    with pytest.raises(PreparationError, match="mapped training labels") as error:
        preview_pipeline(
            chips,
            "assignments.csv",
            "augmented",
            tmp_path / "gallery",
            positive_samples=1,
            draws=2,
        )
    assert str(path) in str(error.value)


def test_pipeline_viewer_embeds_safe_json_and_needs_no_remote_code(tmp_path):
    source = '</script><img src="bad" onerror="alert(1)">'
    records = [
        dict(preview_name="training_01", window=dict(source_key=source), draws=[])
    ]
    write_viewer(
        tmp_path, {"scope": "train only"}, records, template_name="pipeline_viewer.html"
    )
    document = (tmp_path / "index.html").read_text()
    embedded = re.search(
        r'<script type="application/json" id="gallery-data">(.*?)</script>',
        document,
        re.DOTALL,
    )
    assert embedded is not None
    data = json.loads(embedded.group(1))
    assert data["samples"][0]["window"]["source_key"] == source
    assert source not in document and "<" not in embedded.group(1)
    assert "__GALLERY_DATA__" not in document
    assert not re.search(r"<script[^>]+src=|fetch\s*\(|https?://", document)
