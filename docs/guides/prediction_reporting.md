# Prediction and labeled reports

For the scientific rationale and evaluation scopes, see [methods](../methods.md).

Use the [tiny walkthrough](../quickstart.md) first. These sections provide detailed options and reusable recipes. Run steps sequentially and stop if a command fails. Use fresh output names.

## Post-training validation diagnostics

After training finishes and exports `model/`, save predictions first, then make
reports from those saved probabilities. Use `predict-chips` followed by `report`.

Copy [the chip-report recipe](../../configs/report/chips.toml) and edit its paths:

```toml
predictions = "/path/to/fresh-validation-predictions"
output = "/path/to/fresh-validation-report"
max_examples = 12
```

After saving that recipe, run:

```bash
(
  set -e
  uv run --frozen kelpseg predict-chips \
    --run /path/to/completed-run \
    --output /path/to/fresh-validation-predictions \
    --device cuda
  uv run --frozen kelpseg report --recipe /path/to/chip-report.toml
)
```

Omit `--device cuda` to use CPU inference. Prediction refuses incomplete training
runs and existing outputs. Reporting reads saved predictions and referenced
labels/imagery; it does not load weights, run inference or require a GPU. To
regenerate a report, keep `predictions` unchanged and choose a fresh `output`.
Both steps stop on failure; there is no partial-output resume. Nothing modifies
training, W&B, checkpoints or the selected threshold.

`predict-chips` accepts validation (`--split val`, the default) or a sampled
training scope (`--split train`); it does not accept `--split test`. For held-out
test evaluation after selection is frozen, use `predict` on the declared test
TIFFs, then `report` with `split = "test"` and the matching assignments.

The training run's saved chip/assignment paths must be available for prediction.
The saved prediction directory retains probabilities on source-coordinate
canvases, selection records and references to chip payloads. Keep those payloads
available for reporting labels and figures; the training run and model weights
are no longer needed by reporting. Paths in report recipes resolve relative to
the recipe file.

For fixed unaugmented training diagnostics, add `--split train`,
`--sources-per-region 3` and `--seed 42` to `predict-chips`, using a fresh output.
This samples original training TIFFs uniformly within each region without looking
at labels, then applies the disjoint evaluation-window selection. It includes
background-only windows, even though those are excluded from optimization, and
never changes saved assignments. `windows.csv` records exact selected windows.
Compare common regions separately: training-only BC regions have no validation
counterpart. A sampled train–validation gap also reflects source/date/patch-size
composition, so it is not a pure measurement of overfitting.

### Extend the tiny walkthrough through reporting

