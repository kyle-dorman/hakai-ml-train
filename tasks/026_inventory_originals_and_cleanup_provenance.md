# Task 026: Inventory originals and trace cleanup provenance

Status: Complete.

Depends on: Task 025.

Execution: Local, read-only examination of existing collections. Write only new
audit artifacts outside Git and concise documentation in Git. No data repair.

## Abstract

Establish which local collections could be original deliveries and explain how
representative CA/BC inputs became the existing derived labels and chips.
Separate observations, historical claims, unresolved questions, and proposed
cleaning rules before implementing a replacement preparation pipeline. A folder
called a raw merge is not evidence that its labels are original.

This task ends with an inventory of the declared scan scope and a bounded
provenance report. It does not establish complete original-delivery membership
by assumption, approve unexplained label changes, or rebuild any dataset.

## Inputs and reading route

After the normal entry documents, read [data_artifacts.md](../docs/data_artifacts.md)
and [documentation.md](../docs/documentation.md). Read the relevant alignment and
outcome sections of [Task 002](002_create_and_validate_raw_merge.md) and the
nodata/BC coverage repair sections of
[Task 009A](009a_repair_metadata_nodata_and_repackage.md). Treat these as historical
evidence requiring comparison with actual files.

Initial discovery boundary: `/Volumes/x10pro/kelpseg`. Starting candidates:

- `ca/` and `bc/Planet8bSR_BC_Labelled/10km_tiles/`.
- `merged_all_regions_v1/`, its raster manifests, copy/alignment QA, and recorded
  creation command; these are derived artifacts, despite the old raw-merge name.
- `chips_all_regions_1024_512_v1/` manifests and
  `repair_history/metadata_nodata_v2/`, including available plans, source nodata
  inventory, repair audits, pre-repair label/manifest snapshots, and NPZ rewrite
  inventory. Historical snapshots are not additional original deliveries.
- Other candidate collection folders and archive listings discovered within
  this boundary. Look for names such as `merged_ds` and `pre-chipped-8b` without
  assuming they exist at any particular path or contain originals.
- Existing repo split CSVs, preparation code, tests, and Git history only where
  needed to interpret a trace. Inspect legacy producers; do not execute merge,
  repair, chip, filter, or packaging entry points.

The Task 025 package at `references/legacy_ps8b_v1/` is immutable and excluded
from scanning raster payloads. Counts in current docs are comparison baselines,
not freshness or completeness guarantees. Do not search the entire Mac, mount
remote storage, access Box, or extract large archives to expand the scope.

## Expected outputs

The completed audit package is at
`/Volumes/x10pro/kelpseg/audits/task026_originals_v1/`. It contains reports and small
diagnostics, never replacement imagery, labels, chips, or copied collections.

| File | Required content |
|---|---|
| `scan_plan.json` | Explicit input roots, collection IDs, exclusions, symlink policy, work bounds, output root, and planned checks |
| `collections.json` | Discovered collections, scope/counts, classification, supporting evidence, and unresolved membership |
| `files.csv` | One row per scoped file: collection-relative path, role, size/mtime, raster metadata or explicit read error, and hash status |
| `pairs.csv` | Image/label relationships, source/region/date identity, evidence for matching, missing/ambiguous pairings, and grid comparisons |
| `trace_selection.json` | Four to six distinct source IDs, deterministic selection reasons, source/derived paths, windows, and pre-read identities |
| `traces/<source_id>.json` | Observed transformations, quantitative comparisons, coverage/nodata distinctions, input hashes, code/history references, and remaining discrepancies |
| `previews/` | Small diagnostic panels for traced grids, classes, and coverage where useful; exact legend, display windows, and scaling recorded |
| `findings.json` | Evidence-linked facts, historical claims, inferences, unknowns, proposed rules, and concrete questions |
| `validation.json` | Reconciliation checks, sampled immutability checks, skipped/unreadable inputs, runtime, and limitations |
| `audit.py`, `invocations.txt` | Exact bounded audit producer and invocations; no dependency synchronization or repair |
| `manifest.json` | Atomic completion record for the declared audit scope, output hashes, counts, and unresolved-issue summary |

In Git, write a short `docs/cleanup_provenance.md` explaining what is established,
what remains unknown, and which proposed rules need resolution before Task 029.
Link it from `docs/data_artifacts.md` when it exists. Keep per-file inventories
and detailed traces external. Update this task and both task queues on execution
completion. Contract drafting alone leaves this task Pending.

