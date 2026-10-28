# Task 033E: Training, validation and EMA

Status: Planned — 2026-10-28. Not started; the current user request is docs only.
Depends on: Completed 033D model/input helpers and selected augmentation recipe.

## Abstract

Implement one single-device epoch loop with validation-only model selection,
EMA, flat recipes and local records. Stop before exact resume and final portable
bundle guarantees, which belong to 033F.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
Shared parent, 033D helpers, chosen 033B policy, [experiments](../docs/experiments.md),
[quickstart](../docs/quickstart.md) and the retained optimizer/scheduler/callback
code as a reference. Preserve the completed-study identities as history.

## Outputs and planned interface

Planned `training/settings.py`, `training/loop.py`, initial checkpoint-writing
helpers, thin `cli/train.py`, `configs/train/planet8.toml`, `planet4.toml`,
`planet3.toml`, `tiny_cpu.toml` and focused loop/settings tests. Future command:
`uv run kelpseg train --recipe <file> --paths <file> --variant augmented --run-id <fresh-id> [--dry-run]`.
Local settings/run records, validation CSV and distinct best/last saved state
outside Git. No resume interface until 033F.

## Plan/spec

Use one strict schema and ordinary functions; reject unknown settings and
initial output collisions. Preview roots, source/canonical/eligible counts,
bands, cap/stats, selected augmentations, initialization and epoch/update budget.
Define final partial accumulation and valid-pixel loss weighting. Validate on
the disjoint selector subset with deterministic preprocessing. Keep threshold
0.5 and aggregate validation IoU selection, earliest ties. EMA uses decay .999,
first update after optimizer step101, current weights before an average exists,
then averaged validation/best state. Save ordinary and EMA state separately.
Match epoch count/effective batch/policy across BC variants and report actual
updates. Local records work offline; W&B is optional and uses the fixed project.
Never open test arrays, including at fit completion.

## User decisions required

Production epoch count, effective batch and scheduler numeric values must be
explicitly resolved in the recipe before expensive execution; historical values
are proposals. Tiny CPU settings are separate. Do not launch production training.

## Smoke and validation

Focused seeded loop, scheduler/final accumulation, early EMA validation,
EMA/current saved-state distinction, pooled metrics, empty support and no-test
access checks. Run a tiny CPU training/validation/save smoke and band/variant
recipe previews. Run affected tests/lint; use pre-commit for broad changes.
No exact-resume or fresh-directory bundle claim yet.

## Acceptance and non-goals

One installed train/dry-run path produces correct local records and separate
best/recovery state with validation-only selection; no full experiment runs.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: 033F: make best models portable and verify completed-epoch resume.
