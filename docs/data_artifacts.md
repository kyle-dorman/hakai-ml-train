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
and generated reports stay outside Git. Historical tracked split CSVs remain as
small legacy records; external copies are preserved in Task 032A. New generated splits are external. Keep current
split-generation rules in Git.

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

Use source identities and known filename aliases to reconcile differently named
copies; retain every delivery association and any existing content evidence.
Reject unresolved known conflicts without adding new payload hashing.
The 339 CA filenames are not yet a proven unique-content count. Backup of
unchanged deliveries does not require deleting duplicates or resolving every
alias first. Task 027 verified copies while preserving this variant-1 boundary.

## Current local working set

Keep current cleaned imagery, canonical chips, split/collection controls and tiny
inputs under `data/`, plus analyses, references, audits, preparation inputs,
backup evidence and small historical experiment results. Local raw ZIPs and
organized v1 payloads were evicted after verified Box publication; restore them
from Box only when needed for reconstruction. Box releases remain immutable.

Small historical controls, the 31 pre-repair label snapshots and retired
bootstrap source/tests are at
`/Volumes/x10pro/kelpseg/history/legacy_pre_rebuild_v1/`, preserving their former
relative paths. The finished `preparation_inputs/ca_bc/v1/` catalog stays active.
The installed preparation/loading workflows do not require the obsolete
merge/chip directory layout. Bulk old datasets,
ZIP/TAR copies, local smoke checkpoints and generated smoke/restore/example runs
were removed. The [Task 032C record](../tasks/032c_archive_legacy_and_evict_local_data.md)
contains the pre-execution deletion plan, archive scope and measured results.
The archive is local only; this cleanup performed no Box operation.

## Box project organization and upload verification

Use the verified project root `kelp-box:kelpseg` and its [recorded folder identity](box_backup.md).
Task 027 populated the raw/reference/audit paths; Task 030A verified the organized
`data/2_organized/ca_bc/v1` release and its separate transfer evidence. Task 030B
verified `data/3_cleaned/ca_bc/v1` and its own evidence. Task 032B published
`data/chips/ca_bc/v1`, `data/splits/ca_bc/v1`,
`data/collections/ca_bc/v1` and `data/examples/tiny_ca_bc/v2`.
Other locations below are reserved until their owning tasks publish them:

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
  transfers/task030a_organized_ca_bc_v1/     # organized QA, checks, completion
  transfers/task030b_cleaned_ca_bc_v1/       # cleaned QA, checks, completion
