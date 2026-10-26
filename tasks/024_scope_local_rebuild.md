# Task 024: Scope the local kelp workflow rebuild

Status: Complete

Depends on: Task 023; user direction on 2026-10-26.

Execution: Local documentation and planning only.

## Abstract

Replace the completed PS8B-only study's project contract with the requested
small, researcher-friendly Planet kelp toolkit. Record the decisions, preserve
the known Git starting point, and order small implementation tasks. Stop after
this planning task; do not begin reference inference or remove code here.

## Inputs

- User discussion on 2026-10-26, including permission for breaking changes and
  extensive removal of unsupported workflows.
- Starting commit `ac933fd667c2ddb445b8a622d8404387a2d056e2`.
- Current source, focused tests, configs, and Tasks 000–023 as evidence.
- Downloaded checkpoint:
  `/Users/kyledorman/Downloads/kelp_ps8b_segformer_b3_epoch-62_val-iou-0.7047.ckpt`.
- Existing local data beneath `/Volumes/x10pro/kelpseg`.

## User decisions recorded

- Scope: binary kelp segmentation on Planet 8/4/3-band inputs; modest recipe
  variations and a possible later RGB DINOv3 experiment.
- Working interpretation of the band answer: compare RGB+NIR and RGB subsets
  from the same eight-band acquisitions first. Validate band names and indices
  against actual metadata; do not silently take the first N channels. Separate
  Planet product families would need an explicit later contract.
- Capture a few representative legacy checkpoint inputs, labels, and results
  as a gut check. Exact training reproduction and backward-compatible APIs are
  not requirements.
- Build and test as much as practical locally. Use bounded inference and tiny
  optimizer/checkpoint checks on the Mac; full training belongs on a GPU host.
- Original-data scope is not yet known. Inventory it, recover the cleaning
  decisions, document them, and rebuild cleaned data without changing originals.
- Store original, cleaned, and chipped data on UCLA Box. Generated dataset
  splits belong with data outside Git; keep generation rules in Git.
- New-region comparisons are: existing kelp model without adaptation; kelp
  checkpoint fine-tuned on new data; generic pretrained weights fine-tuned on
  new data; retraining with combined old/new data. The final run's starting
  weights remain an explicit later choice, not an assumed sequential stage.
- Prefer small numbered tasks, simple Python, strong uv defaults, no final
  `scripts/` directory, and removal of unrelated code.
- Follow-up: incorporate concrete usability acceptance into the existing
  roadmap. Start the researcher guide with package work, but defer the reusable
  tiny walkthrough until Box and the cleaned dataset are established. Keep Box
  integration to ordinary folders, manifests, and documented rclone commands.

## Expected outputs and implementation contract

1. Update the repository entry points and owned contract documents to reflect
   this scope. Clearly distinguish the current legacy implementation from the
   intended replacement; never advertise an unimplemented command as working.
2. Keep current-facing docs compact. Retain historical implementation evidence
   in existing numbered tasks and the known starting commit.
3. Publish the ordered roadmap in `docs/todo.md`. Create a full next-task
   contract for Task 025; later roadmap slots receive detailed contracts only
   when selected so data discoveries can inform them.
4. Preserve source identity, no-leakage splits, source-aware nodata, ignore
   index `-100`, correct inverse padding, and unique-pixel overlap scoring.
5. Keep scientific claims bounded to represented imagery and supplied labels.

## User decisions required

None to finish this planning task. Later tasks must resolve original-delivery
membership and ambiguous label meanings before building a new cleaned release.
Joint-training initialization and exact GPU host details are later decisions.

## Plan/spec

Use the owned docs as the replacement design. Each roadmap slot remains one
bounded task with explicit local acceptance. A completed task updates its
outcome and queue and stops; the roadmap does not authorize executing all
numbered tasks in this window.

## Smoke and validation

- Inspect all changed Markdown and verify local links.
- Check agreement between AGENTS, README, index, queue, and owned contracts.
- Run `git diff --check`; source/tests/data are unchanged.

## Acceptance criteria

- Scope, breaking-change permission, local validation strategy, Box storage,
  external splits, and all four adaptation comparisons are recorded.
- Task 025 is ready to execute without asking for an unnecessary full training
  reproduction decision.
- Unknown original-data membership remains visible.
- No source deletion, data rebuild, transfer, inference, or training occurs.

## Non-goals

Implementing the replacement package; creating data releases; configuring Box;
capturing the reference chips; running remote work.

## Outcome template

Record changed repo files, durable external artifacts, checks, unresolved
issues, and the exact next action.

## Outcome

Completed locally on 2026-10-26. The user decisions above now govern the
rebuild. The current implementation remains unchanged, and planned package
commands and data releases are explicitly distinguished from available ones.

Changed repository files:

- `AGENTS.md`, `README.md`, and `docs/index.md`: concise new scope, entry path,
  breaking-change boundary, and implemented-versus-planned status.
- `docs/product.md`, `docs/architecture.md`, `docs/data_artifacts.md`, and
  `docs/experiments.md`: spectral comparison, original-data reconstruction,
  external split/Box storage, local validation, scoring, and adaptation contracts.
- `docs/todo.md`: ordered small-task roadmap through local relocation rehearsal.
- `docs/documentation.md`, `docs/backlog.md`, and `tasks/README.md`: aligned
  documentation process, optional experiments, and historical/current routing.
- This task and `tasks/025_capture_legacy_reference.md`: decision evidence and
  the complete next-task reference-capture contract.

Durable external artifacts: none created or changed. No code removal, dataset
mutation, transfer, reference inference, training, or remote action occurred.

Validation: reviewed the Markdown changes and routing; all local Markdown
links in the 13 changed/new documents resolve and code fences balance.
`git diff --check` passes. Two independently scoped reviews checked the
roadmap/contracts and reference-capture spec. The latter clarified use of
`uv run --no-sync` to avoid an accidental environment synchronization during
legacy capture. This docs-only task did not run training tests or lint.

Unresolved later choices: complete original-delivery membership, unexplained
cleanup differences, actual source-band metadata, combined-data initialization
and sampling, and eventual GPU host/resource checks. None blocks Task 025.

Exact next action: execute Task 025 locally, select its five or six samples
before viewing predictions, and capture/verify the external gut-check package.
Stop this planning task without starting that inference task in this window.

### Usability follow-up

The user approved adding concrete simplicity checks to the existing roadmap,
with the reusable tiny walkthrough deferred until dataset/Box establishment.
Updated `docs/todo.md` and the owned architecture, artifact, experiment, and
documentation contracts; aligned `AGENTS.md` and `tasks/README.md`.

Task 028 starts the short researcher guide, simple setting/path/output
conventions, and automated focused CPU checks. Task 031 begins the small real
walkthrough after verified Box setup (027) and the cleaned release (030).
Subsequent workflows extend that example. Task 025's legacy capture and focused
test fixtures keep their earlier place. The walkthrough subset stays outside
Git and needs only a one-time fetch for routine offline use.

Added portable prediction bundles, helpful preflight/errors, a consistent run
layout, and a recorded simplicity check per implementation task. Box remains
ordinary folders/manifests and direct documented rclone operations. Final
handoff includes another researcher following the instructions.

Validation: inspected the updated Markdown, checked local links and fence
balance across the eight follow-up files, and passed `git diff --check`. A
bounded independent review confirmed the sequence and distinction between
the walkthrough, legacy capture, and correctness fixtures. No code, data,
transfers, or external artifacts changed. No new blocking decisions arose.
Next action remains Task 025; no inference or implementation was started here.
