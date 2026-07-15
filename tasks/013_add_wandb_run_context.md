# Task 013: Add W&B run context

Status: Pending

Depends on: Tasks 011 and 012

Execution: Remote-aware code/config task; only smoke runs are allowed.

## Abstract

Make baseline, LORO, and prediction runs understandable in W&B while they are
running. Normalize the active PS8B tracking destination, select a user-approved
group and naming contract, and ensure manifests, dataset counts, fold identity,
git state, and filtering policies are logged consistently. The local resumable
run registry and multi-run execution belong to Task 014.

## Goal

Provide one reusable run-context builder/injection path rather than manually
editing W&B fields in 13 YAML copies.

## Inputs

- `docs/experiments.md`
- Task 011 baseline fold manifest/summary
- Task 012 LORO fold manifests/summaries
- `configs/kelp-ps8b/california/segformer_b3.yaml`
- `configs/kelp-ps8b/california/segformer_b3_remote_1epoch.yaml`
- `trainer.py`
- Lightning `WandbLogger` version installed by `uv.lock`

## Fixed W&B destination

```text
entity: kdorman90-ucla
project: kelpseg
```

Do not copy identity or grouping from legacy configs.

## User decisions required

Confirm:

1. W&B group for the complete comparison suite. Recommendation:
   `planet8b-loro-v1`; use a stable semantic version, not only a date.
2. Run-name form. Recommendation:
   `baseline-temporal-v1` and `loro-<region_id>-v1`.
3. Checkpoint artifact policy. Options:
   - upload best checkpoint only (recommended for 13 full runs);
   - upload best plus last;
   - retain checkpoints remotely and log path/hash only.
4. Whether smoke runs belong in the same group with `smoke` job type/tag or a
   separate group. Recommendation: same project, separate `smoke` group.

Record decisions in this task and `docs/experiments.md` before implementation.

## Required run context

W&B config/summary or artifact metadata must include:

```text
experiment_version,run_type,fold_id,held_out_region,dataset_version,
archive_sha256,chip_manifest_sha256,fold_manifest_sha256,
train_tiff_count,val_tiff_count,test_tiff_count,
train_chip_count,val_chip_count,test_chip_count,
train_regions,val_regions,test_regions,
train_date_range,val_date_range,test_date_range,
nodata_threshold_pct,background_policy,chip_size,chip_stride,
num_bands,image_dtype,label_remap,ignore_index,
model_config_path,seed,git_commit,git_dirty,hostname
```

Use JSON-compatible values. Large region/count tables belong in manifest
artifacts, not flattened into hundreds of config keys.

## Artifact contract

For each training run, log or reference:

- resolved run config;
- exact fold manifest and summary;
- canonical dataset metadata and manifest hashes;
- best checkpoint according to approved policy;
- compact final metrics/summary.

Use W&B artifacts/tables for portable metadata. Do not upload canonical NPZ
chips solely for tracking.

## Implementation requirements

- Verify actual `WandbLogger` API from the locked Lightning version before
  choosing CLI/config injection.
- Prefer a small shared run-context helper and generated/resolved per-run config
  over hand-edited copies.
- Fold identity and hashes must come from files, not a run-name parser.
- Dirty git state is logged explicitly; do not silently claim a clean commit.
- Offline mode must preserve the same metadata for later sync.
- Prediction runs later reuse the same group/fold/checkpoint identity.

## Plan / spec requirement

Add an implementation plan describing the W&B injection point, resolved-config
artifact, hash computation, checkpoint upload behavior, offline behavior, and
how Task 014 consumes the helper.

## Smoke test

Run a fast-dev or one-batch baseline smoke and one `ca_001` LORO smoke. Verify
in W&B (or offline run files if network is unavailable): destination, group,
name, tags/job type, held-out region, counts, hashes, config artifact, and
checkpoint policy.

## Validation

- Unit-test context generation from fixture fold summaries/manifests.
- Verify wrong/missing manifest hash, missing held-out region, or inconsistent
  counts fail before trainer launch.
- Run focused Ruff/pytest and `git diff --check`.
- Manually inspect the two smoke runs in W&B when online.

## Acceptance criteria

- Correct entity/project and user-approved group/names are used.
- Baseline and LORO smoke runs are distinguishable without reading console logs.
- Dataset/fold identity and filtering context are visible and artifact-backed.
- Checkpoint policy is explicit and tested.
- No full training run has started.

## Non-goals

- Do not build the multi-run registry/runner.
- Do not launch full baseline or LORO training.
- Do not compare models or log prediction tables yet.
- Do not normalize every legacy config in the repo.

## Review pass

- ML researcher: verify run context captures experimental comparability.
- Risk-averse engineer: verify hashes, dirty-state reporting, and offline
  behavior prevent ambiguous runs.

## Outcome template

Record user decisions, implementation files, final metadata/artifact schema,
smoke run IDs/URLs or offline paths, checkpoint behavior, validation, and Task
014 integration instructions.