```

Create only needed folders as work arrives. Keep versioned payloads at their
project locations and never silently overwrite a release. Existing transfer
evidence stays with its historical release.

For all tasks, the user's current direction is plain manifests, ordinary
functions and minimal bookkeeping. Do not add new hashing, checksum catalogs,
authentication catalogs, transfer receipts or verification frameworks. This
supersedes the heavier requirements in older contracts. Existing published
hashes/receipts and implemented legacy command behavior remain documented as
historical evidence and current behavior; they are not requirements for new work.

Use ordinary explicit rclone copies and compare relative paths, file counts and
sizes. Test a bounded representative restore by opening/loading the actual data
and comparing small arrays where useful. Record the scope and limits in the task
outcome; do not call path/size or load checks checksum verification. Keep sources
immutable, stop on errors and use fresh versioned destinations.

## Adding regions and combined datasets

All datasets are peers. The current 369-pair scope can be dataset `ca_bc`, with
exactly the same variant folders, release versions, manifests, preparation and
storage rules as any other dataset. It is not an automatic parent or mandatory
member of later collections. Every published release remains unchanged, whether
it was created first or later. "Baseline" is an explicitly chosen experiment
role, not a privileged storage or ingestion category.

Raw folders identify source bundles/deliveries: one can cover several regions,
and one region can occur in several deliveries or datasets. Regions are explicit
metadata, independent of delivery, dataset/release, and filename identity.

For every dataset, including the current one:

1. Preserve its original files under a new `data/1_raw/<delivery_id>/`, with
   source metadata and an ordinary Box backup. Leave earlier raw
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
arrive. Tasks 029A/029B implement extensible preparation; Task 032A supplies
collection-aware assignments and Task 032B published the full release;
Task 037 uses those prepared data for its four
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
   inputs retain their valid imagery. Record original/output paths, grids,
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
2026-10-27. Keep source/output identity explicit during production; no source is
renamed or modified in place. Original image/label grids may differ at this
stage, including full regional BC label mosaics; alignment belongs to cleanup.

The organizer publishes `images/`, `labels/`, `regions.csv`, `sources.csv`, and
`filename_aliases.csv`. Variant 3 retains those identities/crosswalks and records
variant-2 parent references and cleanup parameters/changes. Historical releases
also retain their existing hashes.
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
archive names, exact source member paths, and separate input/output image and
label references. Existing hashes stay as historical metadata. Preserve all
known longer-name and shorter-name aliases
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

## Historical local evidence

A bounded inventory on 2026-10-26 found the artifacts below. Their paths/counts
describe that historical inventory, not current local availability. Task 032C
evicted the bulk payloads and retained small controls/snapshots in the history
archive above. Payload hashes were not rerun by that inventory. The original
collection's full historical delivery membership remains unconfirmed.

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
unconfirmed. Raw ZIPs and the organized Box release preserve source/companion
payloads; local historical controls and snapshots preserve the cleanup evidence.

## Reconstructing cleanup

1. Inventory candidate collections, filenames, pairings, existing evidence,
   source metadata, region/date identity, band order, label classes, and grids.
   Distinguish original deliveries, derived artifacts, duplicates, and unknowns.
2. Trace representative cleaned CA/BC pairs back to candidate originals. Explain
   label remapping, reprojection/alignment, missing coverage, and nodata changes.
   Ask about unexplained differences before encoding a new cleaning rule.
3. Write a short researcher-readable preparation recipe in Git and include a
   copy with the external release. Record what changes, why, source evidence,
   exact producing command/config, and validation.
4. Test the transformation on small raster fixtures and real examples. Rebuild
   into a new versioned root. Preserve original deliveries on Box and retain
   useful historical controls/snapshots; obsolete local derived payloads may be
   evicted under an explicit recorded cleanup scope.
5. Publish practical source/cleaned/chip inventories, split assignments and
   parameters with each dataset release. Check counts/paths/sizes and a bounded
   restore/load example before calling its Box copy usable.

Previous cleanup aligned labels to image grids and repaired source-aware nodata,
including some declared `65535` sources rather than only zero. CA labels used a
KATE mapping; BC originally used binary labels. Tasks
[002](../tasks/002_create_and_validate_raw_merge.md) and
[009A](../tasks/009a_repair_metadata_nodata_and_repackage.md) hold detailed
historical evidence. Re-establish these rules from actual inputs; do not apply
a single remap to every label family without checking its meaning.

The old chip recipe used 1024-pixel windows/512 stride, a 50% nodata cutoff,
and training-only exclusion of non-positive chips. The replacement's selected
defaults are configurable 512-pixel windows, stride 256 and a 50% maximum
image-nodata cutoff. Keep partial edge chips at their true source size, with
explicit padding during loading. The current
[study and decision](../tasks/031_chipping_bands_and_tiny_walkthrough.md#512-pixel-analysis-outcome-2026-10-27)
record unique per-TIFF coverage, the projected-cleanup scope, exact producer/
parent identities and external evidence paths. Retain canonical background
chips and all nodata-excluded identities/reasons without requiring excluded
payloads. Keep chip eligibility consistent across experimental assignments;
test results never choose it. Sliding-window inference has its own declared
footprint and does not inherit training-chip omissions.

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

Task 031's reusable tiny inputs are external at
`<data_root>/data/examples/tiny_ca_bc/v1/` and
`kelp-box:kelpseg/data/examples/tiny_ca_bc/v1/`: nine crop pairs across regions
002/003/012, three dates per region, including a 768-by-769 partial-edge case.
`metadata.csv` keeps original TIFF identity, region/date, dimensions and crop
offsets; `selection.json` describes the selection and band assumption. Chips
belong separately under `<data_root>/examples/runs/<fresh-name>/`.
See [the walkthrough](quickstart.md#tiny-real-data-walkthrough) for fetch and
offline use. Real payloads/generated metadata stay outside Git; synthetic
correctness fixtures stay in Git. Task 025 remains a separate historical reference.

The published example at `<data_root>/data/examples/tiny_ca_bc/v2/` and the
matching Box path has 13 crop pairs, preserving v1 and its partial edge.
V2 has 28 files / 82,537,678 input bytes; fetch it once for offline use.
The installed splitter writes a plain crop collection, Task 031 chip-identity
export and original-source assignments separately from the chip payload root.
Dataset/release/source references are explicit; generated controls contain no
machine paths. [The split walkthrough](quickstart.md#tiny-v2-split-chip-and-load-locally)
owns the routine recipes; Tasks 032A and 032A.1 record validation/output paths.

Task 032A.1 selects disjoint existing validation/test windows while retaining
all canonical chips and overlapping training windows. Overlap exclusions are
manifest selections with reason `evaluation_overlap`, not payload deletions or
per-fold copies. Uncovered edge/gap geometry is explicit; no new edge chips are
created. Keep candidate/retained payload counts separate from active evaluation
window counts when publishing/restoring the release.

The full native-band `ca_bc/v1` chip release is at
`data/chips/ca_bc/v1/` locally and on Box: 369 sources, 40,571 candidate
windows, 26,573 retained payloads (14,386 background-only and 2,982 partial
edges), 13,998 nodata omissions; 26,577 files / 65,565,628,953 bytes including
controls. Every source has retained windows. `data/splits/ca_bc/v1/` contains
five controls / 935,947 bytes, covering both variants and ten LORO folds.
`data/collections/ca_bc/v1/collection.json` is a 539-byte declaration with
relative cleaned/chip/split references and the existing split `collection.csv`.
It does not copy TIFFs or duplicate the collection CSV. Runtime readers take
explicit local chip/split roots.

With-BC `augmented` is primary; `base` is the comparison. Active baseline
window counts are 18,311/933/1,262 train/val/test with BC and
15,621/933/1,262 without BC. All 6,067 retained evaluation overlap exclusions
remain canonical. The baseline evaluation input footprint is 906,445,909
geometric pixels: disjoint nominal grid 872,744,371, retained selected area
557,094,374, uncovered edges/gaps 33,701,538 and nodata-omitted grid area
315,649,997. These include native nodata within retained windows and exclude
padding; they are not valid-label support, geographic area or model scores.
[Task 032B](../tasks/032b_produce_and_publish_chip_release.md#outcome-2026-10-28)
owns complete fold counts/coverage, ordinary Box inventory comparisons and
bounded restore/load results. [The quickstart](quickstart.md#restore-and-use-the-full-cabc-chip-release)
owns the fetch/use recipe. No per-fold or spectral copies exist.

For all tasks the user explicitly removed new hashing/checksum/catalog/receipt
machinery. The Task 031
example used ordinary copy/fetch with relative path/size checks and bounded array
comparisons, without new checksum verification. Chipping retains practical
source/band/window/shape/exclusion metadata and a compact completion summary;
it does not inherit the organizer/cleaner authentication machinery. Historical
recorded checksums remain evidence for those older releases. No study upload or
new authentication catalog is required.

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
`preparation_inputs/<dataset>/<version>/` outside Git. The existing CA/BC
catalog at `preparation_inputs/ca_bc/v1/` was constructed
from Task 026/027 evidence and remains unchanged. The historical bootstrap is
retired; its source and historical input controls are archived under
`history/legacy_pre_rebuild_v1/`. Normal organization reads the finished tables
directly. Other datasets supply the same tables without a dataset-specific
bootstrap. Restore the raw ZIPs to their declared paths before rebuilding.

The full unsplit `ca_bc/v1` organized release is preserved on Box at
`kelp-box:kelpseg/data/2_organized/ca_bc/v1`; its formerly verified local payloads
were evicted by Task 032C. Release totals remain: 369 pairs, 418 companions,
3,919 aliases, 1,163 total files and
28,568,499,959 bytes. Root manifest SHA-256:
`435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8`.
[Task 030A's outcome](../tasks/030a_build_and_publish_organized.md#outcome-2026-10-27)
owns the complete identity and QA/transfer evidence; [Box recovery](box_backup.md#restore-the-organized-cabc-release)
owns the fetch/check recipe. All primary pixels decoded; 34 grid mismatches,
355 label nodata declarations and 326 paired nodata findings remain preserved
in the immutable parent; Task 030B repaired its separate cleaned output. Companion
internal strings stay unchanged, and internal-TIFF headers do not establish
unknown physical band or mask semantics.

The full unsplit cleaned `ca_bc/v1` is verified locally at
`/Volumes/x10pro/kelpseg/data/3_cleaned/ca_bc/v1` and on Box at the same project
relative path: 369 aligned pairs/12 regions, 747 files / 18,662,320,805 bytes.
Its authenticated root manifest SHA-256 is
`43815a8a7e412d0f0ed021c813c6c3b4f3a9a532a4fcbb3f9624a91bbdd5ba61`,
derived from the organized parent identity above. All output pixels passed full
cleaned QA; exact remote inventory/checksums and a bounded three-pair restore
passed. All 418 companions remain inactive hashed parent references, with exact
source/region/alias/asset snapshots; they are not copied active output payloads.
Labels retain categories 0–4, image nodata 0/label ignore 3, and the approved
outside-annotation exclusion. Source absolute paths are operational provenance;
restored images/labels load independently. [Task 030B](../tasks/030b_build_and_publish_cleaned.md#outcome-2026-10-27)
owns detailed evidence and limits; [Box recovery](box_backup.md#cleaned-cabc-v1)
owns trusted completion/catalog identities and the fresh-directory recipe.

Published release payloads are immutable. The historical organized/cleaned
releases include completion hashes over their payload/control files; new work
uses the simpler policy above. The existing organizer's portable plan identity covers
normalized declarations, recipe values and delivery content/evidence identities;
resolved machine paths, stat hints and logs do not define that identity. It is
provenance, not a job-recovery protocol.

Organization, catalog construction and cleanup write once into a fresh sibling
`.<output-name>.incomplete`, check the full result, then rename it to the final
output. Neither the final nor incomplete path may already exist. Preparation has
no resume, writer lock, saved per-file receipt or recovery journal. A failed run
leaves the incomplete directory; inspect and deliberately move/remove it before
a full rerun, or choose a fresh output. Keep practical source paths, original/
output grids, counts and a compact completion summary. Existing commands retain
their recorded hash fields; new workflows do not add hash machinery.
