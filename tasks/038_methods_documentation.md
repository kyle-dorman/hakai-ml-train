# Task 038: Write the current methods document

Status: Complete. Task 037E documentation cleanup is committed as `79de12f`.
This task replaces the old 038 new-region roadmap number; that work is now 039.

## Abstract

Write a researcher-readable methods description of the implemented segmentation
workflow, separate from operating instructions and historical experiment logs.
Consolidate the scientific rules needed to understand splitting, preprocessing,
training/evaluation scope and source-level predictions. Task creation does not
start writing the methods document.

## Inputs and expected output

Read the standard entry documents and docs/documentation.md, then the completed
037E outcome and its current document map. Consult current architecture,
experiment, preparation and prediction/reporting references, implementation and
focused correctness tests. Historical tasks are evidence when needed, not the
structure for the new prose.

Planned output: `docs/methods.md`, with short links from architecture, product,
experiment and researcher guides. Update docs/index.md and documentation
ownership when the document exists. No CLI or implementation changes.

## User decisions required

None for this scope:

- Explain source/date/physical-spacecraft split isolation and evaluation scopes.
- Explain nodata, ignore labels, padding inversion, overlap reconstruction and
  coverage accounting as implemented.
- Explain outside-label coverage as handled, not unresolved: paired imagery
  nodata zero, stored label ignore 3, loader/training/scoring ignore -100.
  Label-free prediction remains independent of label coverage.
- Leave LORO normalization provenance and the completed-study claim qualification
  in Task 037/the LORO write-up; link if discussing that specific study. Describe
  current normalization use without retelling its selection history.
- Do not introduce band-identity uncertainty or delivery-completeness caveats.
  Normal declared band selection/order is still a method, not an open question.

## Plan and implementation contract

Before drafting, write a short outline and map each methodological claim to its
current implementation/test/reference. Use plain scientific language, not task
numbers or a file-by-file code tour. Cover:

1. Inputs, declared band selection, source/window identity and preparation/chips.
2. Partitioning: no source TIFF split across partitions; temporal/date grouping;
   one physical spacecraft on a UTC date kept in one partition; whole-region
   holdouts and documented companion exclusions. Distinguish current baseline
   operation from archived LORO study orchestration.
3. Image nodata, label ignore mapping and coverage; background-only canonical
   chips versus training eligibility; padded pixels and true source footprints.
4. Model inputs and selected/current versus generic-default configuration,
   augmentation, normalization application, training and validation-only model
   selection. Explain checkpoints/EMA only to the extent needed for reproducibility.
5. Label-independent tiled inference; remove loading padding, reconstruct source
   probabilities over overlap, threshold once, and count each covered source pixel
   once. Keep disjoint chip evaluation and tiled-source scopes distinguishable.
6. Pooled confusion-based metrics, explicit ignored/uncovered support, temporal
   common-footprint comparisons and claims of agreement with supplied labels.
   Include optional diagnostics only where they clarify interpretation.

Move duplicated detailed scientific explanations to this owner after verifying
that guides retain the operational instructions and short cautions they need.
Preserve historical evidence and the exact scientific behavior. Stop if drafting
reveals a real implementation inconsistency requiring a separate scoped fix;
do not silently alter scientific policy.

## Validation and acceptance

Methods agree with current functions, settings and focused correctness tests.
Audit assertions about partitioning, label mapping, padding, overlap and pooled
counts against those sources; cite repository references where useful. Distinguish
supported behavior from study-specific choices and planned new-region work.
Check Markdown targets/anchors and run
`uv run --frozen pytest -q tests/test_repository_hygiene.py` plus
`git diff --check`. Run a focused existing test only if needed to resolve a factual
question; no new experiments or production workloads are required.

## Non-goals and handoff

No new methods, code/config changes, altered normalization, reanalysis, new-region
implementation, production training, artifact writes, publication or messages.
No commit or push unless separately requested. Record document changes,
claim/reference checks, validation and unresolved issues in the outcome.
Exact next action after completion: select and bound Task 039 new-region recipes;
Task 042 remains the final researcher handoff. Neither starts here.

## Outline and claim map — recorded before drafting

Entry inspection found a clean working tree. Read the 037E outcome, review and
commit handoff. Scope is Markdown only; preserve operating recipes and history.
The narrative follows inputs/validity, partitions, chip scope, model inputs,
fitting/selection, source reconstruction, then metrics/temporal interpretation.

