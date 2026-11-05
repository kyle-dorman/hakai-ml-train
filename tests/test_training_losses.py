"""Independent binary-loss arithmetic, masks, gradients and recipe combinations."""

from dataclasses import asdict
from itertools import combinations

import pytest
import torch
from torch.nn import functional as F

from kelpseg.training.loss import BinaryObjective, boundary_weights
from kelpseg.training.loss_settings import DEFAULT_PARAMETERS, LossTerm
from kelpseg.training.settings import load_settings

NAMES = tuple(DEFAULT_PARAMETERS)
OVERLAP = {"dice", "jaccard", "tversky", "focal_tversky"}


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("label", [0, 1, -100])
def test_uniform_labels_finite_gradients_and_empty_foreground(name, label):
    logits = torch.zeros((2, 1, 5, 5), requires_grad=True)
    loss, values = BinaryObjective((LossTerm(name),))(
        logits, torch.full((2, 5, 5), label)
    )
    assert set(values) == {name}
    loss.backward()
    assert torch.isfinite(loss) and torch.isfinite(logits.grad).all()
    if label == -100 or (label == 0 and name in OVERLAP):
        assert loss == 0 and not logits.grad.any()
    else:
        assert loss > 0 and logits.grad.any()


@pytest.mark.parametrize("name", NAMES)
def test_mixed_labels_ignore_pixels_and_accept_b1hw(name):
    logits = torch.linspace(-3, 3, 50).reshape(2, 1, 5, 5).requires_grad_()
    targets = torch.zeros((2, 5, 5), dtype=torch.long)
    targets[:, 2:4, 2:4] = 1
    targets[:, 0] = -100
    objective = BinaryObjective((LossTerm(name),))
    loss, _ = objective(logits, targets)
    loss.backward()
    assert torch.isfinite(logits.grad).all()
    assert (logits.grad[:, 0][targets == -100] == 0).all()
    assert logits.grad[:, 0][targets != -100].any()
    changed = logits.detach().clone()
    changed[:, 0][targets == -100] = -1000
    torch.testing.assert_close(objective(changed, targets[:, None])[0], loss)


def test_overlap_and_focal_match_hand_computed_formulas():
    probability = torch.tensor([0.8, 0.3, 0.4, 0.2])
    target = torch.tensor([1, 1, 0, 0]).reshape(1, 2, 2)
    logits = torch.logit(probability).reshape(1, 1, 2, 2)
    tp, fp, fn = 1.1, 0.6, 0.9
    expected = {
        "dice": 1 - 2 * tp / (2 * tp + fp + fn),
        "jaccard": 1 - tp / (tp + fp + fn),
        "tversky": 1 - tp / (tp + 0.3 * fp + 0.7 * fn),
        "focal_tversky": (1 - tp / (tp + 0.3 * fp + 0.7 * fn)) ** 0.75,
    }
    for name, value in expected.items():
        parameters = {"alpha": 0.3, "beta": 0.7} if "tversky" in name else {}
        if name == "focal_tversky":
            parameters["gamma"] = 0.75
        loss, _ = BinaryObjective((LossTerm(name, parameters=parameters),))(
            logits, target
        )
        assert loss.item() == pytest.approx(value)
    correct_class_probability = torch.tensor([0.8, 0.3, 0.6, 0.8])
    alpha = torch.tensor([0.25, 0.25, 0.75, 0.75])
    focal_expected = (
        -alpha * (1 - correct_class_probability) ** 2 * correct_class_probability.log()
    ).mean()
    actual, _ = BinaryObjective((LossTerm("focal", parameters={"alpha": 0.25}),))(
        logits, target
    )
    torch.testing.assert_close(actual, focal_expected)


@pytest.mark.parametrize("gamma", [0.75, 1.0, 2.0])
def test_focal_tversky_zero_loss_has_finite_gradients(gamma):
    logits = torch.full((1, 1, 2, 2), 1000.0, requires_grad=True)
    objective = BinaryObjective(
        (LossTerm("focal_tversky", parameters={"gamma": gamma}),)
    )
    loss, _ = objective(logits, torch.ones((1, 2, 2)))
    loss.backward()
    assert loss == 0 and torch.isfinite(logits.grad).all()


