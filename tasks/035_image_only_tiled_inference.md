# Task 035: Image-only tiled inference

Status: Complete — 2026-11-04. Implemented and verified locally; no remote changes or commits.
Depends on: Completed Task 033 portable models and tiny walkthrough. Remote
Task 034 training may continue independently on its fixed checkout/environment.

## Abstract

Turn a copied model bundle and saved cleaned source TIFFs into georeferenced
kelp probabilities and masks. Reuse the installed model and preprocessing;
add only the raster windowing, reconstruction, outputs and thin CLI needed for
image-only mapping. Task 036 will reuse this predictor for labeled scoring.
No label reads or model-quality evaluation belong in this task.

## Read and inputs

Read AGENTS → docs/index → docs/todo → tasks/README → this contract, then:

- [Architecture](../docs/architecture.md), especially prediction and scoring.
- [Quickstart](../docs/quickstart.md): cleaned inputs, portable models and tiny v2.
- [Experiments](../docs/experiments.md): portable prediction and evaluation boundaries.
- [Documentation](../docs/documentation.md) before editing researcher docs.
- Existing `model_bundle.py`, `preprocessing.py`, band helpers and their tests;
  reuse preparation window/raster utilities only where their behavior fits.

Inputs are a copied model directory, a small source CSV, and one TOML recipe.
Cleanup is a separate, once-per-release operation that saves cleaned TIFFs.
Inference reads those files repeatedly across models without cleaning again.
Raw inputs, arbitrary nodata conventions and label-dependent cleanup are not
performed inside prediction.

## Agreed behavior and defaults

### Inputs and settings

- Accept cleaned uint16 TIFFs with explicit native physical band order,
  all-native-band-zero nodata and usable CRS/transform. Validate headers once;
  reject incompatible inputs with guidance to the existing check/clean workflow.
  Do not repeat a full cleanup audit or guess bands from channel count.
- CSV required columns: `source_key`, `image`, `band_names`; serialize names as
  a semicolon-separated ordered list. Optional identity columns: `dataset_id`,
  `release_id`, `region_id`, `acquisition_date`, `original_source_id`,
  `row_offset`, `col_offset`. Keep supplied identities; missing optional
  metadata remains explicitly unknown. Require unique source keys and reject
  duplicate resolved image paths. Preserve the input filename/path.
- CSV paths resolve from one explicit image root. Prediction does not require
  training chips, split controls, labels, W&B or the training recipe.
- Recipe fields: `model`, `manifest`, `image_root`, `output`, `stride`,
  `min_valid_fraction`, `batch_size`, `device`. Paths resolve relative to the
  recipe; keep machine-specific values together in that file. Reject unknown
  fields. Defaults: stride 256, minimum valid fraction 0.20, batch size 1,
  device `cpu`; allow explicit `cuda` for later GPU use.
- The copied bundle owns input size (currently 512), model channel order,
  normalization, selected weights and threshold (currently 0.5). Do not
  duplicate or override these scientific settings in the prediction recipe.

### Windows and reconstruction

- Use 512 × 512 windows by default, reading source windows through Rasterio.
  Require positive stride no greater than model input size.
- Shift final bottom/right windows inward to the image boundary where a full
  window fits. Deduplicate starts. Cover the entire source geometrically before
  the validity filter; do not change training-chip window behavior.
- For dimensions smaller than 512, pad bottom/right with zero. Record actual
  source offset, true dimensions and padding; remove padding before placement.
- Determine validity from all native bands before selecting model channels.
  Skip windows with valid fraction **less than 0.20**; exactly 20% is retained.
  The denominator is actual source pixels, excluding artificial padding.
  Make the fraction configurable in [0, 1]; always skip entirely nodata windows.
- Apply the same shared preprocessing as portable image-array prediction.
  Average foreground probabilities equally over retained contributions at each
  valid source pixel. Threshold the reconstructed probability once using >=0.5
  for the current bundle. Never average binary masks or treat invalid pixels
  as zero-valued probability contributions.
- Track source nodata separately from valid pixels with zero contributions.
  Retained neighbors can cover pixels inside skipped windows. Compute coverage
  from the reconstructed contribution counts, not summed window areas.
