# Task 036B: Temporal error and matched-footprint change analysis

Status: Complete — 2026-11-05.
Depends on: Completed [Task 036](036_shared_scoring_and_reports.md).

## Abstract

Extend saved labeled evaluation with date/year/month summaries and proportional
canopy-area change comparisons on common footprints. The primary question is
whether predictions reproduce the percentage change shown by labels. Separate actual label
change from changes in model error or geographic coverage. Reuse Task 036
outputs, identity joins, metrics and figures; never rerun inference. This is a
bounded analysis task, not a time-series modeling or spatial mosaicking framework.
The user explicitly requested this separate contract to keep Task 036 smaller.

## Read and inputs

Read AGENTS → docs/index → docs/todo → tasks/README → this contract, then
[product](../docs/product.md), [experiments](../docs/experiments.md#evaluation-and-comparison),
[architecture](../docs/architecture.md), Task 036's final outcome and
[documentation](../docs/documentation.md) before docs edits.
Inspect the implemented Task 036 schemas and shared report code before editing;
this contract does not prescribe a competing artifact format ahead of that work.

Inputs are completed Task 036 reports and their referenced predictions, cleaned
labels, grids, source identities and declared evaluation scope. Summary tables
alone suffice for descriptive grouping; matched-footprint comparisons also need
the referenced rasters. No model weights, inference or training is required.

## Implemented CLI

Available:

```text
kelpseg temporal-report --recipe <temporal.toml>
```

Uses small `reporting/temporal.py` for grouping/reporting,
`reporting/temporal_pairs.py` for supported common-grid comparisons, thin
`cli/temporal_report.py`, and `configs/report/temporal.toml`. Reuse Task 036
input, metric and rendering functions. Split files only where responsibilities
warrant it; use plain functions, records and sequential loops.

Use existing NumPy/Rasterio operations and plotting libraries. Use pandas grouping
only if already available and clearer than ordinary aggregation. Do not write
custom reprojection, polygon overlay, spatial matching, trend estimation, time
series infrastructure or artifact bookkeeping. Do not add a dependency when the
bounded supported-grid problem fits existing libraries.

## Behavior and outputs

- Preserve model, split, experiment, region, source, acquisition date and coverage
  scope. Do not mix chip and TIFF scopes, models or different split definitions
  into one pooled score. Unknown dates/regions remain explicit and unavailable
  for affected groupings; do not infer dates from output filenames.
- Summarize confusion counts, scoreable area, label prevalence, predicted/labeled
  kelp area, signed area error and FP/FN counts/area by region/date, region/year
  and region/month. Include represented year-month as well as any pooled calendar
  month summary; show actual dates, source counts and support. Keep zero-kelp
  cases and undefined ratios. Aggregate counts before calculating metrics.
- Label sums across acquisitions as observation-pixel/area totals, not unique
  land/coast area. Reuse Task 036's within-original deduplication. Distinct
  same-day observations are not assumed spatially unique or averaged into a
  date mosaic. Where they overlap, withhold unique date-area claims unless an
  explicit input selection resolves them.
- Plot signed area error through time within locations, alongside labeled area,
  false positives/negatives and coverage. Keep California and Baja scope explicit.
  Show where region/date support differs; do not turn changing region composition
  into an apparent statewide annual bias. These are descriptive diagnostics,
  without unsupported trend significance or ecological-cause claims.
- Default candidate pairs are ordinary within-region/date combinations, grouped
  by dataset/release/region with no geographic matching engine. Configurable
  inclusive day ranges default to 1–13 (short) and 29–47 (long). Same-day pairs
  remain separate and are not temporal change results; other gaps are omitted.
  An optional explicit pair CSV (`earlier_source,later_source`) uses exact
  `source_keys` identities from the input report and restricts comparisons.
  Preserve explicit unsupported pairs with reasons; reject unknown/duplicate
  identities and reversed dates. Unknown region/date rows stay in source outputs
  with exclusion reasons. Do not infer metadata from filenames.
- Initially support grids with identical projected-metre CRS, pixel basis and
  integer-pixel-aligned origins. Use Rasterio windows/transforms to intersect
  extents and NumPy masks for common valid imagery, finite predictions and
  valid labels at both dates. No nearest/bilinear reprojection to make a pair fit.
  Nonmatching grids, absent overlap or absent common scoreable pixels produce
  an explicit unavailable reason. A future broader-grid feature needs its own
  scientific decision and task.
- Compute both dates' predicted/labeled kelp counts and areas on exactly the
  same common footprint. Primary metrics are label percentage change
  `100 * (L_after - L_before) / L_before`, prediction percentage change
  `100 * (P_after - P_before) / P_before`, and predicted minus labeled change
  in percentage points. Matching +10% changes give zero error even with constant
  multiplicative area bias. No epsilon, pseudocount or clipping of percentages.
- A zero starting count makes that series' percentage undefined; percentage-point
  error is undefined unless both percentages exist. Preserve counts, absolute
  changes and explicit zero-baseline reasons. Flag small nonzero starting counts
  (configurable `small_baseline_pixels`, default 10 inclusive) without dropping
  them. Also report both date biases, common area, coverage fractions, day gap
  and absolute area-change error. Labels can change during either interval.
- Summarize pair error by dataset/release/region and interval: total/spatially
  supported/percentage-defined counts, median signed and mean/median absolute
  percentage-point error. Do not pool paired percentages or call repeated pairs
  independent samples; show region imbalance. Date/year/month tables remain
  descriptive observation totals, not the primary change measure.
- Pairwise common footprints can differ between pairs. Label this explicitly;
  do not connect pair-specific areas into a purported fixed-footprint trend.
  Cross-model paired LORO comparisons remain Task 037.
- Write compact grouped CSVs, `pairs.csv` including unavailable reasons,
  `summary.json`, HTML and PNG plots to a fresh external directory. Read saved
  artifacts only; standard progress logs, initial overwrite refusal, stop on
  failure, no resume/recovery, hashing or receipts. Keep per-pair memory bounded.

## User decisions required

No blocking choices remain. The user selected elapsed-day ranges and percentage
change relative to labels, and authorized implementation. Optional pair CSV and
matching-grid-only support keep ordinary use simple. Read-only validation audit
found 36 supported short source pairs across eight regions and 26 long pairs
across three regions (19 long pairs in region 008); prediction coverage remains
unmeasured until inference exists. Evidence lives outside Git in
`/Volumes/x10pro/kelpseg/analyses/task036b_day_range_support_v1/`.
If no real pairs qualify, record that limit and demonstrate arithmetic with
fixtures; do not expand into reprojection or fabricate temporal evidence.
Production test evaluation and scientific selection of model settings remain
outside this implementation task.

## Smoke and validation

- Fixtures verify +10%/+10% agreement despite multiplicative area bias, unequal
  percent changes, zero and small baselines, inclusive interval endpoints, and
  common-footprint percentages. Also verify grouped counts/ratios, zero-kelp and unknown-date handling,
  year-month versus pooled-month summaries, and separation of models/scopes.
- Two-date fixtures with shifted aligned extents, missing predictions and ignored
  labels prove both dates use the same intersection. Include a case where
  differing raw footprints create a false apparent change that disappears on
  the common footprint; verify signed change and area arithmetic exactly.
- Test invalid pair joins/date order, incompatible grids, empty intersections,
  same-day overlap limitations and explicit unavailable reasons. Reuse existing
  Task 036 deduplication tests rather than creating another implementation.
- Use bounded real validation reports for grouping and at least one pair when
  supported. Record actual available pairs, gaps and coverage. Inspect generated
  tables/figures for misleading comparisons and readable labels. If current saved predictions lack a real temporal pair, verify a real single-date
  report with explicit no-pair output and use fixtures for pair arithmetic; record
  that limitation. No held-out payloads, production inference, remote modifications
  or training. The user explicitly deferred the full 53-TIFF run.
- Run relevant report/CLI tests, an installed tiny command smoke, Ruff formatting
  and lint, pre-commit all-files for multi-file code, relative-doc links and
  `git diff --check`; record preexisting failures. Update the researcher guide
  and current docs only for behavior actually implemented.

## Acceptance and non-goals

A researcher can inspect per-location error through represented dates and compare
supported changes on common footprints using saved outputs and a simple recipe.
Unsupported evidence remains visible, coverage is explicit, and existing metrics
and libraries do the work. No temporal smoothing, threshold tuning, forecasting,
automatic mosaicking, arbitrary-grid reprojection, causal attribution, new model
fitting or claims of uniform future-year generalization.

## Outcome — 2026-11-05

Implemented `kelpseg temporal-report --recipe <temporal.toml>` with a flat recipe,
optional exact-source pair CSV and the agreed default intervals. The main measure
is predicted minus labeled percentage change on the common scoreable footprint.
Zero baselines remain undefined; small positive baselines are flagged.

- Code: `reporting/temporal.py` orchestrates existing canvas loading and report
  writers; `temporal_inputs.py` handles recipes and pair selection;
  `temporal_pairs.py` uses Rasterio windows and NumPy masks;
  `temporal_summary.py` reuses count pooling and metrics; `temporal_views.py`
  reuses HTML tables and Matplotlib. Added the thin CLI and example recipe.
  README, quickstart, architecture, experiments and task routing describe the
  implemented workflow. No new dependencies or inference/model loading.
- Outputs: source/date/year/year-month/calendar-month tables, pair records and
  regional summaries, settings/summary JSON, HTML and two PNG figures. All
  observation totals and unavailable pairs retain their interpretation limits.
- Validation: 120 focused temporal, shared-report, validation-report, prediction
  and CLI tests passed. The wheel/sdist isolation test passed, including a
  two-date installed-command smoke. Ruff formatting/lint and pre-commit all-files
  passed. The only focused-test warning is the existing deliberately invalid
  geotransform fixture. Synthetic tests cover matching +10%/+10%, unequal
  changes, zero/small baselines, partial coverage, integer shifts, incompatible
  grids, same-day records, explicit joins and interval boundaries.
- External evidence:
  `/Volumes/x10pro/kelpseg/analyses/task036b_temporal_report_v1/` contains
  `real-single-date/`, `synthetic-report/`, final figures in `synthetic-final/`,
  source fixtures, recipes and `verification.json`. Real saved production output
  has one date and correctly yields zero pairs. Synthetic short change is
  +10%/+10% (0 percentage-point error); long change is +20%/+50% (30 points).
  Figures were inspected. No real paired prediction result is claimed.
- The earlier read-only validation audit found 43 short candidates (36 supported),
  26 long candidates (26 supported), and 10 same-day combinations. This is label/
  image support only; prediction coverage remains unmeasured. The full 53-TIFF
  inference run was not started, as requested.
- Simplicity review: small functions with separate input, arithmetic, grouping
  and rendering responsibilities; existing report readers supply chip/TIFF
  behavior. No reprojection, mosaics, model calls, recovery framework or new
  bookkeeping. At most two source canvases are retained per pair; repeated
  pairs reread saved rasters. Large-source runtime is not benchmarked here.

Exact next action: select and write Task 037 for LORO and matching-TIFF
comparisons; stop before implementation. Changes are left uncommitted for review.

## Code-quality follow-up — 2026-11-05

Reviewed pair arithmetic/grouping and CLI/loading/rendering independently; no
correctness defects found. Simplified three details: one owner for declared-date
validation, one shared location-field definition, and sets of represented dates
instead of retaining whole source rows solely to collect dates. Removed an unused
identity field from intermediate grouped records. Existing library calls and
small module responsibilities remain; no new abstractions or dependencies.

The 120 focused tests passed again, with only the existing invalid-geotransform
fixture warning. Ruff formatting/lint, pre-commit (including new temporal files)
and diff whitespace checks passed. The installed-distribution check from task
completion remains applicable; this pass changes no packaging or CLI interface.
No production inference, commits or unrelated-file changes. Next action remains
Task 037 contract selection, without implementation.

## Full validation report — 2026-11-05

The user supplied completed remote full-TIFF predictions and authorized local
analysis. No inference was rerun. Verified all 53 source identities exactly match
local baseline/augmented/val assignments, with the stated eight-band order and
all referenced images, labels and probabilities present. The saved model is the
original BCE/Dice best EMA at epoch 18 (model metadata uses zero-based epoch 17).

Artifacts are under
`/Volumes/x10pro/kelpseg/analyses/full_tiff_bce_dice_validation_20261105/`:

- `temporal_local_inputs/`: five saved-report metadata tables/settings with remote
  paths remapped to local paths; its README records the mapping. Original report
  and prediction files remain unchanged.
- `temporal.local.toml`: reproducible recipe using default intervals and baseline
  flags; `temporal-run.log`: completed command log, 11:04:32–11:05:30, about 58 seconds.
- `temporal_report/report.html`: real-data report, figures, CSVs and JSON.

There are 79 candidate pairs: 43 short, 26 long and 10 same-day. Short intervals
have 36 spatially supported pairs across eight regions, 35 with defined percent
errors. All 26 long pairs are supported and defined across three regions. Four
short pairs have incompatible CRS and three have no common scoreable pixels.
The August 2–5 region 006 pair has zero starting kelp in both series, so its
percentages remain undefined. Same-day pairs are separate and unscored.

The input has 234,792,909 valid observation pixels, of which 6,699 are uncovered
and excluded, leaving 234,786,210 scoreable pixels. Added explicit overall input
coverage to temporal summary JSON and HTML, alongside the existing pair coverage
fractions and dated tables. These counts are observation totals, not unique area.

The real plots were inspected. Long-interval support is heavily concentrated in
region 008 (19/26 pairs); percentage outliers are retained. Read regional error
tables and baseline counts rather than interpreting a pooled ecological trend.
The 24 temporal tests, Ruff formatting/lint, pre-commit all-files plus changed
new files, and whitespace checks pass. No weights, training or inference were
loaded; changes remain uncommitted. Next: review the real report with the user;
Task 037 remains unstarted.

Independent CSV verification confirmed every supported pair's arithmetic and
all regional summary statistics. Median smaller-of-two common-footprint coverage
is 85.00% short and 78.29% long. No supported pair has a positive starting count
at or below 10 pixels. Long-interval median absolute errors are 15.72 percentage
points in region 005 (2 pairs), 199.40 in 006 (5), and 80.13 in 008 (19).
Region 008's signed median is only +2.66 points, demonstrating why signed bias
alone should not be interpreted as agreement in temporal change.
