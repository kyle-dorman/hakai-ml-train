# Task 033B: Review and select augmentation settings

Status: Complete - 2026-11-02. Combined outputs approved; final recipe saved and code quality checks passed.
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

An approved plain augmentation recipe using the pinned stock Albumentations
classes, native parameters, probabilities, order, mask/fill rules and seeds;
a concise decision record here and updated parent/experiment contracts.
After selecting operations and ranges, build the separate combined
training-pipeline viewer requested by the user on 2026-11-02. Reuse the actual
classes and data-domain adapter; do not translate custom strength scales.

## Plan/spec

1. Present isolated before/after examples and boundary close-ups; record which
   strength ranges remain useful for each operation and which are excluded.
2. Resolve native class parameter ranges, stock clipping, spatial dropout
   sizes/counts, band-dropout fill/eligible bands and whether it is enabled for
   each spectral recipe. Never drop every selected channel.
3. Choose probabilities after strengths. Only after the user's isolated review
   and choices, preview the selected combined pipeline in actual order, with operation
   lists visible; do not hide stacking effects behind nested random policies.
4. Freeze one supported policy and preserve selected 5000 cap/normalization,
   native validity and band identity. Keep any unselected trials separate.

## User decisions required

The user approved the native ranges, SomeOf(2) composition and combined outputs.
The saved final recipe is `configs/augment/baseline.json`; no augmentation
selection remains open. Do not start later training as part of this task.

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

## Implementation plan - 2026-11-02

The user approved the remaining proposed ranges and requested a visualization
of the actual pipeline. This explicitly starts 033B; 033A stays closed and
later tasks remain unstarted. Use the pinned stock classes and the shared
65535-domain adapter, exact final 5000 cap/normalization and 2000 display.

Use D4(p=1), then SomeOf(n=2, replace=False, p=1), with eight equally eligible
children at p=1 in this configured order: brightness, gain, blur, noise,
Sharpen, CoarseDropout, channel shifts, ChannelDropout. Native sampled ranges:
brightness -0.0025..0.005; gain multiplier 0.8..1.2 (contrast -0.2..0.2);
blur sigma 0.5..1.5 pixels; noise std 0..0.002; Sharpen alpha 0..1; coarse
hole count 1..4 with independent height/width fractions 0.05..0.25; uniform
constant independent per-band shifts -0.01..0.01; drop exactly one eligible
model-input band with zero fill. Other strengths use ordinary uniform library
sampling. Coarse image fill is zero and target/validity fill is -100.

Implement one readable literal stock factory and direct-stock focused checks,
then a separate exploratory Python pipeline gallery entry point. Reuse the
same 14 kelp-rich training examples and two labeled background controls. Eight
seeded pipeline draws per example show the actual D4 element and two selected
operations/parameters. Compare the full pipeline against its same-D4-only
reference by default, with source-original comparison available. Preserve
clean/labeled RGB/NIR views, paired close-ups, navigation and zoom. Save the
native serialized recipe and realized seeds/parameters. No custom kernels,
policy framework, installed CLI, training or later task work.

Inspect the actual generated comparisons and browser controls, update guide,
shared recipe and outcome. Implementation can finish before human review,
but do not declare the final combined-pipeline review complete on the user's
behalf.

## Implementation outcome - 2026-11-02

Implemented the agreed stock recipe and the requested separate combined preview.
The user's approved ranges and SomeOf(2) composition are recorded in the shared
parent. At this initial implementation handoff, human review of the combined
outputs was still open. Final approval and closeout are recorded below.

- `augmentation_pipeline.py` contains the readable literal stock factory and
  source/D4-reference/full-pipeline diagnostic states. It uses the exact real
  Compose(D4, SomeOf) call and records actual operation order, native parameters
  and physical dropped-band names. The library selects two distinct extras;
  no project kernels, sampling overrides or custom policies are introduced.
- `augmentations.py` extends the same raw-domain adapter to stock Compose. Its
  `seed=None` mode advances a reused pipeline's RNG, with deterministic sequence
  replay checked. Native validity remains an int8 additional mask; holes are
  ignored and invalid fill is restored after the complete pipeline, including
  when a later pixel transform changes hole values internally.
- `pipeline_preview.py` and `examples/augmentation_pipeline_preview.py` export
  a training-only offline gallery. Existing preview input loading, exact
  preprocessing/domain metadata and native-image export are shared rather than
  copied. The existing isolated viewer remains available.
- `pipeline_viewer.html` shows actual D4 plus two-operation traces, eight draw
  choices per example, aligned D4-only versus full comparison by default and
  a source-original reference toggle. Clean RGB/NIR, labels on the same base,
  paired kelp close-ups, example navigation and enlarged comparison are retained.
  Noise field SD is explicitly empirical; configured blur/noise ranges are
  shown because stock classes do not expose the sampled nominal scalar.
- Updated focused pipeline/generator tests, installed-distribution checks,
  quickstart, parent, experiments, README/index and task routing. No dependency
  changes, model imports, training run, held-out payload access or later task.

### Durable external artifact

`/Volumes/x10pro/kelpseg/analyses/task033b_pipeline_previews_v1/index.html`