def test_boundary_weights_and_normalized_bce_are_exact():
    target = torch.zeros((1, 7, 7), dtype=torch.long)
    target[:, :, 3:] = 1
    weights = boundary_weights(target, radius=1, factor=3)
    expected = torch.ones((1, 7, 7))
    expected[:, 1:6, 2:4] = 3
    torch.testing.assert_close(weights, expected)
    logits = torch.linspace(-2, 2, 49).reshape(1, 1, 7, 7).requires_grad_()
    objective = BinaryObjective(
        (LossTerm("boundary_bce", parameters={"factor": 3, "smoothing": 0}),)
    )
    actual, _ = objective(logits, target)
    elementwise = F.binary_cross_entropy_with_logits(
        logits[:, 0], target.float(), reduction="none"
    )
    torch.testing.assert_close(actual, (elementwise * expected).sum() / expected.sum())
    target[:, 3, 3] = -100
    weights = boundary_weights(target, radius=1, factor=3)
    assert (weights[:, 2:5, 2:5] == 1).all()
    # Foreground abutting unknown support alone is not a label transition.
    target[:] = 1
    target[:, :, :3] = -100
    assert (boundary_weights(target, 1, 3) == 1).all()


def test_boundary_factor_one_equals_smoothed_bce():
    logits = torch.randn(2, 1, 6, 6)
    targets = torch.randint(0, 2, (2, 6, 6))
    targets[:, 0] = -100
    terms = (LossTerm("bce"), LossTerm("boundary_bce", parameters={"factor": 1}))
    _, values = BinaryObjective(terms)(logits, targets)
    torch.testing.assert_close(values["bce"], values["boundary_bce"])


@pytest.mark.parametrize("names", [*combinations(NAMES, 2), NAMES])
def test_weighted_combinations_preserve_values_and_gradients(names):
    terms = tuple(
        LossTerm(name, weight=(index + 1) / 3) for index, name in enumerate(names)
    )
    logits = torch.linspace(-2, 2, 36).reshape(1, 1, 6, 6).requires_grad_()
    targets = torch.zeros((1, 6, 6), dtype=torch.long)
    targets[:, 2:4, 2:4] = 1
    targets[:, 0] = -100
    combined, components = BinaryObjective(terms)(logits, targets)
    separate = sum(
        term.weight * BinaryObjective((LossTerm(term.type),))(logits, targets)[0]
        for term in terms
    )
    torch.testing.assert_close(combined, separate)
    assert set(components) == set(names)
    expected_gradient = torch.autograd.grad(separate, logits)[0]
    combined.backward()
    torch.testing.assert_close(logits.grad, expected_gradient)


def test_recipe_roundtrip_resolves_defaults_and_parameters(tmp_path):
    recipe = tmp_path / "loss.toml"
    recipe.write_text("""[[losses]]
type = "boundary_bce"
weight = 0.6
parameters = { smoothing = 0.0, factor = 4, radius = 2 }
[[losses]]
type = "focal_tversky"
weight = 0.4
parameters = { alpha = 0.3, beta = 0.7, gamma = 0.75 }
""")
    settings = load_settings(recipe)
    assert settings.losses[0].parameters["radius"] == 2
    assert settings.losses[1].parameters["smooth"] == 0
    assert asdict(settings)["losses"][1]["parameters"]["gamma"] == 0.75


@pytest.mark.parametrize(
    "text",
    [
        "losses = []",
        'losses = "dice"',
        '[[losses]]\ntype = "unknown"',
        '[[losses]]\ntype = "dice"\nweight = 0',
        '[[losses]]\ntype = "dice"\nweight = nan',
        '[[losses]]\ntype = "dice"\nweight = true',
        '[[losses]]\ntype = "dice"\nparameters = { smoothing = 0.1 }',
        '[[losses]]\ntype = "bce"\nparameters = { smoothing = 1 }',
        '[[losses]]\ntype = "focal"\nparameters = { alpha = 2 }',
        '[[losses]]\ntype = "tversky"\nparameters = { alpha = 0, beta = 0 }',
        '[[losses]]\ntype = "boundary_bce"\nparameters = { radius = 1.5 }',
        '[[losses]]\ntype = "boundary_bce"\nparameters = { factor = 0.5 }',
        '[[losses]]\ntype = "focal_tversky"\nparameters = { gamma = 0 }',
        '[[losses]]\ntype = "dice"\n[[losses]]\ntype = "dice"',
        '[[losses]]\ntype = "bce"\nsmoothing = 0.1',
    ],
)
def test_recipe_rejects_loss_mistakes(tmp_path, text):
    recipe = tmp_path / "bad.toml"
    recipe.write_text(text)
    with pytest.raises(ValueError):
        load_settings(recipe)


