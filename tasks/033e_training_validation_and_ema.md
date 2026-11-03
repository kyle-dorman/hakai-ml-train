# Task 033E: Training, validation and EMA

Status: Complete and approved for commit — 2026-11-03, including all review follow-ups.
The user selected PyTorch Lightning, explicit band recipes and historical starting values.
Depends on: Completed 033D model/input helpers and selected augmentation recipe.

## Abstract

Implement single-device training with PyTorch Lightning (`lightning.pytorch`),
validation-only model selection, EMA, flat recipes and local records. Use
Lightning Trainer/LightningModule, TorchMetrics and native logging/checkpoint
facilities; do not write a custom epoch/optimization loop. Stop before exact
resume and final portable bundle guarantees, which belong to 033F.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
Shared parent, 033D helpers, chosen 033B policy, [experiments](../docs/experiments.md),
[quickstart](../docs/quickstart.md) and the retained optimizer/scheduler/callback
code as a reference. Preserve the completed-study identities as history.

## Outputs and implemented interface

Implemented `training/settings.py`, a small `training/module.py` LightningModule,
thin Trainer setup and required EMA glue, `cli/train.py`,
`configs/train/planet8.toml`, `planet4.toml`, `planet3.toml`, `planet_RGB.toml`,
`tiny_cpu.toml` and focused training/settings tests. Command:
`uv run kelpseg train --recipe <file> [--dry-run]`.
The recipe selects `variant` and `paths_file`; run IDs are assigned automatically.
Local settings/run records, validation CSV and distinct best/last saved state
outside Git. No resume interface until 033F.

## Plan/spec

Use one strict schema, small explicit Lightning components and ordinary helper
functions; promote Lightning to runtime dependencies. Reject unknown settings and
initial output collisions. Preview roots, source/canonical/eligible counts,
bands, cap/stats, selected augmentations, initialization and epoch/update budget.
Verify Lightning's final partial-accumulation behavior and define valid-pixel
validation-loss weighting. Use native callbacks/loggers/checkpointing where
possible, with only the small glue required by the scientific contract. Validate on
the disjoint selector subset with deterministic preprocessing. Keep threshold
0.5 and aggregate validation IoU selection, earliest ties. EMA uses decay .999,
first update after optimizer step101, current weights before an average exists,
then averaged validation/best state. Save ordinary and EMA state separately.
Do not blindly reuse the historical
WeightAveraging validation swap: before update 101, validate the current model,
not the initial averaging snapshot. Use Lightning automatic optimization and
verify optimizer-step counting under accumulation.
Match epoch count/effective batch/policy across BC variants and report actual
updates. Local records work offline; W&B is optional and uses the fixed project.
Never open test arrays, including at fit completion.

## Selected starting recipes

The user confirmed these names and ordered model inputs on 2026-11-02:

| Recipe | Ordered band names |
|---|---|
| `planet8` | coastal_blue, blue, green_i, green, yellow, red, rededge, nir |
| `planet4` | red, green, blue, nir |
| `planet3` | nir, red, green (false color) |
| `planet_RGB` | red, green, blue |

These are recipe names, not a change to existing `selection="rgb"` semantics.
Use explicit names through the existing band selector; no separate chip copies.
Task 033D verified three-channel RGB. Add bounded three-channel NIR/R/G coverage
here, preserving native-band validity and selected-band dropout eligibility.

Start from historical `configs/kelp-ps8b/generalization/segformer_b3_v3.yaml`
and its retained optimizer/scheduler implementation:

- Seed 42; 70 epochs; AdamW peak LR 3e-4, betas (0.9, 0.95), weight decay 0.01.
  Preserve the historical exclusion of biases and normalization parameters from
  weight decay; it is implemented in the old model code, not obvious in YAML.
- Microbatch 3, accumulation 8: effective batch 24 on one device, with final
  partial accumulation explicitly tested and reported.
- Linear warmup from zero for five epochs, then cosine decay to 3e-5, stepped
  per optimizer update. Inspect the old scheduler and verify endpoints rather
  than silently changing the schedule when translating to Lightning.
- Gradient norm clipping 0.8; CUDA recipe precision `bf16-mixed`; validation
  every epoch. Historical workers=8, pin_memory=true, persistent_workers=true
  remain explicit machine-adjustable recipe settings.
- SegFormer B3/mit_b3 ImageNet initialization, float32 loss computation,
  0.7 smoothed BCE + 0.3 Lovasz, smoothing 0.1, EMA decay 0.999 with first copy
  after optimizer update 101, and fixed probability threshold 0.5.

