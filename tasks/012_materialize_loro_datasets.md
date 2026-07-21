# Task 012: Materialize leave-one-region-out datasets

Status: Complete

Depends on: Tasks 010, 011

Execution: Remote code plus data-view task.

## Abstract

Use the Task 011 materializer to create one dataset view for each held-out
region. Every retained canonical chip on the approved non-overlapping
evaluation grid from the target region belongs to test; the target region
contributes nothing to train or validation. The remaining regions use a
user-approved policy derived from the temporal baseline. This task validates
all 12 folds and does not launch training.

## Goal

Produce reproducible, hard-linked LORO train/validation/test views and complete
fold manifests for `ca_001`–`ca_011` and `bc`.

## Inputs

- Task 010 canonical remote chips and manifests
- Task 011 materializer and tests
- `planet8b_temporal_image_splits.csv`
- Task 008 approved background-selection output
- `docs/product.md`
- `docs/architecture.md`

## User decisions required

Confirmed 2026-07-21: carry forward the Task 011 grid policy. Training retains
eligible overlapping chips. Validation and test use only canonical chips whose
`row_off` and `col_off` are both divisible by 1024. Evaluation background chips
remain included; overlap exclusions remain explicit in each fold manifest.

Confirm the non-held-out-region policy before materialization.

Approved 2026-07-21 for implementation: use the recommended policy below so
non-held-out baseline-TEST chips remain unused in each LORO fold.

Recommendation:

- test: all non-overlapping-grid canonical chips from the held-out region,
  regardless of their baseline temporal split and without background
  exclusion;
- train: baseline-TRAIN chips from every other region, subject to approved
  background selection;
- validation: non-overlapping-grid baseline-VAL chips from every other region,
  without background exclusion;
- non-held-out baseline-TEST chips: unused in that LORO fold.

This preserves temporal separation and makes paired baseline/LORO comparison
clean, but leaves some non-held-out data unused. Alternative policies that fold
non-held-out test TIFFs into training would need a new leakage/comparability
analysis.

Confirmed 2026-07-21: `ca_005` and `ca_006` remain separate folds keyed by
their canonical region IDs despite sharing the descriptive name
`channelIslands`. Descriptive names must not be used as fold keys.

Confirm the view parent root. Recommendation:

```text
<remote-dataset-root>/views/loro_v1
```

Approved 2026-07-21 for implementation at:

```text
/home/sky/data/planet8b_all_regions_1024_512_v2/views/loro_v1
```

Record all three decisions here before the dry-run.

## Planned CLI

```bash
uv run python scripts/materialize_planet8b_folds.py loro \
  --chip-root <canonical-chip-root> \
  --chip-manifest <chip_manifest.csv> \
  --temporal-splits <planet8b_temporal_image_splits.csv> \
  --background-selection <training-selection.csv> \
  --output-root <loro-view-parent> \
  --held-out-region all \
  --mode hardlink \
  --dry-run
```

Support one `--held-out-region <region_id>` for smoke/recovery and `all` for the
full suite.

## Fold layout

```text
<loro-view-parent>/<region_id>/
  train/*.npz
  val/*.npz
  test/*.npz
  fold_manifest.csv
  fold_summary.json
```

Manifest schema extends Task 011 with:

```text
fold_id,held_out_region
```

Every canonical chip appears once per fold manifest, selected or excluded, with
an explicit reason such as `held_out_region_test`, `nonheldout_temporal_train`,
`nonheldout_temporal_val`, `nonheldout_temporal_test_unused`, or
`training_background_excluded`. Held-out and validation-grid overlap exclusions
must also have explicit reasons.

## Smoke test

Materialize `ca_001` only. Verify complete target-region non-overlapping-grid
test membership, explicit target-region overlap exclusions, no target-region
train/validation membership, correct other-region policy, DataModule loading,
hard-link identity, and rerun behavior.

## Validation

Run Task 011 tests plus LORO-specific cases. Production checks for every fold:

- held-out region has zero selected train/validation chips;
- every active non-overlapping-grid canonical chip from the held-out region is
  selected for test;
- no overlapping-grid chip from the held-out region is selected for test;
- every test chip belongs to held-out region;
- no selected chip appears in multiple splits within a fold;
- selected links equal selected manifest rows;
- background exclusions occur only in train;
- every selected validation chip is on the non-overlapping grid and background
  selection does not exclude validation rows;
- unused non-held-out temporal-test rows are explicit;
- DataModule loads one batch from each split;
- fold counts and bytes are summarized by region/source/date/class presence.

Run focused Ruff/pytest and `git diff --check` for code/doc changes.

## Acceptance criteria

- Twelve validated LORO folds exist.
- The user-approved policy is recorded in `docs/architecture.md` and task
  outcome.
- Fold manifests are sufficient for W&B artifact logging and training runner
  setup.
- No training run has started.

## Non-goals

- Do not combine region IDs based only on names.
- Do not use LORO test data for validation or preprocessing choices.
- Do not change model or training configuration.
- Do not launch training.

## Review pass

- ML researcher: evaluate leakage, comparability, and unused-data policy.
- Remote-sensing researcher: verify region/source support and full-region test
  interpretation.

## Outcome template

Record approved policy/roots, dry-run and smoke evidence, all fold counts,
materialization command, DataModule checks, validation, and Task 013 inputs.

## Outcome

