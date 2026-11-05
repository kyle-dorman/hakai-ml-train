# Task 036: Separate inference and share labeled reporting

Status: Complete — implementation and maintainability review verified 2026-11-05; no remote changes or commits.
Depends on: Completed Tasks 033 and 035. Task 034 remote work stays separate.

## Abstract

Separate the current validation-report command into saved chip inference and
report generation. Feed both those chip predictions and Task 035's existing
full-TIFF predictions into one shared labeled reporting implementation. Reuse
existing metrics and figures rather than building a second evaluator. The key
difference is evaluation footprint and prediction construction, not whether
chips are placed into source coordinates: the current report already does that.
Temporal analysis belongs to [Task 036B](036b_temporal_error_analysis.md).

The user authorized implementation of Task 036 only. Stop before Task 036B.

## Read and inputs

Read AGENTS → docs/index → docs/todo → tasks/README → this contract, then
[architecture](../docs/architecture.md), [experiments](../docs/experiments.md),
[quickstart](../docs/quickstart.md), and
[documentation](../docs/documentation.md) before docs edits.
Inspect `validation_report/{__init__,metrics,selection,views}.py`,
`prediction/`, `model_bundle.py`, their CLI/tests, and
`run_loss_comparisons.sh`. Preserve useful tested diagnostics and training sample
selection. Do not change a running remote experiment.

Inputs:

- Chip inference: completed training run, its selected portable model, canonical
  chip/split references, and existing val or seeded unaugmented train selection.
- TIFF inference: the implemented Task 035 recipe and image-only source manifest.
- Reporting: one completed saved prediction directory; chip labels from recorded
  payload references, or a CSV joining TIFF `source_key` to cleaned label paths
  under an explicit label root. TIFF reports also require declared evaluation
  membership (assignment reference and experiment/variant/split, or an explicit
  external evaluation scope). Never guess membership from filenames.
- Imagery references and native band names for figures; reporting needs no model
  weights, GPU, W&B, or live training configuration. Referenced data must remain
  available; standalone duplication of all imagery/labels is not required.

## Agreed CLI and implementation plan

The following contract commands are now implemented:

```text
kelpseg train --recipe <training.toml>
kelpseg predict-chips --run <completed-run> --output <predictions> [--split val|train] [--device cpu|cuda]
kelpseg report --recipe <report.toml>
```

The other inference path remains the implemented command:

```text
kelpseg predict --recipe <prediction.toml>
kelpseg report --recipe <report.toml>
```

1. Extract chip selection/inference from `validation_report/__init__.py` into
   `prediction/chips.py`, with thin `cli/predict_chips.py`. Keep existing source
   selection, training sample seed/count options, preprocessing, disjoint chip
   geometry and padding inversion. Use `PortableModel`; no second model loader.
   Inference reads image arrays only for model input; label values must not affect
   prediction, window selection or prediction coverage.
2. Save chip probabilities as lossless float32 source-canvas GeoTIFFs using
   Rasterio, with NaN gaps and correct offset-adjusted transforms. Reuse Task
   035 raster-writing helpers where appropriate. Preserve source identities,
   original offsets, selected windows, payload references, bands, model identity,
   threshold, selection and coverage in ordinary CSV/JSON. Use Task 035's existing
   `sources.csv`, `windows.csv`, `settings.json`, `summary.json` conventions where
   they fit; add only fields needed to explain chip scope. Do not create a new
   artifact framework, version registry, receipt or hash system. Chip masks are
   unnecessary if reporting can threshold saved probabilities.
3. Move shared reporting into small `reporting/` modules: `inputs.py` for the
   two explicit input readers and label joins, `report.py` for the sequential
   source loop/aggregation, and reused `metrics.py`/`views.py` for calculations
   and rendering. Ordinary functions provide aligned probabilities, labels,
   scoreable masks and identity/grid metadata. No provider classes, plugin
   registry, generic execution engine or parallel writer abstraction.
4. Add thin `cli/report.py` and `configs/report/chips.toml` and `tiffs.toml`.
   Flat settings contain prediction/output paths, TIFF label/membership inputs
   when needed, and bounded example selection. Paths resolve relative to the
   recipe with explicit data roots. Unknown settings and missing/duplicate joins
   fail with actionable errors. The saved prediction threshold is authoritative;
   reporting does not silently replace it or select a better threshold.
