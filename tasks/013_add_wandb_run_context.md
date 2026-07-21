# Task 013: Add W&B run context

Status: Complete

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

Approved 2026-07-21 by proceeding with the recommended defaults in the task:

- comparison group: `planet8b-loro-v1`;
- run names: `baseline-temporal-v1` and `loro-<region_id>-v1`;
- checkpoint artifacts: upload the single best checkpoint only;
- smoke runs: use the same project and a separate `smoke` group.

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

## Implementation plan

1. Add a shared run-context module that reads the canonical dataset metadata,
   fold manifest, and fold summary; computes file hashes and selected
   split/date/region counts; and rejects identity, held-out-region, summary,
   or dataset-metadata inconsistencies.
2. Serialize the resulting JSON-compatible context with its source paths and
   hashes. Reload and revalidate that record before Lightning instantiates the
   model, data module, loggers, callbacks, or trainer, so missing or changed
   manifests fail before trainer launch.
3. Extend the existing LightningCLI entry point with one `--run_context` path.
   Inject the fixed entity/project, approved group/name, tags/job type, context
   config, fold data paths, and best-only checkpoint policy into the parsed
   config before class construction. Preserve the same injection in W&B
   offline mode.
4. At `before_fit`, log the context plus Lightning's fully resolved YAML as a
   W&B metadata artifact containing the exact fold manifest/summary and
   canonical dataset metadata. Explicitly log the sole
   `save_top_k=1`, `save_last=false` best checkpoint at run completion so the
   artifact behavior is identical in W&B online and offline modes.
5. Give Task 014 a small context-generation CLI/API: it creates one validated
   context file per planned baseline/LORO run, passes that file to `trainer.py`,
   and records its hash in the future local registry without duplicating W&B
   fields across 13 YAML files.

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

## Outcome

Completed 2026-07-21 on the Task 010 host after Task 012 published all LORO
views. The approved decisions are group `planet8b-loro-v1`, names
`baseline-temporal-v1` and `loro-<region_id>-v1`, one best checkpoint artifact,
and a separate `smoke` group with smoke-prefixed names and smoke job type/tag.
The fixed destination remains `kdorman90-ucla/kelpseg`.

Changed repository files are `src/run_context.py`,
`scripts/build_planet8b_run_context.py`, `trainer.py`,
`tests/test_run_context.py`, the two active California SegFormer configs,
`docs/experiments.md`, this task file, `AGENTS.md`, `docs/index.md`,
`docs/todo.md`, and `tasks/README.md`. Task 012's concurrent files and changes
were preserved.

The context schema contains every required identity, split count, region/date
range, filtering, chip/model, git, and host field. It also records source paths
and SHA-256 values for the dataset metadata, archive receipt, canonical chip
manifest, fold manifest/summary, and model config. Generation validates the
dataset-declared chip hash, archive receipt, selected manifest counts, fold
mode, and LORO held-out membership. `trainer.py` revalidates every source hash
before class construction, injects the exact data paths and W&B identity, and
rejects seed/logger/checkpoint-policy mismatches.

At fit start, the trainer logs the context plus resolved Lightning YAML as a
`run-metadata` artifact with the exact source metadata/manifests/config. At fit
end, it logs compact final metrics and explicitly uploads only the best
checkpoint as a model artifact with alias `best`. The configured callback is
forced to `save_top_k=1` and `save_last=false`; `WandbLogger.log_model` stays
false because its automatic upload path is incompatible with offline mode.
The explicit artifact path is identical online and offline.

Two final one-train-batch/one-validation-batch GPU smokes completed in W&B
offline mode:

- baseline run ID `9gvoc92a`, name `smoke-baseline-temporal-v1`, fold-manifest
  SHA-256 `4945e32e1cb4a29d00768ca9ae8aa523d91604516c3adc250ff2b4c0c1bed3c1`,
  under
  `/home/sky/data/planet8b_all_regions_1024_512_v2/smoke_runs/task013/final_baseline`;
- `ca_001` run ID `uwrxi436`, name `smoke-loro-ca_001-v1`, fold-manifest
  SHA-256 `b9785819079d7edc88e757338c80b1786ee85be03de1e45388c000cc7d3d552d`,
  under
  `/home/sky/data/planet8b_all_regions_1024_512_v2/smoke_runs/task013/final_loro_ca_001`.

Both offline records contain entity/project/group/name/job type, tags, hashes,
counts, filtering policy, held-out identity, resolved config, metadata
artifact, compact metrics, and a staged 536 MB best-checkpoint artifact. The
durable generated contexts are under
`/home/sky/data/planet8b_all_regions_1024_512_v2/run_contexts/task013`.

Validation passed with six focused context tests, including changed and
missing fold hashes, inconsistent counts, missing LORO held-out identity, and
offline best-only config injection; both final real-fold smokes; focused Ruff;
the complete 61-test repository suite; and `git diff --check`. Repository-wide
Ruff retains only the two Task 012-recorded legacy notebook findings outside
this task. No full training run was started.

Task 014 should generate one context beside each planned registry entry, store
the context-file hash in that entry, and launch the shared model config with
`trainer.py fit --run_context <path>`. It should not duplicate these fields or
create 13 per-fold YAML files.
