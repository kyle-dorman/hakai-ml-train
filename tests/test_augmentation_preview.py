"""Stock-library trials, aligned source footprints and training-only galleries."""

import json
import subprocess
import sys

import albumentations as A
import numpy as np
import pytest
from matplotlib import image as mpl_image
from typer.testing import CliRunner

from kelpseg.augmentation_debug.panels import closeup_window, render_panel
from kelpseg.augmentation_debug.preview import preview_augmentations
from kelpseg.augmentation_debug.trials import individual_trials, value_metrics
from kelpseg.cli import app
from kelpseg.prepare.check import PreparationError
from kelpseg.preprocessing import BAND_NAMES, CLIP_VALUE, native_validity


def _sample():
    image = np.arange(8 * 8 * 8, dtype=np.uint16).reshape(8, 8, 8) + 10
    image[6:] = 0
    image[:, 7:] = 0
    image[0, 0] = 0
    image[1, 1, 0] = 6500
    label = np.zeros((8, 8), dtype=np.int8)
    label[2, 3] = 1
    valid = native_validity(image, 6, 7)
    label[~valid] = -100
    return dict(
        image=image,
        label=label,
        valid=valid,
        band_names=BAND_NAMES,
        closeup=(1, 2, 5, 6),
        preview_name="training_01",
        background_control=False,
        row=dict(
            region="001",
            acquisition_date="2022-01-01",
            source_key="train",
            row="0",
            col="0",
        ),
    )


def test_stock_trials_are_isolated_and_identity_matches_original():
    sample = _sample()
    before = {name: sample[name].copy() for name in ("image", "label", "valid")}
    families = dict(individual_trials(sample, seed=33))
    assert set(families) == {
        "square_symmetry",
        "brightness",
        "gain",
        "blur",
        "noise",
        "sharpness",
        "spatial_dropout",
        "spatial_dropout_count",
        "channel_shifts",
        "band_dropout_red",
        "band_dropout_nir",
    }
    for family, states in families.items():
        original = states[0]
        assert original["parameters"]["class"] == "NoOp"
        identities = [state for state in states[1:] if state["is_identity"]]
        assert len(identities) == 1
        identity = identities[0]
        for field in ("image", "label", "valid", "display"):
            np.testing.assert_array_equal(identity[field], original[field])
        assert identity["metrics"] == original["metrics"]
        for state in states:
            assert set(state["parameters"]) == {
                "class",
                "kwargs",
                "applied",
                "seed",
                "fixed_parameters",
            }
            assert state["parameters"]["seed"] == 33
        if family not in (
            "square_symmetry",
            "spatial_dropout",
            "spatial_dropout_count",
        ):
            for state in states:
                np.testing.assert_array_equal(state["label"], sample["label"])
                np.testing.assert_array_equal(state["valid"], sample["valid"])
        if family.startswith("band_dropout_"):
            band = family.removeprefix("band_dropout_")
            channel = BAND_NAMES.index(band)
            other = [i for i in range(len(BAND_NAMES)) if i != channel]
            assert len(states) == 3
            for state in states:
                np.testing.assert_array_equal(
                    state["image"][:, :, other], original["image"][:, :, other]
                )
            assert states[-1]["parameters"]["class"] == "ChannelDropout"
            assert not states[-1]["image"][:, :, channel].any()
    for field in before:
        np.testing.assert_array_equal(sample[field], before[field])


def test_d4_moves_padding_labels_and_closeup_with_stock_mask_operation():
    sample = _sample()
    states = dict(individual_trials(sample))["square_symmetry"]
    y0, x0, y1, x1 = sample["closeup"]
    original_crop = sample["label"][y0:y1, x0:x1]
    for state in states[1:]:
        element = state["parameters"]["applied"]["group_element"]
        transform = A.D4(p=1)
        np.testing.assert_array_equal(
            state["label"],
            transform.apply_to_mask(sample["label"], group_element=element),
        )
        np.testing.assert_array_equal(
            state["valid"],
            transform.apply_to_mask(
                sample["valid"].astype(np.int8), group_element=element
            ).astype(bool),
        )
        a, b, c, d = state["closeup"]
        expected = transform.apply_to_mask(original_crop, group_element=element)
        np.testing.assert_array_equal(state["label"][a:c, b:d], expected)
        assert np.all(state["image"][~state["valid"]] == 0)
        assert np.all(state["label"][~state["valid"]] == -100)


