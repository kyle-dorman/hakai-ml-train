# One-off researcher status presentation

Status: Closed — November 5, 2026. User accepted closeout; final 27-slide reveal.js deck delivered.
Meeting: November 5, 2026, 1 PM America/Los_Angeles.
Audience: The other two researchers working on the project.
Queue: Independent of the numbered rebuild roadmap. Do not add this task to
`docs/todo.md` or change the active numbered task when working on it.
Prerequisites: Tasks 036 and 036B are complete; their full-TIFF validation and
temporal reports are available and inventoried below.

## Purpose and scope

Create a high-level presentation explaining decisions through the successive
data stages, UCLA GPU setup, old/current model behavior on saved crops,
regional and temporal results, next training experiments, and the cost of a
single historical cloud inference project. Keep the emphasis on scientific
decisions and visible results. Workflows are still evolving; do not present
a finished operating procedure or give a command/configuration walkthrough.

Use the already copied-back current model. Do not wait for a newer checkpoint,
train another model, implement Tasks 036/036B here, or alter scientific settings.
The user authorized subtasks A and B in this execution turn; later subtasks
remain for subsequent step-by-step work. Record each completed subtask and its exact next
action here, without editing the numbered queues.

## Inputs and tooling

- Read `AGENTS.md`, `docs/index.md`, `docs/todo.md`,
  [task conventions](README.md), and this task at each new working window.
- For data slides, read the relevant portions of
  [data artifacts](../docs/data_artifacts.md),
  [cleanup provenance](../docs/cleanup_provenance.md), and
  [Box organization](../docs/box_backup.md).
- For setup/model context, use [GPU setup](../docs/gpu_setup.md),
  [experiments](../docs/experiments.md), and the final relevant outcomes in
  [Task 034](034_gpu_machine_preparation_and_baseline_launch.md).
- Use [Task 036](036_shared_scoring_and_reports.md) and
  [Task 036B](036b_temporal_error_analysis.md) for implemented evaluation and
  temporal analysis; do not invent CLI syntax from their earlier plans.
- Legacy reference: `/Volumes/x10pro/kelpseg/references/legacy_ps8b_v1`.
  Six samples currently contain original eight-band arrays/labels, saved old
  probabilities and masks, and preview panels. See
  [Task 025](025_capture_legacy_reference.md). They are documented as development
  reference examples, not established held-out accuracy evidence.
- Planet grid inputs: `/Volumes/x10pro/download_planet/wgs84_all_geojson`.
- Discover the already copied-back model path and its saved run identity from
  current local artifacts. Record the exact bundle; do not silently substitute
  a different model if multiple copies are ambiguous.
- Use the Presentations skill and JavaScript presentation tooling:
  **reveal.js**, explicitly selected by the user during assembly. Deliver a local
  HTML deck with bundled assets, editable content/tables and speaker notes.
  Do not use python-pptx. Scientific plots and raster comparison panels may be
  generated with ordinary plotting/image tools; keep charts/diagrams editable
  where practical and preserve original imagery.

## Outputs and storage

This Markdown file is the one-off task contract and outcome record. Keep large
inputs, predictions, tables, plots, presentation assets and exports outside Git.
Proposed external root (check initial overwrite refusal before creating it):
`/Volumes/x10pro/kelpseg/analyses/researcher_update_20261105/`.

Use plain files, with these planned groups:

- `inputs.md`: selected model, source paths, report scopes, and key assumptions.
- `comparison/`: `crop_inventory.csv`, current predictions, per-crop confusion
  summaries and rendered comparison panels.
- `regional/` and `temporal/`: selected existing report outputs and plots.
- `cloud/`: agreed `assumptions.md`, grid inventory/coverage summaries,
  workload and cost tables, dated pricing sources, and explanatory plots.
- `presentation/`: working assets and optional requested exports; record the
  live presentation reference here in the task outcome.

Small one-off processing helpers may live with the external artifacts. Reuse
installed package functions first. Do not add a repository scripts directory,
new public CLI, recovery system, hashing machinery, or artifact registry.

## Ordered subtasks

Complete each bounded subtask, record its outputs/checks, then identify the next
one. Independent source reading or visual review may be delegated; keep dependent
data processing sequential. No new production training or bulk Planet download.

### A. Establish inputs and slide storyboard

- Read completed 036/036B outcomes and locate available reports and the copied
  model. Record model identity and evaluation scopes, without changing them.
- Inventory the six legacy examples and join their source identities/windows
  to current assignments. Distinguish legacy and current model exposure where
  known. If held-out status cannot be established, call them reference crops.