5. Retire the combined `validation-report` CLI and obsolete orchestration after
   migrating its callers. Update `run_loss_comparisons.sh` to run train →
   predict-chips → report sequentially, stopping on failure. Update CLI tests,
   quickstart, architecture/index and task routing. No unnecessary compatibility
   wrapper: breaking CLI changes are authorized. Do not remove unrelated legacy
   scoring/suite consumers still needed by Task 037.

Simple code and library reuse are acceptance requirements. Use NumPy for array
operations, Rasterio for raster I/O/windows/grids, existing OpenCV/SciPy metric
helpers, and existing plotting/HTML code. Reuse existing probability metric
implementations where applicable. Do not reimplement library operations or add
custom tiling, geospatial alignment, serialization or metric frameworks. Use
plain loops and small typed functions with purpose/input/output docstrings.
Before adding a dependency, check whether installed libraries already suffice.

## Scientific behavior and outputs

- Distinguish `chip_disjoint` from `tiff_tiled` scope in report headings and
  machine-readable outputs. Chip coverage retains existing gaps; TIFF coverage
  uses Task 035's averaged overlap probabilities and shifted-edge windows.
  Reporting never reruns inference or stitches the chip path using TIFF rules.
- Match cleaned labels exactly to the image grid; reject mismatched dimensions,
  CRS or transform with cleanup guidance. No implicit reprojection or resampling.
  Reuse the existing stored-label mapping to binary/ignore -100; image validity,
  prediction coverage and label validity are separate exclusions. Stored label
  background must not disappear because of label nodata metadata.
- Score each covered valid labeled original-source pixel once. Preserve dataset,
  release, original TIFF, crop offsets, region/date, split and model identity.
  Where multiple declared crops overlap on one original grid, average their
  finite probabilities before thresholding once and require agreement of valid
  overlapping labels. Group only explicitly identified common originals; missing
  optional identities remain unknown. Never combine different acquisitions as
  if they were one image. Validate grid/offset relationships before combining.
- Preserve existing confusion metrics, area bias, regional pooling, probability,
  boundary, patch-size and qualitative diagnostics through shared functions.
  Add labeled prevalence/coverage fields if missing. Pool counts, not image IoUs;
  retain zero-kelp cases and explicit undefined metrics. Report area only under
  the existing supported projected-metre grid policy, using the affine pixel area.
- Retain diagnostic threshold sweeps for train/validation as descriptive outputs,
  without choosing a threshold. Test reports use the fixed saved threshold and
  omit exploratory threshold sweeps. Test membership must be explicitly selected
  after model selection; task development/smokes use no held-out payloads.
- Keep per-window background diagnostics for chip inputs; label them inapplicable
  for TIFF inputs rather than manufacturing equivalent chips. Boundary/patch
  calculations respect observed coverage; truncated components retain their
  existing explicit treatment. Neither report claims independent ecological truth.
- Reports write HTML, CSV, JSON and bounded PNG figures outside Git. Reuse current
  tables and example rendering; captions retain original source/window identity.
  Record deterministic example selection, include low/zero-kelp examples where
  available, and distinguish diagnostic examples from representative scores.
- Report generation can repeat into a fresh directory from saved predictions
  without loading weights or running a forward pass. Keep source/date counts,
  areas and identities usable by Task 036B. Temporal summaries and comparisons
  are excluded here; per-source signed area bias remains an existing diagnostic.
- Use fresh output directories with initial overwrite refusal, ordinary progress
  logging and final manifests published only on completion. Stop on failure;
  no restart/resume/recovery, concurrent-writer guards or repeated payload audits.
  Process one source at a time and document practical memory limits.

## User decisions required

No blocking design choices remain: the user selected two inference CLI paths,
one shared report command, and separate temporal Task 036B. The command names,
flat recipe layout and Rasterio source-canvas format above are implementation
defaults. Refine details only to simplify ordinary use without changing scientific
scope. Do not introduce additional orchestration or storage machinery.

## Smoke and validation

- Preserve existing metric, probability, boundary, patch and figure tests. A
  deterministic fixture must show the extracted chip workflow reproduces the
  former combined report's predictions, counts and diagnostics on the same
  footprint, including seeded train selection and background-only windows.
