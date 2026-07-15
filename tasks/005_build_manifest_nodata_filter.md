# Task 005: Build the manifest-driven nodata filter

Status: Pending

Depends on: Task 004

Execution: Local code task.

## Abstract

Replace the current rule that deletes any chip containing any all-zero pixel
with a manifest-driven, configurable percentage threshold. The tool must support
analysis without mutation and transactional application with a preserved
removal manifest. This task implements the tool; Task 006 chooses a threshold
and Task 007 applies it.

## Goal

Make nodata selection explicit, testable, idempotent, and independent of
train/validation/test membership.

## Inputs

- Task 004 canonical chip root and `chip_manifest.csv`
- `src/prepare/remove_tiles_with_nodata_areas.py`
- `docs/data_artifacts.md`
- Task 003 nodata definition and units

## Planned CLI

```bash
uv run python -m src.prepare.remove_tiles_with_nodata_areas \
  <chip-root> \
  --manifest <chip-root>/chip_manifest.csv \
  --max-nodata-pct <0-to-100> \
  --report-output <path> \
  --dry-run
```

Application requires an explicit mutation flag:

```bash
... --apply
```

Do not make deletion the default.

## Selection contract

- Keep chips where `nodata_pct <= max_nodata_pct`.
- Remove chips where `nodata_pct > max_nodata_pct`.
- Threshold units are percent `[0, 100]`, not fraction `[0, 1]`.
- Validate `nodata_pixel_count`, `total_pixel_count`, and `nodata_pct`
  consistency before selection.
- Normal selection reads the manifest only; an optional audit mode may reopen a
  sample of NPZs.

## Output and mutation contract

Dry-run writes a report with:

```text
chip_id,chip_path,source_tiff_id,dataset,region_id,nodata_pixel_count,
total_pixel_count,nodata_pct,threshold_pct,action,reason
```

Apply mode:

1. validates every selected path and writes the complete proposed report;
2. moves rejected chips into a temporary quarantine under the same filesystem;
3. writes a new active manifest excluding rejected rows through atomic rename;
4. writes a versioned removal manifest and filter metadata JSON;
5. deletes quarantine only after manifest and counts validate.

If full transactional movement is impractical, use an equally safe staged
design and document it before coding. Never leave the manifest claiming a chip
that was deleted or omit a chip that still belongs to the active collection.

## User decisions required

None. The threshold is intentionally required at runtime and will be selected
in Task 006. Do not add a hidden default threshold.

## Plan / spec requirement

Add a short implementation plan describing dry-run/apply separation, atomic
manifest replacement, quarantine/rollback, and idempotent reruns.

## Smoke test

Use a fixture manifest and NPZ directory containing chips at `0`, just below a
threshold, exactly at it, and just above it. Test missing files, duplicate IDs,
inconsistent percentages, dry-run immutability, apply success, and interrupted
apply rollback or safe failure.

## Validation

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run pytest tests/test_remove_tiles_with_nodata_areas.py
git diff --check
```

Run dry-run against the real canonical manifest at two example thresholds, but
do not use `--apply`.

## Acceptance criteria

- Any-nodata deletion is no longer the active CLI behavior.
- Threshold semantics and units are unambiguous.
- Dry-run never mutates data or active manifest.
- Apply behavior is transactional/idempotent and tested.
- Reports retain region and source-TIFF provenance.
- Task 006 can analyze thresholds without changing code.

## Non-goals

- Do not select or apply the production threshold.
- Do not filter background-only chips.
- Do not modify canonical class statistics.
- Do not create experimental splits.

## Outcome template

Record CLI/schema, mutation strategy, compatibility change, tests, real-manifest
dry-run evidence, and the exact Task 006 command.
