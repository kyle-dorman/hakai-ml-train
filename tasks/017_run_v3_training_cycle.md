# Task 017: Run the complete v3 training cycle

Status: Current; v3 baseline ready for user launch

Depends on: Tasks 014–016

Execution: User-executed remote training; agent verification/check-in afterward.

## Abstract

Run a clean `planet8b-loro-v3` production cycle containing the temporal
baseline and all 12 leave-one-region-out folds. V3 supersedes the stopped v2
baseline attempt and partial v1 production suite because every v3 fit uses the
approved 70-epoch budget and `3e-5` LR floor and logs held-out
diagnostics after each epoch under `test/current/`, while the final
validation-selected checkpoint is evaluated under `test/best/`.

The user launches and monitors training. On follow-up, the agent audits the
registry, logs, W&B runs, checkpoints, and failure state; it does not start or
resume training unless the user explicitly asks.

## Goal

Finish one baseline and 12 comparable LORO v3 runs with consistent model,
budget, fold identity, per-epoch diagnostics, validation-only checkpoint
selection, and verified best/local-last checkpoints.

## Inputs

- `configs/kelp-ps8b/generalization/experiment_matrix_v3.yaml`
- `configs/kelp-ps8b/generalization/segformer_b3_v3.yaml`
- `scripts/run_planet8b_experiments.py`
- Task 016 v2 dry-run validation and stopped v1 handoff
- Task 011 baseline and Task 012 LORO materialized views
- Canonical v2 dataset at
  `/home/sky/data/planet8b_all_regions_1024_512_v2`

## Fixed identity and policy

```text
experiment version / W&B group: planet8b-loro-v3
smoke version: planet8b-loro-v3-smoke-tiered-ema-v1
experiment root: /home/sky/experiments/planet8b-loro-v3
registry: /home/sky/experiments/planet8b-loro-v3/experiment_registry.jsonl
baseline: baseline-temporal-v3
LORO: loro-<region_id>-v3
seed: 42
epochs: 70
peak LR: 0.0003
minimum LR: 0.00003
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

The v1 and v2 registries, checkpoints, logs, and W&B runs are immutable
historical evidence. Do not resume, delete, overwrite, or relabel them. The v2
baseline attempt `3ffe42b7` was interrupted after epoch 66; no v2 LORO run was
started.

## User decisions required

None. On 2026-07-31, after reviewing the active v2 and completed v1 baseline
curves, the user stopped v2 and approved a clean v3 restart. The v1 best IoU
through 70 epochs was 0.70883 versus 0.70966 through 100 epochs, so the uniform
70-epoch budget accepts a 0.00084 observed cutoff difference to reduce nominal
suite compute by 30%. The approved order is:

1. `baseline-temporal-v3`;
2. `loro-ca_006-v3` as the first LORO gate;
3. `loro-bc-v3`;
4. `loro-ca_001-v3`–`loro-ca_005-v3`;
5. `loro-ca_007-v3`–`loro-ca_011-v3`.

Do not change model, seed, budget, filtering, evaluation cadence, or checkpoint
policy per fold.

## Launch

Launch and verify the baseline first:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v3.yaml \
  --run baseline-temporal-v3
```

After baseline verification, launch the first LORO gate explicitly if a pause
is desired:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v3.yaml \
  --run loro-ca_006-v3
```

Then run the remaining queue:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v3.yaml \
  --pending
```

The user may instead use `--pending` immediately after baseline verification;
the matrix order still begins with `ca_006`.

## Per-run preflight and closeout

- Registry has no completed v3 state for the run key.
- Fold manifest hash/counts agree with W&B run context.
- Baseline/LORO split identity and held-out-region exclusions validate.
- Resolved config records `test_every_val_epoch = true`.
- W&B group/name/tags use only v3 identity.
- `test/current/iou_epoch` is present across completed epochs.
- `val/iou_epoch` remains the checkpoint monitor.
- Exactly one best checkpoint plus local `last.ckpt` exists.
- Final `test/best/iou_epoch` comes from the recorded best checkpoint.
- Registry marks completion only after the final best-checkpoint test succeeds.

## Failure and resume policy

