# Task 004: Chip all regions locally

Status: Complete

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

Decision (2026-07-15): use the canonical output root
`/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1`, 1024-pixel chips,
512-pixel stride, all eight bands, and `uint16` image storage. Remap the five
KATE classes with `--remap 0 1 0 -100 0`: water, land, and waves to valid
background; kelp to foreground; and nodata to the `-100` ignore index. Run
sequentially with `--num_workers 0` and retain `--resume` for safe
restartability.

## Execution plan

1. Check free space and estimate output size from one representative raster.
2. Run one California and one BC source through the final command.
3. Validate NPZ arrays and manifest rows.
4. Remove the bounded smoke output, not canonical data.
5. Run the full command with persistent logs and resume enabled as designed.
6. Consolidate the canonical manifest only after all sources complete.
7. Produce `chip_qa_summary.json` and `chip_counts_by_source.csv`.

## Run correction plan

The first sequential production attempt stopped safely after 154 completed
source fragments and 3,762 chips when source `006_20210802_175055_2460`
proved to be 2,416 x 870 pixels, so no 1,024-pixel square window fit. A full
inventory check found 46 valid sources with at least one dimension below
1,024, including every `ca_007` source. Excluding them would eliminate a
region from the canonical chip collection and violate the complete-region
evaluation contract.

Correct the chipper before resuming:

1. For a source dimension below 1,024, emit one true-size window spanning that
   dimension; keep the existing 1,024/512 full-window grid in every dimension
   at least 1,024 pixels long.
2. Store the true partial width/height and bounds in the existing manifest
   fields and chip ID. Do not pad canonical NPZs or invent bounds outside the
   source raster.
3. Preserve all 154 completed full-window fragments unchanged and verify that
   `--resume` processes only unfinished sources.
4. Add focused tests for one- and two-dimension small sources, manifest/NPZ
   shape agreement, bounds, statistics, and resume.
5. Record that later training/validation padding must use the `-100` ignore
   index for masks rather than create artificial class-0 background pixels.

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
class-presence pattern, and nodata-percentage bins. Class-presence reporting
must use the manifest counts to distinguish foreground-positive chips, clean
background-only chips, mixed background/nodata chips, and ignore-only chips.
Record total class-0 background, class-1 foreground, ignore, and nodata pixels,
along with total compressed bytes and manifest row count. These counts are the
input to Task 008's training-only background selection.

## Validation

- Every retained source TIFF has at least one chip or a documented fatal issue.
- Every NPZ maps to exactly one manifest row; every row maps to one NPZ.
- Every row joins to one raster-manifest row.
- Stored image and label shapes agree with manifest dimensions.
- Class plus ignore counts equal total pixels.
- Nodata counts recomputed from a stratified sample match the manifest.
- Offsets/bounds for a sample from every region agree with source rasters.
- Every source dimension below the chip size is represented by a true-size
  partial window, and no canonical array contains synthetic padding.
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

## Outcome

The unfiltered canonical chip collection is complete at:

```text
/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
```

The approved production command used 1,024-pixel windows, 512-pixel stride,
eight retained bands, `uint16` images, `--remap 0 1 0 -100 0`, sequential
source processing, and `--resume`. The exact shell invocation is preserved in
`creation_command.txt`; complete output, the controlled first failure, retry,
and final zero-work resume are preserved in `chipping.log`.

The first run completed 154 sources and 3,762 chips in 32 minutes 55 seconds
before safely stopping on a 2,416 x 870 source. The chipper was corrected to
write true-size windows only when an entire source dimension is below 1,024
pixels. The resumed source-processing phase completed the remaining 215
sources in 18 minutes 23 seconds without rewriting completed fragments. A
final resume rerun validated the completed collection and reported zero
pending sources.

Final inventory:

```text
source TIFFs:              369
regions:                    12
manifest rows / NPZ files: 6,003
true-size partial chips:     52
compressed NPZ bytes:       48,157,853,832 (about 44.9 GiB)
manifest SHA-256:            7fd2316ae07c4c5277ff33a62ae4c1ee60ced14a528e6a153a6489a7e457d9c8
```

Chip class-presence counts are 3,577 foreground-positive, 521 clean
background-only, 1,595 mixed background/nodata, and 310 ignore-only. Counts
across overlapping chips reconcile to 6,276,313,120 stored pixels:
4,416,343,400 class-0, 112,223,916 class-1, and 1,747,745,804 ignore pixels.
Image nodata accounts for 1,670,278,579 of those chip pixels. These are chip
grid totals and intentionally double-count source pixels covered by overlapping
windows; they are selection inputs, not source-level evaluation totals.

Durable external artifacts:

- `all/*.npz`: 6,003 canonical, unfiltered chips.
- `chip_manifest.csv`: portable chip identity, window, class, and nodata rows.
- `manifest_parts/all/*.csv`: 369 restartable completion fragments.
- `chip_counts_by_source.csv`: 369 per-source count summaries.
- `chip_qa_summary.json`: global/dataset/region/year/class/nodata summaries and
  validation evidence.
- `creation_command.txt` and `chipping.log`: exact command and execution log.

Validation passed:

- all 369 source IDs have at least one chip and one completion fragment;
- all 6,003 manifest paths and NPZ files form a bijection, including
  case-insensitive uniqueness;
- every row joins exactly to the raster manifest and all manifest counts,
  percentages, windows, and true-size partial rules reconcile;
- the production consolidation and final resume revalidated every NPZ shape,
  dtype, class/ignore count, and nodata count;
- a deterministic 74-chip sample covering every region, nodata bin,
  class-presence category, and all partial chips matched NPZ arrays and source
  raster CRS/bounds;
- no issue or staging files remain, no chip was filtered, and the final resume
  reported zero pending sources;
- `uv run pytest` passed all 19 tests; task-scoped Ruff and `git diff --check`
  passed.

Repository-wide Ruff remains blocked only by pre-existing formatting drift and
two unused loop variables in legacy SKEMA notebooks, outside the active PS8B
scope. Later dataset/training tasks must pad true-size chip masks with `-100`,
not class-0 background, as recorded in `docs/architecture.md`.

Changed repository files include the small-source window correction in
`src/prepare/make_chip_dataset.py`, the deterministic validator in
`scripts/validate_chip_dataset.py`, focused tests in
`tests/test_make_chip_dataset.py`, and synchronized architecture, artifact,
routing, Task 004, and Task 008 contracts.

The exact next action is Task 005: implement and test the manifest-driven
nodata filter, then run its required report-only examples against this
canonical manifest without applying a threshold.
