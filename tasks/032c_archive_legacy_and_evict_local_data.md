# Task 032C: Archive historical controls and evict obsolete local data

Status: Complete — 2026-10-28. Stop before Task 033 implementation.
Selected directly by the user's cleanup instruction after Task 032B.
Starting repository commit: `de06b91`. No Task 033 implementation is authorized.

## Authorization and plan written before execution

Plan recorded at **2026-10-28T11:00:58-07:00** before archiving, retiring code or deleting data.
The user explicitly requested: archive small historical files, retire the old
catalog bootstrap, delete obsolete local data plus local raw/organized copies,
keep cleaned data/chips/analyses/references, and leave Box untouched.
This instruction authorizes local deletion of these formerly immutable copies;
original raw deliveries and published releases remain preserved on Box.
No additional user decision is needed for this exact scope.

Read route: AGENTS, docs/index, docs/todo, tasks/README, docs/documentation,
current artifact/backup/provenance docs and the bootstrap's actual consumers.
This is a bounded cleanup follow-up, separate from Task 033 planning.
Preserve all existing concurrent Task 033 changes and exclude them from this commit.

## Keep in place

All paths below are under `/Volumes/x10pro/kelpseg/`:

- `data/3_cleaned/`, `data/chips/`, `data/splits/`, `data/collections/`,
  `data/examples/` (including tiny v1/v2).
- All `analyses/` (including ongoing Task 033 statistics), `references/`,
  `audits/`, `preparation_inputs/`, `backups/`, `experiments/`, and `runs/`.
- External example producer/check Python files directly under `examples/`.
- New local historical archive: `history/legacy_pre_rebuild_v1/`.
- Every Box object and folder. Run no Box write, delete, sync or transfer command.
  Existing verified publication/restore evidence is sufficient; do not rehash or
  repeat full release QA.

## Archive first

Create the fresh directory `history/legacy_pre_rebuild_v1/` and preserve original
project-relative paths beneath it. Copy small control/source files from the
listed deletion targets, excluding large raster/chip/checkpoint/archive payloads,
ZIP parts, bytecode, `.DS_Store` and old lock files. In particular keep:

- All old-chip CSV/JSON/text/log metadata, histories and the **31 pre-repair
  label TIFF snapshots** (1,753,657 bytes). All old-chip controls plus snapshots
  were measured at 19,099,356 bytes before this task.
- Merge/reconstruction CSV/JSON/text controls from both merge roots and hakai.
- Small XML/TFW and other nonpayload companion/control files; existing archive
  checksum sidecars are historical records, not new checksum generation.
- Old run/config/log metadata from local_training and smoke/example runs.
- Organized-release controls and its small companions before local eviction.
- Bootstrap source and dedicated tests before their repository removal, under
  `history/legacy_pre_rebuild_v1/repository/`.

Keep existing `preparation_inputs/ca_bc/v1/` unchanged. Its five generated tables
are the normal organizer input; they do not need the old CSV locations or the
historical bootstrap at runtime. Also retain a copy of those five small catalog
files in this historical archive for a self-contained catalog handoff.
Verify each retained copy's relative path, byte size and direct byte equality
before deleting any source. No new hashes, receipts, recovery system or framework.

## Exact local deletion set

These are the only deletion roots; large data elsewhere stays in place.
Counts/sizes below are ordinary filesystem observations made before execution.

| Project-relative deletion target | Files before archival | Logical bytes |
|---|---:|---:|
| `archives` | 16 | 134,636,171,034 |
| `ca` | 1,005 | 25,760,942,063 |
| `bc` | 180 | 5,702,097,565 |
| `hakai_match` | 4,760 | 59,361,271,663 |
| `hakai_match_v0.tar` | 1 | 34,945,363,968 |
| `chips_all_regions_1024_512_v1` | 5,075 | 44,873,273,844 |
| `merged_all_regions_v1` | 748 | 27,783,219,664 |
| `merged_ds` | 583 | 24,420,363,890 |
| `zip_archive` | 3 | 22,150,492,242 |
| `data/2_organized/ca_bc/v1` | 1,163 | 28,568,499,959 |
| `local_training` | 11 | 1,072,817,234 |
| `smokes` | 314 | 33,382,263 |
| `restores` | 108 | 255,362,907 |
| `examples/fetched` | 20 | 54,463,809 |
| `examples/runs` | 149 | 355,559,371 |
| `examples/__pycache__` | 1 | 26,025 |

Total candidate logical bytes: **409,973,307,501**; retained archive
copies reduce net reclamation. Initial filesystem free bytes: **542,718,881,792**.
Earlier allocated-block measurements project roughly 410 GB reclaimed; report
actual logical bytes and observed free-space change separately at completion.

