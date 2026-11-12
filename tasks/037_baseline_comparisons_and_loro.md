# Task 037: Baseline comparisons and leave-one-region-out evaluation

Status: 037A, 037B and 037C complete; 037C is closed. The with-BC epoch-16 EMA remains the
selected 8-band reference. All ten LORO runs and reports are complete, using
unchanged baseline normalization. 037D remains open at the user's request; implementation and validation outcomes are below.

**Researcher summary with example images:**
[read the illustrated summary](/home/sky/data/analyses/task037c-loro-04/results-writeup/results.html)
or [edit the Markdown](/home/sky/data/analyses/task037c-loro-04/results-writeup/results.md).
See [the production outcome](#037c-production-results-and-researcher-summary--2026-11-12)
for evidence and the later communication handoff.

## Abstract

Follow the presentation sequence. First test whether removing British Columbia
(BC) training imagery improves results in the target regions and choose the
8-band reference. Then compare 4-band and 3-band inputs on matching imagery.
Finally measure geographic generalization with leave-one-region-out (LORO)
folds after the baseline and spectral decisions are settled.
Follow with a separate legacy cleanup subtask.

## Inputs and shared rules

- Start with the [plain BCE plus Dice B0 baseline](../docs/experiments.md#current-planet-8-band-b0-baseline),
  the [B0 recipe](../configs/train/model_size/b0.toml), canonical CA/BC v1 chips,
  and the existing source-level assignments. In those assignments, `augmented`
  includes both BC regions (011/012) for training and `base` excludes them.
- Match evaluation sources, labels, and scoreable pixels. Pool the declared
  scope for headline results. Retain source and region confusion counts,
  foreground IoU, precision and recall with label support and coverage.
- Produce a temporal report for the current baseline and every new model,
  including optional runs and each LORO fold. Discuss temporal results alongside
  the segmentation metrics at each comparison.
- Fix recipes, threshold rules and evaluation scope before scoring held-out
  test data. Select checkpoints and any project baseline using validation
  only. Use fresh run identities and save resolved settings, portable models,
  predictions and reports outside Git.
- Use existing `kelpseg train`, `predict-chips`, `predict`, and `report` entry
  points where they fit. Keep each launch sequence explicit and stop on failure.
  Dry-run the recipes and verify a bounded train, predict and report path before
  authorizing a production run. Write the exact commands in each child contract.

## 037A — Train without BC (slide step 2)

The [037A task record](037a_without_bc_launch.md) documents the historical
equal-budget recipe, launch and validation. The comparison used the existing
with-BC B0 bundle and a fresh B0 run with `variant = "base"`. Keep the non-BC source
assignments, 8-band inputs, loss, initialization, batch settings, EMA,
threshold and validation checkpoint rule. Reuse the fixed preprocessing for
the controlled comparison and disclose that its statistics were estimated
with BC imagery. The exclusion applies to model training imagery.

Match planned compute to the existing with-BC reference. It used 8,518 chip
draws, 710 microbatches and 355 optimizer updates per epoch, for a maximum
24,850 updates over 70 epochs. The no-BC split has 7,280 eligible windows.
Draw each once per epoch, select the remaining 1,238 draws from a shuffled
repeat of the same eligible pool, then shuffle the combined draws. Seed the sampling and verify
that it respects the existing completed-epoch resume contract. Match the
five-epoch warmup, full LR schedule, validation cadence, and early-stopping
rule. Before launch, confirm identical validation membership and planned
update counts in the dry run. Report actual updates and the selected checkpoint
for each arm. The with-BC run stopped at 12,780 updates, and the no-BC run may
stop at a different point under the same rule.

Compare on the same validation imagery and evaluation grid. Reuse the saved
with-BC predictions where their scope and coverage match. Present paired
source, regional and temporal results and the effect on the target regions.
The user selected the [with-BC epoch-16 EMA bundle](037a_without_bc_launch.md#baseline-decision)
as the reference for 037B and 037C.

## 037B — Compare 4-band and 3-band inputs (slide step 3)

The [037B task record](037b_spectral_comparison_launch.md) documents the two
spectral recipes and validation results. The user selected the existing 8-band
B0 reference for 037C and skipped the optional false-color DINOv3 comparison.

## 037C — Run LORO comparisons (slide step 4)

This completed contract and its launch commands describe the preserved study.
The task-specific implementation has been retired; see
[implementation recovery](#037c-implementation-retirement--2026-11-12).

Run one 8-band B0 suite using the existing `augmented` assignments for
`loro_001` through `loro_010`. Each fold holds out all source TIFFs in its named
region. BC regions 011 and 012 are eligible for training only, subject to the
same physical spacecraft and UTC acquisition-date exclusions as every other
region. Neither BC region contributes validation or test imagery or defines a
held-out fold. Use the selected with-BC epoch-16 EMA bundle as the baseline.

Extend `kelpseg train --recipe` to consume an explicit fold. Per the user's
2026-11-11 correction, use the selected baseline's existing normalization
values unchanged in every fold; do not compute per-fold statistics. Keep the
5000 raw-unit cap. These values were estimated from the baseline's kelp-positive
training chips, including imagery from the held-out regions. Full-region LORO
therefore holds out model training and checkpoint selection, while reusing the
fixed baseline preprocessing. Check
that both training and validation exclude all held-out-region TIFFs and their
spacecraft/date companions. Keep the model, loss, and evaluation policy fixed
across folds. Record eligible windows and planned and actual optimizer updates
for each fold, since training pool sizes and early stopping can differ.

Validate one tiny fold end to end before any production suite. Check fold
isolation, unchanged baseline statistics, bundle inference, and a matched comparison
where an unmatched TIFF is excluded from the paired table. Then train, predict
and report each approved fold sequentially. Report the full held-out region
for each fold and a separate baseline-versus-LORO table on TIFFs unseen by both
models, using common valid coverage. Compare temporal change on supported
date pairs in that same matched scope. Report full-fold temporal results
separately and record unmatched sources and unsupported pairs.

### 037C implementation contract

Prepare fresh external fold controls and recipes with `examples/task037c.py`;
`examples/run_task037c.sh` runs the ten folds sequentially and stops on failure.
Extend training to select explicit folds while preserving baseline preprocessing.
Keep matched reporting in small ordinary helpers under `reporting/`, using the
existing segmentation and temporal reporters. Verify all ten assignment scopes,
verify unchanged baseline statistics, and run one tiny CPU B0 fit followed by
copied-bundle inference and matched reporting. The tiny example must exclude an
unmatched source. Run focused tests, Ruff and pre-commit before handoff.

No production training is authorized in this preparation window. No additional
user decisions are required. The output is one launch command with prepared
controls, planned budgets, and known report destinations; completed production
results and legacy cleanup remain later work.

## 037D — Retire legacy code

Status: Open — implementation reviewed; do not close without user direction.

### Abstract and inputs

Retire checkout-only Planet workflows now that installed `kelpseg` replacements
are available. The inspected working tree was clean at
`f850a314bd3bb77a6c49375266c627cb379b8f4c`. Inputs are that tree, existing
correctness tests, current recipes and external tiny-v2 data. Stop at cleanup
validation; do not restore the LORO launcher or begin Task 038.

### Implementation contract and outputs

1. Trace consumers and remove the 13 `scripts/` files, root `trainer.py`,
   checkout-only modules outside `src/kelpseg`, `configs/kelp-ps8b/`, and generated
   root `planet8b_temporal_image_splits.csv` once replacements are confirmed.
2. Remove tests solely for obsolete plumbing. Preserve scientific correctness
   coverage of alignment, nodata, padding, overlap, pooled metrics and splits
   against maintained implementations; use fixed expected alignment arrays.
3. Remove the `legacy` dependency group and script import path. Promote W&B
   (current training/GPU login) and OpenCV (augmentation/reporting) to runtime.
   Refresh the lock without unrelated upgrades; explain retained dependencies.
4. Preserve the active GPU bootstrap, installed augmentation preview tools, current TOML recipes,
   installed behavior, historical task evidence and archived checkpoint references.
   Update README/current docs, queue and outcome with replacement commands and
   historical recovery. No new framework or replacement suite launcher.

### User decisions required and non-goals

None. Cleanup, review and a local commit are authorized; keep 037D open. Preserve all external data,
runs, bundles, predictions, reports and unrelated edits. Normalization stays
unchanged. No production training, researcher messages, pushes,
recovery machinery or Task 038. The LORO implementation remains preserved in
`609aa22fe27f2c0f41098b7055321da3ceb62f94`; do not reverse retirement `f850a31`.

### Validation and acceptance

- Fresh external environment: `UV_PROJECT_ENVIRONMENT=<fresh-path> uv sync
  --python 3.12 --frozen`; verify installed CLI and W&B imports.
- Full `uv run --frozen pytest -q`, including isolated wheel/sdist installs.
- `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run pytest -q tests/test_repository_hygiene.py`, Markdown links and
  `git diff --check`.
- External tiny-v2 preparation, bounded CPU training with fixed normalization,
  copied-bundle image-only prediction and labeled report. Record exact commands,
  input/output paths, support counts and limitations in the outcome.
- No `scripts/` directory or live imports of removed modules; preserve current
  GPU/researcher workflows. Record remaining legacy dependencies or blockers.

### Outcome to record

Removed files and consumer/replacement map, retained scientific coverage,
checkpoint/source recovery references, dependency changes, external validation
artifacts, check results, limitations and exact next action. Commit the reviewed
changes locally, leave 037D open, and do not start 038.

## Temporal reporting scope

Temporal consistency means measuring how well predictions reproduce labeled
canopy change between dates on common scoreable footprints.
[Task 036B](036b_temporal_error_analysis.md#full-validation-report--2026-11-05) already
implemented `kelpseg temporal-report` and applied it to 53 saved validation
TIFFs, yielding 62 spatially supported pairs and 61 defined percentage-change
errors. That report used an earlier BCE plus Dice model. Run the reporter on
the current with-BC B0 baseline and all new models. Reuse saved predictions
when the source scope, grid and coverage match, and use tiled TIFF inference
where comparable predictions are missing.

Keep the existing 1–13 and 29–47 day intervals. Compare the same source pairs
on common scoreable pixels at both dates across the models being compared.
Report signed and absolute percentage-point errors, defined pair counts and
coverage by region and interval. Preserve undefined or unsupported cases and
show how much support remains in paired comparisons. Use common unseen TIFFs
for the baseline-versus-LORO temporal comparison.

## Production launch gate

The user confirmed one suite with BC eligible for training and folds for
regions 001–010. Verify one tiny fold end to end before production.

## Acceptance and handoff

Each experiment child records recipes, resolved memberships and budgets,
verified models, segmentation and temporal reports, and the decision needed
by the next child.
The LORO outcome records both full-region and matched-TIFF results with coverage.
Keep the legacy workflow through 037C. Complete the cleanup separately in 037D.

Outcome to record for each child: changed files, durable run/report paths,
checks, decision, remaining limits and exact next action.

Next action: review the uncommitted 037D cleanup. Task 038 remains unstarted;
select and bound its contract in a separate chat. Researcher communication
remains deferred until requested.


## 037C launch preparation outcome — 2026-11-11

The user's final direction supersedes the initial fold-normalization request:
**use the selected baseline's existing normalization unchanged in every fold.**
The attempted per-fold statistics preparation was stopped and discarded. No
new statistics are used, and the original preprocessing, bundle loader and
single-fold pixel-statistics implementation remain unchanged. Full-region
LORO holds out weights training and checkpoint selection, while normalization
retains its known baseline origin, including imagery from held-out regions.
The paired TIFF scope is unseen by both models, including preprocessing inputs.

At the 2026-11-11 launch handoff, production had not started. The single launcher processes `loro_001`
through `loro_010` in order, completing training, full held-out inference,
baseline paired inference and both report types before the next fold.
Any failure stops the sequence; no partial-work reuse or new resume behavior
was added. The fixed B0 loss, ImageNet initialization, batch settings,
70-epoch schedule, five-epoch warmup, augmentation/EMA policy, threshold 0.5
and 20-check early stopping match the selected reference.

### Scope and budgets

All ten folds pass original identity, region/date and spacecraft/UTC-day
isolation checks. Full held-out scope totals 327 TIFFs; 58 TIFFs are unseen
by both models and eligible for paired comparison. Both BC regions remain
training-only. All 42 BC TIFFs are eligible in every fold: none shares a
held-out spacecraft/day. This was checked, not forced.

The reference is the selected with-BC B0 epoch-16 EMA bundle, with eight bands
and threshold 0.5. Its selected checkpoint's saved memberships exactly match
the current 8,518 eligible training windows and 933 validation windows.
`baseline-check.json` records this verification.

| Fold | Eligible training windows | Updates/epoch | Maximum updates |
|---|---:|---:|---:|
| 001 | 7,506 | 313 | 21,910 |
| 002 | 5,710 | 238 | 16,660 |
| 003 | 8,318 | 347 | 24,290 |
| 004 | 7,464 | 311 | 21,770 |
| 005 | 8,145 | 340 | 23,800 |
| 006 | 8,023 | 335 | 23,450 |
| 007 | 8,348 | 348 | 24,360 |
| 008 | 7,109 | 297 | 20,790 |
| 009 | 8,176 | 341 | 23,870 |
| 010 | 8,124 | 339 | 23,730 |

### Exact launch and output locations

Run this once in the existing tmux session:

```bash
bash /home/sky/hakai-ml-train/examples/run_task037c.sh /home/sky/data/analyses/task037c-loro-04
```

Prepared controls live in `/home/sky/data/analyses/task037c-loro-04`:
`fold-plan.csv` summarizes memberships/budgets; each fold contains
`normalization.json` (unchanged reference values), `train.toml`, `preview.json`,
`full.csv`, `paired.csv`, and `labels.csv`. Each preview records its exact fresh
training run ID and output directory under `/home/sky/data/runs/`.

The launcher writes `loro-predictions/`, `baseline-predictions/`, and `reports/`
inside each fold. The six HTML reports are
`reports/{full,paired-loro,paired-baseline}-{segmentation,temporal}/report.html`.
`pairing-coverage.csv` records common coverage; `unmatched.csv` records excluded
TIFFs. Both inference arms use the same tiling and must have identical grids and
finite coverage. Temporal comparison uses identical date pairs and pixels,
with the established 1–13 and 29–47 day intervals.

After all folds, `summary/segmentation.csv` and `summary/temporal.csv` contain
pooled headlines (`region = all`) and per-region rows. Full-region results
remain separate from paired baseline/LORO results. Confusion counts are pooled
before ratios; paired temporal percentage-error headlines use jointly defined
pairs. `sources.csv`, `pairs.csv`, `paired-changes.csv`, and `unmatched.csv`
retain detailed support, undefined/unsupported pairs and exclusions.
`training.csv` records planned/actual updates and selected epochs/weight kinds.

The earlier `task037c-loro-01`, `-02`, and `-03` preparation folders are
abandoned, not runnable suites. Their partial work was never reused. The first
two were interrupted during implementation and the third was stopped when the
user corrected normalization policy. No production run used those controls.

### Implementation, checks and handoff

Fold support and normalization-origin metadata are in `training/settings.py`
and `training/run.py`; assignment checks are in `prepare/splits.py`.
`examples/task037c.py` calls existing training, prediction and reporting
functions; `examples/run_task037c.sh` is the single Bash launcher.
`examples/task037c_smoke.py` provides the bounded CPU rehearsal.
`reporting/loro.py` verifies and reports full/paired scopes;
`reporting/loro_summary.py` pools results and preserves region/date support.
Focused tests cover fixed normalization, copied inference, fold/BC/date
isolation, unmatched exclusion, unequal coverage refusal, pooled counts,
paired temporal support and Bash stop-on-failure behavior.

The final fixed-normalization smoke is saved at
`/home/sky/data/analyses/task037c-smoke-03`. It runs one real CPU B0 optimizer
update, copies the portable bundle and produces all six reports. Three
held-out TIFFs yield 2,880 scoreable pixels and three supported date pairs.
One deliberately baseline-used TIFF is excluded, leaving two paired TIFFs,
1,920 pixels and one supported six-day pair. Its percentage changes are
undefined because the tiny model predicts zero kelp; those cases remain
explicit in the reports. Defined matched-pair behavior is covered by the
reporting tests. Both smoke reporting arms
use the same copied model to test mechanics; these are not scientific scores.

Final verification after the normalization correction: **1,042 tests passed**
(115 existing library/deprecation warnings; no failures), plus 203 focused
training/bundle/split checks. All ten generated recipes were checked against
the exact baseline mean/std values. The installed fold-001 CLI dry-run passed;
none of the ten planned production run directories existed at that handoff. Bash syntax, Ruff
format/lint, pre-commit (including explicit new untracked files), local Markdown
link targets and `git diff --check` passed.

```bash
uv run python examples/task037c.py prepare /home/sky/data/analyses/task037c-loro-04
uv run python examples/task037c.py smoke /home/sky/data/analyses/task037c-smoke-03
uv run kelpseg train --recipe /home/sky/data/analyses/task037c-loro-04/loro_001/train.toml --dry-run
uv run pytest -q
bash -n examples/run_task037c.sh
uv run ruff format --check .
uv run ruff check .
uv run pre-commit run --all-files
git diff --check
```

The preparation and smoke commands above record completed verification; do not
rerun them into those existing directories. Logs are
`/home/sky/data/analyses/task037c-prepare-04.log` and
`/home/sky/data/analyses/task037c-smoke-03.log`. Production subsequently completed; the Bash command above is retained as
historical launch evidence and must not be rerun into the existing outputs.

The [quickstart](../docs/quickstart.md#completed-loro-study)
contains the operating recipe. Routine use relies on flat external settings
and machine paths. Legacy code remains for separately scoped 037D. Changes
remain uncommitted. Production results and actual stopping points are recorded
in the outcome below. Box backup of the new artifacts remains unverified.


## 037C production results and researcher summary — 2026-11-12

All ten folds completed successfully, exported EMA bundles and produced full
held-out and matched baseline segmentation/temporal reports. The completed
suite is `/home/sky/data/analyses/task037c-loro-04`; pooled and per-region
tables are in `summary/`. All models retain the exact baseline normalization.

On the same 58 unseen TIFFs and 316,137,041 scoreable pixel observations,
baseline/LORO foreground IoU was 74.05%/73.19%, precision 85.40%/86.06%,
and recall 84.77%/83.04%. IoU decreased in nine regions; region 003 had the
largest decrease (8.58 points), while 002 improved by 1.05 points. Full-region
LORO IoU across all 327 TIFFs was 73.88%; this separate scope is not a paired
baseline comparison.

For matched 1–13 day changes, mean absolute percentage-change error was
16.55/20.08 points (baseline/LORO; 41 supported, jointly defined pairs).
For 29–47 day changes it was 23.53/19.21 points (26 pairs), but the median
worsened from 14.53 to 20.68 points. The long-interval mean improvement is
driven mainly by three region-004 pairs; 18 of the 26 pairs come from region
008. Counts, unavailable pairs and per-region results remain explicit.

### Saved summary for later researcher communication

The report is saved outside Git at
`/home/sky/data/analyses/task037c-loro-04/results-writeup/`:

- [Illustrated HTML summary](/home/sky/data/analyses/task037c-loro-04/results-writeup/results.html):
  readable standalone document with the figure embedded.
- [Editable Markdown summary](/home/sky/data/analyses/task037c-loro-04/results-writeup/results.md):
  same narrative, pooled/regional tables, methods and interpretation.
- [Region 003 example figure](/home/sky/data/analyses/task037c-loro-04/results-writeup/region003-examples.png):
  three matched crops from April 7, 19 and 29, 2021, with imagery, supplied
  labels, baseline and LORO errors.
- [Portable folder archive](/home/sky/data/analyses/task037c-loro-04/results-writeup.zip):
  both document formats, figure, exact example source/window record and
  copied segmentation, temporal and training source tables.

The examples were deliberately selected to show LORO failures, not to represent
all imagery. Selection details and per-crop confusion counts are in
`example-sources.json`. The report states the normalization origin, matched
pixel/date scope, sparse and overlapping temporal support, and supplied-label
claim boundary. It does not use test results to change model selection.

This follow-up changed the task record and discovery pointers in
`docs/index.md`, `docs/todo.md`, and `tasks/README.md`; implementation and
production artifacts were not changed. Numbers were checked against the saved
CSV tables, source/crop metadata and completed run/report records. The example
figure was visually inspected, embedded assets and local links checked, and
`git diff --check` passed. No new model inference or training was needed.

Exact next action: when the user is ready, draft a message to the other
researchers using the saved summary and images. Nothing has been sent or
scheduled; the user explicitly deferred communication. 037D remains the next
implementation task when separately selected. Box backup remains unverified,
and repository edits were uncommitted at the summary handoff; see the later
closure and retirement commits below.


## 037C closure and implementation preservation — 2026-11-12

The user closed 037C and requested a Git snapshot of the completed workflow
before retiring its task-specific code. This snapshot preserves the launcher,
preflight/smoke drivers, paired reporting, training integration, tests, methods
and results history. Generated data, models and the illustrated summary remain
at the external paths above. The preservation commit is
`609aa22fe27f2c0f41098b7055321da3ceb62f94`. Recovery commands are recorded below.

The authorized follow-up retires the 037C examples, suite-specific reporting
helpers and fold special cases in training run/settings. Shared preparation
isolation checks and generic prediction/reporting remain useful. This is a
bounded 037C cleanup, not the broader 037D legacy retirement.


## 037C implementation retirement — 2026-11-12

**Preservation commit: `609aa22fe27f2c0f41098b7055321da3ceb62f94`**
(`Close Task 037C and preserve completed LORO workflow`). This is the complete
snapshot to inspect or recover: it contains the launcher, preparation/smoke
drivers, suite reporting, fold training integration, tests and task history.
The subsequent cleanup commit removes these one-off consumers from the maintained
checkout. No production models, predictions, reports or researcher-summary
artifacts were removed.

Inspect the history without changing the current checkout:

```bash
git show --stat 609aa22fe27f2c0f41098b7055321da3ceb62f94
git show 609aa22fe27f2c0f41098b7055321da3ceb62f94:examples/run_task037c.sh
git show 609aa22fe27f2c0f41098b7055321da3ceb62f94:examples/task037c.py
git show 609aa22fe27f2c0f41098b7055321da3ceb62f94:src/kelpseg/reporting/loro.py
```

For a complete source copy, extract the preserved tree into a **fresh** directory:

```bash
mkdir /absolute/fresh-loro-source
git archive 609aa22fe27f2c0f41098b7055321da3ceb62f94 | tar -x -C /absolute/fresh-loro-source
```

The archived source requires the external data/model paths recorded in this
task. Its generated recipes and output paths under `task037c-loro-04` describe
the completed study, not empty destinations for another launch.

Removed: `examples/run_task037c.sh`, `examples/task037c.py`,
`examples/task037c_smoke.py`, `reporting/loro.py`, `reporting/loro_summary.py`,
and their task-specific launcher/reporting/training tests. Restored ordinary
baseline-only training in `training/run.py` and `training/settings.py`.
Preserved source-assignment isolation checks and moved their correctness tests
into `tests/test_splits.py`. Unrelated augmentation examples and generic
training, prediction, segmentation and temporal reporting remain available.

Current docs now point to historical recovery instead of advertising the removed
launcher. This closes 037C and its bounded implementation cleanup; the wider
037D legacy removal remains a separate task when selected. The next optional
researcher-facing action is to draft a message from the saved illustrated
summary when requested. Nothing has been sent or scheduled.


Cleanup validation: all **1,024 tests passed**, plus 171 focused settings,
training, split and bundle checks. Ruff format/check, pre-commit, Markdown
link targets and `git diff --check` passed. The preserved commit was checked
to contain every retired source file. A real region-003 portable bundle and
a copy in a fresh temporary directory produced identical probabilities on
4,096 valid pixels using the current generic loader. This verifies that the
archived training integration is not needed to use the completed models.

Both the preservation snapshot and the subsequent cleanup are local Git
commits; nothing has been pushed. The full preservation commit above is the
reference for recovering the original LORO workflow.


## 037D cleanup outcome — 2026-11-12

### Inventory, consumers and replacements

The initial checkout was clean at `f850a314bd3bb77a6c49375266c627cb379b8f4c`.
Consumer tracing found no legacy imports in `src/kelpseg`, the active GPU
bootstrap, augmentation examples or maintained TOML recipes. The old scripts,
class-path YAML configs and checkout-only `src.*` modules formed a closed
workflow; their remaining consumers were obsolete tests and historical docs.

| Removed paths/workflow | Maintained replacement or retirement reason |
|---|---|
| `scripts/merge_planet8b_regions.py`, `validate_planet8b_raw_merge.py`, `planet8b_metadata.py` | Installed `kelpseg organize`, `check`, `clean` and explicit catalog/source metadata |
| `scripts/analyze_planet8b_nodata.py`, `src/prepare/` | `check --full`, canonical chip manifests and manifest-selected training exclusions; keep canonical backgrounds |
| `scripts/materialize_planet8b_folds.py`, root `planet8b_temporal_image_splits.csv` | `kelpseg split`, current split rules and external assignments; no hard-linked views |
| `scripts/package_planet8b_dataset.py` | Ordinary rclone transfer/backup recipes and external releases; no package/receipt framework |
| `trainer.py`, `src/data.py`, `src/models/`, `src/callbacks.py`, `src/schedulers.py`, `src/losses.py` | `kelpseg train --recipe <TOML>` and installed training, EMA, model and loss functions |
| `scripts/build_planet8b_run_context.py`, `run_planet8b_experiments.py`, `src/run_context.py`, all 12 `configs/kelp-ps8b/` YAML files | Installed flat recipes and ordinary run metadata; historical suite launcher retired |
| `scripts/evaluate_planet8b_run.py`, `run_planet8b_predictions.py`, `compare_planet8b_matching_tiffs.py`, `src/evaluation/` | `kelpseg predict`, `predict-chips`, `report`, `temporal-report`; completed specialized paired comparisons remain saved/archived |
| `scripts/benchmark_planet8b_batch_size.py` | Retired old class-path benchmark; current GPU sizing guidance and bounded `train` recipes remain in `docs/gpu_setup.md` |
| `scripts/create_planet8b_region_footprints.py` | Unconsumed old-manifest helper; no current CLI promises dissolved footprint export, so no new replacement was invented |
| `src/__init__.py`, obsolete `.gitignore` family exceptions, pytest `scripts` import path | Installed package is the maintained import surface |

The entire `scripts/` directory is gone, including its ignored bytecode cache.
No installed production module or normalization value changed. Kept
`bootstrap_gpu.sh`, both augmentation examples/tools, current TOML configs,
all external originals/releases/runs/checkpoints/bundles/predictions/reports,
and the immutable Task 025 checkpoint/reference evidence and Task 027 backup
references. The root generated split CSV remains recoverable in Git and in
Task 032A's external controls; current assignments are not modified.

Removed twelve legacy-only test files: `test_analyze_planet8b_nodata.py`,
`test_compare_planet8b_matching_tiffs.py`, `test_epoch_test_diagnostics.py`,
`test_evaluate_planet8b_run.py`, `test_materialize_planet8b_folds.py`,
`test_merge_planet8b_regions.py`, `test_package_planet8b_dataset.py`,
`test_remove_bg_only_tiles.py`, `test_run_context.py`,
`test_run_planet8b_experiments.py`, `test_run_planet8b_predictions.py`, and
`test_validate_planet8b_raw_merge.py`. Their plumbing is no longer supported.

Scientific regression coverage remains in the installed suites: organizer,
check/clean and alignment tests replace merge/validation fixtures; chip/split/
training-data tests cover inclusive nodata boundaries, retained backgrounds,
identity joins and disjoint evaluation; prediction/reporting/validation-report/
chip-loading/model-bundle tests cover padding inversion, overlap averaging
before thresholding, unique-pixel counts, ignored/uncovered pixels, pooled
confusion and undefined ratios. `test_prepare_alignment.py` retains its exact
expected grid and six historical trace cases without importing the retired
implementation. `test_training_loop.py` retains warmup/cosine numeric landmarks.
Epoch-wise held-out test diagnostics are intentionally not retained: current
training selects on validation and reports held-out predictions separately.

### Dependencies and historical recovery

`pyproject.toml` removes the `legacy` group and default-group override.
W&B and directly used OpenCV move to runtime dependencies for current training,
GPU login, augmentation and reporting. `uv.lock` drops `jsonargparse`,
`docstring-parser`, `typeshed-client` and `importlib-resources`, with no retained
package upgrades. NumPy remains direct; Hugging Face Hub, torchvision, tqdm
and PyYAML remain required transitively by supported ML/tracking libraries.
There is no remaining legacy-only dependency group or implementation blocker.
The distribution test now expects W&B availability and jsonargparse absence.

Inspect all pre-037D source without changing this checkout:

```bash
git show f850a314bd3bb77a6c49375266c627cb379b8f4c:trainer.py
git show f850a314bd3bb77a6c49375266c627cb379b8f4c:scripts/evaluate_planet8b_run.py
mkdir /absolute/fresh-pre-037d-source
git archive f850a314bd3bb77a6c49375266c627cb379b8f4c | tar -x -C /absolute/fresh-pre-037d-source
```

This recovery copy is historical source, not a current supported installation.
The separate 037C LORO preservation commit remains
`609aa22fe27f2c0f41098b7055321da3ceb62f94`; retirement commit `f850a31` was
not reversed. Original starting history remains `ac933fd`. Current portable
bundles need none of the removed source; historical Lightning checkpoints are
not automatically converted to current bundles.

Changed supporting docs: README, documentation index, quickstart, architecture,
product, artifact policy, task table and queue. Routine researcher changes still
use flat settings and explicit installed commands; the quickstart contains the
replacement map. No production training was launched and no researcher messages were sent.


### External walkthrough and validation evidence

Successful bounded rehearsal: `/home/sky/data/analyses/task037d-walkthrough-03/`.
The input is the existing real tiny-v2 collection at
`/home/sky/data/data/examples/tiny_ca_bc/v2`. `run.sh` contains the exact
stop-on-failure sequence; `walkthrough.log` records its completed execution:

```bash
bash /home/sky/data/analyses/task037d-walkthrough-03/run.sh
```

This is a historical verification command; do not rerun into these occupied
outputs. The script invokes installed `split`, `chip`, `train --dry-run`,
`train`, `predict`, and `report`, with external flat recipes and copied-bundle
verification between training and prediction. For a new attempt use fresh
paths in every recipe. Thirteen real TIFF crops produce 54 retained chips
(151,535,749 payload bytes). Selection contains 20 training candidates,
11 kelp-positive eligible training windows, 2 validation, 7 test and 25 unused.
The B0 fit performs one CPU optimizer update and one validation batch with
random initialization; it is a mechanics check, not a scientific score.
Eight-band mean/std and the 5000 cap exactly match the unchanged baseline.

The saved run is
`runs/task037d-tiny-b0-20261112T170535651070Z/` under that walkthrough root.
`copied-model/` produces identical probabilities on 4,096 pixels. Image-only
prediction processes the documented 768×768 validation TIFF with four overlapping
windows, covering all 589,824 valid pixels. `report/report.html` is complete,
with 589,824 scoreable pixels and no nodata, ignored pixels or coverage gaps.
The two earlier attempts, `task037d-walkthrough-01` and `-02`, stopped on
external driver mistakes (overbroad recipe substitution and a helper named
`copy.py` shadowing the standard library). Each restarted in a fresh directory;
no partial output was reused and no repository defect was found by these stops.

Fresh frozen environment created at
`/home/sky/data/analyses/task037d-validation/environment` with Python 3.12.11
and 113 installed packages. Imports of `kelpseg`, W&B and OpenCV passed;
jsonargparse is absent. Validation logs are saved in the parent directory.

```bash
UV_PROJECT_ENVIRONMENT=/home/sky/data/analyses/task037d-validation/environment uv sync --python 3.12 --frozen
UV_PROJECT_ENVIRONMENT=/home/sky/data/analyses/task037d-validation/environment OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 CUDA_VISIBLE_DEVICES='' WANDB_MODE=offline HF_HUB_OFFLINE=1 NO_ALBUMENTATIONS_UPDATE=1 uv run --frozen pytest -q
uv lock --check
uv run --frozen ruff format --check .
uv run --frozen ruff check .
uv run --frozen pre-commit run --all-files
git diff --check
```

The focused scientific suite passed 238 tests. The first full run passed 954
tests and found one stale distribution assertion: model-library `timm` imports
W&B when present. The assertion now permits this supported runtime integration
while keeping preparation lazy-import checks and retired-module exclusions.
`pytest.log` preserves that failure; `pytest-final.log` records the final run.


Final full-suite result: **955 passed, 92 library/deprecation warnings**, including
both isolated wheel and sdist installations. No unresolved test failure remains.
Ruff format/check and pre-commit pass. All 305 relative Markdown file targets
and 132 anchors in current docs, the task router and Task 037 resolve;
`git diff --check` passes. All 53 deleted files were verified present in the
pre-cleanup commit. Installed package source, GPU bootstrap, augmentation
examples and training recipes have no diff; retained lock versions are unchanged.

### Limits and exact next action

037D is complete and all changes remain uncommitted for review. No production
training, external source mutation, researcher communication, commit or push
was performed. The tiny CPU run validates mechanics only; production throughput
was not remeasured. Backup of the previously completed LORO/new analysis roots
remains unverified, as already recorded; cleanup did not change Box or claim a
new backup. No legacy-only dependency or cleanup blocker remains.

Exact next action: review and commit the 037D diff when desired. Task 038 is the
next implementation slot, but is **not started**: select it separately and write
its bounded new-region recipe contract. Researcher messaging stays deferred.


## 037D preview CLI follow-up — 2026-11-12

Status: Complete. The user requested installed `preview-augmentations` and
`preview-pipeline` commands and removal of the two example launchers. Preserve
all existing uncommitted cleanup. Add thin lazy-import handlers in
`src/kelpseg/cli/previews.py`, explicit path/sample/seed options and pipeline draw
count; retain existing function defaults, selection, normalization and rendering.
Remove only the two tracked example files, update current docs and exercise
real bounded galleries through the CLI plus invalid inputs and lightweight help.
Run relevant preview/distribution tests, Ruff and pre-commit. No Task 038 work,
production training or commits. Outcome and validation follow below.


Follow-up outcome: added `src/kelpseg/cli/previews.py` and registered both
commands with lazy imports. Required options are `--chips`, `--assignments`
and `--output`. Preserved defaults: augmented variant, seed 33, 14 positive
samples plus two background controls; pipeline draws default to 8. Numeric
bounds match the existing functions. Commands log progress, print `index.html`,
report ordinary errors and restore caller logging. Removed both example Python
files and the now-empty `examples/` directory. Augmentation implementations,
selection, display, trial constructors and normalization have no changes.

README, quickstart, architecture and index now describe installed commands,
including running from another directory through an active environment or
`uv run --project /absolute/path/to/hakai-ml-train kelpseg ...`. The earlier
037D statements about preserving example launchers describe the initial cleanup;
this explicit user-requested follow-up supersedes them while retaining the tools.

Existing bounded gallery tests now invoke both commands from a separate working
directory, retaining training-only payload checks, unchanged-input checks and
rendered metadata/normalization assertions. Tests cover bad paths, occupied
outputs, numeric options, logging restoration and help without heavy imports.
Both isolated wheel/sdist installs exercise command help and missing-input errors.
The focused preview/augmentation/CLI/distribution run passed 98 checks and exposed
one outdated CLI-help assertion expecting no preview command. After updating it,
all 26 package-CLI tests passed. Thus all 99 selected tests pass across the two
runs; no unresolved failure remains. Logs: `preview-cli-tests.log` and
`preview-cli-help-tests.log` in `/home/sky/data/analyses/task037d-validation/`.
Ruff format/check, pre-commit (including the new untracked handler explicitly),
current Markdown links/anchors and `git diff --check` pass. The earlier full
955-test validation remains recorded above; this follow-up used focused checks.

All earlier uncommitted changes are preserved. No new training, production
artifacts or dependencies were introduced. Exact next action: review the
uncommitted cleanup and CLI follow-up together; Task 038 remains unstarted.


## 037D validation tooling follow-up — 2026-11-12

Status: Complete. Replace pre-commit with existing Ruff/pytest validation,
per the user's request. Remove `.pre-commit-config.yaml` and the dev dependency;
retain syntax/debug checks through Ruff and repository file checks through
`tests/test_repository_hygiene.py`. Check tracked and nonignored untracked files,
skip deleted files and lockfiles, and report without rewriting. Update CI,
README and AGENTS validation instructions; preserve historical task evidence.
Validate the checker, frozen install, full tests and Ruff. Preserve all previous
uncommitted work; no commits, hooks, training or Task 038 changes.


Implementation: removed `.pre-commit-config.yaml` and the dev dependency.
The lock removes pre-commit plus cfgv, distlib, identify, nodeenv,
python-discovery and virtualenv, without upgrading retained packages.
PyYAML is now declared directly in dev for repository YAML checks (it was
already installed transitively). Ruff `T100` replaces debugger-statement checks;
Ruff already checks Python syntax and formatting. `tests/test_repository_hygiene.py`
checks JSON/YAML/TOML parsing, merge markers, 500 KiB size limit, mixed line
endings, trailing whitespace and final newlines. It reads tracked and nonignored
untracked files, skips symlinks/deleted files/lockfiles, reports paths/errors,
and never rewrites files. File-size checks now cover all selected files rather
than only newly added files. It is one ordinary pytest test with focused fixtures
for malformed files and Git selection, not a new command framework.

CI includes hygiene in its normal pytest step and retains Ruff checks. README
and AGENTS give the same local validation path; historical pre-commit results
are retained as evidence, not current instructions. No hook is installed or
required, and no user Git hooks were changed. The focused checker passed all
11 tests; a Ruff probe confirmed a debugger call produces T100; frozen sync and
`uv lock --check` passed, and `pre_commit` is absent from the environment.


Validation outcome: **968 tests passed**, including repository hygiene and both
isolated distribution installs, with 92 existing library/deprecation warnings.
Full output is `/home/sky/data/analyses/task037d-validation/no-precommit-tests.log`.
Ruff format/check and `git diff --check` pass. No unresolved blocker remains.
The exact current commands are:

```bash
uv run --frozen pytest -q
uv run --frozen ruff format --check .
uv run --frozen ruff check .
```

For a quick file-only check, use
`uv run --frozen pytest -q tests/test_repository_hygiene.py`.
All previous cleanup and preview CLI edits remain uncommitted. Exact next
action: review the combined 037D changes; Task 038 remains unstarted.


## 037D review and commit — 2026-11-12

The user requested review of the complete cleanup and follow-ups, authorized a
local commit if sound, and explicitly requested that 037D remain open. This
supersedes the earlier uncommitted-only handoffs and completion status. No push
or Task 038 work is authorized. The current task remains 037D after committing.

Independent reviews checked legacy consumers/dependency removal/scientific test
coverage and the preview CLI/repository checker. No legacy-removal or preview
behavior blocker was found. Review reproduced one checker gap: malformed
UTF-8 or NUL-containing JSON/YAML/TOML could be skipped as binary. Known config
formats now reject those inputs; focused regressions also verify binary assets
remain allowed. Current routers have been corrected to keep 037D open.


Final review validation: **975 tests passed**, with 92 existing library warnings,
including isolated wheel/sdist installs and 18 checker regressions. Log:
`/home/sky/data/analyses/task037d-validation/review-final-tests.log`.
Ruff format/check, lock consistency, current Markdown links/anchors and diff
whitespace checks pass. Every removed file remains recoverable from `f850a31`;
retained package versions and scientific/augmentation implementations are
unchanged. No unresolved review findings remain. The reviewed changes are
ready for the authorized local commit. **037D remains open** for the user's
next direction; do not push, close the task or start 038.