- Map each slide to its evidence source, intended visual, and pending work.
- Default to all six crop slides if each is informative; retain one slide per
  included crop rather than compressing comparisons into a montage.

Acceptance: model and crop identities are explicit; a storyboard covers the
agreed sequence below. No unresolved identity ambiguity is hidden.

### B. Prepare data decisions and GPU setup slides

- Explain decisions at four levels: original data/preservation; organization
  and cleanup; chips/spectral inputs; training/evaluation assignments.
- Show how those levels are represented in Box, using a simplified structure
  and a recurring stage diagram. Explain why each decision matters; do not
  show exhaustive paths, commands, or internal bookkeeping.
- GPU slide is a numbered list: access, environment, Box data staging, small
  GPU check, training settings and launch. Lessons are spoken, not slide text.

Acceptance: facts match current owned docs; settled choices and experimental
settings are distinguished; no claim that all workflows are finalized.

### C. Produce matched old/current crop comparisons

- Use saved old-model predictions and original imagery/labels as the reference.
  Run the copied current model on the exact matching footprints using its own
  saved preprocessing and the supported prediction interface.
- Check band selection, dimensions, padding inversion, source windows and valid
  label masks. If cleanup versions differ, reconcile alignment and label scope
  explicitly before computing a comparison; never change original artifacts.
- Compute TP, FN and FP against the same supplied labels and common valid
  support for both models. Keep background subdued and ignored pixels distinct.
  Use documented thresholds; do not tune thresholds from these examples.
- Render one slide-ready panel set per crop: imagery, old-model confusion
  overlay, current-model confusion overlay. Use identical crop extents,
  display stretch, colors and legend across models. Add region/date and one
  concise observation; retain counts as supporting evidence if useful.

Acceptance: verify confusion counts against masks, consistent pixel support,
and spatial alignment; visually inspect every panel at presentation size.
Reference examples do not establish an overall improvement or held-out score.

### D. Prepare regional and temporal findings

- Use completed 036 reports for the selected model to identify stronger and
  weaker regions, with sample/valid-area support visible. Avoid a headline
  overall-metrics slide; use metrics only when they explain regional behavior.
- Use completed 036B outputs for one or two temporal slides immediately after
  the crop comparisons. Distinguish date/season error summaries from supported
  change comparisons on common valid geographic footprints.
- Preserve evaluation split, coverage, date support and label-agreement limits.
  Do not treat unequal footprint or sparse sampling as a biological trend.
- Prepare the next-training slide after temporal analysis: establish baseline,
  without BC, four/three bands, LORO, new regions when data become available.

Acceptance: every plotted result traces to the selected model and report;
observations are supported and uncertainty is visible. Unsupported temporal
claims are omitted rather than filled with hypothetical results.

### E. Define cloud assumptions with the user

Start only after B–D are developed. Present a concise assumption sheet for user
decisions before filling in data volumes or dollar estimates. This checkpoint
is explicitly requested by the user; do not turn elapsed time into agreement.

Fixed scope: a single historical processing project, January 2020–December 2025
(72 months), with scenarios spanning 3–10 complete area coverages per month. There is no ongoing
monthly-operation estimate. Storage duration still needs an explicit choice.

Settle:

- What an image count means: per grid, per region, or total; individual scenes
  versus clipped deliveries/mosaics; candidate versus usable images.
- Which grids/regions are included and how overlapping grids and repeat scenes
  should affect downloads, storage and inference accounting.
- Planet product, band count, resolution, companion assets, clipping and expected
  compression; available sample downloads for measuring bytes.
- Whether Planet access is already covered and any licensing cost boundary.
- Inference model/hardware, batching/tiling, benchmark scope and output formats.
- Imagery/results retention periods, download destination and transfer needs.
- Cloud provider/region and pricing basis; distinguish compute time from storage
  occupancy and any existing institutional resources.

Acceptance: agreed assumptions recorded in plain text, with remaining unknowns
explicit. Do not invent settled values or provision cloud resources.

### F. Estimate historical workload and costs

- Inspect GeoJSON geometry/CRS and inventory grid counts, individual areas and
  union area using appropriate geographic area calculations. A union area does
  not by itself determine downloaded scene volume; apply the agreed accounting.
- Use representative real files or documented product characteristics to
  estimate bytes, with compression/scene-footprint uncertainty explicit.
- Build the agreed image-frequency scenarios across all 72 months. Keep units
  explicit and avoid multiplying spatial coverage or overlap twice.
- Measure bounded inference throughput on agreed representative inputs/hardware,
  or label an unmeasured range clearly. Do not extrapolate Mac CPU timings as
  measured cloud GPU performance. Separate setup/I/O from prediction time.
