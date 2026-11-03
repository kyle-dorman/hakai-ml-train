# Task 033C: Simplify pixel statistics

Status: Complete - 2026-11-02. Installed NumPy statistics and full approved-reference reproduction verified; stop before 033D.
Depends on: Shared parent constants and completed normalization analysis; precedes model work.

## Abstract

Replace legacy statistics and analysis-specific bookkeeping with one small
installed NumPy workflow under prepare/. Stop after its focused checks and a
single reproduction of the selected 5000-capped training reference.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
The shared parent, the retired `src/prepare/channel_stats.py` (Git history), current `select_windows`,
existing true-size chip format, the capped analysis outcome and
[architecture](../docs/architecture.md), [quickstart](../docs/quickstart.md),
[documentation](../docs/documentation.md).

## Outputs and interface

Implemented `src/kelpseg/prepare/channel_stats.py`, thin `cli/pixel_stats.py`,
focused `tests/test_channel_stats.py` and a short actual-use guide. Installed CLI:
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
Do not start another numbered task in this window. The statistics command and
module above are implemented and verified; model workflows remain later tasks.


## Implementation plan - 2026-11-02

Use one small `prepare/channel_stats.py` function that selects active training
rows through existing manifests, optionally filters entire chips by manifest
kelp count, reads only true-size image entries, excludes native all-band-zero
nodata before an optional cap, and merges per-chip float64 central moments.
Compute sample standard deviation with ddof=1. Keep overlap as pixel exposure
weighting, with no label-pixel filtering or artificial padding.

The thin installed CLI exposes the declared chip/assignment paths, experiment,
variant, kelp-only filter, optional cap and fresh JSON output. One report records
settings/references, native bands, means/sample stds and chip/pixel/byte counts.
Use normal progress logs, initial output refusal and one atomic report write.
No extra schema framework, workers, hashes, receipts, restart or recovery.

Check direct NumPy fixtures and ordinary input errors, CLI help/error behavior,
and runtime-only wheel/sdist invocation. Verify legacy consumers before removing
only the replaced utility. Then run the approved full with-BC, kelp-positive,
cap5000 scope once into a fresh external report and compare all bands/counts
against the parent constants and archived analysis with an explicit float64
tolerance. Preserve the selected constants even if an unexplained difference
appears. Update the guide, outcome and queue; stop before 033D.


## Outcome 2026-11-02

Implemented `compute_channel_stats` as one readable sequential NumPy workflow
in `src/kelpseg/prepare/channel_stats.py`, with the thin installed
`kelpseg pixel-stats` command. It reuses source/window assignment selection,
reads only selected training image members, handles true-size edges and native
all-band-zero nodata before the optional explicit cap, and merges float64
per-chip central moments. Sample standard deviation uses ddof=1; overlap counts
as repeated chip exposure. No labels, image scaling, augmentation or model
preprocessing participate in the calculation.

The report records the declared band order, means/sample stds, cap, input/split/
filter references, chip/source/pixel counts, nominal NPZ bytes and elapsed time.
Initial overwrite refusal precedes input reads; one small completed JSON is
published atomically. Existing preparation logging reports phases, current
payload and progress counts/bytes. Settings, empty selection, insufficient
support, shape/dtype errors and named zero-variance bands have clear errors.
There are no workers, ML libraries, custom schemas, hashes, receipts or recovery.

### Changed files and retirement

- Added `prepare/channel_stats.py`, `cli/pixel_stats.py`, registered the command,
  and added focused `tests/test_channel_stats.py`.
- Extended CLI and runtime-only wheel/sdist checks with a real three-band,
  image-only training fixture. Its held-out/background payloads do not exist,
  proving the intended selection boundary in the installed workflow.
- Deferred TIFF-only imports in `chip_inputs.py` and the split writer so metadata
  selection/statistics can import with NumPy alone. Chipping/splitting regression
  tests pass; this changes import timing only.
- Removed `src/prepare/channel_stats.py` after checking all consumers. No active
  consumer remained; its Torch/DataLoader, fixed-path/scaling assumptions and
  temporary array batching are replaced. Historical external analysis files
  remain untouched, including their old self-check reference.
- Updated README, architecture/index, quickstart, shared task parent and task
  routing. No dependencies, approved constants, augmentation recipe or canonical
  source data changed.

### Full reference reproduction

Ran the installed command once on baseline/augmented, with `--kelp-only` and
`--clip-value 5000`. Durable external artifacts:

- `/Volumes/x10pro/kelpseg/analyses/task033c_pixel_statistics_v1/statistics.json`
- `/Volumes/x10pro/kelpseg/analyses/task033c_pixel_statistics_v1/progress.log`

Exact agreement with the archived approved scope: **18,311 available training
chips; 8,518 selected; 9,793 zero-kelp chips excluded; 254 selected original
sources; 2,052,580,518 valid pixel exposures**. The nominal selected NPZ byte
count also matches exactly: **22,000,295,988 bytes**. Labels and excluded,
validation/test payloads were not opened. All eight band names/order and the
5000 cap match the parent contract.

Compared all eight means/sample standard deviations against both the unchanged
`preprocessing.py` constants and the archived approved analysis, using
**rtol=1e-10, atol=1e-8 raw units**. Maximum absolute mean difference is
**1.1368683772161603e-13**; maximum absolute sample-std difference is
**1.4665602066088468e-11**. Maximum relative differences are 2.12e-16 and
2.71e-14 respectively. These are floating-point rounding differences between
per-chip centered moments and the older raw-square subtraction, not changed
normalization. The approved constants remain unchanged.

The pass took **164.71 seconds wall time** (164.61 seconds reported computation)
and **293,257,216 bytes maximum resident memory**, approximately **280 MiB**,
measured by macOS `/usr/bin/time -l`. Only one chip's image/moment arrays are
held at a time, alongside ordinary manifest metadata. No production model
training or repeated full-data pass was run.

### Validation and simplicity review

**132 focused statistics/CLI/chipping/splitting checks** pass, plus the
**runtime-only wheel/sdist installation check**, which executes the actual
command outside the checkout. The 20 statistics checks independently cover
NumPy means/sample stds for 3/8 bands, capped/uncapped values, exact cap edges,
variable true sizes, native nodata versus individual-band zero, whole-chip
kelp eligibility, ignored-label/background image pixels, overlap weighting,
read boundaries, source preservation and ordinary settings/support errors.
Fresh-process checks confirm no Rasterio, Torch, Albumentations or visualization
imports in this workflow. Root/subcommand help remain lazy.

The first installed dependency check exposed an existing eager TIFF import via
the metadata selector. It was fixed with the small deferred imports above; the
complete installed check then passed. No unresolved failure remains. Ruff
format/check, all-file pre-commit plus new-file hooks, Markdown file links and
`git diff --check` pass. Independent read-only review found no material issue
or need for additional safeguards/framework code.

033C is complete. Exact next action: separately select **033D: model and
training inputs**, including the bounded SegFormer update checks. No 033D code,
model download, update, training run or later task was started.
