# Data and artifact contract

## Storage and Git boundary

The local data root is `/Volumes/x10pro/kelpseg`. UCLA Box through rclone is
the target backup and transfer store for original, cleaned, and chipped data,
plus the manifests/split assignments required to use them. Keep checkpoints,
resolved recipes, reference examples, and compact results recoverable there too.

Track source, preparation/split algorithms, small hand-authored configs,
focused fixtures/tests, human cleanup documentation, and task records in Git.
Store real dataset manifests and generated split assignments with versioned
external data releases. Large imagery, chips, archives, checkpoints, predictions,
and generated reports stay outside Git. The currently tracked split CSVs move
out during the replacement split task, after their historical copies are saved.
Do not remove the split-generation rules.

`rclone` is installed and a remote named `kelp-box` is configured. Task 027 verified the project folder, account limits, small round trip, and backup. See [Box backup and recovery](box_backup.md) for actual paths and recipes.
Do not assume the old 45 GB ZIP is a suitable Box transfer unit. Prefer explicit
upload/download copies with verification over deletion-propagating sync.
Credentials remain outside Git, logs, dataset manifests, and task records.

Keep integration to ordinary versioned folders, portable manifests, and
documented direct rclone upload/download/check operations. Use rclone's existing
transfer behavior; do not create a custom cloud storage or synchronization
framework.

Raw uploads preserve source deliveries without repairs, filename normalization,
deduplication, or new experimental train/val/test assignments. Preserve source
archives and as-received directory/member names, masks, and sidecars. Existing
BC delivery folders named train/val are historical provenance, not assignments for the new
workflow. Treat the raw catalog as one unsplit collection. Keep any future
cleaned release and generated split assignments separate.

Use a separate filename/hash crosswalk to reconcile differently named copies;
hash images and labels independently and retain every delivery association.
The 339 CA filenames are not yet a proven unique-content count. Backup of
unchanged deliveries does not require deleting duplicates or resolving every
alias first. Task 027 verified copies while preserving this variant-1 boundary.

## Box project organization and upload verification

Use the verified project root `kelp-box:kelpseg` and its [recorded folder identity](box_backup.md). The following layout reserves locations for future work; only the Task 027 payload and transfer paths have been populated:

```text
kelpseg/
  data/
    1_raw/
      ca_bc_sources_v1/                    # current three-ZIP source bundle
      <delivery_id>/                       # any other delivery, same rules
    2_organized/<dataset_id>/<release>/     # unchanged TIFFs, short names, crosswalks
    3_cleaned/<dataset_id>/<release>/       # cleanup with parent provenance
    collections/<collection_id>/<version>/ # manifests referencing dataset releases
    chips/<dataset_id>/<release>/
    splits/<collection_id>/<version>/      # separate from underlying data
  references/legacy_ps8b_v1/
  audits/task026_originals_v1/
  runs/                        # later: experiments/models/results
  transfers/task027_raw_reference_audit_v1/  # receipts, checks, completion
```

Create only needed folders as work arrives. Keep versioned dataset payloads at
their project locations; transfer receipts refer to them rather than creating
another full data copy per transfer. Never put receipts inside a closed
reference/audit package or silently overwrite an existing release.

