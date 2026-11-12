# Task 037E: Focus current documentation and separate history

Status: Ready, not started. Created at the user's request on 2026-11-12.
Depends on: completed 037D (`4152cc8`). Next: Task 038 methods documentation.

## Abstract

Make the core docs describe what researchers should do now. Separate supported
instructions and reference material from completed experiments, migration notes,
publication evidence and task progress. The existing read-only review found stale
instructions as well as excessive history. This is a documentation-only task;
creating this contract does not start the cleanup.

## Inputs and owned documents

Read AGENTS.md, docs/index.md, docs/todo.md, tasks/README.md and
[the documentation guide](../docs/documentation.md). Review README.md and the
current docs: quickstart, GPU setup, architecture, product, experiments,
data_artifacts, box_backup and cleanup_provenance. Consult numbered task outcomes
only for the evidence being relocated. Check source/configs and CLI help when
needed to distinguish actual supported behavior, defaults and selected recipes.
The completed [037D record](037_baseline_comparisons_and_loro.md) owns removal,
recovery and validation evidence; do not duplicate its logs in core documents.

## User decisions required

None. The following decisions are settled:

- Normalization provenance and its implications for the completed LORO claims
  belong in Task 037/the LORO write-up, not repeated throughout the core docs.
  Preserve actual normalization settings and operational instructions unchanged.
- Source/date/physical-spacecraft split isolation, nodata/ignore handling,
  padding, probability reconstruction and coverage semantics will be explained
  in the separate methods document in Task 038. Preserve concise current rules
  until that document exists; do not remove the only explanation prematurely.
- Outside label coverage is already handled: paired cleaned imagery is nodata
  zero, stored labels use ignore value 3, and loading maps it to -100 for loss
  and scoring exclusion. Describe this as implemented handling, not an unresolved
  coverage concern. Image-only prediction must remain independent of labels.
- Do not carry band-identity uncertainty or original-delivery completeness
  caveats into core docs or the planned methods narrative. Do not reopen those
  questions. Historical audit evidence may remain in its historical record;
  normal instructions for selecting the declared band order still apply.
- Preserve existing external data, runs, models, reports and historical evidence.
  No new experiments, researcher messages, implementation changes or commits
  are authorized by this contract alone.

## Plan and concrete implementation contract

Before editing, record a compact section-to-destination map here. Reuse existing
owners and task outcomes; avoid producing a second giant chronological narrative.
The intended document responsibilities are:

| Document | Intended responsibility |
|---|---|
| README.md | Short project purpose, supported workflows, installation and entry links |
| docs/index.md | Short navigation by researcher goal; no completion log |
| docs/todo.md | Current task, next action, blockers and pending roadmap |
| tasks/README.md | Task process and compact task/history navigation |
| docs/quickstart.md | One sequential tiny workflow: install, fetch, prepare, train, copy bundle, predict, report |
| docs/guides/preparation.md | Detailed preparation commands, schemas and examples moved from quickstart |
| docs/guides/training.md | Training settings, initialization/resume, model/loss options and checkpoint use |
| docs/guides/prediction_reporting.md | Prediction/report recipes, output interpretation and errors |
| docs/guides/diagnostics.md | Augmentation previews and optional shoreline/temporal diagnostics |
| docs/history.md | Compact completed-study/milestone/legacy-recovery index linking task outcomes |
| docs/reference/ca_bc_release.md | Current release locations and release-specific restore/verification references |
| docs/architecture.md | Current implementation and pipeline boundaries; concise scientific rules pending 038 |
| docs/product.md | Current research purpose, use cases, non-goals and claim boundaries |
| docs/experiments.md | Current selected model first, then identity/checkpoint/comparison rules |
| docs/data_artifacts.md | General storage layout, immutability and artifact policy |
| docs/box_backup.md | Current restore/backup operations, with release evidence linked rather than retold |
| docs/cleanup_provenance.md | Focused historical provenance, with current policy owned elsewhere |

New paths in this table are planned outputs, not existing documents. If material
fits an existing owner clearly, use that owner rather than creating an empty or
redundant guide. Record any such consolidation in the section map.

1. Correct stale statements first. Examples from the review: evaluation "arrives
   later" in quickstart; smoothed BCE/Lovasz called the current selected baseline;
   an unstarted loss-screen/current-GPU-run instruction; architecture describing
   only B3; published releases called planned; Task 034 continuation instructions.
   Distinguish generic defaults from the selected B0 BCE+Dice epoch-16 EMA model.
2. Remove completed-task summaries, test-count updates, dated user approvals,
   migration narration and original-host run paths from normal entry documents.
   Link the existing evidence from history/release references instead of copying it.
3. Assemble one tiny-v2 walkthrough in execution order. Keep CPU smoke versus
   production usage clear and output names fresh. Put advanced API/settings
   reference in focused guides. Do not change model/augmentation/preparation
   behavior to make the prose shorter.
4. Move historical loss/LR/weight-decay/model-size/distance-weighting/LORO launch
   sequences out of the normal guide. Retain reusable supported options in the
   training/diagnostic references, and label historical commands as historical.
5. Keep GPU setup focused on access, bootstrap, authentication, data staging,
   a bounded CUDA readiness check, generic monitoring and backup. Link the
   current selected recipe; archive old pilots/benchmarks/production launches.
6. Separate storage policy and portable path examples from release-specific
   inventories, QA/publication counts, hashes and eviction history. Preserve
   useful restore commands and trusted release verification references.
7. Update all inbound links/anchors and documentation ownership together.
   Only adjust AGENTS.md if routing requires it; do not expand its history.
   Leave docs/methods.md authoring and methods consolidation to Task 038.

## Validation and acceptance

- A newcomer can identify the selected current model and follow one tiny
  workflow without reading numbered tasks or jumping through historical studies.
- Each current rule has one clear owner; other documents link to it. No deleted
  explanation is the sole remaining source of a still-required operational rule.
- Current-facing commands use supported interfaces and explicit fresh outputs.
  Verify syntax with source/config review and relevant `uv run --frozen kelpseg
  <command> --help`; do not run production or overwrite completed outputs.
- Check relative Markdown file/anchor links, planned-versus-existing wording,
  migration references, and current/pending task numbers. Inspect the full diff.
- Run `uv run --frozen pytest -q tests/test_repository_hygiene.py` and
  `git diff --check`. Full ML tests/training are unnecessary for prose-only work.
- Record changed documents, preserved history destinations, validation and any
  genuinely unresolved documentation question. Do not introduce the two dismissed
  audit caveats as blockers. Stop after 037E; do not begin methods authoring.

## Non-goals

No code/config/data changes, new scientific analysis, model selection, training,
artifact relocation, historical-code restoration, methods authoring, new-region
implementation, deployment, pushes or researcher communication.

## Outcome to record

Status; section-to-destination map; changed files; preserved evidence/recovery
links; validation results; remaining issues; exact next action to select Task 038.
