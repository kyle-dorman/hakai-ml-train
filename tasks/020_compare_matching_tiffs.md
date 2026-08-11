# Task 020: Compare accuracy on matching source TIFFs

Status: Complete

Depends on: Task 019

Execution: Analysis/report task; no training or prediction.

## Abstract

Compare the temporal baseline with each LORO model on identical source TIFFs
that were unseen by both models, while separately reporting every LORO model's
full held-out-region performance. The default unit is the original TIFF, using
unique-pixel overlap-reconstructed confusion counts from Task 018. This task
must not compare only one aggregate number from differently sized test sets.

## Goal

Produce auditable matched-TIFF tables, per-region summaries, full-region LORO
tables, plots, and a concise interpretation of the geographic-generalization
gap.

## Inputs

- Task 019 suite inventory and all `tiff_metrics.csv`, `region_metrics.csv`, and
  evaluation metadata
- `planet8b_temporal_image_splits.csv`
- Raster manifest for region/date labels
- Baseline and LORO fold manifests
- `docs/product.md`
- `docs/experiments.md`

## Matching contract

For region `R`, a paired comparison TIFF must satisfy:

1. source TIFF region is `R`;
2. source TIFF is `TEST` in the baseline temporal split;
3. baseline result contains that TIFF under the baseline checkpoint;
4. LORO-`R` result contains that TIFF under the held-out-region checkpoint;
5. source shape, scored-pixel mask/coverage contract, label identity, and metric
   schema are compatible.

Join by `source_tiff_id` and `region_id`; never by row order or descriptive
region name. Missing, duplicated, coverage-incompatible, or schema-incompatible
rows are explicit errors or exclusions with reasons.

## User decisions required

Confirm the reporting emphasis after showing a first table mockup:

1. Primary metric. Recommendation: kelp IoU, with kelp recall and precision as
   co-primary diagnostics; accuracy remains secondary because background may
   dominate.
2. Statistical summary. Recommendation: paired TIFF-level differences with
   median, mean, quartiles, and a bootstrap confidence interval by TIFF, but no
   independence-heavy p-value claims because TIFFs may remain spatially and
   temporally correlated.
3. Plot set. Recommendation:
   - paired baseline-versus-LORO TIFF scatter with identity line;
   - per-region paired delta distribution;
   - full-region LORO metric comparison;
   - worst/best matching TIFF table for later qualitative review.
4. Whether to create a standalone Markdown report in addition to CSV/PNG and
   W&B artifacts. Recommendation: yes, concise and tracked only if it becomes
   accepted project evidence; otherwise keep it under external reports.

Record choices before final analysis. Do not select a metric because it makes a
model look better.

Decision recorded 2026-08-10: the user approved the recommended package without
changes: kelp IoU is primary, kelp precision and recall are co-primary
diagnostics, accuracy is secondary, TIFF-level paired differences receive mean,
median, quartiles, and deterministic bootstrap confidence intervals without
independence-heavy p-values, all proposed plots and the best/worst table are
included, and the standalone Markdown report remains an external generated
artifact rather than a tracked project document.

## Output contract

Under a versioned comparison root:

```text
matched_tiff_metrics.csv
matched_tiff_exclusions.csv
paired_region_summary.csv
full_region_loro_summary.csv
pooled_confusion_summary.csv
figures/baseline_vs_loro_scatter.png
figures/paired_delta_by_region.png
figures/full_region_loro_metrics.png
comparison_report.md
comparison_metadata.json
```

`matched_tiff_metrics.csv` contains baseline and LORO confusion counts/metrics
side by side plus deltas, source date, region, scored pixels, coverage, run IDs,
checkpoint hashes, and fold hashes.

## Analysis contract

- Recalculate metrics from stored confusion counts as a consistency check.
- Paired TIFF deltas use each TIFF once per baseline/LORO pair.
- Region-pooled paired metrics sum matched TIFF confusion counts separately for
  baseline and LORO, then derive metrics.
- Full-region LORO summaries use all TIFFs in that held-out region and are
  labeled non-paired.
- Overall pooled results must not allow the largest region to masquerade as
  average region behavior; report both pooled-pixel and equal-region summaries.
- Coverage differences must be zero or explained before metric comparison.
- Do not average chip metrics.

## Plan / spec requirement

Before implementation, add a short plan covering joins/cardinality, compatibility
checks, metric recomputation, paired summaries, bootstrap unit/seed if selected,
plots, W&B artifact/table logging, and report ownership.