- Retrieve current official provider prices with date, region and billing units.
  Estimate download coordination/CPU, imagery storage, GPU inference, results
  storage and applicable transfer/request costs. Avoid double counting.
- Model storage GB-months using the agreed retention and staging assumptions;
  include a combined scenario table and sensitivity to the largest unknowns.

Acceptance: calculations reproduce from saved plain inputs/tables; units and
pricing citations are checked; estimates are not represented as quotes or bills.
No real bulk acquisition, paid provisioning or recurring operation is launched.

### G. Assemble and visually review the presentation

Use reveal.js and the active Presentations skill where compatible with this
explicit user-selected format. Do not use Artifact Sessions for the deliverable.
Create the data/results portion before cloud assumptions are resolved if useful;
keep cloud placeholders visible until E–F are complete.

Agreed slide sequence:

1. Optional agenda only; no project-status slide.
2. Four data-stage slides from B, with Box organization integrated.
3. One numbered GPU setup slide.
4. One regional performance slide.
5. One slide per selected crop, emphasizing both models' TP/FN/FP.
6. One or two temporal analysis slides.
7. One training-next-steps slide, preserving the requested experiment order.
8. One conceptual cloud sequence: schedule/search/order → download → imagery
   storage → inference → results storage.
9. Cloud costs step by step: download coordination/compute; imagery storage;
   inference; result storage and total estimate. Show the agreed image-frequency
   scenarios. Do not explain the collaborators' existing office setup.

No closing discussion slide, workflow demo, or ongoing-operation cost section.
Keep titles plain, text sparse, evidence visuals large and sources in notes.
Use a consistent confusion-map legend with accessible color distinctions.

Acceptance: render and inspect every slide; check text clipping, legibility,
crop alignment, legends, units and factual support. Verify editable slide text
and the final presentation opens through the supported viewer. Provide the live
deck link and any requested export, not intermediate files by default.

## User decisions required

- No additional decision is needed to write this task or prepare the agreed
  storyboard/data/results content once execution is requested.
- Ask only if the copied current model cannot be identified unambiguously.
- Cloud assumptions in E must be defined with the user after the earlier
  presentation sections, before cloud numbers are filled in.
- Styling/layout choices may use the presentation skill's defaults; do not add
  a generic approval gate for reversible authoring work.

## Validation and completion

For this task-file change: inspect Markdown, verify relative links, and run
`git diff --check`. Preserve all unrelated working-tree changes; no commit/push.
For later execution: use the per-subtask checks above. If repository code changes
become necessary, separately justify their scope and run the relevant tests and
repository lint checks; this task is not permission to broaden the toolkit.

## Subtask progress

| Subtask | Status | Output / exact next action |
|---|---|---|
| A — Inputs/storyboard | Complete | Verified model/reports; six-row inventory and storyboard saved |
| B — Data/GPU content | Complete | Four data-stage slides and numbered GPU slide drafted |
| C — Crop comparisons | Complete | Six matched panels, saved predictions and checked counts; next D |
| D — Regional/temporal results | Complete | Three verified figures plus four slide drafts; next E |
| E — Cloud assumptions | Complete | All grids; 3–10 area coverages/month; eight-band SR; 3× candidate masks; AWS/GCP |
| F — Workload/cost estimates | Complete | AWS/GCP 3/10 coverage estimates, assumptions, sources and tables saved; next G |
| G — Final presentation | Complete | 24-slide reveal.js deck, bundled ZIP and browser review complete |

## Outcome template

- Completed subtasks and evidence:
- Selected model and crop/evaluation scopes:
- External artifact root and live presentation reference:
- Agreed cloud assumptions and pricing date:
- Validation and visual review:
- Unresolved limitations:
- Exact next action:

Keep detailed outcomes here, outside the numbered task queues.


## A/B outcome — November 5, 2026

Completed input inventory, storyboard and five slide-content drafts. No live
presentation was created; visual assembly remains G. No inference, training,
cloud estimation or numbered-queue edits were performed.

External outputs under
`/Volumes/x10pro/kelpseg/analyses/researcher_update_20261105/`:

- `inputs.md`: exact model/report locations and scientific scope.
- `comparison/crop_inventory.csv`: six crops, original source/window/date,
  historical selection assignment, current assignment and artifact locations.
- `presentation/storyboard.md`: 21 proposed slides including optional agenda,
  six reference comparisons, two temporal slides and staged cloud discussion.
- `presentation/data_gpu_slide_copy.md`: four data-stage slides plus GPU setup,
  with visual directions, speaker notes, Box paths and source references.

