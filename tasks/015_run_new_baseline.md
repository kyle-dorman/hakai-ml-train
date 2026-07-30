# Task 015: Run the expanded-data temporal baseline

Status: Complete

Depends on: Task 014

Execution: User-executed remote training; agent verification/check-in afterward.

## Abstract

Launch and monitor the one standard baseline run defined by the approved
experiment matrix. This establishes temporally separated in-domain performance
on the expanded 12-region dataset and produces the first checkpoint required by
prediction-evaluator development. This task executes the recorded policy; it
does not tune the model based on test results.

The user launches and monitors this production run. On follow-up, the agent
inspects the existing registry, logs, W&B run, checkpoints, and metrics, records
the outcome, and advances the queue; it does not relaunch training unless the
user explicitly asks.

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
- Task 018 can use this historical checkpoint for evaluator scaffolding, while
  the active comparison evaluator uses the v2 baseline from Task 017.
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

## Outcome

The production temporal baseline completed in one uninterrupted attempt from
`2026-07-22T22:17:19Z` through `2026-07-24T02:59:06Z` (28:41:47 elapsed).
It used the approved SegFormer B3 recipe at commit
`e7382e342a028f493a2fff13dd65101973d7206e`, seed 42, batch size 3 with
accumulation 8, 100 epochs, no early stopping, and no batch limits. The
resolved baseline view contained 2,103 train chips from 240 TIFFs
(`2020-04-22`–`2022-06-14`), 277 validation chips from 67 TIFFs
(`2021-04-28`–`2022-06-20`), and 185 test chips from 53 TIFFs
(`2021-05-27`–`2022-12-28`) across all 12 regions. Its fold-manifest SHA-256
was `4945e32e1cb4a29d00768ca9ae8aa523d91604516c3adc250ff2b4c0c1bed3c1`.

The launch command was:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml \
  --registry /home/sky/experiments/planet8b-loro-v1/experiment_registry.jsonl \
  --run baseline-temporal-v1
```

The registry records `planned -> running -> completed` with exit code 0 and
W&B run `24f6a23a`, which is `finished` in
`kdorman90-ucla/kelpseg`, group `planet8b-loro-v1`, name
`baseline-temporal-v1`, and job type `train`. W&B logged the run-metadata,
best-checkpoint, and history artifacts. Epoch 98 at global optimizer step 8,712
selected the best checkpoint with `val/iou_epoch = 0.70966` (registry value
0.7097):

The attempt root is
`/home/sky/experiments/planet8b-loro-v1/planet8b-loro-v1/runs/baseline-temporal-v1/attempt-01`;
the selected checkpoint is
`kelpseg/24f6a23a/checkpoints/kelp_ps8b_segformer_b3_epoch-98_val-iou-0.7097.ckpt`.

The 714,713,951-byte best checkpoint matches the registry SHA-256
`5f81b79327953bca0654fbde8e98260395850240f72ba68e9752d442502c24a0`.
The separate local `kelpseg/24f6a23a/checkpoints/last.ckpt` is the same size,
exists and is loadable, and has the same SHA-256. Testing loaded the selected
best checkpoint, processed all 62 batches, and reported:

| Metric | Value |
|---|---:|
| Accuracy | 0.993646 |
| F1 | 0.713036 |
| IoU | 0.612573 |
| Loss | 0.411411 |
| Precision | 0.739309 |
| Recall | 0.711615 |

These test metrics are recorded without tuning or relaunch. Registry identity,
checkpoint hash, run context, W&B state/artifacts, full test scope, and the
absence of traceback, CUDA-error, or NaN markers in the persistent log were
verified. Durable external artifacts are the attempt root, checkpoint pair,
W&B run/artifacts, persistent log, and append-only registry under
`/home/sky/experiments/planet8b-loro-v1`.

This closeout changes documentation only: `AGENTS.md`, `README.md`,
`docs/index.md`, `docs/todo.md`, `tasks/README.md`, this task file, and the
Task 016 status/decision handoff. There are no unresolved Task 015 issues. The
exact next action is to launch Task 016's first production fold,
`loro-ca_006-v1`, through the same runner and registry.

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml \
  --registry /home/sky/experiments/planet8b-loro-v1/experiment_registry.jsonl \
  --run loro-ca_006-v1
```
