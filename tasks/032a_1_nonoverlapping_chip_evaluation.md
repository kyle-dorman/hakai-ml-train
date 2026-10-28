# Task 032A.1: Non-overlapping chip validation and test

Status: Complete — 2026-10-28. Stop before Task 032B.
Depends on: completed Task 032A (`9a278c1`). Stop before Task 032B.

## Abstract

Use ordinary chip-based validation during training, with non-overlapping input
windows for validation/test. Keep overlapping training chips. Source assignments,
spacecraft/day isolation and both BC variants stay fixed. Tiled reconstruction
and source-level scoring remain separate post-training workflows.

This user decision supersedes Task 032A's earlier instruction to retain all
validation/test windows; that task's recorded results remain historical.

## Read and inputs

Read `AGENTS.md`, `docs/index.md`, `docs/todo.md`, `tasks/README.md` and this task.
Then read `docs/documentation.md`, `docs/architecture.md` (splits/loading and
prediction/scoring), `docs/product.md` (California target and claims),
`docs/experiments.md` (evaluation), `docs/data_artifacts.md` (portable releases),
`docs/quickstart.md` (split and tiny walkthrough), Task 032A's final handoff and
Task 032B's production contract only to update its handoff.

Reuse the installed chipper, `select_windows`, ordinary manifests and existing
external tiny-v2 inputs/chips/splits under `/Volumes/x10pro/kelpseg/`.
No full-dataset chips, Box work, model training or scoring is authorized here.

## User decisions required

None remaining. The user selected **reuse existing chips and report uncovered
edges** rather than adding edge payloads. Keep the implementation small and the
current module layout, public command and five split controls.

The with-BC variant is the primary baseline; without BC is the comparison.
Current membership names remain `augmented` (with both 011/012) and `base`
(without both). No source membership or cutoff changes are authorized.

## Implementation contract and checklist

- Leave chipping, NPZs, source assignments and recipe defaults unchanged.
- Update `select_windows` to choose a deterministic disjoint subset for source
  roles `val` and `test`, reserving the earliest existing window in crop-key,
  numeric row/column order. Compare half-open rectangles in original TIFF pixel
  coordinates, grouped by `(dataset_id, release_id, source_id)`; this also avoids
  repeated pixels across crops of one original. Touching edges are disjoint.
- Reserve nominal windows even when nodata-omitted. Preserve their omission
  reason; do not replace them with overlapping alternatives. Retained overlapping
  validation/test candidates become `unused` with reason `evaluation_overlap`.
  All rows/payload references remain available; no per-fold copies or links.
- Training and previously-unused source roles retain their current behavior.
  The same evaluation subset applies to both BC and all spectral variants.
- Report geometric coverage using manifest rectangles only: selected input
  footprint (union of crops), disjoint-grid area, retained selected area,
  uncovered edge/gap area and nodata-omitted window area. These are source-window
  areas, not valid-label counts or model scores; artificial padding is excluded.
  Arbitrary supported chip strides may leave interior gaps as well as edges.
- Use small ordinary helpers in `prepare/splits.py`, explanatory inline comments
  and standard progress logging. No new recovery, hashes, receipts, framework,
  payload scans or concurrent-edit protection.
- Update fixture metadata to the actual source/window schema. Cover 511/512/513,
  768/769 dimensions, true-size edges, shifted/identical/disjoint crops, arbitrary
  crop offsets, nodata omissions, training overlap, deterministic selection,
  baseline/LORO roles and unchanged BC/source assignments. Check installed APIs.
- Extend the existing bounded tiny-v2 smoke using fresh `task032a_1_*` outputs
  outside Git, reporting source and window counts separately. Reuse existing
  chips; load bounded representative 8/4/3 arrays and a preserved partial edge.
- Update current researcher/product/architecture/experiment instructions and
  Task 032B's handoff; preserve historical outcomes. Run focused tests, wheel/
  sdist, Ruff format/check, all-file pre-commit, docs links and diff checks.

## Acceptance

Training still selects all canonical retained chips. Active val/test rectangles
share no original source pixel, including across crops. Geometric omissions are
explicit. All 369 source assignments and ten LORO folds remain identical to the
approved controls; both BC variants persist. Model selection uses validation
only, and aggregate chip confusion counts do not imply stitched full-TIFF scores.

## Outcome and exact handoff

Record files, tests, tiny selection/coverage counts, unchanged assignments,
external artifacts and limitations. Close both queues and hand only Task 032B
the final selector policy and corrected tiny/production expectations, then stop.

## Outcome (2026-10-28)

Implemented disjoint existing-chip validation/test selection. Training retains
all canonical overlap; source assignments, chip generation and stored payloads
are unchanged. This implements the user's explicit existing-chip/coverage-gap
choice without adding edge chips or a second dataset. With-BC `augmented` is
the primary baseline and without-BC `base` the comparison.

### Changes and simplicity

- `src/kelpseg/prepare/splits.py`: added two ordinary private helpers for
  rectangular crop-union area and evaluation selection. `select_windows` keeps
  its signature and all candidate rows, visiting evaluation candidates in
  deterministic crop-key and numeric row/column order. Half-open rectangles in
  original TIFF coordinates ensure adjacent edges are allowed and multiple
  crops cannot repeat an original pixel. Retained overlaps become
  `unused`/`evaluation_overlap`, keeping their canonical payload reference.
  Nodata-omitted nominal slots remain reserved and retain their omission reason.
