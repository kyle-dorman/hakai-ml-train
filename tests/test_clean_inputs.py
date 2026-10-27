from dataclasses import replace
from pathlib import Path

import pytest
from clean_fixtures import sample

from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.clean_inputs import build_clean_plan, load_clean_recipe


def test_plan_is_header_only_no_writes(tmp_path, monkeypatch):
    plan, _, _ = sample(tmp_path)
    before = sorted(tmp_path.rglob("*"))
    from kelpseg.prepare import check

    monkeypatch.setattr(
        check, "_scan", lambda *a: pytest.fail("pixels read during plan")
    )
    assert (
        build_clean_plan(plan.images, plan.labels, plan.output, plan.recipe).pairs
        == plan.pairs
    )
    assert sorted(tmp_path.rglob("*")) == before


@pytest.mark.parametrize(
    "change",
    [
        {"qa_masks": "yes"},
        {"compression": "jpeg"},
        {"label_values": (0, 1)},
        {"label_values": (0, 3, 255)},
        {"block_size": True},
    ],
)
def test_direct_recipe_validation(tmp_path, change):
    plan, _, _ = sample(tmp_path)
    with pytest.raises(PreparationError):
        build_clean_plan(
            plan.images, plan.labels, plan.output, replace(plan.recipe, **change)
        )


@pytest.mark.parametrize(
    "setting",
    [
        "unknown = 3",
        'qa_masks = "yes"',
        'compression = "jpeg"',
        'image_band_counts = "eight"',
        "schema_version = true",
    ],
)
def test_unknown_or_invalid_toml(tmp_path, setting):
    path = tmp_path / "recipe.toml"
    path.write_text(setting)
    with pytest.raises(PreparationError):
        load_clean_recipe(path)


def test_overlap_symlinks_and_empty_scopes(tmp_path):
    plan, _, _ = sample(tmp_path)
    for target in (plan.images / "new", tmp_path, plan.labels):
        with pytest.raises(PreparationError, match="overlap"):
            build_clean_plan(plan.images, plan.labels, target, plan.recipe)
    link = tmp_path / "alias"
    link.symlink_to(plan.images, target_is_directory=True)
    with pytest.raises(PreparationError, match="Symlink"):
        build_clean_plan(link, None, plan.output, plan.recipe)
    with pytest.raises(PreparationError, match="--parent"):
        build_clean_plan(
            plan.images, None, plan.output, plan.recipe, parent=tmp_path / "parent"
        )


def test_shipped_recipe_explicit_fallback():
    recipe = load_clean_recipe(
        Path(__file__).resolve().parents[1] / "configs/clean/planet8.toml"
    )
    assert recipe.missing_image_nodata == 0 and not recipe.qa_masks
