# Task 037E: Focus current documentation and separate history

Status: Complete, including review follow-up — 2026-11-12. Commit authorized by the user.
Depends on: completed 037D (`4152cc8`). Next: Task 038 methods documentation.

## Abstract

Make the core docs describe what researchers should do now. Separate supported
instructions and reference material from completed experiments, migration notes,
publication evidence and task progress. The preceding read-only review found stale
instructions as well as excessive history. This task changes documentation only.

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

## Section-to-destination map (recorded before documentation edits)

Working tree was clean at entry. Only Markdown documentation will change.

| Existing sections | Destination and treatment |
|---|---|
| README feature chronology; index completion log; TODO completed milestones | Short current entry pages; evidence linked from `docs/history.md` and existing task outcomes |
| Quickstart install, tiny-v2 fetch/split/chip/train/copy/predict/report fragments | `docs/quickstart.md`, one ordered CPU smoke workflow |
| Quickstart paths, organization/check/clean/chip/split schemas and pixel statistics | `docs/guides/preparation.md` |
| Quickstart model inputs, loss options, train, early stopping, portable bundles and resume | `docs/guides/training.md`; distinguish generic defaults from selected B0 |
| Quickstart tiled/chip prediction and report interpretation | `docs/guides/prediction_reporting.md` |
| Quickstart augmentation, shoreline and temporal recipes | `docs/guides/diagnostics.md` |
| Historical loss/LR/weight-decay/model-size/distance-weighting launches; GPU pilots | Historical recipe reference linked from `docs/history.md`; preserve commands as history |
| Full-release restore; storage inventories and Box publication verification | `docs/reference/ca_bc_release.md`; retain trusted recovery values and commands |
| GPU access/bootstrap/authentication/staging/readiness/monitoring/backup | `docs/gpu_setup.md`, current operations only |
| Architecture pipeline/identity/split/nodata/padding/reconstruction/coverage | `docs/architecture.md`, implemented contracts retained pending 038 |
| Product purpose/comparisons/claims; experiments selected model and run rules | Existing owners, current model first; historical study links in history |
| Storage policy versus historical paths/eviction/audit | `docs/data_artifacts.md` policy; release reference and historical provenance/task owners for evidence |
| Cleanup historical traces and audit limits | `docs/cleanup_provenance.md`, explicitly historical; current policy routes to preparation |
| Task tables and decision checkpoints | Compact `tasks/README.md`; preserve historical navigation separately if needed |
| Ownership and inbound links | `docs/documentation.md` and referring Markdown files updated together |

LORO normalization/claim details remain in Task 037. Methods authoring is deferred
to 038. Outside-label exclusion is implemented; dismissed audit questions will
not be reintroduced into core guidance.

## Outcome — 2026-11-12

037E is complete. The working tree was clean at entry at setup commit `4799dad`;
037D implementation remains `4152cc8`. Changes are documentation-only and remain
uncommitted for review. No implementation, config, normalization, data, model,
report or external artifact was changed. No experiment or researcher message was
launched. Tasks 038, 039 and 042 were not started.

### Current documentation and preserved destinations

- README and the documentation index now lead with the selected with-BC 8-band
  B0 BCE + Dice epoch-16 EMA model and route by researcher goal. The queue contains
  current status, actual follow-ups and the pending roadmap rather than a
  completion narrative. Task navigation retains all task links with compact status.
- The quickstart is one six-step CPU workflow: install, fetch tiny-v2, split/chip,
  train, copy the bundle and predict a validation crop, then report against its
  matching label. It preserves dataset/source/date and original crop offsets,
  uses fresh external outputs and unchanged smoke settings, and states that
  smoke scores are not research results. No training was rerun for this prose task.
- Detailed reusable instructions now live in `docs/guides/preparation.md`,
  `training.md`, `prediction_reporting.md` and `diagnostics.md`. Model-size,
  checkpoint retention and distance-BCE options remain documented as supported
  settings, separate from historical launches.
- `docs/history.md` routes existing outcomes and recovery. Historical launch
  sequences and gallery references moved to `docs/reference/historical_recipes.md`
  and `historical_gpu_recipes.md`; historical decision checkpoints moved from
  the task index to `tasks/historical_decisions.md`. These are the concrete
  destinations for the historical-reference rows in the pre-edit map.
- `docs/reference/ca_bc_release.md` preserves release inventories, full restore
  commands, trusted historical SHA-256 values, verification scopes and local
  eviction references. Storage policy and Box operations are separate current
  guides. The historical audit remains in `docs/cleanup_provenance.md`, including
  older artifact paths and evidence limits; those are not current blockers.
- Architecture retains the essential current isolation, nodata/ignore, padding,
  overlap and coverage explanations pending 038. Outside-label exclusion is
  described as implemented. LORO normalization provenance and claim qualifications
  remain in Task 037/the saved write-up. Dismissed audit questions were not
  introduced into core guidance.
- GPU setup now separates access/bootstrap/authentication/full-data staging,
  bounded CUDA readiness, monitoring and backup from completed pilots. Tiny
  readiness uses a separate fresh walkthrough root; production uses the full
  release root. Generic B3/smoothed-loss defaults are distinguished from selected B0.

