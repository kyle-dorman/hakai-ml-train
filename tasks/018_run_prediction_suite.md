# Task 018: Run the complete prediction suite

Status: Pending

Depends on: Tasks 016 and 017

Execution: Remote multi-run inference task.

## Abstract

Run the Task 017 evaluator for the completed baseline and all 12 LORO
checkpoints. The baseline predicts only its temporal test set; each LORO model
predicts the complete held-out region. The task verifies fold/checkpoint/output
identity and produces one uniform result package per run. It does not perform
the cross-run paired comparison.

## Goal

Create a complete, resumable set of chip diagnostics, unique-pixel source-TIFF
metrics, region summaries, and test summaries for every approved run.

## Inputs

- Task 016 completed LORO registry/checkpoints
- Task 015 baseline registry/checkpoint
- Task 017 evaluator, threshold, reconstruction, output, and W&B policy
- Task 011 baseline fold manifest
- Task 012 LORO fold manifests
- Canonical chip/raster manifests

## User decisions required

None if Tasks 016–017 contain approved checkpoints, threshold, raster-retention
policy, and output root. If storage estimates for approved prediction rasters
materially exceed available disk, stop with an estimate and ask whether to use
the Task 017 lower-storage option; do not silently drop outputs.

## Planned execution surface

Extend Task 014's registry/runner or add a narrowly separate prediction runner
that enumerates completed training entries. Recommended command shape:

```bash
uv run python scripts/run_planet8b_predictions.py \
  --registry <experiment_registry.jsonl> \
  --runs completed \
  --output-root <predictions-root> \
  --resume \
  --dry-run
```

Dry-run must list 13 run/checkpoint/fold/output combinations and expected test
TIFF/chip counts.

## Run contract

- Baseline: only selected `test` rows from Task 011.
- LORO: complete selected `test` rows for that fold's held-out region.
- Checkpoint: recorded best checkpoint from the exact training run.
- Threshold/reconstruction/schema: identical across runs.
- Output directory keyed by experiment version and run key.
- Prediction status/attempts recorded separately or as typed events in the
  experiment registry.

## Execution plan

1. Dry-run all 13 entries and reconcile counts/hashes.
2. Verify disk estimate and W&B connectivity/offline behavior.
3. Re-run/verify baseline output from Task 017 rather than duplicating it.
4. Run one completed LORO fold and audit output end to end.
5. Run remaining pending predictions in deterministic region-ID order.
6. Resume failures without recomputing verified source TIFFs.
7. Build a suite inventory table.

## Suite inventory

```text
run_key,run_type,held_out_region,training_wandb_run_id,prediction_wandb_run_id,
checkpoint_sha256,fold_manifest_sha256,status,test_tiff_count,test_chip_count,
scored_pixel_count,uncovered_pixel_count,output_path,error_summary
```

## Validation

For every run:

- checkpoint/fold/run IDs agree with registry and W&B;
- expected test TIFF/chip counts equal evaluated inputs;
- baseline contains only baseline temporal-test TIFFs;
- each LORO output contains only and all canonical TIFFs/chips from its held-out
  region after universal filtering;
- TIFF accounting and pooled confusion sums reconcile;
- threshold/reconstruction/schema hashes are identical;
- W&B compact tables/artifacts exist according to Task 017 policy;
- resume reports no work after suite completion.

Run focused tests/Ruff for any runner code and `git diff --check`.

## Acceptance criteria

- Thirteen verified prediction result packages exist.
- Every completed training run has exactly one current compatible evaluation.
- Full-region LORO and temporal baseline test scopes are explicit.
- Suite inventory has no missing, duplicate, or misidentified run.
- Task 019 can join TIFF results without opening model checkpoints or NPZ chips.

## Non-goals

- Do not compare metrics across runs.
- Do not tune thresholds or select checkpoints from test results.
- Do not rerun training.
- Do not treat differing test-set aggregate metrics as paired evidence.

## Outcome template

Record dry-run matrix, storage estimate, exact commands, completed/retried
predictions, suite inventory, output/W&B paths, validation, missing items, and
Task 019 inputs.
