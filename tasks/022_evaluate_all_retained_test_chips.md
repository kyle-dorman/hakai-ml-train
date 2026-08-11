# Task 022: Evaluate all retained test chips with overlap stitching

Status: Complete

Superseded for scientific use by Task 023: schema-2 prediction outputs
top-left-cropped centered padding for undersized chips. The v1 artifacts remain
audit evidence only.

Depends on: Tasks 018–020

Execution: Remote/code and prediction/report execution; no training.

## Abstract

Replace the non-overlapping evaluation-input subset with every canonical chip
that survives the universal nodata policy and belongs to the relevant test
source scope. Average foreground probabilities across overlapping 512-stride
windows on the original source grid, threshold once at the unchanged value
`0.5`, and recompute the complete baseline/LORO prediction and matching-TIFF
comparison suites under new versioned artifact roots.

This is a prediction-coverage correction, not a model, checkpoint, threshold,
label, preprocessing, or training change. Tasks 018–020 remain immutable
historical evidence of the non-overlapping-input evaluation.

## User decision

Decision recorded 2026-08-10: use all valid post-nodata chips for inference and
evaluation, stitch their overlapping probabilities into one source-TIFF grid,
and rerun the paired comparison. The user explicitly identified the missing
valid overlap chips and approved the common remote-sensing sliding-window
pattern.

## Inputs

- Verified Task 019 training registry, checkpoints, fold manifests, canonical
  chip manifest, raster metadata, and suite identities.
- Existing overlap-aware probability accumulator and TIFF metric logic from
  Task 018.
- Task 020 comparison implementation and reporting decisions.
- Fixed binary threshold `0.5`; no threshold tuning is permitted.

## Evaluation-scope contract

For each run, include every row in the canonical post-nodata fold manifest that
belongs to the run's test source scope:

- temporal baseline: `source_temporal_split == TEST`;
- LORO region `R`: `region_id == R` and the row is either the selected held-out
  test row or its recorded `held_out_region_overlap_exclusion` counterpart.

The resolver must admit the existing selected non-overlapping test chips plus
only the corresponding overlap-exclusion rows. It must reject training,
validation, other-region, unused temporal-test, background-policy, or unknown
selection reasons. Join by manifest identity, never folder contents or row
order.

Every admitted chip is already part of the post-nodata canonical collection.
Do not restore chips removed by the 50% nodata policy.

## Reconstruction contract

- Predict every admitted 1,024-pixel chip at its recorded source offset.
- Average foreground probabilities once per covered source pixel.
- Threshold the averaged source probability once at `0.5`.
- Score covered, non-ignore pixels once; overlapping chip confusion counts stay
  diagnostic and non-additive.
- Retain probability, mask, coverage, TIFF, region, and suite accounting.
- Record `evaluation_scope = all_retained_test_chips` and a new evaluation
  schema/identity so old completions cannot be resumed as new output.
- Explicitly report remaining uncovered pixels. Existing canonical chips use
  full windows only for dimensions at least 1,024, so final trailing edge strips
  outside the 512-stride grid remain out of scope for this task.

## Outputs

Preserve all Task 019–020 artifacts. Write new outputs beneath:

```text
/home/sky/experiments/planet8b-loro-v3/predictions_all_retained_v1
/home/sky/experiments/planet8b-loro-v3/comparisons/matched_tiffs_all_retained_v1
```

The prediction root contains 13 run packages and a verified suite inventory.
The comparison root contains the same table/figure/report contract as Task 020,
with all-retained evaluation scope and source prediction identities recorded.
Use distinct W&B prediction/comparison names and artifact identities; do not
overwrite or relabel previous W&B evidence.

## Implementation plan

1. Extract a strict, testable fold-scope resolver shared by evaluation and the
   prediction-suite runner. Record selected and overlap-chip counts separately.
2. Add the evaluation-scope identity to metadata, summaries, completions, CLI,
   W&B context, and suite verification so cross-scope resume is impossible.
3. Extend focused fixtures for overlapping chip selection, probability
   averaging, coverage expansion, forbidden-reason rejection, and the
   `ca_006/006_20220813_181819_2474` regression.
