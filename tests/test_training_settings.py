"""Recipes preserve explicit physical channels and historical training choices."""

from dataclasses import replace
from pathlib import Path

import pytest

from kelpseg.bands import resolve_band_indices
from kelpseg.preprocessing import BAND_NAMES, MEAN, STD
from kelpseg.training.settings import TrainingSettings, load_settings

RECIPES = Path(__file__).resolve().parents[1] / "configs/train"


@pytest.mark.parametrize(
    ("recipe", "bands"),
    [
        ("planet8", BAND_NAMES),
        ("planet4", ("red", "green", "blue", "nir")),
        ("planet3", ("nir", "red", "green")),
        ("planet_RGB", ("red", "green", "blue")),
    ],
)
def test_recipe_order_and_historical_defaults(recipe, bands):
    settings = load_settings(RECIPES / f"{recipe}.toml")
    assert settings.name == recipe
    assert settings.experiment == "baseline"
    assert settings.variant == "augmented"
    assert settings.paths_file == str(RECIPES.parent.parent / "paths.local.toml")
    assert settings.band_names == bands
    indices = resolve_band_indices(BAND_NAMES, bands)
    assert settings.mean == tuple(MEAN[i] for i in indices)
    assert settings.std == tuple(STD[i] for i in indices)
    assert settings.clip_value == 5000
    assert (settings.seed, settings.epochs, settings.warmup_epochs) == (42, 70, 5)
    assert (settings.batch_size, settings.accumulate_grad_batches) == (3, 8)
    assert settings.learning_rate == 3e-4
    assert settings.min_lr == 3e-5
    assert settings.betas == (0.9, 0.95)
    assert settings.weight_decay == 0.01
    assert settings.gradient_clip_val == 0.8
    assert settings.precision == "bf16-mixed"
    assert settings.accelerator == "cuda"
    assert settings.encoder_weights == "imagenet"
    assert settings.deterministic


def test_rgb_selector_unchanged_and_nir_recipe_explicit():
    assert resolve_band_indices(BAND_NAMES, "rgb") == (5, 3, 1)
    settings = load_settings(RECIPES / "planet3.toml")
    assert resolve_band_indices(BAND_NAMES, settings.band_names) == (7, 5, 3)


def test_cpu_recipe_separates_bounded_float32_smoke():
    settings = load_settings(RECIPES / "tiny_cpu.toml")
    assert settings.chips == "examples/runs/my-tiny-v2-01-chips"
    assert settings.assignments == "examples/runs/my-tiny-v2-01-splits/assignments.csv"
    assert settings.accelerator == "cpu"
    assert settings.precision == "32-true"
    assert settings.num_workers == 0
    assert not settings.persistent_workers
    assert settings.encoder_weights is None
    assert settings.epochs == 2
    assert settings.limit_train_batches == 2
    assert type(settings.limit_train_batches) is int
    assert settings.limit_val_batches == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"name": ""},
        {"name": "../escape"},
        {"name": 3},
        {"experiment": "loro_001"},
        {"paths_file": ""},
        {"variant": "unknown"},
        {"epochs": True},
        {"batch_size": 0},
        {"accumulate_grad_batches": -1},
        {"warmup_epochs": 70},
        {"seed": -1},
        {"learning_rate": float("nan")},
        {"min_lr": 1},
        {"betas": (0.9, 1.0)},
        {"num_workers": 0},
        {"accelerator": "mps"},
        {"accelerator": "cpu"},
        {"precision": "16-mixed"},
        {"limit_train_batches": True},
        {"limit_val_batches": 0.0},
        {"wandb": "false"},
        {"deterministic": "false"},
        {"deterministic": 0},
        {"chips": ""},
        {"clip_value": 4000},
        {"mean": (0,) * 8},
        {"band_names": ("nir", "red", "red")},
    ],
)
def test_reject_ordinary_setting_mistakes(changes):
    with pytest.raises(ValueError):
        replace(TrainingSettings(), **changes)


def test_reject_unknown_and_malformed_recipe(tmp_path):
    recipe = tmp_path / "bad.toml"
    recipe.write_text("epoch = 3\n")
    with pytest.raises(ValueError, match="Unknown training settings: epoch"):
        load_settings(recipe)
    recipe.write_text('band_names = "rgb"\n')
    with pytest.raises(ValueError, match="TOML array"):
        load_settings(recipe)
    recipe.write_text("epochs = [\n")
    with pytest.raises(ValueError, match="Cannot read training recipe"):
        load_settings(recipe)


def test_machine_path_reference_resolves_relative_to_recipe(tmp_path, monkeypatch):
    recipe_dir = tmp_path / "recipes"
    recipe_dir.mkdir()
    recipe = recipe_dir / "train.toml"
    recipe.write_text('paths_file = "../machine.toml"\nvariant = "base"\n')
    monkeypatch.chdir(tmp_path.parent)
    settings = load_settings(recipe)
    assert settings.paths_file == str(tmp_path / "machine.toml")
    assert settings.variant == "base"
    recipe.write_text("")
    assert load_settings(recipe).paths_file == str(recipe_dir / "paths.local.toml")


def test_recipe_can_disable_deterministic_algorithms(tmp_path):
    recipe = tmp_path / "train.toml"
    recipe.write_text("deterministic = false\n")
    assert not load_settings(recipe).deterministic


@pytest.mark.parametrize("epochs", [(0,), (71,), (4, 4), (5, 4), (True,), (4.5,), [4]])
def test_invalid_checkpoint_epochs(epochs: object) -> None:
    """Reject ambiguous, unordered, or out-of-budget retention epoch numbers."""
    with pytest.raises(ValueError, match="checkpoint_epochs"):
        TrainingSettings(checkpoint_epochs=epochs)


def test_lr_comparison_recipes() -> None:
    """Keep the four sweep recipes controlled except for name, LR and decay."""
    from dataclasses import asdict

    root = Path("configs/train/lr_comparison")
    recipes = [load_settings(path) for path in sorted(root.glob("*.toml"))]
    assert len(recipes) == 4
    assert [(r.learning_rate, r.weight_decay) for r in recipes] == [
        (3e-4, 0.01),
        (1.5e-4, 0.01),
        (1e-4, 0.01),
        (1.5e-4, 0.05),
    ]
    normalized = []
    for recipe in recipes:
        assert recipe.checkpoint_epochs == tuple(range(4, 13))
        assert (recipe.min_lr, recipe.epochs, recipe.warmup_epochs) == (3e-6, 70, 5)
        assert recipe.early_stopping_patience == 20 and recipe.wandb
        values = asdict(recipe)
        for key in ("name", "learning_rate", "weight_decay"):
            values.pop(key)
        normalized.append(values)
    assert all(value == normalized[0] for value in normalized)


def test_model_size_recipes_match_b() -> None:
    """Change only the model encoder and run name from the B recipe."""
    from dataclasses import asdict

    reference = asdict(load_settings("configs/train/lr_comparison/b_half_lr.toml"))
    for size in ("b2", "b1", "b0"):
        candidate = asdict(load_settings(f"configs/train/model_size/{size}.toml"))
        assert candidate["encoder_name"] == f"mit_{size}"
        for key in ("name", "encoder_name"):
            candidate.pop(key)
        expected = {
            k: v for k, v in reference.items() if k not in ("name", "encoder_name")
        }
        assert candidate == expected
    with pytest.raises(ValueError, match="encoder_name"):
        TrainingSettings(encoder_name="resnet50")