## Implementation plan

1. Treat the verified Task 019 suite inventory as the only prediction-package
   entrypoint. Require exactly one completed baseline row and one completed LORO
   row per canonical region, then load the referenced TIFF, region, and metadata
   artifacts without rerunning prediction.
2. Build expected pairs from baseline `TEST` source TIFFs, keyed only by
   `(region_id, source_tiff_id)`. Enforce one-to-one metric rows and check held-out
   region, source shape, scored/covered pixels, coverage, label counts, metric
   schema, threshold, checkpoint identity, and fold identity before admitting a
   pair. Write every absent or incompatible expected pair to the exclusions table
   with an explicit reason; reject unexpected duplicates and wrong-region rows.
3. Recompute accuracy, kelp precision, kelp recall, and kelp IoU from stored
   unique-pixel confusion counts and require agreement with Task 018 metrics.
   Calculate TIFF deltas once per admitted pair, and calculate region-pooled
   metrics only after separately summing baseline and LORO TIFF confusion counts.
4. Summarize TIFF-level paired deltas by region using count, mean, median, and
   quartiles. If the recommended statistical choice is approved, add deterministic
   percentile bootstrap 95% confidence intervals for the mean and median using
   TIFF resampling within region (`10,000` replicates, seed `20260810`), with no
   independence-based p-values. Report pooled-pixel and equal-region summaries
   separately.
5. Produce the approved scatter, paired-delta, and full-held-out-region plots
   strictly from saved tables, plus a best/worst matched-TIFF table in the report.
   A two-region fixture will cover matching, missing, duplicated, wrong-region,
   and coverage-incompatible rows before a one-real-region smoke and full run.
6. Write versioned generated CSV/JSON/PNG/Markdown artifacts outside git under
   `/home/sky/experiments/planet8b-loro-v3/comparisons/matched_tiffs_v1`.
   The repository will track the reusable analysis code, focused tests, and task
   outcome only. Log the compact comparison tables, figures, metadata, and report
   as a W&B artifact/table package only after local validation and only if the
   existing authenticated destination can be verified without changing analysis.

## Smoke test

Build a fixture with two regions, matching/nonmatching TIFFs, duplicate IDs,
coverage mismatch, and known confusion counts. Verify joins, exclusions,
deltas, pooled metrics, and plot generation. Then run one real region before the
full analysis.

## Validation

- Every baseline temporal-test TIFF has either one expected region-specific
  LORO match or an explicit exclusion.
- No train/validation baseline TIFF enters paired comparison.
- No TIFF from the wrong held-out region enters a pair.
- Recomputed metrics agree with Task 018 outputs within tolerance.
- Pooled confusion tables equal sums of their constituent TIFF rows.
- Plot data reconcile to saved tables.
- W&B artifacts identify source run/checkpoint/fold hashes.
- Run focused tests/Ruff for analysis code and `git diff --check`.

## Acceptance criteria

- Matched TIFF results are the primary cross-run comparison.
- Full-region LORO results are clearly separate.
- Primary metric/reporting choices are user-approved and recorded.
- Missing/incompatible pairs are visible, not silently dropped.
- Report states what generalization conclusion is supported and its data limits.
- `docs/todo.md` closes the queue or points to a user-selected follow-up task.

## Non-goals

- Do not retrain, select checkpoints, or retune thresholds.
- Do not compare unmatched aggregate test metrics as if paired.
- Do not claim TIFFs are statistically independent without support.
- Do not expand to architecture or multi-seed comparisons.

## Review pass

- ML researcher: verify paired design, metric choice, aggregation, and claim
  boundary.
- Remote-sensing researcher: verify region/date/coverage interpretation.
- Documentation specialist: verify accepted report versus generated artifact
  ownership.

## Outcome template

Record user reporting decisions, exact inputs/run identities, matched/excluded
counts, artifact paths, headline paired and full-region results, validation,
claim limitations, and recommended next task.

## Outcome

The user approved the recommended reporting package: kelp IoU is primary;
precision and recall are diagnostics; paired TIFF deltas receive mean, median,
quartiles, and deterministic percentile bootstrap intervals without p-values;
all three proposed plots and best/worst TIFF review table are included; and the
standalone report remains an external generated artifact.

Changed repository files:

- `src/evaluation/planet8b_comparison.py` implements strict suite/package
  identity checks, source/fold joins, metric recomputation, pair compatibility,
  explicit exclusions, deterministic TIFF bootstrap summaries, pooled-pixel
  aggregation, and equal-region aggregation.
