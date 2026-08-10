# Task 019: Run the complete prediction suite

Status: Complete

Depends on: Tasks 017 and 018

Execution: Remote multi-run inference task.

## Abstract

Run the Task 018 evaluator for the completed v3 baseline and all 12 v3 LORO
checkpoints. The baseline predicts only its temporal test set; each LORO model
predicts the complete held-out region. The task verifies fold/checkpoint/output
identity and produces one uniform result package per run. It does not perform
the cross-run paired comparison.

## Goal

Create a complete, resumable set of chip diagnostics, unique-pixel source-TIFF
metrics, region summaries, and test summaries for every approved run.

## Inputs

- Task 017 completed v3 baseline/LORO registry and checkpoints
- Task 018 evaluator, threshold, reconstruction, output, and W&B policy
- Task 011 baseline fold manifest
- Task 012 LORO fold manifests
- Canonical chip/raster manifests

## User decisions required

None if Tasks 017–018 contain approved checkpoints, threshold, raster-retention
policy, and output root. If storage estimates for approved prediction rasters
materially exceed available disk, stop with an estimate and ask whether to use
the Task 018 lower-storage option; do not silently drop outputs.

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
3. Re-run/verify baseline output from Task 018 rather than duplicating it.
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
- W&B compact tables/artifacts exist according to Task 018 policy;
- resume reports no work after suite completion.

Run focused tests/Ruff for any runner code and `git diff --check`.

## Acceptance criteria

- Thirteen verified prediction result packages exist.
- Every completed training run has exactly one current compatible evaluation.
- Full-region LORO and temporal baseline test scopes are explicit.
- Suite inventory has no missing, duplicate, or misidentified run.
- Task 020 can join TIFF results without opening model checkpoints or NPZ chips.

## Non-goals

- Do not compare metrics across runs.
- Do not tune thresholds or select checkpoints from test results.
- Do not rerun training.
- Do not treat differing test-set aggregate metrics as paired evidence.

## Outcome template

Record dry-run matrix, storage estimate, exact commands, completed/retried
predictions, suite inventory, output/W&B paths, validation, missing items, and
Task 020 inputs.

## Outcome

The dry-run reconciled all 13 completed v3 training entries: the temporal
baseline was already verified (53 TIFFs/185 chips) and the 12 LORO entries were
pending. The approved observed-suite estimate was 6.03 GiB against 683 GiB
free before launch. The final retained suite occupies 6.2 GiB with 677 GiB
free, so no lower-storage policy was needed.

Changed repository files: `scripts/run_planet8b_predictions.py` now executes
the identity-validated suite sequentially with per-source resume, validates
completed packages, and writes `suite_inventory.csv`; focused coverage is in
`tests/test_run_planet8b_predictions.py`.

Durable external artifacts: all 13 packages are under
`/home/sky/experiments/planet8b-loro-v3/predictions/<run_key>`, with the
complete 13-row inventory at
`/home/sky/experiments/planet8b-loro-v3/predictions/suite_inventory.csv`.
They contain 417 source TIFF rows and 1,513 selected test chips in total.
Every package retains tiled/LZW float32 probability and tiled/LZW uint8 mask
GeoTIFFs. The baseline W&B prediction run is `0u0c5m1j`; the 12 LORO compact
prediction artifacts were written in W&B offline mode because no API key was
configured, and their local syncable run IDs are recorded in the inventory and
each package metadata. The 12 syncable offline run directories are retained at
`/home/sky/experiments/planet8b-loro-v3/predictions/wandb_offline_task019`.

Execution used `uv run python scripts/run_planet8b_predictions.py --dry-run`,
then `--run-key loro-bc-v3 --wandb-mode offline`, followed by the full
`--wandb-mode offline` resume. An external interruption during `ca_008` left 42
valid per-source completions; rerunning safely reused them and completed the
remaining sources without recomputation.

Validation: the final dry-run reports 13 verified and zero pending packages;
all 417 TIFF rows, 1,513 chip counts, checkpoint/fold hashes, completion files,
and pooled unique-pixel confusion sums reconcile. Sampled rasters from every
package meet the approved dtype, LZW, and tiling contract. A final resume
reported no work. Focused runner/evaluator tests passed (7 tests); changed-file
format checks and `git diff --check` passed. Repository-wide Ruff still reports
three pre-existing unrelated findings in two legacy notebooks and `trainer.py`.

Unresolved issue: sync the 12 offline W&B prediction runs when credentials are
available; the external prediction packages are complete and usable now.
Next action: Task 020 should consume `suite_inventory.csv` plus each run's
`tiff_metrics.csv` to construct matching-TIFF baseline/LORO comparisons.