Changed existing files: `README.md`; `docs/index.md`, `todo.md`,
`documentation.md`, `quickstart.md`, `gpu_setup.md`, `architecture.md`,
`product.md`, `experiments.md`, `data_artifacts.md`, `box_backup.md`,
`cleanup_provenance.md`; `tasks/README.md` and this task. New files are the four
guides, three references, history router and historical decision reference named
above. Inbound-link-only updates affect Tasks 031, 032A, 032B, the Task 034 LR
sidecar and Task 037. Task 029B also gains a historical source-recovery note:
five previously broken code/test links now name their paths and point to recovery;
all five paths were verified in starting commit `ac933fd` without restoring files.

### Validation

- All 17 installed subcommands returned success for
  `uv run --frozen kelpseg <command> --help`; root help also passed.
- Current command references were compared with installed help; source/config
  review checked tiny recipe path resolution, source identity/crop offsets,
  prediction/report schemas and output filenames, GPU smoke settings, selected
  B0 settings, resume boundaries and release verifier APIs. No unsupported flags
  were found. Shell code blocks parse with `bash -n`.
- Relative Markdown file and heading links were checked across repository docs
  and tasks, including moved references. No missing targets remain. Historical
  external locations are preserved references, not newly authenticated backups;
  no remote transfer or external URL availability audit was performed.
- `uv run --frozen pytest -q tests/test_repository_hygiene.py`: **18 passed**.
  The initial run found four new files with extra final blank lines; those were
  corrected before the passing run. No unrelated preexisting test failure remains.
- `git diff --check` passes. Reviewed changed Markdown and relocation mappings;
  only Markdown files changed. Full ML tests/training are unnecessary for this
  documentation-only change and were not run.

### Remaining issues and exact next action

No unresolved documentation question blocks 037E. Previously unverified backups
of some earlier external experiments remain recorded in Task 034; this task does
not claim to have verified them. Historical source recovery, release verification
and prior scientific evidence remain available through their owners.

**Next action:** review these uncommitted 037E changes, then select
[Task 038](038_methods_documentation.md) in a new task window and follow its entry
route to author methods. Do not execute 039 or 042 or treat this handoff as starting
038. AGENTS.md did not need a routing change.

## Review follow-up — 2026-11-12

Reviewed the existing uncommitted 037E changes at the user's request, preserving
that work. The review found and fixed these operating gaps:

- **Local setup:** the quickstart now identifies uv/rclone/Box prerequisites,
  explicitly uses Bash, and routes local browser authentication to Box operations
  rather than the GPU-only SSH tunnel instructions. Installation stops on failure.
- **Tiny workflow:** clarified the completed run's `output` field and full output
  paths, added concise failure guidance, and changed reporting to join the
  generated with-BC validation assignments. The prediction CSV retains dataset,
  source/date and crop offsets. Image-only prediction still needs no labels.
- **Preparation:** initialized the missing `paths` variable in the Python
  organizer example and documented the retained input-catalog prerequisite for
  raw reconstruction on another machine. Raw ZIP downloads alone do not restore
  the catalog; the published organized release is the available alternative.
  No new Box catalog location was invented. Stale “below” navigation was fixed.
- **Training/model use:** added explicit selected-B0 fresh-run instructions and a
  copyable existing-model restore recipe; distinguished them from each other and
  from generic B3 defaults. Corrected patience 10 versus selected-B0 patience 20
  and documented the supported resume exception. Fresh fitting from kelp weights
  is not an implemented training recipe option; that remains Task 039 work.
- **Prediction/reporting:** put report-recipe creation before its command,
  made the paired commands stop on failure, explained dataset/release identity
  requirements for assignment joins, and documented that `predict-chips` supports
  val/train, while held-out test TIFFs use `predict` then `report`.
- **Recovery/diagnostics:** full interrupted-run relocation needs the retained
  run folder and best/last checkpoints; a lone last checkpoint is insufficient
  for prior-best selection. Corrected “labels optional for scoring” and removed
  stale preview migration/approval wording while retaining supported defaults.

Follow-up edits are confined to `docs/quickstart.md`, the four focused guides,
`docs/box_backup.md`, `docs/gpu_setup.md`, `docs/experiments.md`,
`docs/architecture.md`, the queue and this record. No implementation, config,
data or durable external artifact changed. No training, inference or transfer
ran, and no later task began.

Validation: **18 repository hygiene tests passed**; `git diff --check` passed;
all relative Markdown links resolved; **68 shell blocks** passed `bash -n` and
**12 Python snippets** parsed. Relevant installed CLI help and configuration
loaders match the revised instructions. A read-only check of the tiny metadata
and TIFF headers confirmed the example's dataset/source/date, original offsets,
768×768 aligned image/label grids and projected-metre CRS. Source assignments
computed in memory from the declared metadata/recipe confirm this source is
`baseline/augmented/val`; prediction/report settings construct successfully.
No image arrays were read and no split artifacts were published by that check.
The two existing W&B reference URLs also resolve to their intended documentation.

No unresolved review finding remains. The walkthrough has been reviewed against
source and metadata, not executed again end to end in this documentation-only
follow-up. Keep the changes uncommitted for user review. **038 remains unstarted**;
select it only in a separately requested task window.

## Commit and handoff — 2026-11-12

The user explicitly requested committing the reviewed 037E documentation and
preparing a prompt for Task 038 in a new chat. This supersedes the earlier
uncommitted-review instructions. The commit includes only the 037E Markdown
changes and this closure update; no push is requested. Task 038 remains planned
and unstarted. Its contract was read only to prepare the handoff prompt.

Exact next action: start a new chat for Task 038 using its existing contract,
with the committed 037E documentation as the baseline. Do not begin 039 or 042.
