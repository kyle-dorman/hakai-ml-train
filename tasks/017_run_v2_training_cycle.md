# Task 017: Run the complete v2 training cycle

Status: Current; ready for user launch

Depends on: Tasks 014–016

Execution: User-executed remote training; agent verification/check-in afterward.

## Abstract

Run a clean `planet8b-loro-v2` production cycle containing the temporal
baseline and all 12 leave-one-region-out folds. V2 supersedes the partial v1
production suite as the comparison set because every v2 fit logs held-out
diagnostics after each epoch under `test/current/`, while the final
validation-selected checkpoint is evaluated under `test/best/`.

The user launches and monitors training. On follow-up, the agent audits the
registry, logs, W&B runs, checkpoints, and failure state; it does not start or
resume training unless the user explicitly asks.

## Goal

Finish one baseline and 12 comparable LORO v2 runs with consistent model,
budget, fold identity, per-epoch diagnostics, validation-only checkpoint
selection, and verified best/local-last checkpoints.

## Inputs

- `configs/kelp-ps8b/generalization/experiment_matrix_v2.yaml`
- `configs/kelp-ps8b/generalization/segformer_b3_v1.yaml`
- `scripts/run_planet8b_experiments.py`
- Task 016 v2 dry-run validation and stopped v1 handoff
- Task 011 baseline and Task 012 LORO materialized views
- Canonical v2 dataset at
  `/home/sky/data/planet8b_all_regions_1024_512_v2`

## Fixed identity and policy

```text
experiment version / W&B group: planet8b-loro-v2
smoke version: planet8b-loro-v2-smoke-tiered-ema-v1
experiment root: /home/sky/experiments/planet8b-loro-v2
registry: /home/sky/experiments/planet8b-loro-v2/experiment_registry.jsonl
baseline: baseline-temporal-v2
LORO: loro-<region_id>-v2
seed: 42
epochs: 100
micro-batch: 3
gradient accumulation: 8
effective batch: 24
checkpoint monitor: val/iou_epoch
```

Each epoch evaluates the complete materialized test split and logs its metrics
under `test/current/*`. These metrics are diagnostic only and must not select
checkpoints, alter later folds, or tune model/preprocessing policy. The runner
tests the validation-selected best checkpoint at fit end under `test/best/*`
before marking the run complete.

The v1 registry, checkpoints, logs, and W&B runs are immutable historical
evidence. Do not resume, delete, overwrite, or relabel them.

## User decisions required

None. The user explicitly chose a clean v2 restart including the baseline and
will execute training. The approved order is:

1. `baseline-temporal-v2`;
2. `loro-ca_006-v2` as the first LORO gate;
3. `loro-bc-v2`;
4. `loro-ca_001-v2`–`loro-ca_005-v2`;
5. `loro-ca_007-v2`–`loro-ca_011-v2`.

Do not change model, seed, budget, filtering, evaluation cadence, or checkpoint
policy per fold.

## Launch

Launch and verify the baseline first:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v2.yaml \
  --run baseline-temporal-v2
```

After baseline verification, launch the first LORO gate explicitly if a pause
is desired:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v2.yaml \
  --run loro-ca_006-v2
```

Then run the remaining queue:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v2.yaml \
  --pending
```

The user may instead use `--pending` immediately after baseline verification;
the matrix order still begins with `ca_006`.

## Per-run preflight and closeout

- Registry has no completed v2 state for the run key.
- Fold manifest hash/counts agree with W&B run context.
- Baseline/LORO split identity and held-out-region exclusions validate.
- Resolved config records `test_every_val_epoch = true`.
- W&B group/name/tags use only v2 identity.
- `test/current/iou_epoch` is present across completed epochs.
- `val/iou_epoch` remains the checkpoint monitor.
- Exactly one best checkpoint plus local `last.ckpt` exists.
- Final `test/best/iou_epoch` comes from the recorded best checkpoint.
- Registry marks completion only after the final best-checkpoint test succeeds.

## Failure and resume policy

- Preserve failed and interrupted attempts in the registry.
- Use `last.ckpt` only through the runner's validated single-run resume path.
- Do not reuse a v1 checkpoint or W&B run ID.
- Pause on identity, data, checkpoint, GPU, disk, or repeated operational
  failures.
- Do not restart a completed v2 entry merely because a later run fails.

## Validation

Suite audit:

```text
run_key,run_type,held_out_region,status,attempts,wandb_run_id,
fold_manifest_sha256,best_checkpoint,best_checkpoint_sha256,best_epoch,
best_val_metric,test_chip_count,current_test_metric_count,
final_best_test_present,error_summary
```

Required checks:

- exactly 13 completed v2 run keys: one baseline and 12 regions;
- no v2 output or registry event uses a v1 run/group/version identity;
- all runs share model-config hash, seed, 100-epoch budget, and batch policy;
- every completed fit has an epochwise `test/current/` trajectory;
- checkpoint selection uses validation only;
- every run has a final `test/best/` result tied to its best checkpoint;
- baseline and LORO fold/checkpoint identities agree with manifests and W&B;
- a completed-suite `--pending --dry-run` reports only skips/no work.

Run relevant focused tests/Ruff and `git diff --check` for any corrective code
change. Training execution itself does not authorize unplanned code changes.

## Acceptance criteria

- The v2 baseline and all 12 v2 LORO entries genuinely complete, or the task
  remains in progress with exact resumable state.
- Registry, W&B, fold manifests, checkpoints, and metric namespaces agree.
- No test-driven checkpoint selection or fold-specific tuning occurred.
- Task 018 can use the completed v2 baseline for evaluator development.
- Task 019 can enumerate all 13 completed v2 checkpoints mechanically.

## Non-goals

- Do not compare model accuracy yet.
- Do not build or run the prediction evaluator.
- Do not tune using held-out test trajectories.
- Do not add architectures, seeds, or folds.
- Do not delete the partial v1 suite.

## Outcome template

Record exact launch commands, per-run registry/W&B/checkpoint identities,
epochwise-current and final-best metric evidence, failures/retries, runtime and
compute notes, suite consistency audit, unresolved/resume state, and exact
Task 018 handoff.
