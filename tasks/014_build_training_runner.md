# Task 014: Build the experiment registry and training runner

Status: Paused; model-config correction requires Task 014B

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

The final approved policy is owned by Task 014B and will be recorded in the
updated matrix: dedicated later-root SegFormer B3 recipe, retained SMP
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
13 runner dry-runs. The checked-in matrix still names the unused pre-014B smoke
identity `planet8b-loro-v1-smoke-1epoch-v3`; no failed-host v2 registry was
imported. Task 014B must replace that misleading identity with
`planet8b-loro-v1-smoke-tiered-ema-v1` after verifying that no real v3 event
exists. After Task 014B closes, resume Task 014 with:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml \
  --registry /home/sky/experiments/planet8b-loro-v1/experiment_registry.jsonl \
  --pending --smoke
```

Do not run this command until Task 014B closes. Task 014B owns the dedicated
generalization config, batch benchmark, tiered-smoke runner/matrix adjustments,
compatibility validation, identity update, and renewed dry-run gate before this
task resumes.
