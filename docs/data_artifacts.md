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

`rclone` is installed and a remote named `kelp-box` is configured. That is not
proof of a working connection or a verified backup. Task 027 verifies access,
chooses the project folder, checks actual account/file-size constraints, tests
a small upload/download, and backs up identified originals and the reference.
Do not assume the old 45 GB ZIP is a suitable Box transfer unit. Prefer explicit
upload/download copies with verification over deletion-propagating sync.
Credentials remain outside Git, logs, dataset manifests, and task records.

Keep integration to ordinary versioned folders, portable manifests, and
documented direct rclone upload/download/check operations. Use rclone's existing
transfer behavior; do not create a custom cloud storage or synchronization
framework.

## Existing local evidence

A bounded inventory on 2026-10-26 found these artifacts. Counts/existence are
fresh inventory observations; payload hashes were not rerun in that inventory.
The original collection's full membership still requires user-assisted audit.

| Family | Existing location | Inventory |
|---|---|---|
| California sources | `/Volumes/x10pro/kelpseg/ca` | 339 paired image/label TIFFs |
| BC source family | `/Volumes/x10pro/kelpseg/bc/Planet8bSR_BC_Labelled/10km_tiles` | 30 paired image/label TIFFs |
| Previously cleaned merge | `/Volumes/x10pro/kelpseg/merged_all_regions_v1` | 369 pairs across 12 region IDs |
| Previously filtered chips | `/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1` | 4,602 NPZs, 367 sources, 12 regions |
| Repaired transfer archive | `/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v2.zip` | 44,859,496,084 bytes; checksum sidecar present |

The downloaded reference checkpoint is
`/Users/kyledorman/Downloads/kelp_ps8b_segformer_b3_epoch-62_val-iou-0.7047.ckpt`.
Task 025 preserved a verified copy and six preselected development-chip results
under `/Volumes/x10pro/kelpseg/references/legacy_ps8b_v1` before source removal.
Its completion manifest, original pairs, probabilities, masks, visually checked
previews, hashes, and standalone verifier are local; Box backup remains Task 027.
See [Task 025](../tasks/025_capture_legacy_reference.md#outcome-2026-10-26) for
capture semantics and validation. Treat this versioned reference as immutable.

Earlier `merged_ds`, `pre-chipped-8b`, other collection folders, and historical
archives may contain originals, duplicates, or derived products. Task 026 must
classify them without changing anything. Do not infer that the two listed
source families are the complete original delivery solely from old docs.

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

Make expensive work restartable and verify identities before reusing outputs.
Refuse missing pairs, duplicates, silent overwrites, and partial manifest
publication. Never mutate original source imagery or labels. A small verified
transfer is required before large upload/download operations.

After Box setup and the cleaned release, Task 031 selects a tiny real-data
walkthrough subset and stores it with the external release, with documented
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
