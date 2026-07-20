# Task 010: Transfer and verify the canonical archive remotely

Status: Complete

Depends on: Task 009A

Execution: Local-to-remote transfer plus remote verification.

## Abstract

Transfer the verified canonical ZIP to the selected GPU machine, confirm the
checksum before extraction, and prove that the portable manifests resolve in
the remote filesystem. This task ends with one recorded remote canonical data
root. It does not materialize experimental folds or launch training.

## Goal

Create a byte-verified remote copy of the Task 009A v2 dataset that Tasks 011–019
can use without accessing the local external drive.

## Inputs

- Task 009A v2 archive, `.sha256`, inventory, archive version, and verification
  command
- `scripts/bootstrap_skypilot.sh`
- `scripts/prepare_remote_planet8b_dataset.sh`
- `docs/data_artifacts.md`
- Remote repo checkout or clone URL/branch

## User decisions required

Provide or confirm at the start of this task:

1. Remote hostname or SSH alias.
2. Remote SSH user.
3. Archive upload directory.
4. Final extracted data root.
5. Whether this is a disposable SkyPilot instance and whether
   `/home/taylor/data` compatibility is required.
6. Whether the repo is already cloned and which branch/commit should be used.

Recommendation: upload to the remote user's home or a staging volume, extract
under the persistent/high-capacity data root, and create a compatibility symlink
only if configs still require it.

Record exact values here before transfer. Do not put credentials or W&B keys in
the task file.

Confirmed values:

- Remote SSH alias: `sky-dad6-kyledorman`
- Remote SSH user: `sky`
- Instance lifecycle: disposable SkyPilot host
- Remote repo: `/home/sky/hakai-ml-train`, clean `main` at `a65a0ee` before the
  dataset-preparation change
- Archive staging directory: `/home/sky/dataset-staging`
- Extracted data root: `/home/sky/data/planet8b_all_regions_1024_512_v2`

The `/home/taylor/data` compatibility link is not required for the canonical
archive; later view/config tasks can add it only if their selected paths need
it.

## Transfer contract

- Download both approved Google Drive objects directly on the remote host;
  preserve a `.partial` file so the 44.9 GB ZIP can resume after interruption.
- Refuse completed files whose exact byte counts differ from Task 009A.
- Do not redownload the original CA/BC source archives.
- Do not trust transfer completion until the remote SHA-256 matches.
- Preserve the local archive until the remote extraction and inventory verify.

## Transfer command

```bash
scripts/prepare_remote_planet8b_dataset.sh --download-missing
```

The script downloads only missing files from the two approved Google Drive
objects, resumes an interrupted `.partial` download, validates exact byte
counts and the approved checksum sidecar, and delegates extraction plus full
inventory/manifest validation to `scripts/package_planet8b_dataset.py verify`.

## Remote verification

- Extracted file count and total uncompressed bytes match Task 009A inventory.
- Canonical chip count matches the active chip manifest.
- Every relative `chip_path` resolves from the documented dataset root.
- Raster, raster-metadata, and temporal manifests exist and join all chip source
  IDs; raster metadata provides source shape/georeferencing without raw TIFFs.
- Open at least five stratified NPZs: CA old region, CA newly included region,
  BC, high-nodata retained chip, and positive-class chip.
- Verify image/label shapes, dtypes, and manifest counts for those samples.
- Run the archive verification helper updated by Task 009A.
- Confirm free disk space after extraction.

## Bootstrap boundary

Run `scripts/bootstrap_skypilot.sh` only to establish Codex, Python 3.12,
dependencies, CUDA checks, and W&B login. Dataset download, verification, and
extraction belong exclusively to `scripts/prepare_remote_planet8b_dataset.sh`;
the bootstrap has no archive defaults or extraction behavior.

## Validation

Record:

```text
remote hostname (non-secret alias), repo commit, archive SHA-256,
staging path, extracted root, chip count, manifest count, random NPZ checks,
free disk, CUDA/PyTorch status
```

Any bootstrap code change runs focused shell/static checks and
`git diff --check`.

## Acceptance criteria

- Remote checksum equals the Task 009A v2 checksum.
- Extracted inventory and manifests validate without local absolute paths.
- The canonical remote dataset root is recorded in this task,
  `docs/data_artifacts.md`, and `docs/todo.md`.
- No baseline/LORO view or training run has started.
- Task 011 can execute using only recorded remote paths.

## Non-goals

- Do not regenerate or filter chips remotely.
- Do not materialize experiment folds.
- Do not edit model hyperparameters or W&B organization.
- Do not launch training.

## Outcome template

Record connection alias, repo commit, exact transfer/checksum/extraction
commands, remote roots, inventory validation, bootstrap changes, issues, and
Task 011 inputs. Omit secrets.

## Outcome

Task 010 completed on the disposable SkyPilot host reached through
`sky-dad6-kyledorman` as user `sky`. The remote checkout was clean `main` at
`a65a0ee` before the Task 010 dataset-preparation changes were copied in for
execution.

Changed repository files:

- `scripts/bootstrap_skypilot.sh` is environment-only and no longer references
  or extracts the historical tar archive.
- `scripts/prepare_remote_planet8b_dataset.sh` owns resumable download of the
  approved v2 Drive objects, exact-size and sidecar checks, transactional clean
  extraction, full archive verification, and idempotent completion detection.
- `README.md`, `docs/data_artifacts.md`, `docs/todo.md`, `tasks/README.md`, and
  this task record the separated workflow and remote result.

The exact remote command was:

```bash
cd /home/sky/hakai-ml-train
scripts/prepare_remote_planet8b_dataset.sh --download-missing
```

Durable external artifacts:

```text
staging ZIP: /home/sky/dataset-staging/planet8b_all_regions_1024_512_v2.zip
checksum:    /home/sky/dataset-staging/planet8b_all_regions_1024_512_v2.zip.sha256
dataset:     /home/sky/data/planet8b_all_regions_1024_512_v2
receipt:     /home/sky/data/planet8b_all_regions_1024_512_v2/metadata/remote_archive_verification.log
```

Validation:

- Exact remote ZIP size: `44,859,496,084` bytes.
- Remote SHA-256:
  `1244ecfe2cc4cee624bb5661087f0126ea239367bda60efd823b4fcb9b7399db`.
- The archive verifier passed 4,623 inventory rows, 4,602 NPZs totaling
  44,854,174,488 bytes, 367 represented source TIFFs, 12 sampled reused hashes,
  all fresh hashes, portable paths, and source/chip manifest joins.
- `chip_manifest.csv` has 4,602 rows; raster manifest, raster metadata, and
  temporal split each have the same 369 source rows.
- Five explicit NPZ checks passed for `ca_001`, newly included `ca_006`, `bc`,
  the maximum retained nodata chip at `49.95565414428711%`, and a distinct
  positive-class chip. All five matched manifest shape, `uint16` image dtype,
  `int64` label dtype, and class counts.
- An idempotent rerun reported the dataset already extracted and verified.
- Final free space was 682 GB. CUDA passed with one NVIDIA A40, PyTorch
  `2.12.0+cu130`, and CUDA 13.0 visibility.
- Focused shell parsing, help, refusal-path, and remote execution checks passed;
  `git diff --check` passed. Repository-wide Ruff remains blocked only by two
  pre-existing unused-loop-variable findings and formatting differences in
  `notebooks/create_skema_aux_files.ipynb`.

No compatibility symlink was created, no baseline/LORO view was materialized,
and no training run started. There are no unresolved Task 010 data issues. The
exact next action is Task 011 using the canonical dataset root above and an
explicit user-approved baseline view root.