## Implementation contract

### 1. Establish the scan boundary without modifying inputs

- Record top-level discovery and freeze explicit collection roots/exclusions in
  `scan_plan.json` before bulk reads. Descend recursively only into those roots.
  Inventory candidate TIFFs and sidecars; list archives without extraction.
  Known chips/checkpoints/reports need collection-level and manifest evidence,
  not a recursive array decode or full archive checksum pass.
- Open files read-only. Disable GDAL persistent auxiliary metadata writes
  (`GDAL_PAM_ENABLED=NO`); never request saved statistics, overviews, or caches
  beside inputs. Do not rename, move, delete, chmod, rewrite, hard-link, repair,
  regenerate manifests, or alter source membership. New reports stay in the
  dedicated audit root; validate that output cannot resolve inside an input
  collection. Skip symlink traversal by default and record unresolved targets.
- Use the existing local environment with `uv run --no-sync`. Keep reads
  streaming/windowed and CPU-only. Parallel agents may inspect disjoint families
  or evidence, but one coordinator owns report publication and identity joins.
- Refuse existing output replacement. Resume only after validating the plan,
  producer, input identities, and completed output hashes. Record inaccessible
  roots and partial scans explicitly; never turn read errors into zero counts.

### 2. Inventory identities, pairings, and metadata

- Record collection-relative paths with one root mapping, file role/type,
  byte size, mtime, and available delivery/processing evidence. Resolve source
  IDs within a collection; repeated IDs across versions are expected lineage,
  while ambiguous pairings remain explicit issues. Do not silently choose one.
- For scoped raster headers record dimensions, dtype, band count/descriptions,
  CRS, transform, bounds, nodata/mask metadata, and relevant processing tags.
  Retain raw metadata alongside any interpretation. Label-value summaries use
  the traced samples; do not imply every label was decoded if only headers read.
- Pair images and labels using manifest/path evidence; retain one-to-many and
  shared-mosaic relationships. Filename equality alone proves neither spatial
  alignment nor common delivery. Report missing pairs and conflicting dates,
  region IDs, grids, or purported band orders.
- Classify collections/files as candidate original, documented derived,
  byte-identical duplicate of a named file, or unknown, with evidence. Confirmed
  delivery status needs delivery records or explicit user confirmation, not
  timestamps or naming. Repeated BC labels may be legitimate shared mosaics.
- Hash traced source/derived payloads and consulted manifests in full. For
  additional duplicate candidates, hash only a bounded, recorded shortlist;
  size/name agreement is merely a duplicate candidate. Distinguish byte equality
  from decoded-array equality and record unhashed rows as such. Do not hash
  every archive or raster to claim collection-wide identity unnecessarily.

### 3. Trace four to six source identities

Select from inventory metadata and historical evidence, write exact IDs before
pixel comparisons, and use lexical source-ID order to break ties. Include at
least two CA and two BC source identities; combine cases within a source where
possible and stop at six. Cover these cases where available:

- Ordinary CA alignment/class handling and a historically mismatched CA label
  grid (Task 002 described `ca_002` and `ca_008` cases).
- A declared-`65535` CA case, preferably historical repair source
  `004_20210525_174950_2463`; examine an additional edge discrepancy only if it
  adds a distinct case within the six-source cap.
- BC within original annotation coverage and BC extending outside coverage.
  Use source/label bounds and alignment evidence to select these cases.

If a required case or upstream original is unavailable, record the attempted
lookup, available intermediate, and evidentiary limit. Do not invent an origin,
silently substitute a different case, or expand to a full pixel audit. An
explicit unavailable case is preferable to an unsupported provenance claim.

For each selected source:

1. Join candidate original image/label to merged image/derived label and relevant
   repair snapshots using explicit paths and identities. Compare source grids,
   image content or bounded source windows, class values/counts, and masks.
   Record any chip link by source ID/window; verifying one existing chip is
   optional supporting evidence, not a new whole-chip-dataset audit.
2. Distinguish image nodata, absent annotation coverage, stored label classes,
   and chip ignore `-100`. A label's declared nodata value `0` does not prove
   that stored zero is missing annotation; zero may be valid water/background.
   A missing image nodata declaration is an unknown, not permission to assume 0.
