# Task 032A: Implement the approved source splits

Status: Complete — 2026-10-28. Approved split unchanged; stop before Task 032B.
Depends on: completed Task 031. Execute only this task, then hand off to 032B.

## Abstract

Add one small installed split command, reusable source/window selection
functions and the split stage of the tiny walkthrough. Use the approved
mixed temporal split and spacecraft/day grouping. This task implements and
checks the workflow; 032B runs full chipping and Box publication.

## Read and inputs

Follow `AGENTS.md`, `docs/index.md`, `docs/todo.md`, `tasks/README.md`, then read
[documentation](../docs/documentation.md), [splits/loading](../docs/architecture.md#splits-and-loading),
[current research scope](../docs/product.md#california-target-and-temporal-consistency),
[artifact policy](../docs/data_artifacts.md#box-project-organization-and-upload-verification),
and [the implemented chip interface](../docs/quickstart.md#chip-cleaned-imagery).
Task 031's outcome is the implementation handoff; earlier draft debates are
[history](history/032_split_planning.md), not required reading.

Local inputs under `/Volumes/x10pro/kelpseg/`:

- `data/3_cleaned/ca_bc/v1/sources.json`: trusted source identities, headers and
  paths. Read controls only; no payload verification, cleaning or repeated QA.
- `analyses/task032_mixed_satellite_day_approved_v1/`: approved
  `source_assignments.csv`, `region_summary.csv`, `split_decisions.json`.
  The CSV's historical column name is `proposed_role`; its memberships are
  approved. Compare generated memberships with it; do not treat the name as
  permission to redesign the split.
- `data/examples/tiny_ca_bc/v1/` and `examples/runs/task031_tiny_v1/`.
- Existing scientific assertions in `tests/test_materialize_planet8b_folds.py`.

## User decisions required

None for the scientific split or the bounded implementation below. Do not ask
again about dates, directions, spacecraft/day groups, BC roles or proportions.
Training sampling/background exclusions are a later training-recipe decision;
this task keeps all canonically retained chips. No model training is authorized.

## Approved grouping and mixed split

Keep `(dataset_id, release_id, source_id)` together, including every crop/chip.
Keep each region/date group intact. Within every experiment/fold, a physical
`(satellite_id, UTC acquisition_date)` group contributes to at most one of
train/validation/test across **all** regions. The spacecraft may cross splits
on different dates. Reuse assignments across 8/RGB+NIR/RGB inputs.

For reverse rows, dates through cutoff 1 are test, through cutoff 2 validation,
and later dates training. For forward rows, those roles are train, validation,
then test. Both cutoffs are inclusive. Region codes stay strings with zeros.

| Region | Direction | Cutoff 1 | Cutoff 2 | Train / val / test TIFFs |
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

Totals: **216 / 53 / 58** original TIFFs in regions 001–010. Regions 011
(Calvert Island, 12 TIFFs) and 012 (BC tiles, 30 TIFFs) form one optional
training-only group. Produce `base` (without both) and `augmented` (with both)
variants; validation/test and 001–010 memberships stay identical. Baseline
augmented training is **258** TIFFs. Neither 011 nor 012 creates a test fold.

Generate one LORO fold per present evaluation region (ten for the full scope):

1. Held-out region, all dates: test.
2. Other-region companions sharing any test spacecraft/day: unused.
3. Remaining evaluation regions: baseline train stays train, baseline val stays
   val, baseline test stays unused.
4. Optional 011/012: unused in `base`, training in `augmented`, subject to rule 2.

Record explicit unused reasons and validate group isolation separately per fold.
Do not restore the old non-overlap evaluation grid or positive-only training.
The mixed baseline is not a uniform future-year benchmark. Temporal/prevalence
reporting remains assigned to Tasks 035/036 in `docs/experiments.md`.

## Implemented interface

The installed interfaces implemented in this task are:

- `src/kelpseg/prepare/split_inputs.py`: one recipe definition, source controls/
  CSV normalization, spacecraft extraction and chip-metadata export.
- `src/kelpseg/prepare/splits.py`: assignment, validation, summary/write functions
  and a small source-to-window selector.
- `src/kelpseg/cli/split.py`: thin handler, registered in the existing app.
- `configs/split/ca_bc_v1.toml`: the table above plus
  `training_only_regions = ["011", "012"]`; strict unknown-setting checks.
- Focused tests, installed-package checks and researcher recipes.

```text
kelpseg split (--cleaned <root> --release-id <version> | --sources <CSV>)
  --recipe <TOML> --output <fresh-directory> [--dry-run]
```

`--cleaned` reads the existing cleaned `sources.json`, taking `dataset_id` from
its identities and the explicit release ID. `--sources` reads ordinary declared
source rows, including Task 031's identity CSV. Dataset/release/source/region/date
are required for scientific splitting; other datasets may supply explicit
`satellite_id`. The current Planet convention can resolve it from original
`source_id`, excluding crop suffixes. Do not infer identity from row order or
machine paths. Support region subsets and combinations through explicit CSV
rows with namespaced identities; no collection-management framework.

Use ordinary recipe keys: `schema_version`, `training_only_regions`, and
`[[regions]]` rows with `region`, `direction`, `first_cutoff`, `second_cutoff`.
Only regions present in the selected collection produce folds; a selected
evaluation region needs a rule. This allows the same recipe on tiny subsets.

For full cleaned inputs, chip `source_key` must equal the canonical image stem,
not the organized catalog's shorter `source_key`. For cropped inputs preserve
the crop key, original source ID, offsets and original dimensions. Multiple crops
of one original source inherit one assignment. Reject conflicting identities,
missing joins and known duplicate aliases; do not add content-hash discovery.

Write only `collection.csv`, `chip_metadata.csv`, `assignments.csv`,
`recipe.json`, `summary.json`. Keep generation rules in Git and real generated
rows outside Git. `collection.csv` has the normalized original/crop identities
and satellite/day fields; dataset/release references are explicit. Paths, when
stored, are relative to their owning manifest; runtime roots are explicit.
`chip_metadata.csv` uses **exactly** Task 031's accepted identity columns, without
`satellite_id`. `assignments.csv` has one row per original source, experiment
(`baseline`/`loro_<region>`) and variant, with split or unused plus reason.
Carry dataset/release/source, region, date and satellite identity in those rows.

Print resolved paths, source/region/date counts and split totals. Dry-run runs
metadata validation without writes or image reads. Normal output is one pass
into a fresh sibling incomplete directory, then renamed when complete. Use
ordinary logging and stop on failure. No resume, hashes, receipts, locks,
concurrent-edit guards or repeated upstream audits.

Expose a plain function selecting existing Task 031 window rows for an
experiment/variant: join `windows.csv` to its list-shaped `sources.json` by
`source_key`, then to original-source assignments. Window identity is chip-root
reference plus `source_key,row,col`; no `chip_id` column exists. Retained payload
paths resolve from that chip root; omitted windows have no payload. Return
selection/unused reasons without writing per-fold payload copies or link trees.
Do not reread NPZ arrays just to validate a manifest join.

Before coding, add a short checklist here for the input/output fields, joins,
assignment order and tests. Routine file/function choices need no approval.

## Tiny v2 and exact smoke

The existing nine crops have **no CA train/validation sources** under the locked
split: all six 002/003 crops are test and three 012 crops are optional training.
Preserve v1. Make local `data/examples/tiny_ca_bc/v2/` by copying those inputs
and adding four 768-square georeferenced crops from the cleaned release:

| Source | Role | Crop row / column |
|---|---|---|
| `002_20210403_173122_2429` | train | 1024 / 768 |
| `002_20210228_182240_2406` | val | 1024 / 768 |
| `003_20210611_183251_2419` | train | 1536 / 1024 |
| `003_20210503_175430_2276` | val | 1536 / 1024 |

Header metadata confirms these windows fit. Check the actual bounded crops
when creating them; if one supplies no supervised retained window, choose a
nearby window of the **same source**, recording the offset. Never change its
partition. Keep v2 inputs below 128 MiB and generated example outputs below
1 GiB. Preserve v1's 769-pixel partial-edge example. No full-TIFF scan is needed.

Use the new command on v2 metadata, then the existing chip command with its
exported `chip_metadata.csv`. Run under fresh `examples/runs/task032a_*`
directories. Expected base source counts: **2 train / 2 val / 6 test**, plus
3 optional training sources in augmented. Exercise the two 002/003 LORO folds,
source-to-window selection and 8/4/3 loading, including partial-edge padding.
All routine commands and Python calls must be copyable in the quickstart.
Publishing v2 belongs to 032B; automated fixtures require no Box access.

## Validation and acceptance

- Metadata-only full-catalog generation reproduces the approved 369-source
  snapshot and 216/53/58 base membership; augmented adds only 42 training sources.
  Check all ten LORO folds against the recorded metadata counts in the approved
  JSON. Its `train_tiffs_with_optional_group` reference counts are augmented;
  derive base counts by omitting optional training rows. This is a bounded
  metadata check, not production chipping.
- Focused fixtures cover forward/reverse boundaries and equality, shared groups
  across regions, crops of one original, date groups, duplicate/missing keys,
  optional training-only roles and explicit LORO companion/test exclusions.
- The tiny v2 smoke above passes without changing approved memberships. Report
  source counts separately from window counts; do not sum overlapping window
  foreground counts as unique area. Mean source kelp counts/fractions use the
  existing source statistics, not a new label scan or model evaluation.
- Current baseline may retain BC token `241` explicitly: its four tiles are
  all 2021-08-13, with no evaluation source that day. Do not guess a full ID.
  Unknown identity on a date shared with evaluation cannot silently pass.
- Port useful legacy split assertions; remove replaced generators/materializer
  only after checking their remaining consumers. Archive tracked historical
  split CSVs outside Git before removing them; keep old consumers working until
  replaced, and do not widen this task into their rewrite.
- Run focused tests, wheel/sdist checks, `uv run ruff format --check .`,
  `uv run ruff check .`, `uv run pre-commit run --all-files`, docs link checks
  and `git diff --check`. Record unrelated preexisting failures.

Acceptance: the installed command/functions, approved recipe, metadata-only
full-scope comparison and tiny v2 smoke pass; output manifests are portable;
the quickstart covers routine use/errors; source assignment never requires
per-fold data copies. No full chip release, Box publication, training, prediction,
scoring, new ingestion, general recovery system or new hashing/receipt work.

## Outcome and handoff

Record changed files, removals, exact local tiny/metadata paths, validation,
limitations and simplicity check. Give 032B the final CLI/function names,
`chip_metadata.csv` schema, recipe path and copyable full production commands.
Confirm all locked memberships remain unchanged, update both queues, then stop.
Next task is [032B](032b_produce_and_publish_chip_release.md).

## Implementation checklist (2026-10-28)

- Normalize cleaned controls or declared CSV rows to Task 031 identity columns
  plus satellite ID; preserve original/crop keys, offsets and dimensions. Export
  exactly `IDENTITY_COLUMNS` for chipping, excluding satellite metadata.
- Deduplicate original identities by dataset/release/source; reject conflicting
  crops, duplicate crop keys and declared original-TIFF aliases. Resolve Planet
  spacecraft from the original source convention, never crop keys.
- Apply inclusive temporal cutoffs, optional training roles, then LORO held-out
  test, companion exclusions and remaining baseline roles in that order.
  Validate region/date and satellite/day isolation per experiment and variant.
- Publish five plain controls through one fresh incomplete sibling. Join windows
  via chip-root/source_key to namespaced original assignments; retain omitted
  and unused reasons without reading arrays or creating per-fold payloads.
- Test boundaries, grouping, crops/aliases, malformed settings/joins and optional
  roles; exercise the installed distributions. Compare all 369 source memberships
  and ten folds with approved metadata; build only the 13-crop tiny v2, select
  windows and verify all spectral loads and preserved partial-edge padding.
- Update routine researcher recipes, record exact artifacts/checks/handoff,
  close both queues and stop before 032B or any publication/full chipping.

## Outcome (2026-10-28)

Implemented the approved split with plain functions and five portable controls.
All 369 original memberships and all ten LORO metadata counts match the approved
reference. No split decision was changed. No full-dataset chips, Box operation,
training, prediction or scoring ran. Task 032A is complete; Task 032B is next
and has not started.

### Implementation and removal

Added `prepare/split_inputs.py`, `prepare/splits.py`, `cli/split.py`,
`configs/split/ca_bc_v1.toml` and `tests/test_splits.py`; registered `split` in
`cli/__init__.py`. Extended the installed wheel/sdist and CLI tests in
`tests/test_distribution.py` and `tests/test_package_cli.py`. Updated researcher
instructions and current-facing status in README, index, architecture,
data-artifact policy, quickstart and both queues.

`read_collection(cleaned=..., release_id=...)` trusts the existing cleaned
source controls; `read_collection(sources=...)` normalizes an ordinary CSV.
`load_split_recipe`, `assign_sources`, `validate_assignments`,
`summarize_assignments`, `write_splits` and `select_windows` are the reusable
functions. Original identities are `(dataset_id, release_id, source_id)`;
collection rows retain crop keys/offsets/dimensions. Full-source chip keys are
canonical image stems, not shorter organizer catalog keys. Planet dates and
known spacecraft tokens are checked against supplied metadata; spacecraft
whitespace is normalized. Unresolved `241` remains literal on its optional-only
date; no full ID is guessed. Unknown spacecraft on evaluation dates fail.

Output contains only `collection.csv`, `chip_metadata.csv`, `assignments.csv`,
`recipe.json` and `summary.json`. Controls contain no machine paths; dataset/
release references are explicit. The exact chip export columns are:

```text
source_key,source_id,original_tiff,dataset_id,release_id,region,acquisition_date,row_offset,col_offset,original_height,original_width
```

`select_windows(chip_root, assignments, experiment="baseline", variant="base")`
accepts an assignment CSV path or rows. It joins `windows.csv` through the
list-shaped `sources.json` to original assignments. Returned window identity is
`(chip_root, source_key, row, col)`, payloads resolve from the explicit root,
and omitted windows stay unused with their disposition as reason and no payload.
No NPZ is opened for this join. Retained background/overlapping windows remain;
there are no non-overlap or foreground eligibility filters.

Removed `scripts/create_temporal_baseline_split.py` after checking consumers.
Archived its source and both historical tracked split CSVs at
`/Volumes/x10pro/kelpseg/analyses/task032a_legacy_split_reference_v1/` using
ordinary copies. Retained both tracked CSVs: `prepare/legacy_catalog.py` still
reads `planet8b_image_splits.csv`, while the legacy comparison script defaults
to `planet8b_temporal_image_splits.csv`. Retained the old fold materializer and
its tests because `run_context.py`, comparison/evaluation and legacy recipes
still consume its link-tree controls. Rewriting those consumers is out of scope.
Useful duplicate/join, original/date isolation and LORO role assertions were
ported into the new manifest tests.

Simplicity check: one recipe schema, straightforward source/fold loops and
ordinary CSV/JSON. Publication uses a fresh incomplete sibling and final rename.
No new hashing, checksum catalogs, receipts, locks, recovery/reuse, concurrency
protection, payload discovery or repeated upstream audits were introduced.

### Full metadata check

Generated only controls at
`/Volumes/x10pro/kelpseg/analyses/task032a_full_metadata_v1/` from the trusted
cleaned `sources.json`; no TIFF was opened. There are 369 originals/crop rows,
12 regions, 227 distinct dates and 315 spacecraft/day groups. All reference
`source_id`, date/spacecraft and approved `proposed_role` memberships agree.
Base baseline is **216 train / 53 val / 58 test / 42 unused**; augmented is
**258 / 53 / 58 / 0**. The ten folds match the approved JSON's augmented counts,
shared-day exclusions and zero partition conflicts. Base fold counts were
checked by removing optional training rows, without changing evaluation roles.

Comparison and source-support summary:
`/Volumes/x10pro/kelpseg/analyses/task032a_metadata_comparison_v1.json`.
Prior supplied-label source statistics give mean kelp pixels/TIFF and mean
scoreable kelp fraction/TIFF of 118,088.38 / 3.1483% (base train),
50,606.94 / 1.4549% (validation), 130,425.55 / 2.9190% (test), and
109,029.07 / 2.8635% (augmented train). Validation/test are unchanged.
These reuse existing source statistics, not new label scans, overlapping-window
sums, model accuracy or unique ecological area.

### Tiny v2 and exact artifacts

- Preserved v1 at `/Volumes/x10pro/kelpseg/data/examples/tiny_ca_bc/v1/`.
- V2 inputs: `/Volumes/x10pro/kelpseg/data/examples/tiny_ca_bc/v2/`.
- Bounded crop producer: `/Volumes/x10pro/kelpseg/examples/make_tiny_ca_bc_v2.py`.
- Splits: `/Volumes/x10pro/kelpseg/examples/runs/task032a_tiny_splits_v1/`.
- Chips: `/Volumes/x10pro/kelpseg/examples/runs/task032a_tiny_chips_v1/`.
- Smoke results: `/Volumes/x10pro/kelpseg/analyses/task032a_tiny_smoke_v1.json`.

V2 copies all nine v1 crop pairs unchanged and adds the four contract sources
at exactly the approved offsets (002: 1024/768; 003: 1536/1024). Each new
768-square crop supplies four supervised retained windows; no nearby replacement
or partition change was needed. Added imagery/labels match their bounded cleaned
windows and georeferenced placement. V1 TIFF copies match byte-for-byte.
V2 has 28 files totaling **82,537,678 bytes**, below 128 MiB. It is local only;
publishing/fetching v2 belongs to Task 032B.

The installed split and chip previews and writes passed sequentially using the
exported identity CSV. Base source counts are **2 / 2 / 6 / 3**; augmented is
**5 / 2 / 6 / 0**. Only the two present evaluation regions generate folds.
The chipper retained all **54** candidate windows, including **31** without kelp,
with zero nodata omissions. Chips total **151,552,032 bytes**, split controls
**14,922 bytes**; combined generated outputs are below 1 GiB.

| Experiment/variant | Train windows | Val | Test | Unused |
|---|---:|---:|---:|---:|
| baseline/base | 8 | 8 | 26 | 12 |
| baseline/augmented | 20 | 8 | 26 | 0 |
| loro_002/base | 4 | 4 | 22 | 24 |
| loro_002/augmented | 16 | 4 | 22 | 12 |
| loro_003/base | 4 | 4 | 20 | 26 |
| loro_003/augmented | 16 | 4 | 20 | 14 |

All six window selections preserve identical window identities. Every retained
window loaded in native eight, RGB+NIR and RGB modes: **162** successful array/
target comparisons with the local crop windows. The two 512-by-257 edge windows
retain `(0, 0, 0, 255)` padding; image zero and target -100 padding invert exactly.
Source counts and window counts are separate; foreground window counts were
not summed as unique area. The quickstart includes copyable split → chip →
select/load commands and common error fixes.

### Validation

Passed **182 focused tests**, including the new split fixtures, chipping/loading,
shared label/alignment/nodata assertions, CLI/progress, retained legacy fold
assertions and isolated wheel/sdist installation outside the checkout. Installed
checks cover metadata-only dry-run/write, exact chip-export columns and lazy
help without ML imports. Synthetic fixtures need no Box, GPU or research inputs.

`uv run ruff format --check .`, `uv run ruff check .` and
`uv run pre-commit run --all-files` passed. Explicit pre-commit checks also cover
all new untracked files. Checked 127 local links/anchors and 35 fenced blocks
across the eight changed Markdown files; Python snippets parse and
`git diff --check` passes. No unrelated failure was observed in these checks;
the full legacy suite was not rerun. Final runtime assignments exactly reproduce
the saved full-scope controls after the review fixes.

### Exact handoff to Task 032B

Next action: select and execute only
[Task 032B](032b_produce_and_publish_chip_release.md), reading its entry route
and this outcome. The splitter and chipper are installed. Use
`configs/split/ca_bc_v1.toml` and `configs/chip/planet8.toml`; keep the chip
export schema above unchanged. Later production commands, **not run in 032A**:

```bash
(
  set -e
  KELP_DATA_ROOT='/Volumes/x10pro/kelpseg'
  mkdir -p "$KELP_DATA_ROOT/data/splits/ca_bc" "$KELP_DATA_ROOT/data/chips/ca_bc"
  uv run kelpseg split --cleaned "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1" --release-id v1 --recipe configs/split/ca_bc_v1.toml --output "$KELP_DATA_ROOT/data/splits/ca_bc/v1" --dry-run
  uv run kelpseg split --cleaned "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1" --release-id v1 --recipe configs/split/ca_bc_v1.toml --output "$KELP_DATA_ROOT/data/splits/ca_bc/v1"
  uv run kelpseg chip --images "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1/images" --labels "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1/labels" --metadata "$KELP_DATA_ROOT/data/splits/ca_bc/v1/chip_metadata.csv" --recipe configs/chip/planet8.toml --output "$KELP_DATA_ROOT/data/chips/ca_bc/v1" --dry-run
  uv run kelpseg chip --images "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1/images" --labels "$KELP_DATA_ROOT/data/3_cleaned/ca_bc/v1/labels" --metadata "$KELP_DATA_ROOT/data/splits/ca_bc/v1/chip_metadata.csv" --recipe configs/chip/planet8.toml --output "$KELP_DATA_ROOT/data/chips/ca_bc/v1"
)
```

Inspect storage and preview output as required by 032B before writing the full
release. The separate analysis-only full metadata check above is already valid;
032B owns the fresh production paths, portable collection declaration, ordinary
Box copies, bounded restore/load and tiny-v2 publication/fetch. Retain the
historical CSV/materializer consumers until their later replacements.

No unresolved implementation blocker remains. The mixed split is not a uniform
future-year benchmark; labels and band-order assumptions retain their recorded
limits. Tiny crop support does not establish full-release retained-window
coverage. Tasks 035/036 still own prevalence/temporal model reporting.

## Researcher usability follow-up checklist (2026-10-28)

Status: Complete; this follow-up remains within Task 032A.

- Keep current modules, public interfaces, manifests and approved assignments.
  Extract only single-row normalization from collection-wide identity checks.
- Identify actual unknown/missing recipe keys and the affected region; include
  source and input-row context in CSV errors. Preserve strict validation.
- Add short inline comments explaining scientific grouping, assignment order,
  crop joins and publication, and ordinary progress logs for input controls,
  source/fold counts, validation, file writes and large manifest joins.
- Make local tiny v2 the primary walkthrough, with one researcher-editable
  name for fresh output paths; retain v1 and its fetch recipe.
- Run focused/installed tests, compare saved full and tiny controls without
  reading payloads, check docs/lint/pre-commit and record the result.
  Stop before 032B, production chipping or Box work.

## Researcher usability follow-up outcome (2026-10-28)

Applied the requested small readability/usability cleanup without changing the
module layout, public functions/CLI, five-file schema, recipe or approved split.

- `prepare/split_inputs.py`: extracted `_normalize_source_row` from
  collection-wide duplicate/original/alias checking. Recipe errors list actual
  unknown/missing keys and the affected region rule. CSV errors locate the source
  and input row, counting the header as row 1. Added inline comments for original
  IDs, crop placement and canonical cleaned keys.
- `prepare/split_inputs.py` and `prepare/splits.py`: ordinary progress logs show
  recipe/control paths, control bytes, row/original counts (every 100 source rows
  plus completion), each baseline/LORO assignment phase, group validation, each
  output file and publication. Window selection logs its input controls, joins
  and every 10,000 window rows plus completion. Library code uses logging only;
  existing CLI setup shows progress on stderr and restores the caller's logger.
- `prepare/splits.py`: comments explain inclusive chronology, collapsing crops,
  held-out spacecraft/day exclusion order, temporal-test unused roles, atomic
  publication, window placement and omitted payloads. The existing loops and
  scientific checks remain unchanged.
- `docs/quickstart.md`: made local v2 the main walkthrough, with one researcher-
  chosen `example_name` deriving both fresh output paths. Preserved v1 and its
  Box fetch instructions, documented stderr/notebook progress and error fixes,
  and kept historical smoke paths in this task record.
- `tests/test_splits.py`: six focused usability cases cover specific setting/row
  errors, library phase logs, no direct library printing, and CLI dry-run progress/
  logger restoration. Both queues retain Task 032B as the unstarted next task.

Validation passed: **188 focused tests**, including isolated wheel/sdist checks;
Ruff format/check; all-file pre-commit and explicit checks on new files; Markdown
links/anchors, fenced blocks and Python snippets; and `git diff --check`. No
unrelated failure was observed; the full legacy suite was not rerun.

Metadata-only temporary writes reproduced **all five controls byte-for-byte**
for both the saved 369-source full scope (8,118 assignment rows) and tiny v2
(13 sources, 78 rows). All six tiny window selections match saved counts. Those
checks opened no TIFFs or NPZs, retained no new external artifacts, and left
every previous input/output unchanged. No new preparation features, hashes,
receipts, recovery or concurrency machinery were added.

Exact next action remains Task 032B using the installed interfaces and production
commands in the handoff above. This follow-up stops before Task 032B, full-dataset
chipping, Box work, training or model evaluation.
