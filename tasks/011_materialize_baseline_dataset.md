# Task 011: Materialize the temporal baseline dataset

Status: Complete

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
- `VAL` source TIFFs map to the non-overlapping `val` subset with no
  background-only exclusion.
- `TEST` source TIFFs map to the non-overlapping `test` subset with no
  background-only exclusion.
- Nodata filtering has already happened canonically and is not repeated.
- One source TIFF can occur in only one experiment split.

## Plan / spec requirement

Before coding, add a plan covering joins and cardinality checks, hard-link
materialization, excluded-row representation, atomic view publication, and how
the same implementation will support LORO mode without duplicating logic.

## Implementation plan

1. Load the canonical chip, temporal split, and training-selection manifests
   with explicit required-column checks. Reject duplicate chip/source keys,
   missing or extra training-selection rows, conflicting source metadata, and
   temporal rows whose source IDs, dataset, region, or acquisition date do not
   agree with the canonical manifests. Require every canonical source to join
   exactly once to `TRAIN`, `VAL`, or `TEST` and reject source-TIFF split
   crossings.
2. Build one fold row per canonical chip. Map temporal `TRAIN` to `train` only
   when the approved selector marks the chip eligible, retaining all spatial
   overlaps; map temporal `VAL` and `TEST` to `val` and `test` only for the
   non-overlapping grid (`row_off` and `col_off` divisible by 1024), without
   applying the background selector. Keep excluded rows with a blank experiment
   split and view path, distinguishing background-policy, validation-overlap,
   and test-overlap exclusions in `selection_reason`.
3. Resolve canonical chip paths beneath the explicit dataset root, reject
   missing files and path escapes, and create hard links in a sibling staging
   directory. Verify each selected row/link bijection and source/destination
   inode equality before writing deterministic manifest, summary, and command
   evidence into the staged view.
4. Publish only by atomically renaming the complete sibling staging directory
   to the requested output. Dry-run performs every manifest and source-file
   check without filesystem mutation. A normal rerun rejects any existing
   output; no resume or replacement mode is introduced in this task.
5. Keep split assignment separate from validation and publication: the common
   loader, selector join, fold-row validation, hard-link writer, and summary
   code accept a mode-specific assignment function. Task 012 can add LORO
   assignments by region without duplicating those contracts or changing the
   baseline CLI.

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
- Background-only chips on the non-overlapping evaluation grid remain present.
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

## Outcome

Completed 2026-07-21 on the Task 010 host. The approved and atomically
published view root is:

```text
/home/sky/data/planet8b_all_regions_1024_512_v2/views/baseline_temporal_v1
```

The user confirmed the final grid policy during implementation: training uses
all eligible overlapping chips and applies the approved `exclude_all`
background policy; validation and test use only rows whose `row_off` and
`col_off` are divisible by 1024, and do not apply background exclusion.

Changed repository files are `scripts/materialize_planet8b_folds.py`, its
focused `tests/test_materialize_planet8b_folds.py`, `docs/architecture.md`,
this task file, `docs/index.md`, and `docs/todo.md`. The materializer validates
required columns, uniqueness, one-to-one selection, source metadata, splits,
and temporal date order; writes deterministic full fold rows; verifies hard
links and inodes; supports dry-run; and atomically publishes from a sibling
stage while refusing an existing output.

The production dry-run and apply used the planned CLI with these resolved
arguments (the dry-run added `--dry-run`):

```bash
uv run python scripts/materialize_planet8b_folds.py baseline \
  --chip-root /home/sky/data/planet8b_all_regions_1024_512_v2 \
  --chip-manifest /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/chip_manifest.csv \
  --temporal-splits /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/planet8b_temporal_image_splits.csv \
  --background-selection /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/training_selection.csv \
  --output-root /home/sky/data/planet8b_all_regions_1024_512_v2/views/baseline_temporal_v1 \
  --mode hardlink
```

The fold manifest contains every canonical chip exactly once: 4,602 rows from
367 source TIFFs. It selects and hard-links 2,565 chips: 2,103 train chips from
240 source TIFFs, 277 validation chips from 67 source TIFFs, and 185 test chips
from 53 source TIFFs. All 12 regions contribute selected chips to every split.
The canonical pre-view chip/source counts are 2,998/245 TRAIN, 941/68 VAL, and
663/54 TEST. The original temporal manifest has 247/68/54 source TIFFs; its two
additional TRAIN sources are the documented post-nodata sources with no
canonical chips (`006_20210805_184050_240c` and BC `...clip5`).

The 2,037 explicit exclusions comprise 895 training background-policy rows,
664 validation overlap rows, and 478 test overlap rows. Five canonical TRAIN
sources have only background-excluded chips. One VAL source
(`010_20210826_180847_2460`) and one TEST source
(`006_20220813_181819_2474`) have retained canonical chips but no
non-overlapping-grid chip; these are reviewed consequences of the confirmed
grid policy, not join failures. The selected evaluation subset retains 74
background-policy-ineligible validation chips and 50 such test chips.

Validation passed:

- `uv run ruff format --check scripts tests`
- `uv run ruff check scripts tests`
- `uv run pytest tests/test_materialize_planet8b_folds.py` (1 passed)
- production dry-run, all-row uniqueness, selected-row/link bijection, and
  inode equality for all 2,565 hard links
- source-TIFF split isolation, all-region participation, temporal date order,
  and explicit existing-output rerun failure
- `DataModule` batch size 1 from train, validation, and test; each image batch
  was `[1, 1024, 1024, 8]` and each label batch `[1, 1024, 1024]`
- `git diff --check`

No training run was started. Task 012 should reuse this script's loaders,
selection join, fold validation, hard-link writer, and atomic publisher while
adding only the LORO assignment policy. It must carry forward the confirmed
non-overlapping validation/test grid policy and use this baseline fold manifest
as the temporal source assignment input.