3. Inspect the historical remap `[0, 1, 0, -100, 0]` and the relevant class
   meanings as evidence. Verify the applicable family before proposing a
   mapping; do not apply the CA mapping universally to BC or unknown labels.
4. Compare recorded alignment/repair steps with current arrays. If needed,
   reproduce nearest-neighbor label alignment or a candidate remap in memory
   for the selected source/window only. Record interpolation, grids, fill,
   window coverage, and mismatch counts. Never write the result as a cleaned
   label or infer full-raster equality from a window comparison.
5. Check the historical BC rule change explicitly: Task 002 describes class 3
   outside original label coverage; Task 009A describes background 0 outside
   coverage with class 3 reserved for image nodata. Show available before/after
   evidence and keep the new-release choice unresolved unless delivery/annotation
   evidence or an explicit user decision settles it. Current repaired data
   alone cannot establish that unannotated space is valid negative truth.
6. Give each claimed transformation an evidence reference (file/hash, code
   revision/function, recorded command, or user statement). Current code may
   include later repairs; it does not prove an earlier artifact's recipe.
   Report unexplained differences rather than fixing them.

### 4. Publish evidence and a bounded handoff

Use explicit evidence labels: `observed`, `historical`, `inferred`, `unknown`,
and `proposed`. Each finding names its scope and supporting file/trace. Proposed
rules are not approved preparation instructions. Summarize label mapping,
alignment, nodata, coverage, and band-order findings in plain language.

Keep absent physical band descriptions visible; conventional Planet indices
alone are not metadata verification. Quantify header/pairing coverage separately
from pixel/hash coverage. Publish a complete audit manifest only after output
validation; it certifies the declared audit, not a complete original delivery
or a cleaned release. Unresolved membership and unreadable files can remain
explicit findings in a completed scoped audit.

Pass Task 027 the evidence-backed candidate backup roots and exclusions, with
unconfirmed status preserved. Pass Task 029 the known transformations and open
questions; unresolved label semantics must be settled before adopting a new
cleaning rule. Do not start either task here.

## External audit interfaces

A one-off audit producer lives in the external audit root. The actual parallel
trace invocations are recorded in the outcome and `invocations.txt`; no new
repository workflow was added. For subsequent audits, do not add a
repository `scripts/` workflow or build the production package in this task.
All roots/limits belong in `scan_plan.json`, not scattered Python edits.

```bash
uv run --no-sync python /Volumes/x10pro/kelpseg/audits/task026_originals_v1/audit.py inventory --plan /Volumes/x10pro/kelpseg/audits/task026_originals_v1/scan_plan.json
uv run --no-sync python /Volumes/x10pro/kelpseg/audits/task026_originals_v1/audit.py trace --selection /Volumes/x10pro/kelpseg/audits/task026_originals_v1/trace_selection.json
uv run --no-sync python /Volumes/x10pro/kelpseg/audits/task026_originals_v1/audit.py verify
```

## User decisions required

None to begin the declared read-only audit. Record uncertain delivery membership
and unexplained cleanup behavior as questions with paths, evidence, and practical
consequences. Ask only if locating an essential collection or interpreting a
specific label meaning prevents a trustworthy trace; continue independent work.
Do not require approval for routine reads or report writing. Do not use elapsed
time, an unanswered question, or an old repair decision as approval of a new rule.

## Plan/spec before execution

Set status In progress and align the queue when the audit is actually selected
for execution. Record roots, expected read volume, exclusions, hash scope,
output layout, producer invocation, and input immutability checks before bulk
reads. After metadata inventory, record the four-to-six trace IDs and reasons
before pixel comparisons. Split excess work into a later contract rather than
expanding this audit to every source or silently dropping declared scope.

## Smoke and validation

### Execution plan (2026-10-26)

The external `scan_plan.json` was written before bulk reads under
`/Volumes/x10pro/kelpseg/audits/task026_originals_v1/`. Discovery was limited to
`/Volumes/x10pro/kelpseg`; frozen roots are `ca`, `bc`, `merged_all_regions_v1`,
`merged_ds`, `hakai_match`, canonical chips/repair history, `archives`,
`zip_archive`, and the existing `hakai_match_v0.tar`. Raster headers are read
without pixels; archives are listed without extraction; NPZ arrays are excluded.
Reference/experiment/training output roots and all audit output are excluded.
Reads use `GDAL_PAM_ENABLED=NO`, `uv run --no-sync`, and no bytecode output.
Consulted evidence and six trace payloads get full hashes; other files get
path/size/mtime snapshots. No bulk archive hashes or data writes are planned.