| Claim / planned section | Implementation and settings | Tests and references |
|---|---|---|
| Identity, cleaning, outside-label exclusion and stored classes | `prepare/clean.py`, `prepare/alignment.py`, `prepare/chip.py`; clean/chip Planet8 recipes | `test_clean.py`, `test_prepare_alignment.py`, `test_chip.py`; preparation guide |
| Source/date/spacecraft isolation, temporal direction and LORO companions | `prepare/split_inputs.py`, `prepare/splits.py`; `configs/split/ca_bc_v1.toml` | `test_splits.py` cutoffs, groups, companions and crops; Task 037 owns archived orchestration/claims |
| Canonical backgrounds, eligibility and disjoint coverage | `prepare/chip.py`, `prepare/splits.py`, `training/data.py` | `test_splits.py`, `test_training_data.py`; preparation/training guides |
| Ordered bands, native validity and padding inversion | `bands.py`, `chips.py`, `preprocessing.py`, `model_bundle.py` | `test_chip_loading.py`, `test_model_bundle.py`; prediction guide |
| Augmentation and fixed normalization | `augmentations.py`, `training/transforms.py`, `preprocessing.py`; `configs/augment/baseline.json` | `test_augmentation_pipeline.py`, `test_pipeline_geometry.py`, `test_training_data.py`; diagnostic guide |
| Selected B0 versus defaults, fitting, EMA and validation selection | `models.py`, `training/settings.py`, `training/loss.py`, `training/module.py`, `training/run.py`, `training/ema.py`; `configs/train/model_size/b0.toml` | `test_training_loop.py`, `test_training_model.py`, `test_training_objective.py`, `test_model_bundle.py`; experiments |
| Image-only tiling, sparse coverage and probability averaging | `prediction/windows.py`, `prediction/predict.py`, `model_bundle.py`; `configs/predict/example.toml` | `test_prediction.py` geometry, averaging, neighbor recovery and padding; prediction guide |
| Original-source assembly, ignored support and pooled confusion | `reporting/canvases.py`, `reporting/inputs.py`, `reporting/metrics.py`, `reporting/report.py` | `test_reporting.py`, `test_validation_report.py`; reporting guide |
| Temporal common-footprint change and qualifications | `reporting/temporal_pairs.py`, `reporting/temporal_inputs.py`, `reporting/temporal_summary.py`; `configs/report/temporal.toml` | `test_temporal_pairs.py`, `test_temporal_summary.py`, `test_temporal_report.py`; diagnostics guide |

Implementation paths are under `src/kelpseg/`; tests are under `tests/`.
Consolidate detailed scientific prose from architecture and experiments into
methods; retain technical/identity contracts and commands. Link product and
guides, preserving operating warnings and historical evidence. LORO normalization
provenance remains in Task 037. No experiment is needed for these behavior claims.

## Outcome — 2026-11-12

Completed only 038 from clean commit `79de12f`. Changes are documentation-only
and remain uncommitted for review. No code, configuration, normalization, data,
model, report or durable external artifact changed; no experiment, transfer or
message was launched. Tasks 039 and 042 remain unstarted.

### Documents and preserved ownership

- Added `docs/methods.md`, following the outline and evidence map above. It covers
  identity and source/date/physical-spacecraft isolation, LORO companions, nodata
  and outside-label exclusion, canonical backgrounds and training eligibility,
  band order/augmentation/fixed normalization, selected B0 versus defaults,
  validation-only selection/EMA, padding inversion, label-independent tiling,
  two-level probability reconstruction, pooled metrics, coverage and temporal
  common-footprint interpretation.
- Consolidated detailed partitioning, selection, reconstruction and temporal
  prose from `docs/architecture.md` and `docs/experiments.md` into methods.
  Architecture retains technical boundaries; experiments retains selected-model
  recovery, tracking, checkpoint and comparison policy. Operating commands,
  schemas, resume instructions and historical evidence remain in their owners.
- Updated `docs/index.md`, `docs/documentation.md`, `docs/product.md` and all four
  `docs/guides/` pages with methods navigation/ownership. Updated `docs/todo.md`,
  `tasks/README.md` and this record for closure. AGENTS.md needed no change.
- LORO normalization provenance and completed-study qualifications remain in
  Task 037/the write-up. No dismissed audit question was reopened.

### Claim audit and validation

Reviewed the mapped implementation, selected settings and existing test assertions.
In particular, checked cross-region spacecraft/day rejection and LORO companion
exclusion; native validity before band selection; stored zero background and
3→-100 mapping; training-only background exclusion; true-size padding inversion;
skipped-window neighbor recovery; average-before-threshold reconstruction and
crop deduplication; pooled confusion ratios; and common-footprint percentages.

The narrative explicitly distinguishes training's zero convention for undefined
ratios from reports' undefined values, microbatch loss pooling from gradient
accumulation, and crop-probability assembly from tile-probability averaging.
Selected epoch-16 EMA identity is supported by the existing experiment record;
this task does not claim to have rerun or independently reselected that model.
No implementation inconsistency requiring a separately scoped fix was found.

- `uv run --frozen pytest -q tests/test_repository_hygiene.py`: **18 passed**.
- Relative Markdown file/heading links checked across repository documentation
  and task records; no missing targets. External artifact/link availability was
  not audited or changed.