- Valid uncovered pixels are an allowed result of the explicit validity filter.
  They remain missing predictions, never background. All-skipped sources produce
  valid all-nodata output files and a clear zero-coverage summary.

### Outputs

Create a fresh output directory, refuse existing destinations initially and stop
on the first failure. No restart, resume, partial reuse or rollback framework.
Publish final manifests only after all sources finish, using the existing
simple atomic-file convention. A failed folder is incomplete and is not reused.

For each source, write losslessly compressed GeoTIFFs preserving exact width,
height, CRS and transform, without reprojection or resampling:

- `probabilities/<source_key>.tif`: float32 probabilities; NaN for no prediction.
- `masks/<source_key>.tif`: uint8 background 0, kelp 1, no prediction 255.

Use safe unique source keys for filenames; reject invalid keys rather than
silently rewriting them. Both source nodata and uncovered valid pixels have
no prediction in these two rasters; distinguish their reasons in coverage
counts and through the original image validity, not an extra mandatory raster.
Do not inherit stale source masks, band metadata or nodata settings into outputs.

Also write:

- `sources.csv`: source identities and input/output paths plus unique total,
  native-valid, native-nodata, predicted-valid and uncovered-valid pixel counts.
- `windows.csv`: source key, actual row/column, true height/width, padding,
  valid fraction and retained/skipped disposition. No per-window prediction files.
- `settings.json`: resolved recipe and the copied bundle's prediction metadata,
  including selected model identity and threshold; no new hashes or receipts.
- `summary.json`: completion status, source/window counts and coverage totals.

Log resolved inputs, bands, outputs and source counts before prediction;
report current file, window progress and coverage using standard logging.
No figures or label metrics are required. Large generated artifacts stay outside Git.

## Implementation plan

This contract is the pre-implementation plan; do not add a second planning layer.
The filenames and command below are now implemented.

1. Add `src/kelpseg/prediction/settings.py` for one settings definition and plain
   CSV/header validation; add `configs/predict/example.toml` and a documented
   minimal CSV example. Reuse existing path/band helpers without importing a
   training configuration or extending a generic configuration framework.
2. Extend `src/kelpseg/model_bundle.py` only as needed for bounded batch inference.
   Use the existing preprocessing and native `torch.stack`, `model.eval()` and
   `torch.inference_mode()`. Keep the single-image API working through the same
   path. Construct the transform once per loaded predictor. Use float32 inference;
   no custom precision, device, checkpoint or prediction framework.
3. Add `src/kelpseg/prediction/windows.py` with small explicit window-start and
   placement functions, and `src/kelpseg/prediction/predict.py` for sequential
   source processing and outputs. Use Rasterio reads/writes and ordinary NumPy
   sums/counts. Keep one source's accumulators in memory; stream tile batches
   and output blocks where convenient. Document the source-size memory cost.
   Do not introduce disk-backed mosaics, distributed execution or worker pools
   absent a demonstrated requirement from the bounded real smoke.
4. Add a thin `src/kelpseg/cli/predict.py`, registered lazily with the existing
   CLI, exposing planned `uv run kelpseg predict --recipe <recipe.toml>`.
   Share ordinary prediction functions with notebook use and future Task 036.
5. Add focused `tests/test_prediction.py`, extend bundle/CLI tests as needed,
   and grow the installed tiny walkthrough in `docs/quickstart.md`. Update
   architecture/index/queue to describe implementation only after it exists.

Prefer common PyTorch and Rasterio operations over new abstractions. Lightning
continues to own training; a direct inference loop is sufficient here, without
creating a second Trainer/LightningModule just to read TIFF windows. Reuse
library functionality whenever it matches the contract. Do not add a new ML
or tiling dependency for a short explicit loop, custom Dataset/DataModule,
callback stack, registries, generic writers or a parallel executor.

Keep parameter/return annotations and useful function docstrings. Use plain
loops, clear names and short functions; fewer layers and less duplicated code
matter more than reducing readable code to clever expressions. Retain legacy
scoring/suite consumers until Tasks 036–037 replace them; remove only code
actually made obsolete by this task.

## User decisions required

