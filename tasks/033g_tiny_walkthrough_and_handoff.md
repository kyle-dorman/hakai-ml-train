# Task 033G: Tiny walkthrough and researcher handoff

Status: Planned — 2026-10-28. Not started; the current user request is docs only.
Depends on: Completed 033A–033F with recorded outcomes.

## Abstract

Integrate the finished baseline workflow into a short fresh-directory researcher
walkthrough, verify package portability and close the task family. Stop before
Task034 implementation or production training.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
Shared parent and child outcomes, [quickstart](../docs/quickstart.md),
[architecture](../docs/architecture.md), [experiments](../docs/experiments.md),
[data artifacts](../docs/data_artifacts.md) and published tiny v2.

## Outputs and planned interface

Concise actual recipes, final package/legacy-consumer cleanup as replacements
permit, recorded tiny runs/bundles and a Task034 handoff. No new CLI family,
runner framework or extra dataset copies.

## Plan/spec

From an unrelated installed-package directory, fetch/use tiny v2 with fresh
outputs and explicit machine paths. Exercise chosen individual previews,
pixel stats, train/validation/save/load/resume and copied-bundle image-array
probabilities. Cover every spectral path and both training-variant selections;
preview all six production combinations without executing production training.
Report eligibility separately from canonical counts and geometry separately
from valid labels. Retire only obsolete code whose consumers have replacements.
Keep remaining legacy dependencies documented until later workflows replace them.
Update current docs and both queues using compact outcomes, with detailed
evidence here and external artifacts identified plainly.

## User decisions required

No new experimental policy. Fix instructions where another researcher would
need undocumented help; do not infer authorization for GPU or production runs.

## Smoke and validation

Installed wheel/sdist outside the checkout, meaningful regression tests,
Ruff format/check, broad pre-commit and Markdown/link/diff checks. Bounded real
CPU walkthrough, fresh copied bundle and all-band/variant dry-runs pass.
Keep new training artifacts within the shared 4GiB smoke budget, running cases
sequentially and retaining one representative durable bundle/recovery pair.
Record preexisting unrelated failures and local/CUDA validation limits.

## Acceptance and non-goals

A researcher can follow short settings-based recipes without Python edits;
all child outcomes and portability limits are recorded and Task034 has a clear
bundle/preprocessing handoff. No production training, tiled inference or scoring.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: Select Task034 in a new window for image-only tiled prediction; stop here.