4. Dry-run all 13 suite entries and quantify chip/TIFF/coverage scope before GPU
   work. Run a real bounded regression, then execute/resume all 13 packages from
   the existing validation-selected checkpoints.
5. Adapt the comparison CLI to accept the new run/scope identity without
   weakening its strict joins. Generate a separately versioned report and log
   compact W&B evidence.
6. Update the product, architecture, artifact, and experiment contracts so
   all-retained overlap stitching becomes the primary evaluation policy while
   the earlier non-overlapping artifacts remain historical.

## Smoke and validation

- Fixture: two overlapping chips with known probabilities must yield the known
  averaged source prediction and unique-pixel confusion counts.
- Scope fixture: selected test plus permitted overlap rows are admitted;
  train/validation/wrong-region/unknown-reason rows fail.
- Real regression: `ca_006/006_20220813_181819_2474` must receive selected chips
  and produce compatible baseline and LORO TIFF metrics.
- Every expected temporal-test source with at least one retained canonical chip
  must appear in the baseline package and its region LORO package.
- For every source, all-retained coverage must be at least historical coverage;
  any equality or remaining uncovered pixels must reconcile to chip geometry.
- Recomputed TIFF/region/test metrics and pooled comparison counts must
  reconcile exactly as in Tasks 018 and 020.
- Run focused tests, the full test suite, Task 022 Ruff/pre-commit checks, and
  `git diff --check`; preserve unrelated legacy notebook issues.

## Acceptance criteria

- All valid post-nodata test chips contribute to overlap-averaged inference.
- The previously excluded `ca_006` temporal-test TIFF is present in both sides
  of the paired comparison.
- New prediction and report artifacts are complete, verified, separately
  versioned, and W&B-identifiable.
- The report quantifies coverage gains and remaining grid-edge limitations.
- No training, checkpoint selection, threshold tuning, or canonical data
  mutation occurs.
- Task outcome records changed files, external artifacts, validation, results,
  limitations, unresolved issues, and exact next action.

## Non-goals

- Do not restore >50% nodata chips.
- Do not create new dynamically edge-anchored windows or rechip source rasters.
- Do not retrain models or change preprocessing/model configuration.
- Do not compare overlapping chip metrics as independent observations.

## Outcome template

Record exact scope rules, old/new chip and coverage counts, run/checkpoint/fold
identities, the `ca_006` regression result, external paths, W&B runs/artifacts,
headline paired/full-region results, validation, remaining uncovered-edge
limits, changed files, unresolved issues, and exact next action.

## Outcome

The evaluator now has two explicit, non-interchangeable scopes. Historical
`selected_nonoverlap` behavior remains schema 1. Primary schema 2
`all_retained_test_chips` evaluation admits baseline rows whose source split is
`TEST` and LORO rows from the held-out region, but only when each row is either
the selected test row or its recorded test-overlap exclusion. Unknown reasons,
other regions, and training/validation rows fail closed. The evaluator averages
foreground probabilities across all admitted windows per source pixel and
thresholds once at the unchanged value `0.5`.

Changed repository files:

- `src/evaluation/planet8b.py`, `scripts/evaluate_planet8b_run.py`, and
  `scripts/run_planet8b_predictions.py` add the shared scope resolver, schema-2
  identity, strict resume/verification checks, selected-versus-overlap counts,
  and distinct prediction/W&B identities.
- `src/evaluation/planet8b_comparison.py` and
  `scripts/compare_planet8b_matching_tiffs.py` enforce the selected evaluation
  scope, compare historical/current coverage, require source-level
  non-regression, and publish a separately identified report.
- `tests/test_evaluate_planet8b_run.py` and
  `tests/test_compare_planet8b_matching_tiffs.py` cover permitted and forbidden
  scope rows, overlap averaging/unique-pixel accounting, and coverage changes.
- `AGENTS.md`, `README.md`, the routed product, architecture, artifact,
  experiment, index, and TODO documents, and this task queue record the new
  primary policy while preserving Tasks 019–020 as historical evidence.

Durable prediction artifacts are rooted at:

```text
/home/sky/experiments/planet8b-loro-v3/predictions_all_retained_v1
```

