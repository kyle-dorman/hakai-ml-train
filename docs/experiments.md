# Experiment and checkpoint contract

## Tracking and identity

Keep W&B at `kdorman90-ucla/kelpseg`. The completed `planet8b-loro-v3` suite and
all earlier suite identities are historical. New datasets and model recipes
receive distinct run/group/output identities; do not resume or relabel old
experiments as part of the rebuild. Keep smoke runs separate from production.

Each run records dataset release, split/manifest reference, band
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

Use a recorded validation-selected checkpoint and a pre-test threshold. During
training, ordinary chip validation uses the selector's non-overlapping windows
and aggregate confusion counts, without TIFF reconstruction each epoch. Training
chips may overlap. Keep test held out until model selection is finished;
chip-based test applies the same disjoint-window rule.

Reuse existing chips and report geometric uncovered edges/gaps, including when
multiple crops share one original source. Do not silently replace nodata-omitted
nominal windows with overlapping alternatives. Record input footprint, nominal
disjoint-grid area, retained selected area and omissions separately; geometry
alone does not count valid labels. Never call an average chip IoU a region IoU.

Post-training tiled prediction/source scoring combines overlapping probabilities
before thresholding, with one prediction per covered source pixel. Export
georeferenced probabilities/masks and compact TIFF/region summaries as needed.
Record coverage and ignored pixels, and distinguish these TIFF results from
chip-scope validation/test metrics.

Compare baseline and LORO on matching source TIFFs unseen by both models;
full-region LORO remains a separate summary. Reuse source assignments and
training policy across spectral comparisons unless the experiment explicitly
controls a change. No held-out results select preprocessing or model settings.

For the current California-focused comparison, regions 001–010 (including Baja)
provide evaluation scopes; 011/012 are a single optional training-only group.
The run including both BC regions (`augmented`) is the primary baseline;
without both (`base`) is the comparison. Compare inclusion versus exclusion of
that group on identical evaluation-region source assignments, with no 011/012
validation or held-out fold. Keep CA source
membership, band recipe, initialization, checkpoint/threshold selection rules
and evaluation coverage matched. Declare the sampling and training budget so
extra BC data and extra optimization are distinguishable experiment choices;
those recipe details are selected in the training task.

Tasks 035/036 must add temporal-consistency reporting alongside pooled accuracy:

- Retain per-source/date confusion counts, scoreable/covered area and labeled
  kelp prevalence; summarize by region, represented year and represented month.
  Report precision, recall, F1/IoU and absolute false-positive/negative counts
  or area, including zero-kelp cases and explicit undefined metrics.
- Show signed area error (predicted minus labeled kelp) across dates within
  each location. Compare changes across dates on common valid labeled footprints
  where supported, resolving overlapping observations before calling an area
  unique. Report available pairs, season/date gaps and coverage; unsupported
  comparisons remain unavailable rather than fabricated.
- Use both pooled source-pixel metrics and region/date summaries, keeping
  California and Baja scope explicit. Examine shared temporal shifts in error
  where dates/months overlap; changing region composition must not masquerade
  as a statewide annual bias. Sparse support limits trend conclusions.

Do not choose favorable test dates or remove low-kelp periods to increase F1.
Audit label support before fixing a scientifically declared split, and preserve
its representative low/zero-kelp cases. Low F1 in low-prevalence imagery needs
the accompanying error counts; it is not evidence by itself of temporal drift.
Acquisition month and label counts do not establish tide, growth or annotation
causes. Test label-based error stability, not constant predictions through time.

Future-date tests and strict future-year extrapolation are distinct scopes.
If claiming no training data from a future year, enforce that cutoff for all
training regions, including 011/012. Region-specific later-date tests may have
other regions' later imagery in training and must be described accordingly.

## Local-to-GPU progression

Use CPU float32 inference and tiny training/validation/checkpoint checks on the
Mac. Validate all production plans and dataset paths before relocation. A
fresh-directory small-data walkthrough must exercise Box fetch through the
working pipeline. Local completion does not establish CUDA compatibility,
mixed-precision behavior, throughput, or production memory requirements; check
those on the selected GPU host before full experiments.
