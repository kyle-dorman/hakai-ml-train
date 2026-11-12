# Methods

For a concise paper-oriented outline, see [paper methods](paper_methods.md).

This document describes the implemented binary kelp segmentation workflow for
Planet imagery. Results measure agreement with supplied labels over the reported
imagery and coverage. They do not establish independent ecological truth or
performance in unrepresented regions. Use the [quickstart](quickstart.md) and
[operating guides](index.md) for commands; [experiments](experiments.md) identifies
the selected model and recoverable artifacts.

## Inputs, identity and valid pixels

Preparation keeps immutable original imagery and labels separate from organized,
cleaned and chipped releases. Organization preserves TIFF contents while recording
names and regional identities. Cleaning writes a separate release with aligned
image/label grids. Dataset/release, region, acquisition date, original source TIFF,
physical spacecraft, crop offsets, native band order and spatial grid identify
observations. Chip windows retain their position and true dimensions within the
original source. These identities allow crops to share one source assignment and
later be reconstructed without counting their overlap twice.

Cleaned images are uint16, with all-native-band zero representing nodata and
`nodata=0` in the TIFF. A zero in just one band is not sufficient to mark a pixel
invalid. Original nodata is detected before values are rewritten. For paired
inputs, label coverage is aligned to the image: matching grids are read directly;
supported differing grids use nearest-neighbor alignment of stored label values.
Stored background zero remains background regardless of label nodata metadata.
Outside-label coverage is already excluded by writing image zero and stored
label ignore 3. Image-only cleaning preserves valid imagery without requiring
labels. Existing label ignore 3 can also occur over otherwise valid imagery.

The default stored-label mapping is 0, 2 and 4 → background 0; 1 → kelp 1;
3 → ignore -100. Chipping maps these values, with image nodata also forcing
-100. Reporting applies the declared mapping when reading cleaned labels.
Ignored targets do not enter losses or confusion counts. Imagery validity,
label validity and prediction coverage remain separate concepts: an ignored
label is not a negative observation, and a missing prediction is not background.

See [preparation](guides/preparation.md) for accepted grids and schemas.
These rules are implemented in [cleaning](../src/kelpseg/prepare/clean.py),
[label alignment](../src/kelpseg/prepare/alignment.py) and
[chipping](../src/kelpseg/prepare/chip.py), with checks in
[cleaning tests](../tests/test_clean.py) and [chip tests](../tests/test_chip.py).

## Partitioning observations

Assignments are made for original source TIFFs before selecting chip windows.
Every crop and chip of an original inherits its role; chips from one TIFF cannot
cross train, validation and test. Spectral comparisons reuse these assignments.
Within each experiment and membership variant, observations from one region/date
cannot contribute to different train/validation/test partitions. The same rule
applies to a physical spacecraft on one UTC date, including crops in different
regions. Explicitly unused observations contribute to none of these partitions. The same spacecraft on different dates may cross partitions.
The spacecraft identity comes from declared metadata or the original filename
convention, not a crop suffix. Conflicting date/spacecraft assignments fail
validation rather than being split automatically.

The [current split recipe](../configs/split/ca_bc_v1.toml) uses region-specific
inclusive date cutoffs. Forward chronology assigns early, middle and late dates
to train, validation and test; reverse chronology swaps train and test. Regions
001–008 use reverse chronology and 009–010 use forward chronology. This is a
region-specific temporal holdout, not a uniform future-year test. A strict
future-year claim would require the cutoff to hold for all training regions.

Regions 001–010, including Baja, supply evaluation scopes. Regions 011 and 012
are a joint optional training-only group: `augmented` includes both and `base`
excludes both, with evaluation-region assignments unchanged. Neither BC region
contributes validation or a held-out region fold. The selected baseline uses
`augmented`; this membership name does not refer to image augmentation.

