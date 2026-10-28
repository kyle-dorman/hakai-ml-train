# Original collections and cleanup provenance

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

The installed preparation surface is shared `organize`, two-tier `check`, and
`clean`; there is no separate BC command/intermediate. The historical results above
remain evidence for the old derived data. The new
[Task 029B contract](../tasks/029b_clean_organized_sources.md) supersedes the
historical BC background-fill rule: outside annotation coverage in paired data
becomes all-band image zero plus label 3. Cleaned image metadata declares
nodata 0; cleaned label metadata declares nodata 3, preserving valid label 0.
Original nodata must be identified before normalization. Raw/organized sources
remain unchanged; new image hashes and transformation counts are expected.

Coverage/reason arrays can be used internally; persistent QA masks are optional
and off by default. Keep counts, original/output grids, policies, hashes and
companion dispositions so ignored pixels need no manual mask inspection.
Image-only processing does not require labels or remove valid imagery for lack
of annotations. Existing logic/tests are reused with explicit assertions for
these new decisions, rather than claiming historical pixel equality everywhere.

The current alignment reads raw native label crops and uses Rasterio nearest
reprojection directly. It preserves class-zero water and computes footprint
coverage without using source masks or nodata metadata. Its supported paired
scope is same-CRS, north-up unrotated imagery and single-band `uint8` labels;
other grids/dtypes fail explicitly. This replaces the earlier virtual-raster
wrapper without changing the declared categories or exclusion policy.

All preparation runs from beginning to end in one attempt. A failure leaves a clearly
marked incomplete directory and never publishes the final release. A new run
starts over; there is no automatic recovery or reuse of unfinished output.

## Remaining limits and later preparation

- The three source ZIPs and historically inventoried CA/BC folders account for the observed
  scope, but no independent delivery manifest establishes that they exhaust
  all original deliveries. Preserve their candidate status.
- All 325 companion-mask grids match their CA image grids; mask meanings were
  not decoded. Preserve them and establish their semantics before using them.
- Six CA and 31 BC image headers name the eight physical bands as
  `coastal_blue, blue, green_i, green, yellow, red, rededge, nir`. The other
  333 CA and five BC headers are untagged or generic. Do not extend those names
  to every source merely from channel count or a conventional RGB display.
- Historical background filling does not independently establish negative
  annotation truth beyond the BC mosaic's coverage. The cleaned release retains
  coverage provenance; scoring must explicitly state its labeled/scored scope. Existing
  processing history and new scientific interpretation are separate questions.
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
owned by [data_artifacts.md](data_artifacts.md#planned-raw-intermediate-and-cleaned-releases).
