# Optional diagnostics

For the scientific rationale and evaluation scopes, see [methods](../methods.md).

Use the [tiny walkthrough](../quickstart.md) first. These sections provide detailed options and reusable recipes. Run steps sequentially and stop if a command fails. Use fresh output names.

## Preview individual augmentations

The installed `preview-augmentations` command uses the actual **Albumentations 2.0.8** classes and their native
parameters; there is no custom augmentation math or separate parameter schema.
The preview generators, display helpers, trial sweeps and HTML live together in
[`kelpseg/augmentation_debug/`](../../src/kelpseg/augmentation_debug). The approved
training factory and raw-data adapter stay outside that debug package.

Choose the canonical chips, assignments and a fresh output directory:

```bash
uv run kelpseg preview-augmentations --chips /data/chips/ca_bc/v1 --assignments /data/splits/ca_bc/v1/assignments.csv --output /data/analyses/my-isolated-previews-01
```

After installation, `kelpseg preview-augmentations` works from any directory
when that environment is active. Alternatively, use
`uv run --project /absolute/path/to/kelpseg kelpseg preview-augmentations`
with the same absolute input/output options from another directory. No Python
file needs editing to choose paths. Options default to `--variant augmented`,
`--seed 33` and `--positive-samples 14` (allowed range 1–16), plus two background
controls. A smaller collection may require fewer positive samples. Run
`kelpseg preview-augmentations --help` for the available options.

Open its `index.html` in a browser. With the default sample count, choose one
operation, then flip the 16 examples with the previous/next buttons or arrow keys while keeping the same
setting. The large original/trial views support clean RGB, clean NIR false
color, labels on either view and a kelp-boundary close-up, including in the
expanded comparison. Longer sweeps use a native-value dropdown. Coarse dropout
has separate size and hole-count selectors. The two labeled background controls
are last.

Read/edit the literal constructors in
[`trials.py`](../../src/kelpseg/augmentation_debug/trials.py) to change trial
values. Equal range endpoints fix a library strength; the seed fixes its other
random choices. Library validation owns the parameter rules. The viewer shows
exact constructor arguments and realized parameters, plus the library version.

| Preview | Actual implementation and parameter |
|---|---|
| Rotations/reflections | `D4`, fixed `group_element` for the eight square symmetries |
| Additive brightness | `RandomBrightnessContrast`, `brightness_limit`, contrast zero |
| Gain / contrast | `RandomBrightnessContrast`, `contrast_limit`, brightness zero; stock contrast is multiplication by `1 + contrast_limit` |
| Blur | `GaussianBlur`, fixed `sigma_limit`, stock kernel; `NoOp` identity because sigma zero is invalid in this release |
| Noise | `GaussNoise`, fixed `std_range`, independent pixel/channel noise |
| Sharpening | `Sharpen(method="gaussian")`, native `alpha`, kernel size 5 and sigma 1 |
| Spatial holes | `CoarseDropout`, separate count/size sweeps, image fill 0 and mask fill -100 |
| Independent channel shifts | `AdditiveNoise`, uniform `noise_params.ranges` and `spatial_mode="constant"` |
| Red or NIR dropout | `ChannelDropout`, full removal with fill 0; fixed diagnostic channel index |

