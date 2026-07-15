# Task 002: Create and validate the raw merged dataset

Status: Pending

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

Before the full run, confirm the canonical output root. Recommendation:

```text
/Volumes/x10pro/kelpseg/merged_all_regions_v1
```

Also confirm whether to use hard links as recommended. Copy mode is only needed
if the output moves to another filesystem.

Record both decisions in this task before execution.

## Execution plan

1. Check free space and source mount health.
2. Run the full dry-run and save its console summary.
3. Review `merge_issues.csv`; stop on any fatal issue.
4. Run the real organizer once into an empty versioned root.
5. Validate every image/label pair with Rasterio.
6. Write `raster_qa.csv` and `raster_qa_summary.json` beside the manifest.
7. Reconcile the manifest to `planet8b_temporal_image_splits.csv` by
   `source_tiff_id`; every temporal-split row must match exactly one merged row.

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
<canonical-raw-root>/raster_qa.csv
<canonical-raw-root>/raster_metadata.csv
<canonical-raw-root>/raster_qa_summary.json
<canonical-raw-root>/creation_command.txt
```

The summary must include counts by dataset, region, acquisition year, image
dtype, label dtype, image band count, label-value set, and QA status.

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
- Every merged file exists and is linked/copied from the recorded source.
- Every split CSV row joins exactly once; no merged row lacks a recognized
  region/date.
- QA has no unresolved error status.
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

Record the canonical path, creation command, link/copy mode, counts, QA summary,
label values, image dtype/range, exceptions, validation, and exact Task 003
inputs.
