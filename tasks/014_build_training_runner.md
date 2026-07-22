# Task 014: Build the experiment registry and training runner

Status: Complete

Depends on: Tasks 013, 014A, and 014B

Execution: Remote-aware code task; smoke runs only.

## Abstract

Build a resumable runner for one baseline and 12 LORO training jobs. The runner
must resolve dataset paths/config overrides from fold manifests, register every
planned run before launch, inject Task 013 W&B context, and preserve honest
pending/running/completed/failed state. This task verifies orchestration with
short smokes; Tasks 015–016 perform full training.

## Goal

Replace manual YAML editing and ad hoc shell loops with one explicit experiment
matrix and restartable execution surface.

## Inputs

- Task 013 run-context helper and W&B decisions
- Task 011 baseline view/manifest
- Task 012 LORO views/manifests
- Dedicated config produced by Task 014B:
  `configs/kelp-ps8b/generalization/segformer_b3_v1.yaml`
- Smoke profile: the selected production config with runner-owned tiered budget
  and batch-limit overrides; model recipe, selected batch/accumulation pair,
  precision, workers, and transforms otherwise match production
- `trainer.py`
- `docs/experiments.md`

## User decisions required

The comparison and smoke policies are approved:

1. Base model config: **approved as the dedicated Task 014B config derived from
   the later root PS8B SegFormer B3 recipe**, including its existing SMP
   eight-band ImageNet adaptation.
2. Seed policy. Recommendation: one fixed seed (`42`) for the first complete
   baseline/LORO suite; multiple seeds are backlog follow-up.
3. Full training budget: **approved at 100 epochs**, with no early stopping and
   `val/iou_epoch` as the best-checkpoint monitor. Smoke uses two full epochs
   for the temporal baseline and `loro-bc-v1`; the other 11 LORO entries use one
   bounded epoch with two optimizer updates' worth of training micro-batches,
   two validation batches, and two test batches.
4. Execution mode: sequential runs (recommended for one GPU) versus an external
   scheduler.
5. Failure policy: **approved to continue to the next sequential run after
   recording a failure**.

The approved base model is the dedicated Task 014B SegFormer B3, with fixed
seed `42`, a benchmark-selected micro-batch/accumulation pair whose product is
24, and sequential single-GPU execution. The user will launch the production
runs in Tasks 015 and 016; those tasks are post-run verification/check-in
boundaries, not agent-owned launch steps.

Record exact choices in this task and the checked-in experiment matrix.

## Planned files and CLI

Recommended repo files:

```text
configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml
scripts/run_planet8b_experiments.py
tests/test_run_planet8b_experiments.py
```

Runtime registry under the remote experiment root:

```text
experiment_registry.jsonl
experiment_registry.csv
resolved_configs/<run_key>.yaml
logs/<run_key>.log
```

Generated run artifacts are namespaced by `experiment_version`; smoke and
production attempts never share resolved configs, checkpoints, logs, or latest
registry state.

CLI:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml \
  --registry <experiment-root>/experiment_registry.jsonl \
  --run baseline-temporal-v1 \
  --dry-run
