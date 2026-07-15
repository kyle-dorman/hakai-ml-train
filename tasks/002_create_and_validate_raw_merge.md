# Task 002: Create and validate the raw merged dataset

Status: Complete

Depends on: Task 001

Execution: Local data task.

## Abstract

Run the Task 001 organizer against the complete local California and BC sources,
then validate the resulting 369 image/label pairs at raster level. This task
promotes one versioned raw merge as the canonical input to chipping. It does not
modify the chipper or generate NPZ chips.

## Goal

Create a complete, immutable-input raw merge with a validated raster manifest
and a compact QA report that Task 003 can trust.

## Inputs

- Task 001 outcome and `scripts/merge_planet8b_regions.py`
- `/Volumes/x10pro/kelpseg/ca`
- `/Volumes/x10pro/kelpseg/bc/Planet8bSR_BC_Labelled/10km_tiles`
- `planet8b_temporal_image_splits.csv`
- `docs/data_artifacts.md`

## User decisions required

The canonical output root recommendation was:

```text
/Volumes/x10pro/kelpseg/merged_all_regions_v1
```

The user confirmed that the canonical dataset should use independent copies,
not hard links, because Task 002 must derive corrected label rasters. Both
decisions are recorded below.

Approved execution decisions:

```text
canonical output root: /Volumes/x10pro/kelpseg/merged_all_regions_v1
image materialization mode: copy
label source: paired labels under the BC 10km_tiles and CA source roots
derived label nodata class: 3
```

The canonical merge must be independent of the source trees: copy every image
and write every label as a derived raster. Do not use hard links. The source
images and labels remain immutable, while the copied dataset can carry corrected
label grids and nodata metadata without sharing canonical file inodes with the
raw inputs.

## Execution finding and approved remediation

The full dry run passed and the organizer materialized 369 hard-linked pairs at
the approved root. The required three-pair raster smoke test then stopped the
QA run because the selected BC image and label did not share a grid. A
metadata-only audit (without generating QA acceptance artifacts) found:

```text
335 of 339 CA pairs have exactly matching image/label grids
4 of 339 CA pairs have shape and/or transform mismatches
0 of 30 BC pairs have matching image/label grids
30 BC labels use one 14,920 x 29,304 EPSG:32609 grid
21 of 30 BC image extents are fully covered by that label grid
```

The four CA mismatches are one `ca_002` pair with a larger, offset label and
three `ca_008` pairs whose labels are 11 columns narrower and shifted 33 m
east. The BC labels are full-area rasters rather than per-image aligned tiles;
nine BC images extend beyond their label bounds.

Inspection of `bc/Planet8bSR_BC_Labelled/full_scenes` found six matching
image/label families, but those labels also use smaller, offset annotation
grids. The 30 labels under `10km_tiles` are byte-identical copies of one
regional mosaic. Cropping that regional mosaic provides more labeled coverage
than using only the matching full-scene label, so the approved source remains
`10km_tiles`.

The user approved the following derived-label contract:

- Write every output label on the exact width, height, CRS, affine transform,
  and bounds of its paired image.
- Reproject/crop source labels with nearest-neighbor sampling; never interpolate
  categorical classes.
- Preserve stored KATE class values. In particular, keep `0 = water` and
  `1 = kelp`; the BC labels contain only `0` and `1`, while the complete source
  inventory contains `0`, `1`, `2`, and `3`.
- Set the output value to `3 = nodata` wherever all eight image bands equal
  zero or the image pixel lies outside the source label's geographic coverage.
- Set output TIFF nodata metadata to `3`. Do not honor the source label's
  conflicting `nodata=0` metadata because `0` is the water/background class.
- Keep output labels as `uint8`. The later label-remapping stage will convert
  class `3` to the training ignore index `-100`; Task 002 does not perform that
  remapping.

The first materialized root is provisional because it uses hard links and its
labels are unaligned. Rebuild the approved root atomically with copied images
and derived labels before full QA. Raw sources remain unchanged.

## Execution plan

1. Check free space and source mount health.
2. Run the full dry-run and save its console summary.
3. Review `merge_issues.csv`; stop on any fatal issue.
4. Extend the organizer with deterministic, blockwise derived-label creation
   and per-source alignment statistics. Stage the complete output atomically.
5. Rebuild the provisional root with copied images and derived labels.
6. Validate the three-pair smoke set, including assigned class-3 pixels.
7. Validate every image/label pair with Rasterio.
8. Write `raster_qa.csv`, `label_alignment.csv`, and
   `raster_qa_summary.json` beside the manifest.
9. Reconcile the manifest to `planet8b_temporal_image_splits.csv` by
   `source_tiff_id`; every temporal-split row must match exactly one merged row.
