# Planet kelp segmentation

A small Python toolkit for binary kelp segmentation on Planet 8/4/3-band
imagery: prepare and chip data, train SegFormer models, map unlabeled imagery,
and evaluate saved predictions against supplied labels.

The selected CA/BC model is **8-band SegFormer B0, BCE + Dice, epoch-16 EMA,
trained with BC**. Its identity and location are in the
[experiment contract](docs/experiments.md#current-planet-8-band-b0-baseline).
Tiny training is a workflow check, not a reproduction of this model.

## Start here

Follow the [sequential tiny walkthrough](docs/quickstart.md) from installation
through a copied model, predictions and a labeled report. It uses a small Box
example and CPU training. Use [GPU setup](docs/gpu_setup.md) for production.
The [documentation index](docs/index.md) routes detailed recipes and references.

## Install

From this repository, with uv installed:

```bash
uv python install 3.12
uv sync --python 3.12 --frozen
uv run --frozen kelpseg --help
```

The installed command calls reusable functions in `kelpseg`. Settings are plain
recipe files; machine-specific paths and large artifacts stay outside Git.
Preparation writes once to a fresh destination and stops on failure. Original
imagery and labels are immutable. UCLA Box through rclone is the transfer and
backup store; see [storage policy](docs/data_artifacts.md).

## Development

Read [AGENTS.md](AGENTS.md), [the queue](docs/todo.md) and the selected
[task contract](tasks/README.md) before editing. Use Python 3.12 and the locked
environment. Relevant focused tests accompany changes:

```bash
uv run --frozen pytest
uv run --frozen ruff format --check .
uv run --frozen ruff check .
```

`uv run --frozen pytest -q tests/test_repository_hygiene.py` checks repository
file syntax, size, conflict markers and whitespace. No Git hooks are required.
`uv build` creates the installable wheel and source distribution.

See [history and recovery](docs/history.md) for completed studies and retired
code. New-region experiment recipes and a consolidated methods document remain
in the [pending roadmap](docs/todo.md).