- Use identical aligned arrays/coverage through both readers and assert identical
  shared report results. Verify sparse/all-skipped predictions, ignored labels,
  native nodata, zero-kelp cases, undefined scores and unique coverage counts.
- Test overlapping crops of one original with differing probabilities: count
  once, average before threshold, preserve offsets, and reject conflicting labels
  or incompatible grids. Test pooled region/global counts and affine area units.
- Verify exact label mapping/alignment, missing/duplicate identity joins, scope
  metadata, fixed thresholds, and explicit test-scope behavior without test data.
- Run report after making weights unavailable; assert no model load/forward is
  needed. Change report output/example settings and rerun without inference.
- Extend tiny-v2 with installed predict-chips → report and existing predict →
  report using bounded training/validation imagery and copied weights. Inspect
  HTML/PNG legibility and raster alignment; no production fitting or remote edits.
- Run focused prediction/report/bundle/CLI tests, runtime-only wheel/sdist checks,
  `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run pre-commit run --all-files`, relative-doc link checks and
  `git diff --check`. Record unrelated preexisting failures explicitly.

## Acceptance and non-goals

A researcher can run either inference path and then the same report command;
report regeneration requires no model execution. Existing chip diagnostics retain
their definitions, and source-TIFF evaluation reports its own measured coverage.
Metrics/figures have one implementation and shell recipes remain plain sequences.
No temporal analysis, LORO runner, model selection, threshold tuning, production
benchmarking, new training, data cleanup or generalized reporting framework.

## Outcome template

- Changed files and obsolete code/CLI removed:
- Durable external prediction/report artifacts:
- Validation, parity evidence and memory limits:
- Simplicity/library reuse review and unresolved issues:
- Exact next action: select Task 036B for temporal analysis; stop before execution.


## Outcome — 2026-11-05

- Implemented `predict-chips` and `report --recipe`; retained Task 035 `predict`.
  Removed the combined `validation-report` CLI and old package. Chip inference
  lives in `prediction/chips.py`; shared label loading, source canvases, metrics,
  figures and report output live in small modules under `reporting/`.
- Reused the former metric/figure implementations, existing portable model and
  selector, stored-label mapper, NumPy/Rasterio/OpenCV/Matplotlib operations.
  Added no dependencies. Moved the fixed example selector into
  `prediction/selection.py` so training panels and reports share it; no framework,
  hashing, receipts, recovery or custom geospatial resampling was introduced.
- Chip inference reads only images and writes georeferenced source probability
  canvases, selected-window references and plain coverage/model/selection records.
  Report reads those outputs or existing TIFF prediction outputs without model
  loading. Exact label grids, explicit membership, original-crop overlap averaging,
  label agreement and unique coverage are enforced. Unknown original identities
  retain distinct source keys; `input_sources.csv` preserves original references.
- Shared reports preserve existing diagnostics, show coverage explicitly, use the
  saved threshold, omit test threshold sweeps, and retain undefined metrics.
  Chip-only background-window summaries stay separate from TIFF examples. Source
  identity, bands, offsets, split and dates remain available for later analysis.
- Updated CLI registration, `configs/report/`, README, quickstart, architecture,
  experiments and task routers. `run_loss_comparisons.sh` now runs inference then
  report after each training run, stopping on failure. Its tests also exposed
  GNU-only `realpath` flags on macOS; standard `pathlib` now resolves these paths.
- Durable real-data evidence is under
  `/Volumes/x10pro/kelpseg/analyses/task036_reports_v1/`: copied tiny RGB bundle/run
  reference, old reference report, saved chip/TIFF predictions, installed reports,
  recipes, logs, distributions, `parity.json` and `verification.json`.
  No source data or remote runs were modified. Used tiny-v2 validation imagery
  and labels only; no held-out test payloads or production fitting.
- Captured the old combined report before removing it. The new installed chip
  report matches every prior numerical column exactly: global/source/region and
  background metrics, patch sizes, boundaries, error zones, threshold sweeps and
  probability histograms. Its two source canvases score 524,288 pixels.
- The installed full-TIFF check uses one 768-square validation crop plus a nested
  127 × 193 crop. Raw predictions cover 614,335 pixel observations; the report
  averages the overlap and scores 589,824 unique original pixels, with no gaps.
  HTML scope/coverage and false-color/error PNGs were inspected; figures are
  legible. Tiny results establish execution and spatial correctness, not quality.
