# Task 011: Materialize the temporal baseline dataset

Status: Pending

Depends on: Task 010

Execution: Remote code plus data-view task.

## Abstract

Build a reproducible hard-linked train/validation/test view for the new
all-region temporal baseline. Source-TIFF split membership comes only from
`planet8b_temporal_image_splits.csv`; chip membership comes from the canonical
chip manifest; the approved background selector applies to training only. The
task writes a complete fold manifest and QA report before any training starts.

## Goal

Implement or extend one general materializer and use it to produce a validated
baseline dataset view compatible with `src.data.DataModule`.

## Inputs

- Task 010 remote canonical dataset root
- Canonical active chip manifest
- Raster manifest
- `planet8b_temporal_image_splits.csv`
- Task 008 approved background policy and selector
- `src/data.py`
- `docs/architecture.md`
- `docs/product.md`

## User decisions required

Confirm the baseline view root. Recommendation:

```text
<remote-dataset-root>/views/baseline_temporal_v1
```

No split-policy decision is required: Task 000's CSV is authoritative. The
background policy must already be approved in Task 008; if not, stop.

## Planned materializer CLI

Prefer one script reusable by Task 012:

```bash
uv run python scripts/materialize_planet8b_folds.py baseline \
  --chip-root <canonical-chip-root> \
  --chip-manifest <chip_manifest.csv> \
  --temporal-splits <planet8b_temporal_image_splits.csv> \
  --background-selection <training-selection.csv> \
  --output-root <baseline-view-root> \
  --mode hardlink \
  --dry-run
```

Required non-dry rerun behavior: fail on an unexpected nonempty output; support
an explicit verified resume or `--replace` only if implemented transactionally.

## View layout

```text
<baseline-view-root>/
  train/*.npz
  val/*.npz
  test/*.npz
  fold_manifest.csv
  fold_summary.json
  materialization_command.txt
```

`fold_manifest.csv` includes every canonical chip, even excluded chips:

```text
chip_id,chip_path,source_tiff_id,dataset,region_id,acquisition_date,
source_temporal_split,experiment_split,selected,selection_reason,view_path
```

`experiment_split` is blank for excluded rows. `selection_reason` distinguishes
selected, background-policy exclusion, and any invalid/unexpected state.

## Split contract

- Join each chip to exactly one temporal split by `source_tiff_id`.
- `TRAIN` source TIFFs map to `train`, subject to training background selection.
- `VAL` source TIFFs map to `val` with no background-only exclusion.
- `TEST` source TIFFs map to `test` with no background-only exclusion.
- Nodata filtering has already happened canonically and is not repeated.
- One source TIFF can occur in only one experiment split.

## Plan / spec requirement

Before coding, add a plan covering joins and cardinality checks, hard-link
materialization, excluded-row representation, atomic view publication, and how
the same implementation will support LORO mode without duplicating logic.

## Smoke test

Use a small manifest subset containing three regions, all temporal splits,
positive/background training chips, and background validation/test chips.
Prove exact selection, links, excluded rows, and rerun failure.

## Validation

```bash
uv run ruff format --check scripts tests
uv run ruff check scripts tests
uv run pytest tests/test_materialize_planet8b_folds.py
git diff --check
```

Production QA:

- every canonical chip appears once in `fold_manifest.csv`;
- every selected row has exactly one hard link and every link has one row;
- no source TIFF crosses experiment splits;
- all 12 regions contribute selected chips to train, validation, and test, or a
  user-reviewed documented exception exists;
- train/validation/test source-TIFF counts reproduce Task 000 after accounting
  only for training background exclusions at chip level;
- per-region date ordering matches the temporal split CSV;
- inode/link checks confirm hard links rather than copies where supported.

## Acceptance criteria

- Baseline view, manifest, and summary are complete and validated.
- DataModule can load one batch from every split.
- Background-only evaluation chips remain present.
- No training run has started.
- Remote view path/counts are recorded in task outcome and `docs/todo.md`.

## Non-goals

- Do not create LORO folds.
- Do not modify the temporal split CSV.
- Do not tune background or nodata policy.
- Do not edit model hyperparameters or launch training.

## Review pass

- ML researcher: verify temporal/source grouping and training-only exclusion.
- Risk-averse engineer: verify join cardinality and atomic hard-link view.

## Outcome template

Record approved root, implementation files, exact command, split/source/chip
counts, exclusion counts, DataModule smoke, validation, and Task 012 inputs.