After header inventory, `trace_selection.json` records these IDs before pixel
comparisons: CA `001_20200422_173136_2277` (ordinary),
`002_20210419_182256_240c` (larger/offset label),
`004_20210525_174950_2463` (65535 repair),
`008_20201010_180745_2304` (accepted edge/narrower label); BC
`20210811_184459_09_245c_3B_AnalyticMS_SR_8b_harmonized_clip1` (within coverage)
and `20210811_185433_06_2262_3B_AnalyticMS_SR_8b_harmonized_clip0` (outside coverage).
Selection uses lexical IDs and recorded special cases; exact paths and reasons
are in the external selection. CA/BC trace modules own disjoint outputs; the
coordinator owns inventory, reconciliation, and completion publication.

The earlier task records and Git history are being checked as primary historical
evidence, including explicit prior user approvals; recorded decisions will not
be presented as absent merely because the current docs are shorter.

### Required checks

- Reconcile file counts by collection/role and pair statuses. Each scoped input
  appears once under its collection; ambiguous identities and read failures are
  reported, not dropped. No collection count implies delivery completeness.
- Reopen external CSV/JSON outputs and resolve all evidence/trace references.
  Verify output hashes, source/window identities, grid comparisons, and selected
  trace case coverage; record unavailable cases and limitations explicitly.
- Recompute at least one CA and one BC trace comparison from unchanged inputs;
  confirm mismatch counts/class summaries without using previously generated
  comparison arrays as truth. Reopen and visually inspect any saved panels.
- Compare before/after SHA-256 for all traced source/derived payloads and
  consulted manifests. Compare inventory path/size/mtime snapshots for other
  scanned inputs and check for unintended auxiliary files. State clearly that
  these metadata checks are not a byte-level proof for every unsampled file.
- Keep source-read handles read-only and all writes within the audit output or
  named repo docs. Validate duplicate/missing identities, failed reads, output
  reuse refusal, and output/input path overlap checks on small disposable
  fixtures if a producer is implemented; never test mutations on real inputs.
- Inspect Markdown/diffs, verify relative links, and run `git diff --check`.
  If tracked source changes are necessary, run focused tests and the required
  Ruff checks with `uv run --no-sync`; explain unrelated existing failures.

## Acceptance criteria

- The declared local scope has a reconciled inventory with explicit pairing,
  origin/classification evidence, exclusions, read failures, and unknowns.
- Four to six source identities trace at least two CA/two BC cases; unavailable
  originals or special cases have concrete evidence of the limit. Class mapping,
  alignment, coverage, and nodata are distinguished and supported per trace.
- The BC outside-coverage rule change is examined without silently declaring
  uncovered annotation space background. Proposed rules and unresolved user
  questions are clearly separated from observed facts.
- A compact researcher-readable provenance summary and a reopenable external
  audit package record the producer, runtime, input identities, checks, and
  completion scope. No accuracy or whole-delivery completeness claim is made.
- Sources, historical derived datasets/manifests, and the legacy reference
  remain unchanged. No repair, source removal, transfer, training, or new
  cleaned/chip release runs. The reusable walkthrough remains deferred.
- Simplicity check: ordinary files and one local path/limit specification;
  no storage service, preparation framework, or replacement package. No
  obsolete code is removed during this read-only task.

## Non-goals

Data cleaning/repair or release publication; universal label/nodata policy;
full-raster pixel/hash audit of every collection; archive extraction/repacking;
chip filtering or split regeneration; Box access/backup; production package
work; inference/training/evaluation; the reusable researcher walkthrough.

## Outcome template

Record scanned roots/counts and exclusions; classification evidence and unknown
membership; traced IDs and transformations; external package path/manifest hash;
changed repo files; read-only validation and producer checks; unresolved label
or coverage decisions; and candidate backup roots for Task 027. Mark complete
only for the declared audit scope. Exact next action: scope Task 027's Box
verification and backup contract, carrying forward unresolved data semantics.
Stop before Task 027 or implementation of a cleaning recipe.

## Outcome (2026-10-26)

