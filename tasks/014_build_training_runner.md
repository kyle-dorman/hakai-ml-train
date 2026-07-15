# Task 014: Build the experiment registry and training runner

Status: Pending

Depends on: Task 013

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
- Reference config: `configs/kelp-ps8b/california/segformer_b3.yaml`
- Smoke config:
  `configs/kelp-ps8b/california/segformer_b3_remote_1epoch.yaml`
- `trainer.py`
- `docs/experiments.md`

## User decisions required

Confirm the comparison policy before generating the matrix:

1. Base model config. Recommendation: California PS8B SegFormer B3 unless the
   user explicitly selects another already-working PS8B config.
2. Seed policy. Recommendation: one fixed seed (`42`) for the first complete
   baseline/LORO suite; multiple seeds are backlog follow-up.
3. Full training budget: maximum epochs, early-stopping policy if any, and
   checkpoint monitor. Recommendation: preserve the selected base config unless
   the baseline smoke reveals a concrete problem.
4. Execution mode: sequential runs (recommended for one GPU) versus an external
   scheduler.
5. Failure policy: continue to next run after recording failure (recommended)
   or stop suite.

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
- `--smoke` with bounded trainer overrides;
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
- Resume uses compatible `last.ckpt`; completed runs remain immutable unless the
  user explicitly creates a new version/attempt.

## Plan / spec requirement

Add a plan covering config override/generation, subprocess invocation, registry
event/state model, W&B run ID capture, checkpoint discovery, interruption
handling, and duplicate-run prevention.

## Smoke test

1. Dry-run the complete 13-run matrix and inspect commands/configs.
2. Run one bounded baseline smoke.
3. Run one bounded `ca_001` LORO smoke.
4. Simulate one failed command and one interrupted entry.
5. Re-run `--pending` and verify completed smokes are skipped and failed work is
   represented honestly.

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
- Two smoke runs use correct W&B context and dataset views.
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