After [quickstart step 4](../quickstart.md#4-train-the-bounded-cpu-model), use
its completed run directory with `predict-chips --run <tiny-run> --output
<fresh-tiny-predictions>` (CPU default). Point the chip report recipe above at
that output and run `report --recipe <tiny-report.toml>`. Keep the tiny chip
payloads available; reports no longer need the run or copied model. This checks
the same saved-prediction workflow as production without new training.

For the tiny TIFF walkthrough below, pair each predicted tiny validation image
with its same-named file under the tiny release's `labels/` directory. If testing
a smaller cropped image, create the exactly matching label crop first. Declare
that validation-only scope in the TIFF report recipe. Do not add held-out inputs
to a smoke or treat tiny-model results as a quality evaluation.

### Report full-TIFF predictions

Run [image-only TIFF prediction](prediction_reporting.md#predict-cleaned-source-tiffs), then use the same
`report` command with [the TIFF-report recipe](../../configs/report/tiffs.toml).
Provide a label CSV with `source_key,label` columns matching `sources.csv` in the
prediction output. Label paths resolve under `label_root`. For example:

```csv
source_key,label
example,example_label.tif
```

```toml
predictions = "/path/to/tiff-predictions"
output = "/path/to/fresh-tiff-report"
labels = "/path/to/labels.csv"
label_root = "/path/to/cleaned-labels"
external_scope = "Independent validation collection"
split = "val"
max_examples = 12
```

For existing experiment membership, replace `external_scope` with `assignments`,
`experiment` and `variant`; keep the explicit `split`. Include `dataset_id` and
`release_id` in the prediction source CSV so the report can join the exact
assignment identity. The label CSV can supply
`source_id` when the declared original prediction identity is not the exact
assignment source ID. The report checks the identity join rather than guessing
from filenames. Use test scope only after model settings and thresholds are fixed.

Cleaned labels must match image dimensions, CRS and transform exactly. Reporting
does not clean, resample or reproject them. The default stored CA/BC label mapping
is 0→background, 1→kelp, 2→background, 3→ignored, 4→background. Other collections
can supply an explicit `[label_mapping]` table; values are 0, 1 or -100. See the
example recipe. Stored background is preserved regardless of label nodata metadata.

### Read the shared report

Open `report.html` alongside its `examples/` directory and `diagnostics.png`.
Both inference paths share the same metrics, tables and figure implementation:

- Global/source/region confusion counts, IoU, precision, recall and F1, labeled
  prevalence, scored coverage and signed kelp-area bias. False positives and
  misses remain separate because signed errors can cancel.
- Diagnostic threshold sweep from 0.1 to 0.9 for train/validation and probability
  histograms by supplied kelp/background labels. The saved model threshold stays
  the primary result; test reports omit exploratory sweeps.
- Boundary precision/recall/F1 at Euclidean tolerances of 1, 2 and 3 pixels,
  and error rates near labeled boundaries versus interiors.
- Pixel recall and fraction of wholly missed label components in size bins
  1–10, 11–100, 101–1000 and >1000 pixels. Connectivity is eight-neighbor;
  these label fragments are not necessarily biological kelp beds.
- Bounded, deterministic NIR/red/green false-color examples, labels, predictions,
  probability maps and TP/FP/FN panels. Examples are diagnostics, not a random
  or representative score. Chip background-window diagnostics remain specific
  to the chip workflow.

The report states `chip_disjoint` or `tiff_tiled` scope. Chip inference places
selected disjoint windows in source coordinates; gaps remain unknown. TIFF
inference averages overlapping window probabilities before thresholding. Reports
count each covered, valid labeled original-source pixel once, including declared
cropped inputs sharing an original grid. Neither scope guarantees complete
scoreable coverage, and their scores are not directly interchangeable. In chip
reports, coverage counts describe retained windows within the saved canvas;
zero uncovered-valid pixels does not establish full-TIFF coverage. Consult the
selector logs for full input-footprint omissions, including edges outside the
saved canvas. See [coverage definitions](../methods.md#scoring-and-coverage).

Nodata, missing predictions and ignored labels remain explicit exclusions.
Boundary scores exclude unknown/image edges by tolerance + 1 pixels for scored
contour pixels. Matching references include contours with an observed 3×3
neighborhood; near-boundary error scoring uses a four-pixel exclusion. Components
touching unknown support or image edges are flagged and excluded from patch-size
summaries. Undefined ratios are blank in CSV, null in JSON and a dash in HTML.
Area reporting requires projected metre units.

Saved predictions use float32 inference, which may differ slightly from bf16
training validation. Reports measure agreement with supplied labels on their
recorded scope. `input_sources.csv` preserves input paths and identities;
`source_keys` links merged report rows to their constituent prediction inputs. Large predictions and reports belong outside Git and should be
backed up to Box. The separate [temporal report](diagnostics.md#temporal-canopy-change) uses
these saved outputs for comparisons across dates.

Reporting holds one original source's imagery, labels, probabilities and diagnostic
arrays in RAM. Overlapping crop inputs also remain in memory while that original
is assembled. Boundary/patch operations allocate additional arrays; reports are
not a streaming solution for mosaics larger than available memory. `max_examples`
limits figure output, not the scoring footprint or peak raster memory.

## Predict cleaned source TIFFs

`predict` maps imagery without reading labels or requiring training chips/splits.
Run cleanup once and retain its cleaned TIFFs; prediction does not clean again.
Inputs must be uint16 GeoTIFFs with internal CRS/transform, declared `nodata=0`
and the cleaned all-native-band-zero convention. Raw 65535-nodata imagery must
first go through the existing check/clean workflow. Declare every native band
by physical name, even when the model selects only three or four of them.

Copy [the example recipe](../../configs/predict/example.toml) to a local directory.
Keep all machine-specific paths in this file; relative paths resolve from it:

```toml
model = "/path/to/copied/model"
manifest = "sources.csv"
image_root = "/path/to/cleaned/images"
output = "/path/to/new/predictions"
stride = 256
min_valid_fraction = 0.20
batch_size = 1
device = "cpu"
```

Create `sources.csv` beside the recipe. Image paths resolve from `image_root`:

```csv
source_key,image,band_names,region_id,acquisition_date
scene_001,scene_001.tif,coastal_blue;blue;green_i;green;yellow;red;rededge;nir,002,2021-02-28
```

Only `source_key`, `image` and `band_names` are required. Other supported columns
are `dataset_id`, `release_id`, `region_id`, `acquisition_date` (YYYY-MM-DD),
`original_source_id`, `row_offset` and `col_offset` (nonnegative source crop offsets).
Preserve known identities; omitted metadata stays blank. Keys must start with a
letter/digit and contain only letters, digits, underscore, dot or hyphen. Keys
must also be unique ignoring case (for example, `Scene` and `scene` conflict);
resolved image paths must be unique. Channels are selected by name, not count.

```bash
uv run kelpseg predict --recipe /path/to/predict.toml
```

The bundle supplies its weights, 512-pixel canvas, normalization, channel order
and 0.5 threshold. Inference shifts the last windows inward at the bottom/right;
only dimensions smaller than 512 need bottom/right padding. Padding is removed
before source placement. Stride must be 1–512; the default 256 overlaps windows.
Probabilities are averaged equally at valid source pixels before thresholding
once (`probability >= 0.5`). There is no test-time augmentation or label input.

Windows below 20% valid imagery are skipped; exactly 20% is retained. This
fraction excludes artificial padding and is calculated before band selection.
Entirely nodata windows are always skipped, even with `min_valid_fraction=0`.
Overlapping retained windows may still predict pixels inside a skipped window.

The output directory contains:

- `probabilities/<source_key>.tif`: float32 probabilities, NaN where not predicted.
- `masks/<source_key>.tif`: uint8 background 0, kelp 1, no prediction 255.
- `sources.csv`: identities, paths and unique pixel coverage counts per source.
- `windows.csv`: actual offsets, sizes, padding, valid fractions and dispositions.
- `settings.json`: resolved settings and model metadata.
- `summary.json`: complete status, source/window counts and summed pixel counts.

Both rasters preserve the source CRS, transform and dimensions and use lossless
compression. Native nodata and uncovered valid pixels share the raster no-prediction
value; the coverage tables distinguish their counts. To locate those reasons,
combine output validity with all-native-band-zero validity in the original image.
An all-skipped source still produces rasters with no predictions and zero coverage.
These are mapping outputs, not accuracy scores. Use the shared `report` command above for labeled scoring.

Use a fresh output directory. Existing outputs are refused; failure stops the
run and leaves incomplete files for inspection. Choose a new output for another
attempt. A completed `summary.json` marks completion; there is no resume/reuse.
Progress logs show sources, retained windows and covered/uncovered valid pixels.

CPU is the default; use `device="cuda"` only on a suitable GPU host. Batch size
controls tile memory, not whole-source memory. Processing holds one source's
float32 sum, uint32 count and boolean validity arrays (9 bytes/pixel), plus
output masks, temporary arrays and model/tile memory. For example, 100 million
source pixels require at least 0.9 GB just for those accumulators. Reduce batch
size for model-memory pressure; larger-than-memory source mosaics are outside
this simple implementation. GPU throughput has not been validated locally.

For notebook use, call `predict(load_settings(recipe))` from
`kelpseg.prediction.predict` and `kelpseg.prediction.settings`. Both labeled and unlabeled workflows use this same image-only predictor.

### Extend the tiny walkthrough with prediction

Use the complete [quickstart prediction example](../quickstart.md#5-copy-the-model-and-predict-a-validation-tiff),
which includes the copied bundle and original crop offsets. Reuse one **training
or validation** TIFF from
`tiny_ca_bc/v2/images/`. For the published tiny v2 baseline, the validation source
`002_20210228_182240_2406_tiny.tif` is a 768 × 768 multiwindow example. Use it as
the CSV image with source key `tiny_val`, native eight-band names, region `002`
and date `2021-02-28`; set `image_root` to the tiny images directory. Copy the
model and image into a fresh directory if checking portability. Run the command
with a new output and inspect its probability/mask TIFFs in a GIS. No labels,
training registry or online connection are needed after installation and input/model
fetching. Check `sources.csv` coverage
before interpreting the maps. A tiny smoke model demonstrates execution and
spatial correctness, not useful segmentation accuracy.