```

Support:

- `--run <run_key>` repeatable;
- `--pending` for all non-completed matrix entries;
- `--dry-run`;
- `--smoke` selecting the separate tiered-EMA experiment identity, per-run
  budget/batch limits, registry state, output root, and W&B smoke identity;
- explicit `--resume-checkpoint` for a failed/interrupted entry where valid;
- no implicit rerun of completed entries without a deliberate override.

## Registry schema

Each immutable event row includes:

```text
timestamp,experiment_version,run_key,run_type,fold_id,held_out_region,
status,attempt,command,resolved_config_path,fold_manifest_path,
fold_manifest_sha256,git_commit,git_dirty,hostname,wandb_run_id,
checkpoint_path,best_metric,exit_code,error_summary
```

Statuses: `planned`, `running`, `completed`, `failed`, `interrupted`, `skipped`.
JSONL is the append-only event source; CSV is a regenerated latest-state view.

## Runner invariants

- Matrix contains exactly one baseline and one entry for every approved LORO
  region ID.
- Resolve train/val/test paths from the fold, never from manually copied legacy
  paths.
- Verify fold manifest hash/counts before every launch.
- Generate a resolved config per attempt and attach it through Task 013.
- Record `running` before subprocess launch and final status after exit.
- Capture stdout/stderr to per-run log while preserving live console output.
- A W&B run ID and checkpoint can never be silently reassigned to another fold.
- Resume uses compatible local `last.ckpt`; only the best checkpoint is uploaded
  to W&B. Completed runs remain immutable unless the user explicitly creates a
  new version/attempt.

## Plan / spec requirement

Add a plan covering config override/generation, subprocess invocation, registry
event/state model, W&B run ID capture, checkpoint discovery, interruption
handling, and duplicate-run prevention.

## Smoke test

1. Dry-run the complete 13-run matrix and inspect commands/configs.
2. Run the temporal baseline and `loro-bc-v1` for two full epochs each; verify
   both cross optimizer step 100, update EMA, validate with EMA weights, and
   produce a usable best checkpoint plus local `last.ckpt`.
3. Run the other 11 LORO folds for one bounded epoch each, with exactly two
   optimizer updates' worth of training micro-batches followed by two
   validation batches and two test batches.
4. For every smoke, load the selected best checkpoint for the configured test
   scope. Treat all smoke metrics as integration evidence only.
5. Simulate one failed command and one interrupted entry.
6. Re-run smoke `--pending` and verify completed smokes are skipped and failed
   work is represented honestly.
7. Verify production `--pending` still selects all 13 entries because smoke and
   production state are isolated.

## Validation

```bash
uv run ruff format --check scripts tests
uv run ruff check scripts tests
uv run pytest tests/test_run_planet8b_experiments.py
git diff --check
```

Validate resolved data paths and W&B metadata for all 13 dry-run entries.

## Acceptance criteria

- User-approved matrix/config/seed/budget are checked in.
- Dry-run shows one baseline plus 12 LORO runs with correct fold paths.
- Registry survives success, failure, interruption, and resume tests.
- All 13 smoke runs use correct W&B context and dataset views.
- No full training run has started.

## Non-goals

- Do not launch full baseline/LORO training.
- Do not add multi-GPU distributed scheduling unless selected by the user.
- Do not tune hyperparameters by fold.
- Do not build prediction/evaluation orchestration.

## Review pass

- Software architect: verify config generation and registry ownership.
- Risk-averse engineer: verify interruption, duplicate, resume, and fold-mixup
  protections.

## Outcome template

Record user-approved matrix policy, files/CLI, registry schema, dry-run matrix,
smoke run results, failure/resume evidence, validation, and Task 015 command.

## Progress

The final approved policy is recorded in the updated matrix: dedicated
later-root SegFormer B3 recipe, retained SMP
eight-band ImageNet adaptation, benchmark-selected effective batch size 24,
seed `42`, 100 production epochs, no early stopping, best `val/iou_epoch`
checkpoint plus local `last.ckpt`, sequential execution, and
continue-after-failure. The user will execute Tasks 015–016; those tasks will
verify and record the resulting runs after the fact.

The runner, registry tests, and all 13 real-fold smoke/production dry-runs are
implemented and passing. A historical batch-size-1 baseline smoke completed fit,
validation, checkpoint upload, and test under W&B run `8f4268b3`; it measured
`val/iou_epoch = 0.14294` and `test/iou = 0.28319`. That profile took 43:47 for
fit and was superseded because it did not match production runtime settings.

The production-like `planet8b-loro-v1-smoke-1epoch-v2` suite then reached batch
281/701 of the baseline before the A40 disappeared from the driver with
`cudaErrorUnknown`. PyTorch now reports zero CUDA devices and `nvidia-smi`
cannot obtain the device handle. The attempt and interruption remain in
`/home/sky/experiments/planet8b-loro-v1/experiment_registry.jsonl`; no v2 run is
marked complete.

The original host is no longer available. Task 014A completed the replacement
A40 host gate at commit `5461cfeb45aab216d43cd8d80451d8a420ae00f0`, including
the canonical dataset, all hard-linked views, W&B/CUDA/GPU preflight, and all
13 runner dry-runs. Task 014B created and validated the dedicated config,
selected micro-batch 3 with accumulation 8, replaced the unused pre-014B smoke
identity after confirming no real v3 registry event exists, and passed all 13
smoke plus all 13 production dry-runs. The completed fresh suite was launched
with:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml \
  --registry /home/sky/experiments/planet8b-loro-v1/experiment_registry.jsonl \
  --pending --smoke
```

That command produced the completed
`planet8b-loro-v1-smoke-tiered-ema-v1` evidence recorded below.

## Outcome