The default for this and future dataset uploads is a local SHA-256 identity
plus a provider-native transfer checksum. For Box, compare **every file's
SHA-1, byte size, and relative path** with Box metadata; rclone's
[Box documentation](https://rclone.org/box/#modification-times-and-hashes)
documents SHA-1 support. Require actual nonempty checksum values; `--checksum`
alone may fall back to size and is not sufficient verification evidence.

Calculate local SHA-1 and SHA-256 together in one intentional read of finalized
files when no trusted catalog exists. Reuse verified immutable-release catalogs
when their identity/provenance remains valid; size/mtime alone is not proof of
content identity. Do not force repeated full rehashes or full remote readbacks
for every upload. Check source metadata before/after and rehash affected files
when inputs change or trust in a saved catalog is lost. Rclone may perform its
own hashing during transfer; this policy avoids extra deliberate full passes.

Use streamed remote SHA-256 readback for affected files if native checksums
are missing or disagree; use a whole-release deep readback only when explicitly
requested or justified by a recorded problem. Diagnose a mismatch; do not
accept size-only matches or silently ignore conflicting hashes. Record each
file's method as `provider_sha1_verified` or `readback_sha256_verified`, with
native-checksum failures retained as evidence. This distinguishes provider
verification from end-to-end download verification without forcing both.

Keep the initial small real round trip. Task 027 also restored the relatively
small reference/audit packages and runs their own SHA-256 verifiers; it does not
redownload all raw ZIPs by default. Later large releases use their scoped task's
bounded restoration check with the same checksum/fallback policy. No extraction
or per-TIFF hashing inside raw ZIPs is required merely to back up those ZIPs.

## Adding regions and combined datasets

All datasets are peers. The current 369-pair scope can be dataset `ca_bc`, with
exactly the same variant folders, release versions, manifests, preparation and
checksum rules as any other dataset. It is not an automatic parent or mandatory
member of later collections. Every published release remains unchanged, whether
it was created first or later. "Baseline" is an explicitly chosen experiment
role, not a privileged storage or ingestion category.

Raw folders identify source bundles/deliveries: one can cover several regions,
and one region can occur in several deliveries or datasets. Regions are explicit
metadata, independent of delivery, dataset/release, and filename identity.

For every dataset, including the current one:

1. Preserve its original files under a new `data/1_raw/<delivery_id>/`, with
   hashes, provenance and the normal checksum-based backup. Leave earlier raw
   folders unchanged; new dates from an existing region are a new delivery too.
2. Register any new stable region codes/names without renumbering existing
   regions. Version the small mapping/settings in Git and publish a mapping
   snapshot with the external release. Keep original aliases/source paths.
3. Run the same organization stage into its own dataset/release under variant
   2, then shared cleanup with explicit supported-input settings into variant 3.
   Use explicit
   input manifests and recipes, not Python edits or an unconditional old CA/BC
   class mapping. Each stage preserves parent identities and has its own QA.
4. Publish a versioned collection manifest selecting any one dataset, any region
   subset, or any combination of datasets. It references exact cleaned releases
   and eligible source identities; it does not require copying their TIFFs into
   another merged directory or changing earlier releases. No dataset is included by
   default. Research recipes choose which collection is the reference, training,
   adaptation or evaluation scope for that experiment.
5. Generate new versioned chip/split artifacts for the declared scope, reusing
   compatible immutable chip releases when identity/recipe matches. Keep fixed
   held-out assignments explicit. Check renamed duplicate imagery across
   deliveries and reject unresolved identity/label-version conflicts; duplicates
   must not cross train/validation/test merely because their names changed.

Keep raw deliveries and all aliases even when a collection resolves duplicates.
This is a few manifests and ordinary folders, not a dataset-management service.
The researcher guide gains a copyable "add a region" recipe as these stages
arrive. Tasks 029A/029B implement extensible preparation; Task 032 supplies
collection-aware assignments; Task 037 uses those prepared data for its four
new-region comparisons. None of that ingestion is executed by Task 027.

## Planned raw, intermediate, and cleaned releases

User direction on 2026-10-27 establishes three numbered dataset variants.
Variants 2 and 3 are the two intermediates before chipping; these variant
numbers describe processing stages, not release version numbers.
These same variants apply to every dataset. The current ZIPs and 369-pair count
below define only the first dataset's input scope, not special pipeline rules.

1. **Raw sources:** for the current dataset, preserve the three ZIPs unchanged:
   `ca_data.zip`, `extra_data.zip`, and `Planet8bSR_BC_Labelled.zip`, with archive
   hashes. These are sufficient for the user's declared raw-delivery scope;
   this does not assert that every historical delivery elsewhere is known.
2. **Organized intermediate:** one unsplit collection of the current 369 pair
   identities (339 CA-family pairs plus 30 BC tiles), with short stable names,
   but unchanged image/label bytes, grids, classes, nodata, and sidecars/masks
   where applicable. Organization and renaming are the only transformations.
   The six BC full scenes remain in the raw sources, outside this intermediate's
   declared tile scope. Source delivery train/val paths are provenance only.
3. **Cleaned intermediate:** derive aligned/repaired labels and normalize actual
   image nodata pixels plus metadata to 0. Labels keep valid class-zero
   background and use nodata/ignore value and metadata 3. For paired data,
   outside-label coverage becomes all-band image zero plus label 3; image-only
   inputs retain their valid imagery. Record original/output hashes, grids,
   nodata rules, changed-pixel counts and asset dispositions. Detailed coverage/
   reason rasters are optional QA outputs, off by default. Keep this collection
   unsplit too; experimental assignments arrive separately after chipping.

There is no `bc_cleaned` stage. Shared checking/cleanup handles CA/BC through
the same functions and explicit settings. The production route remains
raw → organized → cleaned. Ordinary directories can also be checked/cleaned
without a published organizer catalog; optional supplied metadata adds verified
lineage without inventing missing region/date/band evidence. The installed
commands and explicit settings are documented in [quickstart.md](quickstart.md).

Rebuild the intermediate from verified raw ZIP members, or verified source
folders, using the existing 369-row merge manifest to establish membership and
upstream paths. Do not try to undo the repaired labels in
`merged_all_regions_v1`; that collection is historical derived evidence.
All 369 referenced source image and source label paths were present on
2026-10-27. Check each source/output byte hash during production; no source is
renamed or modified in place. Original image/label grids may differ at this
stage, including full regional BC label mosaics; alignment belongs to cleanup.

The organizer publishes `images/`, `labels/`, `regions.csv`, `sources.csv`, and
`filename_aliases.csv`. Variant 3 retains those identities/crosswalks and records
variant-2 parent hashes, cleanup parameters/changes, and new output hashes.
The region table retains existing
CA codes 001–011 and their legacy region IDs/names; code 012 is
the BC tile group, retaining legacy ID `bc`. Region code is the key: 005 and
006 both have historical name `channelIslands` and must stay distinct.
Filename construction must preserve enough date/scene/tile information to avoid
collisions, especially multiple BC tiles from the same scene. Freeze and test
the exact naming rule in the implementation task rather than inventing names
from row order.

For every pair, the portable source manifest records canonical ID, region code,
legacy source ID, acquisition date, output-relative image/label paths, source
archive names/hashes, exact source member paths, and separate input/output
image and label hashes. Preserve all known longer-name and shorter-name aliases
with their evidence and alias type (archive member or recorded legacy name);
allow several aliases per role. Existing evidence provides long aliases for
290 identities (260 CA and 30 BC); the other 79 CA sources have exact short
archive member paths but no verified long alias. For many CA files the long name
is a legacy CSV alias, not the actual name inside the source ZIP. An original
relative path is sufficient when no verified long product name survives. Never
fabricate a missing long name. Keep repeated-image/different-label associations
and BC shared-mosaic label relationships explicit; content equality must not
silently remove pair identities.

Versioned preparation code and recipes stay in Git; generated release manifests
and payloads stay outside Git. Expose separate organize and clean stages through
the small installed command, rather than keeping a permanent scripts
directory. Given the same verified raw inputs, mapping/configuration, and code,
the stages must reproduce membership, byte identities of organized copies,
cleaning decisions, and output provenance. Tasks 028–029B implemented the
package, organization, checking and cleanup; Tasks 030A/030B build and publish
the full variants 2 and 3.
[Task 027](../tasks/027_verify_box_and_back_up_raw_reference_audit.md#outcome-2026-10-27) verified the Box backup of variant 1, the reference, and audit.

## Existing local evidence

A bounded inventory on 2026-10-26 found these artifacts. Counts/existence are
fresh inventory observations; payload hashes were not rerun in that inventory.
The original collection's full membership still requires user-assisted audit.

| Family | Existing location | Inventory |
|---|---|---|
| California sources | `/Volumes/x10pro/kelpseg/ca` | 339 paired image/label TIFFs |
| BC source family | `/Volumes/x10pro/kelpseg/bc/Planet8bSR_BC_Labelled` | 30 tile pairs and six full-scene pairs |
| Previously cleaned merge | `/Volumes/x10pro/kelpseg/merged_all_regions_v1` | 369 pairs across 12 region IDs |
| Previously filtered chips | `/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1` | 4,602 NPZs, 367 sources, 12 regions |
| Repaired transfer archive | `/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v2.zip` | 44,859,496,084 bytes; checksum sidecar present |

The downloaded reference checkpoint is
`/Users/kyledorman/Downloads/kelp_ps8b_segformer_b3_epoch-62_val-iou-0.7047.ckpt`.
Task 025 preserved a verified copy and six preselected development-chip results
under `/Volumes/x10pro/kelpseg/references/legacy_ps8b_v1` before source removal.
Its completion manifest, original pairs, probabilities, masks, visually checked
previews, hashes, and standalone verifier are also backed up on Box.
See [Task 025](../tasks/025_capture_legacy_reference.md#outcome-2026-10-26) for
capture semantics and validation. Treat this versioned reference as immutable.

Task 026's read-only audit reconciled CA's 339 IDs to 325 `ca_data.zip` families
plus 14 `extra_data.zip` mappings, and identified the older 289-pair `merged_ds`
and reconstructed `hakai_match` as derived collections. Its verified report is
at `/Volumes/x10pro/kelpseg/audits/task026_originals_v1`. See
[cleanup_provenance.md](cleanup_provenance.md) for observed lineage, prior
cleanup decisions, and remaining coverage/mask/band questions. Archive indexes
were listed without verifying payloads; original-delivery completeness remains
unconfirmed. Preserve candidate originals, companion masks, and sidecars.

## Reconstructing cleanup

1. Inventory candidate collections, filenames, pairings, hashes where useful,
   source metadata, region/date identity, band order, label classes, and grids.
   Distinguish original deliveries, derived artifacts, duplicates, and unknowns.
2. Trace representative cleaned CA/BC pairs back to candidate originals. Explain
   label remapping, reprojection/alignment, missing coverage, and nodata changes.
   Ask about unexplained differences before encoding a new cleaning rule.
3. Write a short researcher-readable preparation recipe in Git and include a
   copy with the external release. Record what changes, why, source evidence,
   exact producing command/config, and validation.
4. Test the transformation on small raster fixtures and real examples. Rebuild
   into a new versioned root; preserve every original and old derived collection.
5. Publish source/cleaned/chip inventories, split assignments, payload hashes,
   parameters, QA receipt, and completion identity with each dataset release.
   Verify the local release and its Box copy before calling it backed up.

Previous cleanup aligned labels to image grids and repaired source-aware nodata,
including some declared `65535` sources rather than only zero. CA labels used a
KATE mapping; BC originally used binary labels. Tasks
[002](../tasks/002_create_and_validate_raw_merge.md) and
[009A](../tasks/009a_repair_metadata_nodata_and_repackage.md) hold detailed
historical evidence. Re-establish these rules from actual inputs; do not apply
a single remap to every label family without checking its meaning.

The old chip recipe used 1024-pixel windows/512 stride, a 50% nodata cutoff,
and training-only exclusion of non-positive chips. Treat these as documented
reference choices to examine during reconstruction. Retain canonical background
chips and store exclusion reasons explicitly. Keep nodata policy consistent
across train/validation/test; test results never choose it.

## Portable release requirements

Use stable relative paths plus explicit dataset roots. Retain region/source/date,
source grid/CRS/transform, window placement, band identity/order, dtype, class
mapping, ignore index, nodata rules, chip geometry, and exclusions. Split
assignments identify their generator/config/seed and source inventory. Cross-band
experiments share source assignments. Never rely on hard-linked directory
layouts or local absolute paths to recover membership on another machine.

Preparation runs in one pass and never reuses interrupted outputs. Each step
stops on failure; the next attempt starts from the beginning into a fresh output.
Refuse missing pairs, duplicates, silent overwrites, and partial manifest
publication. Never mutate original source imagery or labels. A small verified
transfer is required before large upload/download operations.

After Box setup and Task 030B's cleaned intermediate 3, Task 031 selects a tiny
real-data walkthrough subset and stores it with the external release, with documented
membership and a one-time fetch recipe. Keep real example payloads outside Git;
small synthetic test fixtures remain in Git. After fetching, routine walkthrough
checks work without Box or W&B access. The earlier Task 025 legacy capture is
a separate reference artifact and retains its original place in the queue.

## Historical experiment artifacts

Tasks 000–023 and starting commit
`ac933fd667c2ddb445b8a622d8404387a2d056e2` retain the old study's provenance.
Remote paths in those records are historical and do not establish a live host
or surviving outputs. Inventory any local exports separately.

Task 023's corrected schema-3 `predictions_all_retained_v2` and
`comparisons/matched_tiffs_all_retained_v2` are the historical primary results.
Earlier all-retained-v1 and non-overlap prediction/report packages have the
undersized center-padding crop bug and are invalid for scientific use on the
affected imagery. Preserve that distinction if recovering old artifacts.

## Organization input catalogs and current execution boundary

The implemented organizer reads explicit portable tables and recipe settings;
[quickstart.md](quickstart.md#organize-raw-sources) owns their complete schema
and operating recipes. Generated declarations live under
`preparation_inputs/<dataset>/<version>/` outside Git. The one-time
`kelpseg.prepare.legacy_catalog.build_legacy_ca_bc_catalog` converter reconstructs the
current input catalog from the named Task 026 metadata and Task 027 trusted
archive catalog. It does not read source payloads. Other datasets supply the
same tables directly.

The full 369-pair metadata plan is reconciled. Task 029A permits only a separate
two-pair smoke dataset; it does not create or publish the full `ca_bc/v1`
organized release. Task 030A owns full member hashing/materialization, production
QA and verified Box copy. Shared cleanup is implemented; Task 030B owns the
full cleaned build/publication. Source grids may differ, companions retain
original internal strings, and internal-TIFF header
records do not establish unknown physical band or mask semantics.

Published release payloads are immutable and include completion hashes over
all payload/control files. The organizer's portable plan identity covers
normalized declarations, recipe values and delivery content/evidence identities;
resolved machine paths, stat hints and logs do not define that identity. It is
provenance, not a job-recovery protocol.

Organization, catalog construction and cleanup write once into a fresh sibling
`.<output-name>.incomplete`, check the full result, then rename it to the final
output. Neither the final nor incomplete path may already exist. Preparation has
no resume, writer lock, saved per-file receipt or recovery journal. A failed run
leaves the incomplete directory; inspect and deliberately move/remove it before
a full rerun, or choose a fresh output. Source/output hashes, source paths,
original/output grids, counts and the final completion manifest remain required.
Completed releases can be independently verified without rerunning preparation.
