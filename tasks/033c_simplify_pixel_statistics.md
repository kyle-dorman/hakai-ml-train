# Task 033C: Simplify pixel statistics

Status: Planned — 2026-10-28. Not started; the current user request is docs only.
Depends on: Shared parent constants and completed normalization analysis; precedes model work.

## Abstract

Replace legacy statistics and analysis-specific bookkeeping with one small
installed NumPy workflow under prepare/. Stop after its focused checks and a
single reproduction of the selected 5000-capped training reference.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
The shared parent, `src/prepare/channel_stats.py`, current `select_windows`,
existing true-size chip format, the capped analysis outcome and
[architecture](../docs/architecture.md), [quickstart](../docs/quickstart.md),
[documentation](../docs/documentation.md).

## Outputs and planned interface

Planned `src/kelpseg/prepare/channel_stats.py`, thin `cli/pixel_stats.py`,
focused `tests/test_channel_stats.py` and a short actual-use guide. Future CLI:
`uv run kelpseg pixel-stats --chips <root> --assignments <csv> --experiment baseline --variant augmented --kelp-only --clip-value 5000 --output <fresh-report.json>`.
One plain report contains bands, cap, means/sample stds, pixel/chip counts and
input/split/filter references. No hardcoded CA/BC paths or Clay/region tables.

## Plan/spec

Use ordinary streaming functions/loops and float64 moments; native nodata is
identified before the optional explicit cap. Read image arrays only, handle
true-size edges without padding and keep overlap weighted by chip exposure.
Select training rows through existing manifests, with optional kelp-only counts.
Use standard phase/file/count/byte logging. Refuse an existing report initially
and publish the completed small JSON atomically. Check consumers, then retire
the legacy statistics utility; retain old external analyses as history.
Do not add Torch/DataLoader, hashes, receipts, recovery or parallel workers.

## User decisions required

No new scientific choice: reproduce the parent's selected cap5000, sample
standard deviation and kelp-positive with-BC reference. Do not change constants
to conceal a discrepancy; report an unexplained difference.

## Smoke and validation

Focused direct-NumPy moments, zero-nodata and variable-shape fixtures, clip
boundaries, training/kelp selection, overlap weighting and insufficient or
zero-variance support. Verify another declared channel count works. Run the
selected production scope once with bounded memory and compare full-precision
values within documented float64 tolerance. Run affected CLI/distribution checks,
Ruff format/check and `git diff --check`.

## Acceptance and non-goals

Small researcher-maintained code reproduces the selected values, requires no
ML framework and leaves all canonical payloads unchanged.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: 033D: implement model inputs and the bounded SegFormer update checks.