- `git diff --check`: passed. Reviewed Markdown and the consolidation diff;
  changed files are Markdown only. Existing behavioral tests were inspected as
  evidence, not rerun; no full ML suite or experiment was needed for this task.

### Remaining issues and exact next action

No unresolved methods question blocks completion. Earlier external backup
follow-ups remain with their existing owners; no new verification is claimed.
Review the uncommitted 038 documentation. Then select and bound Task 039
new-region recipes in a separate task window. Keep Task 042 for the final
researcher handoff; neither task starts here.

## Review follow-up — 2026-11-12

Reviewed the uncommitted 038 changes at the user's request, preserving the
existing documentation work. Rechecked methodological statements against current
source, selected settings and focused test assertions; reviewed the consolidation
diff for lost operating instructions or comparison controls.

Fixed these documentation issues:

- **Coverage scope:** chip reports know imagery validity only in retained windows
  and report gaps within their saved bounding canvas. Zero uncovered-valid pixels
  does not establish full-original coverage. Methods and the reporting guide now
  distinguish these counts from selector logs covering the input footprint and
  omitted edges. Evidence: `prediction/chips.py`, `reporting/inputs.py`,
  `reporting/report.py`, `test_chip_prediction.py` and `test_splits.py`.
- **Partition exclusions:** clarified that region/date and spacecraft/day groups
  cannot contribute to different train/validation/test partitions; explicit unused
  observations contribute to none. This avoids implying excluded LORO companions
  enter the held-out partition. Evidence: `prepare/splits.py` and `test_splits.py`.
- **Inputs and statistics:** explained that spatial augmentation moves loading
  padding with its validity mask. Statistics default to all training chips and
  no cap; optional kelp-positive selection still includes all native-valid pixels
  in those chips. Evidence: `training/data.py`, `prepare/channel_stats.py`,
  `test_training_data.py` and `test_channel_stats.py`.
- **Fitting and comparisons:** documented ordinary shuffled full-epoch sampling,
  expanded BCE/IoU/D4 terminology, and restored explicit matching of band recipe,
  initialization, selection policy and coverage for with/without-BC comparisons.
  Evidence: `training/run.py`, the selected B0 recipe and the prior experiment
  contract. Moved the product methods pointer into its relevant section.
- **Temporal language:** distinguished signed pixel/area changes and errors from
  absolute-error summaries. Explicit pairs outside configured intervals remain
  unavailable; they do not override interval settings. Evidence:
  `reporting/temporal_inputs.py`, `reporting/temporal_pairs.py` and their tests.

Review edits affect `docs/methods.md`, `docs/experiments.md`,
`docs/guides/prediction_reporting.md`, `docs/product.md`, the queue and this record.
Implementation paths above are under `src/kelpseg/`, tests under `tests/`.
No implementation inconsistency was found requiring behavior changes. All earlier
scope decisions and historical evidence remain intact.

Validation: **169 tests passed** using `uv run --frozen pytest -q` on
`tests/test_splits.py`, `tests/test_reporting.py`, `tests/test_temporal_pairs.py`,
`tests/test_temporal_report.py`, `tests/test_channel_stats.py`,
`tests/test_chip_loading.py` and `tests/test_repository_hygiene.py`.
These bounded fixtures resolve the reviewed behavior questions; no production
training/inference, external-data changes or experiment was run. Relative Markdown
file/heading links and `git diff --check` pass. No unresolved review finding remains.

All changes remain Markdown-only and uncommitted. Task 038 and its review are
complete. The next action remains user review, then separately select and bound
039; neither 039 nor 042 was started.

## Paper summary follow-up — 2026-11-12

At the user's request, added `docs/paper_methods.md`: a concise grouped bullet
summary for manuscript drafting, with optimizer details in an appendix section.
Preserved the detailed methods reference and added navigation/ownership links.
Reporting detail is deferred as requested. The summary corrects the proposed
normalization wording against Task 033C's verified reference: kelp-positive
with-BC training chips include background pixels, but not background-only chips.
It also distinguishes the >50% chip-nodata exclusion from the 20%-valid full-TIFF
inference rule. LORO-specific provenance remains with Task 037. The user's supplied
previous-study comparison is retained without inventing a paper citation.

Validation: repository hygiene and `git diff --check` passed; new relative links
resolve. All changes remain documentation-only and uncommitted; no later task,
experiment or external-artifact change was started.

## Commit and closure — 2026-11-12

The user approved committing all Task 038 documentation, including the paper
methods summary. This supersedes earlier instructions to leave the work
uncommitted. The commit contains only the 038 Markdown changes and this closure
update. No push is authorized or performed. Task 038 is complete; stop here.
Tasks 039 and 042 remain unstarted and require a separate request.
