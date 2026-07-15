# Project TODO

## Current phase

Status: expanded-data temporal baseline and leave-one-region-out generalization
is planned; local data preparation is next.

Current active task:

```text
No implementation task is active.
```

Next task:

```text
Task 002: Create and validate the raw merge.
tasks/002_create_and_validate_raw_merge.md
```

Task 001 completed the dry-run-first raw merge organizer. Its full-source dry
run found 339 California and 30 BC pairs across 12 region IDs without creating
the merged dataset. The current tracked split output is
`planet8b_temporal_image_splits.csv`.

## Open queue

Local dataset preparation:

- Tasks 001–002: build and validate the all-region raw merge.
- Tasks 003–004: extend the chipper and create canonical chips/statistics.
- Tasks 005–007: analyze, select, and apply universal nodata filtering.
- Task 008: build non-destructive training-only background selection.
- Task 009: package and verify the portable dataset archive.

Remote experiment preparation and execution:

- Task 010: transfer and verify the archive.
- Tasks 011–012: materialize baseline and LORO dataset views.
- Tasks 013–014: establish W&B/run registry and training orchestration.
- Tasks 015–016: run the baseline and LORO training suite.
- Tasks 017–018: build and run chip/TIFF prediction evaluation.
- Task 019: compare accuracy on matching source TIFFs.

See `tasks/README.md` for status and direct task links. Detailed acceptance and
outcomes belong in the task files, not here.

## Completed maintenance

- Task 020 restructured active documentation around the PS8B project, corrected
  the W&B destination to `kdorman90-ucla/kelpseg`, and routed project context out
  of the former catch-all `AGENTS.md` and README.

## Current validation loop

```bash
uv run ruff format --check .
uv run ruff check .
```

Use task-specific behavioral checks in addition. Docs-only work also runs
`git diff --check` and verifies Markdown links.
