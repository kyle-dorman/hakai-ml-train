# Task 014B: Correct the generalization-suite model config

Status: Complete

Depends on: Tasks 013 and 014A

Execution: Configuration, bounded systems benchmark, and validation task; no
experiment training or Task 014 smoke launch.

## Abstract

Task 014 selected `configs/kelp-ps8b/california/segformer_b3.yaml` as the
baseline/LORO model config. Before launching the replacement-host smoke suite,
the user clarified that the intended scientific baseline is the later recipe in
`configs/kelp-ps8b/segformer_b3.yaml`. That recipe added linear warmup plus
cosine decay, 70/30 label-smoothed cross-entropy/Lovasz weighting, and EMA, but
also retains settings that conflict with the current all-region contract. Its
ImageNet initialization uses SMP's generic multispectral adaptation: the three
RGB input filters repeat cyclically across eight channels and are scaled by
`3/8`, while the deeper encoder retains its pretrained weights. The user chose
to preserve that established behavior for this baseline; a PS8B-aware input
projection is deferred to the backlog.

Create one dedicated generalization-suite config that preserves the intended
root PS8B training recipe while applying explicitly approved safety and
current-suite corrections. Before fixing its runtime batch settings, benchmark
micro-batch/accumulation pairs with constant effective batch size 24. Update the
Task 014 matrix and documentation to use that config, implement a tiered smoke
that deeply exercises EMA on the baseline and one LORO fold without spending
two full epochs on every fold, validate all 13 smoke and production resolutions,
and stop before launching training.

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
2. Preserve the root recipe's SegFormer B3 architecture, existing SMP ImageNet
   initialization behavior for eight input bands, AdamW settings,
   linear-warmup/cosine-decay scheduler, 70/30 label-smoothed
   cross-entropy/Lovasz weighting, and EMA behavior. Do not add a custom input
   projection to the current baseline.
3. Use exactly 100 epochs with no early stopping for the comparable production
   suite; smoke budget and batch-limit overrides are runner-owned and never
   apply to production.
4. Use label ignore index `-100` for canonical nodata and every transform-made
   black or padded mask area. Do not train artificial padding or dropout holes
   as class-0 background.
5. Keep one validation-selected best checkpoint plus local `last.ckpt`.
6. Use the current `kdorman90-ucla/kelpseg` W&B contract, comparison/smoke
   grouping, and runner-injected per-fold names and paths.
7. Retain other current runtime improvements that do not change the intended
   scientific recipe, including isolated output roots and asynchronous
   checkpoint I/O if compatibility validation passes.

The user has also approved these runtime-validation decisions:

1. Keep effective batch size fixed at 24 while benchmarking exact divisor pairs
   `(micro_batch_size, accumulate_grad_batches)` of `(3, 8)`, `(4, 6)`,
   `(6, 4)`, `(8, 3)`, `(12, 2)`, and `(24, 1)`. Select the fastest stable pair
   with at least 15% A40 memory headroom under the complete training recipe,
   including EMA. Record throughput and peak allocated/reserved memory for all
   attempted pairs; OOM candidates fail individually rather than aborting the
   benchmark. This is a systems choice, not metric tuning.
2. Run a two-epoch full smoke for the temporal baseline and `loro-bc-v1`. BC is
   the representative LORO fold because it exercises the non-California data
   path and has enough optimizer steps for EMA to update during epoch two. Run
   the other 11 LORO entries as shallow one-epoch smokes with bounded train,
   validation, and test batches: process exactly two optimizer updates' worth
   of training micro-batches after applying accumulation, then two validation
   and two test batches. This is sufficient to instantiate and step the full
   stack, calculate validation metrics, and write/test a checkpoint. Do not
   interpret smoke metrics as model-quality evidence.

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

- retain eight input bands, SegFormer `mit_b3`, the root config's
  `encoder_weights: imagenet` behavior, and AdamW `lr = 3e-4`, weight decay
  `0.01`, and betas `[0.9, 0.95]`;
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
- use the benchmark-selected batch size and accumulation pair while keeping
  their product exactly 24; retain workers, precision, normalization, and
  non-mask augmentation settings unless validation exposes an incompatibility;
