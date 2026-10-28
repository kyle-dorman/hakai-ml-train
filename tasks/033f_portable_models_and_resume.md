# Task 033F: Portable models and completed-epoch resume

Status: Planned — 2026-10-28. Not started; the current user request is docs only.
Depends on: Completed 033E training/state writing and 033D model construction.

## Abstract

Export a self-contained selected model and implement narrow same-run recovery.
Stop before georeferenced/tiled inference and scientific scoring.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
Shared parent, 033E saved-state layout, [experiments](../docs/experiments.md),
[architecture](../docs/architecture.md) and the legacy EMA save/load findings.

## Outputs and planned interface

Complete small bundle/checkpoint helpers and `tests/test_model_bundle.py`,
`tests/test_training_resume.py`. A copied `model/` holds `weights.pt` and
`model.json` with architecture, ordered bands, cap5000, normalization, input/
padding/nodata policy, threshold and EMA identity. Future resume interface:
`uv run kelpseg train --resume <run/checkpoints/last.pt> --paths <relocated-paths>`.
Update actual researcher save/load/resume instructions.

## Plan/spec

Bundle loading constructs the model with no pretrained fetch or original
recipe/registry path. Restore optimizer, scheduler, ordinary weights, EMA,
progress and relevant random/sampling state for same-run completed-epoch resume.
Saved settings own the run identity/budget; reject changed bands, memberships or
recipe. Restart a partial epoch from its last completed checkpoint; no mid-batch
recovery framework. Model-only initialization is distinct from resume and does
not restore optimizer/progress. No general adaptation recipes in this task.

## User decisions required

No new scientific choice. Keep the selected inference weight kind and narrow
recovery boundary; machine roots can relocate explicitly without changing data
or recipe identity.

## Smoke and validation

Copy a bundle to a fresh unrelated directory and reproduce supplied image-array
probabilities without labels, original config paths, W&B or a weight download.
Compare uninterrupted two-epoch tiny training against a completed-epoch save/
resume with the same total schedule, including optimizer/scheduler/progress/RNG/
EMA state within documented CPU tolerance. Cover 8/4/3 bundles and meaningful
resume identity errors. Run affected distribution checks and required lint.

## Acceptance and non-goals

Copied models and completed-epoch resume are verified separately. No label
alignment dependency, hidden online service or georeferenced-inference claim.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: 033G: rehearse the installed tiny workflow and prepare the Task034 handoff.
