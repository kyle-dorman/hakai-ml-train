# Task 014B: Correct the generalization-suite model config

Status: Pending

Depends on: Tasks 013 and 014A

Execution: Configuration and validation task; no training.

## Abstract

Task 014 selected `configs/kelp-ps8b/california/segformer_b3.yaml` as the
baseline/LORO model config. Before launching the replacement-host smoke suite,
the user clarified that the intended scientific baseline is the later recipe in
`configs/kelp-ps8b/segformer_b3.yaml`. That recipe added linear warmup plus
cosine decay, 70/30 label-smoothed cross-entropy/Lovasz weighting, and EMA, but
also retains settings that conflict with the current all-region contract.

Create one dedicated generalization-suite config that preserves the intended
root PS8B training recipe while applying the current dataset, ignore-index,
fixed-budget, checkpoint, W&B, and runner contracts. Update the Task 014 matrix
and documentation to use that config, validate all 13 smoke and production
resolutions, and stop before launching training.

## Goal

Make the model recipe used by the baseline and every LORO fold scientifically
intentional, self-consistent, and immutable before Task 014 restarts.

## Inputs

- Intended baseline recipe: `configs/kelp-ps8b/segformer_b3.yaml`
- Previously selected config:
  `configs/kelp-ps8b/california/segformer_b3.yaml`
- Experiment matrix:
  `configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml`
- Current dataset and training contracts in `docs/architecture.md` and
  `docs/experiments.md`
- Task 014 runner and resolved-config behavior
- Canonical replacement-host views beneath
  `/home/sky/data/planet8b_all_regions_1024_512_v2/views`

## User decisions required

The user has approved these decisions:

1. The intended scientific baseline is the later root PS8B SegFormer B3 recipe,
   not the California-specific config.
2. Preserve the root recipe's SegFormer B3 architecture, ImageNet encoder
   initialization, AdamW settings, linear-warmup/cosine-decay scheduler,
   70/30 label-smoothed cross-entropy/Lovasz weighting, and EMA behavior.
3. Use exactly 100 epochs with no early stopping for the comparable production
   suite; smoke runs use the same recipe with only the runner-owned one-epoch
   budget override.
4. Use label ignore index `-100` for canonical nodata and every transform-made
   black or padded mask area. Do not train artificial padding or dropout holes
   as class-0 background.
5. Keep one validation-selected best checkpoint plus local `last.ckpt`.
6. Use the current `kdorman90-ucla/kelpseg` W&B contract, comparison/smoke
   grouping, and runner-injected per-fold names and paths.
7. Retain other current runtime improvements that do not change the intended
   scientific recipe, including isolated output roots and asynchronous
   checkpoint I/O if compatibility validation passes.

No further user decision is required unless EMA and asynchronous checkpointing
prove incompatible or a proposed adjustment would change the scientific recipe
beyond the choices above.

## Planned files and config contract

Create a dedicated config rather than mutating either historical source config:

```text
configs/kelp-ps8b/generalization/segformer_b3_v1.yaml
```

Update both `model_config` and `smoke_model_config` in
`configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml` to that file.

The new config must:

- retain eight input bands, SegFormer `mit_b3`, ImageNet encoder weights,
  AdamW `lr = 3e-4`, weight decay `0.01`, and betas `[0.9, 0.95]`;
- retain `src.schedulers.LinearWarmupCosineDecayLR`, five warmup epochs, minimum
  LR `3e-6`, and step interval;
- retain `LabelSmoothingLovasz` with CE weight `0.7`, Lovasz weight `0.3`, and
  ignore index `-100`;
- retain `src.callbacks.EMAWeightAveraging`;
- set mask fill to `-100` for `RandomCrop`, `PadIfNeeded`, and
  mask-affecting black/dropout transforms;
- use 100 epochs, no `EarlyStopping`, `save_top_k = 1`, and `save_last = true`;
- use the current W&B entity/project/group defaults with `log_model = false`,
  leaving per-run identity and paths to validated run-context injection;
