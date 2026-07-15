# Task 009: Package the portable canonical dataset archive

Status: Pending

Depends on: Tasks 007 and 008

Execution: Local packaging task.

## Abstract

Package the cleaned canonical chips and all metadata needed to reconstruct
baseline and LORO datasets remotely. The archive must be portable, inventory-
checked, and checksum-verified. It must not contain raw TIFF imagery, local
absolute path dependencies, checkpoints, or historical chip collections.

## Goal

Create one versioned ZIP archive that Task 010 can transfer and verify without
re-downloading or re-chipping data.

## Inputs

- Task 007 active chip root, chip manifest, removal evidence, and selected
  nodata threshold
- Task 008 background-selection tool and recorded policy
- Task 002 raster manifest and QA summary
- Task 002 portable `raster_metadata.csv`
- `planet8b_temporal_image_splits.csv`
- Task 004 creation parameters/summary
- `docs/data_artifacts.md`

## User decisions required

Confirm:

1. Archive output directory. Recommendation:
   `/Volumes/x10pro/kelpseg/archives`.
2. Versioned archive name. Recommendation derived from approved parameters,
   for example `planet8b_all_regions_1024_512_v1.zip`; do not include a date as
   the only version identifier.
3. Whether removal-analysis/contact-sheet artifacts should be included. Default:
   include compact CSV/JSON/Markdown evidence, exclude large QA images unless
   needed remotely.

ZIP format is already fixed by the user.

## Archive layout

```text
planet8b_all_regions_<version>/
  chips/all/*.npz
  manifests/chip_manifest.csv
  manifests/raster_manifest.csv
  manifests/raster_metadata.csv
  manifests/planet8b_temporal_image_splits.csv
  manifests/nodata_removal_manifest.csv
  manifests/background_policy.json
  metadata/dataset_parameters.json
  metadata/chip_qa_summary.json
  metadata/raster_qa_summary.json
  metadata/archive_inventory.csv
  metadata/README.md
```

All paths inside manifests required remotely must be relative to the extracted
dataset root. Preserve local provenance in separate optional columns/files, not
as required runtime paths.

## Packaging requirements

- Add a small reusable packaging/verification script if shell-only packaging
  would make inventory or path rewriting fragile.
- Inventory every archive member with relative path, byte size, and SHA-256 for
  manifests/metadata; recording every NPZ checksum is preferred if runtime is
  acceptable, otherwise record archive checksum plus NPZ count/bytes.
- Write `<archive>.sha256` beside the ZIP.
- Refuse to include symlinks, raw TIFFs, checkpoints, W&B directories, or files
  outside the declared input set.
- Preserve a staging directory until verification succeeds, then clean it
  deliberately.

## Suggested execution

1. Estimate ZIP size and confirm free space.
2. Build portable staging layout.
3. Validate all rewritten paths from the staging root.
4. Create ZIP.
5. Compute SHA-256.
6. Extract into a temporary local verification root.
7. Validate inventory, manifests, random NPZs, and checksum.

## Smoke test

Package a tiny fixture subset first and prove path portability and verification
failure on a deliberately changed member/checksum.

## Validation

- Archive checksum verifies.
- Temporary extraction contains expected chip and manifest counts.
- Active chip manifest resolves every chip relative to extraction root.
- Raster and temporal manifests join all source TIFF IDs used by chips.
- Portable raster metadata supplies source shape, CRS, transform, and bounds for
  every source TIFF without requiring raw TIFF access.
- No absolute `/Volumes/...` path is required for remote materialization.
- No raw TIFF, checkpoint, W&B directory, or historical chip root is included.
- Run focused tests/Ruff for new packaging code and `git diff --check`.

## Acceptance criteria

- Archive path, bytes, SHA-256, dataset version, and inventory counts are
  recorded in this task and `docs/data_artifacts.md`.
- A clean local extraction passes all verification.
- Task 010 needs only remote connection/destination details from the user.

## Non-goals

- Do not transfer or extract remotely.
- Do not materialize baseline/LORO folders inside the archive.
- Do not include raw merged TIFFs.
- Do not change filtering or chip parameters.

## Outcome template

Record approved name/path, staging layout, archive size/checksum, inventory and
extraction validation, excluded artifacts, scripts changed, and Task 010
transfer command template.
