# Task 017: Build overlap-aware chip and source-TIFF evaluation

Status: Pending

Depends on: Tasks 003 and 015

Execution: Remote-aware code task using the completed baseline checkpoint.

## Abstract

Build standardized inference that preserves chip diagnostics but reconstructs
overlapping predictions onto each source TIFF grid before calculating the
default per-TIFF metrics. With 1024 chips and 512 stride, summing chip confusion
counts would double-count overlap pixels and produce invalid TIFF/region
accuracy. This task implements one probability-combination, threshold, coverage,
and metric contract and validates it on synthetic overlap plus the baseline test
set. Task 018 runs it for every model.

## Goal

Create a resumable evaluator that loads a recorded best checkpoint, predicts a
fold's test chips, reconstructs unique covered source pixels, and writes
auditable chip/TIFF/region/test-set results tied to run and manifest hashes.

## Inputs

- Task 003 approved overlap contract and chip window manifest fields
- Task 015 baseline best checkpoint and W&B/registry identity
- Task 011 baseline test fold manifest
- Canonical chip/raster manifests and portable `raster_metadata.csv`
- `src/models/smp.py`
- `src/data.py`
- `trainer.py`
- `docs/product.md`
- `docs/architecture.md`
- `docs/experiments.md`

## User decisions required

Confirm before implementation:

1. Overlap combination. Recommendation recorded in Task 003: average foreground
   probabilities for each covered source pixel, then threshold once.
2. Binary threshold. Recommendation: fixed `0.5` unless a threshold was selected
   from validation data before test evaluation. Never optimize it on test.
3. Prediction raster retention:
   - recommended: save per-source georeferenced foreground-probability and
     binary-mask GeoTIFFs locally/remotely, but log only compact tables and
     selected examples to W&B;
   - lower-storage option: save counts/tables plus a small QA sample of rasters.
4. Compression/dtype for probability rasters if retained. Recommendation:
   float32 tiled/compressed GeoTIFF for probabilities and uint8 compressed
   GeoTIFF for masks.

Record exact choices here and in `docs/experiments.md`.

## Planned CLI

Recommended entry point:

```bash
uv run python scripts/evaluate_planet8b_run.py \
  --run-key baseline-temporal-v1 \
  --registry <experiment_registry.jsonl> \
  --fold-manifest <baseline>/fold_manifest.csv \
  --chip-manifest <canonical>/chip_manifest.csv \
  --raster-manifest <canonical>/raster_manifest.csv \
  --raster-metadata <canonical>/raster_metadata.csv \
  --output-root <predictions-root>/baseline-temporal-v1 \
  --threshold <approved-value> \
  [--save-rasters] \
  [--resume]
```

Run identity, checkpoint, fold hash, and W&B ID come from the registry. Explicit
overrides must be recorded and must not silently replace identity.

## Reconstruction contract

For each source TIFF:

1. Allocate foreground-probability sum and coverage-count arrays for the source
   pixel grid, or use a memory-bounded windowed equivalent.
2. Place every chip probability into the recorded `row_off`, `col_off`, width,
   and height window.
3. Assert overlapping ground-truth labels agree wherever both are non-ignore;
   disagreement is fatal.
4. Divide probability sum by coverage count where coverage is positive.
5. Threshold the averaged probability once.
6. Score only pixels with positive coverage and ground truth not equal to
   `-100`.
7. Report uncovered pixels, ignored pixels, coverage-count distribution, and
   scored fraction.

Do not use chip loop order or filename suffix to infer windows. Do not count a
source pixel more than once in TIFF confusion counts.

If full source arrays are too large, implement block/window accumulation with
the same mathematical result and test equivalence.

## Metric contract

For binary segmentation, write unique-pixel TIFF counts:

```text
true_negative,false_positive,false_negative,true_positive,
ignored_pixel_count,uncovered_pixel_count,covered_pixel_count,
scored_pixel_count,total_source_pixel_count
```

Derive, with explicit zero-denominator behavior:

```text
accuracy,kelp_precision,kelp_recall,kelp_f1,kelp_iou,background_iou,
macro_iou,dice
```

Region and full-test metrics sum TIFF confusion counts first, then derive
metrics. Chip metrics are diagnostic only and must be labeled non-additive when
chips overlap.

## Output contract

```text
<run-output>/
  evaluation_metadata.json
  chip_diagnostics.csv
  tiff_metrics.csv
  region_metrics.csv
  test_summary.json
  source_predictions/<source_tiff_id>_probability.tif   # if approved
  source_predictions/<source_tiff_id>_mask.tif          # if approved
  logs/evaluation.log
```

All tables include experiment version, run key, W&B run ID, fold ID, held-out
region, checkpoint hash, fold-manifest hash, source TIFF, region, and date where
applicable.

## Restartability

- Use per-source completion metadata keyed by checkpoint/fold/threshold/schema
  hashes.
- Resume verifies outputs before skipping.
- Changed checkpoint, threshold, fold, or schema requires a new output version
  or explicit invalidation.
- Consolidated tables write atomically from verified per-source results.

## Plan / spec requirement

Before code edits, add a plan covering model-logit/probability conversion,
window reconstruction, memory bounds, label consistency, metric formulas,
zero-denominator handling, raster georeferencing, resume keys, and W&B logging.

## Smoke tests

1. Synthetic 2x-overlap case with analytically known averaged probabilities and
   confusion counts.
2. Ignore pixels in single and overlapping windows.
3. Uncovered border pixels from discarded partial chips.
4. Conflicting overlapping ground truth must fail.
5. Zero-positive ground truth/prediction denominator cases.
6. One real baseline source TIFF end to end, including raster alignment if
   retained.

## Validation

```bash
uv run ruff format --check scripts src tests
uv run ruff check scripts src tests
uv run pytest tests/test_evaluate_planet8b_run.py
git diff --check
```

Baseline test validation:

- test chip/source counts match Task 011 fold manifest;
- every predicted chip belongs to the baseline test split;
- TIFF scored plus ignore/uncovered accounting reconciles to source dimensions;
- region/full counts equal sums of TIFF counts;
- probability/mask rasters match source CRS, transform, shape, and bounds;
- W&B artifact/table identity matches the baseline run and checkpoint.

## Acceptance criteria

- Synthetic overlap proves unique-pixel TIFF metrics.
- Baseline test evaluation completes with validated source coverage.
- Chip diagnostics cannot be mistaken for additive pooled metrics.
- Per-TIFF output is the default comparison surface.
- Resume and identity mismatch behavior are tested.
- Task 018 can enumerate/run the evaluator without manual path editing.

## Non-goals

- Do not run all LORO predictions.
- Do not tune the threshold on baseline test data.
- Do not compare baseline and LORO performance yet.
- Do not average chip IoUs or sum overlapping chip confusion counts.

## Review pass

- ML researcher: verify threshold, metrics, aggregation, and test isolation.
- Remote-sensing researcher: verify source-grid reconstruction, coverage, and
  georeferencing.
- Risk-averse engineer: verify checkpoint/fold identity and resume invalidation.

## Outcome template

Record user decisions, CLI/schema, reconstruction/metric formulas, tests,
baseline evaluation artifacts/counts/coverage, W&B artifact, validation, and
Task 018 command template.
