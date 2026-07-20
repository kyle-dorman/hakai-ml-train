# Task 008: Build the training-only background selector

Status: Complete

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

Classify chips from the manifest's explicit pixel counts rather than reopening
NPZ files or treating every non-positive value as one undifferentiated bucket:

- `positive`: `class_1_pixel_count > 0`;
- `clean_background_only`: `class_1_pixel_count == 0`,
  `class_0_pixel_count > 0`, and `nodata_pixel_count == 0`;
- `mixed_background_nodata`: `class_1_pixel_count == 0`,
  `class_0_pixel_count > 0`, and `nodata_pixel_count > 0`;
- `ignore_only`: both retained class counts are zero.

Water, land, and waves are valid class-0 background under Task 004's approved
remap. Nodata remains separately visible through `nodata_pixel_count` and the
`-100` ignore count. Ignore pixels do not make a chip positive.

## CLI

```bash
uv run python -m src.prepare.remove_bg_only_tiles \
  --manifest <active-chip-manifest.csv> \
  --output-manifest <training-selection.csv> \
  --summary-output <training-selection-summary.csv> \
  --policy <exclude_all|retain_fraction> \
  [--retain-fraction <0-to-1>] \
  [--seed <int>] [--overwrite]
```

Use `--report-only` with `--summary-output` and without `--output-manifest` to
write the full audit before creating the selection manifest.

Despite the historical module name, the new default behavior must not unlink
NPZ files. If keeping that module name is misleading, add a clearer module and
leave a deprecation/error path in the old entry point.

Selection output columns:

```text
chip_id,source_tiff_id,region_id,class_0_pixel_count,class_1_pixel_count,
ignore_pixel_count,nodata_pixel_count,class_presence,selected_for_training,
selection_reason,policy,retain_fraction,seed
```

For fractional retention, sample deterministically within region and preferably
source TIFF so one large background-heavy TIFF cannot dominate retained
background. The exact grouping must be recorded in the task plan.

## User decisions required

Decision (2026-07-15): use `exclude_all` for production training views. Exclude
all `clean_background_only`, `mixed_background_nodata`, and `ignore_only`
chips; retain positive chips that passed the universal nodata filter. Before
materializing that selection, report chip and pixel counts for every class
presence category globally, by region, and by source TIFF so the effect is
auditable. Canonical, validation, and test collections remain unchanged.

The implementation may retain a tested `retain_fraction` mode for future
experiments, but it is not the selected production policy.

## Plan

1. Validate unique chip identity and explicit nonnegative class, ignore, and
   nodata counts; derive the four class-presence values exactly as defined
   above without opening NPZs.
2. Always retain positive chips. `exclude_all` excludes every other presence
   class. The future `retain_fraction` mode groups non-positive chips by
   `(region_id, source_tiff_id, class_presence)`, ranks each group by a seeded
   SHA-256 of its stable identity, and retains
   `floor(group_size * retain_fraction)` rows.
3. Write one deterministic selection row per input chip and a summary with all
   four categories at global, region, and source-TIFF scopes, including zeros.
   Writes are atomic, identical reruns are idempotent, and differing outputs
   require explicit `--overwrite`.
4. Keep the historical module path for compatibility, but make both the old
   positional CLI and `remove_bg_only_tiles(input_dir)` fail before inspecting
   or deleting any NPZ.
5. Tasks 011–012 join the selection one-to-one on `chip_id` and apply
   `selected_for_training = true` only to train rows. Validation and test rows
   bypass the selector.

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

Run report-only selection on the real active manifest and summarize the
approved `exclude_all` policy's impact globally, by region, and by source TIFF
before materializing any training view.

## Acceptance criteria

- Canonical files and manifest are never deleted or rewritten by this selector.
- The approved `exclude_all` policy is reported from explicit foreground,
  background, ignore, and nodata counts before training-view materialization.
- Training-selection output is deterministic and joins one-to-one to chips.
- Validation/test materializers can bypass the selector.
- Ignore-only behavior is explicit and tested.

## Non-goals

- Do not materialize experiment folders.
- Do not apply nodata filtering.
- Do not balance positive classes or regions beyond the chosen background rule.
- Do not use test performance to choose the policy.

## Outcome

The approved production policy is `exclude_all`; retain fraction and seed are
not applicable. `src/prepare/remove_bg_only_tiles.py` now validates and
classifies the canonical manifest, supports the tested future
`retain_fraction` policy, writes atomic selection and summary CSVs, and cannot
delete NPZ files. The old positional CLI and destructive Python function fail
with migration guidance before touching the input directory.

The real report-only run preceded selection materialization. Global counts are:

| Class presence | Chips | Selected | Total pixels | Class 0 | Class 1 | Ignore | Nodata |
|---|---:|---:|---:|---:|---:|---:|---:|
| `positive` | 3,210 | 3,210 | 3,350,032,072 | 2,890,965,851 | 107,131,696 | 351,934,525 | 341,894,468 |
| `clean_background_only` | 521 | 0 | 546,308,096 | 508,126,951 | 0 | 38,181,145 | 0 |
| `mixed_background_nodata` | 892 | 0 | 934,860,120 | 729,282,738 | 0 | 205,577,382 | 194,606,340 |
| `ignore_only` | 14 | 0 | 14,680,064 | 0 | 0 | 14,680,064 | 2,647,571 |

Durable external artifacts are:

```text
/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1/
  background_selection/exclude_all/training_selection.csv
    SHA-256 6a62fd9031f8d238e2a9fd9448519f765da9b958ea5022df35796de7a3da9a1b
  background_selection/exclude_all/selection_summary.csv
    SHA-256 21a3ecae1a5ec4f462b947b289dfc129f5749a0f36d1edff9740f7190a7c72d7
```

`training_selection.csv` has 4,637 unique rows in canonical manifest order.
`selection_summary.csv` has 1,520 rows: four global rows, 48 region rows, and
1,468 source-TIFF rows. Every chip and pixel total reconciles as selected plus
excluded. The canonical manifest retains SHA-256
`edf754888dea183f12873594b546b980f350b5b4e293ff62ca7eca64a2c39a39`;
the 4,637-file NPZ size/path/mtime inventory hash was unchanged before and after
both commands at
`74e3f420d9d897ed5176429cca19bc73b274df69dda24416362d0ad38d1dc261`.

Changed repository files are `src/prepare/remove_bg_only_tiles.py`,
`tests/test_remove_bg_only_tiles.py`, and the synchronized status,
architecture, artifact, routing, and task documentation. Focused tests cover
both policies, deterministic grouping, all four presence categories across two
regions/sources, report-only behavior, invalid manifests, the safe legacy
failure path, and no NPZ mutation. Final validation passed:
`uv run ruff format --check src tests` (28 files),
`uv run ruff check src tests`,
`uv run pytest tests/test_remove_bg_only_tiles.py` (8 tests), and
`git diff --check`. The full suite also passed with 42 tests. There are no
unresolved Task 008 issues.

The exact next action is Task 009: package the post-nodata canonical collection,
the active manifest, the Task 008 selection and summary, split metadata, and
required compact provenance into the portable archive. Stop before Task 009.