Model: `analyses/task035_production_model_v1/model` under the external kelpseg
root, run `planet8-cabc-loss-bce-dice-70ep-20261105T004320758369Z`.
Local model.json exactly matches the supplied full-TIFF report model metadata;
weights.pt exists. Epoch 18 EMA is stored as checkpoint_epoch=17. Existing
reports are in `analyses/full_tiff_bce_dice_validation_20261105/`.
Report identity/scope, support files and regional rows were inspected; prior
validated report arithmetic was not rerun.

The 53 validation TIFFs cover regions 001–010. CA/BC is the collection name;
BC regions 011/012 are training-only. Drafts preserve this distinction.
All six saved reference inputs/labels/probabilities/masks/previews exist.
Joined exact legacy IDs through the cleaned parent sources.csv and then current
baseline/augmented assignments. Five are current training sources; Palos Verdes
2021-04-28 is current test. Historical selection TRAIN/VAL fields do not prove
legacy checkpoint exposure. These are reference examples, not a shared holdout
benchmark. No test raster payload was opened during A/B.

Validation: all six identity joins were unique; required model/report/reference
files exist; selected local and report model metadata agree; storyboard has 21
numbered rows. Source-grounded data/GPU copy reviewed, relative task links and
Markdown whitespace checked. No changes to original data or existing reports.

Unresolved for C: exact old/current pixel/label compatibility and 1024 versus
512 input tiling need checking before comparisons. Label the current-test example
explicitly and do not use it to select model settings. Cloud assumptions remain
intentionally deferred until B–D are developed.

Exact next action: subtask C, generate matched current-model predictions and
one TP/FN/FP comparison slide asset per selected reference crop. Do not begin
cloud estimates or change the selected checkpoint.


## C outcome — November 5, 2026

Generated six matched reference comparison assets under the external presentation
root, `comparison/matched_v1/`. `index.html` displays one panel per crop;
`counts.csv` and `summary.json` retain all counts and coverage. Numbered folders
hold current probability/mask arrays, common support masks, PNG panels and
per-crop summaries. `comparison/build_comparisons.py` records the one-off
producer outside Git. Existing reference files and reports were unchanged.

Used the selected original BCE/Dice epoch-18 EMA bundle on the original saved
crop imagery with installed prediction helpers: CPU float32, 512 windows,
stride 256, minimum valid fraction 0.20, inward-shifted final windows, mean
probabilities before threshold 0.5. No training, threshold selection or broader
inference was performed. Current-test Palos Verdes is explicitly labeled TEST.

Validation: all six original/current source CRS, transforms and dimensions
match. Common valid imagery and 0/1 label values match the current cleaned crops
with zero differing pixels. Old/current scoring uses identical preserved labels
and common valid support. All image-valid pixels were covered. Independent
bincount confusion recount matched all 12 model/crop results. All six PNGs were
visually inspected, including independent review of the first three; no apparent
shifts, clipped text or legend inconsistencies. Task links and diff whitespace
checks passed. No repository implementation changes or commit.

Observations are mixed: dense BC and BC nodata examples have fewer misses;
Big Sur/Refugio trade fewer false positives for more misses; Palos Verdes has
more misses and false positives; both models predict zero kelp in the background
example. The comparison includes different historical/current input canvases and
preprocessing, so it cannot isolate a single training change or establish overall
held-out improvement. See matched_v1/README.md for method and display details.

Exact next action: subtask D, select regional and temporal findings from the
existing full-TIFF reports and prepare those slide drafts plus training next
steps. Cloud assumptions remain deferred until that content is prepared.


## D outcome — November 5, 2026

Prepared regional performance, two temporal findings slides and the requested
training-next-steps slide, preserving their agreed order. No model inference,
report regeneration, cloud estimation or live slide assembly was performed.

External outputs under the existing researcher_update_20261105 root:
- `presentation/results_training_slide_copy.md`: four slide drafts, scientific
  scope, speaker notes, source references and experiment order.
- `presentation/findings_preview.html`: three figures plus training sequence.
- `regional/regional_performance.png` and `.svg`, with `slide_data.csv`.
- `temporal/short_change_error.png` and `.svg`, `long_change_error.png` and
  `.svg`, with `slide_data.csv`.
- `presentation/build_findings.py`: one-off external producer from saved CSVs.
- Updated storyboard marks results/training content ready for assembly.

Findings: 001/002 have about 78% validation IoU; 004/006/007 miss substantial
labeled kelp; 008 has lower precision. Temporal figures show regional median
absolute percentage-change error with defined-pair counts, preserving 36/35
short supported/defined pairs and 26/26 long pairs. Long evidence is concentrated
in 008 (19 pairs); its +2.7-point signed median coexists with 80.1-point median
absolute error. No pooled ecological trend or causal interval effect is claimed.

