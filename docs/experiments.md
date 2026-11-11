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
fields. Do not infer them from a run name. Recipes supply a descriptive `name`
for the automatic `<name>-<UTC timestamp>` run ID and a separate `experiment`
for assignment selection (currently `baseline` only).

Local machine-readable records are required even when W&B is offline. Keep the
implementation small; the legacy registry schema is not a compatibility target.
Checkpoints, settings, dataset references, and compact results must be recoverable
outside ephemeral compute, using Box as specified in `data_artifacts.md`.

Metrics use one slash-separated phase prefix: `train/loss_step` for logged
batch loss, `train/iou_step` for current-batch foreground IoU,
`train/loss` and `val/loss` for epoch loss, and `train/iou`,
`val/iou` (likewise precision, recall and F1) for pooled epoch metrics.
`train/auroc`, `val/auroc` and corresponding `calibration_error` metrics use
sigmoid probabilities, excluding -100 labels, pooled over the epoch. AUROC uses
257 uniform thresholds (a bounded-memory approximation); calibration error uses
15 uniform bins and L1 expected calibration error, with running bin totals
matching TorchMetrics BinaryCalibrationError. The calibration adapter avoids
retaining every epoch probability/label. AUROC inherits TorchMetrics computation
but uses histogram updates to avoid scanning each pixel once per threshold;
parity tests protect that dependency when the library is upgraded. Higher AUROC and lower calibration
error are better. Background prevalence influences both, so keep foreground IoU,
precision and recall alongside them. Accuracy is no longer logged.
Batch IoU uses the same .5 threshold, ignored -100 pixels and zero for undefined
IoU as epoch metrics, without changing their accumulation. Step metrics log every
optimizer update; with accumulation they describe its final microbatch.
Each configured term has an implementation `type`, independent unique logging
`name`, positive `weight` and loss-specific `parameters`. Types may repeat; names
may not. Pooling and supported library options are explicit recipe choices.
Each configured term logs unweighted `train/<name>`, `val/<name>` and
`train/<name>_step` values. Epoch components use the same valid-pixel weighting
as combined loss, so `loss = sum(weight * component)` up to rounding. Default
recipes still use `bce` (0.1 label smoothing) and batch-pooled `lovasz` with weights
0.7 and 0.3. CSV and W&B use the same component names. See
[loss experiments](quickstart.md#configurable-loss-experiments) for supported
terms, parameter conventions and TOML examples.
CSV uses the same names. `val/pixels` records validation support and
`trainer/optimizer_updates` records completed updates. Keep native Lightning
`WandbLogger` global-step handling and existing logging frequency; do not mix in
manual `wandb.log(step=...)` calls. This follows W&B guidance on
[shared-prefix panel grouping](https://docs.coreweave.com/support/models/tags/experiments)
and [Lightning logging](https://docs.coreweave.com/products/wandb/integrations/lightning).
Optional native early stopping also monitors `val/iou` (mode max): patience counts
validation checks, min_delta requires a strictly larger gain. Default patience 0
disables it; BCE/Dice enables patience 10 and min_delta 0. The configured total
epoch budget still defines the LR schedule, and best-model export is retained.
Resume can increase an existing positive patience while keeping the saved best
score and wait count. Other recipe and membership changes remain rejected.
A completed early-stopped run can continue under that increase; its model/report
and settings/run metadata are moved into `completed-patience-<old patience>/`
before fitting, preserving prior selected outputs. Current best/last checkpoints
remain working recovery files and may be replaced normally. Dry-run is read-only.
Checkpoint selection monitors `val/iou`; completed-epoch resume preserves the
best score from preceding checkpoints that used `val_iou`. Existing W&B history
retains its old names; a running process adopts new names only after restart.

W&B prediction panels reuse existing forwards: a fixed validation sample across
regions plus background chips, and four augmented training examples each epoch.
The [quickstart](quickstart.md#prediction-panels-and-regional-metrics) describes
the media and regional metrics. Captions retain source/window identities;
ignored pixels stay explicit. Media are diagnostics, not a representative score.
Regional `val_region_<code>/` metrics pool validation pixels within each region,
with the same global metric semantics. They do not change checkpoint selection.

The separate `predict-chips` command runs after completion against the exported
selected model and saved validation membership. Optional `--split train` uses a
seeded sample of training sources with the same disjoint evaluation grid;
selection is label-blind and recorded in `windows.csv`. Training-only regions
and differing source composition must be stated when comparing scores.
The `report` command consumes those saved probabilities or image-only TIFF
predictions from `predict`, plus aligned labels/imagery. It shares confusion,
area, boundary, patch and probability diagnostics across both scopes without
loading a model. Report headings and outputs distinguish `chip_disjoint` from
`tiff_tiled` coverage. The primary threshold comes from saved model metadata;
train/validation sweeps are descriptive only and test reports omit them.
See [post-training diagnostics](quickstart.md#post-training-validation-diagnostics)
for recipes, definitions, coverage exclusions and the float32 inference distinction.

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

## Selected rebuild baseline recipe

The installed training command uses PyTorch Lightning automatic optimization,
native CSV logging/checkpointing and delayed EMA. It implements the historical
starting optimizer, batch and schedule values recorded in the [contract](../tasks/033e_training_validation_and_ema.md#selected-starting-recipes).
This preserves the new preprocessing and test isolation. The user selected the
existing 0.7 smoothed-BCE / 0.3 Lovasz loss, EMA with decay 0.999, equal epochs
for the BC comparison, and the newly measured **kelp-positive with-BC training
statistics**, computed after a **5000 upper cap**, for normalization. Use raw-unit
`(min(image, 5000) - mean) / std`, selecting statistics by band name and storing
the cap and values directly in recipes/model bundles. Detect native nodata
before clipping; training's final cap follows photometric augmentation and
precedes standardization. Validation/prediction use the same cap and statistics.
Training eligibility requires at least one kelp pixel per chip, using existing
manifest counts after split selection. Keep background-only canonical chips
and evaluation rows; report training exclusions separately. This filter belongs
to Task 033 and does not change Task 032B's published inputs or assignments.
The [Task 033 contract](../tasks/033_baseline_training_and_portable_models.md#selected-training-normalization)
owns the exact values and estimation scope. Use one fixed baseline reference
across spectral and BC variants; record its with-BC origin explicitly. A
without-BC run using it is not independent of BC-derived preprocessing.

This is a substantial change from the legacy Clay constants: Clay means are
about 4.5–5.3 times larger than the selected estimates. Give the new recipe a
distinct identity. Preserve the original normalization when loading a legacy
checkpoint. The selected estimates were recomputed after clipping at 5000;
earlier unclipped estimates are historical references. LORO cannot treat these
baseline estimates as training-only when they include its held-out region.

Keep ordinary training weights and EMA state in the recovery checkpoint; use
EMA for validation and the selected portable model after averaging begins.
Before the first averaging update, validate current weights. Augmentation
parameters must be checked with previews from the same transforms used in
training, including aligned masks and visible clipping/ignore behavior.
The first pass is [033A's isolated class previews](../tasks/033a_individual_augmentation_previews.md).
The user's 2026-11-02 direction replaces custom augmentation math with pinned
stock Albumentations 2.0.8, using actual native constructor parameters. Preview
and training use those implementations and the same input-domain scaling;
strengths must not be translated to another implementation afterward.
Preview adapters and the training Albumentations Compose use native uint16 /
65535, stock operations, raw-unit restoration and the final 5000 model cap.
Training then applies stock Normalize with the shared band-named constants
and ToTensorV2 inside that Compose. Stock clipping and zero-nodata boundary effects
are disclosed; there is no bespoke valid-weighted blur or mean-centered
contrast. Labels/validity remain paired; spatial holes have ignored targets.

The [selected ranges and composition](../tasks/033_baseline_training_and_portable_models.md#limits-selected-after-isolated-review)
use D4(p=1), then light Affine(p=0.5) outside SomeOf, followed by
SomeOf(n=2, replace=False, p=1); all eight pool children have
p=1 and equal selection eligibility. Stock SomeOf executes selected operations
in configured list order. Task 033B's combined preview uses this actual recipe,
the same kelp-rich training examples, clean/labeled close-ups and 2000 display
ceiling. The user approved the initial combined outputs and added affine jitter
during Task 033D review; the user also approved the updated affine previews. The recipe is saved
as [native Albumentations JSON](../configs/augment/baseline.json), checked against
the readable Python factory. Later training must consume this approved policy.
The native-eight-band preview drops exactly one eligible input band; later
3/4-band training must restrict dropout to that model's selected bands and
preserve physical identity. Reuse one seeded pipeline with advancing random
state in training; fixed per-draw seeds in the viewer are for inspection.
Smooth illumination, haze and misregistration remain excluded.

## Portable prediction model

Training exports the validation-selected `model/` bundle containing weights,
architecture settings, band names/order, normalization, and prediction settings
including threshold. The installed Python loader predicts supplied image arrays
offline without labels or original recipe paths. The installed `predict` command
extends it to tiled/georeferenced source rasters with explicit sparse-window
coverage; see the [prediction recipe](quickstart.md#predict-cleaned-source-tiffs).
Keep recipe/model identity and averaging semantics explicit. Verify that copying
the bundle to a fresh directory is enough to predict supplied imagery with the
installed package, without the old training registry, original config-directory
paths, or an online tracking service. Completed-epoch resume uses the separate `checkpoints/last.ckpt`, preserving
the saved run identity and total schedule. The recipe and selected memberships
must match; machine roots may relocate explicitly. Ordinary weights, optimizer,
scheduler, progress, random/sampling state and EMA restore through native
Lightning mechanisms. `deterministic = true` (the default) enables native
Lightning deterministic algorithms and its CUDA workspace configuration.
`deterministic = false` permits faster GPU kernels with numerical variation.
Both modes support completed-epoch continuation. With loader workers, worker
augmentation streams restart and sample order may differ after continuation;
the model, optimizer, scheduler, EMA and completed-epoch progress are restored.
Exact replay requires zero workers and deterministic execution from the start;
cross-device/software bitwise equivalence is not promised. Resume requires the
complete current settings and callback state; historical missing fields and
metric names are not migrated. Partial-epoch recovery is unsupported.
Bundle loading is model-only initialization and restores none of that training state.

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

Task [036B](../tasks/036b_temporal_error_analysis.md) implements temporal reporting
from one saved Task 036 report; Task 037 reuses it for comparisons. The primary
measure is agreement with the labels' proportional canopy change, not constant
predictions or constant absolute area error.

- Default pair intervals are 1–13 days and 29–47 days inclusive, configurable in
  the recipe. Pair only within dataset/release/region; retain same-day observations
  separately without temporal scoring. Optional explicit pairs restrict this
  date-based selection. Do not infer region/date metadata from filenames.
- Measure labels and predictions at both dates on the same common valid labeled
  and predicted footprint. Each percentage uses its own earlier kelp count:
  `100 * (after - before) / before`. Primary error is predicted minus labeled
  percentage change in percentage points. Equal +10% changes give zero error
  even when a model has constant multiplicative area bias.
- Zero earlier kelp makes that series' percentage undefined; percentage-point
  error needs both percentages. Preserve counts/areas and absolute change/error.
  Flag small nonzero baselines (default at most 10 pixels), without exclusions,
  pseudocounts or clipping. Labels may change over either interval.
- Compare only matching projected-metre grids with integer-aligned origins.
  Report unavailable comparisons, elapsed days, coverage and both starting
  counts. Pairwise footprints may differ; no fixed-footprint trend is inferred.
  Regional interval summaries give support plus median signed and mean/median
  absolute percentage-point error. Repeated pairs are not independent samples;
  uneven region composition must not masquerade as a statewide temporal result.
- Retain per-source/date confusion counts, scoreable area, labeled prevalence,
  signed area bias and separate false-positive/negative counts or area. Group
  by represented date, year, year-month and calendar month, pooling confusion
  counts before ratios. These are observation totals, not unique geographic area
  across acquisitions. Same-day overlapping observations are not silently mosaicked.
  Pool the declared evaluation scope for headline results and retain region
  identities. Preserve zero-kelp cases and undefined metrics. The [researcher recipe](quickstart.md#temporal-canopy-change)
  describes outputs and the separate no-inference command.

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

## Current Planet 8-band B0 baseline

Use the B0 model-size run `planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z`
as the selected 8-band reference after the [Task 037A validation decision](../tasks/037a_without_bc_launch.md#baseline-decision).
It uses the
[B0 recipe](../configs/train/model_size/b0.toml), with ordinary BCE plus Dice
on the canonical chips with `variant = "augmented"` (with BC). Use its
portable EMA bundle from completed epoch 16
(`checkpoint_epoch = 15`) at probability threshold 0.5.

- Local bundle: `/home/sky/data/model-size-runs/planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z/model`
- Box bundle: `kelp-box:kelpseg/runs/model-size-runs/planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z/model`
- Validation report: `/home/sky/data/model-size-runs/planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z/validation-report/report.html`

Both bundle files matched Box on 2026-11-10. The
[Task 041 alpha 0 run](../tasks/041_distance_weighted_bce_experiment.md#baseline-decision)
remains the control for the five-arm distance experiment.

## Local-to-GPU progression

Use CPU float32 inference and tiny training/validation/checkpoint checks on the
Mac. Validate all production plans and dataset paths before relocation. A
fresh-directory small-data walkthrough must exercise Box fetch through the
working pipeline. Local completion does not establish CUDA compatibility,
mixed-precision behavior, throughput, or production memory requirements; check
those on the selected GPU host before full experiments.

[Task 034](../tasks/034_gpu_machine_preparation_and_baseline_launch.md) owns the
remote-first setup procedure with a small local checklist/bootstrap handoff, environment/data
validation, hardware sizing, completed-epoch resume checks and initial baseline
launch. It does not depend on tiled prediction or scoring. Later tasks can
proceed locally while the baseline uses its fixed committed checkout, environment
and recipe remotely; integrate setup fixes through separate commits rather than
changing a running job. Task 039 reuses the setup procedure for the final
researcher walkthrough and does not repeat the initial relocation/launch gate.


Optional `checkpoint_epochs` retains specified one-based completed epochs in
addition to best/last, without changing checkpoint selection or validation
metrics. These native full checkpoints use the existing EMA save hooks and
can be exported for later inference. See the [LR comparison recipe](quickstart.md#controlled-learning-rate-comparison)
for the saved recipes and historical output root.


Model-size recipes select `encoder_name` from `mit_b0`, `mit_b1`, `mit_b2`,
or `mit_b3`. B3 remains the generic constructor default; current B0/B1 baseline
recipes select their encoder explicitly. Portable exports record the encoder and reconstruct it
when loaded; encoder changes are fresh experiments, not compatible resumes.