Completed the declared read-only audit, including previous task records and
historical Git docs. The external package at
`/Volumes/x10pro/kelpseg/audits/task026_originals_v1/` has an atomic completion
manifest with SHA-256
`71859fa0d2b091348603f05b9fc3b6684154d13041d6d692eb157b3410d4ed20`.
`README.txt` explains the package; `findings.json` and `lineage_findings.json`
contain refined classifications. Initial classifications in `files.csv` and
`collections.json` are intentionally preserved as the header-phase snapshot.
The completed package has read-only file/directory permissions. No data repair,
source removal, transfer, training, or inference ran.

### Inventory and prior documentation

- Nine collection roots: 12,371 file paths, 3,000 readable raster headers,
  15,301 archive member records, zero input read errors. All 1,322 image/label
  pairs reconcile; 31 standalone pre-repair labels are deliberate historical
  snapshots, not missing original pairs. No NPZ arrays or archive payloads were
  decoded. The reference, training/experiment outputs, and audit roots were
  excluded as recorded in `scan_plan.json`.
- CA has 339 pairs and 325 companion masks. Archive indexes plus explicit extra
  mappings account for 325 `ca_data.zip` families and 14 `extra_data.zip` pairs.
  BC has 30 tile pairs plus six full-scene pairs. Archive/local path-size
  agreement supports candidate-source status, not payload equality or proof
  of complete original delivery. Preserve masks and sidecars.
- `merged_ds` is documented derived, resolved from its own merge manifest.
  Its 289 source identities equal `hakai_match`'s reconstruction set, omitting
  79 CA sources (35 `ca_006`, 32 `ca_007`, 12 `ca_011`) and BC
  `20210813_193301_80_241_8_band_Clip3` versus current 369. The 4,179 real NPZ
  tar members match live `hakai_match/chipped` paths/sizes; archive bytes remain
  unverified. No `pre-chipped-8b` collection appeared in the declared discovery
  boundary; no search outside that boundary was attempted.
- Earlier docs **do record prior approvals**. Task 002 records exact-grid
  nearest alignment and the initial outside-annotation class-3 rule. Task 009A
  records the later user-approved BC image-only nodata rule, background fill
  outside annotation, and the audited cohort's missing-metadata effective-zero
  fallback. Task 004 records the binary remap. Historical commit
  `598490bf97a36a6d34969da9a12be9dc9e94367b` retains the longer earlier docs;
  `ff0dd12` shows the initial Task 009A contract before its later zero fallback.
  `historical_evidence.json` gives exact file hashes/line references. No
  duplicate approval was requested for those recorded historical decisions.

### Six traced identities

All six selected current labels match the applicable historical replay with
**zero mismatches**. All six source/merged image files are byte-identical;
decoded imagery comparison covers bounded windows for CA and full selected
tiles for BC. Label comparisons cover each selected image's full footprint.

| Source | Verified transformation |
|---|---|
| `001_20200422_173136_2277` | Ordinary CA alignment and effective-zero image nodata; independent 333-pixel block traversal also matches |
| `002_20210419_182256_240c` | Larger/offset 4380 × 4308 source label sampled onto 2416 × 2816 image grid |
| `004_20210525_174950_2463` | Exactly 5,203 pre/current pixels changed class 2 → 3, all at eight-band `65535` nodata |
| `008_20201010_180745_2304` | Shifted/narrower label and accepted 21,471 class-3 pixels over valid imagery; 395 valid-image pixels outside annotation coverage |
| `20210811_184459_09_245c_3B_AnalyticMS_SR_8b_harmonized_clip1` | BC within annotation coverage; both historical recipes match preserved labels, no pre/current change |
| `20210811_185433_06_2262_3B_AnalyticMS_SR_8b_harmonized_clip0` | BC outside annotation: 637,016 valid-image pixels changed 3 → 0; 3,465,907 outside-annotation image-nodata pixels stayed 3 |

The CA edge manifest's `outside_source_label_not_nodata_pixels` field counts
outside annotation with derived label other than 3, not outside annotation with
valid imagery. Its zero value is consistent with the observed 395; this is
terminology to preserve, not a defect to repair. Source/code evidence remains
separate from proposed preparation rules.

### Validation and artifacts

