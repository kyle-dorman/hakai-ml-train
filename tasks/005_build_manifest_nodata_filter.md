# Task 005: Build the manifest-driven nodata filter

Status: Complete

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

## Implementation plan

1. Parse and validate the active manifest before selection, including required
   provenance fields, unique chip IDs and paths, count/percentage consistency,
   threshold units, and active file existence.
2. Build one deterministic report from manifest rows. Dry-run writes that
   report atomically and performs no chip or active-manifest mutation.
3. In apply mode, write the proposed report first, move rejected chips into a
   same-filesystem quarantine, atomically replace the active manifest, and
   atomically write a versioned removal manifest plus filter metadata.
4. Validate post-apply manifest/file counts before deleting quarantine. On any
   pre-commit failure, move quarantined chips back; after the active-manifest
   commit, retain enough transaction state for an idempotent rerun to finish
   or safely refuse rather than creating silent partial state.
5. Cover threshold boundaries, invalid manifests, missing files, dry-run
   immutability, successful application, rollback, and idempotence with a
   fixture, then run two report-only examples against the canonical manifest.

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

## Outcome

`src/prepare/remove_tiles_with_nodata_areas.py` is now a manifest-driven CLI
whose threshold and mode are both explicit. It requires `--manifest`,
`--max-nodata-pct`, `--report-output`, and exactly one of `--dry-run` or
`--apply`. Threshold units are percent in `[0, 100]`; rows at the threshold are
kept and only rows above it are selected for removal. Before reporting, the
tool validates required provenance columns, case-insensitive chip ID/path
uniqueness, portable paths, active file existence, finite counts, and exact
count/percentage consistency. Reports use the specified 11-column schema and
retain source-TIFF, dataset, and region identity.

Dry-run writes only the requested atomic report. Apply first writes the same
report, preserves the original active manifest as
`filter_history/nodata_<threshold>/pre_filter_manifest.csv`, stages the retained
and removal manifests, and moves rejected NPZs into a same-root transaction
quarantine. It atomically replaces the active manifest, reconciles the
snapshot against retained plus removed rows, verifies retained and quarantined
files, publishes `removal_manifest.csv`, deletes quarantine only after those
checks, and writes `filter_metadata.json` last as the completion marker. The
metadata records hashes, command/commit provenance, global counts, and
dataset/region counts. Pre-commit failures restore quarantined files; a
post-commit interruption is recovered from the pre/post manifest hashes on the
next identical apply. A completed repeat apply validates the evidence and
returns `already_applied` without deleting again. Existing different reports
or history artifacts are not silently overwritten.

The compatibility change is intentional: the old recursive three-channel
`-n/--num_channels` CLI that immediately deleted any chip containing one black
pixel no longer exists. Normal selection reads the canonical manifest and does
not reopen NPZ payloads.

Changed repository files:

- `src/prepare/remove_tiles_with_nodata_areas.py`: threshold validation,
  manifest/report contracts, transactional apply, rollback/recovery, filter
  metadata, and the new CLI.
- `tests/test_remove_tiles_with_nodata_areas.py`: 0%, below/exactly/above
  threshold fixture plus missing-file, duplicate-ID/path, inconsistent-percent,
  dry-run immutability, apply, rollback, post-commit recovery, and idempotence
  coverage, including an apply with no rejected rows.
- `AGENTS.md`, `README.md`, `docs/index.md`, `docs/architecture.md`,
  `docs/data_artifacts.md`, `docs/todo.md`, `tasks/README.md`, and this task:
  current filter and Task 006 handoff routing.

Real-manifest dry-runs created two durable report-only artifacts under
`/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1/filter_reports/task005`:

```text
threshold 0%:  6,003 total; 1,600 kept; 4,403 removed
  nodata_threshold_0_report.csv
  SHA-256 5eddeefe64850962627fcba8478ea98b218a10c2fcde32c5cb3f3d370db31bcc
threshold 50%: 6,003 total; 4,637 kept; 1,366 removed
  nodata_threshold_50_report.csv
  SHA-256 58479d634243e73127bb8124d3fa46269e2dd47b74cc8e6ea904f7b1a9d68fb4
```

Before and after both runs, `chip_manifest.csv` retained SHA-256
`7fd2316ae07c4c5277ff33a62ae4c1ee60ced14a528e6a153a6489a7e457d9c8`,
the active directory contained all 6,003 NPZs, and neither `filter_history` nor
`.nodata_filter_transactions` existed. No threshold was selected or applied,
no background chip was filtered, and canonical class statistics were not
modified.

Validation completed:

```text
uv run ruff format --check src tests                         # passed
uv run ruff check src tests                                # passed
uv run pytest tests/test_remove_tiles_with_nodata_areas.py # 13 passed
uv run pytest                                              # 32 passed
git diff --check                                           # passed
real CLI dry-runs at 0% and 50%                            # passed
```

Repository-wide Ruff still reports only the pre-existing formatting drift and
two unused loop variables in legacy SKEMA notebooks, outside the active PS8B
scope. The production threshold remains intentionally unresolved for Task 006.

The exact first Task 006 report command is:

```bash
root=/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
analysis=/Volumes/x10pro/kelpseg/nodata_threshold_analysis_v1
for threshold in 0 1 5 10 20 30 40 50; do
  uv run python -m src.prepare.remove_tiles_with_nodata_areas \
    "$root" \
    --manifest "$root/chip_manifest.csv" \
    --max-nodata-pct "$threshold" \
    --report-output "$analysis/filter_report_${threshold}.csv" \
    --dry-run
done
```

The exact next action is to open Task 006, generate the full global/region
distribution and candidate summaries plus representative contact sheet, then
ask the user to select one universal threshold without applying it.