- Standard progress logs report source and total geometric input footprint,
  nominal disjoint-grid area, retained selected area, uncovered edges/gaps and
  nodata-omitted window area. Crop-union areas avoid counting overlapping crop
  inputs twice. No arrays are read for selection/coverage; no image-size masks
  are allocated by runtime selection. No new public command, recipe option or
  output manifest format was needed.
- `tests/test_splits.py`: corrected the fixture controls to real source/window
  dimensions and offsets; added 12 cases for boundary dimensions, original/crop
  uniqueness, nodata slot reservation, nonaligned/disjoint/identical crops,
  deterministic ordering, retained training overlap, BC/LORO consistency and
  generic strides with interior gaps. `tests/test_distribution.py` exercises
  the new selector from both isolated wheel and sdist installations.
- Updated researcher, architecture, product, experiment and artifact instructions,
  README/index, both queues and the Task 032B handoff. Ordinary chip validation
  and held-out chip test are distinguished from later tiled prediction/TIFF
  scoring. Only validation selects checkpoints. Historical Task 032A outcomes
  remain unchanged; this task supersedes their window-selection policy.

The module layout, original-source/spacecraft/day assignments, both BC variants,
all spectral selections, chipper and loader stay intact. No hashes, receipts,
recovery/reuse, frameworks, extra guards, link trees or payload copies were added.

### Exact smoke artifacts and unchanged inputs

- Reused tiny inputs: `/Volumes/x10pro/kelpseg/data/examples/tiny_ca_bc/v2/`.
- Reused chips: `/Volumes/x10pro/kelpseg/examples/runs/task032a_tiny_chips_v1/`.
- Reused assignments: `/Volumes/x10pro/kelpseg/examples/runs/task032a_tiny_splits_v1/`.
- New bounded selection report: `/Volumes/x10pro/kelpseg/examples/runs/task032a_1_tiny_selection_v1/`;
  only `summary.json` and `window_selections.csv` (324 rows = 54 x six scopes).
  References in the summary are relative to this report.
- Reproducible smoke: `/Volumes/x10pro/kelpseg/examples/check_task032a_1_tiny.py`.
- Progress/evidence log: `/Volumes/x10pro/kelpseg/analyses/task032a_1_tiny_smoke.log`.

Metadata-only temporary writes reproduce **all five original controls byte for
byte** for the full 369-source scope (8,118 assignments across the baseline/ten
LORO folds and two variants) and tiny v2 (13 sources, 78 assignments). The full
baseline remains 216/53/58 without BC and 258/53/58 with BC. No old control or
payload was overwritten; no full-dataset chips or transfers ran.

Tiny v2 still has 13 original sources, with base source counts 2 train / 2 val /
6 test / 3 unused and augmented 5 / 2 / 6 / 0. Its 54 canonical retained payloads
(including 31 background-only windows) are unchanged. Active selection now is:

| Experiment/variant | Train windows | Val | Test | Unused | Evaluation overlap exclusions |
|---|---:|---:|---:|---:|---:|
| baseline/base | 8 | 2 | 7 | 37 | 25 |
| baseline/augmented | 20 | 2 | 7 | 25 | 25 |
| loro_002/base | 4 | 1 | 6 | 43 | 19 |
| loro_002/augmented | 16 | 1 | 6 | 31 | 19 |
| loro_003/base | 4 | 1 | 5 | 44 | 18 |
| loro_003/augmented | 16 | 1 | 5 | 32 | 18 |

All active evaluation rectangles are disjoint within each original and all
six scopes. Evaluation identities match across BC variants. Training identities
remain unchanged. Twelve representative 8/4/3-band loads pass across train,
validation, test and the retained partial test edge. The 512-by-257 window still
pads `(0, 0, 0, 255)` with image zero and target -100.

| Evaluation scope (both variants) | Input footprint pixels | Disjoint/retained window pixels | Uncovered edges/gaps |
|---|---:|---:|---:|
| baseline | 4,719,360 | 2,228,736 | 2,490,624 |
| loro_002 | 3,539,712 | 1,704,448 | 1,835,264 |
| loro_003 | 3,538,944 | 1,572,864 | 1,966,080 |

There are no nodata-window omissions in the real tiny example; synthetic cases
separately prove the reservation and reporting. Areas above include native
nodata inside retained windows, exclude artificial padding, and are not valid-
label support or ecological area. These 768-square crops intentionally lose
large edge strips when selecting existing 512-square windows; their coverage
fraction does not estimate the full release. Generic strides can leave interior
gaps as well. The policy neither promises complete coverage nor evaluates new
pixels outside the existing canonical windows.

### Validation and exact next action

Passed **200 focused tests**, including isolated wheel/sdist checks and retained
legacy scientific assertions; Ruff format/check; all-file and explicit new-file
pre-commit; changed-document links/anchors, fenced blocks and Python snippets;
and `git diff --check`. No unrelated failure was observed; the full legacy
suite was not rerun. An independent read-only review found no remaining issue
and cross-checked crop-union areas against bounded pixel masks.

Next action: execute only [Task 032B](032b_produce_and_publish_chip_release.md)
when selected. Its split/chip production commands and five-control export schema
remain unchanged. After production, call the updated `select_windows` for each
experiment/variant and filter by active `split`; retaining a `payload` alone
is not evidence that a row is selected. Record active evaluation exclusions and
coverage separately from canonical retained/omitted payload counts and source
assignments. Reuse one chip collection, publish the ordinary controls and tiny
v2, then perform bounded active train/val/test restoration and load checks.
Post-training reconstruction/scoring remains Tasks 034–036; this task implements
no trainer or metric calculation. Task 032B has not started.
