# Data and artifact contract

## Storage and Git boundary

Keep source, preparation/split rules, small hand-authored configs, focused
fixtures/tests, human cleanup documentation and task records in Git. Keep real
imagery, chips, generated manifests/split assignments, checkpoints, predictions,
and reports outside Git under a machine-specific artifact root.

Set `data_root` and `runs_root` in your local paths file; see
[preparation settings](guides/preparation.md#set-paths-once-per-machine).
Use UCLA Box through rclone for backup and transfer. Credentials stay outside
Git, logs and manifests. The [release reference](reference/ca_bc_release.md)
owns current CA/BC locations and recovery evidence; local absolute paths there
are historical locations, not required paths on another machine.

## Current local working set

Keep the cleaned imagery, canonical chips, collection/split controls and tiny
inputs needed for current work under `data/`. Analyses, models, audits and
references stay in separate external folders. Restore raw or organized inputs
only when reconstruction needs them. Existing releases remain immutable.
Historical evictions and retained controls are recorded in the
[release reference](reference/ca_bc_release.md#historical-local-cleanup-and-retained-controls).

## Box project organization and upload verification

Mirror this layout under the local artifact root and `kelp-box:kelpseg`:

```text
data/
  1_raw/<delivery_id>/
  2_organized/<dataset_id>/<release>/
  3_cleaned/<dataset_id>/<release>/
  collections/<collection_id>/<version>/
  chips/<dataset_id>/<release>/
  splits/<collection_id>/<version>/
  examples/<example_id>/<version>/
preparation_inputs/<dataset_id>/<version>/
runs/
analyses/
references/
audits/
```

Create only folders needed for the work. Use plain manifests and ordinary
copies, compare relative paths/counts/sizes, and test a bounded representative
restore by opening the actual data. Record verification scope accurately.
Do not add hashing, checksum catalogs, authentication catalogs, transfer
receipts or verification frameworks. Existing hashes and receipts remain
historical release evidence. See [Box operations](box_backup.md).

## Raw, organized and cleaned releases

Dataset stages are processing stages, not release version numbers:

1. **Raw:** preserve deliveries unchanged, including archive member names,
   sidecars and masks. Delivery folders named train/val are provenance, not
   experimental assignments. Keep raw inputs unsplit.
2. **Organized:** give sources stable identities and short names while preserving
   image/label bytes, grids, classes, nodata and companion associations.
3. **Cleaned:** align categorical labels to imagery and normalize image nodata
   to zero. Preserve valid class-zero background; stored label ignore is 3.
   Outside annotation coverage in paired data is all-band image zero plus label
   3, mapped to -100 during loading and excluded from loss/scoring. Image-only
   processing retains valid imagery without requiring labels.

Both intermediates are unsplit. Chipping and experimental source assignments
are separate outputs. There is no separate BC cleanup stage. The supported
settings, input tables and commands are in the [preparation guide](guides/preparation.md).

## Adding regions and combined datasets

Every dataset follows the same storage/preparation rules. A raw delivery can
span regions, and a region can span deliveries. Region identity is explicit,
independent of delivery names and dataset/release identity.

1. Preserve each new delivery in its own raw folder; never rewrite an earlier
   release, including when adding new dates to an existing region.
2. Register stable region codes without renumbering existing regions. Keep
   original aliases and paths. Region codes remain distinct even when names match.
3. Organize and clean using explicit input tables and supported recipe settings.
   Do not silently reuse a label mapping for a different label family.
4. Publish an explicit versioned collection selecting exact cleaned releases and
   source identities. Collections may select a subset or combine datasets without
   copying them into a merged TIFF directory; none is included by default.
5. Generate versioned chip/split artifacts, reusing compatible immutable chips.
   Reject unresolved identity/label conflicts and keep renamed copies of the same
   imagery from crossing partitions.

This is a folder/manifest policy. The dedicated four-case new-region experiment
recipe is still planned in Task 039; it is not an implemented automatic workflow.

## Portable release requirements

Use relative paths plus explicit roots. Preserve source TIFF, dataset/release,
region, acquisition date, band order, source CRS/grid, source window and crop
placement. Keep label mapping, ignore/nodata rules, chip geometry and exclusions
with each release. Split assignments retain generator/config/seed and source
inventory; spectral comparisons share source assignments.

Keep canonical background-only chips. Training exclusions are manifest
selections, not payload deletion. Validation/test use disjoint existing windows;
keep overlap exclusions and geometric coverage separate from valid-label support.
See [architecture](architecture.md) for current loading and scoring contracts.

Preparation runs once into a fresh output and stops on failure. Both final and
sibling `.<output-name>.incomplete` paths must be absent. Publication occurs only
when the complete step succeeds. If interrupted, inspect the incomplete output
and start a full new attempt with a fresh name. There is no preparation resume or
partial-work reuse. Existing published releases can be verified read-only.
Never mutate original imagery or labels; refuse missing identities, duplicate
identities and silent overwrites.

## Shoreline reference and derived analysis

Preserve supplied shoreline exports as immutable raw references. Derived
land/distance rasters, cluster-ID rasters, inventories and augmented reports
belong in fresh external analysis folders, separate from cleaned imagery/chips.
Keep source identity, CRS/transform, distance convention/cap, input references,
geometry repair counts and coverage assumptions with them.

Cluster IDs are local to one source and acquisition; they do not identify
biological beds across dates. Zero is known background and uint32 maximum is
unavailable/ignored support. Keep full observed component sizes and boundary
fragment flags. Expected training-window exposure counts repeated appearances;
it is separate from unique-pixel label support. These outputs never modify
labels, splits or chip payloads. Recipes are in [diagnostics](guides/diagnostics.md).

## Organization input catalogs and current execution boundary

The organizer reads portable tables under
`preparation_inputs/<dataset>/<version>/`; the
[preparation guide](guides/preparation.md#organize-raw-sources) owns their schema.
The existing CA/BC catalog is retained at `preparation_inputs/ca_bc/v1/` and reads
restored raw ZIPs from its declared paths. It does not need the retired catalog
bootstrap. Other datasets supply the same tables directly.

Preserve source aliases, original member paths and repeated-image/different-label
associations rather than inventing missing aliases or deleting pair identities.
Recorded parent references explain provenance, not preparation recovery.
The [historical cleanup audit](cleanup_provenance.md) and
[release reference](reference/ca_bc_release.md) retain reconstruction evidence.
