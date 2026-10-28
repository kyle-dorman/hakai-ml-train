# Task 033B: Review and select augmentation settings

Status: Planned — 2026-10-28. Not started; the current user request is docs only.
Depends on: Completed 033A gallery and numerical checks.

## Abstract

Review the actual isolated previews with the user and select a small explicit
augmentation policy. Stop before model implementation or training.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
The shared parent, 033A outcome and its gallery, trial settings and realized
parameter records. Read [experiments](../docs/experiments.md) and
[documentation](../docs/documentation.md) before updating selected policies.

## Outputs and planned interface

An approved plain augmentation recipe with strengths, probabilities, order,
mask/fill rules and seeds; a concise decision record here and updated parent/
experiment contracts. If explicitly requested after isolated review, use the
existing preview command for small combinations; do not implement new transforms.

## Plan/spec

1. Present isolated before/after examples and boundary close-ups; record which
   strength ranges remain useful for each operation and which are excluded.
2. Resolve channel-shift units/ranges, additive lower bounds, spatial dropout
   sizes/counts, band-dropout fill/eligible bands and whether it is enabled for
   each spectral recipe. Never drop every selected channel.
3. Choose probabilities after strengths. Only after the user's isolated review,
   preview explicitly requested combinations in actual order, with operation
   lists visible; do not hide stacking effects behind nested random policies.
4. Freeze one supported policy and preserve selected 5000 cap/normalization,
   native validity and band identity. Keep any unselected trials separate.

## User decisions required

The user must select production strengths/probabilities and band-dropout rules
from the review. Preview availability alone is not approval. If undecided,
record the open choices and remain awaiting review; do not start later training.

## Smoke and validation

Verify saved values reproduce displayed examples, selected fields are supported
by 033A and the recipe records every fill/mask/order decision. Run focused tests
only if code changes are required; otherwise inspect Markdown/links and run
`git diff --check`. Visual plausibility is not accuracy evidence.

## Acceptance and non-goals

Selected settings and any requested combination review are recorded clearly,
with no test imagery, production training or new augmentation family.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: 033C: simplify the pixel-statistics utility; consume this selected policy later.