Validation: regional source counts/confusion/support sum to the report tables;
53 TIFFs total. All regional temporal absolute-error medians recomputed, and
independent review verified all 61 percentage errors from before/after counts
plus signed/absolute regional medians. All three charts visually inspected;
notes disclose differing short/long axis scales, unequal samples, repeated pairs,
zero baseline and uncovered pixels. Relative artifact links and diff whitespace
checked. No repository implementation or numbered queue changes, commit or push.

Exact next action: E, define cloud assumptions with the user before calculating
volume or costs for the single 2020–2025 historical processing project. Final
JavaScript slide assembly remains G; the four content drafts and assets are ready.


## E outcome — November 5, 2026

User settled cloud assumptions after the data/results drafts. Saved the full
agreement to the external root's `cloud/assumptions.md`, with a plain GeoJSON
file/feature inventory in `cloud/inventory.json`. Every grid is included using
summed per-grid coverage, preserving current download practice even if overlap
is found. Frequency is complete area coverage 3–10 times/month, not scenes.
Use 3 m pixels, eight-band surface reflectance and quality masks for 3× selected
coverage (not 3× imagery bytes). Retain all downloads and all three result types;
quote storage per month, separately from one-time compute. Compare AWS/GCP;
slow processing is acceptable. Planet licensing excluded. Box results export
is an optional scenario with cloud transfer costs, not assumed free storage
movement. No dollar estimates or bulk transfers performed in E.

Exact next action: F, calculate area-equivalent workload and storage, qualify
compression/acquisition/throughput assumptions, and obtain official provider
pricing. No additional scope decision is needed to begin the estimate. Do not
interpret monthly storage charges as recurring acquisition/inference costs.


## F outcome — November 5, 2026

Estimated AWS us-east-1 and GCP us-central1 costs for 3 and 10 complete monthly
coverages across 2020–2025. External `cloud/` outputs: `cost_estimate.md`,
`cost_estimates.csv`, `cost_estimates.json`, `calculate_costs.py`,
`pricing_sources.md`, `grid_areas.csv`, `geometry_summary.json` and extracted AWS
rate evidence. No paid resources, inference, downloads or Box writes launched.

All 170 polygons valid. EPSG:6933 equal-area sum is 9,077.641 km²; union is
9,018.160 km², a 0.66% overlap. Preserved summed per-grid accounting as agreed.
3 m resolution gives 1.008627 billion pixels/coverage; 216/720 coverages.

Main storage scenario uses eight-band uint16 SR at 65% raw bytes and eight-band
uint8 quality masks at 3% raw, with 3× candidate coverage. Those compression
factors are extrapolated from four small real one-site clips, not archive-wide
measurements. Results conservatively retain raw float32 probabilities and uint8
masks plus a small summary allowance. Total 3.51/11.71 decimal TB. Raw-byte
sensitivity is 9.81/32.68 TB; not an upper bound on scene delivery overhead.

Public rates verified from official provider sources. Main estimate:
- AWS one-time processing $77–335 / $257–1,116; storage $75 / $251 per month.
- GCP one-time processing $79–342 / $262–1,141; storage $65 / $218 per month.
- Raw-byte storage sensitivity: AWS $210/$700, GCP $183/$609 per month.
- Optional results-only Box egress before free tiers: AWS $91/$305, GCP $122/$406.

Runtime uses an explicitly unmeasured T4 sensitivity range (2–10 512-pixel
windows/sec, 256 stride, 25% overhead), not a cloud benchmark. Download/filter
CPU time uses 50–200 Mbps effective throughput plus 25%; request/IP allowances
are explicit. Storage while processing and post-run retention are separate from
one-time compute. No all-in lifetime total is asserted. Same-region services,
no paid NAT gateway, no institutional/Spot/commitment discounts assumed.

Validation: independent official AWS/GCP rate lookup and Planet format review;
regional files/geometry checked; result sizes inspected without raster inference;
all scenario values scale by 10/3 and itemized processing costs sum correctly.
Relative output links and Markdown whitespace checked. One missing optional
pyproj dependency was avoided by using installed Rasterio transforms to EPSG:6933;
no environment modification. Detailed assumptions and source URLs are in report.

Exact next action: G, assemble the agreed content and figures into the editable
JavaScript presentation, incorporating the stepwise cloud table and its explicit
compression/runtime assumptions. A T4 benchmark would narrow costs but no cloud
provisioning is authorized by this estimate.


## Compression refinement and G outcome — November 5, 2026