Leave-one-region-out (LORO) assignments put the entire held-out region into test.
Other regions retain their temporal train/validation roles; their temporal test
sources remain unused. Any other-region observation sharing a held-out test
spacecraft/date is also unused, including optional training imagery. These
exclusions affect assignments, not canonical data. Full-region LORO results and
comparisons on matching TIFFs unseen by both models are separate scopes.

The maintained splitter implements these assignments, while the maintained
training command is for the baseline. Completed LORO training orchestration is
archived. Its normalization provenance, study-specific qualifications and recovery
references remain in the [LORO study record](../tasks/037_baseline_comparisons_and_loro.md).
Existing LORO bundles can use maintained prediction/reporting. New-region fitting
recipes remain future work.

The [split implementation](../src/kelpseg/prepare/splits.py) and
[split tests](../tests/test_splits.py) cover source inheritance, region/date and
cross-region spacecraft/date isolation, held-out companions and optional regions.

## Canonical chips and evaluation scope

The standard [chipping recipe](../configs/chip/planet8.toml) uses 512-pixel
windows with stride 256. The regular grid does not shift trailing windows inward;
partial edge chips are stored at their true source size. Windows with more than
50% image nodata are omitted from payloads but retain manifest records and reasons.
The fraction uses true source pixels, excluding artificial loading padding.
Retained background-only chips stay in the canonical collection.

Training eligibility is a separate selection: the loader requires a retained
training chip to have `kelp_pixels > 0` in its manifest counts. It records excluded
training rows without altering assignments or deleting canonical backgrounds.
Evaluation retains background-only windows, subject to geometric selection and
nodata omissions. Thus training scores describe a different sampled population
from representative validation.

Training windows may overlap. Chip validation instead selects a deterministic
disjoint subset of existing windows in original-source coordinates, considering
crop keys and numeric row/column order. Different crops of one original share
that exclusion. An omitted nominal window still reserves its footprint; an
overlapping alternative does not replace it. This avoids repeated scored pixels,
but can leave interior gaps and edge strips. Coverage records distinguish input
crop union, nominal disjoint-grid area, retained area and omitted/uncovered area
in the selector logs. These geometric areas are not counts of valid labels and
are separate from the saved report coverage described below.

Training validation uses this disjoint scope each epoch, without full-TIFF
reconstruction. The selector also supports disjoint test windows, but the installed
`predict-chips` command exposes validation or sampled training diagnostics only.
Held-out TIFF evaluation uses `predict` then `report` after selection is frozen.
The saved report labels the scope `chip_disjoint` or `tiff_tiled`; their scores
are not interchangeable. See [window-selection tests](../tests/test_splits.py)
and [training-input tests](../tests/test_training_data.py).

## Bands, augmentation and normalization

One native-band collection supplies the spectral variants. Selection uses
explicit physical band names or validated indices, preserving requested order:

| Recipe | Model input order |
|---|---|
| `planet8` | coastal_blue, blue, green_i, green, yellow, red, rededge, nir |
| `planet4` | red, green, blue, nir |
| `planet3` | nir, red, green |
| `planet_RGB` | red, green, blue |

Native validity is computed before band selection, capping or augmentation and
carried as a mask. Selected bands becoming zero do not redefine nodata.
Loading pads only the bottom/right to the model canvas, with image fill zero and
label fill -100. True height/width and `(top, bottom, left, right)` padding are
explicit. During training, spatial augmentation can move padding; the transformed
validity mask identifies it. Unaugmented validation and inference retain the
bottom/right placement. Their predictions are cropped to the true dimensions
before source placement; offsets are never inferred from labels.

Training uses the shared [Albumentations policy](../configs/augment/baseline.json):
a random rotation/reflection from the eight square symmetries (D4), a light
affine transform with probability 0.5,
then two distinct operations from an equally eligible eight-operation pool.
The pool contains brightness, contrast, blur, Gaussian noise, sharpening, coarse
spatial dropout, constant additive noise and single-channel dropout. Selected
operations execute in configured order. The JSON records exact parameter ranges;
preview tools use the same factory. Spatial transformations move labels/validity
with nearest-neighbor mask interpolation; introduced holes have ignored targets.
Channel dropout acts only on the model's selected bands. Validation and inference
have no random augmentation or test-time augmentation.