- use current baseline-view paths as safe defaults even though the runner
  injects the correct fold paths before instantiation; and
- contain exactly one W&B logger and one `ModelCheckpoint` callback so Task 013
  validation remains enforceable.

Do not silently carry legacy `/home/taylor` paths, `hakai/kelp-ps8b` W&B
identity, May 2026 grouping, two-best-checkpoint policy, or early stopping into
the dedicated config.

## Plan / spec requirement

### Reconciliation recorded before implementation

| Field | Root recipe versus California config | Decision |
|---|---|---|
| Architecture and initialization | Both use SegFormer `mit_b3`, eight inputs, and SMP `encoder_weights: imagenet`. | Preserve intended root scientific recipe and its established cyclic SMP multispectral adaptation. |
| Optimizer | Both use AdamW at `3e-4`, weight decay `0.01`, and betas `[0.9, 0.95]`. | Preserve intended root scientific recipe. |
| Scheduler | Root uses five-epoch linear warmup plus cosine decay to `3e-6`; California uses OneCycleLR. | Preserve intended root scientific recipe. |
| Loss | Root explicitly weights label-smoothed CE/Lovasz `0.7/0.3`; California leaves weights implicit. | Preserve intended root scientific recipe with ignore index `-100`. |
| EMA | Root enables `EMAWeightAveraging`; California omits it. | Preserve intended root scientific recipe. |
| Transforms and normalization | Non-mask augmentation and eight-band normalization otherwise match; root uses unsafe mask fill `0` in crop, dropout, and padding. | Preserve non-mask recipe; replace every artificial mask fill with the approved `-100` current-suite contract. |
| Data paths | Both historical configs use stale dataset roots. | Runner-owned; use the current temporal-baseline view as the safe default. |
| Batch runtime | Both use micro-batch 3 and accumulation 8. | Select from the approved constant-effective-batch benchmark; product must remain 24. |
| Epochs and stopping | Root uses 250 epochs plus early stopping; California uses fixed 100 epochs without early stopping. | Replace with approved fixed 100-epoch current-suite contract and no early stopping. |
| Checkpointing | Root keeps two best checkpoints and `last`; California keeps one best and `last` with asynchronous I/O. | Replace with one best plus local `last.ckpt`; retain asynchronous checkpoint I/O if compatible. |
| W&B | Root uses legacy identity and model upload; California uses the current destination with runner-safe defaults and `log_model: false`. | Replace with current `kdorman90-ucla/kelpseg` contract; run identity remains runner-owned. |
| Smoke budget | Neither source config represents tiered smoke. | Runner-owned: two full epochs for baseline and BC; one bounded epoch for all other LORO folds. |

No unresolved recipe incompatibility was identified before implementation.

Before editing, write a short field-by-field reconciliation of the root and
California configs. Classify every difference as one of:

- preserve intended root scientific recipe;
- replace with an approved current-suite contract;
- runner-owned and therefore only a safe config default; or
- unresolved incompatibility requiring user review.

Then implement only the recorded reconciliation. Do not use held-out test
results to choose any setting.

Before choosing the runtime pair, add or use a bounded, non-W&B benchmark that:

- runs each candidate in a fresh process against real baseline training chips;
- uses the final transforms, bf16 precision, forward/backward pass, optimizer,
  gradient accumulation, and EMA memory footprint;
- processes the same number of samples and optimizer updates after warmup for
  every candidate;
- records failures, samples/second, optimizer-step time, and CUDA peak
  allocated/reserved memory in the task outcome; and
- creates no checkpoint, W&B run, registry event, or durable experiment run.

The benchmark must not use validation or test metrics, and it must not change
the effective batch size, optimizer, scheduler, loss, or augmentation recipe.

## Smoke and validation

Add focused tests or assertions that load the dedicated YAML and verify its
scientific and safety invariants, including scheduler, loss weights, EMA,
`-100` mask fills, retained ImageNet encoder setting, effective batch size 24,
fixed production budget, absence of early stopping, checkpoint policy, W&B
destination, and eight-band input.

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
- the baseline and `loro-bc-v1` deep-smoke entries resolve to two full epochs;
- the other 11 LORO entries resolve to one bounded epoch with explicit train,
  validation, and test batch limits;