`pipeline.json` is the native stock serialized recipe. `gallery.json`, selected
window CSV, per-example parameter JSON and native PNGs retain the source/window
identities and realized draws. The same 16 selected rows as 033A v2 comprise 14
kelp-rich windows and two separately labeled background controls: **128 draws /
384 states / 1,008 native PNGs**. Core generation totals **1,028 files /
327,573,058 bytes**, before browser proof. All source data are unchanged.

### Validation and review boundary

All **70 focused adapter/pipeline/input/display/preview tests** pass. The
runtime-only wheel/sdist check also passes, including the packaged pipeline
viewer and actual Compose call outside the checkout. Ruff format/check and
all pre-commit hooks pass; Markdown file links and `git diff --check` pass.

The actual gallery audit verifies the exact stock factory kwargs and parent
normalization, 65535 input domain, final 5000 cap and fixed 2000 display. Every draw
records D4 plus two extras. All eight families, all eight D4 groups and all
eight native bands occur; 37 draws include a single-channel drop. All native
asset paths exist. Reconstructed all 128 D4 masks/crops and all 35 coarse hole masks;
full valid/foreground/scoreable/ignored counts match exactly. Actual generated
clean comparisons and labeled coarse-dropout images were inspected.

An independent replay loads saved `pipeline.json` via stock `A.from_dict`,
replays nine recorded seeds covering all eight operations, a partial edge and
both controls, and reproduces all metrics plus 36 clean/labeled RGB/NIR PNGs
pixel for pixel. Actual offline browser checks pass without errors: all 128
records, three trace cards, eight draw controls, draw-index retention and wrap,
source-reference toggle, unchanged right output, aligned clean/NIR-label zoom,
96/512-pixel canvases, background examples and mobile 390-pixel layout without
horizontal overflow. Inspected browser screenshots and results are retained in
`review_screenshots/` beside the gallery.

At the initial implementation handoff, the next action was user review of the
combined gallery. That review is now resolved by the final approval below.


## Final approval and code quality plan - 2026-11-02

The user approved the actual combined outputs and explicitly requested a code
quality pass prioritizing simplicity/readability, saving the final recipe,
closing 033A/033B and committing the work. This resolves the combined-review
gate. Do not start 033C; explain its planned scope after this handoff.

Review the raw adapter/pipeline/preprocessing, Python gallery helpers and both
plain HTML viewers in bounded scopes. Prefer ordinary functions and readable
formatting; remove confusing defaults/labels rather than add a framework.
Keep the approved native constructor values and scientific masks unchanged.
Save `configs/augment/baseline.json` as the native Albumentations snapshot of
the literal factory, with a focused parity check. Refresh viewer HTML only on
the existing approved gallery data and recheck the real browser/pixels. Run
focused package tests, installed distributions, Ruff and pre-commit before the
local commit. Record any unrelated failure without expanding the task.


## Final approval, quality pass and closeout - 2026-11-02

The user approved the combined pipeline after inspecting the actual viewer.
Saved the final native recipe at `configs/augment/baseline.json`: exact
Albumentations serialization of `build_training_augmentation`, verified by a
focused parity test and against the approved external `pipeline.json`. There
is one literal implementation and no custom settings schema or parser.

The code quality pass prioritized ordinary readable functions and source:

- Formatted both offline viewers as readable HTML/CSS/JavaScript and clarified
  function names. Friendly operation headings include **Channel shifts** while
  keeping the actual stock class visible. Approved-policy text replaces stale
  pending-review text. No framework or dependency was added for formatting.
- Consolidated duplicated clean-image/label-overlay export into one explicit
  loop; exact exported-pixel checks still pass. Example outputs now use fresh
  researcher names instead of existing published task artifact directories.
- Changed the raw adapter's ordinary default to `seed=None`, so reused seeded
  pipelines advance naturally. Diagnostic calls still pass explicit seeds.
  Native serialized Compose without optional parameter tracking applies
  correctly and returns an empty trace instead of raising a KeyError.
- Clarified pipeline metadata names and added meaningful advancing-RNG,
  explicit-seed replay, stock serialization roundtrip and final-snapshot checks.
  No approved constructor values, pool order, normalization, source data,
  physical bands, labels, validity or generated preview pixels changed.

All **157 relevant checks** pass, including chip/loading, CLI, augmentation
behavior, input/display/generation and runtime-only wheel/sdist installation.
The final **73 augmentation checks** also pass after all cleanup. Ruff format
and lint, every pre-commit hook, Markdown file links and diff checks pass.
No unrelated failure was found in this validation scope.

Refreshed the existing 033A v2 and 033B v1 HTML from their saved records; native
PNG files were reused. Final browser verification is recorded below. 033A and
033B are complete with no open augmentation choices. The local commit includes
only these task implementations, approved recipe, focused tests and routing.
Exact next action: explain and separately select **033C: simplify pixel
statistics**. No 033C implementation, model work or training was started.


Final browser verification passed for both refreshed galleries with zero browser
errors. The combined viewer shows the approved badge and friendly Channel shifts
heading alongside the native AdditiveNoise class; all draw/example navigation,
source/D4 comparison, clean/labeled zoom, backgrounds and mobile controls work.
The isolated viewer retains all families, native-value selectors and coarse
modes. Actual final screenshots were inspected and retained under each gallery's
`review_screenshots/final_quality_pass/` with browser results. No review finding
remains open. The approved data and native PNGs were unchanged.
