# Task 003: Extend the chipper and define the chip manifest

Status: Pending

Depends on: Task 002

Execution: Local code and fixture task; do not run full chipping.

## Abstract

Extend `src/prepare/make_chip_dataset.py` so the canonical `all` raw dataset can
be chipped once and later materialized into baseline and LORO views entirely
from manifests. The manifest must contain pixel/class/nodata statistics and the
source-window geometry needed to reconstruct overlapping chip predictions into
one source-TIFF prediction without double-counting pixels. This task implements
and smoke-tests the contract; Task 004 performs the full run.

## Goal

Support `--splits all`, consume the raster manifest, and write deterministic,
restartable per-chip metadata with enough spatial identity for correct TIFF
reconstruction.

## Inputs

- Task 002 canonical raw root, raster manifest, portable raster metadata, and
  QA summary
- `src/prepare/make_chip_dataset.py`
- `src/data.py`
- `docs/architecture.md`
- `docs/data_artifacts.md`
- `docs/product.md`
- `planet8b_temporal_image_splits.csv`

## User decisions required

Before implementation, confirm the evaluation-overlap contract because it
determines mandatory manifest columns.

Recommendation:

- retain overlapping chips for training;
- record source pixel window offsets and geospatial bounds for every chip;
- during TIFF-level prediction, average foreground probabilities for every
  source pixel covered by multiple chips, threshold once after averaging, and
  score each source pixel once;
- retain coverage counts so uncovered/overlapped pixels are auditable.

Alternative: create separate non-overlapping evaluation chips. That is simpler
but introduces a second chip artifact family and different train/eval windows.

The user does not need to choose final chip size, stride, dtype, remapping, or
worker count until Task 004. This task must keep them CLI-configurable.

## Planned CLI changes

```bash
uv run python -m src.prepare.make_chip_dataset \
  <raw-root> <chip-root> \
  --splits all \
  --source-manifest <raw-root>/raster_manifest.csv \
  --manifest-output <chip-root>/chip_manifest.csv \
  --size <pixels> --stride <pixels> --num_bands 8 \
  --dtype <dtype> --remap <values> \
  [--resume]
```

Add or formalize:

- `all` as an allowed split name;
- required `--source-manifest` for canonical manifested runs;
- `--manifest-output`, defaulting to `<output>/chip_manifest.csv`;
- explicit `--resume`; without it, refuse a nonempty target split;
- current `--num_workers` behavior.

## Chip manifest schema

CSV is the portable canonical format. Columns in stable order:

```text
chip_id,chip_path,source_tiff_id,dataset,region_id,region_name,
acquisition_date,source_width,source_height,source_crs,
chip_index,row_off,col_off,chip_width,chip_height,
minx,miny,maxx,maxy,total_pixel_count,
class_0_pixel_count,class_1_pixel_count,ignore_pixel_count,
nodata_pixel_count,nodata_pct,image_dtype,label_dtype
```

If Task 002 finds more than two retained label classes, generate one sorted
`class_<value>_pixel_count` column per non-ignore class and record the exact
schema in the outcome. `nodata_pct` is `100 * nodata_pixel_count /
total_pixel_count` and uses `[0, 100]` units.

Path and geometry rules:

- `chip_path` is relative to the chip root.
- `source_tiff_id` joins exactly to the raster manifest.
- Source width/height/CRS agree with `raster_metadata.csv`; the source affine
  transform remains owned by that table rather than repeated in every chip row.
- `row_off` and `col_off` are integer pixel offsets in the source raster grid.
- Width/height describe the stored chip. Partial edge windows remain excluded
  unless Task 004 explicitly reopens that current behavior.
- Bounds use the source CRS and must agree with offsets and affine transform.
- `chip_id` is deterministic from source TIFF ID and window identity, not only
  loop order. Recommended form: `<source_tiff_id>__r<row>_c<col>_h<h>_w<w>`.

## Statistics contract

- Count label classes after remapping into the stored label array.
- Count `-100` separately as ignore.
- Class counts plus ignore count must equal total pixels.
- Nodata is all retained image bands equal to zero at a pixel.
- Nodata is an image statistic independent of label class.
- Do not overwrite nodata labels to background before statistics are recorded.
  If current stored-label behavior must remain, document both the original
  nodata mask and final stored-label counts.
- Record actual stored image/label dtype.

## Restartability and write contract

- Produce one temporary manifest fragment per completed source TIFF.
- Write a source TIFF's chips and fragment transactionally enough that resume
  can distinguish complete from partial work.
- `--resume` verifies existing chip files against the fragment before skipping.
- Consolidate fragments deterministically into the canonical manifest using an
  atomic rename.
- Never append duplicate rows blindly.
- A failed source must leave an actionable issue/log record and must not be
  represented as complete.

## Plan / spec requirement

Before code edits, add an implementation plan covering:

- deriving pixel offsets/bounds from TorchGeo queries and the source transform;
- passing raster-manifest metadata into the per-source loop;
- preserving current NPZ loading compatibility;
- transactional fragments/resume behavior;
- how nodata-label behavior changes or remains compatible;
- exact fixture geometry for overlap reconstruction.

## Smoke test

Create a tiny georeferenced 8-band raster and aligned label raster whose values
make expected windows and class/nodata counts obvious. Use overlapping windows.
Prove:

- correct number and identity of chips;
- correct offsets/bounds;
- correct class, ignore, and nodata counts;
- manifest-to-NPZ agreement;
- resume produces no duplicates;
- a synthetic probability reconstruction from manifest windows counts each
  source pixel once after overlap averaging.

## Validation

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run pytest tests/test_make_chip_dataset.py
git diff --check
```

Also run a bounded smoke against one real California TIFF and verify its
manifest geometry against Rasterio window calculations.

## Acceptance criteria

- `all` chipping and raster-manifest joins work.
- Every saved NPZ has exactly one manifest row and vice versa.
- The manifest supports correct overlap-aware TIFF reconstruction.
- Statistics reconcile to stored arrays.
- Resume and failure behavior are tested.
- Existing train/val/test calls remain supported.
- Task 004 has an exact command template with only run parameters undecided.

## Non-goals

- Do not run all 369 TIFFs.
- Do not select the production chip parameters.
- Do not remove nodata or background chips.
- Do not materialize experiment folds.
- Do not implement model inference beyond the small reconstruction proof.

## Review pass

- ML researcher: verify statistics and no label/split leakage.
- Remote-sensing researcher: verify window, CRS, transform, and overlap logic.
- Software architect: verify restartable artifact and manifest ownership.

## Outcome template

Record the approved overlap contract, final CLI/schema, compatibility changes,
fixture evidence, real-TIFF smoke result, validation, and exact Task 004
decision list.