Its verified inventory contains all 13 expected packages, the original
checkpoint and fold-manifest hashes, and 5,265 test chips: 1,513 selected
non-overlap rows plus 3,752 admitted overlap rows. The baseline package grows
from 185 to 663 chips and from 53 to all 54 temporal-test TIFFs. The 12 LORO
packages contain all 367 held-out-region source TIFFs. Prediction W&B run IDs
are `ettvn4t6`, `5tj5b9hb`, `9umz3rn7`, `s3xln2i3`, `ewlyzzgm`, `249ue6z3`,
`p3mkcagg`, `uen2w3xm`, `xffl565h`, `r1ogzhea`, `uuapr7ht`, `cwb6kela`, and
`4z5e2usb`; the inventory is the authoritative mapping from each ID to its run,
checkpoint, fold, and output path.

The previously missing `ca_006/006_20220813_181819_2474` is recovered by three
retained overlap chips in both applicable packages. Baseline and LORO now
reconstruct exactly 2,097,152 covered pixels, score the same 1,532,285 label
pixels, and report the same 564,867 ignored and 5,687,839 uncovered pixels.
Their kelp IoUs are `0.15549` and `0.14089`, respectively. This confirms that
its earlier exclusion caused the 53-of-54 result: it had no chip on the selected
non-overlapping grid, not an invalid image or label.

Durable comparison artifacts are rooted at:

```text
/home/sky/experiments/planet8b-loro-v3/comparisons/matched_tiffs_all_retained_v1
```

All 54 expected temporal-test TIFFs match one-to-one and none is excluded. The
comparison includes the contracted CSV tables, three figures, report,
metadata, and the new historical-versus-current coverage table. W&B run
`usyvece2` logged the compact package as
`planet8b-loro-v3-matched-tiffs-all-retained-v1`. An earlier Task 022
comparison publication without the coverage table is preserved, clearly
superseded, at
`comparisons/superseded/matched_tiffs_all_retained_v1_without_coverage_lm7oizmo`.

Coverage increases for every package that has admitted overlap rows, with no
shared-TIFF regression. Baseline covered pixels increase by 95,152,640 and its
represented-grid coverage rises from 47.0% to 69.1%. Across all 13 package
outputs, covered-pixel counts increase by 702,010,368. `ca_007` and `ca_011`
are unchanged because their fold manifests contain no eligible overlap rows.

Headline matched results are an equal-region pooled kelp IoU of `0.54959` for
the baseline versus `0.51184` for LORO, delta `-0.03775`; pooled-pixel kelp IoU
is `0.76885` versus `0.74622`, delta `-0.02264`. Across the 53 pairs where IoU
is defined for both models, mean TIFF-level delta is `-0.02404` with descriptive
95% bootstrap interval `[-0.03781, -0.01150]` and median `-0.00740`. LORO
exceeds baseline pooled IoU in one of 12 matched regions. Full-region LORO
results remain separately reported across 367 TIFF rows.

Validation completed during execution includes dry-run and verified-resume
checks for all 13 packages, exact per-source coverage reconciliation against
the historical inventory, the recovered-`ca_006` regression, comparison
`--validate-only` replay, saved-table reconciliation, and visual inspection of
all three figures. The full behavioral suite passes with `90 passed`; the seven
Task 020/022 Python files pass Ruff format/check, the changed-file pre-commit
gate passes, `uv lock --check` passes, all local Markdown links resolve, and
`git diff --check` passes. Repository-wide Ruff still reports only untouched
legacy notebook debt: two notebooks would be reformatted, and two unused loop
variables remain in `notebooks/create_skema_aux_files.ipynb`. Those unrelated
notebooks were preserved.

No source data, training run, checkpoint selection, model setting, or threshold
was changed. Remaining uncovered pixels are real limitations of the existing
canonical footprints: principally trailing source-edge strips not reached by a
full 1,024-pixel window at 512 stride, plus areas represented only by chips
removed under the fixed nodata policy. Creating dynamically edge-anchored
windows would require a new task and new prediction inputs. There are no
unresolved Task 022 implementation issues. The exact next action is to stop;
any qualitative error review, edge-window extension, multi-seed replication,
or other follow-up must be selected and scoped as a new numbered task.
