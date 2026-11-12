# Task 037: Baseline comparisons and leave-one-region-out evaluation

Status: 037A, 037B and 037C complete; 037C is closed. The with-BC epoch-16 EMA remains the
selected 8-band reference. All ten LORO runs and reports are complete, using
unchanged baseline normalization. 037D remains a planning draft.

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

Start after 037C verifies the replacement LORO workflow. Inventory the old
entry points, configs, tests, and dependency group. Remove legacy pieces whose
workflows have replacements, keep the archived references and useful scientific
tests, and preserve the active GPU bootstrap and documented examples. Verify a
fresh frozen install, the full test suite, formatting and lint, and the tiny
prepare, train, predict and report walkthrough. Record the removed code and how
to find the historical workflow in Git. Write the cleanup contract when selected.

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

Next action: review the saved researcher summary when ready to communicate the results;
037D is the next implementation task when selected.


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