The old 1024/512 datasets, ZIP/TAR copies and one-epoch local smoke checkpoints
are superseded. Exact historical training reproduction is not required. Raw
ZIPs (22,150,492,242 bytes) and organized v1 (28,568,499,959 bytes) have verified
Box copies from Tasks 027/030A; the current cleaned/chip releases remain local.
Copy the small retained evidence first, then remove these explicit roots in a
plain sequence; stop on an actual failure. Remove empty raw/organized parent
folders only if empty. No general cleanup utility or new installed command.

## Bootstrap retirement and documentation

After the archive is verified, remove `src/kelpseg/prepare/legacy_catalog.py`
and `tests/test_legacy_catalog.py`. Remove only its test/import/fixture from
`tests/test_prepare_catalog_progress.py`, preserving generic organizer progress
coverage. Update `tests/test_distribution.py` and the prepare package docstring.
No other runtime module imports this bootstrap. Keep all generic organizer,
cleanup, chip/split code and useful scientific tests.

Update the researcher guide to use the finished catalog directly and restore
raw ZIPs from Box before a future rebuild. Replace stale current-facing bootstrap
and local-presence statements in architecture, artifact policy and provenance;
retain historical task evidence. Add a compact entry to both queues.

## Validation and completion

- Archive path/size/direct-byte comparisons pass before local deletion.
- Every explicit deletion target is absent; retained roots still exist.
- Before raw eviction, validate the existing catalog through the generic
  metadata-only organizer preview. After eviction retain its schema/recipe
  references and document restoring ZIPs before any future live preview; do not
  fetch raw data just to test cleanup.
- Load representative current chips in 8/4/3 modes and verify the retained
  cleaned headers without full payload rescanning or a new release audit.
- Run relevant generic organizer/CLI/distribution tests, Ruff format/check and
  all-file pre-commit for this multi-file removal; preserve unrelated failures
  and concurrent changes. Check changed Markdown links and git diff whitespace.
- Record actual archived/deleted file counts, bytes, free-space change, code/docs
  changes, validation, limits and exact handoff. Commit only this cleanup.

Stop after this task; Task 033 remains separate. No training, prediction,
scoring, new ingestion, new release production, or Box changes.

## Pre-deletion execution checkpoint

Recorded **2026-10-28T11:04:19-07:00**,
before deleting local data. Historical archive verified by direct byte equality:
**910 copied files / 33,990,476 bytes**, plus README: **911 files / 33,991,103
bytes**. It includes all 31 label snapshots (1,753,657 bytes), original bootstrap
source/tests and the finished catalog. The archive remains local; no Box command
has run.

Bootstrap retirement is complete in the five planned code/test paths. All
**105 focused organizer/progress/CLI/distribution tests pass**, including isolated
wheel/sdist installs; Ruff format/check pass. The generic organizer preview using
the retained catalog and a fresh, unwritten `cleanup_validation` release resolves
**369 pairs / 418 companions / 1,156 payloads** after bootstrap removal. A first
validation assertion had an incorrect expected payload total of 1,155; the
correct arithmetic is 2 x 369 + 418 = 1,156. No product/input failure occurred.
No old CSV location is required by the normal organizer. No preview output was
written. The deletion phase may now proceed for the exact roots above.

## Outcome (2026-10-28)

The user-approved plan and pre-deletion checkpoint above were written before
execution. All 16 primary deletion roots and the two separately pre-documented
organized-smoke addendum roots were removed in plain sequential operations.
No deletion occurred outside those two explicit lists. Empty organized parent
directories were removed after all local organized copies were evicted.

### Measured local results

- Historical archive: `/Volumes/x10pro/kelpseg/history/legacy_pre_rebuild_v1/`,
  **938 files / 34,123,571 bytes**, including README, preserved original relative
  paths, bootstrap source/test snapshots and a copy of the finished catalog.
  All 937 copied files passed individual size and direct byte-equality checks
  before source deletion. The 31 pre-repair label TIFFs total 1,753,657 bytes.
- Deleted: **14,177 files / 410,017,227,683 logical bytes**. This includes the
  raw ZIPs, organized v1, superseded datasets, old ZIP/TAR/part duplicates,
  obsolete one-epoch local checkpoints, and generated smoke/restore/example
  copies. The exact per-root counts/sizes are the main and addendum pre-execution tables.
- Observed filesystem free bytes increased from **542,697,906,176** before
  archiving to **952,718,057,472** after all deletions: **410,020,151,296 bytes**
  (about 410.0 GB). Logical deleted sizes and observed filesystem free-space
  changes are separate measurements; the archive remains allocated locally.