Historical values do **not** restore old preprocessing, 1024-sized centered
padding, old augmentation, old run identities, or test-every-epoch evaluation.
Keep the approved 512 input canvas, bottom/right padding, cap=5000 constants,
and reviewed D4 + Affine(p=0.5) + SomeOf(2) Albumentations tensor pipeline.
Keep the tested stock SMP channel initialization for this starting baseline;
a band-aware initialization comparison is a separate future experiment, not
an unrequested model change in this task.

## User decisions required

Lightning, band recipes and historical starting settings are selected. Tiny
CPU smoke settings are separate: float32, workers=0 and a bounded epoch/batch
budget. CUDA memory/batch feasibility remains a GPU-host check. Do not launch
production training on the Mac or open test payloads.

## Smoke and validation

Focused seeded Lightning fitting, scheduler/final accumulation, early EMA
validation,
EMA/current saved-state distinction, pooled metrics, empty support and no-test
access checks. Run a tiny CPU training/validation/save smoke and band/variant
recipe previews. Run affected tests, installed-package and lazy-import checks,
Ruff and broad pre-commit. Leave changes uncommitted for review unless explicitly asked to commit.
No exact-resume or fresh-directory bundle claim yet.

## Acceptance and non-goals

One installed train/dry-run path produces correct local records and separate
best/recovery state with validation-only selection; no full experiment runs.
Do not start another numbered task in this window. The command/modules above are implemented and verified in this task.

## Outcome — 2026-11-02

- **Implementation:** added one strict flat `training/settings.py` schema,
  `module.py` LightningModule, `scheduler.py`, guarded native `ema.py`, thin
  `run.py` Trainer setup and lazy `cli/train.py`. Added four production recipes
  and separate `tiny_cpu.toml`. CLI registration, runtime dependency/lock,
  installed-distribution tests, NIR/R/G data/model coverage and focused
  settings/loop/run tests changed. README, guide, architecture/experiments,
  index, shared decisions and queues now describe implemented training.
  No custom epoch runner, manual optimization, resume API or new bookkeeping
  system was added. Lightning moved from legacy to runtime dependencies;
  retained legacy consumers still need their implementation, so none was removed.
- **Scientific behavior:** existing source selection, train-positive eligibility,
  representative validation, native validity, 512 bottom/right padding, exact
  constants/cap, approved augmentation and objective are reused. Explicit
  NIR/R/G checks preserve RGB selector semantics. Loss runs float32; validation
  loss weights batch objectives by scored pixels with float64 accumulation and
  integer support. TorchMetrics pools confusion counts, threshold stays .5,
  empty support fails, and earliest tied aggregate IoU wins.
- **Framework checks:** the complete 141-point sampled LR sequence matches the
  retained scheduler exactly. LR starts at zero, reaches peak after warmup and
  floor after the final optimizer update. Native automatic optimization with
  five microbatches and accumulation two makes three updates with measured
  gradients 1, 1, .5 for a constant-gradient objective. EMA first copies update
  101 and applies .999 decay at 102; early validation never sees the initial
  averaging snapshot. Checkpoints separate validation `state_dict`, ordinary
  `current_model_state` and `averaging_state`.
- **Checkpoint finding:** installed Lightning 2.6.1's monitored callback with
  `save_last=True` left last stale on an IoU tie in the regression test. Two
  ordinary native callbacks now select best at validation end and save last
  every training epoch. Tests verify best remains the earliest tie while last
  advances. Native WeightAveraging guards are narrowly limited to early swaps,
  early saves and preventing its train-end overwrite of ordinary weights.
- **Validation:** 68 data/model/objective/settings tests pass, including
  sequential real B3 CPU updates for native8, RGB+NIR, RGB and NIR/R/G.
  Another focused invocation passes 58 settings/loop/run/CLI tests (overlapping
  settings coverage), including seven loop tests and three runner tests.
  The 23 CLI/distribution checks pass with isolated wheel and rebuilt-sdist
  runtime installations and lazy imports. Existing augmentation/pipeline/split
  regressions pass (98 tests). Ruff format/check, broad pre-commit and diff
  whitespace checks pass. New files are also explicitly included in pre-commit.
  Changed Markdown file links resolve. No unrelated test failure was observed.
- **Real metadata previews:** all four recipes × both BC variants pass with
  payload reads blocked. With BC: 18,311 candidates, 8,518 eligible, 254 eligible
  sources; without BC: 15,621 candidates, 7,280 eligible, 213 eligible sources.
  Both preserve 933 validation windows and 1,262 test metadata identities.
  Equal 70 epochs imply 24,850 versus 21,280 optimizer updates. The installed
  CLI NIR/R/G dry-run also passes without creating a run folder.
