# Task 003: Extend the chipper and define the chip manifest

Status: Complete

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

Decision (2026-07-15): create one canonical family of 1024-pixel square chips
at 512-pixel stride. Retain the full overlapping family for training and final
test reconstruction. Future validation views select the non-overlapping subset
whose row and column offsets are both multiples of 1024; edge-shifted windows
outside that grid are excluded and validation coverage must be reported. Final
TIFF evaluation averages foreground probabilities over every covered source
pixel, thresholds once, and retains coverage counts.

Size and stride are now fixed at 1024 and 512. Output root, dtype, exact label
remapping, and worker count remain Task 004 decisions. All run parameters stay
CLI-configurable.

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

## Implementation plan

1. Join each discovered image to one unique raster-manifest row by
   `source_tiff_id`, validate the paired label and portable source-grid
   metadata, and carry dataset, region, date, dimensions, CRS, and transform
   into the per-source operation.
2. Preserve the TorchGeo path for existing unmanifested train/validation/test
   calls. For manifested runs, use explicit top-left-anchored Rasterio pixel
   windows and derive bounds from the source affine transform. TorchGeo's grid
   sampler uses a lower-left anchor and ceil-padded edge queries, so it cannot
   provide the required full-window pixel identity without ambiguous negative
   or out-of-bounds offsets.
3. Preserve the existing NPZ keys and array layout (`image` as HWC and `label`
   as HW). Keep label remapping, but stop rewriting image-nodata pixels to
   background: class and ignore counts describe the stored remapped label,
   while nodata remains an independent all-retained-bands-zero statistic.
4. Stage each source's NPZ files under a temporary source directory. Move its
   complete NPZ set into the flat split directory, then publish the fragment as
   the completion marker. On `--resume`, validate every fragment row against
   its NPZ before skipping; sources without a fragment have orphan NPZs and
   incomplete staging state removed before retry.
5. Consolidate complete source fragments in source-ID/window order and replace
   the canonical CSV atomically. Refuse a nonempty target split without
   `--resume`, duplicate IDs, missing pairs, ambiguous manifest joins, and
   incompatible fragment schemas.
6. Use a 6x6-pixel, 8-band georeferenced fixture with 4x4 windows at 2-pixel
   stride. Its four overlapping windows have hand-checkable offsets, bounds,
   class/ignore/nodata counts, and a 6x6 probability reconstruction whose
   coverage ranges from one to four. Also exercise resume and a failed-source
   retry without duplicate rows.

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
- Do not select the remaining production output root, dtype, remap, or worker
  count.
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

## Outcome

The approved contract uses one top-left-anchored canonical family of
1024-pixel chips at 512-pixel stride. Training and final test evaluation retain
the overlapping chips. Future validation views select rows whose `row_off` and
`col_off` are both multiples of 1024. Final TIFF evaluation averages foreground
probabilities over every covered source pixel, thresholds once, and reports
coverage; no second evaluation-chip artifact is created.

`src/prepare/make_chip_dataset.py` now supports `--splits all`, required source
manifest joins for canonical runs, atomic canonical-manifest replacement,
per-source fragments under `manifest_parts/all`, explicit `--resume`, and
sequential or concurrent source processing through `--num_workers`. It refuses
nonempty targets without resume, mismatched image/label inventories or grids,
duplicate source/chip IDs, incomplete pairs, incompatible fragments, and NPZs
whose shapes, dtypes, class/ignore counts, or nodata statistics disagree with
their fragment. Failed sources leave JSON issues and no completion fragment.

Manifested runs use explicit full Rasterio windows because TorchGeo's existing
grid sampler is lower-left anchored and ceil-pads edge queries. Partial edge
windows remain excluded. Existing unmanifested train/validation/test calls
retain the prior TorchGeo path and NPZ keys/layout. Manifested labels no longer
rewrite image-nodata pixels to background: stored labels reflect the requested
remap, while nodata is counted independently from all retained image bands.

The final schema is the requested stable identity/geometry/statistics schema,
with one sorted `class_<value>_pixel_count` field per non-ignore remap output.
For the binary fixture and provisional real smoke remap, these are
`class_0_pixel_count` and `class_1_pixel_count`; labels are stored as `int64` so
the `-100` ignore index is preserved. `chip_path` is relative to the chip root,
and chip IDs encode source ID plus row, column, height, and width.

Changed repository files:

- `src/prepare/make_chip_dataset.py`: manifested Rasterio window path,
  statistics, transactional fragments, resume verification, and CLI.
- `tests/test_make_chip_dataset.py`: georeferenced overlap fixture,
  reconstruction proof, resume/corruption checks, and failed-source evidence.
- `pyproject.toml`: expose both the repository root and `scripts/` to pytest.
- `docs/architecture.md`: canonical 1024/512 grid and validation/test overlap
  policy.
- `AGENTS.md`, `README.md`, `docs/index.md`, `docs/todo.md`, `tasks/README.md`,
  Task 004, and this task: completed status and handoff routing.

Fixture evidence: a 6x6, 8-band georeferenced raster at 4-pixel size and
2-pixel stride produced the four deterministic windows `(0,0)`, `(0,2)`,
`(2,0)`, and `(2,2)`. Bounds, exact class/ignore/nodata counts, NPZ agreement,
one-to-four-pixel overlap coverage, unique-pixel probability reconstruction,
resume without duplicates, corrupt-completion refusal, and failed-source issue
writing all passed.

The bounded real-TIFF smoke used California source
`001_20200422_173136_2277` (1841x2749, EPSG:32611) with 1024/512 windows. It
produced eight chips at row offsets `0,512` and column offsets
`0,512,1024,1536`. All shapes, manifest counts, CRS, and bounds matched the NPZ
files and Task 002 portable affine metadata. A resume rerun performed zero
source work and retained eight rows. The temporary smoke artifacts were
removed; Task 003 created no durable external data artifacts.

Validation completed:

```text
uv run ruff format --check src tests       # passed
uv run ruff check src tests                # passed
uv run pytest tests/test_make_chip_dataset.py  # 3 passed
uv run pytest                              # 16 passed
git diff --check                           # passed
one-source California 1024/512 smoke       # 8 chips; passed
one-source resume rerun                     # 0 sources rerun; passed
```

The all-files pre-commit pass passed every hook except `end-of-file-fixer`,
which proposed only a pre-existing final newline in the unrelated historical
`planet8b_image_splits.csv`; that incidental modification was removed. Ruff and
all other pre-commit hooks passed.

The exact Task 004 command template is:

```bash
uv run python -m src.prepare.make_chip_dataset \
  /Volumes/x10pro/kelpseg/merged_all_regions_v1 <chip-root> \
  --splits all \
  --source-manifest /Volumes/x10pro/kelpseg/merged_all_regions_v1/raster_manifest.csv \
  --manifest-output <chip-root>/chip_manifest.csv \
  --size 1024 --stride 512 --num_bands 8 \
  --dtype <dtype> --remap <values> \
  --num_workers <workers> --resume
```

Task 004 still needs approval of the output root, `uint16` output dtype (the
Task 002 images reach 65,535 and cannot safely use `uint8`), exact binary
handling of raw label class `2`, and local worker count. Size `1024`, stride
`512`, and eight retained bands are fixed. The exact next action is to open
Task 004, approve those four remaining run parameters, perform its bounded
CA/BC/nodata preflight, and then start the resumable 369-source run.
