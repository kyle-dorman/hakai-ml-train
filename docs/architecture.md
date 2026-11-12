# Architecture contract

Scientific explanations are owned by [methods](methods.md); this document owns
the implementation boundaries and interfaces.

## Current implementation

The installed `src/kelpseg/` package provides the Typer command and read-only
machine-path checks, generic byte-preserving organization, quick/full directory
checks, shared cleanup, native-band chipping with optional labels, and source
assignment/window-selection functions and streaming training-image pixel
statistics. Installed model/input helpers connect these manifests to
SegFormer B0/B1/B2/B3 (`mit_b0` through `mit_b3`) with 8/4/3 inputs and one logit.
B3 is the constructor default; the [selected recipe](experiments.md#current-planet-8-band-b0-baseline)
uses B0 with ordinary BCE plus Dice. `training/data.py`
loads kelp-positive training rows and representative validation; test rows stay
metadata only. Shared preprocessing and the approved stock augmentation factory
feed float32 tensors through an Albumentations Compose ending in Normalize
and ToTensorV2. `training/loss.py` and `training/metrics.py` implement the
configured weighted binary objectives (default smoothed BCE/Lovasz) and native
TorchMetrics accumulation. Typed loss terms live in `training/loss_settings.py`;
all terms share ignore masking and float32 reduction. Training uses
PyTorch Lightning Trainer/LightningModule and native callbacks/loggers.
Portable bundles support image-array probabilities and the installed `predict`
command reconstructs georeferenced source rasters without labels. `predict-chips`
saves selected disjoint chip probabilities on source-coordinate canvases. Both
feed `report`, which loads saved probabilities and aligned labels and shares
metrics/figures without model inference. Completed-epoch resume uses native
Trainer checkpoints with explicit random/sampling state.
The maintained implementation is the installed `kelpseg` package; the GPU
bootstrap is a standalone shell helper. `preview-augmentations` and
`preview-pipeline` call the same training-only augmentation functions used in
training. Historical implementations and recovery references are indexed in
[history](history.md).

The package uses uv and `uv_build`, with no plugin framework, generic model zoo
or manual per-fold config copies. New-region adaptation remains a later task.

```text
variant 1: raw, immutable source deliveries
  -> variant 2: organized, unsplit intermediate; unchanged TIFFs and name/region crosswalks
  -> variant 3: cleaned, unsplit intermediate; documented repairs and parent provenance
  -> one canonical chip collection and chip statistics
  -> external temporal/LORO assignments and training eligibility
  -> explicit band selection and training recipe
  -> checkpoint
  -> image-only tiled prediction and georeferenced reconstruction
  -> optional label scoring, comparisons, and visual review
```

Prefer small functions with explicit inputs/outputs and a limited supported
scope. Preparation runs once from beginning to end; a failure stops the sequence
and an interruption requires a fresh attempt. There is no preparation restart,
resume or partial-output reuse. Publish complete manifests atomically and refuse
silent overwrites. The current one-pass cleaner is the upper bound on file
complexity; prefer smaller functions and files with one clear purpose.

## Researcher interface

Use `uv run --frozen kelpseg <command>` with explicit recipe/path/output
arguments. Thin Typer handlers call ordinary typed Python functions; notebooks
and tests can call those functions directly. The [preparation guide](guides/preparation.md)
provides schemas, command examples and the module map.

`organize`, `check`, `clean`, `chip`, `split` and `pixel-stats` share the
`src/kelpseg/prepare/` package. Directory checking/cleanup supports imagery with
optional labels; an organizer catalog is not required. Quick checks inspect
structure/headers; full checks scan selected pixels and state unavailable checks.
Both are read-only. There is no BC-specific intermediate or command.

Machine paths are explicit, without automatic discovery. Organizer/path-file
roots resolve relative to the path file. Direct-directory check/clean CLI paths
resolve from the working directory; recipe references resolve relative to their
recipe. Keep machine paths in one place and workflow settings in short recipes.
Unknown settings fail with actionable errors. Preparation progress uses standard
Python logging for phases, files and counts/bytes.

`train --recipe <recipe-file>` creates run records, metrics, checkpoints and a
portable bundle. `--resume <run/checkpoints/last.ckpt>` restores a completed
epoch in the same run with matching schedule and input identities. Exact replay
requires zero workers and deterministic execution; multiworker continuation
restarts worker augmentation streams and can change sample order. Preparation
remains one pass. See [training and resume](guides/training.md).

Pixel statistics uses true-size chip images in declared native band order,
selecting training rows from existing assignments with optional kelp-positive
chip eligibility. Exclude native all-band-zero nodata before the optional cap.
Streaming float64 central moments yield means and sample standard deviations;
overlap counts as repeated chip exposure. Labels, model preprocessing and
artificial loading padding do not enter the calculation.

The frozen environment contains the maintained workflow dependencies and the
checkout adds the `dev` group. Heavy libraries load when the corresponding
workflow runs. No legacy dependency group is needed.

## Identity and preparation

Preserve dataset/release, region ID, source TIFF ID, acquisition date, chip ID,
source window, shape, CRS/transform, band names/order, dtype, label mapping, and
nodata interpretation. Paths in portable manifests resolve from an explicit
dataset root. Do not derive identity from mutable directories or list order.

Raw imagery and labels are immutable. Preserve explicit source declarations and cleanup
transformations when preparing a new release.

Keep organization/renaming separate from cleanup. Organization preserves source
image/label bytes, region mappings and aliases in an unsplit intermediate.
Original grids need not match until cleanup. The published CA/BC releases and
portable chip/split controls are described in the
[release reference](reference/ca_bc_release.md). New preparation uses plain
manifests and the [artifact policy](data_artifacts.md), without new hashing or
receipt machinery.

Cleanup writes into a fresh sibling `.<output-name>.incomplete` directory and
renames it to the requested output only after all checks pass. Failed runs leave
that incomplete directory for inspection. The cleaner never resumes or reuses it;
move or remove it deliberately before a full rerun, or choose a new output path.
There are no cleanup receipts, active-file journals or producer-matching resumes.

Cleaned imagery stores nodata as all-band zero and declares
`nodata=0`; labels retain valid class-zero background and use stored/metadata
ignore value 3. Detect original nodata before normalizing values. For paired
data, align labels and exclude outside-label coverage by writing image zero
plus label 3. Image-only cleanup never blanks valid imagery because labels are
absent. Raw/organized payloads stay unchanged.
Detect retained all-zero value collisions instead of silently changing validity.
Detailed coverage/reason rasters are optional and off by default; compact
counts, transformation records, source/output references and asset dispositions
remain required. Rewritten image and label sidecars must not reactivate stale
metadata/masks/overviews.

Paired labels on the exact image grid are read directly without resampling.
When grids differ, alignment reads the native label crop without masking,
nearest-reprojects the array onto the image window, and identifies coverage
using an unused value 255. This preserves stored class zero regardless of source
nodata metadata. Supported inputs have matching CRS, north-up unrotated grids
and single-band `uint8` labels. Other grids/dtypes fail explicitly. Each source
crop is limited to 16,777,216 pixels; a smaller processing window is required
above that limit. Image-only cleanup has no label-alignment requirement.

Preparation accepts declared deliveries, region mappings and recipes uniformly
for every dataset. The current 369-pair scope is the first ordinary dataset,
not an implicit base that subsequent data must extend. All datasets get their
own organized/cleaned release IDs and parent links; all published releases remain
unchanged. Region, delivery and dataset IDs are separate concepts. A collection
is a versioned manifest selecting one dataset, a region subset, or any combination
of exact cleaned releases/source identities, without another physical TIFF merge.
Only an experiment recipe assigns a dataset/collection the role of baseline.
See [the add-region flow](data_artifacts.md#adding-regions-and-combined-datasets).

A channel count is insufficient to specify a product. Select bands by explicit
validated names/indices; RGB and RGB+NIR are not the first three/four PS8B bands.
Record normalization and initialization appropriate to each band recipe.

Keep canonical background chips. Express nodata and training eligibility in
metadata, retaining excluded identities/reasons. The installed chipper uses
a configurable 512-pixel chip size, stride 256 and maximum of 50% image nodata;
omit payloads only above that limit and keep their manifest records. Count
actual source-window pixels, excluding artificial padding. Training selects
kelp-positive chips separately; this does not remove canonical backgrounds or
filter evaluation. Use ignore index
`-100` for unscored labels and padding.

`chip_inputs.py` validates a flat recipe, optional exact-key identity CSV and
cleaned headers; `chip.py` reads windows sequentially without cleaning or
realigning labels. Stored labels map explicitly to 0/1/-100, with image nodata
forcing -100. Label masks/nodata metadata cannot erase stored background.
One native uint16 HWC NPZ collection supplies all spectral variants. `bands.py`
and `chips.py` select channels in declared order and pad while loading.

Chipping writes only `chips/`, `windows.csv`, `sources.json`, `recipe.json` and
`summary.json` (complete status), publishing the fresh incomplete directory by
rename. Window rows join source metadata by `source_key`; original TIFF identity,
crop offsets and dimensions allow reconstruction and later grouping. Crops of
one original must agree on CRS and their offset-adjusted grid. Input headers
are checked once during planning. Nodata and
valid-imagery ignored targets have separate window counts. Those counts overlap;
unique source coverage must be reconstructed from retained windows when needed.
There is no parent authentication, hashing, receipt or recovery step in chipping.
The [preparation guide](guides/preparation.md#chip-cleaned-imagery) owns the recipe and CSV schema.

## Splits and loading

Store generated split assignments with the external dataset release. Keep split
algorithms/configs in Git. Load one canonical collection through manifests;
remove the requirement for hard-linked train/validation/test directory trees.

New-region and combined-data experiments select an explicit collection version.
Generate versioned assignments for that scope and preserve declared fixed test
identities. Check known declared aliases across deliveries as well as source
IDs so known renamed copies cannot leak between train, validation and test.
This uses identity declarations, without new content-hash discovery. Resolve
conflicting annotation versions before selecting a collection's scoring labels.

[Partitioning methods](methods.md#partitioning-observations) define original-source,
region/date and physical-spacecraft/day isolation, temporal directions, optional
BC membership and LORO companion exclusions. Keep source assignments identical
across spectral comparisons. LORO assignment generation remains installed;
completed study training orchestration and its qualifications are archived in
[Task 037](../tasks/037_baseline_comparisons_and_loro.md).

`split_inputs.py` reads trusted cleaned controls or explicit CSV rows without
opening TIFFs; full cleaned chip keys come from canonical image references.
`configs/split/ca_bc_v1.toml` contains the approved cutoffs. `splits.py` generates
one assignment per namespaced original/experiment/variant and validates region/
date and spacecraft/day isolation. Only present evaluation regions create folds.
The unresolved BC token `241` stays literal and is allowed only on dates without
evaluation imagery; explicit known Planet metadata must agree with its original ID.

The installed `split` command publishes only `collection.csv`,
`chip_metadata.csv`, `assignments.csv`, `recipe.json` and `summary.json` through
a fresh incomplete sibling. The chip metadata export uses the declared
identity columns and excludes satellite ID. `select_windows(chip_root,
assignments, experiment="baseline", variant="base")` joins list-shaped chip
source controls to original assignments and returns window rows with roles/
reasons and paths resolved from the explicit chip root. Omitted windows stay
unused without payloads. Selection reads no arrays and creates no fold copies.

The selector returns retained assigned training windows; `training/data.py`
requires `kelp_pixels > 0` for optimization and records exclusions. Validation/test
window selection is disjoint in original coordinates, including overlapping crops.
Canonical payloads and omitted-window reasons remain unchanged. See
[chip scope and coverage](methods.md#canonical-chips-and-evaluation-scope) for the
selection method and [preparation recipes](guides/preparation.md#assign-sources-and-select-chip-windows)
for settings and coverage outputs.

## Prediction and scoring

Training validation uses disjoint chips and selects checkpoints by validation IoU.
`predict-chips` saves validation or sampled training probabilities for reporting;
held-out TIFFs use `predict` followed by `report` after model selection is frozen.
The image-only predictor reads a portable bundle and cleaned imagery, preserving
georeferencing and explicit window/padding placement without labels. It averages
overlapping probabilities before thresholding and records sparse-window coverage.
See [prediction methods](methods.md#label-independent-tiled-prediction).

`report` has separate chip and TIFF input paths that share original-source
assembly, metrics and figures. It requires saved predictions and matching labels,
not model weights or a training run. Exact cleaned-label grids are required
without resampling. Declared crop overlaps are combined before scoring, with
conflicting valid labels rejected. Metadata retains identities, offsets, split,
model and threshold. [Scoring methods](methods.md#scoring-and-coverage) own pooled
counts and coverage semantics; [the guide](guides/prediction_reporting.md) owns
commands, schemas and output interpretation.

`temporal-report` reads one completed labeled report and its saved references.
It reuses source reconstruction and compares date pairs without new inference
or resampling. [Temporal methods](methods.md#temporal-comparisons-on-a-common-footprint)
define common support and change errors; [the temporal recipe](guides/diagnostics.md#temporal-canopy-change)
owns settings and outputs.

## Shore-distance diagnostics

`prepare-shoreline` rasterizes the union of three explicit polygon layers on each
image grid without reading labels. Polygon parts/holes are retained; geometry
repair and discarded linework are counted. Complete vector coverage is an explicit
input assumption. Native-grid Euclidean distances use a halo beyond source edges,
projected metre spacing and a recorded right-censoring cap. They approximate
land-pixel-center distance, not subpixel or tide-corrected shoreline distance.

`shore-inventory` joins prepared rasters, cleaned labels, chip identities and
locked assignments. It counts full-source, selected-chip and training-eligible
pixel unions independently of predictions. Original crop overlaps are deduplicated;
unknown/land label support and absent split groups remain visible. `report` can
read the same rasters using canonical keys or the saved chip-window identity
mapping. Optional distance bands partition the original scored footprint exactly,
including land and unknown categories; global counts and thresholds do not change.
Label-only cluster analysis assigns eight-connected IDs on the complete original
canvas before selecting chip footprints. Each kelp pixel inherits full observed
component area. Source-local IDs and component tables remain georeferenced;
components touching unknown labels or canvas edges are flagged as fragments.
Distance/size distributions and additive Pearson moments pool by region/split;
correlations use uncapped ocean kelp only, with both pixel and cluster weighting.
Interior-only results are primary, with all-observed sensitivity tables. Repeated
pixels and acquisitions are not independent evidence; no significance tests.
Optional joint validation uses saved original-source cluster-ID rasters and full
component sizes, aligned to the existing scored canvas without reclustering.
All observed components partition TP/FN; interior plus truncated counts reconcile
to that total. Near/offshore comparisons additionally omit mapped land/unknown.
Region/distance/size summaries pool counts, retain explicit empty groups and
count unique contributing sources/dates. Matched-acquisition comparisons and
largest-source/date removal expose support imbalance; no false positive is
assigned to a true label-cluster size. Precision remains a region/distance metric.
Training-window exposure is distinct from unique-pixel support: sum label-pixel
appearances across every eligible training window, preserving overlap and full
source component sizes. Uniform without-replacement draws yield a sum per full
epoch and a mean per draw. Region-conditional exposure and global contribution
have different denominators. Keep all observed fragments, land/unknown support
and exclusion counts explicit; this describes nominal preaugmentation sampling,
not augmented loss pixels or gradient weighting.
Display native imagery using log1p before contrast stretching (the user’s
preferred imagery display); this is visualization only, never model preprocessing.
Shoreline panels share a yellow boundary, with a metre colorbar for distance.
Region/split distributions describe observed labeled support, not unique habitat
area or optimizer exposure. Commands and interpretation are in
[the shore-distance recipe](guides/diagnostics.md#shore-distance-coverage-and-validation-diagnostics).

## Local verification

Exercise cleaning, chipping, band selection, splitting, loading, a tiny optimizer
update, validation, checkpoint save/load/resume, prediction, scoring, and transfer
locally. Keep real bounded examples alongside focused fixtures. Preserve useful
existing tests for source-aware nodata, split leakage, manifest joins, overlap,
centered padding, and corruption handling as implementations are replaced.
CUDA behavior and production resource sizing remain remote-host checks.

Focused CPU fixtures run without Box/W&B access, a GPU or large downloads.
The [tiny walkthrough](quickstart.md) fetches a small real-data example once
and then exercises installed preparation, training, copied-model prediction
and reporting. CUDA behavior and production sizing require the GPU host.
