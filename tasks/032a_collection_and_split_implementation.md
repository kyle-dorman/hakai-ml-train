# Task 032A: Implement the approved source splits

Status: Ready for implementation — plan finalized 2026-10-27. Not started.
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

## Planned implementation and interface

These interfaces are **planned**, not installed yet:

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