- Preserve failed and interrupted attempts in the registry.
- Use `last.ckpt` only through the runner's validated single-run resume path.
- Do not reuse a v1 or v2 checkpoint or W&B run ID.
- Pause on identity, data, checkpoint, GPU, disk, or repeated operational
  failures.
- Do not restart a completed v3 entry merely because a later run fails.

## Validation

Suite audit:

```text
run_key,run_type,held_out_region,status,attempts,wandb_run_id,
fold_manifest_sha256,best_checkpoint,best_checkpoint_sha256,best_epoch,
best_val_metric,test_chip_count,current_test_metric_count,
final_best_test_present,error_summary
```

Required checks:

- exactly 13 completed v3 run keys: one baseline and 12 regions;
- no v3 output or registry event uses a v1/v2 run, group, or version identity;
- all runs share model-config hash, seed, 70-epoch budget, `3e-5` LR floor,
  and batch policy;
- every completed fit has an epochwise `test/current/` trajectory;
- checkpoint selection uses validation only;
- every run has a final `test/best/` result tied to its best checkpoint;
- baseline and LORO fold/checkpoint identities agree with manifests and W&B;
- a completed-suite `--pending --dry-run` reports only skips/no work.

Run relevant focused tests/Ruff and `git diff --check` for any corrective code
change. Training execution itself does not authorize unplanned code changes.

## Acceptance criteria

- The v3 baseline and all 12 v3 LORO entries genuinely complete, or the task
  remains in progress with exact resumable state.
- Registry, W&B, fold manifests, checkpoints, and metric namespaces agree.
- No test-driven checkpoint selection or fold-specific tuning occurred.
- Task 018 can use the completed v3 baseline for evaluator development.
- Task 019 can enumerate all 13 completed v3 checkpoints mechanically.

## Non-goals

- Do not compare model accuracy yet.
- Do not build or run the prediction evaluator.
- Do not tune using held-out test trajectories.
- Do not add architectures, seeds, or folds.
- Do not delete the partial v1 suite or interrupted v2 baseline.

## V3 preparation checkpoint

The user stopped W&B run `3ffe42b7`; the v2 registry records
`baseline-temporal-v2` attempt 1 as interrupted after epoch 66, with no live
runner process and no v2 LORO attempt. The replacement v3 configuration changes
only the approved suite identity, the uniform budget from 100 to 70 epochs, and
the cosine floor from `3e-6` to `3e-5`. V1 and v2 configs and experiment roots
remain unchanged.

Preparation changed:

```text
configs/kelp-ps8b/generalization/segformer_b3_v3.yaml
configs/kelp-ps8b/generalization/experiment_matrix_v3.yaml
scripts/run_planet8b_experiments.py
src/models/smp.py
tests/test_run_planet8b_experiments.py
AGENTS.md
README.md
docs/architecture.md
docs/experiments.md
docs/index.md
docs/todo.md
tasks/017_run_v3_training_cycle.md
tasks/018_build_prediction_evaluator.md
tasks/019_run_prediction_suite.md
tasks/README.md
```

The same commit intentionally includes the user's `src/models/smp.py` edits:
the active binary metric lookup now has an explicit `MetricCollection` type
annotation, and the legacy multiclass implementation is commented out. The v3
binary model class and recipe do not use that legacy class.

The v3 model-config SHA-256 is
`1acfa459ed0bb6232e06feda3bad840833714c96975f62df8d8dcc7696a056d1`.
All 13 production dry-runs resolved at 70 epochs with effective batch 24,
the v3 W&B/run/root identity, validation-only checkpoint selection, and
per-epoch current-test diagnostics. All 77 tests passed; targeted Ruff format
and lint checks plus `git diff --check` passed. Repository-wide Ruff remains
blocked only by two pre-existing notebook format findings and two unused-loop
variable findings in `notebooks/create_skema_aux_files.ipynb`. No v3 registry,
run directory, W&B run, or checkpoint was created by preparation. The exact
next action is the baseline launch command above.

## Outcome template

Record exact launch commands, per-run registry/W&B/checkpoint identities,
epochwise-current and final-best metric evidence, failures/retries, runtime and
compute notes, suite consistency audit, unresolved/resume state, and exact
Task 018 handoff.
