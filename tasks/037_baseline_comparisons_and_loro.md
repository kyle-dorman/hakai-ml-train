# Task 037: Baseline comparisons and leave-one-region-out evaluation

Status: 037A complete. The user selected the with-BC epoch-16 EMA baseline. Later tasks remain planning drafts.

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
- Match evaluation sources, labels, and scoreable pixels. Keep CA regions and
  Baja (001/002) visible separately. Use source and region confusion counts,
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

Use the selected 037A reference and the same variant, source membership,
training budget and B0 recipe. Prepare planned `b0_planet4.toml` and
`b0_planet3.toml` under `configs/train/baseline_comparisons/`. Use the existing
Planet 4-band red/green/blue/NIR and Planet 3-band false-color NIR/red/green
band orders and their matching normalization entries. Train both from the same initialization policy
as the reference and score all three models on matching imagery.

The [Task 033G tiny walkthrough](033g_tiny_walkthrough_and_handoff.md) already
exercised these spectral inputs. Production comparisons remain open. Verify
the new recipes resolve to the expected bands, shared assignments and budget,
and check that a copied bundle predicts on a tiny source with the correct bands.
The 8-band reference remains the baseline by default. Review results before
deciding whether any spectral variant should inform 037C.

### Optional false-color DINOv3 follow-up

Decide after the 3-band results. If selected, write a separate bounded contract
for a DINOv3 run on false-color NIR/red/green. Use the 037B 3-band B0 run as
its control, with matching imagery and band order from the
[Planet 3-band recipe](../configs/train/planet3.toml). Agree on the model,
how pretrained inputs are adapted, training budget and runtime checks at that
point. Record whether the optional result changes the recipe going into 037C.

## 037C — Run LORO comparisons (slide step 4)

Start after 037A and 037B decisions are recorded and the optional DINOv3 branch
is complete or skipped. Default to the selected baseline variant and spectral
recipe. A second BC variant across all folds is a separate production scope
for the user to choose after the earlier results.

Reuse existing `loro_001` through `loro_010` assignments. Extend
`kelpseg train --recipe` to consume an explicit fold, with training-only
normalization computed from that fold through `kelpseg pixel-stats`. Allow no
held-out region or held-out spacecraft/date companion in training or validation.
Keep the selected loss, model and evaluation rules fixed across folds.

Validate one tiny fold end to end before any production suite. Check fold
isolation, fold-specific statistics, bundle inference, and a matched comparison
where an unmatched TIFF is excluded from the paired table. Then train, predict
and report each approved fold sequentially. Report the full held-out region
for each fold and a separate baseline-versus-LORO table on TIFFs unseen by both
models, using common valid coverage. Compare temporal change on supported
date pairs in that same matched scope. Report full-fold temporal results
separately and record unmatched sources and unsupported pairs.

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

## User decisions required

- After 037B, decide whether to run false-color DINOv3 and freeze the recipe
  for LORO.
- Before LORO production, decide whether to run only the selected BC variant
  or both. Confirm the scope and launch only after the tiny fold passes.

## Acceptance and handoff

Each experiment child records recipes, resolved memberships and budgets,
verified models, segmentation and temporal reports, and the decision needed
by the next child.
The LORO outcome records both full-region and matched-TIFF results with coverage.
Keep the legacy workflow through 037C. Complete the cleanup separately in 037D.

Outcome to record for each child: changed files, durable run/report paths,
checks, decision, remaining limits and exact next action.

Next action when selected: write the 037B contract using the [selected 8-band reference](037a_without_bc_launch.md#baseline-decision).