@pytest.mark.parametrize("name", NAMES)
def test_bfloat16_inputs_use_float32_loss_arithmetic(name):
    logits = (
        torch.linspace(-3, 3, 36, dtype=torch.bfloat16)
        .reshape(1, 1, 6, 6)
        .requires_grad_()
    )
    targets = torch.zeros((1, 6, 6), dtype=torch.long)
    targets[:, 2:4, 2:4] = 1
    objective = BinaryObjective((LossTerm(name),))
    with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
        loss, values = objective(logits, targets)
    assert loss.dtype == values[name].dtype == torch.float32
    torch.testing.assert_close(loss, objective(logits.float(), targets)[0])
    loss.backward()
    assert torch.isfinite(logits.grad).all()


@pytest.mark.parametrize("loss_type", NAMES)
def test_per_image_pooling_keeps_identity_and_excludes_empty_images(loss_type):
    logits = torch.tensor(
        [
            [[[-2.0, 1.0], [0.5, -1.0]]],
            [[[3.0, 2.0], [-2.0, -3.0]]],
            [[[1.0, 2.0], [3.0, 4.0]]],
        ],
        requires_grad=True,
    )
    targets = torch.tensor(
        [[[1, -100], [-100, -100]], [[0, 1], [0, 1]], [[-100, -100], [-100, -100]]]
    )
    per_image = BinaryObjective((LossTerm(loss_type, parameters={"per_image": True}),))
    pooled = BinaryObjective((LossTerm(loss_type),))
    actual, _ = per_image(logits, targets)
    expected = (
        pooled(logits[:1], targets[:1])[0] + pooled(logits[1:2], targets[1:2])[0]
    ) / 2
    torch.testing.assert_close(actual, expected)
    actual.backward()
    assert torch.isfinite(logits.grad).all()
    assert not logits.grad[2].any()
    if loss_type in ("bce", "dice", "lovasz", "jaccard", "tversky"):
        assert not torch.isclose(actual, pooled(logits, targets)[0])


def test_names_are_independent_and_repeated_types_work(tmp_path):
    recipe = tmp_path / "repeat.toml"
    recipe.write_text("""[[losses]]
type = "bce"
name = "pixel_bce"
weight = 0.25
parameters = { smoothing = 0.0 }
[[losses]]
type = "bce"
name = "smooth_bce"
weight = 0.75
parameters = { smoothing = 0.2, per_image = true }
""")
    settings = load_settings(recipe)
    logits = torch.tensor([[[[2.0, -1.0]]]])
    targets = torch.tensor([[[1, 0]]])
    loss, values = BinaryObjective(settings.losses)(logits, targets)
    assert set(values) == {"pixel_bce", "smooth_bce"}
    expected_plain = F.binary_cross_entropy_with_logits(logits[:, 0], targets.float())
    expected_smooth = F.binary_cross_entropy_with_logits(
        logits[:, 0], targets.float() * 0.8 + 0.1
    )
    torch.testing.assert_close(values["pixel_bce"], expected_plain)
    torch.testing.assert_close(loss, 0.25 * expected_plain + 0.75 * expected_smooth)
    assert asdict(settings)["losses"][1]["type"] == "bce"


def test_positive_weight_reduction_and_boundary_normalization():
    logits = torch.zeros((1, 1, 5, 5))
    targets = torch.zeros((1, 5, 5), dtype=torch.long)
    targets[:, :, 2:] = 1
    elementwise = F.binary_cross_entropy_with_logits(
        logits[:, 0], targets.float(), pos_weight=torch.tensor(3.0), reduction="none"
    )
    for reduction in ("mean", "sum"):
        actual, _ = BinaryObjective(
            (LossTerm("bce", parameters={"pos_weight": 3, "reduction": reduction}),)
        )(logits, targets)
        expected = elementwise.mean() if reduction == "mean" else elementwise.sum()
        torch.testing.assert_close(actual, expected)
    weights = torch.ones((1, 5, 5))
    weights[:, 1:4, 1:3] = 2
    for normalization in ("weights", "pixels"):
        actual, _ = BinaryObjective(
            (
                LossTerm(
                    "boundary_bce",
                    parameters={"pos_weight": 3, "normalization": normalization},
                ),
            )
        )(logits, targets)
        denominator = weights.sum() if normalization == "weights" else 25
        torch.testing.assert_close(actual, (elementwise * weights).sum() / denominator)