- production resolves to 100 epochs;
- baseline and all 12 LORO paths are injected correctly;
- current W&B identity/group/name/job type are injected correctly;
- checkpoint roots are isolated under the fresh experiment namespace; and
- no training process, W&B run, registry event, or checkpoint is created.

The runner currently has one global `smoke_max_epochs` and returns from
`--dry-run` before writing a resolved config. Task 014B may make the smallest
runner/matrix change needed to represent the two smoke tiers and expose or test
pure config resolution without instantiating training or W&B. Production must
remain uniform across all 13 entries.

Replace the now-misleading unused
`planet8b-loro-v1-smoke-1epoch-v3` identity with
`planet8b-loro-v1-smoke-tiered-ema-v1`. Before doing so, verify and record that
no real `v3` registry event exists. If any real `v3` event is found, preserve it
as historical evidence and still use the new tiered identity; never reuse one
identity across different model-config hashes or smoke budgets.

## Acceptance criteria

- A dedicated generalization SegFormer B3 config exists and is the sole
  smoke/production model config in the matrix.
- It preserves the user-selected root PS8B scientific recipe, including its
  existing SMP eight-band ImageNet adaptation, and applies every approved
  current-suite adjustment above.
- A reproducible benchmark selects a stable batch/accumulation pair whose
  product is 24, with recorded throughput and at least 15% A40 memory headroom.
- All black/padded mask pixels introduced by transforms use `-100`.
- The suite uses 100 fixed production epochs, no early stopping, one best
  checkpoint, local `last.ckpt`, and current W&B metadata.
- Focused config-contract checks pass.
- All 26 runner dry-runs resolve the correct config, paths, hashes, tiered-smoke
  limits, production budgets, checkpoint roots, and W&B context.
- The smoke matrix uses `planet8b-loro-v1-smoke-tiered-ema-v1`, with no real
  event silently reassigned from an older identity.
- No smoke or production training has started.
- Task 014 records the exact clean restart command and final smoke identity.

## Non-goals

- Do not launch Task 014 smoke runs or Tasks 015–016 production runs.
- Do not tune the recipe using validation or held-out test results.
- Do not change or compare encoder initialization within this baseline task.
- Do not compare batch candidates using segmentation metrics.
- Do not change dataset membership, fold policy, nodata threshold, background
  selection, chip geometry, or label remap.
- Do not mutate or delete the two historical source configs.
- Do not clean unrelated legacy configs or notebooks.

## Review pass

- ML scientist: confirm the dedicated config preserves the intended root
  scheduler, loss balance, EMA, optimizer, normalization, and augmentation
  recipe without test-driven tuning, including the deliberately retained SMP
  ImageNet adaptation for eight input bands.
- Risk-averse engineer: verify all artificial mask fill is `-100`, early
  stopping is absent, batch benchmarking preserves effective batch size 24,
  tiered smoke reaches EMA updates in both deep entries, checkpoint/W&B
  contracts are current, and no real run state exists under a reused config
  identity.
- Software architect: verify runner-owned overrides remain centralized and the
  dedicated config is the single matrix source for all 13 folds.

## Outcome template

Record the reconciliation decision table, preserved initialization decision,
batch benchmark method/results/selection, changed repository files, final
config path and SHA-256, tiered-smoke identity and limits, all focused and
runner validation, unresolved issues, confirmation that no experiment training
launched, and the exact Task 014 restart command.

## Outcome

Task 014B created the dedicated generalization config at
`configs/kelp-ps8b/generalization/segformer_b3_v1.yaml` with SHA-256
`132695ae361c5e5e1b4d3fc6acf1dd910d88d1f05dfe985f8f44d0269aaba9c9`.
It preserves the root recipe's SegFormer B3 architecture, SMP ImageNet
initialization for eight inputs, AdamW settings, linear-warmup/cosine-decay
scheduler, 70/30 label-smoothed CE/Lovasz loss, normalization, augmentation,
and EMA. Approved suite corrections set every artificial mask fill to `-100`,
fix production at 100 epochs without early stopping, retain one best plus
local `last.ckpt`, use the current W&B destination, and retain compatible
asynchronous checkpoint I/O. Neither historical source config was changed.

