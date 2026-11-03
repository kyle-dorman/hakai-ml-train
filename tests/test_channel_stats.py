"""Direct NumPy statistics and the training-only, image-only read boundary."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from kelpseg.cli import app
from kelpseg.prepare.channel_stats import compute_channel_stats
from kelpseg.prepare.check import PreparationError
from kelpseg.preprocessing import BAND_NAMES


def _images(channels):
    first = np.zeros((2, 2, channels), dtype=np.uint16)
    first[0, 1] = np.arange(channels) * 100  # Zero in one band is valid.
    first[1, 0] = np.arange(4999, 4999 + channels)
    first[1, 1] = np.arange(1, channels + 1) * 42
    first[1, 1, 0] = 65535
    second = np.zeros((1, 3, channels), dtype=np.uint16)
    second[0, 1] = np.arange(1, channels + 1) * 10
    second[0, 2] = np.arange(1, channels + 1) * 200
    background = np.array(
        [
            np.arange(1, channels + 1) * 300,
            np.arange(1, channels + 1) * 600,
        ],
        dtype=np.uint16,
    )[None, :, :]
    return [first, second, background]


@pytest.fixture
def collection(tmp_path, monkeypatch):
    def create(images, names, kelp_counts=None):
        chips = tmp_path / "chips"
        chips.mkdir()
        (chips / "recipe.json").write_text(
            json.dumps(dict(source_band_names=names, chip_size=512))
        )
        assignments = tmp_path / "assignments.csv"
        assignments.write_text(
            "fixture: selection is supplied by the existing selector\n"
        )
        if kelp_counts is None:
            kelp_counts = [1] * len(images)
        rows = []
        for index, (image, kelp) in enumerate(zip(images, kelp_counts, strict=True)):
            height, width, _ = image.shape
            valid = np.any(image != 0, axis=-1)
            label = np.zeros((height, width), dtype=np.int8)
            label[~valid] = -100
            if kelp and valid.any():
                label[tuple(np.argwhere(valid)[0])] = 1
            if valid.sum() > 1:
                # A valid image pixel with an ignored label must still contribute.
                label[tuple(np.argwhere(valid)[-1])] = -100
            payload = chips / f"train_{index}.npz"
            np.savez_compressed(payload, image=image, label=label)
            rows.append(
                dict(
                    dataset_id="fixture",
                    release_id="v1",
                    source_id=f"source_{index}",
                    source_key=f"source_{index}",
                    region="001",
                    acquisition_date="2022-01-01",
                    row="0",
                    col=str(index),
                    original_row="0",
                    original_col=str(index),
                    height=str(height),
                    width=str(width),
                    kelp_pixels=str(kelp),
                    split="train",
                    payload=str(payload),
                )
            )
        for split in ("val", "test", "unused"):
            rows.append(
                dict(
                    rows[0],
                    split=split,
                    kelp_pixels="999999",
                    payload=str(chips / f"{split}_forbidden.npz"),
                )
            )
        calls = []

        def selected(
            root, source_assignments, *, experiment="baseline", variant="augmented"
        ):
            assert Path(root) == chips
            assert Path(source_assignments) == assignments
            calls.append((experiment, variant))
            return rows

        monkeypatch.setattr("kelpseg.prepare.channel_stats.select_windows", selected)
        return chips, assignments, rows, calls

    return create


def _direct_pixels(images, cap):
    pixels = np.concatenate(
        [image[np.any(image != 0, axis=-1)] for image in images]
    ).astype(np.float64)
    return np.minimum(pixels, cap) if cap is not None else pixels


@pytest.mark.parametrize("channels", [3, 8])
@pytest.mark.parametrize("cap", [None, 5000])
def test_true_size_stats_match_numpy_and_read_only_selected_image_members(
    collection, tmp_path, monkeypatch, channels, cap
):
    names = list(BAND_NAMES) if channels == 8 else ["red", "green", "blue"]
    images = _images(channels)
    chips, assignments, rows, calls = collection(images, names, [1, 1, 0])
    before = {path: path.read_bytes() for path in chips.glob("*.npz")}
    expected = _direct_pixels(images[:2], cap)
    original_load, original_member = np.load, np.lib.npyio.NpzFile.__getitem__
    opened, members = [], []

    def load_selected(path, *args, **kwargs):
        assert str(path) in {rows[0]["payload"], rows[1]["payload"]}
        opened.append(str(path))
        return original_load(path, *args, **kwargs)

    def image_only(archive, key):
        assert key == "image", f"Statistics must not read {key!r} from an NPZ"
        members.append(key)
        return original_member(archive, key)

    monkeypatch.setattr(np, "load", load_selected)
    monkeypatch.setattr(np.lib.npyio.NpzFile, "__getitem__", image_only)
    output = tmp_path / "stats.json"
    result = compute_channel_stats(
        chips, assignments, output, kelp_only=True, clip_value=cap
    )
    np.testing.assert_allclose(
        result["mean"], expected.mean(axis=0), rtol=1e-13, atol=1e-10
    )
    np.testing.assert_allclose(
        result["std_sample"], expected.std(axis=0, ddof=1), rtol=1e-13, atol=1e-10
    )
    assert result["band_names"] == names
    assert result["clip_value"] == cap
    assert result["pixels"] == 5  # Actual edge dimensions; no 512px loading padding.
    assert result["available_training_windows"] == 3
    assert result["selected_training_windows"] == 2
    assert result["excluded_zero_kelp_windows"] == 1
    assert result["selected_training_sources"] == 2
    assert result["payload_bytes_read"] == sum(
        Path(row["payload"]).stat().st_size for row in rows[:2]
    )
    assert opened == [row["payload"] for row in rows[:2]] and members == [
        "image",
        "image",
    ]
    assert calls == [("baseline", "augmented")]
    assert json.loads(output.read_text()) == result
    assert all(path.read_bytes() == content for path, content in before.items())
    assert not list(tmp_path.glob(".*.tmp"))


def test_default_scope_includes_background_training_chips_and_forwards_split_scope(
    collection, tmp_path
):
    images = _images(3)
    chips, assignments, _, calls = collection(
        images, ["red", "green", "blue"], [1, 1, 0]
    )
    expected = _direct_pixels(images, None)
    report = compute_channel_stats(
        chips,
        assignments,
        tmp_path / "all_training.json",
        experiment="loro_003",
        variant="base",
    )
    np.testing.assert_allclose(report["mean"], expected.mean(axis=0))
    np.testing.assert_allclose(report["std_sample"], expected.std(axis=0, ddof=1))
    assert report["pixels"] == 7
    assert (
        report["selected_training_windows"] == 3
        and report["excluded_zero_kelp_windows"] == 0
    )
    assert report["kelp_only"] is False
    assert report["experiment"] == "loro_003" and report["variant"] == "base"
    assert calls == [("loro_003", "base")]


def test_overlapping_chips_count_pixel_exposures_and_share_one_source(
    collection, tmp_path
):
    source = np.arange(1, 19, dtype=np.uint16).reshape(2, 3, 3)
    images = [source[:, :2].copy(), source[:, 1:].copy()]
    chips, assignments, rows, _ = collection(images, ["red", "green", "blue"])
    rows[1]["source_id"] = rows[0]["source_id"]
    expected = _direct_pixels(images, None)
    report = compute_channel_stats(chips, assignments, tmp_path / "overlap.json")
    assert report["pixels"] == 8  # The two shared source pixels contribute twice.
    assert report["selected_training_sources"] == 1
    np.testing.assert_allclose(report["mean"], expected.mean(axis=0))
    np.testing.assert_allclose(report["std_sample"], expected.std(axis=0, ddof=1))


def test_existing_report_is_refused_before_payload_or_manifest_reads(
    tmp_path, monkeypatch
):
    output = tmp_path / "existing.json"
    output.write_text("keep this report\n")

    def forbidden(*args, **kwargs):
        pytest.fail("Initial overwrite refusal must happen before input reads")

    monkeypatch.setattr(np, "load", forbidden)
    monkeypatch.setattr("kelpseg.prepare.channel_stats.select_windows", forbidden)
    with pytest.raises(PreparationError, match="fresh report"):
        compute_channel_stats(tmp_path / "missing", tmp_path / "missing.csv", output)
    assert output.read_text() == "keep this report\n"


@pytest.mark.parametrize("valid_pixels", [0, 1])
def test_insufficient_native_pixels_fail_without_a_report(
    collection, tmp_path, valid_pixels
):
    image = np.zeros((1, 1, 3), dtype=np.uint16)
    if valid_pixels:
        image[0, 0] = [10, 20, 30]
    chips, assignments, _, _ = collection([image], ["red", "green", "blue"], [0])
    output = tmp_path / "insufficient.json"
    with pytest.raises(
        PreparationError, match=rf"at least two valid pixels; found {valid_pixels}"
    ):
        compute_channel_stats(chips, assignments, output)
    assert not output.exists()


@pytest.mark.parametrize(
    ("image", "cap", "band"),
    [
        (
            np.array([[[10, 5, 1], [20, 5, 2], [30, 5, 3]]], dtype=np.uint16),
            None,
            "green",
        ),
        (
            np.array([[[5001, 5, 1], [6000, 6, 2], [65535, 7, 3]]], dtype=np.uint16),
            5000,
            "red",
        ),
    ],
)
def test_zero_variance_names_the_band_including_cap_induced_variance_loss(
    collection, tmp_path, image, cap, band
):
    chips, assignments, _, _ = collection([image], ["red", "green", "blue"], [0])
    output = tmp_path / "constant.json"
    with pytest.raises(PreparationError, match=rf"Zero variance.*{band}"):
        compute_channel_stats(chips, assignments, output, clip_value=cap)
    assert not output.exists()


def test_empty_training_selection_does_not_open_payloads(
    collection, tmp_path, monkeypatch
):
    chips, assignments, rows, _ = collection(_images(3)[:1], ["red", "green", "blue"])
    rows[0]["split"] = "val"

    def forbidden(*args, **kwargs):
        pytest.fail("No held-out payload should be opened")

    monkeypatch.setattr(np, "load", forbidden)
    output = tmp_path / "empty.json"
    with pytest.raises(PreparationError, match="No selected training windows"):
        compute_channel_stats(chips, assignments, output)
    assert not output.exists()


@pytest.mark.parametrize("cap", [0, -1, float("nan"), float("inf"), True])
def test_invalid_caps_fail_before_inputs_are_opened(tmp_path, cap):
    with pytest.raises(PreparationError, match="clip_value"):
        compute_channel_stats(
            tmp_path / "missing",
            tmp_path / "missing.csv",
            tmp_path / "invalid.json",
            clip_value=cap,
        )


def test_pixel_stats_cli_writes_the_requested_selection_and_band_summary(
    collection, tmp_path
):
    chips, assignments, _, calls = collection(
        _images(3), ["red", "green", "blue"], [1, 1, 0]
    )
    output = tmp_path / "cli.json"
    result = CliRunner().invoke(
        app,
        [
            "pixel-stats",
            "--chips",
            str(chips),
            "--assignments",
            str(assignments),
            "--experiment",
            "loro_003",
            "--variant",
            "base",
            "--kelp-only",
            "--clip-value",
            "5000",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_text())
    assert report["pixels"] == 5 and report["selected_training_windows"] == 2
    assert report["clip_value"] == 5000 and report["kelp_only"] is True
    assert calls == [("loro_003", "base")]
    assert "non-nodata pixel exposures: 5" in result.stdout
    assert all(f"{band}: mean" in result.stdout for band in ("red", "green", "blue"))
    assert "sample std" in result.stdout


def test_pixel_stats_cli_reports_missing_inputs_without_a_traceback(tmp_path):
    output = tmp_path / "missing.json"
    result = CliRunner().invoke(
        app,
        [
            "pixel-stats",
            "--chips",
            str(tmp_path / "missing"),
            "--assignments",
            str(tmp_path / "missing.csv"),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 1
    assert "Error:" in result.stderr and "recipe.json" in result.stderr
    assert "Traceback" not in result.output
    assert not output.exists()


def test_statistics_module_does_not_import_tiff_ml_or_visualization_frameworks(
    tmp_path,
):
    code = """
import importlib.abc
import sys
class BlockUnneededImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'rasterio','torch','lightning','wandb','albumentations','matplotlib'}:
            raise AssertionError('Unexpected statistics dependency: ' + fullname)
sys.meta_path.insert(0, BlockUnneededImports())
from kelpseg.prepare.channel_stats import compute_channel_stats
assert callable(compute_channel_stats)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
