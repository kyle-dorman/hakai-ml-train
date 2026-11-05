# Task 036B: Temporal error and matched-footprint change analysis

Status: Planned — contract written 2026-11-05; implementation not started.
Depends on: Completed [Task 036](036_shared_scoring_and_reports.md).

## Abstract

Extend saved labeled evaluation with date/year/month summaries and supported
comparisons of kelp-area change on common footprints. Separate actual label
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

## Implementation plan and planned CLI

Planned, not implemented:

```text
kelpseg temporal-report --recipe <temporal.toml>
```

Add small `reporting/temporal.py` for grouping/reporting,
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
- Use an explicit pair CSV as the initial matched-footprint interface: location
  identity, earlier source and later source, referring to recorded prediction
  identities. This avoids a custom geographic/date matching engine. Validate
  dates and require the same model/scope. Preserve requested pairs and explain
  unsupported cases instead of silently dropping them.
- Initially support grids with identical projected-metre CRS, pixel basis and
  integer-pixel-aligned origins. Use Rasterio windows/transforms to intersect
  extents and NumPy masks for common valid imagery, finite predictions and
  valid labels at both dates. No nearest/bilinear reprojection to make a pair fit.
  Nonmatching grids, absent overlap or absent common scoreable pixels produce
  an explicit unavailable reason. A future broader-grid feature needs its own
  scientific decision and task.
- Compute both dates' predicted/labeled kelp areas on precisely the same common
  footprint. Report later-minus-earlier predicted change, labeled change and
  change error (predicted change minus labeled change), plus both date biases,
  pair coverage fractions and elapsed days. Record season/month/date gaps; do
  not imply regular temporal sampling or constant kelp should be expected.
- Pairwise common footprints can differ between pairs. Label this explicitly;
  do not connect pair-specific areas into a purported fixed-footprint trend.
  Cross-model paired LORO comparisons remain Task 037.
- Write compact grouped CSVs, `pairs.csv` including unavailable reasons,
  `summary.json`, HTML and PNG plots to a fresh external directory. Read saved
  artifacts only; standard progress logs, initial overwrite refusal, stop on
  failure, no resume/recovery, hashing or receipts. Keep per-pair memory bounded.

## User decisions required

No blocking planning choice remains. Explicit source pairs and matching-grid-only
support are conservative implementation defaults, not a claim that the current
dataset supplies enough pairs. Inspect actual validation support during execution.
If no real pairs qualify, record that limit and demonstrate arithmetic with
fixtures; do not expand into reprojection or fabricate temporal evidence.
Production test evaluation and scientific selection of model settings remain
outside this implementation task.

## Smoke and validation

- Fixtures verify grouped counts/ratios, zero-kelp and unknown-date handling,
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
  tables/figures for misleading comparisons and readable labels. No held-out
  payloads, production inference, remote modifications or training.
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

## Outcome template

- Changed files and shared functions reused:
- Durable external summaries, pair records and figures:
- Validation and actual temporal/footprint support:
- Simplicity/library reuse review and unresolved limitations:
- Exact next action: select and write Task 037 for LORO and matching-TIFF
  comparisons; stop before implementation.
