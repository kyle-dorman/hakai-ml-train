# Task 015: Run the expanded-data temporal baseline

Status: Pending

Depends on: Task 014

Execution: Remote full training task.

## Abstract

Launch and monitor the one standard baseline run defined by the approved
experiment matrix. This establishes temporally separated in-domain performance
on the expanded 12-region dataset and produces the first checkpoint required by
prediction-evaluator development. This task executes the recorded policy; it
does not tune the model based on test results.

## Goal

Complete or leave a cleanly resumable baseline training run with verified W&B
context, best/last checkpoint handling, and final validation/test metrics.

## Inputs

- Task 014 matrix, runner, registry, resolved config policy, and smoke evidence
- Task 011 baseline view and fold manifest
- Task 013 W&B destination/group/artifact policy
- Remote GPU/environment from Task 010

## User decisions required

Before launch, show the user the resolved baseline summary:

```text
run key, model, seed, epochs/early stopping, train/val/test TIFF and chip counts,
date ranges, data paths, W&B destination/group, checkpoint policy, estimated
runtime if available
```

Ask for confirmation only if Task 014 did not already approve the full-run
matrix/budget or if the resolved summary differs. Do not reopen approved choices
without evidence.

## Preflight

- Working tree/commit and dirty state match the registry context.
- Dataset/fold hash and counts match Task 011.
- One batch from each split loads.
- GPU, CUDA, disk, and W&B connectivity/offline mode are healthy.
- No conflicting completed baseline entry exists.
- Checkpoint and log directories are writable with sufficient space.

## Execution

Use Task 014 runner, not a handwritten trainer command. Recommended shape:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml \
  --registry <registry.jsonl> \
  --run baseline-temporal-v1
```

Monitor early batches/epochs for finite loss, reasonable throughput, validation
execution, checkpoint creation, and correct W&B identity. If interrupted, use
the runner's recorded resume path rather than starting an ambiguous duplicate.

## Test and closeout

- Use the selected best checkpoint for the configured baseline test split.
- Do not inspect test results to relaunch/tune this baseline within the task.
- Record validation-selected best epoch and metric separately from test metrics.
- Verify W&B artifact/checkpoint policy and local registry final state.

## Validation

- Registry has one unambiguous completed baseline entry and attempt history.
- W&B run shows correct group/name, dataset/fold hashes, counts, and config.
- Best checkpoint exists, loads, and matches recorded monitor value.
- Last checkpoint exists if required by policy.
- Test command exits successfully and metrics are recorded.
- Logs contain no unresolved NaN, data, or checkpoint errors.

## Acceptance criteria

- Baseline run is completed or explicitly documented as resumable; do not mark
  complete merely because compute stopped.
- Best checkpoint path/hash and W&B run ID are recorded.
- Final validation/test metrics are attached without tuning on test.
- Task 017 can use this checkpoint for evaluator development.
- `docs/todo.md` advances to Task 016 only after genuine completion.

## Non-goals

- Do not tune hyperparameters or preprocessing using baseline test metrics.
- Do not run LORO folds.
- Do not build the final prediction evaluator in this task.
- Do not compare against historical runs with incompatible data.

## Outcome template

Record resolved run summary, exact runner command, attempts/resume events,
runtime, W&B run ID, checkpoint paths/hashes, best validation epoch/metric, test
metrics, validation evidence, and next action.
