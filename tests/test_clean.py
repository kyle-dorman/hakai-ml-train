import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest
import rasterio
from clean_fixtures import sample, write_tiff
from typer.testing import CliRunner

from kelpseg.cli import app
from kelpseg.prepare import clean
from kelpseg.prepare.check import PreparationError, check_inputs
from kelpseg.prepare.clean import clean_dataset, verify_cleaned_release
from kelpseg.prepare.clean_inputs import build_clean_plan


def test_shared_clean_exact_arrays_counts_metadata_and_originals(tmp_path):
    plan, original, categories = sample(tmp_path)
    before = {
        p: (p.read_bytes(), p.stat().st_mode)
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    result = clean_dataset(plan)
    expected_image = original.copy()
    expected_image[:, :, [0, 4]] = 0
    expected_label = np.full((4, 5), 3, dtype=np.uint8)
    expected_label[:, 1:4] = categories
    with (
        rasterio.open(result / "images/cove/spring.TIF") as image,
        rasterio.open(result / "labels/cove/spring.tiff") as label,
    ):
        np.testing.assert_array_equal(image.read(), expected_image)
        np.testing.assert_array_equal(label.read(1), expected_label)
        assert image.nodatavals == (0,) * 3 and label.nodata == 3
        assert image.transform == label.transform and image.crs == label.crs
        assert image.width == label.width == 5
        assert image.read()[:, 0, 1].tolist() == [65535, 9, 9]
        assert image.read()[:, 1, 2].tolist() == [9] * 3
    record = json.loads((result / "sources.json").read_text())["sources"][0]
    assert record["identity"]["region"] is None
    for role, path in (("image", plan.pairs[0].image), ("label", plan.pairs[0].label)):
        assert record["inputs"][role]["path"] == str(path)
        assert (
            record["inputs"][role]["sha256"]
            == hashlib.sha256(before[path][0]).hexdigest()
        )
        assert record["inputs"][role]["bytes"] == len(before[path][0])
    assert record["counts"] == {
        "total_pixels": 20,
        "original_image_nodata": 1,
        "outside_label_footprint": 8,
        "nodata_and_outside": 1,
        "retained_valid_imagery": 12,
        "final_exclusions": 8,
        "changed_image_pixels": 8,
        "existing_label_ignore": 1,
        "changed_label_pixels": 8,
    }
    assert sum(record["class_transitions_target_grid"].values()) == 20
    assert record["label_audit"]["fn"] == 0
    assert not (result / "qa").exists()
    assert all(
        (p.read_bytes(), p.stat().st_mode) == state for p, state in before.items()
    )
    assert check_inputs(
        result / "images",
        result / "labels",
        plan.recipe.check_recipe("cleaned"),
        full=True,
    ).passed
    assert verify_cleaned_release(result)["status"] == "complete"


def test_image_only_preserves_values_and_no_fake_labels(tmp_path):
    plan, original, _ = sample(tmp_path, paired=False)
    result = clean_dataset(plan)
    expected = original.copy()
    expected[:, 0, 0] = 0
    with rasterio.open(result / "images/cove/spring.TIF") as source:
        np.testing.assert_array_equal(source.read(), expected)
    assert not (result / "labels").exists()
    assert (
        json.loads((result / "sources.json").read_text())["summary_counts"][
            "outside_label_footprint"
        ]
        == 0
    )


def test_qa_and_window_sizes_preserve_core_pixels_and_counts(tmp_path):
    first, _, _ = sample(tmp_path / "one", qa=False, block_size=2)
    second, _, _ = sample(tmp_path / "two", qa=True, block_size=3)
    a, b = clean_dataset(first), clean_dataset(second)
    one = json.loads((a / "sources.json").read_text())["sources"][0]
    two = json.loads((b / "sources.json").read_text())["sources"][0]
    assert one["counts"] == two["counts"]
    for name, expected in one["files"].items():
        assert two["files"][name] == expected
        assert (a / name).read_bytes() == (b / name).read_bytes()
    with rasterio.open(b / "qa/reason/cove/spring.tif") as reason:
        values = reason.read(1)
        assert values[0, 0] == 3 and values[1, 0] == 2 and values[1, 1] == 0


def test_retained_zero_collision_and_outside_zero_allowed(tmp_path):
    plan, values, _ = sample(tmp_path, paired=False)
    values[:, 2, 2] = 0
    write_tiff(plan.pairs[0].image, values, nodata=65535)
    with pytest.raises(PreparationError, match="collide"):
        clean_dataset(plan)
    assert not plan.output.exists()
    other, values, _ = sample(tmp_path / "outside")
    values[:, 2, 0] = 0
    write_tiff(other.pairs[0].image, values, nodata=65535)
    clean_dataset(other)


def test_source_sidecars_masks_and_overviews_are_inactive(tmp_path):
    plan, original, _ = sample(tmp_path)
    for pair in plan.pairs:
        for path in (pair.image, pair.label):
            with (
                rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False),
                rasterio.open(path, "r+") as raster,
            ):
                raster.write_mask(
                    np.zeros((raster.height, raster.width), dtype=np.uint8)
                )
            path.with_name(path.name + ".aux.xml").write_text(
                '<PAMDataset><PAMRasterBand band="1"><NoDataValue>7</NoDataValue></PAMRasterBand></PAMDataset>'
            )
    plan = build_clean_plan(plan.images, plan.labels, plan.output, plan.recipe)
    result = clean_dataset(plan)
    assert not list(result.rglob("*.msk")) and not list(result.rglob("*.xml"))
    with rasterio.open(result / "images/cove/spring.TIF") as raster:
        assert raster.nodata == 0 and raster.read()[1, 0, 1] == original[1, 0, 1]
        assert raster.dataset_mask()[1, 1] == 255
    with rasterio.open(result / "labels/cove/spring.tiff") as raster:
        assert raster.read(1)[0, 1] == 0 and raster.nodata == 3
    assert any(
        v.get("disposition")
        for v in json.loads((result / "sources.json").read_text())[
            "inactive_assets"
        ].values()
    )


