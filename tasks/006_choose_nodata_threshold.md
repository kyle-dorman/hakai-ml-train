# Task 006: Choose the universal nodata threshold

Status: Complete

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

## Analysis for decision

The rerunnable analysis is implemented in
`scripts/analyze_planet8b_nodata.py`. Its versioned external outputs are under:

```text
/Volumes/x10pro/kelpseg/nodata_threshold_analysis_v1
```

The manifest distribution is strongly right-skewed: the global median is
12.33% nodata, the 75th percentile is 43.83%, the 90th is 84.72%, and the 95th
is 99.93%. The required candidate thresholds plus a 60% class-retention break
were analyzed. Headline global results are:

| Threshold | Retained chips | Removed chips | Removed chips | Removed class-1 pixels | Source TIFFs eliminated |
|---:|---:|---:|---:|---:|---:|
| 40% | 4,301 | 1,702 | 28.35% | 6.96% | 2 |
| 50% | 4,637 | 1,366 | 22.76% | 4.54% | 2 |
| 60% | 4,919 | 1,084 | 18.06% | 0.92% | 1 |

At the proposed 50% threshold, regional chip removal ranges from 0% in
`ca_007` and `ca_011` to 33.69% in `bc`; no region is eliminated. Two source
TIFFs lose every chip: `006_20210805_184050_240c` and
`20210811_185433_06_2262_3B_AnalyticMS_SR_8b_harmonized_clip5`. The former
regains one retained chip at 60%; the latter has a minimum chip nodata fraction
of 83.09% and remains eliminated at 60%.

The contact sheet shows the nearest manifest chips below and above 40%, 50%,
and 60%. It uses one-indexed PlanetScope bands 6/4/2 as an RGB-like view, with
2nd–98th percentile scaling over non-nodata pixels, plus the remapped label and
an independently recomputed all-eight-band-zero mask. All six NPZ counts match
the manifest. The masks follow hard source-coverage borders; legitimate dark
water remains unmasked when any stored band is nonzero.

Recommendation: approve `max_nodata_pct = 50`. It is an interpretable majority-
valid rule that removes edge-dominated chips while retaining 95.46% of class-1
pixels. A 60% threshold is the coverage-preserving alternative; it reduces
class-1 removal to 0.92% and preserves one additional source TIFF, but admits
chips whose majority area is nodata. A stricter 40% threshold increases both
chip and class-1 selection bias.

On 2026-07-15, the user approved `max_nodata_pct = 50`. No filter has been
applied; Task 007 owns that mutation.

## Outcome

The required distribution, candidate, per-chip, and visual analyses are stored
under `/Volumes/x10pro/kelpseg/nodata_threshold_analysis_v1`. The user approved
the recommended universal threshold of 50% after reviewing its global and
regional effects and comparing it with 30%, 40%, and 60%. At 50%, the dry-run
retains 4,637 chips and removes 1,366 (22.76%); removed chips contain 5,092,220
class-1 pixels (4.54% of the canonical total). No region is eliminated. The
decision explicitly acknowledges that two source TIFFs lose all chips:
`006_20210805_184050_240c` and
`20210811_185433_06_2262_3B_AnalyticMS_SR_8b_harmonized_clip5`.

Changed repository files are `scripts/analyze_planet8b_nodata.py`,
`tests/test_analyze_planet8b_nodata.py`, this task, `tasks/007_apply_nodata_filter.md`,
`tasks/README.md`, `AGENTS.md`, `README.md`, `docs/index.md`, `docs/todo.md`, and
`docs/data_artifacts.md`. Durable external artifacts are the five required
outputs, the contact-sheet selection table, and nine independent Task 005
dry-run reports under the analysis directory. The recommendation artifact
records the approval and confirms that filtering has not yet been applied.

Validation passed for all candidate-report reconciliations, regional totals,
contact-sheet NPZ/manifest resolution, and the canonical inventory. The active
manifest retained SHA-256
`7fd2316ae07c4c5277ff33a62ae4c1ee60ced14a528e6a153a6489a7e457d9c8`
and all 6,003 NPZs remain active. Focused Ruff passed, all 34 tests passed, and
`git diff --check` passed. Repository-wide Ruff still reports only the two
pre-existing unused notebook loop variables and formatting drift in those same
legacy notebooks.

There are no unresolved Task 006 issues. The exact next action is Task 007's
50% production dry-run, count reconciliation to 4,637 retained and 1,366
removed, followed by the separately scoped transactional apply.