def test_wider_native_endpoints_keep_reference_values_and_change_the_preview():
    families = dict(individual_trials(_sample()))
    brightness = {
        state["parameters"]["kwargs"]["brightness_limit"][0]: state
        for state in families["brightness"][1:]
    }
    assert {-0.005, -0.0025, 0, 0.0025, 0.005}.issubset(brightness)
    assert (min(brightness), max(brightness)) == (-0.2, 0.2)
    blur = {
        state["parameters"]["kwargs"]["sigma_limit"][0]: state
        for state in families["blur"][1:]
        if state["parameters"]["class"] == "GaussianBlur"
    }
    assert {0.4, 0.8, 1.2, 3}.issubset(blur)
    assert max(blur) == 3
    noise = {
        state["parameters"]["kwargs"]["std_range"][0]: state
        for state in families["noise"][1:]
    }
    assert {0, 0.00015, 0.0004, 0.0008, 0.44}.issubset(noise)
    assert max(noise) == 0.44
    shifts = {
        state["parameters"]["kwargs"]["noise_params"]["ranges"][0][1]: state
        for state in families["channel_shifts"][1:]
    }
    assert {0, 0.0004, 0.001, 0.002, 0.1}.issubset(shifts)
    assert max(shifts) == 0.1
    for trials, old_max, new_max in (
        (brightness, 0.005, 0.2),
        (blur, 1.2, 3),
        (noise, 0.0008, 0.44),
        (shifts, 0.002, 0.1),
    ):
        assert not np.array_equal(
            trials[old_max]["display"], trials[new_max]["display"]
        )
        assert trials[new_max]["parameters"]["fixed_parameters"] is None


def test_coarse_size_and_count_sweeps_match_stock_holes_and_mask_targets():
    sample = _sample()
    families = dict(individual_trials(sample))
    sizes = families["spatial_dropout"][2:]
    counts = families["spatial_dropout_count"][2:]
    assert [s["parameters"]["kwargs"]["hole_height_range"][0] for s in sizes] == [
        0.05,
        0.1,
        0.2,
        0.25,
        0.35,
        0.5,
    ]
    assert [s["parameters"]["kwargs"]["num_holes_range"][0] for s in counts] == [
        1,
        2,
        4,
        8,
        16,
    ]
    for states, is_count_sweep in ((sizes, False), (counts, True)):
        for state in states:
            parameters = state["parameters"]
            assert parameters["class"] == "CoarseDropout"
            kwargs = parameters["kwargs"]
            if is_count_sweep:
                assert kwargs["hole_height_range"] == [0.25, 0.25]
            else:
                assert kwargs["num_holes_range"] == [4, 4]
            assert kwargs["hole_height_range"] == kwargs["hole_width_range"]
            # Let the actual stock class establish both hole coordinates and
            # ignored targets. Even tiny zero-area native holes keep their
            # library behavior rather than being repaired by the preview.
            reference = A.CoarseDropout(**kwargs)
            reference.add_targets({"validity": "mask"})
            reference.set_random_seed(parameters["seed"])
            actual = reference(
                image=sample["image"].astype(np.float32) / 65535,
                mask=sample["label"].copy(),
                validity=sample["valid"].astype(np.int8),
            )
            holes = reference.get_applied_params()["holes"]
            assert len(holes) == kwargs["num_holes_range"][0]
            np.testing.assert_array_equal(parameters["applied"]["holes"], holes)
            np.testing.assert_array_equal(state["label"], actual["mask"])
            np.testing.assert_array_equal(state["valid"], actual["validity"] == 1)
            assert state["label"].dtype == np.int8
            assert set(np.unique(state["label"])) <= {-100, 0, 1}
            assert np.all(state["label"][sample["valid"] & ~state["valid"]] == -100)
            assert np.all(state["image"][~state["valid"]] == 0)


def test_metrics_report_raw_negatives_and_final_upper_cap():
    sample = _sample()
    image = sample["image"].astype(float)
    image[1, 2, 0] = -150
    metrics = value_metrics(image, sample["label"], sample["valid"], BAND_NAMES)
    assert metrics["above_cap_values"] == 1
    assert metrics["below_zero_values"] == 1
    assert metrics["bands"]["coastal_blue"]["raw_range"] == [-150, 6500]
    assert metrics["bands"]["coastal_blue"]["capped_range"] == [-150, CLIP_VALUE]
    assert metrics["valid_pixels"] == 41
    assert metrics["foreground_pixels"] == 1