def test_completed_output_is_verified_read_only_and_never_reused(tmp_path):
    plan, _, _ = sample(tmp_path)
    clean_dataset(plan)
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in plan.output.rglob("*")
        if path.is_file()
    }
    assert verify_cleaned_release(plan.output)["status"] == "complete"
    with pytest.raises(PreparationError):
        clean_dataset(plan)
    assert before == {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before
    }
    image = plan.output / "images/cove/spring.TIF"
    image.write_bytes(image.read_bytes() + b"corruption")
    with pytest.raises(PreparationError):
        verify_cleaned_release(plan.output)


def test_interrupted_run_stays_incomplete_and_requires_a_fresh_output(
    tmp_path, monkeypatch
):
    plan, _, _ = sample(tmp_path)
    real_clean_pair = clean._clean_pair

    def interrupted(*args):
        real_clean_pair(*args)
        raise RuntimeError("fixture interruption after raster close")

    monkeypatch.setattr(clean, "_clean_pair", interrupted)
    with pytest.raises(PreparationError, match="interruption"):
        clean_dataset(plan)
    monkeypatch.setattr(clean, "_clean_pair", real_clean_pair)

    stage = plan.output.with_name(f".{plan.output.name}.incomplete")
    assert stage.is_dir() and not plan.output.exists()
    assert not (stage / "manifest.json").exists()
    assert not (stage / "receipts").exists()
    assert not (stage / "state.json").exists()
    assert not (stage / "active.json").exists()
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in stage.rglob("*")
        if path.is_file()
    }
    with pytest.raises(PreparationError, match="[Ii]ncomplete|fresh"):
        clean_dataset(plan)
    assert before == {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before
    }

    # The caller can inspect the failed attempt and choose a new output.
    fresh = replace(plan, output=tmp_path / "second-attempt")
    assert clean_dataset(fresh) == fresh.output
    assert before == {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before
    }


@pytest.mark.parametrize("symlink", [False, True])
def test_existing_staging_scope_is_refused_without_touching_it(tmp_path, symlink):
    plan, _, _ = sample(tmp_path)
    stage = plan.output.with_name(f".{plan.output.name}.incomplete")
    preserved = stage
    if symlink:
        preserved = tmp_path / "outside-content"
        preserved.mkdir()
        stage.symlink_to(preserved, target_is_directory=True)
    else:
        stage.mkdir()
    evidence = preserved / "keep.txt"
    evidence.write_text("This is not owned by the new run.")
    before = evidence.read_bytes(), evidence.stat().st_mtime_ns
    with pytest.raises(PreparationError):
        clean_dataset(plan)
    assert (evidence.read_bytes(), evidence.stat().st_mtime_ns) == before
    assert not plan.output.exists()


def test_another_run_cannot_claim_the_same_staging_directory(tmp_path, monkeypatch):
    plan, _, _ = sample(tmp_path)
    real_clean_pair = clean._clean_pair
    attempted = False

    def try_competing_run(*args):
        nonlocal attempted
        attempted = True
        with pytest.raises(PreparationError):
            clean_dataset(plan)
        return real_clean_pair(*args)

    monkeypatch.setattr(clean, "_clean_pair", try_competing_run)
    assert clean_dataset(plan) == plan.output
    assert attempted


def test_independent_checker_prevents_broken_publication(tmp_path, monkeypatch):
    plan, _, _ = sample(tmp_path)
    real = clean._clean_pair

    def broken(*args):
        record = real(*args)
        with rasterio.open(args[2] / "labels/cove/spring.tiff", "r+") as raster:
            values = raster.read(1)
            values[0, 0] = 0
            raster.write(values, 1)
        return record

    monkeypatch.setattr(clean, "_clean_pair", broken)
    with pytest.raises(
        PreparationError, match="Independent cleaned-output check failed"
    ):
        clean_dataset(plan)
    assert not plan.output.exists()


