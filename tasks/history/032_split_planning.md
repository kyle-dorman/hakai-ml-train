# Task 032 split planning history

Historical discussion and superseded proposals, retained as evidence only.
The current handoff contracts are [032A](../032a_collection_and_split_implementation.md)
and [032B](../032b_produce_and_publish_chip_release.md). Their approved mixed
split supersedes earlier dates, counts, open questions and next-action wording
below. No historical proposal is an instruction to reopen the agreed split.

# Task 032A: Collection and split implementation

Status: Planning — scientific split approved and locked on 2026-10-27; implementation not started.

Depends on: completed Task 031. Its chipper/loader and review are complete;
the scientific split is agreed. Finalize the implementation checklist before coding.

## Abstract

Implement small collection and source-assignment functions for temporal baseline
and LORO experiments. Extend the existing tiny walkthrough. Full chip production
and Box publication belong to Task 032B. The approved grouping and mixed split
section below owns the final scientific decisions; earlier proposals are history.
This planning closeout does not launch implementation.

## Inputs and reading route

Read the entry docs, then `docs/product.md`, `docs/architecture.md`,
`docs/data_artifacts.md`, `docs/documentation.md`, and Task 031's final outcome.
Read Tasks 000/012/022/023 and the retained splitter/materializer only for
historical policy and reusable correctness tests.

Inputs: completed Task 031 chip manifests/loader/tiny example, source region/date
metadata, exact external release references, and the user-selected split policy.
The old split CSV is historical evidence, not the new assignment by default.

## User decisions required

- Approved and locked: the reconciled mixed-direction split below, including
  exact source assignments and the reviewed date/foreground limitations. Uneven
  proportions are accepted. No temporal split choice remains open; do not
  reopen it or silently reuse the historical split. Source assignments are
  recorded externally under `task032_mixed_satellite_day_approved_v1`.
- Agreed grouping: all imagery from the same physical spacecraft on the same
  UTC acquisition date stays in one partition per experiment/fold, across regions
  and crops. The same spacecraft may cross partitions on different days. This
  supersedes the briefly considered whole-spacecraft exclusion. Keep region/date
  groups intact and validate both baseline and each LORO fold.
- Agreed: regions 001–010, including both Baja regions, are evaluation-eligible.
  Use one LORO fold per evaluation region. Held-out region is test across all
  available dates; other evaluation regions use temporal training and validation
  sources, with their temporal tests unused. Keep canonical regions distinct.
- Agreed: 011 (Calvert Island, 12 sources) and 012 (BC tiles, 30 sources) are
  training-only, toggled together in a with/without comparison. They never
  contribute validation or a test fold. Keep all 001–010 assignments fixed
  across variants. The user's duplicated "001 and 001" was read as 001 and 002,
  the two Baja regions asked about; no geographic renumbering is performed.
- Geographic generalization is the primary concern for California deployment;
  future-date/year tests and temporal error stability remain explicit goals.
  The approved mixed-direction boundaries use the actual support audit below.
  This is not a uniform future-year benchmark. Strict global future-year claims
  require all training
  inputs, including the optional 011/012 group, to precede the cutoff.
- Historical storage used hard links to the canonical chips, not symlinks.
  Current architecture uses portable manifests without requiring link trees;
  physical link views are not yet selected for this replacement.
- Preserve background chips canonically. Historical training excluded background
  chips; any new training eligibility decision remains explicit and separate.
  The original non-overlap test restriction was superseded in Tasks 022/023;
  do not restore it implicitly when recreating LORO source membership.
- Agreed for all tasks: plain manifests/functions, minimal bookkeeping, no new
  hashing, checksums, authentication catalogs, or receipts.

## Draft implementation contract and expected outputs

Before coding, finalize a short plan here with the agreed scientific policy,
manifest fields, CLI and filenames after Task 031 closes. Candidate files are
`src/kelpseg/prepare/splits.py`, `src/kelpseg/cli/split.py`, a small explicit
split recipe under `configs/`, and focused tests. These names and `kelpseg split`
are planned, not implemented.

