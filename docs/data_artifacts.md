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

It contains independent image copies and exact-image-grid derived labels. Raw
label class `3` means nodata wherever all eight image bands are zero or source
label coverage is absent; later chipping/remapping converts that class to the
training ignore index. `raster_manifest.csv`, `copy_verification.csv`,
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
Task 009 will record the portable archive and checksum. Task 010 will record the
remote extracted path.

Nodata dry-run reports belong under an explicit analysis or `filter_reports`
directory and never change the active collection. An applied threshold writes
`filter_history/nodata_<threshold>/pre_filter_manifest.csv`,
`removal_manifest.csv`, and `filter_metadata.json`; the metadata is the
completion marker for the quarantined transaction. Task 007 also records
`post_filter_summary.csv` and `apply.log` there. The active manifest is replaced
atomically only in explicit apply mode.

Task 006's versioned decision evidence is under
`/Volumes/x10pro/kelpseg/nodata_threshold_analysis_v1`. The user-approved
universal policy is `max_nodata_pct = 50`: keep chips at or below 50% all-eight-
band-zero pixels and remove chips above 50%. Task 007 applied that exact policy:
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
