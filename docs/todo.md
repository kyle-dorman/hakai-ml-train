# Project TODO

## Current phase

Status: Task 009A repaired the source-aware nodata defect, regenerated the
selected one California plus all 30 BC label/source fragments, reapplied the
approved 50% policy, and clean-extraction verified the v2 archive. Remote
transfer has not started.

Current active task:

```text
Task 010: Transfer and verify the repaired v2 archive.
tasks/010_transfer_and_verify_remote.md
```

Next task:

```text
Task 011: Materialize the temporal baseline dataset view.
tasks/011_materialize_baseline_dataset.md
```

Task 002 created the 26 GB canonical raw merge at
`/Volumes/x10pro/kelpseg/merged_all_regions_v1`: 339 CA and 30 BC pairs across
12 region IDs. All 369 independent image copies passed checksum verification;
all derived labels match their image grids and use KATE class `3` for image
nodata or, in the original Task 002 output, missing label coverage. Task 009A
later superseded the repaired-source label contract described below. Raster QA
and the temporal-split join both passed for all 369 rows.

Task 004 created the 45 GB unfiltered canonical chip collection at
`/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1`: 6,003 chips and 369
source fragments across all 12 regions. Manifest/filesystem validation, a
74-chip stratified NPZ/raster audit, and a zero-work resume check passed.

Task 005 replaced the any-nodata deletion script with a required-threshold,
manifest-driven dry-run/apply CLI. Fixture rollback/recovery tests and real
report-only runs at 0% and 50% passed; at Task 005 completion the canonical
manifest and all 6,003 chips remained unchanged.

Task 006 analyzed global, regional, source-TIFF, class-1, and visual effects of
candidate nodata thresholds. The user approved `max_nodata_pct = 50`: the
validated dry-run retains 4,637 chips and removes 1,366 without eliminating a
region.

Task 007 transactionally applied the approved threshold. At Task 007
completion, the active manifest contained 4,637 chips from 367 source TIFFs
across all 12 regions, with
44,912,049,410 compressed NPZ bytes. The immutable 6,003-row pre-filter
manifest, 1,366-row removal manifest, completion metadata, apply log, and
global/region/source summary are preserved under `filter_history/nodata_50`.

Task 008 replaced destructive background deletion with a manifest-only
training selector. Its pre-repair `exclude_all` selection joined all 4,637
active chips one-to-one, selected 3,210 positive chips, and explicitly excluded
1,427 non-positive chips. Its global, region, and source-TIFF audit summary and
selection manifest are under `background_selection/exclude_all`; canonical
chips and the active manifest are unchanged.

Task 009 created and clean-extraction verified
`planet8b_all_regions_1024_512_v1.zip` under
`/Volumes/x10pro/kelpseg/archives`. The 44,917,177,439-byte ZIP has SHA-256
`6640757c19d803a000834b34abdb20c71a5359e215e8edf08b4958123c4ab098`
and contains all 4,637 canonical NPZs plus the portable manifests and compact
provenance needed by Tasks 010–012. Its internal inventory hashes every NPZ.
This v1 archive is preserved as historical evidence but is superseded as a
transfer candidate.

Task 009A inventoried all 369 source TIFFs as 44 with declared nodata metadata
and 325 with approved effective nodata `0`; the only nonzero declarations are
the five known California `65535` sources. It repaired 5,203 California label
false negatives and rebuilt all 30 BC merged labels from their raw `{0,1}`
labels so class `3` now exactly matches image nodata. Only those 31 complete
source fragments were re-chipped: 724 NPZs were regenerated and 482 remain in
the active collection. Corrected statistics added 35 removals, yielding 4,602
active chips and 1,401 total removals. The refreshed `exclude_all` selection
contains all 4,602 active chips, selects all 3,210 positive chips, and excludes
1,392 non-positive chips.

The clean-extraction-verified v2 archive is
`/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v2.zip`.
It is 44,859,496,084 bytes with SHA-256
`1244ecfe2cc4cee624bb5661087f0126ea239367bda60efd823b4fcb9b7399db`.
Its 4,623-row inventory contains 4,602 NPZs; 4,120 unchanged chip hashes were
reused from the trusted v1 inventory, while all 482 rewritten retained NPZs and
21 manifest/metadata members were freshly hashed.

## Open queue

Local dataset preparation:

- Tasks 001–002: complete; built and validated the all-region raw merge.
- Task 003: complete; added the restartable manifested chipper and fixture.
- Task 004: complete; built and validated the unfiltered canonical chips.
- Task 005: complete; added the transactional manifest-driven nodata filter.
- Task 006: complete; selected the universal 50% nodata threshold.
- Task 007: complete; applied the approved threshold transactionally.
- Task 008: complete; built and applied the non-destructive training selector.
- Task 009: complete; packaged and verified the portable dataset archive.
- Task 009A: complete; repaired source-aware nodata metadata, scoped labels and
  source fragments, dependent selections, and the clean-verified v2 archive.

Remote experiment preparation and execution:

- Task 010: pending; transfer and verify the repaired v2 archive.
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
