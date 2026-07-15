# Task 019: Compare accuracy on matching source TIFFs

Status: Pending

Depends on: Task 018

Execution: Analysis/report task; no training or prediction.

## Abstract

Compare the temporal baseline with each LORO model on identical source TIFFs
that were unseen by both models, while separately reporting every LORO model's
full held-out-region performance. The default unit is the original TIFF, using
unique-pixel overlap-reconstructed confusion counts from Task 017. This task
must not compare only one aggregate number from differently sized test sets.

## Goal

Produce auditable matched-TIFF tables, per-region summaries, full-region LORO
tables, plots, and a concise interpretation of the geographic-generalization
gap.

## Inputs

- Task 018 suite inventory and all `tiff_metrics.csv`, `region_metrics.csv`, and
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
- Recomputed metrics agree with Task 017 outputs within tolerance.
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
