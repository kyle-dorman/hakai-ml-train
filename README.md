# Planet kelp segmentation

A local rebuild of this fork into a small toolkit for binary kelp segmentation
on Planet 8/4/3-band imagery. The workflow covers data preparation and chipping,
training, evaluation, unlabeled inference, leave-one-region-out comparisons,
and adaptation to new regions.

The legacy implementation is still present. Breaking changes and substantial
removal of unrelated code are intended. The starting commit is
`ac933fd667c2ddb445b8a622d8404387a2d056e2`; historical Tasks 000–023 remain
available as evidence. New package commands will be documented when implemented.

## Start here

Read [docs/index.md](docs/index.md) for task-specific context and
[docs/todo.md](docs/todo.md) for the ordered small-task roadmap. Tasks 025–026
completed the legacy reference and read-only provenance audit. Next, scope
Task 027 to verify Box and back up the three unchanged raw source ZIPs, the
legacy reference, and the audit.

The target is one simple installable Python package, short explicit recipes,
strong uv defaults, and no `scripts/` directory. Test as much of the workflow as
practical on the Mac with small examples before moving to a GPU host. Full
training is not intended for the Mac.

## Environment

Use Python 3.12 and the locked uv environment:

```bash
uv python install 3.12
uv sync --python 3.12 --frozen
```

Current code validation uses focused tests under `tests/` and:

```bash
uv run ruff format --check .
uv run ruff check .
```

Package build/install and replacement CLI checks arrive with the package task.

## Data and experiments

Raw archives, organized and cleaned intermediates, chips, generated split
assignments, checkpoints, and results live outside Git. Keep preparation rules,
configs, focused tests, and human-readable cleanup documentation in Git.
UCLA Box through rclone is
the target backup/transfer store; the existing local root is
`/Volumes/x10pro/kelpseg`.

The planned three variants are **1 raw ZIPs**, **2 organized intermediate**,
and **3 cleaned intermediate**. Both intermediates stay unsplit; organization
preserves source bytes, while cleanup records explicit transformations. The
scoped audit is complete; existing repaired datasets remain historical evidence.
See [docs/data_artifacts.md](docs/data_artifacts.md) for variant/provenance rules
and [docs/cleanup_provenance.md](docs/cleanup_provenance.md) for established facts
and remaining evidence limits. The new intermediates are not implemented yet.

The first spectral comparison is interpreted as 8 bands, RGB+NIR, and RGB from
the same acquisitions. Start with the working SegFormer recipe; a possible RGB
DINOv3 variant follows separately. New-region work compares direct transfer,
kelp-checkpoint fine tuning, generic-pretrained fine tuning, and combined
old/new training on fixed held-out test data.

W&B remains `kdorman90-ucla/kelpseg`; new work uses new experiment identities.
See [docs/product.md](docs/product.md) for the research contract and
[docs/experiments.md](docs/experiments.md) for run and checkpoint rules.