User explicitly selected reveal.js, overriding the earlier Artifact Sessions
plan. Final deliverable: external presentation/reveal_deck/index.html, with local
reveal.js 6.0.2, assets, CSS, editable HTML tables/text and per-slide speaker notes.
Portable bundle: presentation/kelp_researcher_update_reveal.zip. Builder:
presentation/build_reveal.mjs. Local preview: http://127.0.0.1:8879/ while the
server runs; README explains reopening and speaker view. No remote publishing.
An empty Spaces presentation was created before the format correction, but was
not populated or used as the deliverable.

Compression update: measured 106 files from 53 existing prediction pairs.
Entire compressed file bytes divided by predicted-valid pixels, not canvas
pixels. Rounded above observed per-source maxima to 3.85 bytes/valid pixel for
probabilities and 0.065 for masks; apply to every future pixel as valid. This
removes the approximately 41% nodata area discount. Updated cloud estimate,
JSON/CSV, producer and new compression_evidence.md/csv and compression_summary.json.
No new inference. Outputs are compressed GeoTIFFs; COG layout and extra overview
pyramids were not assumed or verified. Conservative for observed data, not a
universal upper bound for other imagery.

Results are now 0.854/2.847 decimal TB for 3/10 coverages per month. Total archive
3.277/10.922 TB. Monthly total storage: AWS $70.19/$233.96, GCP $61.03/$203.44.
Results-only Box egress before free tiers: AWS $71.58/$238.61, GCP $95.44/$318.14.
Input and compute assumptions unchanged. Raw-byte sensitivity preserved.

Deck contains 24 slides: agenda, four data decisions, GPU setup, regional results,
six crop comparisons, two temporal analyses, training sequence, cloud concept,
workload, download costs, input storage, GPU costs, results retention, project
cost summary and optional Box export. No closing discussion slide or workflow
demo. Expanded cloud section gives workload, total and Box option adequate room.

Validation: all 24 slides rendered in headless Chromium. All assets load, no
JavaScript errors, arrow navigation works, no detected off-slide text/tables/images.
All slides reviewed in overview; results/crops and key text/cost slides inspected
at full size, with independent visual review. Fixed image CSS specificity overflow
and clarified table headers to explicitly say 3/month and 10/month. Final check
passes after fixes. Relative assets and task links checked; git diff --check passes.
The originally attempted local port was occupied, so preview uses 8879 without
changing the other server. No repo code changes, numbered-queue edits or commit.

Exact next action: user reviews/presents the reveal.js deck. Task complete;
future edits can target its HTML/CSS or rebuild from the recorded JavaScript.


## Presentation review — source data and Box

Updated slide 2 to name Taylor and Kate as ZIP delivery sources, with a two-column
introduction to original data and UCLA Box. Linked the Box project and explained
stage folders and local/GPU downloads. Slides 3–5 now explain the purpose of their
Box folders in plain language. No attribution of individual archives to a person
was inferred. Updated builder, content draft, HTML and portable ZIP. Browser checks
pass; slide 2 visually inspected. Next: continue user-led slide-by-slide edits.


## Presentation review — combined preparation slide

Combined raw, organized and cleaned into slide 2 with the UCLA Box introduction.
Retained Taylor/Kate attribution, preservation, naming/identity and cleanup
decisions. Removed the separate organization/cleanup slide; deck now23 slides.
Builder, HTML and ZIP updated. Browser checks and visual inspection pass.
Next: continue user-led review of chips and assignment slides.


## Presentation review — cleaned data and chips

Slide2 now covers raw/organized data and Box. Slide3 combines cleanup with
chips; chips text is only “512-pixel crops with overlap for training.” Removed
the spectral/background/eligibility bullets from that slide. Builder, HTML and
ZIP updated;23 slides remain. Browser checks and slide3 visual review pass.


## Presentation review — temporal split explanation

Slide4 now explains temporal splitting and choosing direction using kelp support
and available dates. Removed source-TIFF and matching-assignments bullets. Retained
spacecraft/day grouping and BC training-only. Footer specifies reverse001–008,
forward009/010. Checked original approved decision in tasks/history/032_split_planning.md:
kelp counts/fractions, dates/source counts and cross-region spacecraft/day conflicts
all informed choices, before model evaluation. Notes explain this nuance. Rebuilt
HTML/ZIP; browser and slide4 visual checks pass.


## Presentation review — explicit cleanup rules

Slide3 now specifies all-band image nodata0, label/image grid alignment, binary
kelp1/other valid classes0 and ignored nodata/unannotated pixels. Notes distinguish
cleaned TIFF ignore3 from chip target-100 and explain binary mapping occurs during
chipping. Chip description unchanged. Builder/HTML/ZIP updated; browser and visual
checks pass.


