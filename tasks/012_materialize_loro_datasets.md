# Task 012: Materialize leave-one-region-out datasets

Status: Pending

Depends on: Tasks 010, 011

Execution: Remote code plus data-view task.

## Abstract

Use the Task 011 materializer to create one dataset view for each held-out
region. Every retained canonical chip from the target region belongs to test;
the target region contributes nothing to train or validation. The remaining
regions use a user-approved policy derived from the temporal baseline. This
task validates all 12 folds and does not launch training.

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

Confirm the non-held-out-region policy before materialization.

Recommendation:

- test: all canonical chips from the held-out region, regardless of their
  baseline temporal split;
- train: baseline-TRAIN chips from every other region, subject to approved
  background selection;
- validation: baseline-VAL chips from every other region, without background
  exclusion;
- non-held-out baseline-TEST chips: unused in that LORO fold.

This preserves temporal separation and makes paired baseline/LORO comparison
clean, but leaves some non-held-out data unused. Alternative policies that fold
non-held-out test TIFFs into training would need a new leakage/comparability
analysis.

Also confirm that `ca_005` and `ca_006` remain separate folds despite sharing
the descriptive name `channelIslands`. Recommendation: keep them separate by
region ID.

Confirm the view parent root. Recommendation:

```text
<remote-dataset-root>/views/loro_v1
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
`training_background_excluded`.

## Smoke test

Materialize `ca_001` only. Verify complete target-region test membership, no
target-region train/validation membership, correct other-region policy,
DataModule loading, hard-link identity, and rerun behavior.

## Validation

Run Task 011 tests plus LORO-specific cases. Production checks for every fold:

- held-out region has zero selected train/validation chips;
- every active canonical chip from held-out region is selected for test;
- every test chip belongs to held-out region;
- no selected chip appears in multiple splits within a fold;
- selected links equal selected manifest rows;
- background exclusions occur only in train;
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