@pytest.mark.parametrize("loss_type", ["dice", "jaccard", "tversky", "focal_tversky"])
def test_overlap_options_match_installed_library(loss_type):
    from segmentation_models_pytorch.losses import DiceLoss, JaccardLoss, TverskyLoss

    logits = torch.tensor([[[[-2.0, 1.0], [2.0, -1.0]]]])
    targets = torch.tensor([[[1, 0], [1, 0]]])
    parameters = {"smooth": 0.3, "eps": 0.01, "log_loss": True}
    factory = {
        "dice": DiceLoss,
        "jaccard": JaccardLoss,
        "tversky": TverskyLoss,
        "focal_tversky": TverskyLoss,
    }[loss_type]
    if "tversky" in loss_type:
        parameters.update(alpha=0.3, beta=0.7, gamma=0.75)
    expected = factory(mode="binary", **parameters)(logits, targets)
    actual, _ = BinaryObjective((LossTerm(loss_type, parameters=parameters),))(
        logits, targets
    )
    torch.testing.assert_close(actual, expected)


@pytest.mark.parametrize(
    "parameters",
    [
        {"normalized": True, "reduction": "sum"},
        {"normalized": True, "reduction": "mean", "alpha": 0.3, "gamma": 1.5},
        {"reduced_threshold": 0.5, "reduction": "sum"},
    ],
)
def test_focal_options_match_installed_library(parameters):
    from segmentation_models_pytorch.losses import FocalLoss

    logits = torch.tensor([[[[-2.0, 1.0], [2.0, -1.0]]]])
    targets = torch.tensor([[[1, 0], [1, 0]]])
    expected = FocalLoss(mode="binary", **parameters)(logits, targets)
    actual, _ = BinaryObjective((LossTerm("focal", parameters=parameters),))(
        logits, targets
    )
    torch.testing.assert_close(actual, expected)


@pytest.mark.parametrize(
    "term",
    [
        {"type": "bce", "name": "loss"},
        {"type": "bce", "name": "iou"},
        {"type": "dice", "name": "bce_step"},
        {"type": "bce", "name": "bad/name"},
        {"type": "bce", "parameters": {"reduction": "none"}},
        {"type": "bce", "parameters": {"per_image": 1}},
        {"type": "bce", "parameters": {"pos_weight": 0}},
        {"type": "dice", "parameters": {"eps": 0}},
        {"type": "dice", "parameters": {"log_loss": "true"}},
        {"type": "focal", "parameters": {"reduced_threshold": 0.5}},
        {"type": "boundary_bce", "parameters": {"normalization": "unknown"}},
    ],
)
def test_invalid_experimental_options(term):
    with pytest.raises(ValueError):
        LossTerm(**term)


def test_loss_screen_recipes_are_matched_and_cover_all_types():
    from pathlib import Path

    baseline = load_settings("configs/train/planet8_gpu_70ep_fast.toml")
    recipes = sorted(Path("configs/train/losses").glob("*.toml"))
    assert len(recipes) == 13
    names = set()
    singles = set()
    budgets = set()
    for path in recipes:
        settings = load_settings(path)
        assert settings.name not in names
        names.add(settings.name)
        budgets.add(settings.epochs)
        expected = asdict(baseline)
        # The selected baseline now stops on plateaus; LR schedule stays matched.
        if path.stem == "bce_dice":
            expected["early_stopping_patience"] = 10
        actual = asdict(settings)
        for key in ("name", "epochs", "losses"):
            expected.pop(key)
            actual.pop(key)
        assert actual == expected, path
        assert settings.wandb and settings.epochs > settings.warmup_epochs
        if len(settings.losses) == 1:
            singles.add(settings.losses[0].type)
        logits = torch.zeros((1, 1, 5, 5), requires_grad=True)
        target = torch.zeros((1, 5, 5), dtype=torch.long)
        target[:, 2:4, 2:4] = 1
        loss, _ = BinaryObjective(settings.losses)(logits, target)
        loss.backward()
        assert torch.isfinite(loss) and torch.isfinite(logits.grad).all()
    assert singles == set(NAMES)
    assert len(budgets) == 1


def test_default_objective_adds_no_checkpoint_state_and_names_are_not_module_keys():
    assert not BinaryObjective().state_dict()
    objective = BinaryObjective((LossTerm("bce", name="training"),))
    _, components = objective(torch.zeros((1, 1, 2, 2)), torch.ones((1, 2, 2)))
    assert set(components) == {"training"}