Photometric augmentation uses the stock uint16/65535 scaling, then restores raw
units. The final upper cap is 5000, applied after augmentation and before
standardization. For each selected band, valid pixels use
`(min(raw_value, 5000) - mean) / std`, with the fixed, band-named constants in the
recipe and exported bundle. There is no per-image estimation or replacement of
statistics at model loading. The current loader validates these constants against
the supported fixed reference; arbitrary replacement normalization is unsupported.
Invalid pixels are restored to normalized zero.
Validation and prediction use the same cap and constants. Stock operation clipping
and nodata-boundary effects remain visible in previews.

The optional pixel-statistics utility computes streaming means and sample standard
deviations on training chip imagery. By default it includes background-only chips
and applies no cap; kelp-positive chip selection and an upper cap are explicit
options. Even with kelp-positive selection, statistics include all native-valid
image pixels in those chips, not only labeled kelp pixels. Labels and loading
padding do not enter the calculation. All-native-band-zero pixels are excluded
before any cap, and overlap counts as repeated chip exposure. This utility does
not silently change a model's normalization. Study-specific LORO provenance
stays in the study record linked above.

See [input transforms](../src/kelpseg/training/transforms.py),
[preprocessing](../src/kelpseg/preprocessing.py),
[padding/band tests](../tests/test_chip_loading.py) and
[training-input tests](../tests/test_training_data.py).

## Model fitting and selection

The implementation uses SegFormer with a supported MiT B0/B1/B2/B3 encoder,
8/4/3 selected inputs and one foreground logit. A sigmoid converts logits to
kelp probabilities. The selected reference is the with-BC eight-band B0 model,
using the [B0 recipe](../configs/train/model_size/b0.toml): ImageNet encoder
initialization, 0.7 binary cross-entropy (BCE) plus 0.3 Dice overlap loss, without
BCE label smoothing.
Generic constructor/recipe defaults remain B3 and smoothed BCE/Lovasz; they do
not describe the selected model. For ImageNet initialization, three inputs retain
the RGB input kernels; four/eight inputs repeat them cyclically and scale by
3 / input-channel-count. This is positional initialization, not an assignment of
pretrained physical-band meaning.

The selected recipe uses AdamW, learning rate 0.00015, betas (0.9, 0.95), weight
decay 0.01, batch size 12 and accumulation over two batches. Bias and normalization
parameters have no weight decay. The schedule has five warmup epochs within a
70-epoch budget, followed by cosine decay to 0.000003; it advances per optimizer
update. The first update uses zero learning rate. Gradient clipping is 0.8.
Production settings use bf16 mixed precision and seed 42, with deterministic
execution disabled. The recipe retains these choices so model identity does not
rest on the encoder name alone. A full training epoch shuffles the eligible chips
and visits each once, without region balancing or replacement sampling; overlapping
chips therefore repeat some source pixels.

All objective terms mask -100 and reduce in float32. The selected BCE and Dice
terms pool their supported pixels across each microbatch (gradient accumulation
does not enlarge this pooling group); epoch losses weight batch objectives by
valid pixel count. Epoch intersection-over-union (IoU), precision, recall and F1
pool pixel counts rather than averaging batch scores. Training metrics reflect augmented eligible
chips; validation uses unaugmented disjoint windows.

