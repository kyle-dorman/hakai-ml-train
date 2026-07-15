# Task 008: Build the training-only background selector

Status: Pending

Depends on: Tasks 004 and 007

Execution: Local code task; no canonical deletion.

## Abstract

Replace destructive background-only deletion with a manifest-driven selector
that experiment materialization can apply to training rows only. Canonical,
validation, and test chips remain unchanged. The selector must make the chosen
background policy explicit and auditable rather than silently deleting files.

## Goal

Provide a deterministic command/library function that labels or selects
training-eligible chips from per-class manifest counts.

## Inputs

- Canonical chip-manifest schema from Task 003
- Canonical chip root from Task 004; post-nodata active manifest from Task 007
  will be the eventual production input
- `src/prepare/remove_bg_only_tiles.py`
- `docs/product.md`
- `docs/architecture.md`

## Background definition

A chip is background-only when every positive retained class count is zero.
Ignore pixels do not make a chip positive. An ignore-only chip is not useful
training background and must be separately classified as `ignore_only`, not
silently treated as ordinary background.

## Planned CLI

```bash
uv run python -m src.prepare.remove_bg_only_tiles \
  --manifest <active-chip-manifest.csv> \
  --output-manifest <training-selection.csv> \
  --policy <exclude_all|retain_fraction> \
  [--retain-fraction <0-to-1>] \
  [--seed <int>]
```

Despite the historical module name, the new default behavior must not unlink
NPZ files. If keeping that module name is misleading, add a clearer module and
leave a deprecation/error path in the old entry point.

Selection output columns:

```text
chip_id,source_tiff_id,region_id,class_presence,selected_for_training,
selection_reason,policy,retain_fraction,seed
```

For fractional retention, sample deterministically within region and preferably
source TIFF so one large background-heavy TIFF cannot dominate retained
background. The exact grouping must be recorded in the task plan.

## User decisions required

Before finalizing behavior, choose the production training policy:

1. `exclude_all`: remove every background-only chip from training views; or
2. `retain_fraction`: retain a deterministic fraction for negative examples.

Recommendation: first report counts by region/source and then ask. Do not assume
that the old destructive script's `exclude_all` behavior remains scientifically
appropriate. Record any fraction and seed if selected.

## Plan / spec requirement

Add a short plan covering positive/background/ignore-only classification,
selection grouping, deterministic sampling, backward CLI behavior, and how
Tasks 011–012 consume the output.

## Smoke test

Use a fixture manifest containing positive, background-only, mixed-ignore
background, and ignore-only chips across two regions/sources. Test both policies,
deterministic repeatability, and that no NPZ is modified.

## Validation

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run pytest tests/test_remove_bg_only_tiles.py
git diff --check
```

Run report-only selection on the real active manifest and summarize candidate
impact by region before obtaining the user decision.

## Acceptance criteria

- Canonical files and manifest are never deleted or rewritten by this selector.
- Production background policy is user-approved and recorded.
- Training-selection output is deterministic and joins one-to-one to chips.
- Validation/test materializers can bypass the selector.
- Ignore-only behavior is explicit and tested.

## Non-goals

- Do not materialize experiment folders.
- Do not apply nodata filtering.
- Do not balance positive classes or regions beyond the chosen background rule.
- Do not use test performance to choose the policy.

## Outcome template

Record final CLI, approved policy/fraction/seed, real-manifest counts, tests,
compatibility changes, and how Tasks 011–012 invoke selection.