- retain batch size, workers, precision, accumulation, normalization, and
  non-mask augmentation settings unless validation exposes an incompatibility;
- use current baseline-view paths as safe defaults even though the runner
  injects the correct fold paths before instantiation; and
- contain exactly one W&B logger and one `ModelCheckpoint` callback so Task 013
  validation remains enforceable.

Do not silently carry legacy `/home/taylor` paths, `hakai/kelp-ps8b` W&B
identity, May 2026 grouping, two-best-checkpoint policy, or early stopping into
the dedicated config.

## Plan / spec requirement

Before editing, write a short field-by-field reconciliation of the root and
California configs. Classify every difference as one of:

- preserve intended root scientific recipe;
- replace with an approved current-suite contract;
- runner-owned and therefore only a safe config default; or
- unresolved incompatibility requiring user review.

Then implement only the recorded reconciliation. Do not use held-out test
results to choose any setting.

## Smoke and validation

Add focused tests or assertions that load the dedicated YAML and verify its
scientific and safety invariants, including scheduler, loss weights, EMA,
`-100` mask fills, fixed budget, absence of early stopping, checkpoint policy,
W&B destination, and eight-band input.

Run:

```bash
uv run pytest tests/test_run_planet8b_experiments.py
uv run ruff format --check scripts tests
uv run ruff check scripts tests
git diff --check
```

Dry-run all 13 smoke entries and all 13 production entries. Inspect generated
or programmatically resolved configs—not only the matrix JSON summaries—to
verify:

- the dedicated config hash is recorded in every run context;
- smoke changes only the epoch budget to one;
- production resolves to 100 epochs;
- baseline and all 12 LORO paths are injected correctly;
- current W&B identity/group/name/job type are injected correctly;
- checkpoint roots are isolated under the fresh experiment namespace; and
- no training process, W&B run, registry event, or checkpoint is created.

If the base config changes after any real `v3` registry event exists, choose a
new smoke experiment identity rather than reusing an identity for a different
model-config hash. If no real `v3` event exists, record that evidence before
deciding whether the unused `v3` identity remains valid.

## Acceptance criteria

- A dedicated generalization SegFormer B3 config exists and is the sole
  smoke/production model config in the matrix.
- It preserves the user-selected root PS8B scientific recipe and applies every
  approved current-suite adjustment above.
- All black/padded mask pixels introduced by transforms use `-100`.
- The suite uses 100 fixed production epochs, no early stopping, one best
  checkpoint, local `last.ckpt`, and current W&B metadata.
- Focused config-contract checks pass.
- All 26 runner dry-runs resolve the correct config, paths, hashes, budgets,
  checkpoint roots, and W&B context.
- No smoke or production training has started.
- Task 014 records the exact clean restart command and final smoke identity.

## Non-goals

- Do not launch Task 014 smoke runs or Tasks 015–016 production runs.
- Do not tune the recipe using validation or held-out test results.
- Do not change dataset membership, fold policy, nodata threshold, background
  selection, chip geometry, or label remap.
- Do not mutate or delete the two historical source configs.
- Do not clean unrelated legacy configs or notebooks.

## Review pass

- ML scientist: confirm the dedicated config preserves the intended root
  scheduler, loss balance, EMA, optimizer, normalization, and augmentation
  recipe without test-driven tuning.
- Risk-averse engineer: verify all artificial mask fill is `-100`, early
  stopping is absent, checkpoint/W&B contracts are current, and no real run
  state exists under a reused config identity.
- Software architect: verify runner-owned overrides remain centralized and the
  dedicated config is the single matrix source for all 13 folds.

## Outcome template

Record the reconciliation decision table, changed repository files, final
config path and SHA-256, smoke identity decision, all focused and runner
validation, unresolved issues, confirmation that no training launched, and the
exact Task 014 restart command.