Task 014 completed the runner implementation and the fresh 13-entry
`planet8b-loro-v1-smoke-tiered-ema-v1` integration suite on the replacement
NVIDIA A40. The suite ran from `2026-07-22T20:02:41Z` through
`2026-07-22T21:56:00Z`. The append-only registry contains exactly 13
`planned`, 13 `running`, and 13 `completed` events for this version; every
latest state has exit code 0, a W&B run ID, a validation-selected best
checkpoint with a matching recorded SHA-256, and a separate local
`last.ckpt`.

The two deep gates both crossed EMA step 100 and validated afterward:

| Run | W&B ID | Final optimizer step | Best `val/iou_epoch` | Test batches | Test IoU |
|---|---|---:|---:|---:|---:|
| `baseline-temporal-v1` | `87bcc703` | 176 | 0.4005 | 62 | 0.374109 |
| `loro-bc-v1` | `fd4195b0` | 172 | 0.4998 | 51 | 0.155444 |

All 11 California LORO smokes ran exactly 16 training micro-batches with
accumulation 8, reached optimizer step 2, validated on two batches, loaded the
selected best checkpoint, and tested on two batches. Their W&B IDs are:

| Run | W&B ID | Best `val/iou_epoch` | Test IoU |
|---|---|---:|---:|
| `loro-ca_001-v1` | `dd56111f` | 0.0455 | 0.014247 |
| `loro-ca_002-v1` | `51a9dfb0` | 0.0257 | 0.033441 |
| `loro-ca_003-v1` | `2a66ac87` | 0.0257 | 0.001215 |
| `loro-ca_004-v1` | `0b5250a7` | 0.0257 | 0.036984 |
| `loro-ca_005-v1` | `3659bf4a` | 0.0257 | 0.009279 |
| `loro-ca_006-v1` | `69875b28` | 0.0257 | 0.015178 |
| `loro-ca_007-v1` | `65e34864` | 0.0257 | 0.006964 |
| `loro-ca_008-v1` | `72084f55` | 0.0257 | 0.069283 |
| `loro-ca_009-v1` | `1800275a` | 0.0257 | 0.007480 |
| `loro-ca_010-v1` | `64764561` | 0.0257 | 0.001180 |
| `loro-ca_011-v1` | `5c000519` | 0.0257 | 0.010572 |

These metrics are integration evidence only and were not used for tuning.
W&B produced transient GraphQL timeout/HTTP 500 retries late in the suite, but
each affected upload/resume/close recovered without intervention and every
local run finished consistently. A post-suite W&B API audit found all 13 run
IDs in state `finished`, group `smoke`, with the expected name and `smoke` job
type. The A40 remained visible throughout; its thermal-slowdown flags stayed
inactive.

Changed repository files across Task 014 are the experiment matrix, runner,
focused runner tests, and task/queue documentation. This closing pass added
direct failed-command and keyboard-interruption execution tests. Durable
external artifacts are under
`/home/sky/experiments/planet8b-loro-v1/planet8b-loro-v1-smoke-tiered-ema-v1`
(18 GB, 26 checkpoints), with the append-only JSONL registry and regenerated
CSV at `/home/sky/experiments/planet8b-loro-v1`. The final JSONL SHA-256 is
`a5202da828650be3489fa9dc5ba3fd061a3e6e6a70ebbb6bf5fd4d2f24f99ffd`.

Validation passed:

```text
uv run ruff format --check scripts tests
uv run ruff check scripts tests
uv run pytest tests/test_run_planet8b_experiments.py  # 10 passed
```

The behavioral tests record `planned -> running -> failed` for a simulated
exit code 17 and `planned -> running -> interrupted` for a simulated keyboard
interrupt. Real smoke `--pending --dry-run` selected zero entries without
changing the registry hash, while production `--pending --dry-run` selected
all 13 entries. No production training started. There are no blocking
unresolved issues.

Repository-wide Ruff format/check remains blocked by two unchanged legacy
notebooks: `notebooks/create_skema_aux_files.ipynb` would be reformatted and
also contains two pre-existing B007 unused-loop-variable findings, while
`notebooks/export_skema_models_onnx.ipynb` would be reformatted. These files are
outside the active PS8B task scope; task-scoped checks are clean.

The exact next action is the user-executed Task 015 baseline launch:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml \
  --registry /home/sky/experiments/planet8b-loro-v1/experiment_registry.jsonl \
  --run baseline-temporal-v1
```
