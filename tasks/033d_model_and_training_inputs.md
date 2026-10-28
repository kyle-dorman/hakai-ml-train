# Task 033D: Model and training inputs

Status: Planned — 2026-10-28. Not started; the current user request is docs only.
Depends on: Completed 033A–033C and selected 033B augmentation policy.

## Abstract

Connect manifest-selected data and shared preprocessing to one SegFormer B3.
Implement loss/confusion helpers and bounded updates; stop before an epoch runner,
tracking, checkpoints or resume.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
Shared parent, selected augmentation recipe, 033A preprocessing/functions,
`chips.py`, `bands.py`, `select_windows`, retained model/loss code and
[architecture](../docs/architecture.md), [experiments](../docs/experiments.md).

## Outputs and planned interface

Planned `src/kelpseg/models.py`, `training/data.py`, `training/loss.py` and
`training/metrics.py`; focused model/data/loss tests. Promote actual Torch/SMP
runtime dependencies and update installed-distribution expectations. No new
public train command or model zoo yet.

## Plan/spec

Reuse the shared cap/normalization/augmentation path; never copy it into a
second loader. Select `train` plus positive kelp count, retain disjoint val and
metadata-only test identities. Preserve native validity, -100, true extents,
band order and source identity. Construct only SegFormer B3/mit_b3, one logit;
record actual pretrained channel adaptation. Keep the selected smoothed-BCE /
Lovasz objective, handle empty support and sum confusion counts before ratios.
Do not remove retained legacy evaluator imports before their replacement exists.

## User decisions required

Model family, loss, band selections and preprocessing are settled. Use
no-download initialization in automated cases; verify generic ImageNet loading
separately with cached weights or an explicitly recorded initial fetch.

## Smoke and validation

Synthetic CPU float32 forward/backward for real B3 on 8/4/3 paths; partial
edges, background-only/ignored loss cases, pooled confusion counts and a test
payload access guard. Verify training positivity affects train only. Run affected
installed-distribution and lazy-import checks, Ruff format/check and broad
pre-commit if this is a broad code change. Record limits; no CUDA claims.

## Acceptance and non-goals

All spectral inputs can make a bounded optimizer update through the shared
path without test reads, legacy class-path config or a training runner.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: 033E: implement the plain training/validation loop and EMA.