Completed 2026-07-21 on the Task 010 host. The atomically published parent is:

```text
/home/sky/data/planet8b_all_regions_1024_512_v2/views/loro_v1
```

The approved policy uses each canonical region ID as one fold, including
separate `ca_005` and `ca_006` folds. Test contains all retained held-out-region
chips on the non-overlapping 1024 grid regardless of temporal split and without
background exclusion. Train contains eligible baseline-TRAIN chips from all
other regions, validation contains their non-overlapping baseline-VAL chips,
and non-held-out baseline-TEST chips remain unused. Every fold manifest records
all 4,602 canonical chips, including explicit overlap, background, and unused
temporal-test exclusions.

Changed repository files are `scripts/materialize_planet8b_folds.py`,
`tests/test_materialize_planet8b_folds.py`, `AGENTS.md`, `docs/index.md`,
`docs/product.md`, `docs/architecture.md`, `docs/todo.md`, this task file, and
`tasks/README.md`. The shared materializer now supports one held-out region or
`all`, preserves the baseline CLI, validates LORO membership and grid rules,
writes fold identity fields and grouped count/byte inventories, refuses reruns,
and atomically publishes the complete fold parent.

The production dry-run and apply used the planned CLI with these resolved
arguments (the dry-run added `--dry-run`):

```bash
uv run python scripts/materialize_planet8b_folds.py loro \
  --chip-root /home/sky/data/planet8b_all_regions_1024_512_v2 \
  --chip-manifest /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/chip_manifest.csv \
  --temporal-splits /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/planet8b_temporal_image_splits.csv \
  --background-selection /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/training_selection.csv \
  --output-root /home/sky/data/planet8b_all_regions_1024_512_v2/views/loro_v1 \
  --held-out-region all \
  --mode hardlink
```

Selected chip/source counts and explicit exclusion counts are:

| Fold | Train | Val | Test | Held-out overlap | Other TEST unused | Other VAL overlap | Train background |
|---|---:|---:|---:|---:|---:|---:|---:|
| `bc` | 2,048/233 | 184/50 | 152/29 | 277 | 626 | 491 | 824 |
| `ca_001` | 2,010/224 | 271/64 | 41/21 | 88 | 645 | 652 | 895 |
| `ca_002` | 1,623/199 | 243/58 | 228/59 | 465 | 555 | 593 | 895 |
| `ca_003` | 1,998/228 | 262/64 | 82/17 | 295 | 621 | 611 | 733 |
| `ca_004` | 1,575/220 | 209/62 | 402/29 | 1,106 | 445 | 477 | 388 |
| `ca_005` | 2,016/225 | 271/64 | 40/21 | 83 | 645 | 652 | 895 |
| `ca_006` | 1,898/218 | 261/63 | 110/33 | 305 | 588 | 623 | 817 |
| `ca_007` | 2,081/218 | 272/62 | 32/32 | 0 | 658 | 664 | 895 |
| `ca_008` | 1,796/194 | 257/57 | 143/65 | 337 | 581 | 595 | 893 |
| `ca_009` | 1,981/230 | 269/65 | 54/14 | 188 | 630 | 636 | 844 |
| `ca_010` | 2,011/218 | 273/63 | 32/32 | 130 | 638 | 646 | 872 |
| `ca_011` | 2,096/233 | 275/65 | 12/12 | 0 | 661 | 664 | 894 |

Each selected cell is `chips/source TIFFs`. The parent contains 27,508 verified
hard links representing 278,061,059,521 logical NPZ bytes without duplicating
canonical file content. Each `fold_summary.json` additionally gives exact
selected counts and bytes by split, region, source TIFF, acquisition date, and
class presence.

The `ca_001` smoke created 2,322 links, loaded one train/validation/test
DataModule batch with image shape `[1, 1024, 1024, 8]`, verified all inodes, and
proved rerun refusal; its temporary hard-link view was then removed. The full
production audit independently rejoined all manifests, checked every assignment
and all 27,508 source/destination inodes, reconciled every selected link and
summary, rejected source-TIFF split crossings, loaded all 36 fold/split batches,
proved full-parent rerun refusal, and found no abandoned staging directory.

Three held-out source TIFFs have retained canonical chips but no retained chip
on the approved non-overlapping grid: `001_20210408_182017_2401`,
`006_20220813_181819_2474`, and `010_20210826_180847_2460`. Their rows remain
explicit held-out overlap exclusions. This is a reviewed evaluation-coverage
consequence, not missing fold membership; downstream reports must retain the
existing coverage qualification.

Validation passed:

- `uv run ruff format --check scripts tests`
- `uv run ruff check scripts tests`
- `uv run pytest tests/test_materialize_planet8b_folds.py` (2 passed)
- production dry-run, single-fold smoke, full apply, independent all-fold QA,
  DataModule checks, rerun refusal, and staging cleanup checks
- `git diff --check`

The required repository-wide checks were also attempted. They remain blocked
only by two pre-existing legacy-notebook findings outside this task:
`ruff format --check .` would reformat `notebooks/create_skema_aux_files.ipynb`
and `notebooks/export_skema_models_onnx.ipynb`, while `ruff check .` reports two
unused loop indices in `create_skema_aux_files.ipynb`. Those legacy notebooks
were not changed.

No training run was started. Task 013 should consume the baseline and these 12
fold manifests/summaries as the dataset identity and W&B artifact inputs.