@pytest.fixture
def gallery_inputs(tmp_path, monkeypatch):
    chips = tmp_path / "chips"
    chips.mkdir()
    (chips / "recipe.json").write_text(
        json.dumps(dict(source_band_names=BAND_NAMES, chip_size=8))
    )
    sample = _sample()
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
        path = chips / f"{split}_{index}.npz"
        if split == "train":
            label = sample["label"][:6, :7].copy()
            if foreground:
                label[3, 2:6] = 1
            else:
                label[label == 1] = 0
            np.savez_compressed(path, image=sample["image"][:6, :7], label=label)
        rows.append(
            dict(
                source_key=f"source_{index}",
                source_id=f"original_{index}",
                row="0",
                col="0",
                region=region,
                acquisition_date="2022-01-01",
                split=split,
                payload=str(path),
                kelp_pixels="5" if foreground else "0",
                background_pixels="40",
                nodata_pixels="1",
                height="6",
                width="7",
            )
        )

    def selected(chip_root, assignments, experiment, variant):
        assert chip_root == chips
        assert experiment == "baseline" and variant == "augmented"
        return rows

    monkeypatch.setattr("kelpseg.augmentation_debug.inputs.select_windows", selected)
    return chips, rows


def test_bounded_gallery_reads_training_only_and_writes_native_assets(
    gallery_inputs, tmp_path, monkeypatch
):
    chips, rows = gallery_inputs
    output = tmp_path / "gallery"
    source_bytes = {path: path.read_bytes() for path in chips.glob("*.npz")}
    real_load = np.load
    opened = []

    def load_training_only(path, *args, **kwargs):
        assert "train_" in str(path)
        opened.append(str(path))
        return real_load(path, *args, **kwargs)

    monkeypatch.setattr(np, "load", load_training_only)
    actual_panels = []

    def bounded_render(path, sample, family, states, limits):
        if sample["preview_name"] == "training_01" and family == "brightness":
            render_panel(path, sample, family, states, limits)
            actual_panels.append(path)
        else:
            mpl_image.imsave(path, np.zeros((2, 2, 3)))

    monkeypatch.setattr(
        "kelpseg.augmentation_debug.preview.render_panel", bounded_render
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "preview-augmentations",
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
        ],
    )
    assert result.exit_code == 0, result.output
    assert str(output / "index.html") in result.output
    assert "Loading training preview" in result.output
    assert len(opened) == 3
    assert set(opened) == {row["payload"] for row in rows if row["split"] == "train"}
    assert all(path.read_bytes() == content for path, content in source_bytes.items())
    metadata = json.loads((output / "gallery.json").read_text())
    assert len(metadata["samples"]) == 3
    assert metadata["normalization"]["clip_value"] == 5000
    assert all(row["window"]["split"] == "train" for row in metadata["samples"])
    records = [
        json.loads((output / row["parameters"]).read_text())
        for row in metadata["samples"]
    ]
    assert records[0]["padding"] == [0, 2, 0, 1]
    assert records[0]["native_valid_pixels"] == 41
    families = {entry["family"]: entry for entry in records[0]["families"]}
    assert len(families) == 11
    base = families["brightness"]["states"][0]["metrics"]
    assert (
        families["spatial_dropout"]["states"][-1]["metrics"]["valid_pixels"]
        < base["valid_pixels"]
    )
    assert (
        families["band_dropout_red"]["states"][-1]["metrics"]["valid_pixels"]
        == base["valid_pixels"]
    )
    assert (
        families["band_dropout_red"]["states"][-1]["metrics"]["foreground_pixels"] == 5
    )
    assert actual_panels
    png = mpl_image.imread(output / "training_01/brightness.png")
    assert png.shape[0] > 500 and png.shape[1] > 1000
    viewer = (output / "index.html").read_text()
    assert "__GALLERY_DATA__" not in viewer
    assert "background_control_01" in viewer
    for record in records:
        for family in record["families"]:
            for state in family["states"]:
                assert state["closeup"]
                for asset in state["assets"].values():
                    assert (output / asset).is_file()
    full = mpl_image.imread(
        output / records[0]["families"][0]["states"][0]["assets"]["rgb"]
    )
    assert full.shape[:2] == (8, 8)
    assert not output.with_name(".gallery.incomplete").exists()


