# Historical collections and cleanup provenance

This is a historical audit record, not the current operating contract. Use the
[preparation guide](guides/preparation.md) for current cleanup and the
[release reference](reference/ca_bc_release.md) for restoration.

Task 026 completed a read-only local audit on 2026-10-26. The earlier task
records already contain the main cleanup decisions. Six selected source traces
reproduce the existing derived labels exactly; that verifies those histories,
not every source or the completeness of the original deliveries.

Detailed inventories, traces, input hashes, previews, and the completion manifest
are outside Git at `/Volumes/x10pro/kelpseg/audits/task026_originals_v1/`.
Start with `README.txt` and `findings.json`. The
[task outcome](../tasks/026_inventory_originals_and_cleanup_provenance.md#outcome-2026-10-26)
records the checks and producer invocations.

## Current storage

The collection paths below describe Task 026's historical inventory. Task 032C
subsequently evicted their obsolete local payloads and local raw/organized
copies under the user's explicit cleanup instruction. Original raw deliveries
and organized/cleaned/chip releases remain on Box; current cleaned imagery and
chips remain local. Small historical controls and all 31 pre-repair label
snapshots are retained at `history/legacy_pre_rebuild_v1/` under the data root.
The one-time catalog bootstrap is retired; the finished input catalog remains
at `preparation_inputs/ca_bc/v1/`. See the
[cleanup record](../tasks/032c_archive_legacy_and_evict_local_data.md) for the
prewritten plan and results. The audit and references are unchanged.

## Which collections contain what

| Collection | Established evidence | Interpretation |
|---|---|---|
| `ca/` | 339 image/label pairs; 325 companion `nan_mask` rasters | Candidate source collection; raw/companion payloads preserved on Box |
| `zip_archive/ca_data.zip` and `extra_data.zip` | 325 source families plus 14 mapped additional pairs reconcile to CA's 339 IDs | Candidate delivery archives; member indexes do not verify payload integrity |
| `bc/Planet8bSR_BC_Labelled/` | 30 tile pairs and six full-scene pairs; BC ZIP index matches local TIFF paths/sizes | Candidate source collection; original delivery completeness remains unconfirmed |
| `merged_all_regions_v1/` | 369 copied images and aligned/repaired labels, documented by manifests and previous tasks | Derived dataset; its historical raw-merge name does not make labels original |
| `merged_ds/` and `hakai_match/` | Same 289 source identities; manifests document merging and reconstruction/renaming | Older derived collections, omitting 79 CA and one BC source from the current 369 |
| Chips, repaired archives, and `hakai_match_v0.tar` | Chip/repair manifests and archive member listings | Superseded payloads; small historical controls/snapshots retained |

The 79 omitted CA identities are 35 in `ca_006`, 32 in `ca_007`, and 12 in
`ca_011`. The missing BC identity is
`20210813_193301_80_241_8_band_Clip3`. These are membership comparisons, not
instructions to change either collection.

The 339 count describes the current short, region-prefixed CA filenames; it is
not a count of SHA-256-unique image/label pairs. `ca_data.zip` already uses the
short names for 325 families. The 14 `extra_data.zip` pairs have longer product
names mapped to the current short names, while `hakai_match` reconstructs an
older split collection under longer names. Thus the current inventory includes
filename reconciliation; it does not identify who renamed files or establish
which delivery predates every rename.

A read-only follow-up confirmed exact image **and** label hash equality between
the current CA source and the differently named `hakai_match/raw_data` copy for
`001_20200422_173136_2277` and `008_20201010_180745_2304`. These examples establish
renamed byte-identical copies, not a complete cross-collection deduplication.
Preserve aliases and label associations; filename uniqueness is not content
uniqueness, and identical images do not necessarily imply identical labels.

The inventory read 3,000 raster headers across 12,371 scoped files and listed
15,301 archive members. It found 1,322 image/label pairings plus 31 standalone
pre-repair label snapshots. The snapshots deliberately have no colocated image;
they are not missing original pairs. Four CA pairs and all 36 BC pairs have
different original image/label grids. All 369 current merged pairs are aligned.
No input read errors were recorded. ZIP/TAR payloads and NPZ arrays were not
decoded or checksum-verified during this audit.

## Previously recorded decisions and observed results

[Task 002](../tasks/002_create_and_validate_raw_merge.md#execution-finding-and-approved-remediation)
records nearest-neighbor sampling of categorical labels onto each image grid,
preserving stored classes and valid class-zero water even where source label
metadata declares `nodata=0`. BC tile labels can be shared regional mosaics;
repeated content does not establish an erroneous duplicate.

[Task 004](../tasks/004_chip_all_regions_locally.md) records the later binary
mapping `[0, 1, 0, -100, 0]`: kelp becomes foreground; water, land, and waves
become background; stored nodata class 3 becomes ignore `-100`. This historical
mapping is evidence for the identified family, not a universal mapping for
unknown future labels. Task 026 did not generate or remap chips.

[Task 009A](../tasks/009a_repair_metadata_nodata_and_repackage.md#user-decisions-required)
records the later user-approved image-nodata contract: use consistent declared
nodata; for the previously audited metadata-missing cohort, use effective zero.
The existing five declared-`65535` CA sources must not be interpreted as zero
nodata. In the selected repair case, `004_20210525_174950_2463`, exactly 5,203
class-2 pixels became class 3 at all-eight-band `65535` pixels. The preserved
pre-repair label and current label reproduce this change exactly.

The same task explicitly records the later BC decision: class 3 exactly at
image nodata, background 0 outside original annotation coverage where imagery
is valid. This superseded Task 002's earlier outside-coverage class-3 rule.
The outside-coverage trace reproduces 637,016 pixels changing from 3 to 0;
another 3,465,907 pixels outside annotation coverage also have image nodata and
remain class 3. The within-coverage trace has no pre/post change. Both old and
new recipes match the preserved corresponding labels with zero mismatches.
The prior processing decision is recorded; it does not need to be rediscovered
or presented as absent approval.

The selected CA offset-grid case reproduces nearest alignment exactly. The
accepted CA edge case, `008_20201010_180745_2304`, retains 21,471 class-3 pixels
where imagery is valid, as previously documented. In that source, 395 valid
image pixels lie outside annotation coverage. The manifest field
`outside_source_label_not_nodata_pixels` counts outside coverage with a
**derived label other than 3**, so its zero value does not contradict the 395.
Keep image nodata and label class 3 distinct when reading the old QA tables.

## Current rebuild cleanup policy

The current [preparation guide](guides/preparation.md#clean-into-a-separate-directory)
owns cleanup instructions. It supersedes the historical BC background-fill rule:
paired pixels outside annotation are image nodata zero and stored label ignore 3,
mapped to -100 for loss/scoring exclusion. Image-only preparation remains
independent of labels. Raw and organized sources remain unchanged.

## Historical audit limits and subsequent disposition

- The three source ZIPs and historically inventoried CA/BC folders account for the observed
  scope, but no independent delivery manifest establishes that they exhaust
  all original deliveries. This records the audit scope, not an open task.
- All 325 companion-mask grids match their CA image grids; mask meanings were
  not decoded; the current pipeline does not use them as active masks.
- Six CA and 31 BC image headers name the eight physical bands as
  `coastal_blue, blue, green_i, green, yellow, red, rededge, nir`. The other
  333 CA and five BC headers were untagged or generic. This is the recorded
  header inventory; current recipes use the declared band order.
- Historical background filling does not independently establish negative
  annotation truth beyond the BC mosaic's coverage. Current paired cleanup
  excludes that footprint through image nodata and ignored labels.
- Archive listings and recorded CRCs/sizes are not fresh integrity checks or
  proof of a verified backup. Task 027 owns transfer and backup verification.

The user selected the three source ZIPs as the sufficient declared raw scope.
Task 027 verified their Box preservation alongside the legacy reference and
this audit. Archive members, including masks/sidecars, remain unchanged there.
The audit's earlier proposed roots in `findings.json` remain historical evidence
of its inventory scope, not required current local paths.

Tasks 029A/029B implemented organization and shared checking/cleanup;
Tasks 030A/030B built and published the complete 369-pair organized and cleaned
releases. Task 032B published canonical chips, source assignments and tiny v2.
Task 032C then evicted obsolete local datasets and raw/organized copies after
archiving their small historical records. Current cleaned imagery, chips,
analyses, audits and references remain local; Box was untouched by cleanup.
The finished catalog remains available without the retired bootstrap.

The raw catalog stays unsplit. Organization/renaming, cleanup and experimental
assignments remain separate. Source delivery train/val names are provenance,
not adopted experimental memberships. The repaired historical merge cannot
supply original label bytes; its archived manifest identifies source members
preserved in the raw Box delivery. The current release/mapping contract is
owned by [data_artifacts.md](data_artifacts.md#raw-organized-and-cleaned-releases).


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
cleanup decisions, and historical audit observations. Archive indexes
were listed without verifying payloads; original-delivery completeness remains
unconfirmed. Raw ZIPs and the organized Box release preserve source/companion
payloads; local historical controls and snapshots preserve the cleanup evidence.


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
