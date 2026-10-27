# Task 029B: Implement two-tier checks and shared cleanup

Status: Complete — preparation-wide simplification verified on 2026-10-27.

Current cleanup contract: **one pass into a fresh output**, with no resume,
receipts, recovery journal or producer matching. The one-pass revision/outcome
at the end supersedes those parts of the initial contract and earlier outcomes.

Depends on: completed Tasks 026–029A and their recorded evidence/reusable code.
Execution: Local implementation, synthetic tests, and bounded real smoke.
The revised plan is approved; this execution implements and verifies it.

## Abstract

Provide three preparation commands overall: the existing `organize`, a new
read-only `check`, and a new shared `clean`. Use Typer handlers backed by plain
functions under `kelpseg.prepare`. The stored stages remain **raw → organized
→ cleaned**. There is no BC-specific cleaner, adapter command, or intermediate.

Both new commands accept ordinary image directories with optional paired-label
directories. New data must not need a published release or input catalog just
to be checked or cleaned. An explicit existing catalog can enrich/verify
provenance. The production path still uses organized variant 2 as the parent of
cleaned variant 3. Full production builds/publication remain Tasks 030A/030B.

Reuse/refactor the existing cleanup logic and correctness tests. Preserve their
established behavior except for the explicit current decisions below. Add
coverage for the new interface and outputs; do not start a fresh scientific
implementation or reproduce the old archive/repackaging framework.

## Inputs and reading route

