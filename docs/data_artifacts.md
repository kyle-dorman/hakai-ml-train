# Data and artifact contract

For navigation, start with `docs/index.md`. Read this file before creating,
moving, filtering, deleting, archiving, transferring, or interpreting data and
generated artifacts.

## Storage boundary

The code repository tracks source, configs, small split metadata, documentation,
and task contracts. Large or generated artifacts live outside git.

Current local root:

```text
/Volumes/x10pro/kelpseg
```

Current verified source families:

```text
/Volumes/x10pro/kelpseg/ca
/Volumes/x10pro/kelpseg/bc/Planet8bSR_BC_Labelled/10km_tiles
```

The old CSV-limited merge and chips are historical inputs, not the new canonical
dataset:

```text
/Volumes/x10pro/kelpseg/merged_ds
/Volumes/x10pro/kelpseg/pre-chipped-8b/1024_512_20250814_cali_bc
```

The Task 002 canonical raw merge is:

```text
/Volumes/x10pro/kelpseg/merged_all_regions_v1
```

It contains independent image copies and exact-image-grid derived labels. After
Task 009A, raw label class `3` follows source-aware image nodata for all repaired
sources: the California repair preserves four accepted edge-only class-3 false
positives, while all 30 BC labels are rebuilt from raw `{0,1}` labels and use
class `3` exactly at image nodata. Later chipping/remapping converts class `3`
to the training ignore index. `raster_manifest.csv`, `copy_verification.csv`,
`label_alignment.csv`, `raster_metadata.csv`, and the raster QA artifacts own
its provenance.

The canonical chip collection built by Task 004 and filtered by Task 007 is:

```text
/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
```

Task 004 created 6,003 NPZ chips from all 369 source TIFFs. The regular grid is
1,024 pixels at 512-pixel stride; 52 original chips use true source dimensions
where an entire source dimension is below 1,024 pixels. Images are eight-band
`uint16`; labels remap KATE classes with `0 1 0 -100 0`.
`chip_counts_by_source.csv`, `chip_qa_summary.json`, `creation_command.txt`,
and `chipping.log` retain the original chipping counts, validation, parameters,
and execution provenance.

Task 007 applied `max_nodata_pct = 50`, retaining 4,637 NPZ chips and
44,912,049,410 compressed bytes from 367 source TIFFs across all 12 regions.
The active collection contains 47 true-size partial chips and preserves all
521 clean background-only chips. Active `chip_manifest.csv` has SHA-256
`edf754888dea183f12873594b546b980f350b5b4e293ff62ca7eca64a2c39a39`.

Task 009A superseded that active membership after source-aware repair. The
current collection contains 4,602 NPZ chips and 44,854,174,488 compressed bytes
from 367 source TIFFs across all 12 regions, including 47 true-size partial
chips. The corrected 6,003-row inventory has 1,401 total removals: the original
1,366 plus 35 metadata-nodata additions. Active `chip_manifest.csv` has SHA-256
`b8b14d8db7910fe7de69803a669ce8922b07fa401a0d99999019f5cc1f12886f`.
Repair plans, pre-repair snapshots, label audits, row-level statistic changes,
the 724-row rewritten-NPZ inventory, combined removals, summaries, and
completion metadata are under `repair_history/metadata_nodata_v2`.

The refreshed Task 008 non-destructive production selection is under
`background_selection/exclude_all`. `training_selection.csv` joins one-to-one
to all 4,602 active chips, retains the 3,210 positive chips for training, and
explicitly excludes 440 clean background-only and 952 mixed
background/nodata chips. `selection_summary.csv` reports all four categories
globally, for every region, and for every source TIFF, including zero-count
categories. Their SHA-256 hashes are
`200db4b41f84cacd00296b86f5cc50174368f568fa8540eb1c704567484b38fa` and
`2531b1494f21cfcc54a6339a5517190bcf20a224f9dc64e3d72512e89f9fb0ce`,
respectively. These small artifacts belong in the portable archive; the
selector does not change canonical NPZs or `chip_manifest.csv`.

Task 009's v1 portable canonical archive is:

```text
/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip
```

It is a 44,917,177,439-byte ZIP64 archive with SHA-256
`6640757c19d803a000834b34abdb20c71a5359e215e8edf08b4958123c4ab098`;
the adjacent `.zip.sha256` sidecar owns that transfer checksum. The archive has
one versioned dataset root and 4,653 files: 4,637 canonical NPZs, nine portable
manifests, six compact metadata/provenance files, and
`metadata/archive_inventory.csv`. The inventory records byte size and SHA-256
for all 4,652 other payload files, including every NPZ, and has SHA-256
`a07d8326a8b3946907aeb04c0fac042e714a7c226b96c24d6f93302c33f01fbc`.
Runtime manifests resolve from the extracted dataset root and contain no local
absolute path dependency; original raster paths are isolated in the optional
`metadata/local_raster_path_provenance.csv`. A clean local extraction passed
full inventory verification, manifest joins, and sampled NPZ validation under
the former all-band-zero nodata definition. A later audit found five California
TIFFs that declare `65535` as nodata, so this v1 archive is preserved as
historical evidence but must not be transferred.

Task 009A's transfer candidate is:

```text
/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v2.zip
```