def test_existing_output_refused_before_payload_reads(
    gallery_inputs, tmp_path, monkeypatch
):
    chips, _ = gallery_inputs
    output = tmp_path / "existing"
    output.mkdir()

    def no_payload(*args, **kwargs):
        pytest.fail("Overwrite refusal must precede payload reads")

    monkeypatch.setattr("kelpseg.augmentation_debug.preview.load_chip", no_payload)
    with pytest.raises(PreparationError, match="fresh directory"):
        preview_augmentations(
            chips, "assignments.csv", "augmented", output, positive_samples=1
        )


def test_missing_chip_input_reports_ordinary_file_error(tmp_path):
    with pytest.raises(OSError, match="recipe.json"):
        preview_augmentations(
            tmp_path / "missing",
            tmp_path / "missing.csv",
            "augmented",
            tmp_path / "gallery",
        )


def test_cli_and_preview_help_remain_lightweight(tmp_path):
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "preview-augmentations" in result.output
    code = """
import importlib.abc
import sys
from typer.testing import CliRunner
class BlockWorkflowImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'numpy','matplotlib','albumentations','torch','lightning','wandb'}:
            raise AssertionError('Unexpected workflow import: ' + fullname)
sys.meta_path.insert(0, BlockWorkflowImports())
from kelpseg.cli import app
result = CliRunner().invoke(app, ['--help'])
assert result.exit_code == 0, result.output
assert 'preview-augmentations' in result.output
for command in ('preview-augmentations', 'preview-pipeline'):
    result = CliRunner().invoke(app, [command, '--help'])
    assert result.exit_code == 0, result.output
    assert '--chips' in result.output and '--positive-samples' in result.output
"""
    process = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr


def test_preview_imports_do_not_load_application_models(tmp_path):
    code = """
import importlib.abc
import sys
class BlockModelWorkflows(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'lightning','wandb','transformers','segmentation_models_pytorch'} or fullname.startswith('kelpseg.models'):
            raise AssertionError('Unexpected model workflow import: ' + fullname)
sys.meta_path.insert(0, BlockModelWorkflows())
from kelpseg.augmentation_debug.preview import preview_augmentations
assert callable(preview_augmentations)
"""
    process = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stderr


def test_closeup_finds_foreground_on_bottom_right_edge():
    label = np.zeros((512, 512), dtype=np.int8)
    label[500, 500] = 1
    y0, x0, y1, x1 = closeup_window(label)
    assert (label[y0:y1, x0:x1] == 1).any()


def test_closeup_prefers_visible_kelp_boundary_over_tiny_fringe():
    label = np.zeros((512, 512), dtype=np.int8)
    label[:, 128:384] = 1
    label[0, 0] = 1
    y0, x0, y1, x1 = closeup_window(label)
    assert 0.3 < np.mean(label[y0:y1, x0:x1] == 1) < 0.8


@pytest.mark.parametrize("command", ["preview-augmentations", "preview-pipeline"])
def test_preview_cli_errors_and_logging_restoration(tmp_path, command):
    import logging

    logger = logging.getLogger("kelpseg")
    before = logger.level, logger.propagate, list(logger.handlers)
    args = [
        command,
        "--chips",
        str(tmp_path / "missing"),
        "--assignments",
        str(tmp_path / "assignments.csv"),
        "--output",
        str(tmp_path / "gallery"),
    ]
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1
    assert "Error:" in result.output and "recipe.json" in result.output
    assert (logger.level, logger.propagate, logger.handlers) == before
    assert not (tmp_path / "gallery").exists()
    (tmp_path / "gallery").mkdir()
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 1 and "exists" in result.output.lower()
    for option, value in [
        ("--seed", "-1"),
        ("--positive-samples", "0"),
        ("--positive-samples", "17"),
    ]:
        result = CliRunner().invoke(app, [*args, option, value])
        assert result.exit_code == 2
    if command == "preview-pipeline":
        result = CliRunner().invoke(app, [*args, "--draws", "33"])
        assert result.exit_code == 2