Gain and stock contrast share one sweep because they duplicate each other.
The preview sweeps are broader than the current training settings, described
in [the combined pipeline section](#preview-the-combined-augmentation-pipeline).

The wider exploratory sweeps retain earlier values and reach the library's
default brightness limits **-0.2 to 0.2**, blur sigma **3 px**, noise standard
deviation **0.44**, and uniform channel-shift amplitude **0.1**. Noise and
brightness/shift values use the library's unit float domain. These endpoints
can overwhelm this dark imagery; they are comparisons, not selected maxima.
Coarse dropout compares **1/2/4/8/16 holes at side 0.25**, and **sides
0.05/0.1/0.2/0.25/0.35/0.5 at four holes**. Side lengths are fractions of image
height/width; holes may overlap. Each trial is one stock transform.

[`augmentations.py`](../../src/kelpseg/augmentations.py) contains the small data
adapter only. It converts native uint16 imagery to **float32 / 65535**, calls
the real class, restores raw units and zero invalid fill. It applies no model
pre-cap. Stock pixel functions clip to their native **[0,1]** domain where
implemented, including a raw-zero lower bound. Stock blur sees zero nodata and
padding, so neighboring valid pixels can darken; there is no hidden
validity-normalized replacement kernel. Labels and validity travel as mask
targets; -100 under a spatial hole makes it invalid. Validity is detected before
augmentation and never inferred again from augmented zero values.

After augmentation, model preprocessing still uses the approved **5000 upper
cap** and [exact fixed normalization](../../tasks/033_baseline_training_and_portable_models.md#selected-training-normalization).
The viewer alone clips colors to **raw 0–2000**, consistently across examples.
The input scale, model cap and display ceiling have distinct purposes.

With the default sample count, the same 14 kelp-rich training windows and two
background controls are selected
from the canonical manifests before any arrays are opened. Positive examples
have at least 10% labeled kelp in their true footprint; this is showcase
sampling, not evaluation sampling or a new training eligibility rule. No
validation/test payload is opened. Native bands are augmented before choosing
RGB/NIR views, so their random draws stay consistent.

Outputs include `selected_windows.csv`, library/version/domain metadata in
`gallery.json`, per-window `parameters.json`, native-resolution view PNGs and
optional contact sheets. Full-image noise fields are represented by shape and
seed rather than copied into JSON. Source files remain unchanged. Existing
outputs are refused before payload reads; choose a new directory for each run.

## Preview the combined augmentation pipeline

Use the same path/sample options with the installed `preview-pipeline` command:

```bash
uv run kelpseg preview-pipeline --chips /data/chips/ca_bc/v1 --assignments /data/splits/ca_bc/v1/assignments.csv --output /data/analyses/my-pipeline-previews-01 --draws 8
```

`--draws` defaults to 8 and accepts 1–32. The variant, seed and positive-sample
count have the same defaults as the individual preview. This command also runs
from any directory with the installed environment active or `uv run --project`.
Both commands log progress and print the gallery's `index.html` path. Missing
inputs, insufficient training examples and existing output directories produce
an error; choose a fresh destination for each run.

Open its `index.html`. At the default sample count, flip the same 16 training
examples or use **Next draw**
to inspect eight seeded draws per example. **Inspect affine** compares D4 alone
with the same D4 plus the sampled affine step. **Inspect full pipeline** compares
the geometry-only reference with the full result, so the remaining augmentation
can be assessed separately. Switch the left reference to **Source original**
when useful. The operation cards report affine applied/skipped, actual scale
and pixel shifts, alongside D4 and the two pool operations.

Clean RGB/NIR, label overlays, paired kelp close-ups and enlarged comparison
remain available. Close-ups follow the same source footprint through D4 and
affine. Two labeled background controls are diagnostics; training eligibility
is unchanged. Choose a fresh output name for each gallery; historical review evidence is linked
from [history](../history.md).

The readable recipe is
[`build_training_augmentation`](../../src/kelpseg/augmentation_pipeline.py): stock
`D4(p=1)`, then `Affine(p=0.5)`, then `SomeOf(n=2, replace=False, p=1)`,
with every pool child at `p=1`. Affine stays outside the SomeOf pool. It uses
0.95–1.05× shared-axis zoom, independent ±16-pixel x/y shifts, no extra rotation
or shear, and the original output size. Imagery is bilinear; labels/validity are
nearest-neighbor. New borders use zero image fill and ignored mask fill.
Children are selected uniformly and execute in listed order: brightness, gain,
blur, noise, Sharpen, coarse dropout, channel shifts, channel dropout. Current Gaussian noise uses `std_range=(0, 0.0005)`: sigma 0–32.77 raw units
because the library domain is raw / 65535. The isolated viewer also retains
`0.002` as an exploratory comparison at the same display limits; its default is
`0.0005`. The current factory and recipe below specify the other selected ranges.
The final [native Albumentations recipe](../../configs/augment/baseline.json) is a
saved snapshot of that factory, verified by a focused parity check. It can be
loaded directly with `albumentations.from_dict`; there is no custom parser.
Channel dropout removes exactly one of the eight physical input bands in this
preview. The RGB/RGB+NIR training loader restricts eligibility to that
model's selected input bands. D4 includes the identity square symmetry.

`pipeline.json` saves the stock serialized recipe. `gallery.json`, selected
windows and per-example parameter records save the input/domain/normalization
metadata, draw seeds, actual operations and support counts. Kernel/noise-map
records reflect what the stock classes expose: the blur sigma range and actual
kernel, and the noise std range plus explicitly empirical realized field std.
Full noise arrays are not copied into JSON. The cap remains 5000 after the
entire pipeline, using exact fixed normalization; display remains 0–2000.

The preview constructs a seeded pipeline for each reproducible draw. The
training loader reuses one seeded Albumentations pipeline that includes
normalization and tensor conversion. Its random state advances across samples;
explicit per-draw seeds are for replayable previews. This gallery runs no model and opens no held-out payloads.
Existing outputs are refused; failed generation needs a fresh output.

## Shore-distance coverage and validation diagnostics

Use `prepare-shoreline` to create land and distance rasters once, then reuse them
for a label-only split inventory and for saved-prediction reports. Neither
workflow changes chips, labels, source assignments, model weights or thresholds.

```bash
uv run --frozen kelpseg prepare-shoreline --recipe /path/to/shoreline.toml
uv run --frozen kelpseg shore-inventory --recipe /path/to/shore-inventory.toml
uv run --frozen kelpseg report --recipe /path/to/validation-report.toml
```

Run these in order, stopping if a command fails. Outputs must be fresh directories;
there is no preparation resume or partial-output reuse.

### Prepare source-grid land and distance rasters

Copy [the shoreline recipe](../../configs/prepare/shoreline.toml). Set the three
GeoPackage paths, image root, source CSV and output directory. Use the existing
[prediction source CSV](prediction_reporting.md#predict-cleaned-source-tiffs) format: `source_key,image`,
with `band_names` for false-color previews and the explicit dataset/release,
region/date, original-source and crop-offset columns. For the inventory, keys
must match the canonical chip collection, and `original_source_id` must equal
its assignment `source_id`. Do not substitute a filename alias for this identity.
The TIFF labels are not used in this step.

The CA/BC shoreline inputs are
`<data_root>/data/1_raw/shorelines_v1/{mainlands,big_islands,small_islands}.gpkg`,
backed up at `kelp-box:kelpseg/data/1_raw/shorelines_v1/`. All three are EPSG:4326.
Their GeometryCollections may contain linework: the command keeps polygon parts
and holes, records discarded non-area parts and any repairs, and unions the land.
`coverage = "complete"` declares that the supplied polygons cover the requested
source halos. An incomplete regional export cannot be treated as empty ocean.

Source imagery must use north-up projected metre grids. The command creates
`land/` (0 ocean, 1 land, 255 unknown), `distance/` (float32 metres, NaN unknown),
`sources.csv`, settings, summary and bounded imagery/shoreline previews. Geometry
covers image nodata too; downstream analysis applies native validity separately.
The shoreline data are an approximate static reference, not a land truth mask.

Distance is from an ocean pixel center to the nearest rasterized land-pixel
center. It is computed with a halo beyond the TIFF before chip windows are read.
This is a native-pixel approximation: on a straight shoreline halfway between
3 m pixel centers, the first ocean distance is 3 m rather than 1.5 m to the vector
boundary. `max_distance_m = 500` caps distant values; 500 means **at least 500 m**,
not an exact distance. Source age, tides, omitted rocks and shoreline position
can matter more than this raster approximation near shore. Inspect `examples/`.

### Compare label support by region and split

Copy [the inventory recipe](../../configs/report/shore_inventory.toml). Set
`shoreline` to the prepared output, `image_root`, `label_root`, canonical
`chip_root`, locked `assignments`, explicit `experiment`/`variant`, and a fresh
output. The label CSV needs `source_key,label`, with label paths relative to
`label_root`, and must match the shoreline source keys exactly. The default
stored-label mapping is the same as the shared report. No predictions are needed.

`training_positive_only = true` matches the current training policy; change it
only when describing a run with different eligibility. The inventory reports:

- `full_source`: all valid labeled pixels in the declared cleaned source scope.
- `selected_chips`: the union of selected windows for each source's split,
  including the existing disjoint validation/test gaps.
- `training_eligible`: the union of training windows after the configured
  background-chip exclusion, shown only for training.

Every original-source pixel contributes once within each scope, including
intersections between crops or training windows. Padding never contributes.
These coverage tables measure unique available support. The separate training-
exposure section below counts repeated window appearances before augmentation.
Regions 011/012 remain training-only; absent split groups are shown as unavailable.
Unused source assignments are retained as a separate category.

Open `report.html` for normalized distance distributions and the
region/split nearshore heatmap. Absolute-area and cumulative-distance figures
are omitted; their underlying CSV tables remain available. CSVs include source/region/split pixel counts,
observed hectares, kelp prevalence, the fraction of all kelp in each band, and
source/date support. Area totals sum observations across acquisitions; they are
not unique habitat area. Nearshore means ocean distance **below 120 m**;
land and unknown kelp remain separate and included in the all-kelp denominator.

The inventory also assigns each known kelp pixel to an **eight-connected label
cluster** on the full original-source canvas. Components are defined before chip
selection, so window edges do not divide clusters. `cluster_sources.csv` links
source identities to georeferenced `cluster_ids/` rasters: zero is known background,
positive IDs identify clusters within that source, and 4294967295 is unavailable
or ignored label support. Join source ID plus cluster ID to `clusters.csv` for
pixel count, area, source location and boundary-fragment flag.

`cluster_distance.png` uses marked lines to show which full-cluster sizes labeled
pixels belong to at each ocean-distance band, separately by split. Size classes
are 1–10, 11–100, 101–1,000, 1,001–5,000 and >5,000 pixels. Each distance band
uses its own total kelp pixels as denominator, so the five shares sum to 100%.
The final 500+ distance is censored, not an exact offshore distance. It excludes components touching
image edges or unknown labels; CSVs also retain all observed components.
`cluster_correlations.csv` compares pixel distance with log10 full cluster area
by source, region/split, split and globally. Pixel-weighted results repeat cluster
size for every eligible pixel; cluster-weighted results use one observation per
cluster and the mean of its uncapped ocean-pixel distances. Land, unknown and
capped distances are excluded from correlations, but remain in distribution
counts. No p-values assume independent pixels. These observed components are
not necessarily biological beds, and a linear correlation can miss nonlinear
relationships. Inspect region/split distributions and both fragment treatments.

The training-exposure section describes the current uniform window sampler:
shuffle eligible training windows once per full epoch, with no dropped final
batch. It sums pixel appearances across windows, **including overlap**, unlike
the unique-pixel coverage tables. `training_positive_only = true` matches the
current positive-window selector; false describes a hypothetical all-window
eligibility policy, not the current run. Exposure uses the declared inventory
source scope, so use the complete training collection to describe the full run.

`exposure_windows.csv` gives per-window label counts by shore zone and full-source
cluster size. `exposure_summary.csv` and the HTML report give expected pixels per
draw, full-epoch appearances and the probability a draw contains each category,
with global and regional breakdowns. Regional means conditional on choosing that
region are separate from its unconditional contribution to the global sampler.
Nearshore is ocean <120 m, offshore includes ≥120 m and capped 500+ pixels;
mapped land/unknown stay separate. The small-cluster summary uses ≤100 pixels
(900 m² at 3 m resolution), retaining all five cluster-size bins in CSVs.

All observed clusters contribute, including boundary fragments, because their
pixels are offered to training; the fragment contribution remains explicit.
Padding, nodata and ignored labels do not contribute. These are nominal counts
**before augmentation**, not the number of pixels reaching the loss or gradient
weights: affine transforms and dropout can alter support. No multiplier is chosen
or applied by this analysis. Epoch totals assume all batches are consumed.

### Add distance bands to a saved-prediction report

Add these top-level settings to an existing chip or TIFF report recipe, before
any `[label_mapping]` table:

```toml
shoreline = "/path/to/prepared-shoreline-output"
distance_edges = [0, 30, 60, 120, 250, 500]
```

Bins are half-open (for example 30–60 includes 30 but excludes 60), with separate
land, unknown and final 500+ categories. The last boundary cannot exceed the
prepared distance cap. Reports without `shoreline` retain their existing behavior.
Chip reports use recorded `chip_source_key` and `source_id` mappings to read
matching source raster windows; they do not rebuild or modify the chips.

The report adds source, regional and pooled distance-band CSVs, metric/support
plots and bounded overlays. Imagery is displayed with log1p followed by a
per-channel 2–98% contrast stretch to reveal the NIR kelp signal. Yellow mapped
shorelines appear on imagery, distance, supplied labels and predicted kelp;
a colorbar gives distance in metres. These display changes never alter model
inputs, labels or predictions. Confusion counts pool before precision/recall/IoU/F1;
land and unknown categories reconcile with the unchanged overall score. Coverage,
ignored labels and missing predictions remain explicit. Keep chip and full-TIFF
results separate. The saved threshold is fixed, and test performance must remain
held out until model selection is finished. Use within-region support comparisons
to interpret a nearshore validation gap; pooled differences alone do not establish
that training representation caused it.

### Compare recall within region and full-source cluster size

To stratify a saved-prediction report using an already completed shoreline label
inventory, add this top-level setting alongside `shoreline`:

```toml
cluster_inventory = "/path/to/completed-shore-inventory"
```

Use the standard distance edges `[0, 30, 60, 120, 250, 500]`. The inventory must
contain the five size classes (1–10, 11–100, 101–1,000, 1,001–5,000, >5,000),
its original-source `cluster_sources.csv` and `clusters.csv`, and aligned saved
cluster-ID rasters. The report reads these IDs and full-source sizes without
recomputing clusters from windows or prediction coverage. Missing membership
for scored labeled kelp fails explicitly. The saved model threshold is unchanged.

Open the linked `joint_report.html` for regional distance/size recall and
nearshore-versus-offshore comparisons. `joint_sources.csv` and `joint_regions.csv`
contain TP/FN, labeled pixels/area, recall and acquisition support. Nearshore is
<120 m; offshore includes ≥120 m and capped 500+ distances. Land and unknown
remain separate. All-observed, interior-only and truncated-only rows account for
full-source boundary fragments. `joint_reconciliation.csv` reconciles scored
TP/FN against the unchanged shoreline counts and reports uncovered labeled kelp.
False positives and precision stay in `shoreline_regions.csv`; they have no true
label-cluster size.

Support tables report contributing TIFFs/dates, largest-source/date shares,
comparisons within the same TIFF/date, and the gap after removing the largest
contributor. A date may contain several TIFFs. Flags for <100 positive pixels,
<3 dates or >50% contribution from one source/date are descriptive warnings,
not significance tests. Comparisons still concern represented labels, with
residual differences possible within broad size classes; they do not establish
that distance causes missed kelp. Keep test performance held out during selection.

## Temporal canopy change

Run `temporal-report` on one completed labeled report; it does not run inference
or require model weights:

```bash
uv run --frozen kelpseg temporal-report --recipe /path/to/temporal.toml
```

Copy [the temporal recipe](../../configs/report/temporal.toml) and edit its paths:

```toml
report = "/path/to/completed-labeled-report"
output = "/path/to/fresh-temporal-report"
short_min_days = 1
short_max_days = 13
long_min_days = 29
long_max_days = 47
small_baseline_pixels = 10
```

The day endpoints are inclusive. By default, the command considers every source
pair within the same dataset, release and region at either interval. Same-day
observations are recorded separately and are not scored as temporal changes;
other gaps are omitted. Unknown dates/regions appear in `source_exclusions.csv`.
To restrict the comparison, set `pairs = "/path/to/pairs.csv"` with columns
`earlier_source,later_source`, using exact `source_keys` values from the labeled
report's `sources.csv`. A merged original's key may contain semicolons; use the
complete value. Invalid joins or reversed dates fail with an error; unsupported
spatial comparisons remain in `pairs.csv` with their reason.

Both dates are measured on exactly the same pixels: valid imagery, valid labels,
and finite saved predictions at both dates. Grids must have the same projected
metre CRS and pixel basis with integer-aligned origins; there is no reprojection.
Keep the labeled report's referenced predictions, labels and imagery/chip payloads
available. Processing holds the two source canvases and comparison arrays in RAM,
not the entire collection. Each output directory must be fresh; failures stop
without resuming partial work.

The primary comparison is proportional change relative to the labels:

```text
label change (%)      = 100 × (label_after − label_before) / label_before
prediction change (%) = 100 × (prediction_after − prediction_before) / prediction_before
change error (pp)     = prediction change − label change
```

Each series uses its own earlier kelp count. Thus +10% in the labels and +10% in
the predictions gives zero percentage-point error, even with constant
multiplicative area bias. Labels can change during the short interval too;
stability does not mean constant canopy. Zero starting kelp makes that series'
percentage undefined; change error needs both percentages. Counts and absolute
changes remain available. Small nonzero starting counts up to
`small_baseline_pixels` are flagged, never excluded or replaced by an epsilon;
set this value to 0 to disable the flag.

Open `report.html` with `changes.png` and `observations.png` alongside it.
`pairs.csv` records counts, proportional/absolute changes, support and reasons.
`pair_summaries.csv` gives regional interval support and median signed and
mean/median absolute percentage-point error. Reused observations make pairs
non-independent; uneven regional support remains explicit. Different pairs can
have different common footprints, so they do not form a single fixed-footprint
trend. `dates.csv`, `years.csv`, `year_months.csv` and `months.csv` describe pooled
observation counts/areas and coverage, not unique geographic area across dates.

A one-source report is a valid smoke input: it produces descriptive tables and
an explicit no-pairs display. Use a report spanning multiple dates to measure temporal agreement;
`temporal-report` never starts inference.
