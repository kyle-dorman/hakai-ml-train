# Task 023: Fix center-padded prediction alignment and republish evaluation

Status: Complete

Depends on: Task 022

Execution: Remote/code and prediction/report execution; no training.

## Abstract

Correct the evaluator's spatial alignment for canonical chips smaller than
1,024 pixels. The recorded test transform center-pads those chips, but the
Task 018/022 predictor cropped logits from the top-left. This invalidated
predictions for affected pixels, most visibly every `ca_007` and `ca_011` TIFF.
Publish a clean, separately versioned all-retained prediction suite and rebuild
the matching-TIFF report without changing models, checkpoints, data, or the
fixed threshold.

## User decision

Decision recorded 2026-08-10: fix the alignment, rerun inference, and update the
report. Preserve prior outputs as invalid historical evidence rather than
overwriting them.

## Inputs

- Task 022 code and verified all-retained inventory.
- The same 13 validation-selected v3 checkpoints and fold manifests.
- Recorded deterministic test transforms with centered `PadIfNeeded` and mask
  fill `-100`.
- Fixed threshold `0.5`.

## Implementation contract

1. Crop model probabilities back to the original chip footprint using the
   actual transformed shape and centered padding offsets, then verify that the
   corresponding transformed-mask window exactly equals the original label.
   Refuse transforms whose spatial mapping cannot be proven.
2. Increment the all-retained evaluation schema so old completion identities
   cannot resume under corrected semantics. Give corrected prediction and W&B
   runs distinct v2 identities.
3. Add focused regressions for short and narrow chips with odd padding, plus
   unchanged full-size behavior and an alignment-mismatch failure.
4. Dry-run and rerun all 13 packages from unchanged checkpoints beneath:

   ```text
   /home/sky/experiments/planet8b-loro-v3/predictions_all_retained_v2
   ```

5. Rebuild and validate the report beneath:

   ```text
   /home/sky/experiments/planet8b-loro-v3/comparisons/matched_tiffs_all_retained_v2
   ```

   Compare coverage against Task 022 v1; coverage membership must remain exact.
6. Mark Task 022 v1 prediction/comparison roots as invalid for scientific use
   because of center-padding misalignment. Preserve them unchanged.

## Smoke and validation

- A 674×1,024 chip padded to 1,024×1,024 must crop at row 175 and reproduce its
  training-aligned label footprint.
- A 1,016×725 chip must crop at row 4, column 149.
- Corrected `ca_007` and `ca_011` held-out IoUs must agree with the recorded
  training best-test metrics within expected inference precision.
- All 13 suite entries must verify; all 54 temporal-test TIFFs must pair.
- V1-to-v2 chip, TIFF, covered, scored, ignored, uncovered, and label-truth
  membership must be identical. Only prediction-dependent confusion counts and
  metrics may change.
- Run focused tests, the full test suite, targeted Ruff, changed-file
  pre-commit, `uv lock --check`, Markdown-link validation, and
  `git diff --check`.

## Acceptance criteria

- Small-chip predictions align with their original source pixels.
- Corrected region 7/11 results reconcile to training-time held-out tests.
- The complete v2 prediction suite and report are verified and W&B-identifiable.
- Prior invalid artifacts remain available and are explicitly deprecated.
- No training, threshold tuning, data mutation, or checkpoint change occurs.

## Non-goals

- Do not create new edge-anchored windows or change retained chip membership.
- Do not reinterpret validation metrics as held-out-region metrics.
- Do not silently patch v1 rasters or reports in place.

## Outcome template

Record the root cause and corrected mapping, changed files, old/new artifact
paths, exact run/checkpoint identities, affected/corrected metrics, coverage
identity checks, W&B runs/artifacts, validation, unresolved issues, and exact
next action.

## Outcome

The root cause was confirmed in the production evaluator: the recorded test
transform center-pads undersized chips to 1,024×1,024, while the predictor
returned the top-left output window. Task 023 now derives centered row/column
offsets from transformed and original shapes, verifies that the transformed
label interior exactly equals the original label, and crops probabilities only
after that proof. The all-retained evaluation schema is incremented from 2 to
3, and suite verification requires the expected schema so invalid completions
cannot resume.

Changed repository files:

- `scripts/evaluate_planet8b_run.py` corrects and validates spatial inversion
  and uses distinct `all-retained-v2` W&B names.
- `src/evaluation/planet8b.py` advances the all-retained schema to 3.
- `scripts/run_planet8b_predictions.py` requires schema identity during package
  verification.
- `scripts/compare_planet8b_matching_tiffs.py` requires exact same-scope
  chip/source membership, coverage, ignore, scored, uncovered, and label-truth
  identity against superseded v1 before reporting prediction changes.
