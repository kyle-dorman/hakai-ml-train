# Task 040: Shore-distance coverage and pixel-level evaluation

Status: Complete — final code quality review passed; closed for commit, 2026-11-06.
Depends on: Completed Tasks 032A/032B and 036. Task 034 experiments remain separate.

## Abstract

Determine whether weak nearshore validation performance coincides with a shortage
or different distribution of nearshore labeled kelp in training. Build approximate
land masks and distance-to-land rasters aligned to source TIFFs, summarize labeled
kelp by region and train/validation/test, and add pixel-level distance diagnostics
to the existing report. This is descriptive evidence about agreement with labels,
not proof that distance or training representation causes the performance gap.

The user selected pixel-level analysis and requested task number 40 now, ahead
of roadmap slots 037–039. The implementation plan below is retained as the
accepted contract; all stages are complete. See the outcome for implemented
commands, production artifacts, validation and findings.

## Read and inputs

Read AGENTS → docs/index → docs/todo → tasks/README → this contract, then
[architecture](../docs/architecture.md), [product](../docs/product.md),
[data artifacts](../docs/data_artifacts.md), and
[documentation](../docs/documentation.md). Read the reporting portions of
[quickstart](../docs/quickstart.md) before integrating the commands. Read
[experiments](../docs/experiments.md) if changing prediction/run metadata.

Inputs:

