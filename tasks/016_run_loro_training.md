# Task 016: Run the leave-one-region-out training suite

Status: Complete; partial v1 suite closed and clean v2 restart handed off

Depends on: Tasks 015 and 014

Execution: User-executed remote training; agent verification/check-in afterward.

## Abstract

Run a new baseline and one model for each approved held-out region using one
training policy. Verify the clean v2 training/checkpoint/W&B path, then execute
the remaining matrix entries through the resumable runner. Fold-specific tuning
is prohibited.

The user launches and monitors the production suite. On follow-up, the agent
audits the existing registry, logs, W&B runs, and checkpoints, records the
outcome, and advances the queue; it does not relaunch folds unless the user
explicitly asks.

## Goal

Finish one baseline plus 12 comparable LORO v2 training runs with correct fold
identity, manifests, W&B context, checkpoints, and registry state.

## Inputs

- Task 014 approved 13-run matrix and runner
- Task 015 completed baseline evidence
- Task 012 12 validated LORO views/manifests
- Task 013 W&B contract
- Remote environment/storage

## User decisions required

The user confirmed readiness to begin Task 016 on `2026-07-27`. The approved
execution policy is:

1. First full LORO fold: **`ca_006`**, selected as a moderate-size California
   fold (1,898 train, 261 validation, and 110 test chips).
2. Continue through all remaining folds sequentially after `ca_006`; do not
   pause for another approval unless a failure or operational correction needs
   user input.
3. Use deterministic region-ID order after the first fold.

On `2026-07-30`, while the production suite was underway, the user approved
running the held-out test loader after every training epoch so overfitting is
observable in W&B for later pending folds. These metrics are diagnostics only:
validation IoU remains the checkpoint monitor, and neither later folds nor
training policy may be changed in response to held-out test trajectories.

Registry inspection after implementation showed that the suite had already
advanced: `ca_006` and `bc` were complete, while `ca_001` was active under the
original final-test-only resolved config. Those three runs are not represented
as having per-epoch test curves. They remain part of the superseded partial v1
suite and are not retroactively relabeled. W&B separates v2 chronological
diagnostics under `test/current/*_epoch` from the final validation-selected
checkpoint metrics under `test/best/*_epoch`.

On `2026-07-30`, the user chose to stop the partial v1 runner and restart the
entire production cycle, including the temporal baseline. The replacement
identity is:

```text
experiment/W&B group: planet8b-loro-v2
experiment root: /home/sky/experiments/planet8b-loro-v2
baseline run: baseline-temporal-v2
LORO runs: loro-<region_id>-v2
matrix: configs/kelp-ps8b/generalization/experiment_matrix_v2.yaml
```

The v1 registry, checkpoints, logs, and W&B runs remain historical evidence;
do not delete, overwrite, resume, or relabel them. V2 starts with the baseline,
then retains `ca_006` as the first LORO gate before the remaining deterministic
queue.

The user stopped the v1 runner on `2026-07-30`. Its latest registry state
records `loro-ca_001-v1` attempt 1 as `interrupted` with a keyboard interrupt;
the v1 baseline, `ca_006`, and `bc` entries remain completed. No v2 registry
exists at handoff.

Do not change model, seed, budget, or filtering policy per fold.

## Preflight for every run

- Fold manifest hash/counts match matrix and W&B context.
- Held-out region has no selected train/validation chips and complete test
  membership.
- DataModule loads all splits.
- No completed registry entry exists for the same experiment version/run key.
- GPU/disk/checkpoint paths remain healthy.

## Execution

Use Task 014 runner with `experiment_matrix_v2.yaml`. After confirming the v1
runner is stopped, launch `baseline-temporal-v2` explicitly and validate its
identity. Then launch `loro-ca_006-v2` as the first LORO gate and use
`--pending` for the remaining queue. The runner must record and continue/stop
according to the Task 014 failure policy.

## V2 restart preparation evidence

All 13 production dry-runs resolved under `planet8b-loro-v2`, W&B group
`planet8b-loro-v2`, and
`/home/sky/experiments/planet8b-loro-v2/planet8b-loro-v2`. The ordered queue is
the baseline, `ca_006`, `bc`, then `ca_001`–`ca_005` and `ca_007`–`ca_011`.
Every entry resolved `test_every_val_epoch = true` with validation-only
checkpoint selection. The isolated v2 smoke dry-run resolved 13 entries under
`planet8b-loro-v2-smoke-tiered-ema-v1`: the baseline and BC are the two deep
entries and the other 11 are shallow. Neither dry-run created a registry.

