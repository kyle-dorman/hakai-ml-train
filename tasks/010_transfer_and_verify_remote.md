# Task 010: Transfer and verify the canonical archive remotely

Status: Pending

Depends on: Task 009

Execution: Local-to-remote transfer plus remote verification.

## Abstract

Transfer the verified canonical ZIP to the selected GPU machine, confirm the
checksum before extraction, and prove that the portable manifests resolve in
the remote filesystem. This task ends with one recorded remote canonical data
root. It does not materialize experimental folds or launch training.

## Goal

Create a byte-verified remote copy of the Task 009 dataset that Tasks 011–019
can use without accessing the local external drive.

## Inputs

- Task 009 archive, `.sha256`, inventory, archive version, and verification
  command
- `scripts/bootstrap_skypilot.sh`
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

## Transfer contract

- Prefer `rsync --partial --progress` when available so interrupted large
  transfers can resume; otherwise use `scp`.
- Transfer both ZIP and checksum file.
- Do not redownload the original CA/BC source archives.
- Do not trust transfer completion until the remote SHA-256 matches.
- Preserve the local archive until the remote extraction and inventory verify.

## Suggested command shape

```bash
rsync --partial --progress \
  <archive.zip> <archive.zip.sha256> \
  <user>@<host>:<remote-staging>/

ssh <user>@<host>
cd <remote-staging>
sha256sum -c <archive.zip.sha256>
unzip -q <archive.zip> -d <remote-data-parent>
```

Use `shasum -a 256` if the remote platform lacks `sha256sum`, and record the
exact command.

## Remote verification

- Extracted file count and total uncompressed bytes match Task 009 inventory.
- Canonical chip count matches the active chip manifest.
- Every relative `chip_path` resolves from the documented dataset root.
- Raster, raster-metadata, and temporal manifests exist and join all chip source
  IDs; raster metadata provides source shape/georeferencing without raw TIFFs.
- Open at least five stratified NPZs: CA old region, CA newly included region,
  BC, high-nodata retained chip, and positive-class chip.
- Verify image/label shapes, dtypes, and manifest counts for those samples.
- Run the archive verification helper from Task 009 if one exists.
- Confirm free disk space after extraction.

## Bootstrap boundary

Run `scripts/bootstrap_skypilot.sh` only as needed to establish Python 3.12,
dependencies, CUDA checks, and W&B login. Do not let its historical archive
defaults extract or overwrite an older dataset. Pass explicit current archive
and extraction arguments or update the script in a separate bounded correction
if it cannot safely handle the new archive.

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

- Remote checksum equals Task 009 checksum.
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
