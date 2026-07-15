# Product and research contract

For navigation and current task status, start with `docs/index.md`. Read this
file when work may change the research goal, claim boundary, split meaning,
success criteria, or non-goals.

## Purpose

The active project tests how well a binary kelp segmentation method trained on
8-band PlanetScope imagery generalizes across geographic regions.

It has two connected experiments:

1. A new standard baseline trained on the expanded dataset, with every region
   contributing temporally separated train, validation, and test source TIFFs.
2. One leave-one-region-out model per region, with the complete held-out region
   used for testing.

The baseline establishes in-domain performance under temporal separation. LORO
establishes performance when the target geography is absent from training.

## Dataset scope

- 339 paired California source TIFFs across region IDs `ca_001`–`ca_011`.
- 30 paired BC 10-km tiles represented as region ID `bc`.
- 369 source TIFFs total.
- Region IDs are canonical. Names are descriptive metadata and need not be
  unique; `ca_005` and `ca_006` are both currently named `channelIslands`.

The supplied segmentation labels define evaluation truth for this study. The
project does not independently establish ecological truth outside those labels
or claim performance outside the sampled regions, dates, sensors, and
preprocessing contract.

## Split and evaluation contract

- Baseline source TIFFs are split chronologically within each region.
- Acquisition-date groups remain intact.
- Chips inherit their source TIFF's baseline split.
- LORO test sets contain every retained chip in the held-out region.
- Nodata policy is selected and applied before any experimental split.
- Background-only removal may affect training selection, not canonical or
  evaluation data.
- Test data is not used to select preprocessing thresholds, checkpoints, or
  hyperparameters.

Primary cross-run comparison uses source TIFFs that are unseen by both models:
the intersection of a region's baseline temporal-test TIFFs and that region's
LORO test set. Full-region LORO performance is reported separately.

## Success criteria

- Every data and split assignment is reproducible from portable manifests.
- Source TIFF and region identity survive chipping, filtering, training, and
  prediction.
- Baseline and LORO runs share the same model and training policy unless a task
  explicitly records a controlled change.
- W&B exposes enough live context to identify each run, dataset, fold, and
  checkpoint.
- Predictions retain chip diagnostics and unique-pixel source-TIFF confusion
  counts after overlap reconstruction.
- Final reporting separates paired matching-TIFF comparisons from full-region
  LORO results.

## Current non-goals

- Non-PS8B dataset and deployment workflows.
- Architecture sweeps before the baseline/LORO evaluation harness works.
- Random chip-level splitting or treating chip count as independent geographic
  sample size.
- Tuning on held-out test regions or baseline temporal-test TIFFs.
- Treating average chip IoU or summed overlapping-chip counts as TIFF or region
  IoU.
- Claiming universal kelp-mapping accuracy from this bounded experiment.
- Deleting or rewriting legacy code merely because it is outside current scope.