10. Verify that the later label-remapping contract receives `0`, `1`, and `3`
    without performing that remap in this task.

## Raster QA contract

For every pair, record:

```text
source_tiff_id,dataset,region_id,image_width,image_height,label_width,
label_height,image_count,label_count,image_dtype,label_dtype,image_crs,
label_crs,image_transform,label_transform,bounds_match,shape_match,crs_match,
transform_match,image_min,image_max,label_values,status,details
```

Required validity:

- image and label width/height match;
- CRS and affine transform match exactly or within a documented Rasterio-safe
  tolerance;
- bounds match consistently with transform/shape;
- imagery has eight bands;
- label raster has one band;
- output label dtype is `uint8` and TIFF nodata metadata is `3`;
- stored class values are within the KATE set `{0, 1, 2, 3, 4}`;
- every all-eight-bands-zero image pixel has output label `3`;
- every pixel outside source-label coverage has output label `3`;
- covered, data-bearing pixels preserve the nearest source-label class;
- filenames and manifest identity agree;
- TIFFs open without read errors;
- label values are summarized, not silently remapped.

Do not load all raster pixels simultaneously. Stream/block-read min/max and
label-value summaries if files are large.

Also write a portable `raster_metadata.csv` with one row per source TIFF and
stable numeric georeferencing fields needed after raw TIFFs are omitted from the
remote archive:

```text
source_tiff_id,dataset,region_id,region_name,acquisition_date,width,height,
band_count,image_dtype,label_dtype,crs,transform_a,transform_b,transform_c,
transform_d,transform_e,transform_f,bounds_left,bounds_bottom,bounds_right,
bounds_top
```

This table must describe the validated image/label grid and must not require
local absolute paths.

## Expected outputs

```text
<canonical-raw-root>/all/images/
<canonical-raw-root>/all/labels/
<canonical-raw-root>/raster_manifest.csv
<canonical-raw-root>/merge_issues.csv
<canonical-raw-root>/copy_verification.csv
<canonical-raw-root>/raster_qa.csv
<canonical-raw-root>/label_alignment.csv
<canonical-raw-root>/raster_metadata.csv
<canonical-raw-root>/raster_qa_summary.json
<canonical-raw-root>/creation_command.txt
```

The summary must include counts by dataset, region, acquisition year, image
dtype, label dtype, image band count, label-value set, QA status, and total
pixels assigned class `3` by image nodata, missing label coverage, and their
union. `label_alignment.csv` must retain those counts per source TIFF along
with source/output grids and the nearest-neighbor method.

## Suggested commands

Use the final CLI recorded by Task 001. At minimum:

```bash
df -h /Volumes/x10pro
uv run python scripts/merge_planet8b_regions.py <approved arguments> --dry-run
uv run python scripts/merge_planet8b_regions.py <approved arguments>
```

If Task 001 did not add a reusable QA entry point, add a narrow
`scripts/validate_planet8b_raw_merge.py` rather than embedding an opaque one-off
notebook in this task.

## Smoke test

Validate three pairs before the full QA pass: one normal California TIFF, one
California TIFF from a newly included region, and one BC tile. Confirm Rasterio
metadata comparisons and label-value extraction.

## Validation

- Manifest has 369 unique rows: 339 CA and 30 BC.
- Region IDs are `ca_001`–`ca_011` plus `bc`.
- Every merged image is an independent copy of the recorded source with matching
  byte size and checksum; no merged file is hard-linked to a source file.
- Every merged label records its immutable source label and derived-grid
  provenance.
- Every split CSV row joins exactly once; no merged row lacks a recognized
  region/date.
- QA has no unresolved error status.
- Derived labels exactly match their image grids and satisfy the approved
  class-3 assignment checks.
- Re-running the organizer fails safely or reports the documented resume state.
- Run code checks for any script added or changed and `git diff --check`.

## Acceptance criteria

- The approved canonical raw root and portable raster metadata are recorded in this task,
  `docs/data_artifacts.md`, and `docs/todo.md`.
- All 369 pairs pass the required raster checks or the task stops with a
  user-reviewed exception; do not wave through mismatches.
- Label values and image dtype/range are known before Task 003/004.
- The merged root is ready for `--splits all` chipping.

## Non-goals

- Do not chip or filter data.
- Do not choose chip size, stride, dtype conversion, or label remapping.
- Do not create baseline/LORO split folders.
- Do not delete the historical merge or raw source files.

## Outcome template

Record the canonical path, creation command, materialization mode, counts, QA
summary, label values, image dtype/range, exceptions, validation, and exact
Task 003 inputs.

## Outcome

Created and validated the independent canonical raw merge at:

```text
/Volumes/x10pro/kelpseg/merged_all_regions_v1
```

