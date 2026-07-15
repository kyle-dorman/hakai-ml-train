# Task 007: Apply the universal nodata filter

Status: Pending

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