Select one dataset, a region subset, or a declared combination through ordinary
release/source references; preserve original TIFF identity for crops. Generate
external source-level assignments and compact summaries. Chips inherit their
source assignment; 8-band, RGB+NIR and RGB share the same assignments.
Keep algorithms/hand-authored recipes in Git and generated manifests outside it.
Reject duplicate/conflicting/missing identities and known alias conflicts using
available metadata; do not introduce payload hashing or claim exhaustive unseen
duplicate detection. Retain practical paths, region/date, source membership,
fold identity and unused reasons. No copied per-band payloads or link framework.

## Smoke and validation

- Synthetic chronological/date-group cases, exact joins, crop parent grouping,
  missing/duplicate metadata, known aliases, and release conflicts.
- Every LORO fold has no held-out train/validation sources; other-region temporal
  test sources remain unused. Spectral selections retain matching memberships.
- Validate ten evaluation-region folds and both training-only-group variants:
  011/012 never occur in validation/test and 001–010 memberships do not change.
  The tiny example contains 002/003/012, so it supplies two eligible folds and
  one optional training region, not three held-out folds. Use synthetic 011
  fixtures to test the combined training-only group without another data fetch.
- Run the existing tiny example through baseline/all tiny-region LORO assignment
  and loading; no training or full-data chipping. Publish complete fresh outputs
  only, stop on failure, and refuse overwrites.
- Focused tests, required Ruff checks and broad-change pre-commit; inspect docs,
  validate links and run `git diff --check`. Extend researcher instructions with
  copyable recipes and errors; preserve unrelated and Task 031 work.

## Acceptance, non-goals and outcome

Acceptance: the agreed policy is explicit, tested functions/CLI and portable
manifests resolve the tiny cases, routine changes require no Python edits,
and Task 032B has exact runnable inputs/commands. Record changed files, external
example outputs, validation, simplicity/removal check, unresolved limits and the
exact next action. No full production/publication, training, scoring, prediction,
new-region ingestion, recovery system, or unsolicited hashing work.

Next action: finalize the implementation checklist and both task contracts
against Task 031's closing interfaces, preserving the approved split below.

## Metadata-only temporal support review (2026-10-27)

Read final cleaned `sources.json`, organized `regions.csv`, the existing Task
031 source-count report at threshold 50 and the historical split CSV. All 369
source IDs, regions, dates, dimensions and valid-imagery counts joined exactly
between the current metadata and the existing report. No raster reads, new
hashes, model evaluation or new split generation occurred. Foreground counts
reuse the earlier projected-cleanup report reconciled in Task 031; they are
not a new pixel verification. The historical split was joined for the 339
001–011 sources only; BC aliases were unnecessary for this diagnostic.

External plain outputs:
`/Volumes/x10pro/kelpseg/analyses/task032_temporal_metadata_v1/summary.json`,
`region_month_support.csv` and `historical_split_label_support.csv`.
Counts sum source observations, repeating space across dates and possible
overlapping TIFFs; they do not measure unique geographic kelp area.

Year cells show TIFF count followed by represented numeric months. TIFF/date
counts differ where several TIFFs belong to the same indivisible date group.

