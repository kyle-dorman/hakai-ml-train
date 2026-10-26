# Experiment and checkpoint contract

## Tracking and identity

Keep W&B at `kdorman90-ucla/kelpseg`. The completed `planet8b-loro-v3` suite and
all earlier suite identities are historical. New datasets and model recipes
receive distinct run/group/output identities; do not resume or relabel old
experiments as part of the rebuild. Keep smoke runs separate from production.

Each run records dataset release, split/manifest identity and hashes, band
names/order, normalization, model and initialization, resolved recipe, seed,
budget, participating regions, checkpoint selection, Git commit, runtime,
status, and output paths. Held-out region and adaptation case are explicit
fields. Do not infer them from a run name.

Local machine-readable records are required even when W&B is offline. Keep the
implementation small; the legacy registry schema is not a compatibility target.
Checkpoints, settings, dataset references, and compact results must be recoverable
outside ephemeral compute, using Box as specified in `data_artifacts.md`.

## Initialization, fine tuning, and resume

Distinguish three operations:

- Generic pretrained initialization starts a new run with the chosen band's
  input adaptation and fresh optimizer/scheduler state.
- Kelp-checkpoint initialization starts a new fine-tuning run from model weights
  with fresh optimizer/scheduler state; record source checkpoint and any changes.
- Interrupted-run resume restores model, optimizer, scheduler, progress, and
  relevant averaging state for the same run and input identity.

For new regions, identify the four cases in `product.md` separately. Keep fixed
new/old held-out scopes. Choose combined-data initialization and sampling
explicitly when that experiment is scoped; do not assume staged continuation.

Select checkpoints using validation only. Keep a best checkpoint and an exact
recovery checkpoint as distinct artifacts. Record whether inference uses raw or
averaged weights; preserve EMA semantics if retained. Test save/load and resume
locally, including the difference from new fine-tuning initialization.

## Portable prediction model

Tasks 033–034 save a model bundle containing weights, architecture settings,
band names/order, normalization, and prediction settings including threshold.
Keep recipe/model identity and averaging semantics explicit. Verify that copying
the bundle to a fresh directory is enough to predict supplied imagery with the
installed package, without the old training registry, original config-directory
paths, or an online tracking service. Exact interrupted-run recovery may use
its separate checkpoint with optimizer/scheduler/progress state.

## Legacy gut check

Task 025 captures a few preselected development chips using the downloaded
SegFormer B3 checkpoint, saved inputs/labels, original-footprint probabilities,
masks, and previews. It is a visual gut check, not a full training reproduction
or a benchmark to tune against. Record device/precision and compare numerically
only within a documented tolerance; no CUDA-equivalence claim is required.

The checkpoint contains averaged inference weights under `state_dict` and
separate ordinary training weights under `current_model_state`; reverify that
loading contract during capture. Preserve its actual deterministic test
preprocessing, including eight-band normalization and centered-pad inversion.

## Evaluation and comparison

Use a recorded validation-selected checkpoint and a pre-test threshold. Keep
chip diagnostics for traceability, but calculate primary metrics from one
prediction per covered source pixel. Export georeferenced probabilities/masks
and compact TIFF/region summaries as needed. Record coverage and ignored pixels.

Compare baseline and LORO on matching source TIFFs unseen by both models;
full-region LORO remains a separate summary. Reuse source assignments and
training policy across spectral comparisons unless the experiment explicitly
controls a change. No held-out results select preprocessing or model settings.

## Local-to-GPU progression

Use CPU float32 inference and tiny training/validation/checkpoint checks on the
Mac. Validate all production plans and dataset paths before relocation. A
fresh-directory small-data walkthrough must exercise Box fetch through the
working pipeline. Local completion does not establish CUDA compatibility,
mixed-precision behavior, throughput, or production memory requirements; check
those on the selected GPU host before full experiments.