It is a 44,859,496,084-byte ZIP64 archive with SHA-256
`1244ecfe2cc4cee624bb5661087f0126ea239367bda60efd823b4fcb9b7399db`.
The archive contains one versioned dataset root and 4,624 files: 4,602 NPZs,
13 manifests, eight metadata/provenance files, and the inventory itself. The
4,623-row inventory has SHA-256
`9e1e393229ba4bf22ab5b30bdf6756f3c9a4737c27ff67bb3d9e125e5830c408`.
It reuses 4,120 unchanged NPZ hashes from the checksum-verified v1 inventory
and freshly hashes all 482 retained rewritten NPZs plus 21 changed
manifest/metadata members. A clean extraction passed archive checksum, ZIP
integrity, path/size joins, all fresh hashes, a 74-chip reused-hash sample, and
portable NPZ/manifest validation.

Task 010 downloaded, checksum-verified, fully inventory-validated, and cleanly
extracted that v2 archive on the original SkyPilot host. Its canonical root
was:

```text
/home/sky/data/planet8b_all_regions_1024_512_v2
```

The remote staging ZIP and checksum sidecar remain under
`/home/sky/dataset-staging`. The durable verification receipt is
`metadata/remote_archive_verification.log` inside the extracted dataset root.
No `/home/taylor/data` compatibility symlink was created. That GPU host is no
longer available. Task 014A must establish and record a newly verified remote
canonical root before Task 014 resumes; the same path is recommended when the
replacement user is also `sky`, but the old host's existence is not assumed.

Nodata dry-run reports belong under an explicit analysis or `filter_reports`
directory and never change the active collection. An applied threshold writes
`filter_history/nodata_<threshold>/pre_filter_manifest.csv`,
`removal_manifest.csv`, and `filter_metadata.json`; the metadata is the
completion marker for the quarantined transaction. Task 007 also records
`post_filter_summary.csv` and `apply.log` there. The active manifest is replaced
atomically only in explicit apply mode.

Task 006's versioned decision evidence is under
`/Volumes/x10pro/kelpseg/nodata_threshold_analysis_v1`. The user-approved
universal policy is `max_nodata_pct = 50`: keep chips at or below 50% source-
aware image nodata and remove chips above 50%. Task 007 originally applied the
zero-only implementation of that policy:
4,637 of 6,003 chips are active and 1,366 were removed, representing
3,245,804,422 compressed bytes. No region was eliminated. Source TIFFs
`006_20210805_184050_240c` and
`20210811_185433_06_2262_3B_AnalyticMS_SR_8b_harmonized_clip5` lost all chips.
The immutable pre-filter manifest has SHA-256
`7fd2316ae07c4c5277ff33a62ae4c1ee60ced14a528e6a153a6489a7e457d9c8`;
the removal manifest has SHA-256
`37fd56e8f679aebe370a187528dbfb646e09e3c349211d2208b0177fef8f7bcb`.

## Git policy

Tracked:

- Python and shell source.
- YAML configs.
- `planet8b_temporal_image_splits.csv` and its generator.
- Small hand-authored or decision-support GeoJSON/CSV metadata when a task makes
  it part of the reproducible contract.
- Docs and task files.

Not tracked:

- Raw or merged GeoTIFF imagery and labels.
- NPZ chips.
- Archives and checksums tied to local generated archives.
- Checkpoints and W&B run directories.
- Predictions, large metric tables, figures, and generated reports.

## Canonical artifact families

1. Raw source mirrors: immutable California and BC image/label pairs.
2. Merged raw dataset: independent copied images and exact-grid derived labels
   under `all/images` and `all/labels`, plus raster manifest, copy/alignment
   provenance, portable source-grid metadata, and QA report.
3. Canonical chips: un-split NPZ files plus chip statistics manifest.
4. Filter evidence: nodata analysis, approved threshold, removal manifest, and
   background-selection reports.
5. Portable archive: cleaned canonical chips, manifests, split CSV, parameter
   note, inventory, and SHA-256 checksum.
6. Experiment views: hard-linked baseline and LORO train/validation/test folders
   plus fold manifests.
7. Run artifacts: checkpoints, run registry, W&B artifacts, predictions, and
   chip/TIFF metric tables.
8. Comparison artifacts: matched-TIFF tables, region summaries, and final plots
   or reports.

## Provenance requirements

Nontrivial artifact-producing steps should record:

- producer command and git commit;
- input and output paths;
- manifest or fold version and hash;
- dataset, region, source TIFF, date, and split where relevant;
- chip size, stride, bands, dtype, remapping, and ignore index;
- nodata definition and selected threshold;
- retained, removed, and excluded counts with reasons;
- seed and model config for training artifacts;
- run ID and checkpoint for prediction artifacts;
- warnings and unresolved validation issues.

Paths inside the portable archive and chip/fold manifests must be relative to an
explicit dataset root. Local absolute paths may appear in raw-merge provenance,
but must not be required after remote extraction.

## Mutation rules

- Never modify or delete raw source TIFFs.
- Use dry-run before large merge, filtering, archive, or materialization steps.
- Refuse partial manifest updates and silent overwrites.
- Preserve removal manifests when canonical chips are filtered.
- Background-only selection must not delete canonical chips.
- Verify archive checksum and inventory before and after transfer.