| Region | TIFFs/dates | 2020 count (months) | 2021 count (months) | 2022 count (months) |
|---|---:|---|---|---|
| 001 Baja Isla Navidad | 22/22 | 6 (04,09,10,11) | 16 (02,03,04,05,06) | 0 |
| 002 Baja Punta Eugenia | 59/59 | 4 (05,06,09,10) | 31 (02,03,04,05,06,07,08,10,11) | 24 (02,03,04,05,06,07) |
| 003 San Diego | 17/17 | 0 | 10 (04,05,06,08) | 7 (04,05,06,07) |
| 004 Palos Verdes | 29/29 | 1 (08) | 13 (02,03,04,05,06,07,08,09) | 15 (03,04,05) |
| 005 Channel Islands | 21/21 | 1 (05) | 9 (03,04,05,06,08) | 11 (03,04,05) |
| 006 Channel Islands | 35/19 | 0 | 18 (06,08,09,10,11) | 17 (02,03,04,05,08,09,10,12) |
| 007 Refugio | 32/32 | 3 (05,08) | 29 (03,04,05,06,07,08,09,10,11,12) | 0 |
| 008 Big Sur | 65/65 | 15 (05,08,09,10,11,12) | 31 (01,02,03,04,05,06,08,09,10,11,12) | 19 (01,02,03,04) |
| 009 Monterey | 14/14 | 2 (11,12) | 0 | 12 (04,05,06) |
| 010 Northern California | 33/33 | 5 (06,08,09,11) | 28 (02,03,04,05,06,07,08,09,10) | 0 |
| 011 Calvert Island, training-only | 12/12 | 2 (11) | 4 (05,06,08) | 6 (01,03,04) |
| 012 BC tiles, training-only | 30/3 | 0 | 30 (08) | 0 |

The evaluation-eligible scope is 327 sources across ten regions. The optional
training group is 42 sources; the BC tiles cover only 2021-08-11/12/13. Actual
California regions 003–010 contain 246 sources; Baja adds 81. These are declared
experimental roles over the unchanged 369-source release, not new data cleaning.

The old chronological assignments illustrate prevalence/season confounding:

- Region 006's old test has six TIFFs from August–December 2022 and just 4,072
  labeled foreground pixels (0.0120% of its scoreable pixel observations),
  versus 0.3591% in training and 0.8844% in validation. Four TIFFs have zero
  labeled foreground. This is a real diagnostic scope difference, not evidence
  that those test dates should be discarded or that the model failed.
- Big Sur's old training label prevalence is 5.6646%; validation, January–early
  February 2022, is 2.2060%; test, mid-February–April 2022, is 2.5192%.
  Northern California changes in the opposite direction: 0.4184% in training
  versus 2.9580% in the late-September–October 2021 test. Neither establishes
  biological causes or independent F1 distortion without predictions.
- Monterey has no 2021 imagery and only two dates in 2020. A strict pre-2022
  train/validation design leaves almost no training support there. Its old
  validation/test are June 2022, so those are later-date rather than a clean
  unseen-year test.
- Refugio, Northern California and Baja Isla Navidad have no 2022 imagery.
  Whole-year holdouts cannot give every evaluation region a common 2022 test.
  Sparse month support also limits matched-season comparisons.
- Headers have multiple source grids in most regions. Common valid labeled
  footprints must be established before measuring temporal area-change error;
  region/date counts alone do not prove a matched-location time series.

Keep geographic LORO primary, preserve low-kelp cases and add the supported
temporal/prevalence/error diagnostics owned by `docs/experiments.md` to Tasks
035/036. Do not optimize the new test membership for favorable F1. Remaining
discussion: chronological boundary/fraction choices versus an explicitly
separate future-year subset, given this actual support.

## Proposed chronological baseline for review (2026-10-27)

The user accepts uneven proportions and requested concrete per-region dates
and kelp support. This is a manually chosen proposal, not an approved split
or Task 032A implementation. It preserves whole region/date groups, orders
training before validation before test in each evaluation region, retains all
source observations and gives geographic-first experiments substantial training
support. Calendar blocks are preferred; 001/004/005/009 need within-month
boundaries to retain usable validation/test date counts. No model results or
F1 optimization selected these boundaries, and equal kelp shares are not a goal.

Exact proposed source assignments, inclusive cutoffs and summary are external:
`/Volumes/x10pro/kelpseg/analyses/task032_split_proposal_v1/` contains
`source_assignments_proposed.csv`, `region_summary.csv` and `proposal.json`.
They are discussion artifacts only, not published experiment assignments.

Dates below are first/last actual observations, not continuous coverage.
Parentheses give TIFF counts.