The 26 GB artifact contains 369 copied 8-band images and 369 derived labels:
339 CA pairs, 30 BC pairs, and region IDs `ca_001`–`ca_011` plus `bc`. Images
are independent copies rather than hard links. All 369 copies have matching
source/destination SHA-256 checksums and different inodes.

The creation command is recorded in `creation_command.txt`:

```bash
uv run python scripts/merge_planet8b_regions.py \
  --ca-root /Volumes/x10pro/kelpseg/ca \
  --bc-tiles-root /Volumes/x10pro/kelpseg/bc/Planet8bSR_BC_Labelled/10km_tiles \
  --output-root /Volumes/x10pro/kelpseg/merged_all_regions_v1 \
  --mode copy \
  --derive-labels
```

The producer was the Task 002 worktree based on git commit
`ca684aa9409b3695d103a21db5ca5f6b70af364a`, with the Task 002 changes listed
below still uncommitted at artifact creation.

Derived labels use nearest-neighbor reprojection on the exact paired-image
grid. Stored KATE values are preserved; label `3` is assigned wherever all
eight image bands are zero or source-label coverage is absent. Output labels
are `uint8` with TIFF nodata metadata `3`. Across 2,905,415,276 source pixels:

```text
image-nodata pixels:                    1,104,741,072
outside-source-label pixels:               36,925,269
both image-nodata and outside label:        24,053,323
union assigned nodata class 3:           1,117,613,018
```

Source and output label values have union `{0, 1, 2, 3}`. The 369 images are
all 8-band `uint16`, with observed values from 0 to 65,535. The 369 derived
labels are single-band `uint8`.

Changed repository files:

- `scripts/merge_planet8b_regions.py`: optional exact-grid label derivation,
  copy checksum/inode verification, atomic alignment provenance, and creation
  command capture.
- `scripts/validate_planet8b_raw_merge.py`: streamed raster QA, copy/alignment
  provenance checks, portable raster metadata, and split reconciliation.
- `tests/test_merge_planet8b_regions.py` and
  `tests/test_validate_planet8b_raw_merge.py`: focused alignment, KATE nodata,
  grid-mismatch, provenance, and reconciliation coverage.
- `AGENTS.md`, `README.md`, `docs/index.md`, `docs/todo.md`,
  `docs/architecture.md`, `docs/data_artifacts.md`, `tasks/README.md`, and this
  task: canonical artifact and handoff documentation.

Durable external artifacts:

- `raster_manifest.csv`: 369 source/merged identity rows.
- `copy_verification.csv`: 369 matching SHA-256 and independent-inode rows.
- `label_alignment.csv`: 369 source/output grid and nodata-assignment rows.
- `raster_qa.csv`: 369 passing raster QA rows.
- `raster_metadata.csv`: 369 portable grid metadata rows.
- `raster_qa_summary.json`: compact counts and reconciliation result.
- `merge_issues.csv`: header only; no merge issues.
- `creation_command.txt`: exact canonical build command.

Validation completed:

```text
uv run ruff format --check scripts tests
uv run ruff check scripts tests
uv run pytest tests/test_merge_planet8b_regions.py \
  tests/test_validate_planet8b_raw_merge.py  # 13 passed
full-source dry run                         # 369 planned pairs
three-pair CA/ca_011/BC raster smoke       # 3 passed
full streamed raster QA                    # 369 passed
temporal split reconciliation              # 369 joined exactly once
copy verification                          # 369 checksum/inode passes
nonempty-root rerun                         # refused safely
task-scoped pre-commit                      # all hooks passed
git diff --check                            # passed
```

Repository-wide Ruff remains blocked by two pre-existing unused-loop-variable
findings and formatting drift in legacy SKEMA notebooks outside the active
project. The all-files pre-commit pass otherwise completed but proposed only an
unrelated final newline in historical `planet8b_image_splits.csv`; that
incidental change was removed. All intended Task 002 files passed the complete
pre-commit hook set.

There are no unresolved Task 002 issues. The provisional unaligned hard-link
root was removed after the independent copied dataset passed full QA; raw
sources and the historical merge were not modified.

Task 003 must use these exact inputs:

```text
raw root:        /Volumes/x10pro/kelpseg/merged_all_regions_v1
raster manifest: <raw-root>/raster_manifest.csv
raster metadata: <raw-root>/raster_metadata.csv
QA summary:      <raw-root>/raster_qa_summary.json
alignment QA:    <raw-root>/label_alignment.csv
label classes:   0, 1, 2, 3; class 3 is raw-raster nodata
image nodata:    all eight bands equal zero
```

The exact next action is to open Task 003, obtain the recorded user decision on
overlap-aware TIFF reconstruction, then implement the fixture-only chipper and
chip-manifest changes without running the full 369-TIFF chip job.