## Presentation review — train/validation IoU

Added slide6 before regional results: current epoch18 EMA sampled unaugmented
training IoU78.9902% in001–010 versus chip-validation68.9803%, gap10.0099pp.
Source Task034 recorded diagnostic. Notes preserve different dates/composition
and chip/full-TIFF scope. Wording “suggests overfitting,” not causal proof.
Legacy checkpoint confirms val/iou_epoch0.7047 but no matching training metric;
asked user for Taylor curve/metrics and did not assert Taylor overfitting.
24-slide HTML/ZIP rebuilt; browser and visual checks pass.

## Presentation review — Taylor training curve

User supplied W&B run `gfm8o72k` (`hakai-match-v0`); retrieved history through
the authenticated W&B read API. Saved history in external presentation folder
as `taylor_run_gfm8o72k.json` and figure `taylor_iou.svg`. Slide 6 now shows
current clean train/validation IoU 79.0%/69.0% beside Taylor's training and
validation curves. Training curve averages seven logged values per epoch; it
is not an epoch confusion-count aggregate. Validation peaks at 74.447% at
epoch 66 and ends at 74.398% at epoch 96. Training continues improving while
validation plateaus, supporting an overfitting concern. Different evaluation
methods are noted; this is not a controlled comparison of model scores.
This run is distinct from legacy crop checkpoint run `f0d6d24d`.
Rebuilt the 24-slide reveal deck and ZIP. Next: continue user-directed edits.

## Presentation review — both run curves

Replaced the clean-evaluation table on slide 6 with the user's supplied
current BCE/Dice run curves, retrieved from W&B. Plot uses epoch train/iou
and val/iou for all 70 epochs, displayed one-based. Validation peaks at
epoch 18 (68.9859%); final train/validation values are 84.1338%/68.2278%.
Marked selected epoch 18. Taylor curve remains alongside it. Both show
signs of overfitting; differing training metric logging is noted. Saved
current_run_history.json and current_iou.svg externally; rebuilt HTML/ZIP.
Next action: continue user-directed slide review.

## Presentation review — temporal transitions and scatter plots

Replaced the two temporal error-bar figures with three slides (14–16):
a region002 March19→25 example crop showing persistent kelp/loss/gain for
labels and predictions, followed by percentage and signed net-pixel-change
scatter plots. Each scatter has short/long panels, labeled x versus predicted
y, region colors/shapes and an agreement diagonal. Percent includes35/26
defined pairs; pixels36/26 supported pairs. Percent axes compress values
outside ±100% using symmetric log; no outliers removed. Pixel axes are linear.
Net change means gain minus loss, not gross changed pixels. Same common valid
footprint applies within each pair; footprints differ between pairs.
The example is explicitly a768-square illustrative crop; its counts are not
the full-pair scatter values. Shared report alignment/support functions were
reused and full-pair counts checked against pairs.csv. No inference rerun.
External temporal outputs: transition_example.svg/png/json and generator;
scatter_percent.svg/png, scatter_pixels.svg/png and build_change_scatter.py.
Rebuilt25-slide reveal deck and ZIP; all-slide browser checks and visual
inspection completed. Next: continue user-directed presentation review.

## Presentation review — four-panel temporal example

Slide14 now shows before imagery, after imagery, labeled transitions and
predicted transitions side by side. All four use the identical registered
768-square crop; original before/after TIFF windows follow shared pair
alignment. Imagery uses NIR/red/green with a shared per-band2nd–98th percentile
stretch across both dates, recorded in transition_example.json. Transition
counts are unchanged. Rebuilt25-slide deck/ZIP; browser checks and visual
inspection pass. Next: continue user-directed review.

## Presentation review — log imagery display

Updated slide14 before/after imagery display to clip values to[0,2000],
apply log1p (defined at zero), and divide by log1p(2000) for fixed0–1
scaling shared across both dates/channels. Replaces percentile stretch.
Saved display rule in transition_example.json and generator. Source imagery
and transition counts unchanged. Rebuilt deck/ZIP and checked25-slide layout.
Next: continue user-directed slide review.

## Presentation review — percentage comparison retained

User preferred percentage change for comparison. Removed the net-pixel scatter
slide from the main deck; external figure remains available. Temporal section
now contains the four-panel example (with counts) followed by the percentage
scatter. Training next steps follows immediately. Rebuilt24-slide deck/ZIP.
Next: continue user-directed review.

## Presentation review — L4 and retention labels