- Current cleaned imagery, canonical chips, split/collection controls, tiny
  input versions, analyses (including concurrent Task 033 work), references,
  audits, preparation inputs, backups and small corrected historical experiment
  results remain in place. External example producer/check scripts remain.
- **Box was untouched:** no rclone or other Box read/write/delete/sync/transfer
  operation ran in this task. All previously published raw/organized/cleaned/
  chip releases remain their preserved copies; this task made no new remote
  integrity claim. The new historical archive is local only.

### Bootstrap retirement and researcher workflow

Removed the 650-line `src/kelpseg/prepare/legacy_catalog.py` and its dedicated
`tests/test_legacy_catalog.py`. Retired only the bootstrap-specific progress
test/import/fixture plugin, preserving the generic organizer progress test.
Updated the installed distribution expectations and `prepare/__init__.py`
docstring. No runtime module or remaining test imports the bootstrap. Generic
organization, cleanup, chipping, splitting and loading are unchanged.

The active five-file `preparation_inputs/ca_bc/v1/` catalog remains byte-for-byte
unchanged, with 369 membership rows. The generic organizer preview succeeded
after bootstrap removal and before ZIP eviction: 369 pairs, 418 companions and
1,156 planned payloads, with no output/pixel reads. The catalog stores ordinary
input declarations; its historical producer string is provenance, not a Python
import requirement. Future organization requires restoring the raw ZIPs to
`zip_archive/` from Box, or directly fetching the published organized release.
Training/loading current chips needs neither old merge roots nor raw/organized
local payloads.

Updated `docs/quickstart.md` to remove the bootstrap recipe and show the existing
catalog plus an explicit raw-ZIP restore recipe. Updated architecture, data
artifact policy, cleanup provenance, Box recovery and README to distinguish
current local data from historical/remote copies. Both queues record this
cleanup as complete; Task 033 planning remains separate. Existing historical
task records and catalog evidence were preserved.

### Validation and handoff

- **105 focused tests passed** across organizer input/engine/behavior, generic
  progress, CLI and isolated wheel/sdist installation.
- Ruff format/check and all-file pre-commit passed. Changed Markdown links/
  anchors, shell/Python snippets and git whitespace checks passed. No unrelated
  failure was observed. Concurrent Task 033 edits were preserved and excluded
  from this cleanup commit.
- Post-deletion: all required retained roots exist; all five active catalog
  files match their archived bytes; complete chip summary remains unchanged.
  **12 native/RGB+NIR/RGB chip load cases** across active train/val/test and a
  canonical partial edge pass. **Three cleaned image/label header pairs** pass
  band-count/nodata checks without any full pixel rescan.
- No new hashes, receipts, recovery framework, synchronization service or
  hypothetical concurrency guards were introduced. No release was rebuilt,
  and no training, prediction, scoring or Task 033 implementation ran.

Exact next action: continue the separately scoped Task 033 planning/implementation
when selected. Use the retained current chip/split/collection paths and existing
analyses/normalization decisions. Do not restore raw or organized data merely
to train. For future reconstruction use the retained catalog and documented Box
fetch recipe; do not recreate the retired historical bootstrap or resurrect old
dataset layouts. Stop this cleanup task here.

## Pre-execution addendum: remaining organized smoke copies

Recorded **2026-10-28T11:17:56-07:00**
before this additional deletion. Final inspection found two older organized
smoke datasets outside the production-v1 deletion target. They are also within
the user's authorized obsolete-local/organized-copy cleanup:

| Additional project-relative target | Files | Logical bytes |
|---|---:|---:|
| `data/2_organized/task029a_smoke_ca_bc/` | 25 | 21,965,646 |
| `data/2_organized/task029b_prepare_review/` | 15 | 21,954,536 |

First copy their non-raster/control files into the same history archive, preserving
relative paths and excluding old lock files. Verify direct bytes and sizes, then
remove only these two directories and the now-empty `data/2_organized/` parent.
Keep every cleaned/chip/analysis/reference root unchanged. No Box operation.
The main cleanup is already committed as `336b25c`; concurrent Task 033 planning
was preserved in its separate commit. This addendum does not change that work.

### Addendum completion

Both additional organized smoke copies were removed after archiving and direct
byte-checking **27 control files / 132,468 bytes**. The additional deletion was
**40 files / 43,920,182 logical bytes**. `data/2_organized/` is now absent.
Final combined archive/deletion/free-space totals are reported in the outcome
above; the main-phase pre-deletion checkpoint remains an unchanged historical
observation. All retained current/evidence roots remain present. No Box command
or further pipeline change was made.
