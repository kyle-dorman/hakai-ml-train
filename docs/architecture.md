# Architecture contract

For navigation, start with `docs/index.md`. Read this file when changing data
flow, manifest schemas, preprocessing, split materialization, training,
prediction, or metric aggregation.

## Active workflow

```text
California images/labels + BC 10-km tile images/labels
  -> merged raw `all/images` + `all/labels`
  -> raster manifest
  -> overlapping NPZ chips under `all/`
  -> chip manifest with dimensions, class counts, and nodata counts
  -> universal nodata filtering
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
- `src/prepare/make_chip_dataset.py`: GeoTIFF alignment and NPZ chip creation;
  Tasks 003–004 extend it with canonical chip statistics.
- `src/prepare/remove_tiles_with_nodata_areas.py`: current overly aggressive
  nodata filter; Tasks 005–007 replace its policy with a manifest-driven
  percentage threshold.
- `src/prepare/remove_bg_only_tiles.py`: current destructive filter; Task 008
  turns background removal into a training-view selection.
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
and image/label pairing. Portable raster metadata owns source grid shape, CRS,
affine transform, and bounds after raw TIFFs are left out of the remote archive.
The chip manifest owns chip path, source TIFF, region, date, source-window
offsets/bounds, width, height, class pixel counts, ignore count, nodata count,
and nodata percentage. Fold manifests own experiment split and selection reason.

Manifest writes should be deterministic and atomic. Filtering must preserve a
separate removal or exclusion report rather than erasing provenance.

## Split materialization

The baseline joins chips to `planet8b_temporal_image_splits.csv` through source
TIFF ID. LORO views use region ID. Hard links avoid duplicating canonical chip
content.

The current planned LORO policy is:

- test: all retained chips from the held-out region;
- train: baseline-TRAIN chips from other regions, with the selected
  background-only training policy;
- validation: baseline-VAL chips from other regions;
- non-held-out baseline-TEST chips: unused in that LORO fold.

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
contribute, and coverage must be reported.

## Compatibility boundary

Legacy configs and source modules may remain importable. They are not active
documentation or design constraints for this project. Do not preserve a stale
PS8B behavior if a numbered task deliberately replaces it, but do not perform
unrelated repository-wide cleanup.
