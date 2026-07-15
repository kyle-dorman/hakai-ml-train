# Task 007: Apply the universal nodata filter

Status: Complete

Depends on: Task 006

Execution: Local data-mutation task.

## Abstract

Apply the user-approved universal nodata threshold to the canonical chips,
preserve complete removal evidence, and revalidate the active manifest. This is
the only destructive canonical-chip step in the plan and must use Task 005's
transactional path exactly once.

## Goal

Produce a clean canonical chip collection whose active manifest contains only
chips at or below the approved nodata threshold.

## Inputs

- Task 006 approved threshold and analysis artifacts
- Task 005 filter CLI
- Task 004 canonical chip root and manifest
- `docs/data_artifacts.md`

## Approved Task 006 input

The user-approved universal threshold is `max_nodata_pct = 50`. Task 006's
validated projection is 6,003 total chips, 4,637 retained, and 1,366 removed.
No region is eliminated; two source TIFFs lose all chips.

The exact production dry-run command is:

```bash
root=/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
uv run python -m src.prepare.remove_tiles_with_nodata_areas \
  "$root" \
  --manifest "$root/chip_manifest.csv" \
  --max-nodata-pct 50 \
  --report-output "$root/filter_reports/task007_nodata_50_dry_run.csv" \
  --dry-run
```

Stop unless this reports exactly 4,637 kept and 1,366 removed. Do not infer a
different threshold from later inspection.

## User decisions required

None if Task 006 contains an explicit approved numeric threshold. If it does
not, stop; do not infer one from the recommendation.

## Execution plan

1. Verify backup/rollback strategy and free space for quarantine.
2. Run dry-run with the approved threshold.
3. Compare counts exactly to Task 006's approved candidate row.
4. Stop on any discrepancy.
5. Run apply mode once.
6. Validate active manifest, removal manifest, filesystem, and metadata.
7. Produce post-filter summaries by region, source TIFF, and class presence.

## Required outputs

```text
<chip-root>/chip_manifest.csv
<chip-root>/filter_history/nodata_<threshold>/removal_manifest.csv
<chip-root>/filter_history/nodata_<threshold>/filter_metadata.json
<chip-root>/filter_history/nodata_<threshold>/post_filter_summary.csv
<chip-root>/filter_history/nodata_<threshold>/apply.log
```

Preserve the original unfiltered manifest as a versioned immutable snapshot.

## Validation

- Dry-run projected removals equal Task 006 approved counts.
- Active manifest rows plus removal rows equal the pre-filter manifest exactly.
- No active row has `nodata_pct` above the threshold.
- No active row points to a missing NPZ.
- No removed NPZ remains in the active location.
- No unrelated file was deleted.
- Re-running apply reports an idempotent already-applied state.
- Post-filter totals reconcile globally and by region/source TIFF.

Run Task 005 tests and focused Ruff if code changes are necessary; otherwise do
not widen this execution task into implementation work. Run `git diff --check`
for task/doc updates.

## Smoke test

The production dry-run is the required smoke. Do not perform a second ad hoc
mutation on a subset of the canonical root.

## Acceptance criteria

- The approved threshold is applied universally.
- The active chip collection and manifest are consistent.
- Removal evidence and rollback provenance are retained.
- Updated canonical counts/path are recorded in `docs/data_artifacts.md` and
  `docs/todo.md`.
- Task 009 can package the cleaned collection.

## Non-goals

- Do not change the threshold.
- Do not remove background-only chips.
- Do not create baseline/LORO views.
- Do not package or transfer data.

## Outcome template

Record threshold, pre/post counts and bytes, exact commands, artifact paths,
validation, discrepancies/retries, and next-task inputs.

## Outcome

Task 007 applied the user-approved universal `max_nodata_pct = 50` policy to
the canonical chip root:

```text
/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
```

The required production dry-run reported exactly 6,003 total, 4,637 retained,
and 1,366 removed. Its report has SHA-256
`58479d634243e73127bb8124d3fa46269e2dd47b74cc8e6ea904f7b1a9d68fb4`.
The filter apply then succeeded on its first attempt, and an intentional repeat
reported `already_applied` with the same counts.

The exact dry-run command was:

```bash
root=/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
uv run python -m src.prepare.remove_tiles_with_nodata_areas \
  "$root" \
  --manifest "$root/chip_manifest.csv" \
  --max-nodata-pct 50 \
  --report-output "$root/filter_reports/task007_nodata_50_dry_run.csv" \
  --dry-run
```

The exact apply command, with the required durable log, was:

```bash
mkdir -p /Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1/filter_history/nodata_50
set -o pipefail
root=/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
uv run python -m src.prepare.remove_tiles_with_nodata_areas \
  "$root" \
  --manifest "$root/chip_manifest.csv" \
  --max-nodata-pct 50 \
  --report-output "$root/filter_reports/task007_nodata_50_apply.csv" \
  --apply 2>&1 | tee "$root/filter_history/nodata_50/apply.log"
```

The same filter command was then repeated with `tee -a` and returned the
tested idempotent `already_applied` state. No recovery action or threshold
change was needed.

The active and removed artifact totals are:

```text
pre-filter chips:          6,003 from 369 source TIFFs, 12 regions
retained chips:            4,637 from 367 source TIFFs, 12 regions
removed chips:             1,366; 2 source TIFFs eliminated; 0 regions eliminated
pre-filter compressed:     48,157,853,832 bytes
retained compressed:       44,912,049,410 bytes
removed compressed:         3,245,804,422 bytes
pre-filter class-1 pixels:    112,223,916
retained class-1 pixels:      107,131,696
removed class-1 pixels:         5,092,220
```

The two source TIFFs with no retained chips are
`006_20210805_184050_240c` and
`20210811_185433_06_2262_3B_AnalyticMS_SR_8b_harmonized_clip5`. All clean
background-only chips remain active; Task 007 did not perform background
selection.

Durable filter artifacts are:

```text
chip_manifest.csv
  SHA-256 edf754888dea183f12873594b546b980f350b5b4e293ff62ca7eca64a2c39a39
filter_history/nodata_50/pre_filter_manifest.csv
  SHA-256 7fd2316ae07c4c5277ff33a62ae4c1ee60ced14a528e6a153a6489a7e457d9c8
filter_history/nodata_50/removal_manifest.csv
  SHA-256 37fd56e8f679aebe370a187528dbfb646e09e3c349211d2208b0177fef8f7bcb
filter_history/nodata_50/filter_metadata.json
  SHA-256 4e1fefbc56880d7d11cd19371a14f62fd04df1884b7d179707042157b2cdc551
filter_history/nodata_50/post_filter_summary.csv
  SHA-256 50ddeb3d5732ccd31129dc92fc53a576a91657ae1da4a39f7fa8f857f0b1f9fa
filter_history/nodata_50/apply.log
  SHA-256 623767173420e5ec5d68161f5fe1af86ed34987ec573f6fa82a7452afb5a4da7
```

`post_filter_summary.csv` contains one global row, 12 region rows, and 369
source-TIFF rows, including zero-retained rows for both eliminated sources. It
reconciles pre-filter, retained, and removed chip counts and class-presence
counts, plus retained pixel and compressed-byte totals.

Validation passed for all acceptance checks:

- active plus removal manifests reproduce all 6,003 immutable pre-filter rows
  exactly, with no overlap or row changes;
- every active row has `nodata_pct <= 50`, every removal row is above 50%, and
  all 12 regions remain active;
- the 4,637 active manifest paths exactly equal all NPZ paths on the filesystem,
  while no removed path or transaction quarantine remains;
- completion metadata and pre-filter, active, removal, and report hashes all
  match their recorded values;
- original chipping provenance, all 369 completion fragments, and empty
  issue/staging directories remain present; and
- global totals equal summed region totals and summed source-TIFF totals, with
  each class-presence category reconciling pre-filter as retained plus removed.

No repository code changed. Changed repository documentation is `AGENTS.md`,
`README.md`, `docs/index.md`, `docs/architecture.md`,
`docs/data_artifacts.md`, `docs/todo.md`, `tasks/README.md`, and this task file.
There are no unresolved Task 007 issues.

The exact next action is to open Task 008 and build the non-destructive,
training-only background selector against active manifest SHA-256
`edf754888dea183f12873594b546b980f350b5b4e293ff62ca7eca64a2c39a39`,
without deleting canonical chips. Stop before Task 009 packaging.
