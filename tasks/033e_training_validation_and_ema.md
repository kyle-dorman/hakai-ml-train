# Task 033E: Training, validation and EMA

Status: Next — handoff updated 2026-11-02. Implementation belongs in a new chat.
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

## Outputs and planned interface

Planned `training/settings.py`, a small `training/module.py` LightningModule,
thin Trainer setup and required EMA glue, `cli/train.py`,
`configs/train/planet8.toml`, `planet4.toml`, `planet3.toml`, `planet_RGB.toml`,
`tiny_cpu.toml` and focused training/settings tests. Future command:
`uv run kelpseg train --recipe <file> --paths <file> --variant augmented --run-id <fresh-id> [--dry-run]`.
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
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: 033F: make best models portable and verify completed-epoch resume.