| Region | Train | Validation | Test |
|---|---|---|---|
| 001 baja_islaNavidad | 2020-04-22–2021-04-10 (14) | 2021-04-18–2021-04-30 (4) | 2021-05-21–2021-06-11 (4) |
| 002 baja_puntaEugenia | 2020-05-15–2021-11-10 (35) | 2022-02-25–2022-03-18 (6) | 2022-04-07–2022-07-15 (18) |
| 003 sanDiego | 2021-04-07–2021-08-26 (10) | 2022-04-13–2022-04-24 (2) | 2022-05-10–2022-07-01 (5) |
| 004 palosVerdes | 2020-08-27–2022-03-29 (20) | 2022-04-06–2022-04-14 (5) | 2022-04-21–2022-05-10 (4) |
| 005 channelIslands | 2020-05-20–2022-03-23 (13) | 2022-04-13–2022-04-20 (4) | 2022-04-23–2022-05-31 (4) |
| 006 channelIslands | 2021-06-11–2022-02-16 (22) | 2022-03-06–2022-04-05 (3) | 2022-05-06–2022-12-28 (10) |
| 007 refugioStateBeach | 2020-05-17–2021-07-23 (19) | 2021-08-01–2021-08-26 (7) | 2021-09-22–2021-12-12 (6) |
| 008 bigSur | 2020-05-25–2021-10-11 (38) | 2021-11-04–2021-12-01 (8) | 2022-01-20–2022-04-08 (19) |
| 009 monterey | 2020-11-09–2022-05-29 (8) | 2022-06-08–2022-06-15 (3) | 2022-06-20–2022-06-28 (3) |
| 010 northernCalifornia | 2020-06-29–2021-08-31 (26) | 2021-09-14–2021-09-30 (4) | 2021-10-08–2021-10-16 (3) |

Labeled foreground pixels from existing source summaries, counted once per
source TIFF. Percentages are each partition's share of that region's labeled
foreground, not foreground prevalence among all pixels. Space repeats across
acquisitions; these are not unique geographical area or overlapping chip totals.

| Region | Train kelp pixels | Validation kelp pixels | Test kelp pixels |
|---|---:|---:|---:|
| 001 | 2,148,648 (53.7%) | 885,727 (22.1%) | 966,301 (24.2%) |
| 002 | 7,088,686 (53.2%) | 1,287,596 (9.7%) | 4,952,656 (37.2%) |
| 003 | 820,188 (60.1%) | 123,892 (9.1%) | 421,297 (30.9%) |
| 004 | 1,844,045 (66.7%) | 456,603 (16.5%) | 465,210 (16.8%) |
| 005 | 984,826 (55.2%) | 423,659 (23.7%) | 376,779 (21.1%) |
| 006 | 342,721 (50.0%) | 124,200 (18.1%) | 218,796 (31.9%) |
| 007 | 116,776 (65.7%) | 44,752 (25.2%) | 16,263 (9.1%) |
| 008 | 7,124,888 (71.1%) | 1,381,393 (13.8%) | 1,520,246 (15.2%) |
| 009 | 308,320 (39.6%) | 185,048 (23.8%) | 285,285 (36.6%) |
| 010 | 391,551 (46.7%) | 266,699 (31.8%) | 180,889 (21.6%) |

Totals for 001–010: **205 train / 46 validation / 76 test TIFFs**
(62.7% / 14.1% / 23.2%). Labeled foreground totals are
**21,170,649 / 5,179,569 / 9,403,722 pixels** (59.2% / 14.5% / 26.3%).
Regions 011/012 optionally add **42 training TIFFs and 2,622,410 labeled kelp
pixels**; they add nothing to validation/test. With that group included, training
is 247 TIFFs and 23,793,059 labeled foreground pixels. Baseline 001–010
assignments stay identical across band and training-only-group variants.

Important limitations and rationale:

- 002/003 use early 2022 validation and later 2022 testing. 004/005/006/009
  include 2022 training. This is within-region later-date testing, not a globally
  unseen-year experiment; optional 011 imagery also includes 2022. Big Sur's
  full represented 2022 block remains test.
- 006 test includes May plus the depleted August–December tail. All four
  zero-foreground TIFFs remain in test. About 98.1% of its test foreground
  occurs in May; report both periods rather than letting their pooled F1 hide
  low-kelp behavior. It is not a continuous May–December record.
