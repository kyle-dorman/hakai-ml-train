# AGENTS.md

## Project

This repository is currently focused on binary kelp segmentation in 8-band
PlanetScope imagery. The active research question is geographic generalization:
compare a new temporally separated all-region baseline with leave-one-region-out
(LORO) models whose test set is one complete held-out region.

The repository still contains older model families and non-PS8B configs. They
are legacy surfaces, not the current project scope. Do not expand, document, or
clean them up unless a numbered task explicitly requires it.

## Entry Path

Read this file first. Then read `docs/index.md`, which routes the rest of the
documentation without duplicating it.

Before implementation, read:

1. `docs/todo.md` for current status and the next task.
2. The selected numbered file under `tasks/`.
3. Only the product, architecture, artifact, or experiment docs routed by
   `docs/index.md` for that task.

For documentation changes, also read `docs/documentation.md`. After context
compaction or in a new window, reread this file, `docs/index.md`,
`docs/todo.md`, and the active task file before editing.

## Current Status

Tasks 000–009 established the 369-TIFF temporal baseline assignment, validated
copied raw merge, restartable manifested chipper, canonical chip collection at
`/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1`, and the transactional
manifest-driven nodata filter, then selected and applied the universal 50%
nodata threshold. The active collection contains 4,637 chips from 367 source
TIFFs across all 12 regions. Its training-selection manifest retains all 3,210
positive chips and explicitly excludes 1,427 non-positive chips without
changing the canonical collection. Task 009 packaged and clean-extraction
verified the 44,917,177,439-byte v1 portable ZIP at
`/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip`.
A later audit found that five California TIFFs declare `65535` as nodata while
the current chip statistics count only all-band-zero pixels. The next task is
Task 009A, which repairs affected manifests and selections without a full
re-chip and produces a v2 archive. Task 010 transfers only that repaired
archive.
The complete ordered queue is in `docs/todo.md`; detailed contracts are in
`tasks/`.

Do not start multiple numbered tasks in one window. Close the selected task,
update its outcome and `docs/todo.md`, and stop.

## Scientific And Evaluation Boundaries

- Keep source-TIFF and region identity through every preprocessing stage.
- Never split chips from one source TIFF across baseline train, validation, and
  test sets.
- The baseline is temporal within every region; LORO test data is the complete
  held-out region.
- Do not tune preprocessing, models, or thresholds on held-out test results.
- Compare runs on matching original TIFFs by default. Retain chip-level metrics
  for traceability.
- For overlapping chips, reconstruct one prediction per covered source pixel
  before calculating TIFF confusion counts. Sum TIFF confusion counts for
  region/test-set metrics; do not sum overlapping chip counts or average chip
  IoUs.
- Report agreement with the supplied segmentation labels. Do not generalize the
  result beyond the represented imagery, labels, regions, and acquisition dates.

Read `docs/product.md` for the full current research contract.

## Data And Artifact Rules

Keep large imagery, chips, checkpoints, predictions, and generated reports out
of git. The local data root is `/Volumes/x10pro/kelpseg`; remote paths are
recorded per task. Portable manifests are the source of truth for dataset,
region, split, and source-TIFF membership.

Read `docs/data_artifacts.md` before adding, moving, filtering, archiving, or
interpreting data artifacts.

## Implementation Rules

- Use Python 3.12 and `uv`.
- Prefer small, restartable scripts or package modules over notebook-only state.
- Make long data operations support dry-run or report-only behavior when useful.
- Never mutate raw source imagery.
- Use deterministic manifests and explicit seeds.
- Refuse silent overwrites, missing image/label pairs, duplicate IDs, and partial
  manifest updates.
- Use maintained geospatial and ML libraries rather than hand-written raster,
  projection, or metric logic.
- Use `-100` as the label ignore index.
- Keep background-only chips in the canonical collection; training views may
  exclude them, but evaluation views should remain representative.
- Apply the selected nodata policy before dataset splitting so it is identical
  for train, validation, and test.
- Preserve user changes and unrelated work in a dirty worktree.

Read `docs/architecture.md` before changing pipeline boundaries, manifest
contracts, training orchestration, or evaluation aggregation.

## W&B

The current W&B destination is:

```text
entity: kdorman90-ucla
project: kelpseg
```

The experiment group for the new baseline/LORO suite has not been selected yet.
Do not copy W&B identity or grouping from legacy configs into new work. Read
`docs/experiments.md` before changing W&B configuration or run metadata.

## Setup And Validation

Install the locked Python 3.12 environment with:

```bash
uv python install 3.12
uv sync --python 3.12 --frozen
```

Use `uv run` for repo commands. Before completing code work, run the relevant
targeted smoke check and:

```bash
uv run ruff format --check .
uv run ruff check .
```

Run pre-commit when the task changes code broadly:

```bash
uv run pre-commit run --all-files
```

For docs-only work, inspect the rendered Markdown or diff and run:

```bash
git diff --check
```

There is not yet a repository test suite. Tasks that add data-contract or metric
logic should add focused tests rather than treating lint as behavioral proof.

## Task Contract

`tasks/README.md` owns task-file structure and handoff rules. A task outcome must
record changed repo files, durable external artifacts, validation, unresolved
issues, and the exact next action. Detailed run logs belong in the task file,
not in `AGENTS.md` or `docs/todo.md`.