- Focused evaluator, runner, and comparison tests cover short/narrow odd center
  padding, full-size behavior, unprovable alignment rejection, schema checks,
  and same-scope identity.
- Routed architecture, artifact, experiment, status, queue, and orientation
  documents make corrected v2 primary and mark prior affected outputs invalid.

The complete corrected prediction suite is rooted at:

```text
/home/sky/experiments/planet8b-loro-v3/predictions_all_retained_v2
```

All 13 packages verify under schema 3 with the same 5,265 chips, 421
package-level TIFF rows, checkpoint hashes, fold hashes, and fixed threshold
`0.5`. Prediction W&B run IDs are `slp2xvnr`, `4h6k3kjg`, `n85epfbw`,
`d3vgqpgl`, `0f55srru`, `r7xhhzr9`, `tuec7z5a`, `yo98mtrz`, `1hqxyush`,
`gb7b73op`, `usbqp94q`, `jkswv1yq`, and `45wcag3l`; the suite inventory is the
authoritative run-to-checkpoint/fold mapping. Local W&B cache evidence was moved
outside git to
`/home/sky/experiments/planet8b-loro-v3/wandb/task023-center-padding-v2`.

V1-to-v2 identity checks pass for every package: exact chip and source sets,
covered/scored/ignored/uncovered/total pixels, and foreground/background label
truth counts are unchanged. Prediction confusion changes are confined to eight
baseline TIFFs, one BC LORO TIFF, all 32 `ca_007` TIFFs, and 10 of 12 `ca_011`
TIFFs. The one undersized `ca_006` chip has no scored foreground and predicts
background under both crops, so its confusion and region metrics are unchanged.

The corrected report is rooted at:

```text
/home/sky/experiments/planet8b-loro-v3/comparisons/matched_tiffs_all_retained_v2
```

It contains all 54 expected matching temporal-test TIFFs with zero exclusions,
the full 367-TIFF LORO summaries, exact v1→v2 membership/coverage evidence,
five CSV analysis tables, three visually verified figures, metadata, and the
Markdown report. W&B comparison run `jn42gtta` logged
`planet8b-loro-v3-matched-tiffs-all-retained-v2`.

The primary human-readable report and the unhighlighted per-TIFF
baseline-versus-LORO chart requested for the final handoff are:

```text
comparison_report.md
  SHA-256 7e732971927da92e6c296930318a2ad6cf6bded460f763f6f6630bf61e51f0a3
figures/baseline_vs_loro_scatter.png
  SHA-256 4f042d8a1ee6ec1ada590a88962f7e84627c68326f2a9605373052544ca89e4c
```

Both remain in the external comparison root under the repository artifact
policy; `comparison_metadata.json` records the same hashes. They are not copied
into git.

The corrected full-region LORO kelp IoUs are `0.50702` for `ca_006`, `0.55898`
for `ca_007`, and `0.38229` for `ca_011`. Regions 7 and 11 now reproduce their
recorded training held-out-test IoUs (`0.55858` and `0.38258`) within `0.0004`.
Their corrected paired temporal-test results are baseline/LORO `0.473/0.436`
for region 7 and `0.578/0.422` for region 11. Region 6 remains `0.210/0.099` on
its six-TIFF paired temporal subset; its `0.7074` training headline was
non-held-out validation, not the region-6 test metric.

Corrected headline matched results are equal-region pooled kelp IoU `0.63730`
baseline versus `0.58333` LORO, delta `-0.05397`; pooled-pixel IoU `0.77255`
versus `0.74921`, delta `-0.02333`. Across 53 pairs with IoU defined for both
models, mean TIFF delta is `-0.03765` with descriptive 95% bootstrap interval
`[-0.05379, -0.02227]` and median `-0.01459`. LORO exceeds baseline pooled IoU
in one of 12 matched regions.

Validation includes 13-package dry-run and verified replay, comparison
`--validate-only`, exact v1→v2 scope/coverage/truth reconciliation, real region
7/11 agreement with training-time held-out metrics, and visual inspection of
all three figures. The full suite passes with `94 passed`; all eight Task
020–023 Python files pass Ruff format/check and `uv lock --check` passes.
Changed-file pre-commit, Markdown links, and diff checks pass at closure.
Repository-wide Ruff retains only the unrelated legacy notebook issues already
recorded by Task 022.

Task 022's `predictions_all_retained_v1` and
`matched_tiffs_all_retained_v1` artifacts, plus the older non-overlap packages,
remain unchanged for audit but are invalid for scientific use on undersized
chips. There are no unresolved Task 023 implementation issues. The exact next
action is to stop; any qualitative error analysis or new edge-window work must
be selected as a new numbered task.