- 010 uses whole August/September/October boundaries, retaining July/August
  observations in training. Its test is only October 8–16, 2021. Monterey's
  test is only June 20–28, 2022. Neither establishes annual temporal stability;
  geographic LORO/full-date diagnostics remain essential.
- San Diego validation has two dates. Region 006 validation has three TIFFs
  across two dates; do not treat its three TIFFs as three temporal replicates.
  All evaluation-region validation/test partitions have at least two dates.
- Source foreground statistics come from the previous metadata audit. The
  earlier 50% nodata-window projection retains all proposed validation/test
  foreground, omits 175 training foreground pixels from 001–010, and omits
  1,764 from optional 011/012 training. These are projected chip coverage counts,
  not a newly executed chip release or repeated raster verification.

Validation: 369 unique proposed source rows; complete membership reconciliation;
strict per-region chronological ordering; intact date groups; ten evaluation
regions; two training-only regions; counts/foreground totals reconciled;
independent review confirmed 205/46/76 and date support. No pixels, hashes,
training, production chipping or approved experiment assignments were generated.

Next action: review these proposed boundaries/support with the user. Once
agreed, freeze the baseline source assignments and use the already agreed LORO
policy (held-out region all dates; other regions' temporal tests unused).

## Fresh reverse-chronological alternative (2026-10-27)

The user clarified that test → validation → train should be redesigned with
reasonably sized partitions, not constrained to the forward proposal's counts.
Retrospective mapping is an accepted tradeoff to discuss; the earlier reversed
count-matching example did not answer that request. This alternative is not
approved or applied and does not replace the forward proposal by default.

A fresh whole-month-block proposal for all ten evaluation regions is external
at `/Volumes/x10pro/kelpseg/analyses/task032_reverse_split_proposal_v1/`:
`proposal.json`, `region_summary.csv`, `source_assignments_proposed.csv`.
It uses 200/59/68 train/validation/test TIFFs (61.2%/18.0%/20.8%), with
24,246,985/3,903,578/7,603,377 source foreground pixels. Optional 011/012
add the same 42 training TIFFs and 2,622,410 foreground pixels.

| Region | Test through (inclusive) | Validation through (inclusive) | Training after |
|---|---|---|---|
| 001 | 2020-12-31 | 2021-03-31 | 2021-03-31 |
| 002 | 2021-03-31 | 2021-05-31 | 2021-05-31 |
| 003 | 2021-04-30 | 2021-05-31 | 2021-05-31 |
| 004 | 2021-04-30 | 2021-06-30 | 2021-06-30 |
| 005 | 2021-04-30 | 2021-06-30 | 2021-06-30 |
| 006 | 2021-08-31 | 2021-11-30 | 2021-11-30 |
| 007 | 2021-03-31 | 2021-04-30 | 2021-04-30 |
| 008 | 2020-12-31 | 2021-05-31 | 2021-05-31 |
| 009 | 2020-12-31 | 2022-04-30 | 2022-04-30 |
| 010 | 2020-12-31 | 2021-03-31 | 2021-03-31 |

Focused support for the regions raised by the user:

- 006: test June–August 2021 has 11 TIFFs / 4 dates / 88,922 kelp pixels;
  validation September–November 2021 has 7 TIFFs / 4 dates / 87,270 pixels;
  training in 2022 has 17 TIFFs / 11 dates / 509,525 pixels. The low-/zero-kelp
  late-2022 observations remain as training input.
- 007: test through March 2021 has 5 TIFFs / 5 dates / 31,797 kelp pixels;
  validation April 2021 has 5 TIFFs / 5 dates / 24,411 pixels; training
  May–December 2021 has 22 TIFFs / 22 dates / 121,583 pixels. Test spans
  actual May/August 2020 and March 2021 observations, not a
  continuous time series.

This improves useful support for 006/007 relative to the previous rigid reverse
example. It does not equalize all regions: 010 validation (February–March 2021)
has 9 dates but only 16,074 foreground pixels. Regions 001/003/009 validation
each have only 2 dates; 009 test has 2 dates. Report prevalence/errors alongside F1 and retain
LORO across all held-out-region dates. Future-year evaluation remains a
separately defined diagnostic if reverse chronology is selected for the main
baseline. No future-year split or additional training suite is authorized here.

Validation: 369 unique source rows; intact date groups; strict test < val < train
within all ten evaluation regions; minimum 2 validation/test dates; totals
reconcile to existing source statistics. No pixels, hashes or model results
were generated/read. Independent review confirmed 006/007 support.

Next action: compare this independently sized reverse proposal with the forward
proposal, discuss 010's remaining low-prevalence validation support, and agree
the direction and boundaries before implementation.

## Per-region direction and shared-acquisition review (2026-10-27)

The user proposes forward chronology for 010 and forward/reverse choices per
region based on useful support, with each satellite/image confined to one split.
At this historical review the term "satellite" was still being clarified.
The later spacecraft/day decision below is current. Regional direction and
boundaries remained draft choices. A mixed
design can serve the geographic-first baseline; it must not be presented as a
uniform forward-time or backward-time benchmark. Freeze decisions before model
evaluation and preserve them across bands and the 011/012 training comparison.

Read-only source metadata reveals 15 exact acquisition `source_key` identities
shared across regions: 14 between 001/002 and one between 005/006. The current
reverse 001–009 / forward 010 candidate has 12 conflicting acquisition roles.
For example, `20210404_173957_2441` is train in 001 but validation in 002;
`20210802_175057_2460` is train in 005 but test in 006. No final assignment or
claim of scene independence has been made.

The diagnostic is external at
`/Volumes/x10pro/kelpseg/analyses/task032_temporal_metadata_v1/shared_acquisition_diagnostic.json`.
It joins existing metadata only, with no pixels, hashes or physical-satellite
platform inference. These are acquisition identities; several dates captured
by the same spacecraft are a different grouping question.

The preliminary acquisition-only check was superseded by the stronger same-
spacecraft/day check below. Jointly reconcile the coupled regional
boundaries while keeping region/date groups intact, then report the resulting
counts. Carry parent-acquisition IDs through crops/chips. In LORO, an acquisition
represented in the held-out test region cannot simultaneously supply a crop in
another region's train/validation; mark that companion unused in the fold.
This adds a scientific shared-scene exclusion to the historical source policy,
not a hashing or duplicate-discovery framework. BC acquisitions must pass the
same membership checks if they overlap selected evaluation inputs.

Next action: clarify the requested identity grouping, then produce a jointly
consistent per-region-direction proposal; do not treat the existing independent
regional cutoffs as already acquisition-exclusive.

## Approved grouping and mixed split (2026-10-27)

The user clarified physical spacecraft ID (for example suffix `240c`), then
refined exclusivity to **same spacecraft, same day**. Group by physical ID and
recorded UTC acquisition date across all regions/crops; observations from the
same spacecraft on different days may cross partitions. Whole-spacecraft
isolation is withdrawn. The earlier physical-satellite feasibility diagnostic
is only evidence for that withdrawn alternative. Planet's naming convention
confirms the satellite field:
<https://docs.planet.com/data/imagery/planetscope/#product-naming>.

The user approved and locked this split after reviewing dates, TIFF counts,
mean kelp counts/fractions per TIFF and the zero-conflict checks. The approved
external record is
`/Volumes/x10pro/kelpseg/analyses/task032_mixed_satellite_day_approved_v1/`:
`source_assignments.csv`, `region_summary.csv`, `split_decisions.json`.
These preserve the reviewed proposal
`task032_mixed_satellite_day_proposal_v1` memberships without changes. No
implementation, production chipping or Box publication has started. Use reverse chronology
for 001–008 and forward for 009/010, with **216/53/58** train/validation/test
TIFFs and **25,507,090/2,682,168/7,564,682** labeled source foreground pixels.
Optional 011/012 add 42 training TIFFs and 2,622,410 foreground pixels.

Changes needed beyond independent regional choices:

- Align 001/002 around test through 2020, validation February–March 2021,
  training from April 2021. Their shared acquisitions otherwise cross splits.
  This leaves 002 with 51 training / 4 validation / 4 test TIFFs: uneven, but
  both held-out partitions have 4 dates and useful foreground.
- Put the shared 005/006 August 2, 2021 spacecraft/day group in validation.
  Region 005 trains on 2022; 006 tests on June 2021, validates August–November
  2021, and trains on 2022. Region 006 test has 6 TIFFs / 2 dates / 81,179
  foreground pixels; validation has 12 TIFFs / 6 dates / 95,013 pixels;
  training has 17 TIFFs / 11 dates / 509,525 pixels.
- Use forward chronology for 009 so its April 8, 2022 group remains training,
  matching 008. Its existing forward proposal gives 8/3/3 TIFFs and
  308,320/185,048/285,285 foreground pixels. Region 010 retains 26/4/3
  forward membership.

Actual regional first/last dates and counts are in the external summary.
Inclusive cutoff rules follow (first partition is test for reverse, train for
forward; middle is validation; remaining observations enter the last partition).

| Region | Direction | First cutoff | Second cutoff | Train / val / test TIFFs |
|---|---|---|---|---|
| 001 | reverse | 2020-12-31 | 2021-03-31 | 14 / 2 / 6 |
| 002 | reverse | 2020-12-31 | 2021-03-31 | 51 / 4 / 4 |
| 003 | reverse | 2021-04-30 | 2021-05-31 | 11 / 2 / 4 |
| 004 | reverse | 2021-04-30 | 2021-06-30 | 18 / 4 / 7 |
| 005 | reverse | 2021-04-30 | 2021-08-31 | 11 / 5 / 5 |
| 006 | reverse | 2021-06-30 | 2021-11-30 | 17 / 12 / 6 |
| 007 | reverse | 2021-03-31 | 2021-04-30 | 22 / 5 / 5 |
| 008 | reverse | 2020-12-31 | 2021-05-31 | 38 / 12 / 15 |
| 009 | forward | 2022-05-31 | 2022-06-15 | 8 / 3 / 3 |
| 010 | forward | 2021-08-31 | 2021-09-30 | 26 / 4 / 3 |

Validation: 369 unique sources; source/region/date joins; intact region/date
groups; strict declared direction in each region; at least 2 dates in each
val/test partition; source/foreground totals reconciled. There are 315 recorded
spacecraft/day groups over all 369 sources (299 over 327 evaluation sources),
with 17 shared cross-region groups (16 evaluation-only). Baseline assignments
have zero group crossings; independent review confirmed 216/53/58 and these checks.

LORO must be validated separately: all held-out-region sources become test;
other-region companions sharing its spacecraft/day become unused before other
train/validation selection. The metadata-only check for all ten folds passes
with those exclusions and other-region baseline test sources still unused.
This checks proposed source assignments, not an implemented split command,
chip generation, model evaluation or verification of unrecorded identities.

Spacecraft identity uses the user's declared filename field, independently
consistent with Planet naming docs. There are 365 sources with full
four-character IDs; four BC tiles preserve the literal shorter token `241`.
Aliases/available metadata do not establish its full-ID equivalent. Those tiles
are all August 13, 2021, when no 001–010 source exists; any full-ID correction
cannot cause a cross-partition conflict on that date in this scope because all
same-day sources are training-only. Keep the unresolved token explicit rather
than inventing an ID or a new payload audit.

Accepted limitations: 002's small held-out fractions; two-date validation in
001/003; two-date 006 test and short 009/010 test windows. The user reviewed
mean per-TIFF foreground counts/fractions and approved the final memberships.
Preserve the temporal/prevalence/error reporting for 035/036. No additional
split approval is needed. Next action: finalize the 032A implementation checklist
and 032B production handoff against 031's implemented interface, using these
locked source assignments and cutoff rules. This approval does not run either task.
