# Task 014A: Move the experiment environment to a replacement GPU machine

Status: Pending

Depends on: Tasks 010–013

Execution: Replacement-host environment, data-transfer, and data-view task; no
training.

## Abstract

The original Task 010 host lost its A40 while Task 014 was running the
production-like smoke suite. Re-establish the verified v2 canonical dataset,
baseline view, all 12 LORO views, locked Python environment, W&B access, and a
healthy CUDA runtime on a replacement machine. This task ends at a dry-run of
the 13-entry runner. Task 014 then restarts its one-epoch smoke suite with fresh
runtime state.

## Goal

Make the replacement host equivalent to the validated Task 010–013 host at the
data, fold, environment, and service boundaries without treating files from
the failed host as current experiment state.

## Inputs

- Repository branch/commit containing the in-progress Task 014 runner and
  experiment matrix
- `scripts/bootstrap_skypilot.sh`
- `scripts/prepare_remote_planet8b_dataset.sh`
- `scripts/materialize_planet8b_folds.py`
- Task 009A v2 archive identity:
  - exact size: `44,859,496,084` bytes
  - SHA-256:
    `1244ecfe2cc4cee624bb5661087f0126ea239367bda60efd823b4fcb9b7399db`
- Canonical manifests inside the extracted archive
- Task 011 baseline and Task 012 LORO materialization policies
- Task 013 W&B destination and run-context contract
- Task 014 matrix and runner CLI

## User decisions required

Provide or confirm before execution:

1. Replacement host SSH alias/user and whether it is disposable.
2. Repository checkout path and exact branch/commit to deploy.
3. Staging, canonical data, and experiment roots.
4. Whether the old host's experiment directory is recoverable for read-only
   evidence.

Recommended paths, if the replacement host also uses user `sky`:

```text
repo:            /home/sky/hakai-ml-train
archive staging: /home/sky/dataset-staging
canonical data:  /home/sky/data/planet8b_all_regions_1024_512_v2
experiment root: /home/sky/experiments/planet8b-loro-v1
```

Use the existing Google Drive download IDs embedded in the preparation script.
Do not require recovery of the failed host to proceed: the completed historical
smoke is already recorded in W&B, and the interrupted local registry is
evidence rather than an input to the new smoke suite.

## Replacement-host contract

1. Record the replacement hostname, GPU model, storage capacity, repo
   branch/commit, and resolved roots. Ensure capacity for the approximately
   45 GB archive, approximately 45 GB extraction, hard-link views, environment,
   logs, and checkpoints.
2. Bootstrap Python 3.12 and install the locked environment with `uv`. Verify
   the checkout includes the Task 014 runner and matrix before data work.
3. Download only the approved v2 ZIP and checksum sidecar. Preserve resumable
   `.partial` behavior, require the exact byte count and SHA-256 above, perform
   a clean transactional extraction, and retain the verification receipt.
4. Re-run baseline and LORO materialization from the canonical manifests. Use
   dry-run first, then hard-link mode. Never copy or regenerate canonical NPZs.
   Keep the canonical root and view roots on the same filesystem and verify
   their device IDs before apply; hard links cannot cross filesystem boundaries.
5. Independently verify manifest/link cardinality, source/destination inode
   equality, split isolation, and one loadable batch from every materialized
   split.
6. Verify W&B login for `kdorman90-ucla/kelpseg` without recording credentials.
7. Require a healthy CUDA/PyTorch preflight and a bounded sustained-load check.
   Record GPU temperature, clocks, power, utilization, and driver health before
   and after; stop on thermal throttling, Xid errors, device loss, or CUDA
   visibility changes.
8. Dry-run all 13 Task 014 entries. Do not launch training in this task.

## Exact data commands

From the replacement checkout, prepare and verify the canonical archive:

```bash
scripts/prepare_remote_planet8b_dataset.sh \
  --download-missing \
  --staging-dir /home/sky/dataset-staging \
  --data-parent /home/sky/data
```

Dry-run and then apply the baseline view; omit `--dry-run` only after review:

```bash
uv run python scripts/materialize_planet8b_folds.py baseline \
  --chip-root /home/sky/data/planet8b_all_regions_1024_512_v2 \
  --chip-manifest /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/chip_manifest.csv \
  --temporal-splits /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/planet8b_temporal_image_splits.csv \
  --background-selection /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/training_selection.csv \
  --output-root /home/sky/data/planet8b_all_regions_1024_512_v2/views/baseline_temporal_v1 \
  --mode hardlink \
  --dry-run
```

Dry-run and then apply all LORO views; omit `--dry-run` only after review:

```bash
uv run python scripts/materialize_planet8b_folds.py loro \
  --chip-root /home/sky/data/planet8b_all_regions_1024_512_v2 \
  --chip-manifest /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/chip_manifest.csv \
  --temporal-splits /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/planet8b_temporal_image_splits.csv \
  --background-selection /home/sky/data/planet8b_all_regions_1024_512_v2/manifests/training_selection.csv \
  --output-root /home/sky/data/planet8b_all_regions_1024_512_v2/views/loro_v1 \
  --held-out-region all \
  --mode hardlink \
  --dry-run
```

If different approved roots are selected, substitute them consistently in the
commands and Task 014 matrix. Do not create compatibility symlinks implicitly.

## Runtime-state policy

- Do not copy the failed host's registry, resolved configs, checkpoints, or
  logs into the replacement experiment root as active state.
- If recovered, preserve them under a clearly named read-only migration-history
  directory and record their origin. W&B run `8f4268b3` and the interrupted v2
  attempt remain historical evidence.
- Task 014 must start a fresh smoke registry/output namespace and use a new
  smoke experiment identity (recommended next suffix: `v3`) so the replacement
  host runs all 13 entries as one coherent suite.
- Production state remains isolated from every smoke namespace.

## Smoke and validation

Expected data evidence:

- canonical dataset: 4,602 NPZs from 367 represented source TIFFs;
- baseline view: 2,565 selected hard links;
- LORO parent: 12 folds and 27,508 selected hard links;
- total view links: 30,073, all inode-equal to canonical NPZs;
- baseline DataModule: one batch from train, validation, and test;
- LORO DataModules: one batch from all 36 fold/split combinations;
- archive verification receipt exists and records the approved checksum;
- all 13 runner dry-runs resolve the replacement-host paths and correct fold
  hashes.

Repository validation for any documentation-only closing edits:

```bash
git diff --check
```

If code must change for host portability, run its focused tests plus:

```bash
uv run ruff format --check .
uv run ruff check .
```

## Acceptance criteria

- The replacement host and exact repo commit are recorded.
- The approved v2 archive is downloaded, checksum/inventory verified, and
  extracted at one recorded canonical root.
- The baseline and all 12 LORO views are rematerialized from manifests and all
  30,073 hard links pass independent inode/cardinality checks.
- The locked environment, W&B login, CUDA visibility, and bounded GPU health
  check pass without thermal or driver warnings.
- All 13 Task 014 entries dry-run against the replacement roots.
- No training or one-epoch experiment smoke has started.
- Task 014 has an exact clean-restart command and fresh smoke identity.

## Non-goals

- Do not regenerate chips from source TIFFs.
- Do not change split, nodata, background-selection, model, or epoch policy.
- Do not launch the Task 014 smoke or Tasks 015–016 production training.
- Do not infer completion from data copied from the failed host.
- Do not delete historical W&B runs or any recoverable failed-host evidence.

## Review pass

- Risk-averse engineer: verify archive identity, transactional extraction,
  inode checks, storage headroom, and refusal of ambiguous old runtime state.
- ML systems engineer: verify the CUDA sustained-load gate, resolved paths, and
  fresh smoke/production namespace isolation.

## Outcome template

Record replacement connection alias, repo branch/commit, GPU/driver/PyTorch
identity, roots, exact preparation and materialization commands, archive
receipt/checksum, link and DataModule audits, W&B and GPU preflight evidence,
runner dry-run result, any recovered historical artifacts, unresolved issues,
and the exact Task 014 restart command.