No blocking scientific decisions remain. The user agreed to saved cleanup,
shifted bottom/right windows, configurable sparse-window skipping and image-only
prediction. The exact-20% case uses the stated default: retain, skip below 20%.
Recipe/schema details, CPU batch size 1 and plain per-source accumulators are
implementation defaults that may be refined for clarity without expanding scope.
The user subsequently authorized local implementation and testing without remote
changes or commits.

## Smoke and validation

Use deterministic fixture predictions for spatial/arithmetic tests, plus a small
real copied-bundle smoke. Do not require production training or GPU availability.

- Verify exact and non-multiple dimensions, both small and mixed small/large
  dimensions, bottom/right inward shifts, no duplicate starts and full geometric
  coverage before filtering. Coordinate-sensitive fixture predictions must catch
  offsets/padding errors, not merely produce a constant output.
- Test native validity before band selection, 0%, below/exactly/above 20%,
  padding excluded from the denominator, all-skipped sources and overlap recovery
  of pixels inside skipped windows. Assert unique coverage-count identities.
- Use differing overlapping probabilities to prove equal averaging followed by
  one threshold, with nodata/uncovered excluded and exact-threshold behavior.
- Round-trip GeoTIFF dimensions, CRS, transform, probability/mask values and
  nodata; verify identity/window records and no overwrites.
- Compare batch size 1 versus a small batch (including a short final batch), and
  single-image versus tiled prediction for an eligible source within one canvas.
  Preserve four-recipe band-selection coverage in existing bundle tests.
- Check actionable errors for ordinary invalid settings, duplicate identities,
  missing files, unsupported dtype/bands/georeferencing and raw nodata policy.
- Copy a tiny bundle and cleaned training/validation example into a fresh external
  directory with no labels/config registry. Run the installed command offline;
  inspect its rasters/coverage. Exercise a multiwindow example and small-image
  padding. No held-out test payloads or model-quality selection in this smoke.
- Verify installed-package imports and CLI behavior without legacy checkout
  dependencies; run focused tests, `uv run ruff format --check .`,
  `uv run ruff check .`, `uv run pre-commit run --all-files` for this multi-file
  implementation, and `git diff --check`. Record unrelated existing failures.
- For this planning-only change: inspect Markdown/diffs, verify relative links
  and run `git diff --check`; no behavioral test claim.

## Acceptance and non-goals

A researcher can predict from copied weights and cleaned imagery by editing
ordinary settings only, with no labels, network services or training paths.
Spatial placement, coverage exclusions, batch equivalence and offline installed
use pass the checks above. The same functions are ready for Task 036 to consume
without a second predictor. No scoring, threshold tuning, test-set inspection,
LORO runner, raw cleanup inside inference, TTA, weighted blending, cloud storage
service, restart system or production GPU benchmarking. Leave remote jobs and
source imagery unchanged. Do not commit or push without an explicit request.

## Outcome template

- Changed repository files and obsolete code removed:
- Durable external smoke artifacts:
- Validation and practical memory/device limits:
- Simplicity review and unresolved issues:
- Exact next action: Task 036 contract for labeled scoring and qualitative figures;
  stop before implementing that task.

## Outcome — 2026-11-04

- Implemented `kelpseg predict --recipe ...` with thin CLI, flat typed settings,
  explicit source CSV validation, inward-shifted windows and sequential source
  reconstruction. `prediction/settings.py`, `windows.py` and `predict.py` use
  Rasterio, NumPy and standard-library parsing/logging; no dependencies added.
- Extended `PortableModel` with bounded `predict_batch`, shared cached
  preprocessing and the existing single-array API. Native validity precedes
  channel selection; padding is inverted before source placement. PyTorch owns
  stacking, evaluation mode and inference mode; no new Trainer or dataset layer.
- Outputs include lossless probability/mask GeoTIFFs and plain settings,
  identity/window/coverage records. Native nodata and skipped-window gaps are
  distinct counts; neither becomes background. Fresh outputs only; no recovery.
- Updated researcher guide, example prediction recipe, README, architecture,
  experiment docs and task routing. Existing legacy scoring/suite code remains
  because Tasks 036–037 still own those consumers; no unrelated removal.