- Before/after full hashes match for the traced payloads and consulted evidence;
  final verification checks 61 input/evidence files totaling 1,243,568,168 bytes
  (including three intermediate audit tables used by lineage analysis).
  All 12,371 scoped file paths, sizes, and mtimes remain unchanged, with no
  added auxiliary files. Unsampled payloads were not byte-audited.
- Independent CA raw-label/image-mask traversal agrees; independent BC direct
  nearest `reproject` agrees with the primary blockwise VRT comparison and all
  relevant class/coverage/change counts. No cached comparison arrays served
  as truth.
- Reopened and visually inspected all seven PNGs (six traces plus a valid-pixel
  RGB supplement for the nodata-heavy CA repair source). Labels and coverage
  align without an apparent shift. Exact small changes are established
  numerically, not inferred from downsampled previews. Agent visual inspection
  is recorded in `visual_qa.json`, not presented as human sign-off.
- Eight disposable-fixture checks passed: corrupt/missing raster reporting,
  duplicate collection identity, path overlap, output escape, overwrite
  refusal, missing pairing, and ambiguous pairing. Fixtures live only in the
  audit output. Original raster open modes remain read-only with PAM disabled.
- `audit.py verify` published the completion record after all checks. The
  standalone `verify_package.py` passed from `/private/tmp` with isolated
  imports: **43 payload hashes**, CSV/JSON reopening, no source-data or legacy
  imports. `manifest.sha256` protects the completion record separately.
- Runtime: Python 3.12.11, rasterio 1.5.0, NumPy 2.4.4, Matplotlib 3.10.9,
  Pillow 12.2.0; existing environment, `uv run --no-sync`, no sync or repair.
  No tracked source changed; validation is the external producer checks,
  numerical comparisons, Markdown/link inspection, and `git diff --check`.

The inventory command above ran as recorded. CA/BC traces ran independently
with `GDAL_PAM_ENABLED=NO PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python -B`
followed by the external `trace_ca.py` or `trace_bc.py` path. The RGB supplement
used `preview_ca_65535.py`. Lineage used a recorded Python stdin producer,
preserved as `audit_lineage.py`. `summarize.py` wrote curated findings before
`uv run --no-sync python -B /Volumes/x10pro/kelpseg/audits/task026_originals_v1/audit.py verify`.
The exact commands, scope, selection, code, and runtime are preserved externally.

Changed repo files: this task, `tasks/README.md`, `docs/todo.md`,
`docs/cleanup_provenance.md`, `docs/data_artifacts.md`, `docs/index.md`, and
`docs/documentation.md`. The concise provenance guide owns the current-facing
facts and limits; per-file details remain external. The implementation,
environment, data, and Task 025 reference remain unchanged.

Remaining limits: delivery completeness, archive payload integrity, semantics
of the 325 companion masks, and physical band identities for untagged/generic
headers. Six CA and 31 BC headers explicitly name physical bands; do not extend
this to the others. The historical BC background-fill approval is established;
it does not independently supply negative annotation truth outside coverage.
The new release must retain coverage provenance and declare its scored scope.
These limits do not prevent completion of the declared read-only audit.

Simplicity check: one frozen root/limit plan, plain reports and one-off external
producers; no storage service, new repository scripts workflow, preparation
framework, or obsolete-code removal. The reusable walkthrough remains deferred.

Exact next action: scope Task 027's Box verification and backup contract using
the candidate source ZIPs, CA/BC trees including masks/sidecars, legacy reference,
and audit; carry the derived-artifact exclusions and unresolved semantics.
Task 027 has not started. Stop before transfer or preparation implementation.

### Filename/split clarification follow-up (2026-10-26)

The user recalled overlapping content under different filenames and requested
an unsplit, unrepaired raw baseline for Box. Task 026 created no splits. Current
CA sources use unsplit `images/labels`; BC retains delivery train/val folders.
The current merge uses `all/` but has derived/repaired labels. Older
`merged_ds`/`hakai_match` have 218/41/30 train/val/test pairs. Split CSVs are
separate assignments, not evidence that source TIFFs were changed.

Read-only full SHA-256 comparisons confirmed image and label equality between
short-name CA source pairs and differently named `hakai_match/raw_data` pairs:

| Current CA stem | Reconstructed long stem | Image SHA-256 | Label SHA-256 |
|---|---|---|---|
| `001_20200422_173136_2277` | `20200422_173136_01_2277_3B_AnalyticMS_SR_8b_harmonized_baja_islaNavidad` | `5e42f47b27508f2fe3951852c80b7a9c7b5640429ae4fffd3eb0a34eebb6c9d0` | `68645c767cf02a5649d46bdd32cd0d164b79bb635c8f5ebd747cc873317dc947` |
| `008_20201010_180745_2304` | `20201010_180745_75_2304_3B_AnalyticMS_SR_8b_harmonized_bigSur` | `f18f88be39015686398b88204b62182322d2cafc5b604eaccd8f65ecb6cb002a` | `3b7e516473ae28f2b74117c3f687abf7bb552354fbece78bb59f4d869f27af3b` |

The 339 current filenames include 325 archive-name matches and 14 mappings from
longer extra-data names; they are not a proven unique-content count or proof of
which renaming happened first. The follow-up did not modify the completed
external audit package, source data, or archive payloads. Current guidance now
requires unchanged delivery preservation and a separate alias/hash crosswalk,
with future repairs and experimental splits outside the raw baseline. No Box
action started. A full content reconciliation remains future bounded work.

### Organized-intermediate design follow-up (2026-10-27)

The user accepted the three source ZIPs as the raw baseline and requested a
separate unsplit 369-pair intermediate: 339 CA-family pairs plus 30 BC tiles,
short stable names, unchanged TIFF contents, a region name/code table including
BC, and per-file longer/shorter-name and source-path provenance. Cleaning must
be a separate reproducible stage. The six full BC scenes remain preserved in
raw inputs without being added to the declared 369-pair intermediate.

A read-only existence check found all 369 `source_image` and 369 `source_label`
paths referenced by the existing merge manifest. Use those original payloads
or verified raw ZIP members; do not reverse repairs from current merged labels.
Member-path crosswalks are available for all 369 pairs: 325 in `ca_data.zip`,
14 in `extra_data.zip`, and 30 in the BC ZIP. This verifies naming/membership
recoverability, not archive payload integrity. Long aliases are documented for
290 identities (260 CA plus 30 BC); the remaining 79 CA identities in regions
006/007/011 have no verified long alias in the examined evidence. A recorded
legacy CSV alias is distinguished from the actual source ZIP member name.
Legacy names are not unique region keys (005/006 both say `channelIslands`),
and long product aliases are not available for every source, so provenance must
retain exact original relative paths without fabricating missing names.

`docs/data_artifacts.md` now owns the planned three-stage boundaries and mapping
fields; architecture and roadmap route organization separately from cleanup.
No intermediate was produced and no ZIP extraction, source/data change, upload,
or Task 027 execution occurred. This is a design follow-up to the completed
audit; implementation belongs to later bounded task contracts.

### Final closeout and three-variant roadmap (2026-10-27)

Task 026 is closed. The agreed variants are 1 raw (three unchanged ZIPs),
2 organized intermediate (369 byte-preserved pairs, short names and provenance
tables), and 3 cleaned intermediate (separate recorded transformations). Both
intermediates remain unsplit; unavailable long aliases use exact source paths.
The user selected the three ZIPs as sufficient raw-baseline scope; extra
CA/BC folder copies are optional, not a prerequisite for Task 027.

The owned data/artifact and architecture contracts record this design. The
roadmap now separates implementation into Tasks 029A (organization) and 029B
(cleanup), and publication into Tasks 030A (variant 2) and 030B (variant 3).
These remain unselected scope slots, not new implementation contracts. The
walkthrough starts after verified Box setup and Task 030B, in Task 031; split
assignments remain Task 032. The README and queues point to scoping Task 027.

Final repository changes are documentation only: `README.md`,
`docs/architecture.md`, `docs/data_artifacts.md`, `docs/cleanup_provenance.md`,
`docs/documentation.md`, `docs/index.md`, `docs/todo.md`, `tasks/README.md`, and
this task. Markdown links/anchors, fences, whitespace, and `git diff --check`
were verified. A bounded independent review checked routing, stage boundaries,
and backup scope. Prior numerical/artifact validation above remains the audit
evidence; no new inference, data preparation, source mutation, environment
change, or transfer was performed during closeout. The external audit remains
read-only and unchanged.

Exact next action: write Task 027's contract, verify the configured Box transfer
path and account limits, test a small verified round trip, then back up raw
variant 1 plus the reference/audit under that contract. Task 027 is not started
by this documentation commit.
