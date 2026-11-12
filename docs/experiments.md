# Experiment and checkpoint contract

## Current Planet 8-band B0 baseline

Use the B0 model-size run `planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z`
as the selected 8-band reference after the [Task 037A validation decision](../tasks/037a_without_bc_launch.md#baseline-decision).
It uses the
[B0 recipe](../configs/train/model_size/b0.toml), with ordinary BCE plus Dice
on the canonical chips with `variant = "augmented"` (with BC). Use its
portable EMA bundle from completed epoch 16
(`checkpoint_epoch = 15`) at probability threshold 0.5.

The recoverable bundle is at
`kelp-box:kelpseg/runs/model-size-runs/planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z/model`.
After [connecting Box](box_backup.md#connect-box-on-a-local-machine), restore
the complete bundle into a fresh external directory:

```bash
(
  set -e
  model_dir="$HOME/kelpseg-models/planet8-b0-epoch16-01"
  test ! -e "$model_dir"
  rclone copy kelp-box:kelpseg/runs/model-size-runs/planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z/model \
    "$model_dir" --immutable --size-only --ignore-checksum
  test -f "$model_dir/model.json"
  test -f "$model_dir/weights.pt"
)
```

Set `model` in a [prediction recipe](guides/prediction_reporting.md#predict-cleaned-source-tiffs)
to this directory. Copy both files together; no training checkpoint, W&B login or
original training-directory path is needed for inference.
The task records retain the original host paths, validation report and backup
verification. The distance-weighting alpha-0 run is an experiment control,
not this selected baseline.

The constructor default remains B3 and generic recipes may use smoothed
BCE/Lovasz. Select the encoder and loss explicitly when reproducing the current
B0 recipe; do not infer them from defaults. Supported encoders are `mit_b0`,
`mit_b1`, `mit_b2` and `mit_b3`. Changing encoder starts a new experiment.

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
for assignment selection (`baseline` in the maintained training command).
Completed LORO study decisions and source recovery belong to
[Task 037](../tasks/037_baseline_comparisons_and_loro.md#037c-implementation-retirement--2026-11-12).
Portable LORO bundles use the maintained prediction commands.

Local machine-readable records are required even when W&B is offline. Keep the
implementation small; the legacy registry schema is not a compatibility target.
Checkpoints, settings, dataset references, and compact results must be recoverable
outside ephemeral compute, using the [artifact policy](data_artifacts.md).

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
[loss experiments](guides/training.md#configurable-loss-experiments) for supported
terms, parameter conventions and TOML examples.
CSV uses the same names. `val/pixels` records validation support and
`trainer/optimizer_updates` records completed updates. Keep native Lightning
`WandbLogger` global-step handling and existing logging frequency; do not mix in
manual `wandb.log(step=...)` calls. This follows W&B guidance on
[shared-prefix panel grouping](https://docs.coreweave.com/support/models/tags/experiments)
and [Lightning logging](https://docs.coreweave.com/products/wandb/integrations/lightning).
Optional native early stopping also monitors `val/iou` (mode max): patience counts
validation checks, min_delta requires a strictly larger gain. Default patience 0
disables it; the selected B0 recipe uses patience 20 and min_delta 0. The configured total
epoch budget still defines the LR schedule, and best-model export is retained.
Resume can increase an existing positive patience while keeping the saved best
score and wait count. Other recipe and membership changes remain rejected.
A completed early-stopped run can continue under that increase; its model/report
and settings/run metadata are moved into `completed-patience-<old patience>/`
before fitting, preserving prior selected outputs. Current best/last checkpoints
remain working recovery files and may be replaced normally. Dry-run is read-only.
Checkpoint selection monitors `val/iou`. Resume requires the current callback
and settings state; retired metric-name formats are not migrated.

W&B prediction panels reuse existing forwards: a fixed validation sample across
regions plus background chips, and four augmented training examples each epoch.
The [training guide](guides/training.md#prediction-panels-and-regional-metrics) describes
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
See [post-training diagnostics](guides/prediction_reporting.md#post-training-validation-diagnostics)
for recipes, definitions, coverage exclusions and the float32 inference distinction.

## Initialization, fine tuning, and resume

Distinguish three operations:

- Generic pretrained initialization starts a new run with the chosen band's
  input adaptation and fresh optimizer/scheduler state.
- Kelp-checkpoint initialization starts a new fine-tuning run from model weights
  with fresh optimizer/scheduler state; record source checkpoint and any changes.
- Interrupted-run resume restores model, optimizer, scheduler, progress, and
  relevant averaging state for the same run and input identity.

For new regions, identify the four cases in [product.md](product.md) separately.
The installed `train` command currently starts from `encoder_weights = "imagenet"`
or `"none"`, or resumes its own completed-epoch checkpoint. It has no recipe
setting for initializing a fresh fit from a kelp bundle. Bundle loading supports
inference; it is not a fine-tuning command. The complete transfer recipes and
kelp-initialized fitting remain planned under Task 039. Keep fixed
new/old held-out scopes. Choose combined-data initialization and sampling
explicitly when that experiment is scoped; do not assume staged continuation.

Select checkpoints using validation only. Keep a best checkpoint and an exact
recovery checkpoint as distinct artifacts. Record whether inference uses raw or
averaged weights; preserve EMA semantics if retained. Test save/load and resume
locally, including the difference from new fine-tuning initialization.

## Preprocessing and training policy

Use raw-unit `(min(image, 5000) - mean) / std` with the exact band-named values
in the chosen recipe and exported bundle. Detect native nodata before clipping.
Training applies its final cap after photometric augmentation and before
standardization; validation and prediction use the same cap and constants.
Do not estimate replacement statistics when loading a model. Normalization
provenance and qualifications for the completed LORO study remain in its
[task/write-up](../tasks/037_baseline_comparisons_and_loro.md).

Training requires kelp-positive chips using manifest counts after split
selection. Keep background-only chips in the canonical collection and evaluation;
report training exclusions separately. Train/validation inputs use the same
band selection, normalization and ignore handling as prediction.

The installed trainer uses Lightning automatic optimization, CSV logging,
checkpointing and delayed EMA (decay 0.999). Recovery checkpoints preserve
ordinary weights and EMA state. Validation and portable exports use EMA after
averaging begins, and ordinary weights beforehand. Optional `checkpoint_epochs`
retains listed one-based completed epochs in addition to best/last; it does not
change validation selection.

The augmentation policy is [native Albumentations JSON](../configs/augment/baseline.json):
D4(p=1), light Affine(p=0.5), then SomeOf(n=2, replace=False, p=1).
All eight pool children have equal eligibility; selected operations execute in
configured list order. Preview and training use the same stock Albumentations
2.0.8 operations and constructor parameters, native uint16/65535 scaling,
raw-unit restoration and final 5000 cap. Training ends with Normalize and
ToTensorV2. Spatial holes have ignored targets. Stock clipping and zero-nodata
boundary effects remain visible in previews; there is no custom blur/contrast
replacement. Dropout only uses the model's selected bands. Training advances
one seeded pipeline; fixed viewer seeds are for inspection. Smooth illumination,
haze and misregistration are excluded. See the [diagnostic guide](guides/diagnostics.md)
for previews and the [training guide](guides/training.md) for settings.

## Portable prediction model

Training exports the validation-selected `model/` bundle containing weights,
architecture settings, band names/order, normalization, and prediction settings
including threshold. The installed Python loader predicts supplied image arrays
offline without labels or original recipe paths. The installed `predict` command
extends it to tiled/georeferenced source rasters with explicit sparse-window
coverage; see the [prediction recipe](guides/prediction_reporting.md#predict-cleaned-source-tiffs).
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
record these choices in the resolved recipe.

`temporal-report` reads one saved labeled report. The primary
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
  identities. Preserve zero-kelp cases and undefined metrics. The [researcher recipe](guides/diagnostics.md#temporal-canopy-change)
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

## Local-to-GPU progression

Use CPU float32 inference and bounded training/checkpoint checks locally. Follow
the [tiny walkthrough](quickstart.md) before a production experiment. Check
CUDA, mixed precision, memory and throughput on the actual GPU host using
[GPU setup](gpu_setup.md); local success does not establish those properties.
Keep production code, environment and recipe fixed while a run executes.