Read the normal entry documents, then
[architecture.md](../docs/architecture.md),
[data_artifacts.md](../docs/data_artifacts.md),
[cleanup_provenance.md](../docs/cleanup_provenance.md),
[documentation.md](../docs/documentation.md), and
[quickstart.md](../docs/quickstart.md).
Read [Task 029A's outcome](029a_organize_raw_sources.md#outcome-2026-10-27)
and actual `kelpseg.prepare` functions/schemas. Use
[Task 026's six traces](026_inventory_originals_and_cleanup_provenance.md#six-traced-identities)
and Tasks [002](002_create_and_validate_raw_merge.md) and
[009A](009a_repair_metadata_nodata_and_repackage.md) as historical processing
and regression evidence, distinguishing it from the newly approved policy.

Planning reads code/docs and small existing metadata. Execution is limited to
bounded fixtures and the declared two-pair smoke below.

## User decisions recorded

- Preparation uses only `organize`, `check`, and shared `clean`; no separate BC
  processing command or `bc_cleaned` intermediate.
- `check` has two levels: quick metadata/structure checks by default, and an
  explicitly requested full pixel scan. Both support images-only or paired data.
- Common cleanup handles label alignment and missing annotation coverage for
  CA, BC, and other explicitly supported datasets. Dataset names do not select
  hidden code paths. BC's expected source vocabulary is already water/background
  0 and kelp 1; shared cleanup introduces ignore 3 where needed.
- Cleaned image nodata pixels are **0 across all original bands**, and image
  metadata declares **nodata=0**. Cleaned label nodata/ignore is **3**, with
  metadata **nodata=3**; stored label 0 remains valid water/background.
- For paired inputs, locations outside original label coverage become image
  all-band zero plus label 3. This replaces historical BC background filling
  outside coverage. Do not interpret absent annotation as background.
- Image-only inputs retain their valid imagery; having no labels must never
  cause annotation-based blanking of the image.
- Detailed coverage/reason masks are optional QA outputs, **off by default**.
  Keep automatic counts, transformation records, identities and hashes. Later
  training/scoring can exclude label 3 without requiring a separate coverage TIFF.
- Preserve existing supported categories, including CA land/wave classes and
  existing class 3; binary remapping and ignore index -100 remain Task 031.
- Keep originals and organized payloads unchanged. Cleanup writes a separate
  derived directory and records actual pixel/metadata changes.

No further blocking user choice is required. Unknown mask meanings/band names
remain unknown; novel semantics fail with a useful explanation when encountered.
Do not reapprove these decisions or infer policy from held-out results.

## Expected outputs

| Location | Deliverable |
|---|---|
| `src/kelpseg/prepare/check.py` | Reusable directory discovery, quick/full validation, typed results and optional atomic reports |
| `src/kelpseg/prepare/clean_inputs.py`, `clean.py` | One explicit recipe schema, cleanup planning, migrated scientific functions, provenance, verified resume/publication |
| `src/kelpseg/cli/check.py`, `clean.py`, existing CLI root | Thin handlers, default progress logging; no BC command |
| `configs/check/planet8_source.toml`, `planet8_cleaned.toml`; `configs/clean/planet8.toml` | Small hand-authored expectations and repair settings, without class paths or machine-specific roots |
| Existing nodata/alignment/repair tests; `tests/test_check.py`, `tests/test_clean_inputs.py`, `tests/test_clean.py` | Preserve relevant fixtures/assertions and extend them for current decisions |
| Existing installed-distribution/CPU checks and researcher guide | Working direct-directory recipes, report meanings, outputs/errors and ordinary new-data use |
| This task and queues | Actual API/settings, function/test migration map, checks, artifacts, limits and next action |

Reports, generated manifests, rasters, smoke artifacts and detailed QA remain
outside Git. No new repository `scripts/` directory or generic framework.

## Implementation contract

### 1. Freeze the small interface and format expectations

Record exact recipe fields, result/report schemas, pairing rules and bounded
smoke selection before coding. Use ordinary functions, one definition of each
schema, explicit loops and standard progress logging under `kelpseg.prepare`.
Keep imports lazy so help/version do not initialize geospatial/ML workflows.

Implemented commands:

```bash
uv run kelpseg check --images <images-dir> --labels <labels-dir> --recipe configs/check/planet8_source.toml
uv run kelpseg check --images <images-dir> --recipe configs/check/planet8_source.toml --full
uv run kelpseg clean --images <images-dir> --labels <labels-dir> --output <new-dir> --recipe configs/clean/planet8.toml --dry-run
uv run kelpseg clean --images <images-dir> --labels <labels-dir> --output <new-dir> --recipe configs/clean/planet8.toml
uv run kelpseg check --images <new-dir>/images --labels <new-dir>/labels --recipe configs/check/planet8_cleaned.toml --full
```

Omit `--labels` for image-only checks/cleanup. Check additionally supports an
optional explicit `--report <file>`; cleanup supports explicit `--resume` and
optional QA masks through its recipe. Directory commands do not require a
`--paths` file or catalog. Existing `organize --recipe ... --paths ...` remains
unchanged. CLI directory paths resolve from the working directory; recipe
references resolve from the recipe directory. No discovery of another config.

Recipe expectations include supported band counts/order evidence, dtype,
label vocabulary, georeferencing, and source versus cleaned nodata/grid rules.
Freeze concrete names with examples rather than adding an inheritance system
or a flag for every setting. Changing a supported dataset needs no Python edits.
A band count alone cannot verify physical band identity; report unestablished
names as unknown. Do not infer dates/regions from directories or invent them
when no catalog supplies them. Later experiments still need explicit identities.

Pair ordinary files by a documented relative TIFF-stem rule. Reject empty image
scopes, duplicate
or case-folded collisions and ambiguous/missing image-label pairs before writes.
If an explicit mapping is supported, validate it rather than guessing. Labels
are optional as a whole input mode, not silently optional for individual pairs.
Preserve directory-mode names and record source paths/hashes; do not claim these
are globally unique scientific identities. Use known catalog identities when
explicitly supplied. Reject input/output overlap, escapes and unsafe symlinks.

### 2. Make quick and full evidence distinct

Quick checks enumerate the complete declared directory scope and inspect
headers/pairing: readable TIFF headers, expected bands/dtypes, CRS/affine shape,
nodata declarations, pair counts, names and image/label grid agreement. Report
repairable grid/nodata issues separately from unsupported/ambiguous inputs.
Quick checks do not scan arrays or claim valid class values, full readability,
checksum identity, or pixel-level nodata consistency.

Full checks read **all selected pixels** in bounded blocks, reporting progress,
source/byte scope and the work performed. Validate decodability, allowed class
values, source or cleaned nodata rules, and applicable paired-image/label
consistency. No silent sampling advertised as full. A full scan of large BC
mosaics can be expensive; state that scope rather than hiding it. Reuse verified
identical-input results only with trustworthy content identity. Do not require
a separate whole-file hash pass merely to call a scan full; verify expected
hashes only when supplied and report the actual evidence level.

Return typed results identifying checks passed/failed/skipped, repairable
issues and unknowns. Show a concise human summary and corrective actions.
Success means the **requested level/profile** passed, never unperformed checks.
Expected validation failures produce nonzero exit status and useful stderr
without a traceback. Neither level changes inputs or creates sidecars. A report
is written only when explicitly requested, atomically outside input directories.
Refuse an existing report destination; do not silently replace prior evidence.

### 3. Reuse the existing scientific logic and tests

| Existing implementation | Reuse/refactor | Existing correctness coverage |
|---|---|---|
| [nodata.py](../src/prepare/nodata.py): `declared_nodata_values()`, `nodata_mask()`, `nodata_value_text()` | Source-aware declarations, explicit fallback, dtype safety and all-band detection | [test_nodata.py](../tests/test_nodata.py) |
| [merge_planet8b_regions.py](../scripts/merge_planet8b_regions.py): `derive_aligned_label()` | Nearest exact-grid categorical sampling, valid class-zero handling, independent footprint computation | Cleanup assertions in [test_merge_planet8b_regions.py](../tests/test_merge_planet8b_regions.py) |
| [repair_planet8b_nodata_metadata.py](../scripts/repair_planet8b_nodata_metadata.py): label repair and `_label_audit()` | Missing-image label repair, retained source-ignore classes and QA invariants | [test_repair_planet8b_nodata_metadata.py](../tests/test_repair_planet8b_nodata_metadata.py) |

Extract/refactor functions into the package; do not import `src.*`/`scripts.*`
from the installed commands or wrap the old archive-repair CLI. Reuse organizer
file/header/provenance/staging helpers where practical without imposing its
catalog/release schema on direct-directory use.

Run relevant existing tests before migration, preserve their assertions against
package functions, and record an old-function/test → new-function/test map.
Use bounded shared fixtures for old/new equivalence where behavior is unchanged,
plus independent expected-array/grid assertions. Explicitly update/add tests for
new image normalization and outside-coverage exclusion; old BC fill-0 behavior
remains historical evidence, not the new expected result. Do not weaken unrelated
assertions to make the new implementation pass. Document necessary rewrites;
reuse/refactoring is the default. Retain old entry points until consumers have
migrated and replacement coverage passes.

### 4. Apply shared repairs and normalize actual pixels

Detect original image nodata **before** changing pixel values or metadata.
Use consistent declared nodata, preserving source dtype and all original bands.
The current rule is all bands equal the declared/effective value, not any band.
Declared 65535 takes precedence over zero; missing-metadata fallback must be
explicit for the audited cohort or another declared supported input policy.
Reject partial/inconsistent/nonfinite/nonrepresentable declarations. Unknown
new sources do not silently inherit the old CA/BC fallback.

For paired inputs, nearest-align stored label categories onto the exact image
shape/CRS/transform. Preserve valid class zero despite misleading source label
metadata `nodata=0`. Compute geographic label footprint independently; do not
let unknown source masks, alpha, overviews or sidecars silently change category
sampling or footprint. Validate any temporary warp sentinel is unused.

The image exclusion mask is original image nodata, plus outside original label
coverage for paired data. Set **every original image band** to 0 there, set
corresponding labels to 3, and write image metadata `nodata=0` and label metadata
`nodata=3`. Preserve valid image values elsewhere. Retain existing source label
class 3 even over valid imagery; label ignore does not require inventing
background or automatically blanking every existing ignored-label pixel.

Before publishing, detect retained pixels that were valid under the original
policy but are already all-band zero. They collide with the requested new
nodata representation: fail with an actionable explanation rather than silently
reclassifying them or changing valid values to make the check pass. Already
excluded outside-footprint pixels do not count as retained-value collisions.

Image-only cleanup performs source-aware nodata normalization only, with no
label lookup, label-derived alignment/coverage requirement or annotation-based
blanking. No fake labels are created. Already-correct imagery can pass through
without a raster rewrite. All outputs go to a fresh separate directory; never
repair originals/organized inputs in place or hard-link writable outputs to them.

Do not infer unsupported class semantics or map CA land/waves to binary here.
Later chip conversion maps the declared categories to binary/-100. Keep all
sources, including background-only ones; no chip/nodata-percentage filtering,
split assignment, threshold/model selection or label-dependent inference.

### 5. Keep outputs safe, simple and auditable

Write fresh raster profiles for changed imagery and labels: preserve original
image dtype/band order/grid, set explicit nodata, and use recorded lossless
settings. Aligned labels use the image grid and representable categorical dtype.
Because **both imagery and labels may change**, stale `.msk`, `.ovr`, `.aux.xml`,
world files, statistics and metadata must not reactivate old values or grids.
Preserve source companions as hashed provenance references or separate inactive
assets; regenerate active auxiliaries only from the actual new content. Unknown
`nan_mask` meanings remain preserved-but-unused. Reopen outputs to verify what
GDAL/Rasterio sees, not just producer arrays.

Calculate coverage/reason arrays internally as needed. Persistent coverage,
image-validity and reason rasters are optional QA artifacts, off by default;
turning them on must not change cleaned image/label results. Mandatory compact
records include input/output hashes, supplied parent/delivery identities,
original/output grids and nodata declarations, policies/code/runtime, asset
dispositions, per-source changed-pixel counts and summary totals. Keep absent
region/date/band evidence explicitly unknown for uncatalogued inputs.

Counts distinguish original image nodata, outside label footprint, their
intersection, retained valid imagery, existing label-ignore pixels and final
exclusions. Reconcile partitions and class transitions on the target image grid.
If native contributing-cell statistics are recorded, state that domain rather
than implying a whole shared-mosaic histogram. The final paired invariant is
image nodata → label 3; label 3 can also cover preexisting ignored annotations.

Reuse safe staging, atomic per-file receipts, verified resume and exact-inventory
completion principles from the organizer without requiring its input catalog.
Optional supplied parent manifests must be verified; ordinary directories use
explicit source snapshots and hashes. A final output is immutable. Conflicts,
changed inputs/recipe, unknown/corrupt outputs or concurrent writers fail; only
an identified command-owned interrupted temp file may be recreated. No silent
overwrite or incomplete work described as complete. Keep control hashes
noncircular and logical identities independent of resolved machine paths.

Run the shared full checker against completed outputs before publication,
using the cleaned profile. Its checks must remain independently testable from
the cleaner. Record semantic pixel/grid identities and actual file hashes;
window-size changes preserve pixels/counts, while resumed files must pass byte
verification. Show phases, current file, counts/bytes and resume decisions with
standard CLI logging. The everyday result is a short actionable summary, not a
requirement for the researcher to inspect masks or detailed machine records.

### 6. Bound real work and extend the guide

Implement/test the checker first, then shared cleanup with migrated logic, then
installed-package integration. Use two independent small synthetic datasets;
one must work without any CA/BC catalog or naming convention. Cover images-only
and paired modes through the same APIs.

Use Task 029A's complete two-pair smoke or a small explicitly declared directory
sample. Record selected inputs/identities and estimates before running; default
parent payload budget is at most 128 MiB, with an explicit derived-output/space
budget. Do not scan all 369 payloads to select examples. Translate the six Task
026 behaviors into fixtures; replay feasible real cases and record exactly
which were rerun. Historical BC outside-fill equality is intentionally changed.
No full production release, archive extraction/upload, or real-data walkthrough.

Extend the guide with actual quick/full check, paired/image-only clean, resume,
output/report meanings and corrective errors. Ordinary new directories need no
pre-built catalog. Keep production release recipes explicit and separate.

## Smoke and validation

- Preserve/migrate existing nodata/alignment/repair tests, adding explicit
  expected differences for new policy. Test class-zero labels, dtype-safe
  65535/zero normalization, explicit missing-metadata behavior, and original
  nodata detection before metadata replacement.
- Prove quick checks do no pixel reads and full checks read every selected
  pixel; report skipped/unknown checks and distinguish full scans from hashes.
  Cover missing/ambiguous pairs, duplicate names, wrong bands/dtypes, missing CRS,
  mismatched grids, read failures and unexpected classes.
- Test shared CA/BC and independent-dataset cleanup, exact nearest grids,
  outside-coverage blanking of every image band, label 3 and correct 0/3 metadata.
  Cover all-band/any-band differences and retained all-zero value collisions.
- Test image-only use without labels/catalogs; absence of labels cannot blank
  valid imagery or create labels. Preserve existing valid-image ignored labels.
- Reopen outputs with conflicting old image/label sidecars and verify no stale
  override. Compare optional QA masks off/on for identical core results and
  reconciled counts. Original bytes/permissions and organized inputs stay intact.
- Exercise dry-run no-write, explicit report placement, corrupt/changed inputs,
  interrupted resume, unexpected files, output conflicts and atomic completion.
- Check independent checker failures on deliberately broken cleaner outputs;
  extend wheel/sdist tests for directory check and clean outside the checkout
  with runtime dependencies only and no legacy imports.
- Run focused and retained CPU tests, frozen install/lock checks, Ruff format/
  check, pre-commit, Markdown links, and `git diff --check`. Tests need no GPU,
  W&B/Box login, pretrained weights or online data; record preexisting failures.

## Acceptance criteria

- The preparation surface is organize/check/clean, with no separate BC command
  or intermediate. `organize` retains its byte-preserving implementation.
- Quick/full checks and shared cleanup work for ordinary image directories with
  optional labels and no mandatory catalog or published-release prerequisite.
- Existing scientific logic/tests are reused with an explicit migration map;
  new interface checks and deliberate policy changes are independently covered.
- Cleaned image nodata pixels/metadata are 0; paired label ignore/metadata is 3,
  preserving valid class-zero labels. Missing annotation coverage is excluded,
  and image-only inputs retain their valid imagery.
- Optional QA masks default off; compact counts, provenance and integrity checks
  remain automatic. Fresh outputs, resume and atomic completion are verified.
- The guide explains actual commands and errors without source edits, guessed
  dataset semantics, class paths or framework layers. No full production starts.

## Non-goals

A BC-only processing stage, arbitrary unknown-data repair, scientific truth
validation, mask/band/class inference, binary remapping, filtering, chipping,
splits, models, Box work or full production materialization/publication.

## Outcome template and exact next action

Record actual commands/settings and quick/full evidence, direct-directory versus
catalog behavior, reused functions/tests and deliberate old/new differences,
changed files/dependencies, source/output hashes, nodata/coverage counts, asset
dispositions, bounded external paths/budgets, installed/retained checks, guide
simplicity and unresolved issues. Mark Complete only after acceptance.

Exact next action: scope Task 030A's full organized build/QA/verified-Box contract;
Task 030B later applies shared checking/cleaning to produce full variant 3.
Update both queues and stop before another numbered task.

## Plan revision outcome (2026-10-27)

Replaced the prior family-specific/pinned-parent cleaner plan with the user's
approved organize/check/shared-clean design. Recorded two-tier direct-directory
validation, normalized image pixel/metadata nodata 0, label ignore/metadata 3,
shared outside-annotation exclusion, optional QA masks, and required reuse of
existing logic/tests. Historical BC outside-fill-0 replay remains evidence, not
the new expected behavior. Raw/organized data and old task records are unchanged.

This revision changes documentation only. Implementation stays Pending; no
checks/cleanup ran and no data/environment changes were made. Updated this task,
the architecture/artifact/provenance contracts, and both queues. Independent
reviews checked directory/API consistency and scientific invariants, including
the distinction between historical BC processing and the newly approved policy.
All 84 local links/anchors in the six documents resolve; fences/whitespace and
`git diff --check` pass. No implementation tests or environment changes were
needed for this documentation-only work.

Exact next action: when execution is requested, read this revised contract and
Task 029A's completed code/handoff, freeze the small recipe/report schema and
bounded smoke selection, then implement check first and shared clean second.
Do not add a BC stage or start production builds. Planning is complete;
implementation remains Pending.

## Execution freeze (2026-10-27)

The checker recipe has one flat schema: `schema_version=1`, `profile`
(`source`/`cleaned`), `image_band_counts`, `image_dtypes`, `label_values`,
optional `missing_image_nodata`, optional `band_names`, and `block_size=512`.
The clean recipe uses the same source expectations without `profile`, plus
`qa_masks=false` and `compression="deflate"`. Unknown settings fail. The shipped
Planet recipe explicitly declares the audited missing-metadata fallback 0;
independent recipes omit it unless justified. Cleaned labels are one-band uint8
categories; sources may use integer categories within the declared vocabulary.
The cleaner preserves declared categories, not their binary meaning.

Recursive TIFF pairing uses exact relative stems (casefold collisions rejected);
`.tif` and `.tiff` extensions may differ. Preserve relative filenames. Non-TIFF
companions are hashed inactive provenance; TIFF companions must be outside the
declared image/label directories; a verified organizer parent can reference
separate mask/asset directories. No filename-derived region/date inference. Optional `--parent`
selects an entire verified organized release, matching the supplied directories,
and retains its source/alias/region/delivery records. Directories alone need no
catalog. Report schema 1 records requested level/profile, passed checks, issues
with repairability, skipped checks, unknown evidence, source bytes and scanned
pixel scope. Cleanup manifest schema 1 records portable plan identity, runtime/
code hashes, input snapshots, per-source grids/counts/transitions/semantic and
file hashes, inactive assets and independently checked output inventory.

Real smoke selects exactly Task 029A's completed two-pair organized release:
`/Volumes/x10pro/kelpseg/data/2_organized/task029a_smoke_ca_bc/v1`.
CA `007_20211212_184127_227a` and the previously selected BC tile are already
materialized; no ZIP scan/extraction or other payload discovery is allowed.
Input payload budget 128 MiB (previously measured 21,932,688 bytes); derived
release budget 128 MiB and minimum free-space budget 512 MiB. New external
outputs go under `/Volumes/x10pro/kelpseg/smokes/task029b_clean_v1`.
All native selected label pixels are scanned during full checking, including
the large shared BC mosaic; this is explicitly full scope, not sampled evidence.

Pre-migration baseline: `uv run pytest -q tests/test_nodata.py
tests/test_merge_planet8b_regions.py tests/test_repair_planet8b_nodata_metadata.py`
passed all 16 tests.

## Outcome (2026-10-27)

Implemented the approved preparation surface: existing byte-preserving
`organize`, read-only quick/full `check`, and shared `clean`. Both new commands
accept recursive ordinary image directories with optional complete paired-label
directories. There is no family switch, BC command/intermediate, required catalog,
binary conversion, filtering or split assignment. The optional cleaner `--parent`
verifies a complete organized release and retains its declared identity tables.
Direct directories have explicit unknown scientific identity fields.

### Interface, outputs and behavior

The execution-freeze recipe fields above are the actual schema; unknown settings
fail. `load_check_recipe`, `discover_inputs`, `check_inputs`, `load_clean_recipe`,
`build_clean_plan`, `clean_dataset`, and `verify_cleaned_release` are reusable
functions without CLI context. Check returns immutable typed results with issues,
repairability, passed/skipped checks, unknown evidence, byte and native-pixel
scope. Quick performs no pixel/hash reads; full reads every native selected
image/label pixel in bounded windows, including mismatched large label mosaics.
Source-grid/label-metadata/nodata defects are repairable but still return status 1.
Cleaned checks independently require exact paired grids, image nodata 0, uint8
label nodata 3, supported vocabulary and image-nodata -> label 3. Pixel scanning
alone never claims checksum identity. Only explicit `--report` publishes an
atomic, exclusive report outside input directories.

Cleaning detects original declarations/fallback before conversion, uses all-band
nodata, nearest sampling of stored categories and independently generated footprint,
and excludes original nodata plus paired outside-coverage pixels. Every image
band becomes 0 there and paired labels become 3; source class 0 and existing ignored
annotations over valid image pixels are preserved. Image-only cleanup does not
open labels or create them. Retained original-valid all-band-zero collisions fail
with an actionable error. Fresh lossless Deflate profiles discard active stale
masks/alpha/overviews/statistics/sidecar metadata, preserving image dtype/bands/grid
and band descriptions. Even already-correct imagery is currently rewritten into
an independent raster; unchanged pixel content is recorded separately from file
bytes. This conservative choice avoids copying active stale TIFF masks/overviews.

Outputs retain relative filenames under `images/` and optional `labels/`.
`inputs.json` defines the portable plan hash from recipe, source content and
code/runtime identities; `input_locations.json` records machine paths separately.
`recipe.json`, `sources.json`, `check.json` and exact-inventory `manifest.json`
record grids, original/effective/output nodata, class transitions, counts,
semantic pixel/grid identities and actual SHA-256 hashes. Supplied parent controls
are inactive copies under `parent/`; companion assets remain hashed provenance
references to preserved originals, including unknown masks. QA coverage, original
image-validity and reason TIFFs are optional under `qa/`, off by default. Reasons
encode original nodata 1 + outside footprint 2; coverage is all 1 in image-only mode.
Zero totals remain explicit, partitions reconcile and retained label 3 need not
imply image nodata.

Fresh outputs are staged in sibling `.<name>.incomplete/payload` with exclusive
writer locking and atomic source receipts containing each output file's hash.
Explicit resume verifies source content/recipe/code/runtime, receipt counts and
closed-file bytes before reusing them; it only recreates active command-owned
unfinished rasters. Unknown files/directories, symlinks, corrupt receipts/rasters,
changed scopes, changed-and-restored sources and concurrent writers fail safely.
Completed output remains immutable; matching `--resume` verifies without rewrites.
Independent full cleaned checking and exact-inventory hashing precede atomic
publication. Logical identity excludes resolved machine locations; semantic
identity uses fixed canonical windows independent of the writing window setting.

### Migration map and deliberate changes

| Old function / coverage | Package replacement / preserved coverage |
|---|---|
| `src.prepare.nodata.declared_nodata_values`, `nodata_mask`, `nodata_value_text`; `test_nodata.py` | Moved implementation to `kelpseg.prepare.nodata`; old module reexports it for retained consumers. Original assertions now import package functions. Nonrepresentable NumPy casts become actionable RuntimeError. |
| `scripts/merge_planet8b_regions.py:derive_aligned_label`; `test_merge_planet8b_regions.py` | Extracted the nearest VRT/category/alpha algorithm into `alignment.aligned_label`, `read_aligned_label_window`, `repair_label_block`; original script/tests retained. `test_prepare_alignment.py` compares exact expected arrays and old/new outputs where policy is unchanged. Band-only VRT now prevents masks, sidecars or stale overviews affecting category/footprint sampling. |
| `scripts/repair_planet8b_nodata_metadata.py:_write_repaired_label`, `_label_audit`; `test_repair_planet8b_nodata_metadata.py` | Shared label exclusion in `repair_label_block`, confusion partition in `audit_label_block`, full-array validation in `check_inputs`; package tests compare historical audit counts and preserve source 3. Old archive-repair entrypoint remains for historical consumers. |
| Organizer hashing, JSON bytes, inventory checks and completed-release verification | Reused in cleaner without requiring organizer input schemas. Shared checker owns one expectation schema; CleanRecipe adds only output settings. |

Explicit policy changes: source 65535 is detected first and normalized to actual
all-band 0/image metadata 0; outside annotation becomes image 0/label 3 rather than
historical BC background fill0; all preexisting source 3 categories are retained
instead of rebuilding them as background; detailed persistent masks are optional.
Original labels 0 remain valid despite misleading metadata 0. Source companions
are hashed inactive references rather than writable companions beside changed
rasters. Historical script behavior remains labeled historical; it was not
silently changed to make equality assertions pass. No unrelated assertions were
weakened. The six Task 026 behaviors (ordinary CA, offset CA, declared 65535 repair,
CA narrower-edge/preexisting-ignore, within-coverage BC, outside-coverage BC)
are bounded fixtures, with independently expected arrays for the new exclusions.

### Changed files and simplicity

New package modules: `prepare/check.py`, `clean_inputs.py`, `clean.py`,
`nodata.py`, `alignment.py`; thin CLI `check.py`/`clean.py` and explicit root
registration. Added source/cleaned check TOMLs and one clean TOML. Added
`tests/clean_fixtures.py`, `test_check.py`, `test_clean_inputs.py`, `test_clean.py`,
`test_clean_resume.py`, `test_clean_parent.py`, `test_prepare_alignment.py`;
extended distribution tests and migrated nodata imports. The legacy nodata
implementation is replaced by a compatibility reexport. NumPy is now a direct
runtime dependency (already locked transitively); `pyproject.toml`/`uv.lock` agree.
No new production framework or repository scripts directory was introduced.

README, index, quickstart, architecture, artifact and cleanup-provenance docs
now describe actual commands/settings/outputs/errors. Ordinary dataset changes
use TOML values and directory paths without Python edits or guessed class
semantics. CLI logging is standard Python logging with phases, files, bytes,
native-pixel progress and verified resume decisions. Task/queue changes are
separate from researcher instructions. The concurrently prepared Task 030A
contract is preserved; it has not been executed by this task.

### Bounded real smoke and durable artifacts

All generated evidence is outside Git:
`/Volumes/x10pro/kelpseg/smokes/task029b_clean_v1/`.
`selection.json` froze two exact parent identities and budgets before payload
reads. `run_smoke.py` records each complete CLI command, exit code and elapsed time
in `commands.json`, with separate stdout/stderr logs. The producer refuses
existing report/output destinations; do not overwrite evidence to rerun it.
`verify_pixels.py` independently compares every target pixel using inverse-affine
center-coordinate nearest lookup, without importing any cleanup function.

Input: Task 029A's entire completed two-pair organized smoke at
`/Volumes/x10pro/kelpseg/data/2_organized/task029a_smoke_ca_bc/v1`.
Trusted parent completion SHA-256:
`1b5e695adb8d68d6c63fa6480df0c03b3b5a3c3991566f619ddb08b50f5e23b2`.
Selected payload 21,932,688 bytes; parent hashed files 21,952,265 bytes, below
128 MiB. Derived smoke artifacts measured about 21.8 MB, below the 128 MiB budget;
free space before execution exceeded 512 MiB (about 612 GiB). No all 369 selection
scan, raw ZIP read/extraction, upload or production build occurred.

Actual CLI sequence: source quick report (status 1, repairable label metadata/grid
issues only); source full report (status 1, adds the CA image-nodata label repair);
paired clean dry-run (no writes), paired clean with verified `--parent`, separate
full cleaned report, paired `--resume`, and ordinary image-only clean with no
catalog. Commands use the three tracked recipes listed above. Full source scope
was 2,302,584 image pixels and 437,848,431 native label pixels, including the whole
BC mosaic; it was not advertised as a sampled check. Cleaned full check passed
all 2,302,584 image and 2,302,584 aligned-label pixels. Checker payload scope was
20,552,813 source bytes and 10,825,693 cleaned bytes; it did not perform a separate
whole-file hashing pass.

| Source | Target pixels | Original nodata / final exclusion | Retained image | Outside label | Changed labels |
|---|---:|---:|---:|---:|---:|
| `007_20211212_184127_227a` | 632,751 | 206,854 | 425,897 | 0 | 206,854 |
| `012_20210813_193301_80_241_clip3` | 1,669,833 | 1,139,642 | 530,191 | 0 | 1,139,642 |
| Total | 2,302,584 | 1,346,496 | 956,088 | 0 | 1,346,496 |

Image pixels did not change in these two sources because their effective nodata
was already all-band 0. Both images were rewritten with corrected metadata/fresh
profiles; actual byte hashes changed. Paired and image-only output imagery is
byte-identical for these within-coverage sources. Existing label-ignore count and
nodata/outside intersection are 0 here. Independent full-target array comparisons
passed for both modes, and all original payload/control SHA-256 hashes,
permissions and mtimes are unchanged (`originals_verified.json`). Completed
resume preserved every final-file mtime. No Task 026 full real trace was rerun:
the feasible real replay is exactly these two Task 029A examples; 65535, missing
outside coverage and preexisting-ignore changes are verified in fixtures.

Completed derived roots:

- `paired/manifest.json` SHA-256:
  `9d4fc7d20355b417b91630717734d34b75ca0350d931bb7859576526863c1c9b`.
- `image_only/manifest.json` SHA-256:
  `d04f56702cec17b35de83f741c4911f4a94e4c52c6665b2a69385626185b05ba`.

Their `inputs.json`, `input_locations.json`, `sources.json`, parent snapshot and
manifest inventories record all individual input/output hashes and identities.
`result.json`, three explicit check reports and
`independent_pixel_verification.json` summarize the bounded evidence. Incomplete
state/receipts remain outside final payloads. QA masks were off in real runs;
fixtures prove masks on/off and writing-window changes retain identical core
pixels/counts/semantic identities (and fixture core file bytes).

### Validation and limits

Pre-migration baseline: 16 retained nodata/alignment/repair tests passed.
Focused post-migration checks include all scientific, checker, plan/clean,
parent/receipt, CLI and ordinary independent-data cases. Wheel and sdist each
install into fresh runtime-only environments outside the checkout; both run
quick/full directory checks, paired/image-only cleanup and resume, independently
verify values and original hashes, and prove help/version import no geospatial
or ML workflows. The installed commands import neither `src.*` nor `scripts.*`.

Final validation passed:

- `uv python install 3.12` / `uv sync --python 3.12 --frozen`; `uv lock --check`.
- `uv run --frozen pytest -q`: **329 passed** in 24.50 s, including both isolated
  wheel/sdist runtime-only installations and retained CPU tests. One existing
  `PendingDeprecationWarning` about Rasterio `is_tiled` in the retained evaluation
  test; no failures or new GDAL warnings.
- `uv run --frozen ruff format --check .`: 84 files already formatted.
- `uv run --frozen ruff check .`: passed.
- `uv run --frozen pre-commit run --all-files`: all hooks passed.
- Changed-document Markdown links/anchors, fenced blocks and `git diff --check`:
  passed; concrete counts recorded in the final validation note below.

No GPU, W&B/Box login, weights or online data are required by tests. Original
physical band identities remain unknown unless supported by actual headers;
mask semantics and original-delivery completeness remain the existing audit
limits. This implementation validates represented format/category policy and
agreement with supplied labels, not annotation truth. No unresolved 029B
implementation issue remains.

Exact next action: when requested, execute the already prepared
Task 030A contract, beginning with this
completed checker/handoff and its repairable source-check interpretation.
Full organized publication belongs to 030A; full shared-cleaned publication
belongs to 030B. Both queues are updated and this task stops here.

Final documentation verification: 9 changed/owned Markdown documents,
114 local links/anchors all resolve; fenced blocks are balanced and
`git diff --check` passes. The prepared Task 030A file was read only for the
current handoff and remains untouched.

## Researcher-readability follow-up scope (2026-10-27)

The user requested substantial code simplification after the initial implementation.
Keep this within 029B: use plain, clearly named functions; replace dense expressions
and deeply nested workflows; explain scientific and file-safety decisions in
comments; and log the start/progress/results of each expensive phase. Preserve
commands, recipes, scientific policy, record schemas, integrity checks and default
read-only/dry-run behavior. Do not replace old immutable smoke outputs, start 030A
or build production data. Verify with retained behavioral/installed tests and a
bounded synthetic before/after comparison, then close both queues again.

## Researcher-readability follow-up outcome (2026-10-27)

Completed the requested substantial readability pass without changing the
commands, settings, scientific policy or saved record schemas. This pass focuses
on functions a researcher can follow in order; it does not minimize line count
by compressing expressions.

- `prepare/clean.py`: the main workflow is now 82 lines rather than 274, with
  named functions for workspace recovery, receipt verification, source processing,
  parent provenance and publication. The source-opening function is 118 lines
  rather than 170; `_write_cleaned_windows` visibly owns the pixel rules. Comments
  explain original nodata, all-band detection, class-zero background, missing
  annotation coverage, retained ignore labels, optional QA, and safety ordering.
  Dense class-transition array stacking is replaced by explicit class/count loops.
  Source timestamps use one `stat` call per file rather than four. Runtime facts
  are collected once; descriptive record/header/pixel-hash names replace cryptic
  helper names. Receipt arithmetic uses named totals and intersections.
- `prepare/check.py`: directory checking is 117 lines rather than 243, with
  separate source-opening, image-header, label-header and pixel-scan functions.
  Removed the nested finding callback and deeply nested workflow. Ordinary loops
  construct input pairs/results; comments explain what quick/full can establish.
- `prepare/clean_inputs.py`: explicit CheckRecipe field construction replaces
  dictionary conversion/deletion. One validator handles cleanup settings. Shared
  `discover_companions` avoids repeated asset-discovery logic. Planning uses
  named path/companion operations, explicit optional inputs, and keyword results.
- `cli/_logging.py`: one small standard logging context manager replaces three
  repeated setup/restore blocks in organize/check/clean. Help/version remain lazy.
  The checker logs each finding once rather than repeating it in final output.

Logging now explains discovery/header checks, actual pixel-scan scope, original
nodata declarations or explicit fallback, image-only versus paired alignment,
optional QA, six cleanup phases, per-source counts/changes, completed-receipt
reuse versus unfinished-source restart, periodic long-scan/hash progress,
provenance writing, final inventory verification and publication. Logging settings
are restored after command completion/errors. The quickstart's new code-navigation
section identifies where to follow the workflow and scientific pixel rules and
how to save logs. No new framework, schema or runtime dependency was introduced.

Verification:

- **331 tests passed** in 24.99 s, including all retained CPU, scientific,
  interruption/corruption/parent tests and both wheel/sdist runtime-only installs.
  The sole warning remains the existing evaluation-test Rasterio `is_tiled`
  PendingDeprecationWarning. Added checker scan/logging regression coverage and
  asserted all six default cleanup log phases plus nodata/coverage totals.
- Ruff formatting (85 files), Ruff check, full pre-commit, frozen sync and lock
  checks passed. Markdown links/fences and whitespace were checked again.
- Five bounded synthetic before/after cases (3-band and 8-band paired,
  image-only, QA enabled, alternate writing window) produce **identical output
  file bytes, pixel/grid hashes, counts, class transitions and label audits**.
  Matching new-producer resume also passes for each case. Independent review
  found no scientific or file-safety regression.

Comparison artifacts and readable example logs are outside Git at
`/Volumes/x10pro/kelpseg/smokes/task029b_readability_v1/`: `before.json`,
`after.json`, `comparison.json`, `readability_metrics.json`, `after.log` and
five tiny source/before/after fixture directories (about 313 kB total). A saved
copy of the prior cleaner produced the baselines before the refactor. This is
synthetic verification only; the original two-pair real smoke remains immutable
and its two completed manifests still pass independent byte/inventory verification.
Producer code hashes intentionally change: use a fresh output for new cleaning;
no old receipt or completion identity was rewritten to bypass resume checks.

No unresolved follow-up issue remains. Both queues are closed again. The exact
next action remains the prepared Task 030A, when requested; its contract and all
original/production data are untouched by this follow-up.

## One-pass cleanup revision (2026-10-27)

The user rejected the recovery/support burden and explicitly chose cleanup runs
that must finish in one attempt. This overrides the earlier resume acceptance
and its receipt/recovery/fingerprint machinery. Remove clean --resume, interrupted
source recovery, partial-record reuse, writer locks and producer matching. A fresh
sibling incomplete directory claims the output once; failure leaves it incomplete
and reruns start from the beginning after explicit inspection/removal or at a new
output. Preserve originals, refuse existing outputs, check actual pixels and
publish final output only after independent validation. Organizer resume is a
separate existing workflow and is not changed by this revision.

Also remove canonical semantic pixel hashes and redundant plan/location records.
Keep only source/output file hashes, grids, compact counts/changes, known optional
parent identities, runtime versions, recipe and full-check evidence. The supported
scientific scope remains ordinary TIFF directories, image-only or complete paired
labels, the explicit CA/BC categories/nodata/alignment rules and supported 8/4/3-band
settings. No generic adapter or new dataset framework is needed. This is an actual
feature reduction, not another reorganization that leaves the machinery intact.

## One-pass cleanup outcome (2026-10-27)

Implemented the user's scope reduction. The previous readability pass retained
too much machinery; this pass removes the unsupported recovery guarantees.
The cleaner is now **614 lines instead of 991**, removing 377 lines (38%), and
has 16 functions instead of 27. The bounded audit counted 199 function lines for
recovery/receipts plus 259 for provenance/completion before this reduction;
compact scientific evidence is retained, but job recovery is not.

Removed from cleanup:

- `--resume` and the Python resume argument; completed output is never reused by
  another cleanup command, even for identical inputs.
- `_restart_unfinished_source`, receipt loading/validation, active-source journals,
  state files, lock files, partial-control reuse and recorded-file recreation.
- Producer code/runtime matching, logical plan fingerprints, canonical semantic
  pixel hashes and their extra full pixel read pass.
- Separate `inputs.json`/`input_locations.json` and repeated full source-check
  records. Source paths/input hashes and inactive asset references are consolidated
  into `sources.json`; only actual file hashes are needed for output integrity.

Actual supported workflow: select explicit ordinary TIFF imagery, optionally
complete paired labels, and one recipe; write a fresh sibling
`.<output-name>.incomplete`; full-check the selected inputs; clean every source;
independently full-check the output; verify originals are unchanged; write the
four compact records and rename to final output. Exclusive directory creation
refuses another attempt at that output. Failure leaves the incomplete directory
untouched for inspection. The researcher deliberately moves/removes it or chooses
a fresh output and reruns from the beginning. No partial files are trusted,
recovered, deleted or reused automatically.

The retained formats/use cases are the ones already requested: explicit TIFF
expectations; CA/BC's shared nodata/alignment/categories; image-only and paired
ordinary directories; optional verified organizer identities. Dataset families
already share one pixel path. There are no new adapters, archive-cleaning modes
or general dataset framework. `organize` is unchanged and retains its separately
implemented resume behavior. The pixel-cleaning/profile helpers are unchanged
from the saved pre-reduction implementation; counts, class-zero water, declared
65535 handling, existing ignore labels, outside-coverage exclusion, fresh profiles
and optional QA remain covered by independent expected-array tests.

Outputs are `images/`, optional `labels/` and `qa/`, and exactly four root records:
`recipe.json`, `sources.json`, `check.json`, `manifest.json`. Optional `parent/`
contains only the parent's manifest and source/region/alias/asset crosswalks.
`sources.json` holds per-source `.inputs` paths/hashes/bytes, actual original/output
headers, exclusion/change counts, transitions, QA references, output file hashes,
summary counts, inactive asset hashes and plain runtime versions. The completion
manifest hashes the actual output inventory; the read-only
`verify_cleaned_release` checks it without any job/resume identity protocol.

Changed implementation: `prepare/clean.py`, `clean_inputs.py`, CLI `clean.py`.
Deleted `tests/test_clean_resume.py` and retired assertions for removed recovery
features; migrated the useful within-run changed-and-restored-source assertion
into `test_clean.py`. Scientific/sidecar/QA/parent assertions remain. Added tests
for no-resume CLI, refusal of existing output/stage/symlink, failed-stage contents
remaining untouched, a fresh-output retry, and refusal of a competing attempt.
Wheel/sdist tests now exercise one-pass cleanup; organizer resume checks remain.

Updated AGENTS, the quickstart, architecture, artifact and provenance docs to
make restartability stage-specific. New recovery support needs an explicit stage
requirement. Four logged cleanup phases and explanatory scientific comments stay.
The prepared Task 030A contract and unrelated work were preserved.

Verification:

- `uv run --frozen pytest -q`: **314 passed** in 24.83 s, including retained CPU and
  both wheel/sdist runtime-only installed checks. Only the preexisting Rasterio
  `is_tiled` PendingDeprecationWarning remains.
- Ruff format (84 files), Ruff check, full pre-commit, frozen sync and lock checks
  passed. Markdown links/fences and `git diff --check` passed.
- Five tiny paired 3-band/paired 8-band/image-only/QA-on/alternate-window cases match the
  previous implementation's raster and QA bytes, counts, transitions and label
  audits exactly. Independent review found no scientific/failure-state regression.
- The two original real-smoke releases still byte-verify without rewriting them.
  No new real payload scan, production build, Box operation or later task ran.

Durable bounded comparison evidence:
`/Volumes/x10pro/kelpseg/smokes/task029b_one_pass_v1/`: saved prior source as
`clean_before.py.txt`, before/after size metrics, `comparison.json`, one-pass
example log and five tiny completed outputs. This reuses existing synthetic input
fixtures; the old completed smoke remains immutable. No unresolved 029B issue
remains. Both queues are closed again; the exact next action is the prepared
Task 030A when requested, reading this current one-pass handoff first.

### Standing simplicity rule (2026-10-27)

The user set the current one-pass cleaner as the maximum file complexity going
forward. Each step does one job and stops the sequence on failure. Restart,
resume and partial-work recovery require an explicit user request; task contracts
written by an agent do not establish that authorization. Recorded this in AGENTS
and the architecture/storage contracts. The alignment implementation was inspected
and explained; no alignment code changed in this documentation update.
`git diff --check` passes; no new links or changed anchors were introduced.

## Plain Rasterio alignment revision (2026-10-27)

The user explicitly requested removal of handwritten XML and the generator
wrapper from aligned_label. Replace the layered virtual reader with an ordinary
function that reads the necessary native source window and nearest-reprojects
stored categories using Rasterio. Preserve class 0 despite source nodata 0,
independent annotation coverage, original nodata normalization and source-ignore
semantics. Keep memory bounded; do not load whole shared BC mosaics.

Deliberately support same-CRS, north-up unrotated grids and one-band uint8 labels.
Reject other paired grids/layouts clearly. Read unmasked native pixels so source
masks/sidecars/overviews cannot change labels; use an unused temporary 255 value
to distinguish missing footprint. Bound each source crop to 16,777,216 pixels and
explain smaller block_size on overflow. Plain function API:
`aligned_label(image, label, window, label_values) -> (categories, coverage)`.
Delete the old reader/convenience wrappers instead of keeping a compatibility
layer. No restart/recovery or later-task work is added. Validate retained
scientific fixtures, sourcecrop seams and bounded original two-pair smoke.

## Plain Rasterio alignment outcome (2026-10-27)

Replaced the XML/generator implementation with one ordinary array-returning
function. `aligned_label(image, label, window, label_values)` validates supported
headers/window coordinates, finds the contributing source cells with Rasterio
window functions, reads those cells with `masked=False` and no resizing, and
calls `rasterio.warp.reproject` with nearest sampling. Temporary unused 255 marks
missing coverage; stored 0 remains valid water. It returns categories and coverage
as plain NumPy arrays. There is no handwritten XML, MemoryFile, WarpedVRT,
contextmanager/yield or virtual-reader lifetime on this alignment path.
Deleted `aligned_label_window` and `read_aligned_label_window`; the cleaner opens
an ordinary label reader once and passes it into each window call.

The scientific behavior remains unchanged on supported data: source label nodata
metadata/masks do not suppress stored classes, stale overviews are not sampled,
annotation footprint is independent of class 0/source 3, and cleaning still applies
original-image-nodata/outside-footprint exclusion without blanking every source 3.
Each native label crop is bounded to 16,777,216 pixels (16 MiB uint8); this never
requires decoding the full shared BC annotation mosaic into memory.

Explicit supported scope: paired image/label CRS must match; both grids must be
finite, north-up and unrotated; labels must have exactly one uint8 band. Categories
must belong to the declared vocabulary, excluding 255. Target windows use integer
pixels, are nonempty and lie inside the image. Other formats fail clearly rather
than entering a general conversion path. Source-profile header checks reuse
`validate_alignment`, so unsupported grids/dtypes fail during planning before
full pixel scans or output creation. Image-only cleanup does not invoke alignment.

These restrictions deliberately retire prior cross-CRS alignment and generic
integer-label coercion. Existing differing-CRS test now asserts a clear failure;
new uint16/layout/grid/window tests cover the rejected cases. The optional-parent
fixture previously inherited the organizer's generic uint16 labels; it now writes
supported uint8 categories and refreshes fixture delivery hashes before organizing.
Its provenance/original-data assertions remain unchanged. No compatibility wrappers,
restart support, new dependency or generic framework were added.

Changed files: `prepare/alignment.py`, cleaner window wiring, source-check header
validation; migrated `test_prepare_alignment.py`, added
`test_alignment_boundaries.py`, and adjusted the parent fixture. Quickstart,
architecture and cleanup-provenance docs describe the actual function and limits.
The alignment module is 145 lines of plain validation/array operations and shared
repair/QA functions; the cleaner is 612 lines. The inherited scientific rules do
not require specialized reader construction.

Validation:

- **337 tests passed** in 23.38 s, including both wheel/sdist runtime-only installs,
  retained CPU tests and one-pass failure/publication checks. One preexisting
  Rasterio `is_tiled` PendingDeprecationWarning remains; no new warnings/failures.
- Alignment suites: **40 passed**, preserving exact old/expected arrays, historical
  audit partitions, all six trace fixtures, class 0/source 3, masks and stale-overview
  assertions. Added fractional/resolution/partial-coverage cases at small and
  BC-scale coordinates, whole-window versus tiled seams, no overlap, native crop
  limits before reads, stored255 rejection and unsupported-layout/window failures.
- Independent bounded review prototype matched 390 old-VRT cases (300 random
  fractional origins/resolutions/overlaps plus 90 half-pixel/tie/BC-scale cases)
  in both whole-grid and tiled comparisons. Prototype scratch stayed outside Git.
- Five existing tiny synthetic paired 3-band/paired 8-band/image-only/QA-on/alternate-window
  cases match prior raster and QA bytes, counts, transitions and audits exactly.
- Real smoke repeated only the existing two organized CA/BC pairs. All 2,302,584
  target pixels produced identical raster byte hashes, counts, transitions and
  label QA to the prior real smoke. Original hashes, permissions and mtimes are
  unchanged. Full source checking still scans the selected native labels in
  bounded windows; only alignment avoids whole-mosaic loading.
- Frozen lock/sync, Ruff format (85 files), Ruff check, full pre-commit, Markdown
  links/fences and `git diff --check` passed.

New durable evidence:
`/Volumes/x10pro/kelpseg/smokes/task029b_plain_alignment_v1/`: selection/budget,
prior alignment source snapshot, plain-alignment log, `comparison.json`, five tiny
synthetic outputs and `real_paired/`. Input budget 128 MiB, selected organized
parent 21,952,265 bytes; derived output 11,002,671 bytes, below 128 MiB.
Real output manifest SHA-256:
`21eccbb8efd1d6a6f313b7f0f6062d654e07d735a40ce777b5d8463a12af0e4e`.
Old smoke outputs remain immutable. No production, archive extraction, Box or
later-task work ran. Both queues are closed; no unresolved 029B issue remains.

Exact next action remains the prepared Task 030A when requested, using this
current source-check/paired-input support contract and the one-pass cleanup rule.

## Matching-grid direct-read outcome (2026-10-27)

Previously every paired label used nearest reprojection, including exact matching
image/label grids. Added one explicit direct-read branch: after validating the
supported format and target window, matching dimensions/CRS/transform read stored
native categories with `masked=False` and return full geographic coverage.
Only different grids enter the existing crop/reprojection path. Class 0 remains
valid, source masks do not redefine coverage, and unsupported categories still
fail. The 16,777,216-native-pixel limit also applies before direct reads.

The imagery itself is never geometrically resampled by cleanup. Both paths still
perform original-image-nodata exclusion, label 3/metadata repair and fresh derived
output writes; a matching grid does not imply no cleanup is needed. Per-source
logs now distinguish direct reads from nearest alignment. Quickstart and
architecture descriptions match actual behavior. No flags, wrappers, recovery or
new supported formats were added.

Regression tests make `reproject` fail if matching full/subwindows or matching
paired cleanup call it. They preserve class 0/source 3 with misleading nodata 0 and
source masks, verify image 65535 -> 0 plus corresponding label 3, and assert the
direct-read progress log. A different-grid test confirms reprojection still runs
and matches an independent nearest-pixel oracle. Oversized matching windows fail
before source reads or coverage-array allocation. Focused owned suites: 42 passed.
Full validation: **342 tests passed** in 23.80 s, including both wheel/sdist
installed checks; Ruff format/check, full pre-commit, lock and whitespace checks
passed. Only the existing evaluation-test Rasterio is_tiled deprecation warning
remains. No real dataset
was rebuilt for this small branch. Next action remains prepared Task 030A when
requested, after this current handoff; no later task started.

## Preparation-wide simplification scope (2026-10-27)

The user requested the same rule throughout installed preparation: remove
unnecessary processing/abstraction, use plain functions/comments/logs, stop on
failure, and remove all restart support. This follow-up includes the existing
organizer and metadata catalog converter; it does not execute another numbered
task or production build. Retained historical chip/training scripts remain
reference consumers for their later replacement tasks. Preserve originals,
scientific correctness, known membership/crosswalks and useful tests. Remove
recovery/reuse/lock machinery, repeated payload reads/hashes and error retries.

## Preparation-wide simplification outcome (2026-10-27)

Reviewed every installed `kelpseg.prepare` module and the preparation CLI. Removed
restart support throughout organization, checking, cleaning and metadata-catalog
creation. The review did not start Task 030A production or replace historical
chip/model implementations that are still reference consumers for later tasks.

Concrete removals and work avoided:

- **Organizer 878 -> 606 lines:** removed resume flag/API, locks, per-file receipts,
  state/copy journals, partial-file recovery, idempotent completed-output reuse
  and matching-plan restart handling. A fresh sibling incomplete directory is the
  whole attempt; failure stops and preserves it, and a retry starts from scratch.
  Copying hashes selected bytes once in the stream; one independent output-byte
  verification precedes publication. Removed repeated per-copy readback and final
  rehash passes. Open ZIPs once per run, decode a repeated member once, then make
  independent copies; inspect identical primary TIFF headers once. The existing
  release/provenance format and read-only verifier remain compatible with old
  immutable artifacts. New phase/file/byte logs explain the actual work.
- **Planner 616 -> 613 lines:** fresh final/stage conflict refusal happens before
  catalog reads. Removed matching-output/restart identity branches and obsolete
  temporary-suffix rules. Explicit catalog/delivery/logical-input functions
  replace the nested loader closure and oversized builder. Replaced quadratic
  filename-prefix comparisons with set membership and parent-path checks.
  Portable catalog/plan identities remain provenance, never restart identities.
- **Historical converter 674 -> 650 lines:** removed existing-catalog reuse, writer
  locks, random temporary publication and partial-output protocol. It refuses
  known conflicts before reading audit evidence and writes one fresh catalog
  attempt. The actual 369-source membership, 418-assets and 290-alias-evidence
  joins remain explicit; preserving those facts is required scientific provenance,
  not a generalized support framework. Bounded old/new tables are byte-identical;
  manifest provenance differs only in the expected producing-code hash.
- **Cleanup:** reuse input hashes already established by optional parent-release
  verification within this run. Plain directories get one source hash pass.
  Detect changes using source identities/stats after processing, instead of
  hashing all original bytes again. Reuse each closed raster's recorded hash in
  the final manifest; hash new control files once. Independent full pixel/grid/
  nodata checking remains, but removed repeated automatic byte-reverification of
  the same output. Explicit read-only release verification remains available.
  A regression proves each ordinary input and cleaned raster is hashed once.
- **Checker:** removed error fallback that rescanned an image after a label/read
  failure. Unsupported headers skip expensive arrays; full checking stops after
  the failed source, reports skipped later files, and never retries. Completed
  scan counts are distinguished from unavailable partial-read counts. Quick
  checking remains a complete read-only header diagnosis. Integer imagery skips
  nonfinite-array checks because uint16 cannot contain NaN/inf. No unperformed
  pixel work is reported as complete. Added failure/no-retry/skip-scope tests.
- **CLI:** replaced the custom logging generator/contextmanager with plain
  start/stop functions and explicit `try/finally` in each handler. Logging remains
  default, consistent and restored on exit. No custom contextmanager remains in
  installed preparation code. The simple bounded window iterator is retained.
- **Alignment/nodata:** reviewed and retained the plain native reads, exact-grid
  direct path, nearest crop path, bounded-memory errors, explicit source nodata
  declarations and all-band mask. No unnecessary generalization was added.

The installed preparation/CLI total is 4056 lines versus 4349 before this review.
The main removal is operational machinery, not scientific checks or provenance.
No new modules, dependency, plugin, configuration framework or input family was
introduced. Code remains ordinary functions with comments describing why each
scientific/file-safety step exists. All preparation attempts stop on failure;
there is no installed preparation resume path.

Updated operating docs and AGENTS to state the same one-pass rule for all
preparation. The pending Task 030A contract received only interface/failure-policy
corrections (remove obsolete --resume/locks/receipts and use read-only verification
for existing completed releases). Its status remains Pending and it was not
executed. Both queues now point to this current handoff.

Validation:

- **344 tests passed** in 23.83 s, including retained CPU/scientific tests, explicit
  provenance-corruption tests and both isolated wheel/sdist runtime-only installs.
  Retired only tests for removed recovery/reuse guarantees; kept correctness,
  original-byte, parent-identity, alias, mask/sidecar and failure-publication checks.
- Planner/catalog owned tests: 63 passed; organizer/provenance/progress/clean-parent
  checks: 43 passed. Historical converter comparison produced byte-identical
  deliveries/membership/aliases/assets and unchanged historical evidence rules.
- Ruff format (85 files), Ruff check, full pre-commit, frozen sync/lock and
  whitespace checks passed. The only warning is the preexisting retained
  evaluation-test Rasterio is_tiled PendingDeprecationWarning.
- Fresh bounded organization copied exactly the existing two smoke pairs and
  four companions (21,932,688 selected bytes). All 8 payload hashes/sizes match
  Task 029A exactly; independent manifest/provenance verification passed.
- Five tiny cleanup cases (paired 3-band/paired 8-band/image-only/QA-on/alternate window)
  retain exact raster/QA bytes, counts, class transitions and label audit results.
  No production dataset, archive extraction or Box operation was performed.

Durable smoke/evidence:
`/Volumes/x10pro/kelpseg/smokes/task029b_prepare_review_v1/`: frozen selection,
recipe/regions, progress log, synthetic comparison outputs and `result.json`.
Fresh organized smoke:
`/Volumes/x10pro/kelpseg/data/2_organized/task029b_prepare_review/v1/`.
Manifest SHA-256:
`699d5f6a33580c14aa09bc7478bc9b019d34850ed49ce4317060bbe37a9546f8`.
Plan SHA-256:
`8943378641ab0afd53705ddd3db11ac7c71e9b209df434c4268f907dcbe3a723`.
Its 14 hashed files total 21,952,277 bytes. The input/output budget was 128 MiB;
old catalogs, smoke releases and originals remain unchanged. Trusted raw archive
identities were reused only after checking their existing size/mtime evidence;
no entire raw archive was hashed for this small validation.

No unresolved preparation-review issue remains. Exact next action remains
Task 030A when requested, using these one-pass commands. Stop here.

## Commit closeout (2026-10-27)

Task 029B is complete, including the requested preparation-wide simplification.
The final behavioral/distribution validation is 344 passing tests; Ruff,
pre-commit, lock/environment, documentation and whitespace checks passed.
The code, configs, regression tests, researcher docs, task record and closed
queues are included in the Task 029B commit.

The separately prepared local `tasks/030a_build_and_publish_organized.md` is
preserved outside this commit. Queue entries identify Task 030A as pending without
linking committed documentation to that uncommitted plan. No Task 030A execution,
production materialization, upload or training was started. The exact next action
is to wait for an explicit Task 030A request.