- `scripts/compare_planet8b_matching_tiffs.py` adds the restart-safe comparison
  CLI, atomic external publication, saved-table-driven plots/report, validation,
  and compact W&B table/artifact logging.
- `tests/test_compare_planet8b_matching_tiffs.py` covers a two-region fixture
  with matched and missing TIFFs, coverage mismatch, duplicate IDs, wrong-region
  rows, known deltas, pooled counts, undefined metric denominators, and figure
  generation.
- `pyproject.toml` and `uv.lock` make Matplotlib a direct plotting dependency.
- `AGENTS.md`, `docs/index.md`, `docs/todo.md`, and `tasks/README.md` close the
  numbered queue and route the next action to a user-selected follow-up.

Durable external artifacts are under:

```text
/home/sky/experiments/planet8b-loro-v3/comparisons/matched_tiffs_v1
```

The root contains all five contracted CSV tables, three PNG figures,
`comparison_report.md`, and `comparison_metadata.json`. It was produced only
from the verified Task 019 inventory at
`/home/sky/experiments/planet8b-loro-v3/predictions/suite_inventory.csv`; no
prediction was rerun and the fixed threshold remained `0.5`. W&B comparison run
`ytpasvud` logged the compact tables and latest
`planet8b-loro-v3-matched-tiff-comparison-v1` artifact in
`kdorman90-ucla/kelpseg`, with all 13 source training/prediction run IDs,
checkpoint hashes, fold hashes, and evaluation identities in metadata.

There are 54 expected temporal-test TIFFs: 53 matched one-to-one across all 12
regions, while `ca_006/006_20220813_181819_2474` is explicitly excluded because
it is absent from both baseline and LORO metric packages. All 53 admitted pairs
have identical selected-chip membership, source shape, coverage accounting, and
label truth counts. TIFF-level kelp IoU is defined for both models in 52 pairs;
undefined denominators remain explicit and do not remove the TIFF from other
paired metrics.

Headline matched results:

- equal-region mean pooled kelp IoU is `0.54474` baseline versus `0.50731` LORO,
  delta `-0.03744`;
- all-pixel pooled kelp IoU is `0.77430` baseline versus `0.74523` LORO, delta
  `-0.02907`;
- mean TIFF-level kelp-IoU delta across the 52 defined pairs is `-0.02685`
  (descriptive 95% bootstrap interval `[-0.04200, -0.01346]`), with median
  `-0.00981`;
- LORO pooled kelp IoU exceeds the baseline in two of 12 matched regions.

Full held-out-region LORO summaries separately cover 364 evaluated TIFF rows.
Their kelp IoU ranges from `0.000` for `ca_007` to `0.815` for `ca_002`; these
non-paired results are not presented as baseline differences.

Validation completed:

- the two-region fixture and one-real-region `ca_001` smoke passed;
- every stored TIFF and region metric was recomputed from confusion counts within
  `1e-12`, and all coverage/confusion totals reconcile;
- all baseline rows are temporal `TEST`, all LORO rows belong to the correct
  held-out region, and every expected TIFF is matched or explicitly excluded;
- a full `--validate-only` replay passed from the original inventory and input
  manifests, and the three saved-table-driven figures passed visual review;
- four focused tests and the full suite (`88 passed`) completed; Task 020 files
  pass Ruff format/check, the changed-file pre-commit gate passes, and
  `git diff --check` passes.

The supported conclusion is bounded to agreement with the supplied labels on
the represented imagery, regions, dates, sensor, preprocessing, model recipe,
and single production seed. TIFF bootstrap intervals are descriptive because
spatial/temporal independence is not assumed. There are no unresolved Task 020
implementation issues. Repository-wide Ruff format/check still reports two
untouched legacy issues in `notebooks/create_skema_aux_files.ipynb` (formatting
and unused loop variables); those out-of-scope notebook cells were preserved.
The first comparison package and W&B run `by673tqn`, which used deterministic
per-region seed offsets, are preserved under
`comparisons/superseded/matched_tiffs_v1_seed_offset_by673tqn` as superseded
evidence; the published v1 package and latest artifact use the approved exact
seed `20260810` for every bootstrap and record producer source hashes. The exact
next action is to stop: the user may select a
qualitative error review, multi-seed replication, or another follow-up, which
must be scoped as a new numbered task before implementation.