def test_cli_dry_run_and_error_messages(tmp_path):
    plan, _, _ = sample(tmp_path)
    recipe = tmp_path / "recipe.toml"
    recipe.write_text(
        'schema_version=1\nimage_band_counts=[3]\nimage_dtypes=["uint16"]\nlabel_values=[0,1,2,3,4]\n'
    )
    args = [
        "clean",
        "--images",
        str(plan.images),
        "--labels",
        str(plan.labels),
        "--output",
        str(plan.output),
        "--recipe",
        str(recipe),
    ]
    before = sorted(tmp_path.rglob("*"))
    dry = CliRunner().invoke(app, args + ["--dry-run"])
    assert dry.exit_code == 0, dry.output
    assert "no pixels read" in dry.stdout and sorted(tmp_path.rglob("*")) == before
    good = CliRunner().invoke(app, args)
    assert good.exit_code == 0, good.output
    assert "[Clean 1/1]" in good.stderr
    for phase in range(1, 5):
        assert f"Phase {phase}:" in good.stderr
    assert "effective original nodata 65535" in good.stderr
    assert "detailed QA masks disabled" in good.stderr
    assert "20 pixels; nodata 1; outside labels 8; excluded 8" in good.stderr
    bad = CliRunner().invoke(app, args)
    assert (
        bad.exit_code == 1 and "Error:" in bad.stderr and "Traceback" not in bad.output
    )


def test_clean_cli_has_no_resume_mode():
    runner = CliRunner()
    help_result = runner.invoke(app, ["clean", "--help"])
    assert help_result.exit_code == 0
    assert "--resume" not in help_result.stdout
    result = runner.invoke(app, ["clean", "--resume"])
    assert result.exit_code != 0
    assert "No such option" in result.stderr


def test_changed_then_restored_source_is_detected_during_one_pass(
    tmp_path, monkeypatch
):
    plan, _, _ = sample(tmp_path)
    image = plan.pairs[0].image
    original = image.read_bytes()
    real_clean_pair = clean._clean_pair

    def change_restore_after_read(*args):
        record = real_clean_pair(*args)
        # Content returns to the original value, but timestamps expose a write
        # during this run. Never publish evidence over changing inputs.
        with image.open("ab") as stream:
            stream.write(b"temporary change")
        image.write_bytes(original)
        return record

    monkeypatch.setattr(clean, "_clean_pair", change_restore_after_read)
    with pytest.raises(PreparationError, match="changed"):
        clean_dataset(plan)
    assert image.read_bytes() == original and not plan.output.exists()


def test_matching_labels_skip_reprojection_but_still_apply_nodata_repairs(
    tmp_path, monkeypatch, caplog
):
    from kelpseg.prepare import alignment

    plan, original, _ = sample(tmp_path)
    categories = np.array(
        [[0, 1, 0, 2, 4], [2, 3, 4, 0, 1], [0, 0, 1, 2, 4], [1, 0, 0, 3, 2]],
        dtype=np.uint8,
    )
    write_tiff(plan.pairs[0].label, categories, nodata=0)
    plan = build_clean_plan(plan.images, plan.labels, plan.output, plan.recipe)

    def unexpected_reprojection(*args, **kwargs):
        pytest.fail("Already matching paired labels must not be reprojected")

    monkeypatch.setattr(alignment, "reproject", unexpected_reprojection)
    caplog.set_level("INFO", logger="kelpseg.prepare")
    result = clean_dataset(plan)
    assert "label grid already matches; reading stored labels directly" in caplog.text
    assert "nearest-aligning stored labels" not in caplog.text
    expected_image = original.copy()
    expected_image[:, 0, 0] = 0
    expected_labels = categories.copy()
    expected_labels[0, 0] = 3
    with (
        rasterio.open(result / "images/cove/spring.TIF") as image,
        rasterio.open(result / "labels/cove/spring.tiff") as label,
    ):
        np.testing.assert_array_equal(image.read(), expected_image)
        np.testing.assert_array_equal(label.read(1), expected_labels)
        assert image.nodata == 0 and label.nodata == 3
        assert image.read()[:, 1, 1].tolist() == [9, 9, 9]
    record = json.loads((result / "sources.json").read_text())["sources"][0]
    assert record["counts"]["outside_label_footprint"] == 0
    assert record["counts"]["changed_image_pixels"] == 1
    assert record["counts"]["changed_label_pixels"] == 1
    assert record["counts"]["existing_label_ignore"] == 2


def test_one_pass_cleanup_hashes_each_input_and_raster_only_once(tmp_path, monkeypatch):
    plan, _, _ = sample(tmp_path)
    real_hash = clean._hash
    reads = []

    def counted_hash(path):
        reads.append(path)
        return real_hash(path)

    monkeypatch.setattr(clean, "_hash", counted_hash)
    clean_dataset(plan)
    assert reads.count(plan.pairs[0].image) == 1
    assert reads.count(plan.pairs[0].label) == 1
    stage = plan.output.with_name(f".{plan.output.name}.incomplete")
    assert reads.count(stage / "images/cove/spring.TIF") == 1
    assert reads.count(stage / "labels/cove/spring.tiff") == 1
