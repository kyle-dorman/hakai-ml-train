# Task 001: Build the raw all-region merge organizer

Status: Complete

Depends on: Task 000

Execution: Local code task; do not create the full merged dataset yet.

## Abstract

Add a deterministic organizer that discovers every paired California and BC
PlanetScope 8-band raster, assigns stable dataset/region/date metadata, and
creates a chipper-compatible `all/images` plus `all/labels` view. The historical
split CSV must not control inclusion because it omitted California regions
`006`, `007`, and `011` and one valid BC tile. This task builds and smoke-tests
the organizer only; Task 002 runs it across all 369 pairs and performs raster
QA.

## Goal

Create `scripts/merge_planet8b_regions.py` with a dry-run-first CLI, portable
manifest schema, explicit issue reporting, and hard-link/copy materialization.

## Inputs

- `AGENTS.md`
- `docs/index.md`
- `docs/todo.md`
- `docs/architecture.md`
- `docs/data_artifacts.md`
- `tasks/000_temporal_baseline_split.md`
- `planet8b_temporal_image_splits.csv`
- `scripts/create_temporal_baseline_split.py`
- California root: `/Volumes/x10pro/kelpseg/ca`
- BC tile root:
  `/Volumes/x10pro/kelpseg/bc/Planet8bSR_BC_Labelled/10km_tiles`

## Source inventory contract

- California images and labels live under `images/` and `labels/`; filenames
  match case-insensitively by TIFF stem.
- California stems begin `<region_int>_<YYYYMMDD>_...` where region is
  `001`–`011`.
- BC pairs may occur under existing `train/images|labels` and
  `val/images|labels`; existing split names are source provenance only.
- Do not include BC `full_scenes` because the 10-km tiles derive from those
  scenes and including both would duplicate imagery.
- The expected complete inventory is 339 California plus 30 BC pairs.
- Source TIFFs and sidecars are immutable. TIFF image/label files are always
  materialized. Before excluding `.tfw`/`.TFW`, verify with isolated CA and BC
  fixture copies that Rasterio still reads the same CRS/transform without the
  sidecar. If a sidecar supplies required georeferencing, materialize the
  minimal required sidecar and record it; deduplicate `.tfw`/`.TFW`
  destinations on case-insensitive filesystems. Overviews and auxiliary XML are
  not copied unless a measured read requirement proves otherwise.

## Planned CLI

```bash
uv run python scripts/merge_planet8b_regions.py \
  --ca-root /Volumes/x10pro/kelpseg/ca \
  --bc-tiles-root /Volumes/x10pro/kelpseg/bc/Planet8bSR_BC_Labelled/10km_tiles \
  --output-root <merged-output-root> \
  --mode hardlink \
  --dry-run
```

Required options:

- `--ca-root`
- `--bc-tiles-root`
- `--output-root`
- `--mode {hardlink,copy}`; default `hardlink`
- `--dry-run`

Do not add a symlink mode: the eventual archive should not depend on the source
tree remaining mounted.

## Output contract

```text
<output-root>/
  all/images/<source_tiff_id>.tif
  all/labels/<source_tiff_id>.tif
  raster_manifest.csv
  merge_issues.csv
```

`raster_manifest.csv` columns, in stable order:

```text
source_tiff_id,dataset,region_id,region_name,acquisition_date,
source_split,source_image,source_label,merged_image,merged_label,
materialization_mode
```

Rules:

- `dataset` is `ca` or `bc`.
- `region_id` is `ca_001`–`ca_011` or `bc`.
- `region_name` reuses the mapping in
  `scripts/create_temporal_baseline_split.py`.
- `acquisition_date` is ISO `YYYY-MM-DD`.
- `source_split` is blank for CA and the discovered historical directory name
  for BC; it has no experimental meaning.
- Paths may be absolute in this local raw-merge manifest.
- `source_tiff_id` is case-insensitively unique across both datasets.

`merge_issues.csv` must always be written, including a header-only file on a
clean run. Columns:

```text
severity,issue_type,dataset,candidate_id,path,details
```

Pairing errors, duplicate stems, unparsable IDs/dates, and destination
collisions are fatal. Unsupported non-TIFF sidecars are not issues.

## Implementation requirements

- Discovery and manifest ordering must be deterministic.
- `--dry-run` must perform discovery, pairing, parsing, collision checks, and
  planned-manifest generation without creating links/copies.
- A non-dry run must refuse a nonempty output root unless its contents exactly
  match a supported resume state; simplest acceptable behavior is fail-fast and
  require a new/empty directory.
- Write manifests through temporary files and atomically rename them.
- If hard linking fails because filesystems differ, fail with guidance to rerun
  using `--mode copy`; do not silently change modes.
- Do not read `planet8b_image_splits.csv` to determine inclusion.

## User decisions required

None for this code-only task. Use the CLI and schema above. Task 002 will ask
the user to confirm the versioned output root before the full run.