Switched GPU pricing to AWSg6.xlarge L4 at$0.8048/hour and
GCPg2-standard-4 L4 at$0.706832276/hour, verified official price sources.
Retained unmeasured2–10tiles/sec assumption, no assumed L4 speedup.
Updated calculator, CSV/JSON, cost report, pricing notes, slides and ZIP.
Processing totals at3/10coverages per month: AWS$109–496/$365–1652;
GCP$98–439/$326–1462. Storage/Box export unchanged. Renamed storage rows
Predictions+summaries and Inputs+results; footer defines input imagery/quality
masks and result probabilities/binary masks/summaries.24-slide browser checks
and visual inspection pass. Next: continue user-directed review.

## Presentation review — AWS only

Simplified all cloud slides/tables and speaker notes to AWS us-east-1.
Retained3/10coverage scenarios and L4 pricing/throughput assumption.
Clarified CPU download/filtering title. Underlying two-provider calculation
evidence remains available externally; presentation includes AWS only.
Rebuilt24-slide deck and ZIP; browser checks pass. Next: user-directed review.

## Presentation review — cost summary copy

Removed the three explanatory bullets from the project cost summary at user
request. Cost table and pricing footer remain. Rebuilt HTML and ZIP.
Next: continue user-directed review.

## Presentation review — workload years

Added2020–2025 to Historical workload slide title. User requested skipping
the scheduling-service addition; no scheduling slide added. Rebuilt HTML/ZIP.
Next: continue user-directed review.

## Presentation review — worst regional validation TIFFs

Added three slides14–16 directly after old/current reference comparisons,
ordered006,007,004. Selection is lowest defined full-TIFF validation IoU
per requested region:006_20211011_175154_2442 (9.5%),
007_20210417_184830_2412 (49.7%),004_20210525_174950_2463 (57.2%).
Excluded undefined-IoU006_20210802_175055_2460 (no labeled/predicted kelp).
Each panel shows full-TIFF context and marked detail imagery/error maps;
metrics remain full-TIFF. NIR/red/green display uses clip2000/log1p/0–1.
Reused saved epoch18 EMA probabilities, threshold0.5; confusion/support
counts exactly match report. No inference rerun. External evidence and
figures: comparison/worst_validation/selection.json,build_panels.py,
region_006/007/004.svg/png. Rebuilt27-slide HTML/ZIP; browser checks and
visual inspection pass. Next: continue user-directed review.

## Presentation review — nodata-excluded display scaling

Replaced fixed log1p2000 normalization in worst-TIFF and temporal example
imagery with per-channel valid-pixel min/max normalization after clip2000
and log1p. Nodata does not contribute to scaling; it is colored separately.
Full/detail share source-wide bounds; temporal pair shares pooled bounds.
Bounds recorded in figure JSON evidence. Original image data and model
results remain unchanged. Rebuilt27-slide deck/ZIP; browser checks and
visual inspection pass. Next: continue user-directed review.

## Report review — patch-size recall

User confirmed existing pixel_recall field answers the question and requested
no change. Reverted the brief percentage-formatting edit in report HTML and
reporting/views.py. Existing decimal display and metrics remain unchanged.

## Final closeout — November 5, 2026

Closed at the user's request. The final deliverable is a 27-slide reveal.js
presentation with bundled assets and an editable JavaScript builder. It covers
data decisions, GPU setup, both training curves, regional performance, six
old/current comparisons, three low-IoU validation examples, temporal change,
training next steps, and AWS-only historical processing costs using L4.

Final external artifacts remain under
`/Volumes/x10pro/kelpseg/analyses/researcher_update_20261105/`:

- `presentation/reveal_deck/index.html`: final deck with speaker notes.
- `presentation/build_reveal.mjs`: editable presentation source.
- `presentation/kelp_researcher_update_reveal.zip`: matching portable deck.
- `presentation/qa/checks.json`: 27 slides, no browser/image/layout errors.
- `comparison/`, `regional/`, `temporal/`, and `cloud/`: supporting evidence.

The requested coastline exploration was backed out completely: its generated
folder was deleted, and no coastline content entered the deck or original
report. The patch-recall formatting experiment was also reverted. No package
code changes remain. The numbered task queue is unchanged.

Validation: browser navigation, asset loading and layout checks passed;
scientific figures were visually inspected; final ZIP HTML matches the deck;
local documentation links and `git diff --check` were checked at closeout.
Cloud throughput remains an explicitly unmeasured planning assumption.

Repository change: this one-off task record only. Large presentation assets,
source histories and scientific outputs remain outside Git per project policy.
No further work is pending on this one-off task; reopen only for a new request.