- Built wheel/sdist; runtime-only distribution tests pass for both installation
  routes. Installed the final wheel into `/tmp/task033g-installed` and ran both
  inference/report paths offline from the external artifact directory. Removed
  the copied model from its expected location before both reports; both passed
  and reference parity remained exact. Restored that copied model afterward so
  saved example recipes remain usable. Import checks confirm reporting does not
  load Torch, Lightning, W&B or the model bundle module.
- Validation: 135 focused tests pass across prediction, bundle, reporting, CLI,
  shell sequencing and training visuals/loop; the separate distribution test
  passes (both wheel/sdist). Expected fixture georeferencing and existing
  Lightning/W&B diagnostic warnings remain; no unrelated test failures observed.
  Ruff format/lint, pre-commit all-files and explicit new-file hooks, relative
  documentation links and `git diff --check` pass.
- Limits: one original source's arrays and overlapping crop inputs remain in RAM;
  boundary/patch diagnostics allocate additional arrays. No giant-mosaic streaming
  backend or CUDA throughput claim. Area reporting requires projected metre grids;
  labels must align exactly. No unresolved correctness issue identified.
- Exact next action: select Task 036B for temporal analysis when requested. It is
  still planned and unstarted. No commits or pushes were made.


## Maintainability review — 2026-11-05

- Separated bounded example selection/rendering into `reporting/examples.py`.
  Background-chip scoring is now an explicit reporting function independent of
  figure limits. Separate sets track seen regions and zero-kelp example sources;
  no encoded sentinel strings or shared state with two meanings.
- Indexed saved windows once by source and replaced nested filtering with an
  explicit source loop. Retained plain dictionaries/functions and existing
  NumPy/Rasterio operations; no dependencies or frameworks were added.
- Removed duplicate full-array audits of generated probability ranges and chip
  label categories already validated upstream. Kept grid/shape/identity/nodata
  checks, external label mapping, overlap agreement and unique-pixel arithmetic.
- Fixed ordinary malformed recipe handling: non-table label mappings now raise
  actionable ValueError instead of AttributeError; boolean/float targets are
  rejected. Numeric zero crop offsets are accepted alongside CSV string zero.
- Rebuilt real chip/TIFF reports under the existing external artifact root as
  `quality-chip-report` and `quality-tiff-report`. Summaries, every CSV table and
  example PNG bytes match the pre-review reports exactly; evidence is in
  `quality-review.json`. No model execution or remote work was needed.
- 141 focused tests pass, including six malformed-mapping regressions. Existing
  fixture/Lightning/W&B warnings remain unchanged. Ruff formatting/lint,
  pre-commit all-files and explicit owned new-file hooks pass.
- Both wheel/sdist runtime-only installation checks also pass after the module
  extraction. `git diff --check` passes. No unresolved review findings remain.
- Task 036B and unrelated presentation work remain untouched. No commits.

## Bounded full-validation timing — 2026-11-05

- User requested timing/preparation only after the bounded sample; the full run
  was not launched. Downloaded production model is the eight-band BCE/Dice EMA
  bundle from `planet8-cabc-loss-bce-dice-70ep-20261105T004320758369Z`.
- Exact baseline/augmented validation assignment join selects 53 cleaned TIFFs
  across regions 001–010, 397,735,155 source pixels and 5,538 candidate tiles.
  All image/label files are local; prediction headers and both recipes validate.
- A fresh full-source sample (`002_20210228_182240_2406`) took 81.61 seconds for
  inference (86 retained / 90 candidate tiles) and 0.98 seconds for reporting,
  with CPU float32 and two Torch threads. All 5,291,939 valid pixels were covered.
  Linear extrapolation is about 84 minutes inference plus one minute reporting;
  allow 90–120 minutes for the full run because tile validity and scene complexity
  vary. This is a one-source estimate, not a measured full-set duration.
- External evidence/ready commands:
  `/Volumes/x10pro/kelpseg/analyses/task036_full_validation_v1/` contains full/sample
  manifests and recipes, sample outputs/log/timing, `estimate.json`, and a
  syntax-checked `run-full.sh` that sequentially predicts then reports. Full
  `predictions/` and `report/` outputs do not exist. No held-out test data read.
