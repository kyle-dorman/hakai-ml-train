# Task 009: Package the portable canonical dataset archive

Status: Complete

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

Decision (2026-07-20): use the recommended archive directory and versioned
name, `/Volumes/x10pro/kelpseg/archives` and
`planet8b_all_regions_1024_512_v1.zip`. Include compact CSV/JSON/Markdown QA
and provenance evidence, exclude large QA/contact-sheet images, and keep the
ZIP format fixed by the user.

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

## Outcome

Task 009 created the approved versioned portable archive and adjacent checksum
sidecar:

```text
/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip
/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip.sha256
```

The ZIP is 44,917,177,439 bytes (41.832381 GiB) and has SHA-256
`6640757c19d803a000834b34abdb20c71a5359e215e8edf08b4958123c4ab098`.
It contains one root named `planet8b_all_regions_1024_512_v1` and 4,653 file
members. The payload is 4,637 canonical NPZ chips totaling 44,912,049,410
bytes, nine portable manifests totaling 3,011,141 bytes, six compact metadata
files totaling 134,905 bytes, and the 669,229-byte inventory itself.

`metadata/archive_inventory.csv` has 4,652 rows and SHA-256
`a07d8326a8b3946907aeb04c0fac042e714a7c226b96c24d6f93302c33f01fbc`.
It records the relative path, byte size, file kind, and SHA-256 for every other
archive member, including every NPZ. The inventory excludes only itself to
avoid a recursive self-hash; the archive sidecar protects the ZIP and the
inventory file together.

The portable layout includes the active chip, raster, raster-metadata,
temporal-split, nodata-removal, training-selection, and compact audit
manifests. It also includes dataset parameters, current chip and raster QA
summaries, portable nodata-filter metadata, a dataset README, and an optional
local raster-path provenance CSV. Active `chip_path` values were rewritten
from `all/*.npz` to `chips/all/*.npz`. Runtime raster metadata and manifests do
not require any absolute path; the original local raster paths are isolated in
the explicitly optional provenance CSV.

The exact production packaging command was:

```bash
caffeinate -i uv run python scripts/package_planet8b_dataset.py package \
  --chip-root /Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1 \
  --raster-root /Volumes/x10pro/kelpseg/merged_all_regions_v1 \
  --temporal-split planet8b_temporal_image_splits.csv \
  --archive /Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip \
  --dataset-version 1024_512_v1 \
  --producer-git-commit 5d22dc38330d0bebf5848ec7080b95f4169348a1 \
  --producer-worktree-dirty
```

The packager first built
`/Volumes/x10pro/kelpseg/archives/staging/planet8b_all_regions_1024_512_v1`
with same-volume hard links for the immutable NPZ payload, portable rewritten
manifests, and generated compact metadata. It refused symlinks, undeclared
file types, raw TIFFs, checkpoints, W&B paths, traversal paths, missing joins,
partial selections, and output overwrites. It used `ZIP_STORED` because the
NPZ payloads are already compressed and enabled ZIP64 for the total size.

The exact independent clean-extraction verification command was:

```bash
caffeinate -i uv run python scripts/package_planet8b_dataset.py verify \
  --archive /Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip \
  --checksum-file /Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip.sha256 \
  --extraction-parent /Volumes/x10pro/kelpseg/archives/.verify_planet8b_all_regions_1024_512_v1 \
  --sample-count 12 \
  --staging-root /Volumes/x10pro/kelpseg/archives/staging/planet8b_all_regions_1024_512_v1 \
  --cleanup-extraction \
  --cleanup-staging
```

Verification passed the outer checksum and safe-member checks, extracted all
members to a new root, and re-hashed all 4,652 inventoried payloads. The active
manifest resolved exactly 4,637 extracted NPZs and joined one-to-one to the
training selector. All 367 active source TIFF IDs joined through the 369-row
raster manifest, raster metadata, and temporal split; every source had shape,
CRS, affine transform, and bounds. Twelve deterministic NPZ samples matched
their manifest keys, shapes, dtypes, class counts, ignore counts, and nodata
counts. The staging and verification roots were deliberately removed only
after all checks passed. The source active manifest remained unchanged at
SHA-256 `edf754888dea183f12873594b546b980f350b5b4e293ff62ca7eca64a2c39a39`.

Fixture tests also proved clean portability, full verification failure for a
wrong sidecar checksum, internal-inventory failure for a deliberately changed
member even after recomputing the outer checksum, symlink refusal, and output
overwrite refusal. Large removal-analysis images, contact sheets, raw TIFFs,
historical chip collections, checkpoints, W&B directories, and materialized
baseline/LORO views were excluded.

Final repository validation passed with three focused packaging tests, all 45
repository tests, Ruff format and lint over `scripts`, `src`, and `tests`,
pre-commit over every Task 009 file, `git diff --check`, and relative Markdown
link validation over all changed docs. The broader repository-wide Ruff format
and lint commands remain red only on pre-existing legacy notebook formatting
and two unused `i` variables in
`notebooks/create_skema_aux_files.ipynb`; Task 009 did not modify or expand
those legacy surfaces.

Changed repository files are `scripts/package_planet8b_dataset.py`,
`tests/test_package_planet8b_dataset.py`, and the synchronized status,
artifact, routing, and task documentation. There are no unresolved Task 009
issues.

Task 010 can use this transfer template after the user supplies the SSH alias
and remote staging directory:

```bash
scp \
  /Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip \
  /Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip.sha256 \
  <ssh-alias>:<remote-staging-directory>/
ssh <ssh-alias> \
  'cd <remote-staging-directory> && sha256sum -c planet8b_all_regions_1024_512_v1.zip.sha256'
```

The exact next action is to open Task 010, obtain the remote SSH alias/user,
staging path, extracted root, compatibility path, and repo branch/commit, then
transfer and independently verify this ZIP without re-chipping or changing the
local canonical collection. Stop before Task 011.
