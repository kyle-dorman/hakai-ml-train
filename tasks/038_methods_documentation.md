# Task 038: Write the current methods document

Status: Planned, not started. Depends on Task 037E documentation cleanup.
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
