# Task 029A: Implement raw → organized preparation

Status: Complete — researcher-maintainability follow-up verified, 2026-10-27.

Depends on: Tasks 026–028, now complete. Task 030A owns the full organized
release and its verified Box publication.

Execution: Local implementation, synthetic fixtures, metadata reconciliation,
and bounded real-file smoke checks. Implementation is explicitly authorized.

## Abstract

Implement one understandable organizer for every declared dataset: raw variant
1 becomes an unsplit, short-name variant 2 with unchanged image/label/companion
bytes and explicit provenance. The current 369 CA/BC pairs are the first input
catalog, not a privileged base dataset. A separate independent dataset must
work through the same functions and settings without Python edits.

Stop after implementation, complete metadata planning, and bounded copy tests.
Do not create the full 369-pair release, clean labels, generate splits, or
publish data. Task 029B implements cleanup; Tasks 030A/030B build/publish the
two intermediates. The reusable real-data walkthrough still starts at 031.

## Inputs and reading route

Follow the normal entry path, then read
[architecture.md](../docs/architecture.md),
[data_artifacts.md](../docs/data_artifacts.md),
[cleanup_provenance.md](../docs/cleanup_provenance.md),
[documentation.md](../docs/documentation.md), and
[quickstart.md](../docs/quickstart.md).
Use [Task 026's intermediate design](026_inventory_originals_and_cleanup_provenance.md#organized-intermediate-design-follow-up-2026-10-27)
and [Task 028's outcome](028_package_guide_and_first_removal.md#outcome-2026-10-27).
Consult [Task 027's outcome](027_verify_box_and_back_up_raw_reference_audit.md#outcome-2026-10-27)
and frozen local catalog for raw archive identity; preserve its receipts.

Small evidence tables, not raster payloads, establish the initial declaration:

- `/Volumes/x10pro/kelpseg/merged_all_regions_v1/raster_manifest.csv`:
  369 memberships (339 CA, 30 BC); `source_image`/`source_label` point upstream.
  Never use `merged_image`/`merged_label` as original payloads.
- `/Volumes/x10pro/kelpseg/audits/task026_originals_v1/`:
  `archive_members.csv`, `pairs.csv`, `files.csv`, and
  `lineage_findings.json`. The JSON's `membership.extra_archive_mapping`
  supplies the 14 exact extra-archive mappings.
- The named `merged_ds/merge_manifest.csv`,
  `hakai_match/reconstruction_manifest.csv`, and tracked historical split CSV
  supply recorded-name aliases only; their train/val/test columns do not
  establish assignments for this release.
- Task 027's frozen raw archive catalog supplies archive SHA-256 identities
  and their provenance. Archive indexes/CRCs/sizes are not member SHA-256s.

The six BC full scenes remain raw and outside the selected 30-tile scope.
Keep all 369 pair identities even when image or label bytes repeat. Preserve
325 CA `nan_mask` companions without interpreting their unknown semantics.
Inventory explicitly associated sidecars too: the audit records one CA image
overview and 92 BC tile auxiliaries, including two attached to a **label**.
Do not join sidecars using `files.csv.source_id`: inferred IDs there can still
contain `.tif` or `.TIF.aux`. Freeze exact parent/member associations instead.

## Expected outputs

| Location | Deliverable |
|---|---|
| `src/kelpseg/prepare/organize_inputs.py` | Strict recipe/catalog loading, typed declarations, safe locators and deterministic naming/plan validation |
| `src/kelpseg/prepare/organize.py` | Plain planning, copying, resume, and release-verification functions |
| `src/kelpseg/prepare/legacy_catalog.py`, `tests/test_legacy_catalog.py` | One-time conversion of named historical metadata into the ordinary input schema; mapping/asset/alias regression fixtures |
| `src/kelpseg/cli/organize.py`, `cli/__init__.py` | Thin registered Typer command; no cleanup placeholder |
| `configs/organize/ca_bc.toml`, `configs/regions.csv` | Small hand-authored recipe and stable region mapping; no generated membership manifest in Git |
| `tests/test_organize_inputs.py`, `tests/test_organize.py` | Independent-dataset, provenance, byte preservation, collision, corruption, and restart fixtures |
| Existing CLI/distribution/CI checks | Installed organizer exercised outside the checkout and without legacy imports |
| `docs/quickstart.md`, architecture/artifact contracts as needed | Working organize recipe, input-table instructions, outputs/errors, and clear cleanup/publication boundary |
| This task and both queues | Schema/naming decisions, validation, bounded external outputs, limitations, and exact next action |

Generated input declarations, plans, smoke outputs, and release manifests live
outside Git. Keep small synthetic fixtures in tests; create their archives and
rasters at test time. No new repository `scripts/` helper or storage framework.

## Implementation contract

### 1. Freeze explicit declarations and one naming rule

Before coding, record the final schema, filenames, current-data catalog
construction rules, and bounded smoke selection here. Use strict TOML for the
recipe and UTF-8 CSV for tables, rejecting unknown fields/versions. Keep
machine-specific roots in Task 028's explicit `--paths` file. The recipe's
`input_catalog` is a directory relative to `data_root`, initially
`preparation_inputs/ca_bc/v1`. It contains `deliveries.csv`, `membership.csv`,
`aliases.csv`, and optional `assets.csv`. The tracked `regions` path resolves
against the recipe directory; delivery paths resolve against `data_root`.
Directory-delivery hash-catalog paths resolve against the input catalog.
No machine-specific absolute paths or implicit root discovery in recipes or
portable tables. Local operational records can record resolved absolute paths.

Minimal declared inputs:

- Recipe: `schema_version`, `dataset_id`, `release_id`, `input_catalog`, and
  `regions`. Derive the destination under
  `<data_root>/data/2_organized/<dataset_id>/<release_id>/`.
- Deliveries: unique `delivery_id`, input kind (`zip` or `directory`), relative
  input location, and identity/evidence. ZIPs require a trusted archive SHA-256;
  directory inputs specify a relative `file_catalog` and its SHA-256. That
  frozen CSV has `member_relative_path`, `bytes`, and `sha256` columns, with
  unique paths and a checksum for each selected file. Verify catalog identity
  and selected source hashes; a directory name or timestamp is not its identity.
- Membership: one row per pair with `source_key`, `region_code`,
  `acquisition_date`, `legacy_source_id`, and separate image/label delivery IDs
  and exact member/file-relative paths. Expected member hashes are checked
  when provided; never substitute ZIP CRCs for them.
- Regions: `region_code`, `legacy_region_id`, `region_name`. Preserve 001–011
  and use 012 for legacy `bc`; 005 and 006 remain distinct despite sharing the
  name `channelIslands`. Other datasets can declare independent valid regions.
- Optional assets: owning pair, parent role (image/label/pair), asset kind,
  delivery locator, and explicit relative destination. This includes masks,
  world files, XML, and overviews; do not guess a parent by stripping suffixes.
- Aliases: owning pair/asset and role, exact alias/path, alias type, and evidence
  reference. Distinguish actual archive-member names from recorded legacy names.
  Missing long aliases are allowed and explicitly unverified; do not invent the
  79 CA long names absent from the examined evidence.
  Scope uniqueness/conflict checks by owner, role, and alias type; the same
  alias or original locator can legitimately occur for several pairs/assets.

Use canonical source ID `<region_code>_<source_key>` and primary filenames
`images/<source_id>.tif` / `labels/<source_id>.tif`. `source_key` is supplied
explicitly, beginning with the acquisition date as YYYYMMDD and retaining
scene/time/tile discrimination. The engine does not parse CA/BC filenames.
For example, an existing CA key can remain `20200422_173136_2277`; a BC key
can be `20210812_184548_90_2448_clip5`. Retain exact original names separately.
Freeze case/allowed-character rules and test them before any real copies;
never generate collision suffixes from row order. Dataset ID plus source ID is
the portable pair identity; region/delivery/dataset remain separate concepts.

Primary paths use the canonical name; explicit asset destinations preserve
their association, e.g. `masks/<source_id>.tif` or the renamed parent's sidecar
path. Preserve sidecar **contents** unchanged, including any internal strings;
record the rename and do not claim to repair/reinterpret sidecar semantics.
Reject asset destinations colliding with primary or control-file paths.

Reconcile all 369 declarations and known aliases/companions using only named
metadata tables. Implement `build_legacy_ca_bc_catalog(paths, regions_csv,
destination)` in `kelpseg.prepare.legacy_catalog` as a small, explicit historical-metadata
conversion, separate from the generic organizer. Its inputs are the named
evidence tables above; freeze exact joins, reviewed asset-parent mappings, and
exception rules here before coding. It writes only the external input catalog,
with producer/evidence hashes and atomic completion, never raster payloads.
Refuse conflicting existing catalogs; record its exact invocation and resulting
identity. A planned developer invocation (after implementation) is:

```python
from pathlib import Path
from kelpseg.prepare.legacy_catalog import build_legacy_ca_bc_catalog
from kelpseg.paths import load_paths

paths = load_paths("paths.local.toml")
build_legacy_ca_bc_catalog(
    paths,
    Path("configs/regions.csv"),
    paths.data_root / "preparation_inputs/ca_bc/v1",
)
```

Keep conversion rules/versioned code in Git and generated tables outside Git.
This helper is a one-time reconstruction of existing evidence, not a required
CA/BC ingestion path or an automatic discovery service. A new dataset supplies
the same explicit table schema; it never has to extend the CA/BC catalog or
add a dataset branch to the engine.

### 2. Expose a small command and reusable functions

Planned interface, to be implemented during execution of this task:

```bash
uv run kelpseg organize --recipe configs/organize/ca_bc.toml --paths paths.local.toml --dry-run
uv run kelpseg organize --recipe <smoke-recipe.toml> --paths <smoke-paths.toml>
uv run kelpseg organize --recipe <smoke-recipe.toml> --paths <smoke-paths.toml> --resume
```

Use ordinary `load_organize_recipe()`, `build_organization_plan()`,
`organize_dataset()`, and `verify_organized_release()` functions returning typed
values and raising normal package exceptions. Only Typer presents output and
exit status. Keep imports lazy; help/version cannot load the geospatial stack.
Promote Rasterio into runtime only when using it for actual header inspection;
do not reuse `src.*`/`scripts.*` imports or the old repair-enabled organizer.

Show resolved inputs, selected dataset/release, source/delivery/region counts,
companions, planned destination, and evidence level before copying. Dry-run
validates the whole declared scope and prints the plan without writing files
or hashing/decoding all raw archives. A valid plan is not a verified release.
Organization preserves source band order without selecting/reordering channels.

Use explicit settings only; reject unknown options/keys. Invalid declarations,
missing files, unreadable inputs, or conflicting output produce a useful stderr
message and nonzero status without a traceback. Never require W&B or Box login.

### 3. Plan completely, then copy bytes

- Validate all joins, membership cardinalities, dates, region keys, locators,
  and destinations before writes. Reject missing/duplicate pair IDs and roles,
  dangling owners/conflicting aliases, duplicate table keys, and case-folded
  output collisions. Do not reject alias reuse across different owners or
  deduplicate by alias text or byte hash.
  A repeated source locator can deliberately serve several pairs; duplicate
  physical member entries in a ZIP directory are ambiguous and must fail.
- Stream only declared ZIP members; never `extractall`. Reject traversal,
  absolute/drive paths, symlinks, unsafe member spellings, and duplicate
  normalized member names. Folder inputs also reject escapes/symlinks. Extra
  unselected raw members remain untouched, not errors or implied release members.
- Refuse source/output/staging overlap, silent overwrite, and concurrent writers.
  Copy rather than hard-linking outputs to immutable originals. No reprojection,
  raster rewrite, nodata change, class remap, filtering, or new split assignment.
- Compute SHA-256 while streaming each selected source payload, check expected
  hashes when available, then independently verify output bytes. Record separate
  image/label/asset hashes and sizes. Check source stability around reads; source
  changes, ZIP CRC errors, or byte mismatches prevent completion.
- Reuse trusted Task 027 archive identities with recorded catalog provenance
  and stability checks; do not routinely reread all 23 GB just to establish the
  same parent identity. Rehash affected/untrusted inputs when evidence changes.
  No metadata-only or CRC-only result counts as member byte verification.
- Record actual image/label header metadata after copying: dimensions, band
  count/descriptions, dtype, CRS/transform, and declared nodata. Physical band
  names stay unknown where the source does not establish them; channel count
  is insufficient. Original image/label grids can differ and must not be aligned
  here. Retain each pair even for shared mosaics or repeated image bytes.

### 4. Make interruption and publication explicit

Use a sibling incomplete staging directory on the same filesystem, with a
frozen plan identity and atomic per-file receipts. The portable logical plan
hash covers recipe values, normalized declarations, region/alias/asset tables,
and delivery content identities, excluding resolved machine paths and logs.
Resume requires an explicit `--resume`, the same logical plan/input identities,
fresh resolution of the current machine paths, and byte verification
of completed outputs; timestamps/size or an existing filename do not suffice.
Conflicting/corrupt/unknown files stop rather than being overwritten or removed.
Specify treatment of the command's own interrupted temporary file before
implementation; only an identified incomplete temp file may be recreated.

Final release contents include `images/`, `labels/`, declared companions,
`regions.csv`, `sources.csv`, `filename_aliases.csv`, an assets table when used,
portable recipe/input identity snapshots, and an atomic completion manifest.
Sources record canonical/legacy IDs, date, region, primary output paths, parent
delivery/archive identities and exact member paths, and per-role hashes/sizes.
Alias rows retain exact names, types, roles, and evidence. No source split becomes
an experimental assignment; any delivery train/val path is provenance only.

Validate exact declared inventory and all hashes before publishing the directory
atomically at its final release path. A completed release is immutable; a
repeated matching invocation may verify and report it, never rewrite it.
Keep control-file hashing noncircular. Stable rows/names/identity hashes must
not depend on input order, absolute machine paths, or timestamps. Retain failure
evidence outside final release payloads; no partial directory is called complete.

### 5. Keep real work bounded and document the interface

The full 369-row **metadata plan** is required here. The full payload build,
complete member hashing, production QA, and Box copy are Task 030A.

Before real copying, select a tiny CA/BC sample from member-size metadata,
record identities and total bytes, and set an explicit read/write budget
(default maximum 128 MiB total selected payload). Include a companion and a
grid-mismatched pair if they fit; use synthetic fixtures when real examples
would exceed that budget. Use a separate versioned smoke root outside Git and
the final production release. Read only selected members; do not extract an
entire ZIP to obtain the sample. Record omissions and exact byte evidence.

Extend the researcher guide with the actual input-table/recipe setup,
dry-run/copy/resume recipes, output locations, errors, and adding an independent
dataset through settings. Keep unfinished cleanup/training examples labeled
planned. Do not begin the reusable Task 031 walkthrough or silently add a
permanent catalog/recipe framework. Retire old organization logic only when
its retained consumers/tests have a supported replacement; keep repair and
historical scientific correctness coverage for their later tasks.

## User decisions required

None blocking for this plan. Safe defaults are TOML recipes, explicit portable
CSV inputs, copy mode, 012 for BC, the canonical naming rule above, and a small
bounded smoke. These implement the already agreed three-variant/data-peer
contract. Resolve routine schema details with documented examples and tests.

If evidence contradicts the declared 369 memberships, asset ownership, or an
archive identity, stop the affected real-data operation and present exact
evidence and a proposed mapping correction. Do not drop rows or guess identity.
Mask meanings, annotation coverage policy, band recipes, and cleanup decisions
are not prerequisites for preserving bytes and are deferred to their owners.

The original preparation request authorized planning only. The user explicitly
authorized implementation on 2026-10-27; Task 027 receipts remain immutable.

## Smoke and validation during implementation

1. Confirm the Task 028 baseline and choose a separate environment if Task 027
   still uses `.venv`; never synchronize it underneath the upload thread.
2. Use small synthetic TIFFs/ZIPs/folders for two wholly independent datasets;
   the second uses different source names/regions and can run alone without
   current-data mappings. Verify deterministic IDs/paths under reordered rows.
3. Prove byte identity for images, labels, masks, and image/label sidecars;
   preserve mismatched grids, stored class/nodata values, and band descriptions.
   Preserve repeated images with different labels, shared-label associations,
   and repeated alias text/locators across different owning pairs.
4. Exercise missing/duplicate IDs and pair roles, unknown regions/settings,
   dangling alias owners/conflicting mappings, malformed catalogs, unsafe
   ZIP/folder paths, duplicate ZIP entries, case-folded collisions, and
   input/output overlap.
   Require no-write dry runs and no completed manifest after any failure.
5. Interrupt a fixture after one verified file, resume and verify it, then test
   a corrupted output, changed recipe/catalog/input, unexpected staged file,
   and attempted overwrite of a completed release. Verify atomic completion.
6. Reconcile the current 369-row plan (339 CA/30 BC, 12 regions), all declared
   masks/sidecars, six excluded full scenes, and the 290 known long-alias
   identities. Keep the 79 unverified long aliases explicitly absent. Counts
   are assertions to reconcile, never reasons to discard unexpected evidence.
7. Run the budgeted real smoke, verify hashes/header records and resume, and
   demonstrate installed CLI/library use outside the checkout with only runtime
   dependencies. Extend the distribution test to exercise actual organization.
8. Run focused organizer tests and the retained CPU suite, then
   `uv run ruff format --check .`, `uv run ruff check .`,
   `uv run pre-commit run --all-files`, `uv lock --check`, and a frozen install.
   Run checks through the isolated environment while Task 027 is active.
   Review docs/links and `git diff --check`; record preexisting failures.

## Acceptance criteria

- One Typer command and reusable plain functions organize both the current
  declaration and an unrelated dataset, without code/config inheritance or
  dataset-specific discovery branches.
- The exact schema/naming/region/asset rules and reproducible current-catalog
  construction are recorded; every selected current pair is recoverably mapped
  to original image/label locators. No repaired label is used as an original.
- Fixture and budgeted real outputs preserve payload bytes and scientific
  metadata with portable provenance; missing band/mask semantics remain unknown.
- Collision, corruption, changed-input, overwrite, resume, and atomic-publication
  checks pass. Nothing incomplete is reported as a finished release.
- A researcher can change dataset/roots/release via documented settings and
  tables, preview scope/errors, and understand the resulting outputs without
  Python edits. The guide and offline CPU/distribution checks grow with the code.
- No full production release, Box write, cleanup, chip/split generation,
  inference, or training occurs in this task.

## Non-goals

Task 029B's cleaning implementation, Task 030A's full materialization or upload,
automated discovery of unknown deliveries, source mutation, inferred missing
aliases/bands/classes, deduplication, split assignment, model workflows, a cloud
client, plugin system, or general dataset-management service.

## Outcome template for implementation

Record changed files, actual schemas/naming/examples, direct dependency changes,
removed/reused legacy paths, current-catalog provenance and counts, independent
dataset checks, bounded external artifact paths/bytes/hashes, resume/publication
results, installed-package and retained tests, lint/docs checks, simplicity
check, and unresolved evidence limits. Mark Complete only after acceptance.

Exact next action: scope Task 029B's separate organized → cleaned implementation
contract using Task 026's recorded recipes and scientific evidence limits.
Task 030A remains the later full organized-release build/publication. Update
the queues and stop before executing another numbered task.

## Contract preparation outcome (2026-10-27)

Prepared the organizer contract using read-only repository and named external
metadata review, with independent interface and provenance/asset audits.
No TIFF/ZIP payload reads, archive hashing/extraction, generated input catalogs,
environment changes, or data/Box writes occurred. Task 027 completed in its own
thread during planning; its verified outcome and commit are preserved.

Changed preparation files: this task, `docs/todo.md`, and `tasks/README.md`.
Both reviews clarified shared-alias handling, explicit companion ownership,
directory hash catalogs, portable plan identity, and the versioned metadata-only
catalog converter. All 55 local links/anchors across these three documents
resolve, code fences balance, and `git diff --check` passes. No source tests or
lint were needed for this documentation-only change.

No blocking user decision remains. Exact next action: when implementation is
requested, reread the entry documents and this contract, record the final
schema/mapping examples and bounded smoke selection, mark In progress, then
implement only Task 029A. The plan is linked from both queues; execution stays
Pending and this planning work is complete.

## Frozen implementation decisions (2026-10-27)

Implementation is now authorized. Schema version 1 uses strict UTF-8 CSV:

- `deliveries.csv`: `delivery_id,kind,path,sha256,file_catalog,evidence,verified_bytes,verified_mtime_ns`. The final two fields are optional trusted-identity stability evidence; without them, copy verifies the entire ZIP hash before selected reads.
- `membership.csv`: `source_key,region_code,acquisition_date,legacy_source_id,image_delivery_id,image_member,label_delivery_id,label_member,image_sha256,label_sha256`. Expected role hashes may be blank.
- `aliases.csv`: `source_id,asset_id,role,alias,alias_type,evidence`; asset ID is blank for pair-primary aliases. Multiple recorded names and reuse across owners are valid.
- Optional `assets.csv`: `source_id,asset_id,parent_role,kind,delivery_id,member_relative_path,destination,sha256`.
- `regions.csv`: `region_code,legacy_region_id,region_name`.
- Directory `file_catalog`: `member_relative_path,bytes,sha256`. Its delivery SHA-256 identifies the catalog bytes, and every selected file requires a row.

Dataset/release/delivery/asset identifiers use lowercase ASCII letters, digits,
underscores and hyphens; region codes use lowercase letters/digits. Source keys
use lowercase letters/digits/underscores, start with their YYYYMMDD date and
retain scene/tile discrimination. No automatic collision suffixes. Paths use
relative forward-slash components, without dot/dot-dot, drive prefixes or
backslashes. Destinations reserve control names and their subtrees.

Resume recreates only a command-owned interrupted payload temporary file
identified by the frozen per-file state; unknown temporary files stop. Receipts
verify copied bytes; completed controls are hashed noncircularly by the final
manifest. The final directory appears only after exact-inventory verification.

The mounted `/Volumes/x10pro` was checked before creating the ignored
`paths.local.toml` and any needed output directory. Full metadata planning and
a separately named smoke are the only real-data execution allowed. The smoke
selection is frozen from member sizes before copying, capped at 128 MiB of
selected uncompressed payload; its exact members/bytes are recorded below.

### Frozen historical joins and smoke selection

CA uses 325 exact `images/<legacy>.tif`, `labels/<legacy>.tif`,
`nan_mask/<legacy>.tif` members in `ca_data.zip`; the other 14 use only
`lineage_findings.json:membership.extra_archive_mapping`. BC strips the
`data_root/bc/` prefix from manifest source paths and selects the 30
`10km_tiles` pairs, excluding six `full_scenes` pairs. CA source keys remove
the numeric region prefix; BC keys retain date/time/fraction/scene and clip
number, dropping only the reviewed product fragments.

Companions are joined against exact primary member strings: image plus `.ovr`
or `.aux.xml`, same image stem plus `.tfw`, label plus `.ovr` or `.aux.xml`.
This yields 325 CA masks, the CA overview for
`006_20210611_175348_2235`, 90 BC image auxiliaries and two label auxiliaries
for BC val clip3 of `20210811_184459_09_245c`. `files.csv` inferred source IDs
are never asset join keys. Reconstruction source stems join current legacy
identities; legacy merge image stems/paths and tracked split names are aliases
only. Exactly 260 CA plus 30 BC owners have long names; 79 CA owners remain
without them. No inferred split assignment or companion semantic claim.

The selected real smoke is CA `007_20211212_184127_227a` (image, label,
mask: 6,973,762 bytes) and BC
`20210813_193301_80_241_8_band_Clip3` (image, label, three image sidecars:
14,958,926 bytes). Total selected payload: **21,932,688 bytes**, below the
134,217,728-byte cap. BC has mismatched original grids. The selection covers
mask and sidecar preservation; label-sidecars and extra-archive copies use
synthetic tests in this bounded smoke. Exact archive member names and per-file
byte/hash receipts will remain in the external smoke plan and release.

### Evidence hygiene reconciliation

The first real metadata conversion stopped before writing a catalog because
`planet8b_image_splits.csv` differs bytewise from Task 026's hash. Task 028
explicitly recorded CRLF/end-of-file hygiene in commit `52e6e2b`; parsed rows
remain identical. The pre-028 Git version hashes to the expected
`00a3acc9db79c997b3e42c11bdb50629a338d3ee844fb0189e0238926763268e`
(21,387 bytes); current LF/final-newline bytes hash to
`b26c5fad5d3dfe0935a8091833bd872d818c15ed0b2638d8370832cd10a1bf87`
(21,099 bytes). Reversing only that precise newline normalization recreates
the expected hash exactly. The converter may accept this narrow, explicitly
recorded `old_split` hygiene equivalent, preserving both identities and rule
in its provenance. Any row/content difference still fails. No membership,
asset-parent, archive-identity or experimental-assignment correction is needed.

## Outcome (2026-10-27)

Completed the approved implementation and bounded validation. The installed
`kelpseg organize` Typer handler delegates to plain typed library functions;
no cleanup command or later workflow was started.

### Repository changes and interface

- Added `src/kelpseg/organize_inputs.py`, `organize.py`, `legacy_catalog.py`,
  `cli/organize.py`; registered the thin handler in `cli/__init__.py`.
- Added `configs/regions.csv` (001–012, with 005/006 distinct) and
  `configs/organize/ca_bc.toml`. The schema/naming/mapping decisions above are
  implemented; `docs/quickstart.md` documents every table, ordinary recipe,
  dry-run/copy/resume command, independent-dataset setup, errors and outputs.
- Added `tests/organize_fixtures.py`, `test_organize_inputs.py`,
  `test_organize.py`, `test_organize_engine.py`, `test_legacy_catalog.py`;
  extended `test_distribution.py` and `test_package_cli.py`.
- Updated README, documentation index, architecture/data-artifact contracts,
  this task and both queues. Created ignored `paths.local.toml` only after
  confirming the mounted volume; roots are the user-specified data/runs roots.
- Promoted existing Rasterio requirement into runtime and updated `uv.lock`;
  no dependency versions changed. Typer remains the CLI. Rasterio/NumPy are
  absent from help/version/dry-run imports and available for copied headers.
- Retained old repair-enabled organization and its tests because historical
  cleanup consumers still require them. The new organizer imports no legacy
  `src.*` or `scripts.*`; no repository helper scripts/framework were added.

### Full metadata reconciliation

Invocation from the checkout (Python 3.12, `uv run python`) was exactly the
`build_legacy_ca_bc_catalog(load_paths("paths.local.toml"),
Path("configs/regions.csv"), paths.data_root /
"preparation_inputs/ca_bc/v1")` recipe shown above, followed by
`build_organization_plan(load_organize_recipe("configs/organize/ca_bc.toml"), paths)`.
The newline-only split evidence exception is recorded above and in the catalog.
No membership or archive identity contradiction remains.

Catalog: `/Volumes/x10pro/kelpseg/preparation_inputs/ca_bc/v1/`.
Its `catalog_manifest.json` SHA-256 is
`923c2da76f94006d02b2f14728fbfc3268eb8c9813c82cd54cbfaa93a8fde003`.
It records converter-code and named evidence hashes, raw-table hashes,
explicit six excluded BC full-scene IDs, and counts. Existing matching catalogs
are verified without rewriting; conflicting catalogs fail.

The full metadata plan SHA-256 is
`093990dde1d538e64dce72e001790b5802d8a0977a24b31cbd67c22350143fb8`:
369 pairs (339 CA, 30 BC), 12 regions, 418 assets (325 masks, one CA overview,
90 BC image auxiliaries and two label auxiliaries), 3,919 alias rows, 290 owners
with known long aliases and 79 explicitly absent/unverified. It declares 1,156
payload files and 28,564,758,070 uncompressed bytes including repeated/shared
payload associations. This is metadata planning only, not full payload
verification. The installed full-scope `--dry-run` passed without copying.

### Bounded real smoke and restart evidence

External producer/selection/results:
`/Volumes/x10pro/kelpseg/smokes/task029a_organize_v1/`
(`run_smoke.py`, `selection.json`, `recipe.toml`, `regions.csv`, `plan.json`,
`result.json`). Invocation:
`uv run python /Volumes/x10pro/kelpseg/smokes/task029a_organize_v1/run_smoke.py`.
This producer intentionally refuses an existing smoke catalog; retained results
are subsequently checked through the ordinary CLI/library, not overwritten.

Subset input catalog:
`/Volumes/x10pro/kelpseg/preparation_inputs/task029a_smoke/v1/`.
Release:
`/Volumes/x10pro/kelpseg/data/2_organized/task029a_smoke_ca_bc/v1/`.
Smoke logical plan hash:
`50a63e26e64db5c26d08d5e2eb0c0699275db822cccd0ab57109c3bd9227919f`.
Completion `manifest.json` SHA-256:
`1b5e695adb8d68d6c63fa6480df0c03b3b5a3c3991566f619ddb08b50f5e23b2`.
The 14 hashed payload/control files contain 21,952,265 bytes; the manifest
itself is the noncircular completion root and is authenticated separately here.

The two pairs and all eight exact payload members/sizes are frozen in
`selection.json`. Selected source payload was **21,932,688 bytes**, below the
128 MiB selected-payload cap. Measured source payload reads and new payload
writes were each exactly 21,932,688 bytes (each below its explicit 32 MiB cap);
independent output verification read 116,684,216 bytes during the producer,
below its separate 256 MiB verification budget. Additional CLI/library final
verification passed; it reads output bytes, not entire raw ZIPs.

The CA TIFF is 1039 × 609, eight bands, untagged physical names, missing declared
nodata; its original label remains 1039 × 609. The BC TIFF is 501 × 3333, eight
generic `Band_1`…`Band_8` descriptions and declared nodata 0; its original label
remains **14920 × 29304** with declared nodata 0. All four primary hashes/sizes,
internal headers and four companion hashes/sizes are in `sources.csv`,
`assets.csv` and the completion manifest. The mask, XML, overview and worldfile
bytes remain unchanged; no sidecar strings were repaired or applied to infer
physical bands. Extra-archive payload and label-sidecar coverage use synthetic
fixtures; they were deliberately omitted from this tiny real subset.

Controlled interruption occurred after one atomic verified-file receipt, before
any completion manifest. Explicit resume verified completed bytes and finished
atomically. A repeated matching library invocation and installed CLI `--resume`
verified the completed release with unchanged file mtimes. Receipts/state remain
in sibling `.v1.incomplete`, outside the completed payload; the payload staging
directory was moved to the final smoke path. Unknown files/directories, corrupt
receipts/outputs, changed recipe/catalog/inputs, unsupported/malformed ZIP data,
and concurrent writers are refused in fixtures. Only identified incomplete
payload temporaries can be recreated; partial control-file temporaries stop for
inspection. Crash-after-rename/before-receipt recovery rechecks source and target
bytes without overwriting the existing target.

All three raw archive sizes/nanosecond mtimes still match Task 027's frozen
catalog. Trusted archive SHA-256 identities were reused with stability checks;
no routine 23 GB archive rehash, full extraction or metadata-only claim of member
verification occurred. Originals and Task 026/027 packages/receipts were never
modified. Full `/Volumes/x10pro/kelpseg/data/2_organized/ca_bc/v1/` is absent.

### Validation and remaining boundaries

- `uv run pytest -q`: **234 passed**, with the existing Rasterio `is_tiled`
  pending-deprecation warning in the retained evaluation test. No test failures.
  The initial shared-environment `--no-sync` baseline could not collect package
  tests because the package was not installed there; frozen setup corrected the
  environment, after Task 027 had completed. This was not a source regression.
- Both wheel/sdist installation paths run actual independent-dataset organization
  and library verification outside the checkout with runtime dependencies only.
  Fresh-process help/version and organize-help checks block heavy imports.
- Two unrelated synthetic dataset declarations exercise ZIP and frozen directory
  inputs, different regions/names/band counts, repeated image/label locators,
  owner-scoped asset IDs, reused aliases, byte identity and mismatched grids.
- Tests cover declaration/role/region/date/hash/path errors, duplicate/unsafe ZIP
  entries, CRC/deflate corruption, symlinks/overlap/collisions, no-write dry runs,
  trusted/untrusted input identity, post-read source changes, complete inventory,
  authenticated catalog snapshots, row-order/machine-root identity stability,
  interruption windows, resume corruption and immutable completion. Provenance
  fields are cross-checked against both the plan and verified output bytes.
- `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run pre-commit run --all-files`, `uv lock --check`,
  `uv sync --python 3.12 --frozen` and `git diff --check` pass. Markdown local
  links/anchors (94) and balanced fences across 8 changed documentation files pass.

Simplicity check: dataset, release, region/member/asset mappings and machine
roots change through small settings/tables; one generic engine serves every
input. The one-time historical conversion stays separate. No filtering,
normalization, alignment, class mapping, split assignment, training, inference,
cleanup, production release or Box write occurred. Mask semantics, original
historical completeness, untagged physical bands and annotation-coverage claims
remain the Task 026 evidence limits, not inferred truths.

The concurrently prepared Task 029B contract and its queue entry were preserved;
this task did not edit that contract or begin its implementation.

Exact next action: when requested, execute the prepared Task 029B contract using
this completed schema/API and bounded organized smoke as its handoff. Full
369-pair materialization/production QA/Box publication remain Task 030A. Both
queues now record Task 029A complete; stop before starting another task.

## Researcher-maintainability follow-up plan (2026-10-27)

User requested a preparation folder, plain maintainable code and plentiful
progress messages. Group the existing three modules under `kelpseg.prepare`,
update imports/examples, use ordinary standard-library logging (CLI displays
progress by default; library callers configure logging), and make three small
readability fixes: explicit plan constructor keywords, one shared CSV schema
map and one reverse delivery/archive mapping. Preserve the existing safety
checks and frozen external evidence. No production copy, cleanup or later task.

## Researcher-maintainability follow-up outcome (2026-10-27)

Moved preparation code into a single `src/kelpseg/prepare/` folder:

- `organize_inputs.py`: settings, table schemas, input validation and plans.
- `organize.py`: unchanged-byte copies, restart state and release verification.
- `legacy_catalog.py`: the separate one-time CA/BC metadata reconstruction.
- `__init__.py`: short reading map, without eager imports or wrapper APIs.

Updated CLI, fixture, distribution-test and current-document imports to
`kelpseg.prepare.*`; no compatibility forwarding modules or dependencies were
added. Original outcome paths above describe the initial implementation; the
current code lives in this preparation folder. The command remains
`kelpseg organize` with the same recipe/path/resume options and output format.

Kept the code as plain functions and made three explicit readability changes:
keyword fields replace the dense positional/generator plan constructor; the
converter reuses the existing CSV schema map; one ordinary reverse dictionary
replaces repeated archive/delivery searches. Byte checks, safe resume and
atomic publication protections remain intact.

Added standard Python INFO logging for recipe/table paths and row counts,
delivery/index checks, source identities, copy/header/provenance/verification
phases, current filenames, completed/total files, MiB, resume checks/reused
files and final publication. Long copy/hash operations report bytes about every
ten seconds. CLI progress has timestamps and goes to stderr by default; its
handler/level/propagation are restored afterward. Library callers enable the
normal Python logger themselves; no print callbacks, progress framework or
logging dependency was added.

Added `tests/test_prepare_progress.py` and
`tests/test_prepare_catalog_progress.py`; distribution checks now require the
new folder layout and perform actual organization using the relocated library.
Updated `AGENTS.md`, architecture, quickstart, artifact documentation and both
queues with the researcher-maintainability guidance and current imports.

Validation: **244 tests pass** (including ten new logging/heartbeat checks),
with the existing retained Rasterio `is_tiled` pending-deprecation warning.
Wheel/sdist runtime-only installations outside the checkout pass. Ruff format
and lint, pre-commit for all tracked files and the new preparation files,
`uv lock --check`, frozen Python 3.12 installation and `git diff --check` pass.
Current documentation links/anchors and fences were checked at closeout.

The full 369-pair metadata-only CLI dry-run now visibly logs all phases and
retains the exact plan identity
`093990dde1d538e64dce72e001790b5802d8a0977a24b31cbd67c22350143fb8`.
No raster copies, archive payload hashing, cleanup, production publication or
Box writes occurred during this follow-up. Frozen external catalogs/releases
and historical producer/code hashes remain unchanged; a source-code relocation
is not a reason to regenerate them. A new converter run with changed producer
code requires a new explicit catalog version, as documented in the guide.

Task 029A is complete again. The prepared Task 029B contract is unchanged;
execute it only when requested, using `kelpseg.prepare` imports. Task 030A
continues to own full production organization/publication. Both queues retain
that next action; this follow-up starts no other numbered task.