The reproducible benchmark in `scripts/benchmark_planet8b_batch_size.py` ran
each approved pair in a fresh process against real baseline training chips.
Every successful candidate used one warmup and three measured optimizer
updates (72 measured samples), bf16, final transforms, the complete loss,
optimizer and scheduler, accumulation, and the EMA callback; logging and
checkpointing were disabled. Results on the 46,068 MiB NVIDIA A40 were:

| Micro / accumulation | Status | Samples/s | Seconds/update | Peak allocated | Peak reserved | Reserved headroom |
|---|---:|---:|---:|---:|---:|---:|
| 3 / 8 | selected | 3.348 | 7.168 | 23,264,441,856 B | 23,764,926,464 B | 50.18% |
| 4 / 6 | eligible | 3.120 | 7.692 | 30,649,898,496 B | 31,478,251,520 B | 34.00% |
| 6 / 4 | ineligible | 2.958 | 8.114 | 45,463,442,944 B | 46,850,375,680 B | 1.77% |
| 8 / 3 | OOM | — | — | — | — | — |
| 12 / 2 | OOM | — | — | — | — | — |
| 24 / 1 | OOM | — | — | — | — | — |

The selected production pair is therefore micro-batch 3 and accumulation 8:
it is the fastest stable candidate and exceeds the required 15% headroom. The
durable external report is
`/home/sky/experiments/planet8b-loro-v1/benchmarks/task014b_batch_benchmark.json`
with SHA-256
`44cbedbf8c278292983bb9425a58f88da727169d9fd9f605259b5124542c59d1`.
It is benchmark evidence, not an experiment run.

The matrix now uses the dedicated config for both smoke and production. Its
fresh smoke identity is `planet8b-loro-v1-smoke-tiered-ema-v1`. No registry
file existed beneath `/home/sky/experiments/planet8b-loro-v1` before the
change, confirming that no real `planet8b-loro-v1-smoke-1epoch-v3` event was
reassigned. Baseline and `loro-bc-v1` resolve to two full epochs. Each other
LORO fold resolves to one epoch with 16 train micro-batches (two optimizer
updates at accumulation 8), two validation batches, and two test batches.
Production remains 100 uncapped epochs for all 13 entries.

Changed repository files:

- `configs/kelp-ps8b/generalization/segformer_b3_v1.yaml`
- `configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml`
- `scripts/benchmark_planet8b_batch_size.py`
- `scripts/run_planet8b_experiments.py`
- `tests/test_run_planet8b_experiments.py`
- active routing/status documentation and Tasks 014/014B handoff records

Validation passed:

- nine focused runner/config tests;
- Lightning CLI parse of the dedicated config;
- explicit EMA, one-checkpoint, and `AsyncCheckpointIO` instantiation;
- all 13 smoke and all 13 production dry-runs against real fold artifacts;
- smoke model hash, tier limits, fold paths, W&B identity, and isolated roots;
- `uv run ruff format --check scripts tests`;
- `uv run ruff check scripts tests`;
- scoped pre-commit hooks for every Task 014B file;
- `git diff --check`.

Dry-runs returned before writing resolved configs or contexts. The benchmark
created no W&B run, checkpoint, registry event, or experiment training run.
Repository-wide Ruff format/check additionally reports only two pre-existing
legacy-notebook issues outside this task: formatting drift in
`notebooks/create_skema_aux_files.ipynb` and
`notebooks/export_skema_models_onnx.ipynb`, plus two unused loop indices in the
former. The scoped checks and pre-commit hooks pass, and the legacy notebooks
were not changed. There are no unresolved Task 014B issues. The exact next
action is to resume Task 014's smoke suite with:

```bash
uv run python scripts/run_planet8b_experiments.py \
  --matrix configs/kelp-ps8b/generalization/experiment_matrix_v1.yaml \
  --registry /home/sky/experiments/planet8b-loro-v1/experiment_registry.jsonl \
  --pending --smoke
```