Checkpoint selection maximizes validation IoU at probability threshold 0.5,
retaining the earlier best on a tie. No test result chooses a checkpoint,
threshold, preprocessing or recipe. Early stopping in the selected recipe uses
20 validation checks without improvement; the original budget still defines the
learning-rate schedule. Delayed exponential moving averaging (EMA) first copies
weights after optimizer update 101, then uses decay 0.999. Validation uses ordinary
weights beforehand and EMA afterward. The portable bundle exports the selected
validation weights; the current selected artifact is completed epoch 16 EMA
(zero-based checkpoint epoch 15), as recorded in [experiments](experiments.md#current-planet-8-band-b0-baseline).

The bundle includes architecture, weights, band order, normalization and prediction
settings. It suffices for inference without the training registry or recipe paths.
Recovery checkpoints separately preserve ordinary weights, optimizer/scheduler,
EMA and continuation state; they are not interchangeable with inference bundles.
See [training operations](guides/training.md) for resume boundaries and
[training-loop tests](../tests/test_training_loop.py) and
[bundle tests](../tests/test_model_bundle.py) for selection/EMA/export checks.

## Label-independent tiled prediction

Tiled prediction takes cleaned imagery and a portable bundle; it neither reads
labels nor uses them for spatial alignment. The default stride is 256 on the
512-pixel model canvas. Final bottom/right windows shift inward to cover source
edges with full windows where possible, without duplicate starts. Dimensions
smaller than the canvas receive bottom/right padding, removed before placement.
This inference grid differs deliberately from the stored training-chip grid.

A window is retained when at least 20% of its true pixels have valid native
imagery; the fraction is configurable. Exactly 20% is retained, while entirely
nodata windows are always skipped. Padding never enters this denominator.
Retained overlapping neighbors may provide predictions inside a skipped window.
Coverage is therefore measured on reconstructed unique source pixels, not by
adding window counts.

For each source pixel, finite foreground probabilities from retained overlapping
tiles are summed and divided by their count with equal weight. Only then is the
source probability thresholded (`probability >= 0.5` for the selected bundle).
Tile masks are not voted or averaged. Unpredicted probability pixels are NaN;
output masks use 0 for background, 1 for kelp and 255 for no prediction. Rasters
retain source dimensions, CRS and transform. Native nodata and uncovered valid
imagery share the raster no-prediction value, but coverage tables distinguish them.

Labeled reporting reads these same saved probabilities separately, with labels
required to match the image grid exactly. Declared crops of one original are
assembled using original offsets; finite crop probabilities are averaged where
they overlap and then scored once. This is a second reconstruction level over
saved crop predictions, not a new pass through the model. Valid overlapping
labels must agree. This prevents repeated source pixels from inflating counts.

See [tiled prediction](../src/kelpseg/prediction/predict.py),
[source assembly](../src/kelpseg/reporting/canvases.py) and tests for
[tiling/overlap/padding](../tests/test_prediction.py) and
[crop reconstruction](../tests/test_reporting.py). The
[prediction guide](guides/prediction_reporting.md) owns input/output schemas.

## Scoring and coverage

The scored support is the intersection of valid native imagery, finite prediction
coverage and nonignored labels. Count true positives (TP), false positives (FP),
false negatives (FN) and true negatives (TN) once per covered original-source
pixel. Sum source confusion counts for region and overall metrics before computing
ratios; an average of chip or source IoUs is not pooled IoU.

| Quantity | Definition on the scored support |
|---|---|
| Foreground IoU | TP / (TP + FP + FN) |
| Precision | TP / (TP + FP) |
| Recall | TP / (TP + FN) |
| F1 | 2TP / (2TP + FP + FN) |
| Labeled prevalence | (TP + FN) / (TP + FP + FN + TN) |
| Signed kelp-area bias in pixels | FP − FN |

Area outputs multiply counts by projected pixel area in square metres. Keep FP
and FN separately because signed bias can cancel. Saved reports preserve undefined
ratios as null/blank/dash; training TorchMetrics uses zero for undefined ratios
and records validation support. The trainer refuses checkpoint selection with no
valid validation pixels. Saved float32 inference can differ slightly from bf16
training validation even at the same checkpoint.

Coverage tables distinguish native nodata, predicted valid pixels, uncovered
valid pixels, ignored labels over valid imagery, covered ignored pixels and
scoreable pixels. Some exclusions overlap; do not sum them as disjoint categories.
The reporting footprint depends on the prediction path:

- A TIFF report reads the complete declared image/crop footprints. Uncovered
  valid pixels are native-valid pixels with no finite prediction. When multiple
  crops are assembled, gaps between their footprints remain unknown.
- A chip report reads only retained selected windows. Its geometric gaps are
  unfilled pixels inside their saved bounding canvas, and native validity is
  known only within those windows. A zero uncovered-valid count therefore does
  not mean the full original TIFF was covered. Omitted edge areas outside that
  canvas require the selector's separate input-footprint/omission accounting.

Neither scope guarantees complete scoreable coverage. Match source membership,
state coverage and distinguish these footprints when comparing model scores.

Train/validation reports include descriptive threshold sweeps; the saved model
threshold remains primary and test reports omit sweeps. Boundary and patch-size
diagnostics explain error structure without changing headline support. Boundary
queries exclude unknown/image edges by the tolerance plus one pixel; components
touching unknown support or canvas edges are flagged and excluded from patch-size
summaries. They are observed label components, not necessarily biological beds.
Optional shoreline diagnostics describe support and error distributions, without
changing global counts or thresholds; see [diagnostics](guides/diagnostics.md).

Definitions live in [report metrics](../src/kelpseg/reporting/metrics.py) and
[aggregation](../src/kelpseg/reporting/report.py). Tests explicitly verify
[count pooling and undefined scores](../tests/test_validation_report.py) and
[ignored/uncovered support](../tests/test_reporting.py).

## Temporal comparisons on a common footprint

Temporal reporting reads a saved labeled report without new inference. It pairs
observations within the same dataset, release and region using declared dates.
Default elapsed-day intervals are 1–13 and 29–47 days inclusive; explicit pairs
can restrict the selection. Explicit pairs outside the configured intervals are
retained as unavailable, rather than overriding the interval settings. Same-day
observations remain separate and do not receive temporal change scores.

Each pair uses the intersection of both dates' valid imagery, known labels and
finite predictions on compatible projected-metre grids. Matching pixel bases
and integer origin offsets permit direct comparison without resampling; unsupported
grids or empty common support receive an unavailable reason. Counts for both
labels and predictions at both dates use exactly this shared footprint, avoiding
apparent change caused solely by different observed extents.

Each series uses its own earlier kelp count in
`100 * (after - before) / before`. The primary error is predicted percentage
change minus labeled percentage change, in percentage points. For example, equal
+10% changes give zero error even with constant multiplicative area bias. Zero
earlier kelp makes that series' percentage undefined; the percentage-point error
requires both percentages. Counts, areas and signed changes/errors in pixels and
square metres remain reported even when percentages are undefined.
Small positive baselines (default at most 10 pixels) are flagged without dropping
them, adding pseudocounts or clipping percentages.

Pairwise common footprints may differ, so these are not a fixed-footprint trend.
Report each pair's support, starting counts and elapsed days. Region/interval
summaries include support, median signed error and mean/median absolute error.
Repeated pairs are not independent observations, and uneven regional support
cannot establish a statewide temporal result. Calendar summaries pool confusion
counts and retain prevalence and FP/FN; they total observations across acquisitions,
not unique geographic area. Same-day overlaps are not silently mosaicked.

Retain low/zero-kelp dates in the declared scope. Low F1 at low prevalence alone
does not demonstrate drift, and dates/label counts do not identify tide, growth
or annotation causes. The target is agreement with labeled change, not constant
predictions through time. See [pair calculations](../src/kelpseg/reporting/temporal_pairs.py),
[common-footprint tests](../tests/test_temporal_pairs.py),
[summary tests](../tests/test_temporal_summary.py) and the
[temporal recipe](guides/diagnostics.md#temporal-canopy-change).
