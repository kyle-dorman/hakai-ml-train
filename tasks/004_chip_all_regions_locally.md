# Task 004: Chip all regions locally

Status: Pending

Depends on: Task 003

Execution: Local long-running data task.

## Abstract

Choose the final chip parameters, run the manifested chipper over all 369 source
TIFFs, and validate the resulting unfiltered canonical chip collection. This is
the only full chipping pass planned for baseline and LORO work. It must finish
with a reproducible command, complete manifest, and per-region/source summary.

## Goal

Produce the canonical pre-filter chip root that Tasks 005–009 will analyze,
filter, and archive.

## Inputs

- Task 002 canonical raw root and raster manifest
- Task 003 final chipper CLI and schema
- Task 003 approved overlap-reconstruction contract
- `configs/kelp-ps8b/california/segformer_b3.yaml` for current model input
  expectations, not as authority for paths or W&B
- `docs/data_artifacts.md`

## User decisions required

Confirm these run parameters after reviewing Task 002 dtype/label QA and Task
003 smoke evidence:

1. Canonical chip output root. Recommendation:
   `/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1` if size/stride below
   are accepted.
2. Chip size: `1024`, approved during Task 003.
3. Stride: `512` for 50% overlap, approved during Task 003.
4. Retained bands: `8`.
5. Output dtype. Recommendation must be based on Task 002 range; do not default
   to `uint8` for PlanetScope reflectance.
6. Exact label remapping, based on Task 002 observed values and binary model
   contract.
7. Worker count appropriate for the local machine.

Write the approved values into this task before starting. Do not infer them
solely from historical path names.

## Execution plan

1. Check free space and estimate output size from one representative raster.
2. Run one California and one BC source through the final command.
3. Validate NPZ arrays and manifest rows.
4. Remove the bounded smoke output, not canonical data.
5. Run the full command with persistent logs and resume enabled as designed.
6. Consolidate the canonical manifest only after all sources complete.
7. Produce `chip_qa_summary.json` and `chip_counts_by_source.csv`.

## Required outputs

```text
<chip-root>/all/*.npz
<chip-root>/chip_manifest.csv
<chip-root>/manifest_parts/...
<chip-root>/chip_counts_by_source.csv
<chip-root>/chip_qa_summary.json
<chip-root>/creation_command.txt
<chip-root>/chipping.log
```

The summary must include chip counts by dataset, region, source TIFF, year,
class-presence pattern, and nodata-percentage bins. Record total compressed
bytes and manifest row count.

## Validation

- Every retained source TIFF has at least one chip or a documented fatal issue.
- Every NPZ maps to exactly one manifest row; every row maps to one NPZ.
- Every row joins to one raster-manifest row.
- Stored image and label shapes agree with manifest dimensions.
- Class plus ignore counts equal total pixels.
- Nodata counts recomputed from a stratified sample match the manifest.
- Offsets/bounds for a sample from every region agree with source rasters.
- Chip IDs and paths are unique case-insensitively.
- Resume dry-run reports no work after successful completion.

Run the Task 003 tests and focused Ruff checks after any code correction made
during the run. Run `git diff --check` for recorded task/doc changes.

## Smoke test

The preflight must include:

- one ordinary California TIFF;
- one source from `ca_006`, `ca_007`, or `ca_011`;
- one BC tile;
- one source containing measurable nodata.

## Acceptance criteria

- The canonical chip path and exact parameters are recorded in this task,
  `docs/data_artifacts.md`, and `docs/todo.md`.
- Chipping finishes for all valid source rasters with no unresolved partial
  source state.
- The manifest is complete, portable, and validated.
- No nodata/background deletion has occurred yet.
- Task 005 can operate without reopening NPZ files for normal selection.

## Non-goals

- Do not choose or apply a nodata threshold.
- Do not remove background-only chips.
- Do not create baseline/LORO directories.
- Do not archive or transfer data.
- Do not train a model.

## Outcome template

Record approved parameters, exact command, runtime/restarts, output path and
size, chip/source/region counts, validation evidence, issues, and Task 005
inputs.