Validation at handoff:

```text
uv run pytest -q
76 passed

uv run ruff format --check <changed Python files>
7 files already formatted

uv run ruff check <changed Python files>
All checks passed

git diff --check
passed
```

Do not use test metrics to alter later folds. Operational corrections that
affect all runs require pausing, recording the issue, and deciding whether the
baseline and completed folds must be rerun under a new experiment version.

## Per-run closeout

- Verify best checkpoint and approved artifact behavior.
- Verify W&B fold/held-out region and manifest artifact.
- Record validation-selected epoch/metric.
- A trainer test may run on the full held-out region for an initial scalar
  sanity check, but the standardized per-TIFF prediction suite is Task 019.
- Mark registry complete only after expected outputs validate.

## Validation

Suite-level audit table:

```text
run_key,held_out_region,status,attempts,wandb_run_id,fold_manifest_sha256,
best_checkpoint,best_checkpoint_sha256,best_epoch,best_val_metric,
test_chip_count,error_summary
```

Required checks:

- exactly one completed v2 baseline and one v2 run per 12 region IDs;
- no fold uses another fold's manifest/checkpoint;
- model config, seed, and budget are identical except data/fold/run identity;
- W&B group contains the baseline plus all completed LORO runs with consistent
  metadata;
- failures/retries remain visible and no duplicate is misclassified complete.

## Acceptance criteria

- One genuine completed v2 baseline and twelve completed v2 LORO checkpoints
  exist, or the task remains in progress/blocked with exact resumable state.
- Registry/W&B/fold/checkpoint identities agree.
- No fold-specific tuning occurred.
- Task 019 can enumerate all completed runs and checkpoints mechanically.

## Non-goals

- Do not compare accuracy across folds yet.
- Do not tune later folds from earlier held-out test results.
- Do not add seeds or architectures.
- Do not rewrite the prediction evaluator.

## Outcome template

Record user approvals, first-fold evidence, suite command/order, completed and
failed runs, W&B IDs, checkpoint hashes, runtime/compute notes, consistency
audit, unresolved/resume state, and Task 019 inputs.

## Outcome

Task 016 closed the partial `planet8b-loro-v1` production suite without
deleting or relabeling its evidence. The user stopped the active runner, and
the latest v1 registry states are:

| Run key | W&B run ID | Final status |
|---|---|---|
| `baseline-temporal-v1` | `24f6a23a` | completed |
| `loro-ca_006-v1` | `96ccc81d` | completed |
| `loro-bc-v1` | `2b99ce62` | completed |
| `loro-ca_001-v1` | `b2dedfdb` | interrupted |

The original twelve-completed-LORO v1 acceptance criterion was superseded by
the user's explicit clean-v2 decision; it was not met or represented as met.

The durable v1 registry remains at
`/home/sky/experiments/planet8b-loro-v1/experiment_registry.jsonl`, with its
checkpoints and logs beneath the same experiment root. No v2 registry or
training output existed at closeout.

The task added per-epoch held-out evaluation through separate
`test/current/` and `test/best/` metric collections, kept validation IoU as the
only checkpoint selector, generalized run-context identity injection, and
created the clean v2 matrix. Changed implementation/config/test files were:

```text
src/data.py
src/models/smp.py
src/run_context.py
scripts/run_planet8b_experiments.py
configs/kelp-ps8b/generalization/segformer_b3_v1.yaml
configs/kelp-ps8b/generalization/experiment_matrix_v2.yaml
tests/test_epoch_test_diagnostics.py
tests/test_run_context.py
tests/test_run_planet8b_experiments.py
```

Documentation and routing changes were recorded in:

```text
AGENTS.md
README.md
docs/architecture.md
docs/experiments.md
docs/index.md
docs/todo.md
tasks/016_run_loro_training.md
tasks/README.md
```

All 13 v2 production dry-runs and all 13 isolated v2 smoke dry-runs resolved
with the intended identities, ordering, budgets, and per-epoch test policy.
Validation passed with 76 tests, targeted Ruff format/check, and
`git diff --check`. There are no unresolved Task 016 implementation issues.
The exact next action is Task 017: the user launches and verifies
`baseline-temporal-v2`, then runs the 12 v2 LORO entries.
