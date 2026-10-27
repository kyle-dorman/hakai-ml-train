# Planet kelp segmentation

A local rebuild of this fork into a small toolkit for binary kelp segmentation
on Planet 8/4/3-band imagery. The workflow covers data preparation and chipping,
training, evaluation, unlabeled inference, leave-one-region-out comparisons,
and adaptation to new regions.

The installed `kelpseg` package currently provides help/version and read-only
machine-path checks, plus generic byte-preserving raw organization from explicit
catalogs. Cleanup, training, and prediction commands arrive in later tasks. Retained legacy Planet code/tests support the ongoing
rebuild; unrelated applications have been removed. Historical Tasks 000–023 and
starting commit `ac933fd667c2ddb445b8a622d8404387a2d056e2` remain as evidence.

## Start here

Use the [researcher quickstart](docs/quickstart.md) for installation, local
settings, command output, and fixes for common errors. Development context is
routed through [docs/index.md](docs/index.md) and [the roadmap](docs/todo.md).
The legacy reference and provenance audit are complete;
[Task 027](tasks/027_verify_box_and_back_up_raw_reference_audit.md) owns the
raw/reference/audit backup and its verification status.

The target is one simple installable Python package, short explicit recipes,
strong uv defaults, and no `scripts/` directory. Test as much of the workflow as
practical on the Mac with small examples before moving to a GPU host. Full
training is not intended for the Mac.

## Environment

Use Python 3.12 and the locked uv environment:

```bash
uv python install 3.12
uv sync --python 3.12 --frozen
uv run kelpseg --help
uv run kelpseg --version
```

Create your local path settings as described in the quickstart, then run:

```bash
uv run kelpseg check-paths --paths paths.local.toml
```

The Typer command calls reusable Python functions. Most later workflow settings
will live in recipe files. The selected future training style is
`uv run kelpseg train --recipe <recipe-file>`; training is not implemented yet.

Development checks use synthetic CPU fixtures, including fresh wheel/sdist
installation outside the checkout:

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run pre-commit run --all-files
```

Use `uv build` to create the wheel and source distribution. The default
checkout environment includes `dev` and temporary `legacy` dependency groups;
only the new package's runtime dependencies are required to install its wheel.

## Data and experiments

Raw archives, organized and cleaned intermediates, chips, generated split
assignments, checkpoints, and results live outside Git. Keep preparation rules,
configs, focused tests, and human-readable cleanup documentation in Git.
UCLA Box through rclone is
the target backup/transfer store; the existing local root is
`/Volumes/x10pro/kelpseg`.

The planned three variants are **1 raw sources**, **2 organized intermediate**,
and **3 cleaned intermediate**. Both intermediates stay unsplit; organization
preserves source bytes, while cleanup records explicit transformations. The
scoped audit is complete; existing repaired datasets remain historical evidence.
See [docs/data_artifacts.md](docs/data_artifacts.md) for variant/provenance rules
and [docs/cleanup_provenance.md](docs/cleanup_provenance.md) for established facts
and remaining evidence limits. The organizer is implemented and bounded-smoke verified; full organized-release
materialization/publication and cleaning remain later tasks.

The first spectral comparison is interpreted as 8 bands, RGB+NIR, and RGB from
the same acquisitions. Start with the working SegFormer recipe; a possible RGB
DINOv3 variant follows separately. New-region work compares direct transfer,
kelp-checkpoint fine tuning, generic-pretrained fine tuning, and combined
old/new training on fixed held-out test data.

W&B remains `kdorman90-ucla/kelpseg`; new work uses new experiment identities.
See [docs/product.md](docs/product.md) for the research contract and
[docs/experiments.md](docs/experiments.md) for run and checkpoint rules.