- Local smoke artifacts: `/Volumes/x10pro/kelpseg/analyses/task035_inference_v1/`.
  Reused Task 033G's copied RGB SegFormer B3 bundle with native eight-band inputs;
  copied only tiny-v2 baseline validation imagery, plus a 127 × 193 image crop.
  No label or test payload reads, remote access or production training.
- Installed the built wheel into the existing isolated runtime-only environment
  `/tmp/task033g-installed`, and ran from the external smoke directory with
  Hugging Face offline. Both batch-2 and batch-1 runs produced 614,335 covered
  valid pixels across two sources/five windows, with no gaps in these examples.
  Exact CRS/transforms/dimensions and mask thresholding verified. Batch maximum
  absolute probability difference was 9.5367431640625e-7; the small source also
  matches the original single-array predictor. Evidence: `verification.json`,
  recipes, copied inputs/model, distributions and command logs under that root.
- The smoke caught prediction logs being scoped to the preparation logger;
  the existing helper now accepts a logger name while preserving its default.
  The installed rerun confirms visible source/window/coverage progress.
- Focused synthetic checks cover sparse/all-skipped sources, overlap recovery,
  exact 20% retention, padding, spatial placement, overlap-before-threshold,
  native-band validity, batch tails, identity and ordinary settings/input errors.
  `uv run pytest -q tests/test_prediction.py tests/test_prediction_inputs.py
  tests/test_model_bundle.py tests/test_validation_report.py tests/test_package_cli.py`
  passes 84 tests; the sole warning is the intentional ungeoreferenced error
  fixture. `uv run pytest -q tests/test_distribution.py` also passes (one test,
  both wheel/sdist runtime-only installations), including installed raster
  prediction and visible progress logs.
- `uv run ruff format --check .`, `uv run ruff check .`, pre-commit all-files
  plus explicit new-file hooks, relative Markdown links and `git diff --check`
  pass. Pre-commit initially applied an import-order fix; the subsequent run
  passes. No unrelated failures observed.
- Simplicity/limits: one source's full-size accumulators remain in RAM (9
  bytes/pixel before output/temp/model memory). No giant-mosaic streaming backend
  or GPU throughput claim. Tiny outputs establish execution/spatial correctness,
  not segmentation quality. No unresolved correctness issues identified.
- Exact next action: select and write Task 036 for labeled scoring and qualitative
  figures using this image-only predictor. Stop before its implementation.

## Researcher maintainability review — 2026-11-05

- Reviewed the prediction workflow, portable batching, input settings/window
  helpers, CLI and tests. Keep flat recipes, ordinary CSV/JSON records and
  standard PyTorch/Rasterio/NumPy operations. No new dependency or framework.
- Fixed an initial-output collision: keys differing only by case could map to
  the same TIFF on macOS. Validation now rejects these before prediction while
  retaining original key spelling. Added a regression with distinct source images.
- Band/date errors now identify the source key and CSV line; date errors explain
  the expected format. Use public `dataclasses.fields` for allowed settings.
  Added focused error-context tests and clarified recipe comments.
- Extracted the small GeoTIFF writer from the source loop, retaining the exact
  profile/encoding. Added comments at native-validity accumulation and
  probability averaging where the scientific intent matters. Removed a redundant
  stride check already covered by settings and the fixed-size bundle contract.
- Progress now logs every ten windows: the real full-source check had fewer than
  100 windows and previously showed no intermediate progress during its CPU run.
  Added public bundle-loader annotations; prediction behavior is unchanged.
- Full validation-image follow-up artifacts are retained at
  `/Volumes/x10pro/kelpseg/analyses/task035_full_validation_v1/`, using the
  production eight-band EMA bundle copied in `task035_production_model_v1/`:
  2,416 × 2,816 TIFF, 5,291,939 valid pixels predicted,
  zero uncovered valid pixels. Georeferencing/mask checks and browser controls
  passed. The external diagnostic viewer displays NIR/red/green clipped at 2000;
  it is not a dependency of inference and does not alter model preprocessing.
- Validation: 87 focused tests pass (one expected ungeoreferenced-fixture warning);
  the separate distribution test passes for both wheel/sdist runtime-only installs.
  Ruff formatting/lint, pre-commit all-files plus changed new-file hooks and
  `git diff --check` pass. Remote training and existing predictions were untouched;
  no commits. Next action remains Task 036 planning when selected.