## Plan / spec requirement

Before editing, add a short `## Implementation plan` to this file covering:

- discovery and case-insensitive pairing for CA and BC;
- shared metadata parsing with the temporal split generator without creating
  circular script imports;
- atomic output behavior and dry-run behavior;
- focused fixture layout and failure cases.

## Implementation plan

- Discover California pairs from the root `images`/`labels` directories and BC
  pairs from each historical split directory, matching TIFF stems
  case-insensitively and reporting all pairing and duplicate-stem failures.
- Move the region-name and source-filename parsing contract into a small shared
  script module used by both this organizer and the temporal split generator;
  neither script will import the other.
- Build and validate the planned manifest entirely in memory during dry runs.
  For materialization, require an empty/new output root, stage links or copies
  and both CSVs in a temporary sibling directory, then atomically rename the
  complete tree into place.
- Add isolated two-CA/two-BC fixtures covering dry-run and hard-link success,
  duplicate stems, missing labels, nonempty output refusal, cross-filesystem
  hard-link guidance, and Rasterio georeferencing with and without world-file
  sidecars.

## Smoke test

Create a temporary fixture with two CA pairs and two BC pairs. Exercise dry-run,
hard-link creation, duplicate-stem failure, missing-label failure, and nonempty
output failure. Include an isolated georeferencing check with and without
available world-file sidecars. Do not use the full source tree as the smoke
test.

## Validation

```bash
uv run ruff format --check scripts tests
uv run ruff check scripts tests
uv run pytest tests/test_merge_planet8b_regions.py
git diff --check
```

Also run the planned full-source `--dry-run` and confirm it reports exactly 369
pairs without writing the output tree.

## Acceptance criteria

- The script and focused tests exist.
- Full-source dry-run reports 339 CA, 30 BC, 369 total, and 12 region IDs.
- The historical CSV does not control inclusion.
- All fatal issue types produce actionable errors and issue rows.
- Source files remain unchanged.
- `docs/todo.md` points to Task 002 after closeout.

## Non-goals

- Do not run the full materialization.
- Do not inspect raster alignment, CRS, bands, or label values; Task 002 owns QA.
- Do not chip data.
- Do not assign baseline or LORO splits.
- Do not modify raw source names or directories.

## Review pass

- Software architect: verify restartability, manifest ownership, and that the
  organizer is not coupled to experimental splits.
- Risk-averse engineer: verify fail-fast collision behavior and source
  immutability.

## Outcome template

Add `## Outcome` with an abstract, changed files, exact dry-run result,
validation commands, deviations from this contract, and the Task 002 command
template.

## Outcome

Implemented a deterministic, dry-run-first raw organizer with structured fatal
issues, case-insensitive pairing, shared CA/BC metadata parsing, and atomic
hard-link or copy materialization. No merged dataset was created.

Changed repository files:

- `scripts/merge_planet8b_regions.py`: discovery, validation, manifest, issue,
  dry-run, and atomic materialization CLI.
- `scripts/planet8b_metadata.py` and
  `scripts/create_temporal_baseline_split.py`: shared region/date parsing without
  script-to-script imports; regenerating the temporal split remained
  byte-for-byte identical.
- `tests/test_merge_planet8b_regions.py`: two-CA/two-BC fixture coverage for
  dry-run, hard links, duplicate stems, missing labels, destination collisions,
  nonempty output, cross-filesystem guidance, and world-file independence.
- `pyproject.toml` and `uv.lock`: declared pytest and its test import path.
- `docs/todo.md`, `tasks/README.md`, and this task file: task status and handoff.

Full-source dry-run result:

```text
Dry run complete: 339 CA, 30 BC, 369 total, 12 region IDs
```

Isolated copies of a real CA image/label and BC image/label retained identical
Rasterio CRS and transforms without world files. The selected BC image had a
`.tfw`; its internal georeferencing matched with and without that file. The
other selected TIFFs had no world file. No world-file materialization is
required.

Validation completed:

```text
uv run ruff format --check scripts tests
uv run ruff check scripts tests
uv run pytest tests/test_merge_planet8b_regions.py  # 9 passed
git diff --check
uv run pre-commit run --files <Task-001-changed-files>
```

The intended files passed all pre-commit hooks. A repository-wide pre-commit
pass was also run; its end-of-file hook proposed an unrelated newline change to
`planet8b_image_splits.csv`; that incidental change was removed to preserve
scope. There are no durable external artifacts or unresolved Task 001 issues.

Task 002 should first record the approved output root and mode, then run:

```bash
uv run python scripts/merge_planet8b_regions.py \
  --ca-root /Volumes/x10pro/kelpseg/ca \
  --bc-tiles-root /Volumes/x10pro/kelpseg/bc/Planet8bSR_BC_Labelled/10km_tiles \
  --output-root <approved-canonical-raw-root> \
  --mode <hardlink-or-copy> \
  --dry-run
```
