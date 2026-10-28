# Task 032B: Produce and publish chips and approved splits

Status: Complete — 2026-10-28. Started from `0596ab7`; stop before Task 033.
Depends on: completed Tasks 032A and 032A.1 and their passing metadata/tiny-v2 handoffs.

## Abstract

Run the implemented splitter and Task 031 chipper on the existing 369-source
cleaned release. Publish one native-band chip set, the approved baseline/LORO
assignments and tiny v2 to Box. Use ordinary sequential commands and compact
summaries; no new framework, hashes or transfer receipts.

## Read and inputs

Follow the entry route, then [032A](032a_collection_and_split_implementation.md),
[032A.1](032a_1_nonoverlapping_chip_evaluation.md),
[quickstart](../docs/quickstart.md#chip-cleaned-imagery),
[artifact policy](../docs/data_artifacts.md#box-project-organization-and-upload-verification),
[documentation](../docs/documentation.md) and both final outcomes.
No historical split debate or old checksum protocol is needed.

Under `/Volumes/x10pro/kelpseg/`:

- Cleaned input: `data/3_cleaned/ca_bc/v1/` (369 sources / 12 regions).
- Approved assignment reference:
  `analyses/task032_mixed_satellite_day_approved_v1/`.
- Existing chip recipe: `configs/chip/planet8.toml` (512 size / 256 stride /
  max 50% nodata, true-size edges, native eight bands, canonical backgrounds).
- Implemented split recipe: `configs/split/ca_bc_v1.toml`.
- Task 032A.1's non-overlapping chip validation/test selector and coverage policy.
- Completed local `data/examples/tiny_ca_bc/v2/` from 032A.

## User decisions required

None for the scope, scientific split or normal execution below. Do not reopen
approved memberships. If a target already exists, choose a fresh version/name
and record it; never overwrite or reuse failed preparation output. Stop and
report genuine inconsistencies instead of changing scientific policy.

## Outputs

Use these local project-relative paths, with matching paths under
`kelp-box:kelpseg/`:

| Artifact | Path |
|---|---|
| One native-band chip release | `data/chips/ca_bc/v1/` |
| Collection and split controls | `data/splits/ca_bc/v1/` |
| Portable collection declaration | `data/collections/ca_bc/v1/` |
| Tiny input release | `data/examples/tiny_ca_bc/v2/` |

The collection declaration is one small `collection.json` referencing cleaned,
chip and split dataset/release IDs, their relative paths, and the existing
`collection.csv` inside the split output. Do not duplicate that CSV or merge/copy TIFFs into another
collection or build a storage service. Keep paths relative to this declaration;
installed readers receive explicit local roots after restore.

Keep source-level assignments separate from chip retention. Base baseline counts
are **216 train / 53 val / 58 test** across 001–010; augmented adds only the
42 training-only 011/012 sources. With BC (`augmented`) is the primary baseline;
without both (`base`) is the comparison. There are ten LORO folds, never an
011/012 fold.
All sources belong to the declared scope even if a source produces no retained
window; report that distinction rather than silently changing its assignment.

Training uses all canonical retained windows. Task 032A.1 selects disjoint
existing val/test windows in original TIFF coordinates, including across crops.
Overlaps become `unused`/`evaluation_overlap`; nodata omissions keep their reason.
No extra edge payloads or per-fold link trees are created. Report geometric
uncovered edges/gaps separately from payload retention and source assignments.
Ordinary chip validation selects checkpoints; test remains held out. Later
post-training tiled prediction/source scoring remains a separate workflow.

## Execution plan

Use the installed interfaces and selector policy recorded by 032A/032A.1.
Set the local root once. Do not run these commands as part of planning.

```bash
KELP_DATA_ROOT='/Volumes/x10pro/kelpseg'
uv run kelpseg split --cleaned "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1" --release-id v1 --recipe configs/split/ca_bc_v1.toml --output "$KELP_DATA_ROOT/data/splits/ca_bc/v1" --dry-run
uv run kelpseg split --cleaned "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1" --release-id v1 --recipe configs/split/ca_bc_v1.toml --output "$KELP_DATA_ROOT/data/splits/ca_bc/v1"
uv run kelpseg chip --images "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1/images" --labels "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1/labels" --metadata "$KELP_DATA_ROOT/data/splits/ca_bc/v1/chip_metadata.csv" --recipe configs/chip/planet8.toml --output "$KELP_DATA_ROOT/data/chips/ca_bc/v1" --dry-run
uv run kelpseg chip --images "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1/images" --labels "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1/labels" --metadata "$KELP_DATA_ROOT/data/splits/ca_bc/v1/chip_metadata.csv" --recipe configs/chip/planet8.toml --output "$KELP_DATA_ROOT/data/chips/ca_bc/v1"
```

Run each command only after the previous step succeeds. Before writing, inspect
free space, resolved inputs/output, candidate windows and the tiny-run byte costs;
record a practical storage estimate. Source controls already passed QA; do not
repeat cleaning, the nodata study, input hashes or full label scans.

After writing:

1. Check split totals and membership against the approved reference. Validate
   spacecraft/day and original-source isolation in baseline and every LORO fold,
   shared-day unused companions, optional training roles and fixed evaluation
   membership between base/augmented and band choices.
2. Read the chipper's `summary.json` (`status="complete"`), `sources.json` list
   and `windows.csv`. Reconcile retained/omitted windows, empty omitted payload
   paths and source joins using the updated selector. Reconcile active train/
   val/test and `evaluation_overlap` counts separately; check disjoint original
   pixel rectangles and report geometric grid/retained coverage and omissions.
   Load representative active 8/4/3 inputs and a canonical partial edge. Do not
   audit every NPZ or remap labels again.
3. Write the small collection declaration and a compact source summary including
   region/date support, mean kelp pixels/TIFF and mean labeled kelp fraction/TIFF
   using existing source statistics. Label those as source statistics, not sums
   of overlapping chip pixels or unique geographic area.
4. Publish with ordinary explicit rclone copies to fresh destinations. Use
   `--immutable --size-only --ignore-checksum` as in the tiny example; do not
   introduce deliberate hashing, checksum catalogs or receipts. Compare local/
   remote relative file paths, counts and sizes. Never use deletion-propagating
   sync. Keep existing raw/organized/cleaned releases unchanged.
5. Restore the small manifests and a bounded chip subset into a fresh local
   directory. Preserve their relative layout; select examples from all three
   active baseline splits and both training-only regions, with a partial edge
   and a background chip. Include all window metadata needed to resolve those files,
   while loading only the downloaded subset. Keep this restore below 128 MiB.
   Open/load and compare selected arrays with local originals. Report path/size
   and load/array checks honestly, without a checksum-verification claim.
6. Publish/fetch tiny v2 (below 128 MiB) using the same ordinary copy checks and
   rerun its split/chip/window-selection walkthrough offline in fresh run folders.
   Its generated outputs remain below 1 GiB. This separate tiny fetch is not
   part of the 128 MiB production-subset restore budget.

If any step fails, stop. Preparation is not resumed and failed output is not
reused; a new attempt starts fresh. Do not add recovery infrastructure or
hypothetical concurrent-edit checks.

## Acceptance and validation

- The single native-band chip release and both split variants resolve all ten
  folds without source/date/spacecraft-day leakage. Backgrounds remain canonical;
  band selection happens while loading. Active chip val/test rectangles share
  no original pixel, with explicit geometric uncovered edge/gap reporting.
  Training retains overlap. No copied per-fold/per-band datasets.
- All actual candidate/retained/omitted/source counts and bytes reconcile.
  Treat the earlier 40,571-candidate / 26,573-retained analysis as a projection,
  not an exact production promise; investigate unexplained differences without
  automatically changing the approved recipe or memberships. The chipper's
  canonical candidate/retained projections are unchanged by selector exclusions;
  report active evaluation window counts separately.
- Box path/count/size checks and bounded restore/load checks pass; tiny v2 can
  be fetched once and used offline. Relative paths work from the new local root.
- Inspect Markdown/links and run `git diff --check`. This is a production task;
  code changes need focused tests and required lint, but do not rerun unrelated
  full tests or extend the implementation without a demonstrated need.
- Keep the quickstart current with actual commands, dataset locations, expected
  outputs and simple error remedies. Do not describe future training/scoring
  commands as installed.

Non-goals: new ingestion, training, inference/scoring implementation, GPU work,
new split selection, repeated whole-release QA, hashing, receipts or recovery.

## Outcome and handoff

Record exact local/Box artifact paths, recipes/code version, source/split/window
counts, bytes, mean source kelp support, validation/restore scope and limits,
changed repo files, any removed obsolete options and the simplicity check.
Provide Task 033 the chip/collection/split paths, base/augmented selection API
and tiny-v2 recipe. Preserve the temporal-consistency reporting requirement in
Tasks 035/036. Mark this task complete, update both queues and stop before 033.

## Execution notes (2026-10-28)

Started from clean commit `0596ab7e5fe3d7024e71fe01ea518dd74532812e`.
The intended local/Box `v1` chip, split and collection destinations were absent.
The volume had 567 GiB free. Tiny v2's 151,535,749 payload bytes for 54
windows project about 74.6 GB for the earlier 26,573-retained estimate; allowing
all 40,571 full-size candidates at 17 raw bytes/pixel gives about 181 GB
before compression and small metadata overhead. Available storage covers both.
The production preview confirms 369 sources, 40,571 candidate windows and
18,655,171,412 image/label input bytes. Retention remains a production result.

Installed split dry-run/write succeeded sequentially, followed by chip
dry-run/write using the task's exact paths and recipes. Logs are outside Git
at `analyses/task032b_{split_preview,split,chip_preview,chip}.log` under the
local data root. The split controls match all five completed 032A controls
without hashing. Full memberships, all ten folds, spacecraft/day isolation and
shared-day exclusions pass; `analyses/task032b_source_summary.json` records
metadata validation and existing per-source support statistics.

## Outcome (2026-10-28)

The installed split/chip commands completed without changing recipes, source
assignments, code or scientific policy. The release reconciles exactly with
the earlier projection: **369 sources / 40,571 candidates / 26,573 retained /
13,998 nodata omissions**. Omitted rows have no payload. All 369 sources have
retained windows and every assigned evaluation source has a selected window
in every scope. Canonical payloads include **14,386 background-only** and
**2,982 partial-edge** windows. All overlapping payloads remain available.

### Local release paths and sizes

All paths below are relative to `/Volumes/x10pro/kelpseg/`; Box uses the same
paths below `kelp-box:kelpseg/`.

| Artifact | Relative path | Files | Bytes |
|---|---|---:|---:|
| Native-band chips and four controls | `data/chips/ca_bc/v1/` | 26,577 | 65,565,628,953 |
| Five source/split controls | `data/splits/ca_bc/v1/` | 5 | 935,947 |
| Portable declaration | `data/collections/ca_bc/v1/collection.json` | 1 | 539 |
| Tiny v2 inputs | `data/examples/tiny_ca_bc/v2/` | 28 | 82,537,678 |

Chip payloads alone total **65,560,709,157 bytes**; chip controls account for
4,919,796 bytes. `collection.json` references dataset/release `ca_bc/v1` for
cleaned/chip data and collection/release `ca_bc/v1` for splits. Paths resolve
from its own directory: `../../../3_cleaned/ca_bc/v1`,
`../../../chips/ca_bc/v1`, `../../../splits/ca_bc/v1`, and the existing
`../../../splits/ca_bc/v1/collection.csv`. No CSV/TIFF duplication or fold
link trees were created.

### Source assignments and active windows

There are 8,118 assignments across 22 scopes, 12 regions, 227 UTC dates and
315 spacecraft/day groups. All five split controls equal 032A's completed
controls by direct comparison, without hashing. Approved identities, baseline
roles and all ten fold counts agree with the approved CSV/JSON. Original,
region/date and spacecraft/day isolation pass. Other-region shared-day unused
counts for folds 001–010 are **14, 14, 0, 0, 2, 1, 0, 1, 1, 0**; exact
membership matches the reference. Evaluation membership agrees between BC
variants and all spectral choices. No 011/012 fold exists.

Source counts remain separate from window selection:

| Experiment | Train base / augmented | Val | Test | Unused base / augmented |
|---|---:|---:|---:|---:|
| baseline | 216 / 258 | 53 | 58 | 42 / 0 |
| loro_001 | 191 / 233 | 50 | 22 | 106 / 64 |
| loro_002 | 154 / 196 | 48 | 59 | 108 / 66 |
| loro_003 | 205 / 247 | 51 | 17 | 96 / 54 |
| loro_004 | 198 / 240 | 49 | 29 | 93 / 51 |
| loro_005 | 205 / 247 | 46 | 21 | 97 / 55 |
| loro_006 | 199 / 241 | 40 | 35 | 95 / 53 |
| loro_007 | 194 / 236 | 48 | 32 | 95 / 53 |
| loro_008 | 177 / 219 | 41 | 65 | 86 / 44 |
| loro_009 | 207 / 249 | 50 | 14 | 98 / 56 |
| loro_010 | 190 / 232 | 49 | 33 | 97 / 55 |

The table below counts all candidate rows, with omitted/role-excluded/overlap
rows included in unused. Both variants have the same val/test selection and
overlap exclusions. All retained training windows stay active.

| Experiment | Train base / augmented | Val | Test | Unused base / augmented | Evaluation overlap |
|---|---:|---:|---:|---:|---:|
| baseline | 15,621 / 18,311 | 933 | 1,262 | 22,755 / 20,065 | 6,067 |
| loro_001 | 14,204 / 16,894 | 892 | 236 | 25,239 / 22,549 | 3,141 |
| loro_002 | 11,333 / 14,023 | 842 | 1,184 | 27,212 / 24,522 | 5,572 |
| loro_003 | 14,062 / 16,752 | 849 | 677 | 24,983 / 22,293 | 4,137 |
| loro_004 | 11,471 / 14,161 | 701 | 1,705 | 26,694 / 24,004 | 6,844 |
| loro_005 | 15,107 / 17,797 | 863 | 267 | 24,334 / 21,644 | 3,127 |
| loro_006 | 14,001 / 16,691 | 728 | 716 | 25,126 / 22,436 | 4,111 |
| loro_007 | 15,447 / 18,137 | 923 | 64 | 24,137 / 21,447 | 2,749 |
| loro_008 | 13,806 / 16,496 | 784 | 893 | 25,088 / 22,398 | 4,523 |
| loro_009 | 14,842 / 17,532 | 863 | 319 | 24,547 / 21,857 | 3,335 |
| loro_010 | 14,878 / 17,568 | 901 | 260 | 24,532 / 21,842 | 3,190 |

### Evaluation geometry

All active val/test half-open rectangles are independently disjoint in original
TIFF coordinates. The following geometry is identical for both BC variants.
Input footprint = nominal disjoint grid + uncovered edges/gaps; nominal grid =
retained selected area + nodata-omitted grid area. Native nodata inside retained
windows is included; artificial padding is excluded. These are source-window
areas, not valid-label support, scores or unique ecological/geographic area.

| Scope | Input footprint | Nominal grid | Retained selected | Edges/gaps | Nodata-omitted grid |
|---|---:|---:|---:|---:|---:|
| baseline | 906,445,909 | 872,744,371 | 557,094,374 | 33,701,538 | 315,649,997 |
| loro_001 | 491,404,274 | 470,156,433 | 285,910,815 | 21,247,841 | 184,245,618 |
| loro_002 | 764,559,366 | 715,437,310 | 514,481,951 | 49,122,056 | 200,955,359 |
| loro_003 | 571,667,589 | 555,611,202 | 386,255,897 | 16,056,387 | 169,355,305 |
| loro_004 | 1,101,905,805 | 1,077,923,602 | 622,892,831 | 23,982,203 | 455,030,771 |
| loro_005 | 487,638,513 | 472,379,550 | 287,223,143 | 15,258,963 | 185,156,407 |
| loro_006 | 568,071,205 | 537,059,974 | 372,236,263 | 31,011,231 | 164,823,711 |
| loro_007 | 418,368,754 | 396,585,918 | 252,957,471 | 21,782,836 | 143,628,447 |
| loro_008 | 726,223,488 | 709,503,515 | 420,531,452 | 16,719,973 | 288,972,063 |
| loro_009 | 500,934,755 | 476,320,702 | 302,834,463 | 24,614,053 | 173,486,239 |
| loro_010 | 527,627,170 | 503,292,862 | 298,377,503 | 24,334,308 | 204,915,359 |

### Existing source label support

Reused `source_foreground_pixels` and `scoreable_pixels` from the approved
`analyses/task032_mixed_satellite_day_approved_v1/source_assignments.csv`; no
new label scan or overlapping-window foreground sum was used. Mean fraction
is the arithmetic mean of each TIFF's kelp/scoreable fraction.

| Scope | TIFFs | Dates | Mean kelp pixels/TIFF | Mean labeled kelp fraction/TIFF |
|---|---:|---:|---:|---:|
| All | 369 | 227 | 104,000.95 | 2.6699% |
| Base train | 216 | 157 | 118,088.38 | 3.1483% |
| Primary augmented train | 258 | 167 | 109,029.07 | 2.8635% |
| Validation | 53 | 44 | 50,606.94 | 1.4549% |
| Test | 58 | 47 | 130,425.55 | 2.9190% |
| Training-only 011/012 | 42 | 13 | 62,438.33 | 1.3991% |

Source date support spans **2020-04-22 through 2022-12-28**. Source totals by
region 001–012 are **22, 59, 17, 29, 21, 35, 32, 65, 14, 33, 12, 30**;
distinct date counts are **22, 59, 17, 29, 21, 19, 32, 65, 14, 33, 12, 3**.
The local compact `analyses/task032b_source_summary.json` preserves exact
region/date ranges, region/role support, means and validation. These describe
supplied-label source statistics, not unique ecological area or model quality.

### Local verification artifacts

Under the local root, `analyses/task032b_release_summary.json` records all
canonical counts, inventories, per-scope selections, unused reasons and
coverage. `analyses/task032b_selection.log` contains source-level coverage.
`examples/check_task032b_release.py` is the one-off producer for those checks:
metadata-only joins/geometry, one file inventory/stat pass and **21** bounded
8/4/3-band loads across seven representatives. Shape, band order, true sizes,
zero image padding, -100 target padding and separate nodata masks pass. It
does not audit every NPZ or remap labels.

### Box publication and bounded restoration

All four releases in the table above are published at their matching
`kelp-box:kelpseg/` paths. Ordinary explicit `rclone copy` commands ran
sequentially with `--immutable --size-only --ignore-checksum`; the large chip
copy used eight transfers/eight checkers, and the three small copies and both
fetches used one transfer/two checkers. There was no deletion-propagating sync.
The chip copy encountered a brief DNS outage affecting 22 files; rclone's
normal second attempt completed inside the same command, which exited **0**.
No preparation was rerun and no custom retry/recovery mechanism was added.
All remaining copy/fetch commands exited **0**.

After publication, one complete local/Box comparison matched every relative
file path and size for each release: **26,577 / 5 / 1 / 28 files**, with the
exact byte totals in the release table. No hashes were requested or compared.
Ordinary logs are `analyses/task032b_upload_{chips,splits,collection,tiny}.log`
and `analyses/task032b_fetch_{production,tiny}.log`. The release sizes in the table use actual file inventories rather than
copy-progress byte counters.

Production restore root:
`/Volumes/x10pro/kelpseg/restores/task032b_production_v1/`. It contains
**17 files / 21,258,275 bytes**, including all ten chip/split/declaration controls
and seven NPZs, below the total 128 MiB budget. All restored relative paths and
individual sizes match the selected local originals. Complete `windows.csv`,
`sources.json` and assignments remain available to resolve the subset; only
downloaded payloads were loaded. Representatives cover active baseline train,
val and test, training-only 011 and 012, a background-only test window and a
canonical partial edge. **21** restored 8/4/3-band image/label/nodata-mask
comparisons and true-shape/padding/band-name checks pass against local originals.

The partial canonical example is
`001_20200422_173136_2277/r512_c2304.npz`, true size 512 x 445, padding
`(0, 0, 0, 67)`. It is deliberately `unused/evaluation_overlap` in the baseline:
its successful restoration demonstrates that reader exclusion did not delete
its payload. The background-only active test example is the same source at
`r512_c2048.npz`. The declaration's chip, split and collection-CSV paths resolve
and load from the new root. Its cleaned reference resolves lexically to the
proper project-relative location; cleaned TIFFs are intentionally absent from
this bounded sample and are not needed to load NPZs. This is path/size and
bounded array verification, not checksum verification or a full restored-payload
audit.

### Fetched tiny v2 offline walkthrough

Fresh root: `/Volumes/x10pro/kelpseg/restores/task032b_tiny_v2/`. The fetched
`data/examples/tiny_ca_bc/v2/` has **28 files / 82,537,678 bytes**; every
relative path and individual size matches the original input release. This
separate fetch is below 128 MiB and is independent of the production sample's
budget.

After fetching, the installed split dry-run/write and chip dry-run/write ran
sequentially with `uv run --offline --no-sync kelpseg ...`, using the existing
recipes. Outputs are `examples/runs/offline-v2-splits/` and
`examples/runs/offline-v2-chips/` below this fresh root. No Box access occurred
during split/chip/selection/loading. There are **63 generated files /
151,566,954 bytes**, below 1 GiB: five split controls and 54 NPZs/four chip
controls. All 54 candidates remain canonical, including 31 background-only
windows, with no nodata omission. Source counts remain base 2/2/6/3 unused
and augmented 5/2/6/0.

All six active selection counts reproduce 032A.1:

| Scope | Train | Val | Test | Unused |
|---|---:|---:|---:|---:|
| baseline/base | 8 | 2 | 7 | 37 |
| baseline/augmented | 20 | 2 | 7 | 25 |
| loro_002/base | 4 | 1 | 6 | 43 |
| loro_002/augmented | 16 | 1 | 6 | 31 |
| loro_003/base | 4 | 1 | 5 | 44 |
| loro_003/augmented | 16 | 1 | 5 | 32 |

Tiny baseline geometry is 4,719,360 input footprint pixels, 2,228,736
nominal/retained selected pixels and 2,490,624 uncovered edge/gap pixels.
LORO 002 is 3,539,712 / 1,704,448 / 1,835,264; LORO 003 is
3,538,944 / 1,572,864 / 1,966,080. These triples are input / selected /
uncovered, identical between variants, with zero nodata-window omissions.
They are geometric crop-window counts, not full-release coverage estimates.
**12** representative spectral array comparisons pass, including the active
512 x 257 test edge with `(0, 0, 0, 255)` zero/-100 padding.

`examples/check_task032b_restores.py` runs the bounded checks and four offline
installed commands in a plain sequence. Results are
`analyses/task032b_restore_result.json` and `analyses/task032b_restore_check.log`.
The plain production subset list is `analyses/task032b_restore_files.txt`.
These are local task evidence outside Git; the release tables and results here
retain the durable handoff. No new transfer receipt or authentication catalog was created.

### Researcher instructions, validation and simplicity

Changed repo files: `README.md`, `docs/index.md`, `docs/architecture.md`,
`docs/data_artifacts.md`, `docs/box_backup.md`, `docs/quickstart.md`,
`docs/todo.md`, this task and `tasks/README.md`. The quickstart now gives actual
release locations/counts, fresh-root copy commands, explicit reader roots,
primary/comparison selection, path/error remedies and tiny-v2 fetch/offline use.
Fresh roots include a `runs/` directory and both local path settings are explicit.
No package code, dependencies, recipe values or obsolete options changed or
were removed in this production task.

Production previews/writes, approved metadata comparison, all 22 scientific
source/window selections, canonical inventories, bounded native/RGB+NIR/RGB
loading, four Box inventory comparisons, both restores and offline tiny
walkthrough pass. Markdown links/anchors, shell/Python snippets and
`git diff --check` pass. Repository changes are documentation only; unrelated
full tests/lint and earlier source/cleaned payload QA were not repeated.

Simplicity: one canonical payload collection, five ordinary split controls and
a 539-byte declaration; no fold/per-band payload copies, hard links, new hashes,
checksums, receipts, service/framework, recovery system or concurrent-edit
guards. Validation uses metadata, file sizes and bounded arrays. All original,
organized, cleaned and earlier tiny releases remain unchanged. The transient
copy DNS errors are resolved; no implementation blocker remains. Existing
physical-band assumptions, supplied-label claim limits and geometric/label-area
distinctions remain explicit.

### Exact handoff and next action

Task 032B is complete. Stop here. **No Task 033 implementation ran in this
window.** The next action is to review/refine its small baseline-recipe and
portable-model contract in its own window, then implement only that selected
task. Concurrent Task 033 planning edits were preserved and excluded from this
commit, including their hunks in shared documentation/queues.

Use local root `/Volumes/x10pro/kelpseg` or restore the matching Box layout.
Collection: `data/collections/ca_bc/v1/collection.json`; chips:
`data/chips/ca_bc/v1`; assignments: `data/splits/ca_bc/v1/assignments.csv`.
Code producer: `0596ab7e5fe3d7024e71fe01ea518dd74532812e`; recipes:
`configs/chip/planet8.toml` and `configs/split/ca_bc_v1.toml`.

Call `select_windows(chip_root, assignments, experiment="baseline",
variant="augmented")` for the primary baseline, `variant="base"` for the
comparison, and `experiment="loro_001"` through `"loro_010"` for folds. Filter
active `row["split"]` before loading; a payload alone does not imply selection.
Use `load_chip(..., selection="all"/"rgbnir"/"rgb")` on the same payloads.
Select checkpoints with validation only and preserve the held-out test list.
Apply the separately selected Task 033 training recipe without changing
canonical data or approved source memberships. Reuse the published tiny-v2 quickstart with fresh
run names for later local model checks.

Tasks 035/036 retain temporal-consistency reporting: represented region/year/
month and label prevalence, signed area error and supported matched-footprint
changes, explicit coverage and California/Baja scope. This mixed temporal
baseline is not a uniform future-year benchmark. No training, prediction,
scoring or Task 033 implementation ran here.