- [Global Shoreline Dataset catalog](https://gee-community-catalog.org/projects/shoreline/).
  The catalog describes 30 m shoreline vectors derived from 2014 imagery and
  three complementary size classes, not three alternative shoreline estimates:
  `projects/sat-io/open-datasets/shoreline/mainlands`, `big_islands`, and
  `small_islands`. Combine all three. Retain source attribution and the catalog's
  stated CC BY-SA 4.0 license with downloaded/derived artifacts; verify the actual
  distribution terms and access route during acquisition.
- Existing cleaned imagery/labels, source identities/grids, canonical chip/window
  metadata, and locked experiment/variant/split assignments. Machine paths are
  explicit settings; do not assume historical Mac paths exist on this host.
- Saved chip or full-TIFF predictions and their fixed model threshold from Task
  036. Label inventory must run without any predictions or loaded model.

### Local availability and remaining download

Read-only inventory on 2026-11-06 found 53 cleaned image TIFFs and 53 label
TIFFs at `/home/sky/data/data/3_cleaned/ca_bc/v1/{images,labels}`: the validation
subset used for the completed full-TIFF report. Image payloads total
2,507,904,820 bytes; labels total 2,186,339 bytes. This is a file inventory, not
a fresh full-payload validation. The complete cleaned release contains 369 pairs.

Stage 1 must reconcile these local identities with the release manifest and
fetch the remaining 316 image/label pairs needed for the full-source inventory
from `kelp-box:kelpseg/data/3_cleaned/ca_bc/v1`. Preserve existing local files and
remote releases; use an explicit missing-file copy, not deletion-propagating
sync. Follow the existing bounded transfer check before the larger download.
Verify expected identities, counts and sizes and open a bounded sample after
transfer. Existing validation TIFFs can support the initial alignment/report
smoke before the full collection is available.

Canonical chips and `windows.csv` are already available under
`/home/sky/data/data/chips/ca_bc/v1`. No rechipping is required. Full cleaned
TIFFs are needed for the all-source label inventory, including pixels outside
the retained chip footprint; chip-only counts cannot substitute for that scope.

## User decisions required

No blocking scientific choice is needed to start. Safe initial defaults:

- Union mainland, large-island and small-island polygons; retain interior holes.
- Pixel-level distance bands in metres: `[0,30)`, `[30,60)`, `[60,120)`,
  `[120,250)`, `[250,500)`, and `>=500`, plus separate mapped-land and unknown
  categories. Ocean pixels with distance zero belong to the first band; land
  status is carried separately. Use `<60 m` as an initial nearshore summary and
  also show cumulative fractions at every band boundary. These are proposed
  analysis settings, not a claim of 30 m positional accuracy.
- Primary baseline uses the with-BC assignments. Keep region 011/012 training-only
  and show region-specific results so BC support cannot obscure CA/Baja gaps.
- Use existing completed validation predictions first. Test labels can describe
  split composition, but test performance remains held out until model selection
  is finished. Never use test information to change splits, bins to improve
  results, thresholds, recipes, or checkpoints.

If Earth Engine export requires unavailable user credentials, report that concrete
access blocker and request the missing access or exported polygons. Do not invent
a direct download URL or silently substitute another shoreline product. Continue
independent synthetic implementation while acquisition is blocked.

## Implementation plan and expected outputs

Work in the following bounded stages within task 040, recording each handoff.
If a stage exceeds one window, stop with its exact next action; do not start a
separate numbered roadmap task. Before implementation, mark this task In progress
and inspect existing source reconstruction, settings, CLI and report helpers.
Resolve exact field names against those helpers in this record before coding.

### 1. Acquire remaining cleaned inputs and a bounded shoreline subset

Reconcile and download the missing cleaned pairs as specified above.

Inspect the available export/download route and obtain all three collections for
the represented regions plus a halo. Prefer regional subsets over an unnecessary
global download. Record asset IDs, retrieval date, source reference/license,
export bounds/CRS, feature counts, and any geometry repair in ordinary metadata.
Empty island subsets can be legitimate; failed/missing exports are not ocean.

Inspect a bounded mainland, small-island and BC example against imagery. Shoreline
age, tides, missing rocks and positional error must remain visible in overlays.
Do not tune geometry using kelp labels or model errors. Confirm land polygons
and hole semantics before rasterizing; do not treat linework as filled land.

### 2. Prepare per-source land and distance artifacts

Planned files: `src/kelpseg/prepare/shoreline.py` for input/land raster preparation,
`src/kelpseg/prepare/shore_distance.py` for metric distance calculations, thin
`src/kelpseg/cli/shoreline.py`, and `configs/prepare/shoreline.toml`.
Planned installed command: `kelpseg prepare-shoreline --recipe <shoreline.toml>`.

- Rasterize the union onto each exact image grid using a documented pixel-center
  rule. Preserve source identity, CRS, transform, dimensions and original offsets.
  Masks/distance depend only on imagery geometry and shoreline inputs, not labels.
- Compute distance in metres from ocean pixel centers to the nearest polygon
  land boundary in an appropriate local metric CRS. Use ordinary geospatial
  functions; rasterize separately for land membership. If a raster distance
  transform is adopted for practicality, document its center-to-center distance
  convention and quantify the pixel-size approximation in the smoke check.
- Include land outside the image footprint. Export/search with a halo larger
  than 500 m plus pixel/transform margin. Distances below 500 m must be correct;
  distances beyond that may be capped at 500 m and explicitly documented as
  right-censored (`>=500`), never presented as exact offshore distances. Missing
  coverage is unknown, not far offshore. An entirely offshore TIFF is valid if
  its surrounding search coverage is complete.
- Validate supported CRS/units; reproject vectors for metric calculations without
  resampling source labels or predictions. Explain unsupported grids clearly.
- Write separate land-mask and float distance GeoTIFFs, a simple `sources.csv`,
  resolved settings, coverage counts and a small alignment gallery. Use explicit
  nodata values distinct from land and zero distance. Preserve interior lake/hole
  behavior and describe these as distance-to-land rather than a marine-water map.
- Keep source downloads, rasters and generated manifests outside Git, e.g.
  `<data_root>/references/shoreline/<release>/` and
  `<data_root>/analyses/shore_distance/<fresh-name>/`. Initial overwrite refusal,
  sequential processing, standard progress logging and atomic final manifests;
  no hashes, receipts, resume, partial-work reuse or new artifact framework.

### Using the source rasters with existing chips

Keep land/distance GeoTIFFs separate from canonical chip payloads. Join each
chip through `windows.csv` using `source_key`, then read the identical window
from its source-grid rasters using `row`, `col`, `height`, and `width`. Every
real chip pixel therefore receives a land flag and a distance without resizing,
resampling, rebuilding, or modifying the chip. Exclude artificial loader padding.

Calculate distances on the source grid with the shoreline halo before extracting
chip windows. Never compute a distance transform independently inside a chip:
the nearest land may lie outside that chip or outside its source TIFF.
For reconstructed original-source reporting, use `original_row`/`original_col`
and the existing source/crop offsets to place the same distances on the report
canvas. Validate the grid correspondence and count overlapping windows/crops
once per original-source pixel, preserving the existing report footprint.

### 3. Inventory labeled kelp by region and split

Planned files: `src/kelpseg/reporting/shore_inventory.py`, thin
`src/kelpseg/cli/shore_inventory.py`, and `configs/report/shore_inventory.toml`.
Planned installed command: `kelpseg shore-inventory --recipe <inventory.toml>`.

Use one shared distance-bin function (planned `reporting/shore_distance.py`).
Join by explicit original/source identity and grid, never filename guesses.
Produce source × region × split × distance-band CSVs and pooled region/split
summaries, retaining experiment, variant, date and scope. Include:

- Valid labeled pixels, labeled kelp pixels, corresponding area in m²/hectares,
  kelp prevalence within each band, and each band's fraction of all labeled kelp.
- Nearshore kelp amount and fraction, source/date support counts, and missing or
  unknown distance support. Compute physical area using supported metric grids;
  never convert angular pixel sizes directly to square metres.
- Three explicitly named footprints: all valid cleaned labeled source pixels;
  the union of retained selected chip windows per split; and the union of
  training-eligible windows after the actual training exclusions. The third is
  training only. This exposes data available versus data actually offered to
  training. Overlap contributes once in every footprint, including cropped
  pieces of the same original. Do not interpret union area as optimizer exposure
  frequency or invent augmentation/sampling weights.
- Mapped-land labeled kelp and unknown-distance labeled kelp as explicit counts
  and fractions. Keep them visible rather than cleaning labels or masking errors.

Provide normalized distance distributions alongside absolute area, region/split
heatmaps, and cumulative kelp-distance curves. Empty groups remain explicit with
undefined fractions where the denominator is zero. Totals across dates are
observed area summed over acquisitions, not unique regional habitat area.

### 4. Extend the existing validation report

Add optional shoreline references to existing report settings in
`reporting/inputs.py`; integrate shared bin summaries into `reporting/report.py`
and `reporting/views.py`. Reuse `reporting/canvases.py` reconstruction and existing
confusion/score helpers. Do not build a second evaluator or run inference inside
reporting. Existing reports without shoreline settings retain their behavior.

For each source and band, count TP/FP/FN/TN on the existing scoreable footprint,
then pool counts for regional and split metrics. Report kelp precision, recall,
IoU and F1 with labeled/predicted kelp support and coverage; do not reinstate
background-dominated overall pixel accuracy as the primary diagnostic.
Use the saved threshold unchanged, invert padding, honor ignore `-100`/nodata,
average overlapping probabilities before thresholding once, and count each
original-source pixel once. Keep chip-disjoint and full-TIFF scopes separate.

Add a distance section to report HTML with metric-versus-distance plots, support
bars and bounded imagery/shoreline/label/prediction overlays. Land and unknown
categories remain included in reconciliation with original global confusion
counts; an optional ocean-only subtotal must be labeled. Missing expected mask
identities or misaligned grids fail clearly, not silently skip sources.

Generate the label inventory for train/val/test and a distance report for existing
validation predictions. Compare train versus validation label distributions
within each region as well as pooled results. If a saved training prediction
sample exists, label its limited footprint; do not compare its totals to the
entire training inventory as if they were matched. Record whether nearshore kelp
is underrepresented, whether recall/precision deteriorate within comparable
bands, and alternative explanations (region/date mix and shoreline uncertainty).
No causal conclusion or remedial training experiment is required.

## Validation and acceptance

Focused tests are planned in `tests/test_shoreline.py`,
`tests/test_shore_inventory.py`, and `tests/test_shore_distance_report.py`:

1. Analytic straight coast, island union and polygon hole; coast outside TIFF;
   all-land, wholly offshore and unknown coverage cases; metre units, non-square
   pixels, source alignment and bin-edge assignment including exactly 500 m.
2. Hand-counted labels/TP/FP/FN/TN across bins, land and unknown; zero-positive
   bins remain undefined where appropriate; summed counts reproduce the original
   report exactly. Area and normalized distribution denominators are explicit.
3. Overlapping training windows/crops count once; original offsets and padding
   are respected; ignored/uncovered pixels stay excluded; training exclusions
   change only the declared training-eligible footprint. Region/split joins
   reject missing/duplicate identities without changing assignment membership.
4. Report parity with shoreline disabled; saved threshold unchanged; both chip
   and TIFF reports use the same distance semantics. Missing grids and bad recipe
   settings give actionable errors. Ordinary initial overwrite refusal is tested.
5. Small real mainland/island/BC smoke: inspect overlays, confirm raster headers,
   run inventory and existing saved-prediction reporting offline after export,
   and record coverage/uncertainty. No production training or test inference.

Run focused tests, `uv run ruff format --check .`, `uv run ruff check .`, and
`uv run pre-commit run --all-files` for broad code changes. Preserve and identify
preexisting unrelated failures. Add short recipes to quickstart only once the
commands exist, update architecture/artifact contracts if needed, and verify
Markdown links plus `git diff --check`.

Acceptance: a researcher can prepare shoreline rasters with explicit paths,
obtain region/split nearshore label support without predictions, and generate
an augmented validation report from saved predictions. Global counts reconcile,
coverage differences are visible, and the nearshore representation hypothesis
has a bounded evidence-based assessment. No new framework or production retrain.

## Non-goals

Patch matching; revised labels/splits; shoreline ground truth or tidal correction;
marine/inland-water classification; land-based suppression of predictions;
model/loss/threshold selection; new LORO runs; global download infrastructure;
per-epoch shoreline logging; automatic recovery; commits or pushes.

## Planning outcome — 2026-11-06

- Changed repo files: this task contract, `tasks/README.md`, `docs/todo.md`, and
  `docs/index.md`. Preserved existing experiment and code changes in the checkout.
- External evidence: inspected the linked shoreline catalog; no payload exports,
  data writes, model runs, or durable external artifacts.
- Validation: Markdown relative-file-link check and `git diff --check` passed.
  No behavioral tests were needed for this docs-only planning change.
- Follow-up inventory: confirmed the 53 local validation image/label pairs and
  existing chip window fields; added the remaining 316-pair download and explicit
  source-raster-to-chip window mapping. No downloads or payload changes performed.
- Unresolved: actual shoreline export access, remaining cleaned-pair transfer,
  supported source grids and measured shoreline alignment. Initial bands are documented defaults.
- Exact next action: begin stage 1 access/input inventory and inspect shared report
  interfaces, then implement the small synthetic land/distance smoke in stage 2.
  Task 040 is selected ahead of 037; implementation is not yet complete.

## Implementation start — 2026-11-06

All 369 cleaned image/label pairs are local at
`/home/sky/data/data/3_cleaned/ca_bc/v1`; all 747 paths/sizes match Box and all
pair headers align, with three fully decoded sample pairs. Evidence:
`/home/sky/data/analyses/task040_downloads_20261106/verification.json`.
The user supplied three shoreline exports on Box and requested these inputs:
`kelp-box:kelpseg/data/1_raw/shorelines_v1/`. Local copies at the same relative
data path total 2,694,594,560 bytes. SQLite checks and bounded geometry reads
passed; all use EPSG:4326. Counts are 89 mainland records, 21,993 big islands,
and 318,868 small islands. These exported feature counts differ from the catalog
summary; retain the supplied polygons, without claiming identity to its counts.
Mainland GeometryCollections include polygon and line parts: extract polygon
parts and record discarded linework rather than treating lines as land.
Download evidence: `/home/sky/data/analyses/task040_shoreline_download_20261106/verification.json`.

Concrete preparation interface: prediction-style source CSV with source_key,
image, band_names and existing identity columns; settings manifest, image_root,
output, mainlands, big_islands, small_islands, max_distance_m=500. Output CSV
adds land_mask/distance relative paths, width/height/CRS/transform, cap_m and
coverage. Distances use a halo-aware raster Euclidean transform in metre grids
with the pixel-center approximation documented. Shared report/inventory readers
join these rasters using exact source keys and grid offsets. Reporting settings
add optional shoreline and distance_edges. No preparation resume is introduced.

## Outcome — 2026-11-06

Implemented and ran the complete workflow without retraining, changing split
assignments, editing canonical chips, or scoring held-out test predictions.

### Repository changes and usability

- Added `prepare/shoreline.py`, `shore_distance.py`, `shore_preview.py`, the thin
  shoreline CLI and `configs/prepare/shoreline.toml`.
- Added shared `reporting/shore_distance.py`, inventory orchestration/input/count/
  view modules, the inventory CLI and `configs/report/shore_inventory.toml`.
- Integrated optional shoreline settings, counts and plots through existing
  report inputs/orchestration/views, with `shore_report.py` and `shore_views.py`.
  Existing chip/TIFF recipe templates document the optional settings.
- Registered both installed commands; added locked runtime pyogrio, pyproj,
  scipy and shapely dependencies. Added four focused shoreline test modules.
- Updated quickstart, architecture, data-artifact contracts and task routers.
  Routine use needs only explicit paths and recipe settings, with ordinary CSVs,
  progress logs and clear alignment/identity errors. No recovery, receipts,
  framework or chip payload duplication was introduced. No commits or pushes.

The raster method uses north-up metre grids, center-based land rasterization,
polygon holes, a cap-plus-two-pixel halo, and Euclidean center-to-center distance.
The straight-coast fixture documents the half-pixel boundary approximation
(1.5 m on a 3 m grid); shoreline positional uncertainty is larger and is not
corrected using labels. Distances at or beyond 500 m are right-censored. Bins
are 0–30, 30–60, 60–120, 120–250, 250–500 and 500+ m, plus land and unknown.
Chip reports join exact canonical source identities through saved windows and
use original offsets; no per-chip distance transform or resampling occurs.

### Durable local artifacts

All paths below are outside Git, under `/home/sky/data/analyses/`:

- `task040_shoreline_v1/`: 369 source grids, 738 GeoTIFFs, source/settings/count
  metadata and 12 regional alignment previews (about 462 MiB).
- `task040_shore_inventory_v1/report.html`: full-source, selected-chip and
  training-eligible inventories, regional/split CSVs, distributions, cumulative
  curves and nearshore heatmap. All 369 sources: 258 train, 53 val, 58 test.
- `task040_b0_chip_validation_v1/report.html`: current B0 saved chip validation,
  distance curves, regional/source counts and shoreline/label/prediction panels.
- `task040_b3_tiff_validation_v1/report.html`: existing B3 full-TIFF validation
  through the same distance implementation. Different model and footprint;
  these reports are not a matched model comparison.
- `task040_shore_distance_v1_inputs/`: explicit source/label CSVs, all four
  production recipes, logs, `report_verification.json` and
  `shoreline_source_notes.txt` containing attribution and export limitations.
- `task040_shore_smoke_v1/` and `task040_shore_mainland_smoke_v1/`: small real
  island/BC/mainland preparation runs. Overlays and final report panels inspected.

The supplied Box exports are the inputs described in Implementation start.
Attribution: Sayre et al. (2019), DOI 10.1080/1755876X.2018.1529714; catalog
states CC BY-SA 4.0 and 2014 Landsat-derived shoreline. Actual export feature
counts differ from the catalog; exact export history remains unknown. Selected
geometries required no repairs; non-area pieces are recorded and discarded.
New derived analyses remain local; their Box backup has not been verified.
The production v1 source CSV contains this host's absolute image paths. A final
portability fix preserves relative input image paths in future outputs; its
relocated-image-root test passes. Existing scientific rasters were not rewritten.

### Findings

Nearshore means ocean pixels less than 60 m from mapped land. Fractions below
use all labeled kelp, including mapped-land kelp, as the denominator.

- Across all regions, full-source nearshore kelp fractions are 7.06% train,
  8.54% validation and 3.72% test. Observed nearshore areas are respectively
  1,787.10, 206.17 and 253.13 hectares, summed over acquisitions, not unique habitat.
- Restricting to regions 001–010 shared by train and validation reveals a larger
  difference: 4.24% train versus 8.54% validation. Training-only BC support
  otherwise obscures this gap. Selected chips give 4.24% versus 8.45%; applying
  positive-window training exclusions does not remove labeled kelp in this run.
- The difference varies substantially by region. Region 008 has 0.73% nearshore
  train kelp versus 3.09% validation; region 006 has 44.34% versus 55.09%.
  Region 004 goes the other way (23.95% versus 21.21%).
- B0 chip validation ocean recall is 59.01% nearshore versus 82.35% at least
  60 m offshore. Precision is 81.61% versus 83.04%. Missed labeled kelp dominates
  the nearshore gap. Regional effects differ: region 008 nearshore recall is
  10.76%, while regions 004/006 do not have lower nearshore than offshore recall.
- B3 full-TIFF validation independently shows 58.85% nearshore versus 83.35%
  offshore recall, with 81.71% versus 83.93% precision.
- Mapped-land kelp remains explicit: 236.27 ha train, 37.10 ha validation and
  39.66 ha test. It is not suppressed from labels or predictions.

These results support relative nearshore underrepresentation and poorer
nearshore recall, not a causal explanation. Region/date mix, kelp-bed size,
shoreline age/tides/positional error and differing chip coverage remain possible
contributors. No thresholds, splits or models were selected using these results.

### Validation and handoff

- 89 combined focused/regression tests passed across shoreline preparation,
  shared distance, inventory, report integration, existing reporting, temporal
  reporting and CLI. After the final ordinary settings guard, all 11 inventory
  tests passed; after the path portability fix all 9 preparation tests passed.
- Isolated wheel/sdist installation test passed. Ruff formatting/checks and all
  pre-commit hooks passed. Final Markdown links and whitespace checks passed.
- Both production reports exactly reproduce their previous global metrics and
  coverage. Summed distance-band TP/FP/FN/TN equal original global counts.
- Inventory bins reconcile in all 996 source/footprint groups. Full-source
  native-valid pixels total 1,766,250,207, matching cleaned release metadata;
  21,587 valid ignored-label pixels explain the smaller known-label total.
- Small real mainland/island/BC examples and bounded report overlays align
  plausibly. Unknown support is explicit; complete vector coverage is a declared
  input assumption, not proof that every rock or shoreline is mapped correctly.

No implementation blocker remains. Exact next action: write and review a bounded
Task 037 contract for LORO and matching-TIFF comparisons; do not launch it as part
of Task 040. Further causal experiments and backup of new analyses remain separate.

## User-selected nearshore summary update — 2026-11-06

After viewing 30/60/90/120 m contours on a real TIFF and the existing validation
curves, the user requested **ocean distance below 120 m** for the nearshore
summary. This supersedes the initial 60 m definition for new reports; the
original findings above retain their historical definition. This is a descriptive
cutoff selected after inspecting validation, not an independently validated
performance breakpoint or a model threshold change.

A shared cutoff now controls inventory metadata, cumulative support, regional
heatmaps, summary tables, cap validation and validation-overlay selection. The
individual distance bands and all model scores remain unchanged. Quickstart
states the new definition. New outputs use `_120m_v2` names alongside original
reports; shoreline rasters and saved predictions are reused unchanged.

Updated artifacts under `/home/sky/data/analyses/`:

- `task040_shore_inventory_120m_v2/report.html`
- `task040_b0_chip_validation_120m_v2/report.html`
- `task040_b3_tiff_validation_120m_v2/report.html`

Recipes/logs are the `*_120m` files in
`task040_shore_distance_v1_inputs/`. At the new cutoff, full-source shared-region
001–010 nearshore kelp fractions are 12.20% train and 18.86% validation. B0 ocean
recall below/above 120 m is 64.12%/84.14%; precision is 82.63%/83.01%.
The 120 m boundary is exclusive: pixels exactly at 120 m enter the offshore
120–250 m band. Mapped-land and unknown pixels remain separate.

Validation: 39 focused inventory/report tests passed, including the updated
120 m HTML/metadata assertions; the inventory's 11 tests also passed after
adding a hand-counted exact-120 m exclusion check. Ruff formatting/lint and
pre-commit passed. All six regenerated inventory CSVs match the originals
exactly: only summary selection, presentation and metadata changed.

Both regenerated validation reports passed exact global, coverage and distance-band
parity against v1; their HTML and metadata identify 120 m. Evidence is
`task040_shore_distance_v1_inputs/report_verification_120m.json`. All three
production commands completed successfully. Task 040 remains complete; next
roadmap action remains the bounded Task 037 contract, with no training launched.

## Cluster and display follow-up contract — 2026-11-06

The user requested label-cluster membership and the relationship between pixel
shore distance and cluster size, log-scaled imagery, a distance color legend,
yellow shoreline overlays on supplied labels/predictions, and removal of the
absolute-area and cumulative-distance figures from the inventory HTML.

Reuse the existing eight-connected label-patch convention, defining components
on full original-source label canvases before chip selection. Persist source-local
component IDs and component sizes, count pixel-level distance/size associations,
and describe correlations with log cluster area by region/split and pooled.
Keep mapped-land/unknown/capped distances separate and flag observed fragments
at image/nodata boundaries. Contrast pixel weighting with cluster weighting;
do not infer independent observations or causal significance from pixels.
No training or test performance evaluation is authorized by this follow-up.

Keep normalized distance distributions and nearshore support in HTML; detailed
area/cumulative CSVs remain available. Imagery displays use log1p before contrast
stretch, with this user preference applying to future imagery figures too.
Regenerate inventory and both saved-prediction reports into fresh output folders,
verify existing score/count parity, and visually inspect updated examples.

### Follow-up implementation

- `visualization.py` now centralizes display-only log1p plus per-channel 2–98%
  contrast stretching. Shoreline examples, ordinary report examples and shoreline
  preparation previews use it. Image arrays/model inputs remain unchanged.
- Shoreline figures have a metre colorbar and yellow contours on all four panels.
  Inventory HTML retains normalized distributions/nearshore support, omitting
  absolute-area and cumulative plots. Underlying CSVs remain available.
- `shore_clusters.py` defines full-source eight-connected IDs, observed area,
  boundary-fragment flags and distance/size counts. `shore_clusters_summary.py`
  pools counts/moments and plots interior-component size composition by split.
  Inventory integration writes georeferenced uint32 ID TIFFs plus cluster/source,
  distance-size and correlation tables; HTML includes the plot and correlation
  summary with detailed table links. No additional recipe settings are needed.
- Pearson correlations use distance versus log10(full observed component area),
  excluding mapped land, unknown distance and pixels at the censoring cap.
  Pixel weighting repeats component size per pixel; cluster weighting uses each
  supported component's mean uncapped ocean distance once. Both interior-only
  and all-observed scopes are retained. No independent-pixel p-values or causal
  claims are made. Component IDs identify source observations, not temporal beds.

New production destinations under `/home/sky/data/analyses/` are
`task040_shore_inventory_clusters_v3/`,
`task040_b0_chip_validation_clusters_v3/` and
`task040_b3_tiff_validation_clusters_v3/`. Recipes/logs use `*_clusters` in
`task040_shore_distance_v1_inputs/`. Existing reports remain untouched.

The 52 focused cluster/inventory/shoreline/shared-report tests pass, including
hand-counted diagonal connectivity, repeated full-cluster area per pixel,
constant/empty correlation support, pooled moments, nodata/edge fragments,
land/unknown/cap exclusions, and georeferenced ID round-trip. Ruff formatting,
lint and pre-commit pass. Both regenerated prediction reports preserve global
scores, coverage and distance-band counts exactly. A real region-008 four-panel
image was inspected for log display, legend and matching yellow contours.

### Follow-up production outcome

All three commands completed. The label inventory assigned 175,043 observed
clusters across all 369 sources; 1,035 touch unknown support or canvas edges.
All 369 ID rasters exist. Summed component sizes equal the original full-source
labeled-kelp count, and all six preexisting inventory CSVs match v2 byte for byte.
The new report asset links resolve; absolute/cumulative figures are absent from
HTML. The normalized cluster-size plot and updated example panels were inspected.
Evidence: `task040_shore_distance_v1_inputs/cluster_verification.json`.

For interior clusters and uncapped ocean pixels below 500 m, pixel-weighted
Pearson r(distance, log10 cluster area) is 0.242 train, 0.009 validation and
0.194 test. The one-cluster-one-vote correlations are -0.101, -0.026 and -0.004,
respectively. All-observed sensitivity results are similar. This is not a
universal monotonic small-cluster/nearshore relationship: pixel weighting and
regional/split composition matter, and validation has almost no pooled linear
association.

For example, training kelp pixels in clusters of at most 100 pixels account for
8.02% at 0–30 m, 5.90% at 30–60 m, 4.01% at 60–120 m and 3.28% at 120–250 m.
Validation shares are 5.91%, 5.39%, 5.61% and 6.47%; its smallest clusters do not
follow the same nearshore gradient. These examples use interior components,
not biological-bed counts or independent pixel observations. Larger cluster-size
classes and regional tables remain available for nonlinear comparisons.

Usability: no new settings or separate model run; the existing inventory command
now produces the cluster report and reusable ID rasters. Existing report recipes
produce log imagery and fully annotated shore panels. No source labels, training
inputs, assignments or saved predictions changed. New artifacts are local;
Box backup is not verified. No commits or pushes. Task 040 is complete; the exact
next roadmap action remains scoping Task 037, not launching a training experiment.

## Training-window exposure follow-up contract — 2026-11-06

The user requests expected nearshore kelp exposure under the current training
sampler, small-bed exposure nearshore versus offshore, and regional breakdowns
before choosing any sampling multiplier. Inspect the actual training selector,
DataLoader and current B0 run settings. Keep sampling settings unchanged.

The current loader uniformly shuffles eligible positive windows, without
replacement and without dropping the final batch. B0 uses all batches: 8,518
eligible windows out of 18,311 training candidates, 710 batches at batch size 12.
Compute exact nominal full-epoch pixel appearances by summing eligible windows;
overlap counts repeatedly, unlike the existing unique-pixel inventory. Divide
by all eligible windows for expected per-draw exposure; distinguish a region's
contribution to the global sampler from exposure conditional on drawing that
region. Include draw probabilities of encountering kelp in each category.

Use the full-source cluster IDs/sizes, nearshore ocean distance <120 m, offshore
>=120 m including capped distances, and explicit land/unknown categories. Use
<=100 pixels as the descriptive small-cluster summary while retaining all
existing size bins. Include observed boundary fragments in actual training
exposure, separately flagging their contributions. Exclude padding, nodata and
ignored labels. These are preaugmentation counts, not transformed loss pixels,
loss weights or optimizer gradients: affine and dropout can alter support.

Add window-level CSV and regional/global expected-exposure tables/figures to the
inventory report, regenerate into a fresh folder, reconcile against training
selection metadata, and test overlapping-window multiplicity and regional
denominators. No multiplier selection, sampler change or training run.

### Exposure implementation and validation

`shore_exposure.py` counts window appearances using full-source IDs and pools
expected exposure; `shore_exposure_views.py` renders regional charts and tables.
Inventory integration writes `exposure_windows.csv` and `exposure_summary.csv`
before rendering HTML, with sampler/eligibility/stage metadata in summary JSON.
Window rows retain source, region, date, payload and original spatial offsets.
No new settings or sampling framework were introduced; existing positive-window
eligibility remains the explicit setting. All observed fragments contribute,
with their pixel counts reported separately.

Eighteen focused exposure/cluster/inventory tests pass. Fixtures verify repeated
overlap instead of unique coverage, exact 120 m and capped offshore pixels,
full-source size despite small window fragments, training-only eligibility,
zero-support regions, global versus conditional regional denominators, and
land/unknown/ignored/nodata handling. Ruff and pre-commit checks pass. Independent
training selection metadata identifies 8,518 eligible windows and 106,920,715
kelp appearances before augmentation, to reconcile with the production output.

Production destination: `/home/sky/data/analyses/task040_shore_inventory_exposure_v4/`.
Recipe/log: `inventory_exposure.toml` and `inventory_exposure.log` in
`/home/sky/data/analyses/task040_shore_distance_v1_inputs/`. Earlier inventories
and validation reports remain intact; this follow-up changes label-only analysis.

### Exposure production outcome

The v4 inventory completed successfully. Its 8,518 window records and 106,920,715
kelp appearances match the actual training selector metadata exactly. Every
regional count and window-hit total pools back to its global counterpart. All
12 prior inventory/cluster CSVs match v3 exactly; the new report’s assets and
links resolve. The regional exposure figure was visually inspected. Evidence:
`task040_shore_distance_v1_inputs/exposure_verification.json`.

Current sampler expectations before augmentation:

| Category | Pixels per draw | Pixel appearances per epoch | Draw contains category | Share of all kelp exposure |
|---|---:|---:|---:|---:|
| All kelp | 12,552.33 | 106,920,715 | 100% | 100% |
| Nearshore kelp | 1,995.77 | 16,999,964 | 65.03% | 15.90% |
| Small nearshore cluster kelp | 92.76 | 790,128 | 59.11% | 0.739% |
| Small offshore cluster kelp | 326.36 | 2,779,897 | 86.52% | 2.600% |

Nearshore remains ocean distance <120 m; small means full observed component
size <=100 pixels. Nearshore/offshore omit mapped land and unknown, retained as
separate categories. A small cluster can occur frequently across windows yet
supply few pixels, so window-hit probability and pixel exposure are distinct.
These descriptive quantities do not select a sampling multiplier.

Regional examples: 002 receives 28.41% of draws, 008 receives 16.13% and 012
receives 13.85%. Conditional mean nearshore kelp pixels per regional draw are
2,086.3, 426.8 and 4,398.2 respectively. Region 003 receives 2.35% of draws with
no mapped nearshore kelp. Detailed small-cluster and offshore numbers for every
region are in HTML and CSV, including unconditional global contributions.

Task 040 is complete. No sampler, augmentation, loss, threshold, assignments or
predictions changed; no training launched. Artifacts remain local, backup is not
verified, and no commits/pushes were made. The next roadmap action remains a
bounded Task 037 contract, not an experiment inferred from these diagnostics.

## Cluster distribution plot follow-up — 2026-11-06

The user requests a 5,000-pixel cluster boundary and line/scatter presentation
of cluster-size distribution as a function of shore distance. Split the former
>1,000 category into 1,001–5,000 and >5,000 in cluster and exposure outputs;
leave historical evaluator patch bins unchanged. Replace stacked bars with
one marked line per cluster-size category, for each split. Each distance band's
denominator is all its labeled kelp pixels; size-category fractions sum to 100%.
Land/unknown stay in CSVs, while the plot uses ocean distance bands only and
labels 500+ as censored. Preserve the original cluster assignments, correlations,
small-cluster <=100 definition and sampling settings. Regenerate in a fresh
inventory folder and verify old >1,000 counts equal the two new categories.

Implementation uses a separate `CLUSTER_SIZE_BINS` definition shared by cluster
and sampler-exposure analysis; the evaluator’s historical `PATCH_BINS` remain
unchanged. Exposure CSVs split the former over-1,000 fields accordingly. The
small-cluster <=100 summary is unchanged. Lines use categorical ocean-distance
bands with point markers; land/unknown remain available in tables. Empty bands
stay undefined and display N/A, with explicit ticks even when all values are
missing. A small-fixture layout warning during the first plot check was fixed
by setting categorical positions/limits explicitly; the repeated focused suite
passes without warnings (19 tests, including exactly 5,000 versus 5,001 pixels).

Production destination is
`/home/sky/data/analyses/task040_shore_inventory_size5000_v5/`; the recipe/log
are `inventory_size5000.toml` and `inventory_size5000.log` in
`task040_shore_distance_v1_inputs/`. Original ID assignments and full-source
component areas are not changed by the new reporting bins.

### Five-band production outcome

The v5 inventory completed. Existing label inventory, correlation and source
metadata CSVs remain identical. For every source/region/split and component
scope, the new 1,001–5,000 and >5,000 counts sum exactly to the former >1,000
counts. All 8,518 exposure windows reconcile, including truncated exposures;
all other per-window fields remain unchanged. Supported distance-band fractions
sum to one. Evidence: `task040_shore_distance_v1_inputs/size5000_verification.json`.
The final plot was rendered from completed v5 tables using explicit empty-band
axes and visually inspected. Report links resolve. Focused tests (19), Ruff,
pre-commit and whitespace checks pass.

The new plot makes the composition gradient clearer. Interior training kelp
pixels in >5,000-pixel clusters account for 33.4% at 0–30 m, 42.3% at 30–60 m,
58.5% at 60–120 m and 75.4% at 120–250 m. Validation is flatter across those
bands: 41.1%, 48.8%, 49.3% and 51.3%. These are conditional size compositions,
not cluster counts or model accuracy, and do not replace the prior correlation
results. The last distance band remains right-censored.

Task 040 is complete. New outputs remain local; no training, sampling multiplier,
label change, commit or push occurred. Next roadmap action remains scoping Task
037; no further experiment is started by this follow-up.

## Joint B0 recall follow-up contract — 2026-11-06

Question: does nearshore recall remain lower within the same region and
full-source cluster-size class? Use the completed size5000 v5 inventory and B0
clusters v3 validation report specified by the user. Read saved predictions only,
retain threshold 0.5, source reconstruction, unique scored pixels, ignore/nodata
and coverage. Do not recompute component IDs or sizes on validation windows.

Add optional `cluster_inventory` to the existing report recipe, requiring the
shoreline reference and the existing standard distance bands. Read saved cluster IDs by exact
source identity and aligned grids, and inherit full observed component size and
boundary-fragment flags. Report TP/FN, labeled kelp pixels/area and recall for
all five size bins and every distance band, including land and unknown. Provide
all-observed, interior-only and truncated-only counts; fail clearly on missing
IDs/size metadata for scored kelp rather than dropping it silently.

Pool source counts by region/distance/size, retaining source/date support,
largest source/date share and explicit empty groups. Compare <120 versus >=120 m
within region/size; keep land/unknown outside that ocean comparison. Include
paired-source/date evidence and dominant-source sensitivity to distinguish
broad support from a single TIFF. Sparse flags are descriptive, not p-values.
FP/precision remain in region/distance tables, never assigned a true-cluster size.
Reconcile joint all-observed TP/FN with the shoreline and global totals and
account explicitly for boundary exclusions in interior-only summaries.

Implementation stays in small typed joint input/count/summary/view helpers,
with optional integration into `report`; a linked joint HTML report and CSVs
live in a fresh output directory. Focus interpretation on 004/006/007/008,
including region/date composition, sparse classes and noncausal limitations.
Test full-size inheritance despite clipped prediction coverage, alignment,
ignore/nodata/threshold handling, empty groups, exact count reconciliation,
source/date pooling and dominant-source behavior. No training, sampling/split
changes, threshold tuning, test performance or commits.

### Joint implementation and validation

New typed helpers: `shore_joint_inputs.py` (saved inventory/grid joins),
`shore_joint_counts.py` (positive-label strata), `shore_joint_summary.py`
(source/date pooling, matched comparisons and largest-contributor sensitivity),
`shore_joint_reconcile.py` (explicit accounting), and `shore_joint_views.py`
(readable HTML and focused plots). Existing report settings/orchestration/views
and both report templates expose the optional reference. Three focused test
modules cover source/grid inheritance, count invariants, support pooling and
complete report integration. No cluster relabeling or model invocation is added.

The combined focused/regression suite passed 75 tests, including existing
reporting, temporal reporting and CLI tests. After adding explicit full-source
versus report-footprint accounting, the six affected integration/summary tests
also pass. Ruff and pre-commit pass; no unrelated failures. Checks include a
saved 5,000-pixel component with only three scored pixels, exact threshold 0.5,
ignore/nodata/uncovered pixels, missing IDs, integer offsets, empty strata,
source/date deduplication and sensitivity to one dominant acquisition.

The first production pass at `task040_b0_joint_shore_size_v1/` verified exact
B0 global/coverage/source/region/shoreline parity. The final report with added
full-source footprint accounting is generated separately at
`/home/sky/data/analyses/task040_b0_joint_shore_size_v2/` using
`task040_shore_distance_v1_inputs/b0_joint_report_v2.toml`. The original user
inputs remain unchanged. All generated tables, figures and findings remain
outside Git.


### Joint B0 follow-up outcome — 2026-11-06

Final report: `/home/sky/data/analyses/task040_b0_joint_shore_size_v2/joint_report.html`.
The main `report.html` links to it. Joint CSVs include empty strata, area, TP/FN,
recall, source/date support, paired comparisons and dominant-contributor
sensitivity. FP/precision remain separate region/distance summaries.

Interior-only nearshore minus offshore recall (percentage points):

| Region | 1–10 | 11–100 | 101–1,000 | 1,001–5,000 | >5,000 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 004 | +0.7 | -11.6 | -5.9 | +7.3 | -6.6 |
| 006 | +1.5 | -31.8 | -0.5 | +11.9 | +18.2 |
| 007 | +7.4 | -19.9 | -20.6 | +23.2 | undefined |
| 008 | -13.2 | -24.6 | -23.3 | -35.1 | -69.3 |

008 has the clearest persistent deficit across all five size classes; paired
dates support the direction in 7/9, 7/10, 7/10, 7/9 and 4/4 cases respectively.
Removing the largest contributor preserves every negative gap. Its smallest
class has only 169 nearshore pixels. 004 retains selective deficits, including
>5,000 across all four paired dates. 007 retains deficits in 11–100 and
101–1,000; its apparent 1,001–5,000 advantage has 91.2% of offshore support
in one TIFF. Its >5,000 comparison is unsupported. 006 is mixed: the 11–100
deficit occurs on three of four paired dates, but other classes are sensitive
to acquisition balance; its largest class has just two dates and one TIFF
supplies approximately 78–80% of support. These are pixel-weighted descriptive
associations, not causal evidence or independent repeated-pixel significance.

Exact accounting: 2,682,168 full-source valid kelp pixels across 53 matched
sources minus 107,535 outside the existing report label footprint gives
2,574,633 scored kelp pixels. Uncovered available kelp pixels and unassigned
scored cluster IDs are both zero. TP 2,055,350 and FN 519,283 match existing
global and shoreline counts. Excluding 218,918 boundary-truncated pixels leaves
2,355,715 interior pixels; excluding 39,914 interior mapped-land pixels leaves
2,315,801 interior ocean pixels. Unknown distance is explicitly separate with
zero support.

Global/coverage/shoreline summaries match exactly. Source, region and shoreline
CSVs are byte-identical to B0 v3. Evidence under
`/home/sky/data/analyses/task040_shore_distance_v1_inputs/` includes
`b0_joint_verification.json`, `b0_joint_report_v2.toml`,
`b0_joint_report_v2.log`, and the one-off interpretation `b0_joint_findings.py`.
Report links resolve; the gap plot was visually checked. The implementation
and affected docs/templates are listed above. The 75-test regression suite and
six subsequent affected integration/summary tests pass; Ruff, pre-commit and
whitespace checks pass, with no unrelated failures observed.

Artifacts remain local; Box backup is not verified. Original inventory, labels,
predictions and threshold 0.5 are unchanged. No retraining, sampling/split
changes, threshold tuning, test-performance analysis, commits or pushes occurred.
Task 040 is closed. Next action: review the separate Task 041 plan before any
authorized experiment; Task 037 remains the next general roadmap contract to
scope. Neither task is started here.


## Report presentation follow-up — 2026-11-06

User requests essential plots/tables only, with no written analysis, across
the Task 040 reports. Simplify inventory, sampler exposure, B0/B3 validation
and joint recall pages; keep short metric/denominator labels and put detailed
counts/accounting behind disclosures or CSV links. Update generated HTML from
saved results without changing scoring, predictions, cluster sizes or tables.


### Presentation outcome — 2026-11-06

Updated all 15 Task 040 HTML pages in place: five inventory versions, six
B0/B3 validation versions, and two joint-report directories with two pages each.
Existing browser URLs remain valid. Main pages now show essential plots and
compact tables with short definitions; written interpretation is removed.
Joint recall leads with paired nearshore/offshore dots by region and full-source
size class, followed by pixel/date support and largest-TIFF shares. Secondary
counts, acquisition comparisons, boundary comparisons and reconciliation are
collapsed or linked. Inventory and sampler-exposure pages likewise retain
plots and concise denominators; full tables remain downloadable.

Changed renderers: `shore_joint_views.py`, `shore_inventory_views.py`,
`shore_exposure_views.py`, and `views.py`. Regenerated from saved CSV/JSON only;
no scoring, prediction, clustering or training changes. Saved CSVs and summary
JSON remain unchanged. Focused checks: 14 inventory/exposure, 28 validation,
and 6 joint tests passed. The paired-dot chart was visually inspected and its
legend moved outside the data panels. All 15 pages' local links resolve.
Ruff, pre-commit and whitespace checks pass. No commits or pushes.

Latest pages remain `task040_shore_inventory_size5000_v5/report.html`,
`task040_b0_chip_validation_clusters_v3/report.html`,
`task040_b3_tiff_validation_clusters_v3/report.html`, and
`task040_b0_joint_shore_size_v2/joint_report.html` under
`/home/sky/data/analyses/`. Task closed; next action is user review of the
simplified reports. No further experiment is started.


## Final code quality pass — 2026-11-06

Review all Task 040 preparation, inventory, cluster/exposure, joint diagnostics,
report integration, display helpers, settings and tests. Simplify duplicated
work and unnecessary layers, fix demonstrated correctness/readability issues,
and preserve scientific boundaries and concise reports. Validate focused
fixtures and saved-data parity, then close Task 040 for user review/commit.
No commit, training, prediction, split or sampling change is authorized here.


### Final code quality outcome — 2026-11-06

Reviewed Task 040 preparation, CLI wrappers, grid/identity joins, inventory,
clusters, sampler exposure, joint diagnostics, report integration and rendering.
Kept ordinary functions, explicit CSVs and existing scientific checks; added no
framework, recovery machinery or new abstraction layer.

Simplifications:

- One source-window slicing/bounds helper shared by inventory and exposure.
- Cluster-band pooling accumulates integer counts directly; correlation moments
  retain built-in summation to preserve Python 3.12 floating-point results.
- Joint source/date evidence groups once instead of rescanning every table for
  each region/size comparison; size counts use one bincount per distance/scope.
- Land rasterization/distance calculation has one clear return path.
- Shared default distance edges, one canonical canvas normalization per source,
  no unused HTML sweep argument, and no redundant imagery conversion.
- Inventory rendering uses the Figure API without changing global backend state;
  preview rendering no longer installs an unnecessary canvas explicitly.

Fixed two demonstrated issues: preparation previews now honor raster nodata masks
and nonfinite values instead of treating all zero values as nodata; inventories
without training sources no longer link a nonexistent exposure plot. Both have
focused regression coverage. Existing identity/alignment validation, full-source
cluster membership, score masks, threshold and undefined-value semantics remain.

Changed files in this pass: `prepare/shore_distance.py`, `prepare/shore_preview.py`,
`reporting/inputs.py`, `reporting/report.py`, `reporting/views.py`,
`reporting/shore_views.py`, `reporting/shore_inventory_counts.py`,
`reporting/shore_inventory_views.py`, `reporting/shore_exposure.py`,
`reporting/shore_exposure_views.py`, `reporting/shore_clusters_summary.py`,
`reporting/shore_joint_counts.py`, `reporting/shore_joint_summary.py`, focused
shoreline/exposure tests and task/queue records.

Validation:

- Combined Task 040 plus reporting/temporal/CLI regression suite: 114 passed.
- All seven joint aggregates rebuilt from saved B0 rows: 9,450 rows match exactly.
- Inventory composition/correlation repooling: 2,944 saved-v5 rows match exactly.
- Fresh full B0 validation report across all 53 TIFFs, saved predictions only:
  all 25 data CSVs byte-identical to `task040_b0_joint_shore_size_v2`; global
  scores, coverage, threshold 0.5, shoreline bands and joint accounting identical.
  Qualitative examples were disabled for this scoring check; existing user-facing
  reports remain at their current URLs.
- Ruff format/check, pre-commit and whitespace checks pass. No unrelated failures.

External check report: `/home/sky/data/analyses/task040_code_quality_b0_v1/`.
Recipe, log and exact parity evidence are in
`/home/sky/data/analyses/task040_shore_distance_v1_inputs/` as
`b0_code_quality.toml`, `b0_code_quality.log`, and `code_quality_parity.json`.
No input data, predictions, splits, training or sampling changed. No commits or
pushes. The new outputs' Box backup remains unverified.

Task 040 is closed and ready for user review/commit. Exact next action: review
and commit the Task 040 changes; preserve the separate Task 041 planning work.
Task 041 implementation still waits for the user's instruction. Stop here.


### Closure — 2026-11-06

User authorized closure and commit after the quality pass. Task 040 is complete;
its implementation, tests, recipes and documentation are included in the closure
commit. Separate Task 041 planning changes remain outside this commit. Validation
evidence is recorded above. No push or training launch is requested. Next action:
await the user’s instruction for subsequent work.
