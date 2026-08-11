# Experiment and W&B contract

For navigation, start with `docs/index.md`. Read this file before changing W&B,
training orchestration, run naming, checkpoints, prediction artifacts, or
cross-run comparisons.

## W&B destination

New PlanetScope 8-band baseline and LORO work belongs in:

```text
entity: kdorman90-ucla
project: kelpseg
```

This is the destination used by the current California SegFormer config and its
remote smoke config. Other PS8B configs contain historical values; do not treat
them as the new suite's tracking contract.

The active comparison-suite group is `planet8b-loro-v3`. Baseline and LORO
training runs use `baseline-temporal-v3` and `loro-<region_id>-v3`; the region
ID is the canonical fold key. Smoke runs use the separate `smoke` group, a
`smoke` job type/tag, and the corresponding `smoke-` name prefix. The partial
`planet8b-loro-v1` production suite and interrupted `planet8b-loro-v2`
baseline, together with their registries and artifacts, remain historical
evidence and must not be resumed, relabeled, or overwritten.

## Run organization

Every run should expose these dimensions in W&B and the local experiment
registry:

- run type: baseline training, LORO training, or prediction;
- held-out region ID, or null for the baseline;
- dataset/archive version;
- fold-manifest path, artifact reference, and content hash;
- model config and git commit;
- seed and training budget;
- TIFF and chip counts by split;
- split date ranges and participating regions;
- nodata threshold and background-selection policy;
- W&B run ID, status, best checkpoint, and final metrics.

Names must be predictable and unique. Use region IDs, not potentially duplicated
region names, in LORO run names.

The v3 smoke identity is `planet8b-loro-v3-smoke-tiered-ema-v1`. Baseline and
`loro-bc-v3` use two full epochs so EMA crosses its update gate; the other 11
LORO folds use one epoch capped at two optimizer updates, two validation
batches, and two test batches. Smoke limits are runner-owned and never apply to
the uniform 70-epoch production suite. The completed v1 smoke suite remains
valid historical gate evidence.

`src/run_context.py` owns the required JSON-compatible context. Generate it
from the dataset and fold files with `scripts/build_planet8b_run_context.py`,
then pass it to `trainer.py fit --run_context <path>`. The trainer rehashes all
identity-bearing inputs and injects data paths and W&B fields before Lightning
instantiates any training objects. Do not derive fold identity from the run
name or maintain one YAML copy per fold.

## W&B artifacts

Attach or log references to:

- canonical dataset metadata and chip manifest version;
- baseline or LORO fold manifest;
- resolved training config;
- best checkpoint and final run summary;
- chip- and TIFF-level prediction results;
- paired matching-TIFF comparison results.

Large canonical chips do not need to be uploaded to W&B merely to make the run
reproducible; their archive checksum and manifest identity are the contract.

Training runs keep one validation-selected best checkpoint (`save_top_k=1`) and
a local `last.ckpt` for exact interruption recovery. Only the best checkpoint is
logged as the W&B model artifact at fit end; `last.ckpt` remains a local recovery
artifact. Production LORO fits also evaluate the complete held-out test loader
after every validation epoch and log epoch-level
`test/current/*_epoch` diagnostics. These curves are observational only:
`val/iou_epoch` remains the sole checkpoint-selection metric, and held-out test
trajectories must not change later folds or training policy. The runner still
performs a final full test from the validation-selected best checkpoint under
the separate `test/best/*_epoch` namespace before marking a run complete.
Metadata and best-checkpoint artifacts use the same path in online and offline
mode; offline run directories remain syncable later. The metadata artifact
contains the generated context, resolved Lightning config, fold manifest and
summary, canonical dataset metadata, archive verification receipt, chip
manifest, and model config. Canonical NPZs are not uploaded.

## Prediction evaluation

Prediction evaluation uses the training registry's validation-selected best
checkpoint, averages foreground probabilities at each covered source pixel,
then thresholds once at the fixed pre-test value `0.5`. It retains tiled/LZW
float32 probability GeoTIFFs and tiled/LZW uint8 mask GeoTIFFs outside git at
`/home/sky/experiments/planet8b-loro-v3/predictions_all_retained_v2/<run_key>`.
The primary `all_retained_test_chips` scope includes selected test rows and
their corresponding overlap-exclusion rows from the canonical post-nodata
collection. Evaluation schema 3 records that scope plus corrected centered-pad
alignment and prevents resume from the invalid schema-2 outputs. A separate
`prediction` W&B run logs the compact CSV/JSON result
package and one paired QA raster example; full raster collections remain in
that external output root. Task 022's `predictions_all_retained_v1` packages are
preserved but invalid for scientific use because they top-left-cropped centered
padding. The earlier
`/home/sky/experiments/planet8b-loro-v3/predictions` packages are preserved as
historical `selected_nonoverlap` evidence and have the same undersized-chip
alignment limitation.

## Local experiment registry

W&B is the live review surface, not the only record. Maintain a machine-readable
local registry so interrupted, failed, offline, and completed runs remain
resumable. The registry should include planned runs before launch and update
status atomically.

Do not infer completion only from a checkpoint filename or a W&B page. Verify
the expected fold, manifest hash, checkpoint, and prediction outputs.

## Comparison contract

- Use the recorded best checkpoint for test prediction.
- Keep chip-level diagnostics, but do not treat overlapping chip counts as
  additive TIFF evidence.
- Default reporting and cross-run joins use source TIFF ID.
- Reconstruct one prediction per covered source pixel before TIFF metrics.
- Pooled metrics sum unique-pixel TIFF confusion counts before calculating
  accuracy, precision, recall, and IoU.
- Paired baseline/LORO comparison uses matching TIFFs unseen by both runs.
- Full held-out-region LORO performance is reported separately from the paired
  baseline comparison.
- The primary versioned comparison is
  `/home/sky/experiments/planet8b-loro-v3/comparisons/matched_tiffs_all_retained_v2`;
  `matched_tiffs_all_retained_v1` is superseded/invalid, and `matched_tiffs_v1`
  remains historical non-overlapping-input evidence with the same small-chip
  alignment limitation.
