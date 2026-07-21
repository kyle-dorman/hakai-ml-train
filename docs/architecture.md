# Architecture contract

For navigation, start with `docs/index.md`. Read this file when changing data
flow, manifest schemas, preprocessing, split materialization, training,
prediction, or metric aggregation.

## Active workflow

```text
California images/labels + BC 10-km tile images/labels
  -> independent image copies + exact-grid derived labels
  -> source-aware image nodata and KATE class 3 repair
  -> raster manifest
  -> overlapping NPZ chips under `all/`
  -> chip manifest with dimensions, class counts, and nodata counts
  -> universal nodata filtering
  -> training-only background selection manifest
  -> portable canonical archive
  -> hard-linked baseline and LORO dataset views
  -> Lightning training and W&B run records
  -> chip predictions and additive confusion counts
  -> source-TIFF, region, and test-set summaries
```

Each stage must be restartable and leave enough manifest evidence to validate
the next stage without inferring identity from folder order.

## Active components

- `scripts/create_temporal_baseline_split.py`: deterministic baseline raster
  assignment.
- `src/prepare/make_chip_dataset.py`: restartable GeoTIFF-to-NPZ chip creation
  with portable source-window identity, effective source nodata metadata, and
  canonical chip statistics.
- `scripts/repair_planet8b_nodata_metadata.py`: report-only and transactional
  scoped repair for derived labels, source fragments, corrected statistics,
  dependent membership, and audit evidence.
- `src/prepare/remove_tiles_with_nodata_areas.py`: manifest-driven nodata
  selection with a required percentage threshold, report-only dry runs, and a
  quarantined transactional apply path that preserves filter history. Task 006
  selected the universal 50% threshold, and Task 007 applied it.
- `src/prepare/remove_bg_only_tiles.py`: manifest-only background classifier and
  deterministic training selector. It writes one selection row per canonical
  chip plus global, region, and source-TIFF audit summaries; it never opens or
  deletes NPZ files.
- `src/data.py`: NPZ-backed Lightning data module.
- `src/models/smp.py`: binary segmentation Lightning module.
- `trainer.py`: Lightning CLI entry point.
- `configs/kelp-ps8b/california/segformer_b3.yaml`: current reference model
  configuration, pending path and run-context updates.

## Identity contracts

The stable hierarchy is:

```text
dataset -> region_id -> source_tiff_id -> chip_id
```

- `region_id` is the unique geographic fold key.
- `source_tiff_id` is the default cross-run comparison key.
- `chip_id` is unique and maps to exactly one source TIFF.
- Source TIFF stems must be unique across the canonical merged dataset.
- A chip may appear in multiple hard-linked experiment views, but its canonical
  identity and content do not change.

Do not derive region or source membership from mutable split directories when a
manifest field exists.

## Manifest contracts

The raster manifest owns source/merged paths, dataset, region, acquisition date,
image/label pairing, image copy mode, and label-preparation mode. Label
alignment provenance owns source/output grids and class-3 assignment counts;
copy provenance owns source/output image checksums and inode independence.
Portable raster metadata owns source grid shape, CRS, affine transform, and
bounds after raw TIFFs are left out of the remote archive.
The chip manifest owns chip path, source TIFF, effective source nodata value,
region, date, source-window
offsets/bounds, width, height, class pixel counts, ignore count, nodata count,
and nodata percentage. The training-selection manifest owns derived class
presence, the explicit background policy, and training eligibility. Fold
manifests own experiment split and the reason each chip was selected.

Manifest writes should be deterministic and atomic. Filtering must preserve a
separate removal or exclusion report rather than erasing provenance.

## Split materialization

The baseline joins chips to `planet8b_temporal_image_splits.csv` through source
TIFF ID. LORO views use region ID. Hard links avoid duplicating canonical chip
content. Both materializers join the Task 008 selection one-to-one by `chip_id`
and require `selected_for_training = true` only for training rows. Baseline
validation/test rows and LORO validation/test rows bypass that selector and
remain representative of the canonical post-nodata collection.

The canonical chip grid uses 1024-pixel windows at 512-pixel stride, anchored
at the source raster's top-left pixel. A source dimension below 1024 pixels is
represented by one true-size window spanning that dimension; canonical NPZs
are not padded, and their manifest width, height, and bounds describe only real
source pixels. Dimensions at least 1024 pixels retain full windows only, so
trailing edge strips outside the regular grid remain uncovered. Training views
retain all eligible overlapping chips. Validation and test views select the
non-overlapping subset where both pixel offsets are multiples of 1024;
evaluation coverage must be reported. This is a manifest selection from one
canonical chip family, not a second evaluation artifact. Any later transform
that pads a small canonical chip must fill its mask with the `-100` ignore
index, not class-0 background.

The approved and materialized LORO policy is:

- test: the retained non-overlapping-grid chips from the held-out region;
- train: baseline-TRAIN chips from other regions, with the selected
  background-only training policy;
- validation: baseline-VAL chips from other regions;
- non-held-out baseline-TEST chips: unused in that LORO fold.

The 12 hard-linked folds are rooted at
`/home/sky/data/planet8b_all_regions_1024_512_v2/views/loro_v1`. `ca_005` and
`ca_006` remain separate folds keyed by canonical region ID despite sharing a
descriptive name.

Any change to that policy must be recorded in the relevant task before runs are
launched.

## Training and evaluation

The comparison suite should use one selected model config, seed policy, and
training budget. Dataset and W&B context should be injected by the runner rather
than maintained through 13 manually edited YAML copies.

Prediction must save chip diagnostics plus source-window identity. For
overlapping chips, reconstruct one probability per covered source pixel before
thresholding and calculating TIFF confusion counts. Region and test-set metrics
then sum the non-overlapping TIFF confusion counts. Do not sum overlapping chip
confusion counts into TIFF metrics. Ignore-index and uncovered pixels do not
contribute, and coverage must be reported. Validation and final test evaluation
use the non-overlapping materialized subset; overlap reconstruction remains
required for any evaluation artifact that includes overlapping chips.

## Compatibility boundary

Legacy configs and source modules may remain importable. They are not active
documentation or design constraints for this project. Do not preserve a stale
PS8B behavior if a numbered task deliberately replaces it, but do not perform
unrelated repository-wide cleanup.
