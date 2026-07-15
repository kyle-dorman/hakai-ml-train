# Task 006: Choose the universal nodata threshold

Status: Pending

Depends on: Task 005

Execution: Local analysis and user-decision task; no deletion.

## Abstract

Quantify how candidate nodata thresholds affect the canonical chip collection,
inspect representative chips near plausible cutoffs, and ask the user to select
one universal threshold. Because nodata filtering occurs before experimental
splits, this choice applies identically to baseline/LORO train, validation, and
test data. This task ends with a recorded decision and does not apply it.

## Goal

Produce enough global, regional, source-TIFF, and visual evidence to choose a
single defensible `max_nodata_pct`.

## Inputs

- Task 004 canonical chip manifest and chip root
- Task 005 dry-run filter CLI
- Raster manifest for source TIFF/region metadata
- `docs/product.md`
- `docs/data_artifacts.md`

## Required analysis

1. Distribution summary at percentiles `0, 1, 5, 10, 25, 50, 75, 90, 95,
   99, 100` globally and by region.
2. Candidate removal table at thresholds `0, 1, 5, 10, 20, 30, 40, 50` percent,
   plus any threshold suggested by visible distribution breaks.
3. For each candidate: retained/removed chips, source TIFFs affected, class-1
   pixels retained/removed, and region-specific removal percentage.
4. Flag any source TIFF or region that would lose all chips.
5. Create a contact sheet of representative chips immediately below and above
   the most plausible thresholds. Display a useful false-color or RGB-like band
   combination plus label and nodata mask; record band choice.
6. Distinguish coastal black/nodata borders from legitimate dark water as far as
   the all-band-zero definition allows.

## Expected outputs

Under a versioned analysis directory beside the canonical chip root:

```text
nodata_threshold_analysis.csv
nodata_distribution_by_region.csv
nodata_candidate_summary.csv
nodata_contact_sheet.png
nodata_threshold_recommendation.md
```

The recommendation must state the proposed threshold, quantitative impact,
regional imbalance risk, and at least one reasonable alternative.

## User decisions required

At the end of the analysis, ask the user to approve one threshold. Do not ask
before presenting the evidence. Record the answer in:

- this task;
- `docs/data_artifacts.md`;
- the recommendation artifact.

If the user rejects a universal threshold, stop and write a new task rather than
silently introducing split- or region-specific filtering.

## Suggested commands

Use Task 005 dry-run repeatedly, plus a small analysis script if needed. If the
analysis should be rerunnable, add `scripts/analyze_planet8b_nodata.py`; do not
leave the only logic in a notebook.

## Validation

- Candidate-table counts match Task 005 dry-run outputs.
- Regional totals reconcile to the canonical manifest.
- Contact-sheet chip IDs resolve to manifest rows and NPZ files.
- No canonical chip or active manifest is modified.
- Run focused Ruff/tests for any added script and `git diff --check`.

## Acceptance criteria

- The user selects a numeric threshold in `[0, 100]` percent.
- The decision is supported by global and per-region evidence.
- No region is accidentally eliminated without explicit acknowledgment.
- Task 007 has the exact threshold and dry-run command.

## Non-goals

- Do not apply the filter.
- Do not choose background-only policy.
- Do not use baseline or LORO test performance to choose the threshold.
- Do not introduce per-split thresholds.

## Review pass

- Remote-sensing researcher: review whether all-band-zero detection and visual
  examples reflect actual missing coverage.
- ML researcher: review class/region selection bias introduced by candidates.

## Outcome template

Record artifact paths, candidate table headline, visual review, recommended and
approved thresholds, user decision, validation, and Task 007 command.
