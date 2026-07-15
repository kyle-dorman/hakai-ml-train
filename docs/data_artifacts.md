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

The Task 004 unfiltered canonical chip collection is:

```text
/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
```

It contains 6,003 NPZ chips from all 369 source TIFFs. The regular grid is
1,024 pixels at 512-pixel stride; 52 chips use true source dimensions where an
entire source dimension is below 1,024 pixels. Images are eight-band `uint16`;
labels remap KATE classes with `0 1 0 -100 0`. `chip_manifest.csv` has SHA-256
`7fd2316ae07c4c5277ff33a62ae4c1ee60ced14a528e6a153a6489a7e457d9c8`.
`chip_counts_by_source.csv`, `chip_qa_summary.json`,
`creation_command.txt`, and `chipping.log` own its counts, validation,
parameters, and execution provenance. This collection is unfiltered: no
nodata or background chips have been removed. Task 009 will record the
portable archive and checksum. Task 010 will record the remote extracted path.

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
