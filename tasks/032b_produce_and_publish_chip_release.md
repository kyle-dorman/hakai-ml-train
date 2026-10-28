# Task 032B: Produce and publish chips and approved splits

Status: Ready after Task 032A — plan finalized 2026-10-27. Not started.
Depends on: completed Task 032A and its passing metadata/tiny-v2 handoff.

## Abstract

Run the implemented splitter and Task 031 chipper on the existing 369-source
cleaned release. Publish one native-band chip set, the approved baseline/LORO
assignments and tiny v2 to Box. Use ordinary sequential commands and compact
summaries; no new framework, hashes or transfer receipts.

## Read and inputs

Follow the entry route, then [032A](032a_collection_and_split_implementation.md),
[quickstart](../docs/quickstart.md#chip-cleaned-imagery),
[artifact policy](../docs/data_artifacts.md#box-project-organization-and-upload-verification),
[documentation](../docs/documentation.md) and 032A's final outcome.
No historical split debate or old checksum protocol is needed.

Under `/Volumes/x10pro/kelpseg/`:

- Cleaned input: `data/3_cleaned/ca_bc/v1/` (369 sources / 12 regions).
- Approved assignment reference:
  `analyses/task032_mixed_satellite_day_approved_v1/`.
- Existing chip recipe: `configs/chip/planet8.toml` (512 size / 256 stride /
  max 50% nodata, true-size edges, native eight bands, canonical backgrounds).
- Implemented split recipe: `configs/split/ca_bc_v1.toml`, after 032A.
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
42 training-only 011/012 sources. There are ten LORO folds, never an 011/012 fold.
All sources belong to the declared scope even if a source produces no retained
window; report that distinction rather than silently changing its assignment.

## Execution plan

Use the final installed interface recorded by 032A. These split commands are
planned here until 032A implements them; `chip` already exists. Set the local
root once. Do not run these commands as part of planning.

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
   paths and source joins using 032A's selector. Load representative retained
   8/4/3 inputs and a partial edge. Do not audit every NPZ or remap labels again.
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
   baseline splits and both training-only regions, with a partial edge and a
   background chip. Include all window metadata needed to resolve those files,
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
  band selection happens while loading. No copied per-fold/per-band datasets.
- All actual candidate/retained/omitted/source counts and bytes reconcile.
  Treat the earlier 40,571-candidate / 26,573-retained analysis as a projection,
  not an exact production promise; investigate unexplained differences without
  automatically changing the approved recipe or memberships.
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
