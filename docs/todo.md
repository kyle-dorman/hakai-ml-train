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
Task 005: Build the manifest-driven nodata filter.
tasks/005_build_manifest_nodata_filter.md
```

Task 002 created the 26 GB canonical raw merge at
`/Volumes/x10pro/kelpseg/merged_all_regions_v1`: 339 CA and 30 BC pairs across
12 region IDs. All 369 independent image copies passed checksum verification;
all derived labels match their image grids and use KATE class `3` for image
nodata or missing label coverage. Raster QA and the temporal-split join both
passed for all 369 rows.

Task 004 created the 45 GB unfiltered canonical chip collection at
`/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1`: 6,003 chips and 369
source fragments across all 12 regions. Manifest/filesystem validation, a
74-chip stratified NPZ/raster audit, and a zero-work resume check passed.

## Open queue

Local dataset preparation:

- Tasks 001–002: complete; built and validated the all-region raw merge.
- Task 003: complete; added the restartable manifested chipper and fixture.
- Task 004: complete; built and validated the unfiltered canonical chips.
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
