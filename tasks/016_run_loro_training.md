# Task 016: Run the leave-one-region-out training suite

Status: Pending

Depends on: Tasks 015 and 014

Execution: User-executed remote training; agent verification/check-in afterward.

## Abstract

Run one model for each approved held-out region using the exact training policy
established for the baseline. Begin with one representative fold, verify the
complete training/checkpoint/W&B path, and then execute the remaining pending
matrix entries through the resumable runner. Fold-specific tuning is prohibited.

The user launches and monitors the production suite. On follow-up, the agent
audits the existing registry, logs, W&B runs, and checkpoints, records the
outcome, and advances the queue; it does not relaunch folds unless the user
explicitly asks.

## Goal

Finish 12 comparable LORO training runs with correct fold identity, manifests,
W&B context, checkpoints, and registry state.

## Inputs

- Task 014 approved 13-run matrix and runner
- Task 015 completed baseline evidence
- Task 012 12 validated LORO views/manifests
- Task 013 W&B contract
- Remote environment/storage

## User decisions required

Before launching the suite, confirm:

1. First full LORO fold: **`ca_006`**, selected as a moderate-size California
   fold (1,898 train, 261 validation, and 110 test chips).
2. Continue through all remaining folds sequentially after `ca_006`; do not
   pause for another approval unless a failure or operational correction needs
   user input.
3. Run order if compute scheduling matters. Default: deterministic region-ID
   order after the first fold.

Do not change model, seed, budget, or filtering policy per fold.

## Preflight for every run

- Fold manifest hash/counts match matrix and W&B context.
- Held-out region has no selected train/validation chips and complete test
  membership.
- DataModule loads all splits.
- No completed registry entry exists for the same experiment version/run key.
- GPU/disk/checkpoint paths remain healthy.

## Execution

Use Task 014 runner. Launch first fold explicitly, validate it, then use
`--pending` or explicit remaining run keys after approval. The runner must record
and continue/stop according to the Task 014 failure policy.

Do not use test metrics to alter later folds. Operational corrections that
affect all runs require pausing, recording the issue, and deciding whether the
baseline and completed folds must be rerun under a new experiment version.

## Per-run closeout

- Verify best checkpoint and approved artifact behavior.
- Verify W&B fold/held-out region and manifest artifact.
- Record validation-selected epoch/metric.
- A trainer test may run on the full held-out region for an initial scalar
  sanity check, but the standardized per-TIFF prediction suite is Task 018.
- Mark registry complete only after expected outputs validate.

## Validation

Suite-level audit table:

```text
run_key,held_out_region,status,attempts,wandb_run_id,fold_manifest_sha256,
best_checkpoint,best_checkpoint_sha256,best_epoch,best_val_metric,
test_chip_count,error_summary
```

Required checks:

- exactly one completed run per 12 region IDs;
- no fold uses another fold's manifest/checkpoint;
- model config, seed, and budget are identical except data/fold/run identity;
- W&B group contains the baseline plus all completed LORO runs with consistent
  metadata;
- failures/retries remain visible and no duplicate is misclassified complete.

## Acceptance criteria

- Twelve genuine completed LORO checkpoints exist, or the task remains in
  progress/blocked with exact resumable state.
- Registry/W&B/fold/checkpoint identities agree.
- No fold-specific tuning occurred.
- Task 018 can enumerate all completed runs and checkpoints mechanically.

## Non-goals

- Do not compare accuracy across folds yet.
- Do not tune later folds from earlier held-out test results.
- Do not add seeds or architectures.
- Do not rewrite the prediction evaluator.

## Outcome template

Record user approvals, first-fold evidence, suite command/order, completed and
failed runs, W&B IDs, checkpoint hashes, runtime/compute notes, consistency
audit, unresolved/resume state, and Task 018 inputs.