- **Durable external artifacts:**
  `/Volumes/x10pro/kelpseg/analyses/task033e_checks_v1/` contains preview JSON,
  bounded smoke evidence and logs. Successful B3 CPU run:
  `/Volumes/x10pro/kelpseg/runs/task033e-bounded-cpu-v1/` contains settings/run
  records, native CSV and best/last checkpoints (about 1 GiB total). It used
  two epochs, two microbatches/epoch, accumulation two, one validation batch,
  512 inputs and no pretrained download. Two optimizer updates completed;
  six train/validation payload reads passed an explicit allowlist guard.
  Best is epoch 0/update 1; last is epoch 1/update 2. Neither has an EMA average
  yet, as expected. These scores are smoke evidence only.
- **Interrupted smoke input:** archived tiny-v2 manifests remained locally but
  their chip payloads had been evicted. The first attempt stopped on the missing
  training payload and is recorded as failed at
  `/Volumes/x10pro/kelpseg/runs/task033e-tiny-cpu-v1/`. No partial work was reused.
  The successful fresh run uses the same bounded CPU recipe on current release
  payloads. No test arrays were opened by either run. Restoring/rehearsing the
  tiny collection remains part of 033G, not a production prerequisite claimed here.
- **Simplicity and limits:** native Trainer, automatic optimization, callbacks,
  loggers and TorchMetrics own training mechanics. Routine band/machine/budget
  choices use flat recipes and explicit machine paths. CUDA bf16, production
  resource sizing and optional live W&B remain untested locally. ImageNet
  remains the production initialization; smoke intentionally uses no weights.
  There is no production run, exact-resume guarantee or portable-model claim.
  Implementation was left uncommitted for review; commit authorized on 2026-11-03.
- **Exact next action:** select 033F in a new chat to make best models portable
  and verify completed-epoch resume. Stop here before implementing 033F.

## Review follow-up — recipe interface and native metrics

The recipe now owns `variant` and `paths_file`; the latter resolves relative to
the recipe and points to the existing machine-roots TOML. The installed command
needs only `--recipe`, with optional `--dry-run`. Run IDs use UTC timestamps
assigned automatically. Dry runs reserve nothing. This replaces the original
three required/optional command-line settings described by the initial outcome.

Reviewed the retained `src/models/smp.py`: it cloned train/validation metric
collections and routed an extra test loader through validation. The replacement
now logs train and validation IoU, precision, recall, F1 and accuracy directly
through native TorchMetrics collections. Lightning owns pooled epoch computation
and resets. Native MeanMetric handles pixel-weighted train/validation loss;
training also logs batch loss, and SumMetric records validation support. Removed
the manual TN/FP/FN/TP log loop and hand-maintained validation accumulators. The
Python confusion-matrix helper remains available. Test-during-fit is deliberately
not carried over; no test dataset or payload reads were introduced.

Focused tests verify recipe-relative paths from a different working directory,
automatic IDs, metadata-only CLI execution, pooled (rather than mean batch) IoU,
train/validation separation, automatic epoch reset, uneven valid-pixel weighting,
empty validation support and EMA-after-101 metric state. The final combined
settings/run/loop/objective/data/CLI/distribution invocation passes 97 tests,
including isolated wheel/sdist and lazy-import checks. Ruff and pre-commit pass. The recipe-only real-release preview is saved at
`/Volumes/x10pro/kelpseg/analyses/task033e_checks_v1/review_preview.json` with its
external recipe and log; it creates no training output. No additional B3 or
production training was needed for this interface/logging revision.

Changed files in this follow-up: training settings/run/module/metrics and package
docstring, train CLI, five recipes, settings/run/loop tests, README, researcher
guide and this task/queue. Review changes are included in the approved closeout. Next action remains
033F in a new chat; no resume or portable-bundle work was started.

## Recipe naming follow-up — 2026-11-03

Recipes now supply `name` (run-ID prefix) and `experiment` (assignment scope).
The five shipped names match their recipe stems; custom names are validated
as ordinary filename prefixes. Automatic IDs are `<name>-<UTC timestamp>`.
Selection and run metadata read `experiment` from settings; only `baseline`
is supported at this stage, preserving the later fold-specific normalization
boundary for LORO. A descriptive recipe name does not redefine source assignments.
Settings and CLI dry-run tests verify a custom TOML name differing from the
filename, metadata, and invalid settings. All 59 focused settings/run/CLI tests,
Ruff and pre-commit pass. Guide and experiment contract updated.
User approved closure and commit on 2026-11-03; 033F stays next and unstarted.
