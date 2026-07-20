# PlanetScope 8-band kelp segmentation

This repository currently supports a focused binary segmentation study on
8-band PlanetScope imagery: build an expanded California and British Columbia
dataset, train a temporally separated all-region baseline, train one
leave-one-region-out model per region, and compare predictions on matching
source GeoTIFFs.

Other historical dataset and deployment surfaces remain in the codebase but are
not part of the active project.

## Current status

The temporal source-raster split is complete:

- 369 paired source TIFFs.
- 12 region IDs: California `001` through `011`, plus BC.
- 247 train, 68 validation, and 54 test TIFFs.
- Acquisition dates stay intact and splits are chronological within each
  region.

The copied all-region raw merge is complete and raster-validated at
`/Volumes/x10pro/kelpseg/merged_all_regions_v1`. The canonical chip collection
at `/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1` was built with 6,003
chips from all 369 source TIFFs, then transactionally filtered at the approved
50% nodata threshold. Its active manifest now contains 4,637 chips from 367
source TIFFs across all 12 regions; the unfiltered manifest and complete
removal evidence are preserved under `filter_history/nodata_50`. The
non-destructive training selector retains all 3,210 positive chips and marks
1,427 non-positive chips as excluded from training only. The portable canonical
archive is complete and clean-extraction verified at
`/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v1.zip`.
Task 010 will transfer and verify it remotely. See `docs/todo.md` and
`tasks/README.md`.

## Documentation

- `AGENTS.md`: repository operating contract.
- `docs/index.md`: read/skip router for project documentation.
- `docs/todo.md`: current queue and next action.
- `docs/product.md`: scientific goal, success criteria, and non-goals.
- `docs/architecture.md`: active PS8B data, training, and evaluation workflow.
- `docs/data_artifacts.md`: local/remote artifact and manifest policy.
- `docs/experiments.md`: W&B and run-record contract.
- `tasks/`: one resumable contract per implementation step.

## Setup

The project requires Python 3.12 and uses `uv`:

```bash
uv python install 3.12
uv sync --python 3.12 --frozen
```

Run code through `uv`:

```bash
uv run python trainer.py --help
uv run ruff check .
```

For a disposable remote GPU instance, `scripts/bootstrap_skypilot.sh` installs
the locked environment, verifies CUDA, establishes the expected data-root
compatibility path, and handles W&B login. Dataset archive details will be
connected to the remote compatibility path in Task 010. The current local
transfer source is the Task 009 ZIP and adjacent `.zip.sha256` sidecar under
`/Volumes/x10pro/kelpseg/archives`; do not use the old tar archive as the new
experiment contract.

## Active workflow

```text
paired 8-band GeoTIFF imagery and labels
  -> copied raw images plus exact-grid derived labels and raster manifest
  -> overlapping NPZ chips plus per-chip statistics manifest
  -> universal nodata-percentage filter
  -> portable canonical chip archive
  -> temporal baseline and LORO hard-linked dataset views
  -> PyTorch Lightning segmentation training
  -> chip and source-TIFF prediction metrics
  -> paired matching-TIFF baseline/LORO comparison
```

The current reference model surface is the binary SegFormer B3 PS8B config
under `configs/kelp-ps8b/california/`. Dataset paths and run metadata in that
config will be revised by the numbered tasks before the new full training run.

## Current tracked dataset metadata

- `planet8b_temporal_image_splits.csv`: active baseline source-TIFF split.
- `scripts/create_temporal_baseline_split.py`: deterministic split generator.
- `planet8b_image_splits.csv`: historical split input; not the new baseline
  contract.
- `region_006_007_011_sample_points.geojson`: temporary naming evidence for the
  three regions omitted from the historical CSV.

Large data and generated artifacts live under `/Volumes/x10pro/kelpseg`, not in
git. See `docs/data_artifacts.md` before creating new outputs.

## Training entry point

Training uses the Lightning CLI wrapper in `trainer.py`:

```bash
uv run python trainer.py fit --config <ps8b-config.yaml>
uv run python trainer.py test --config <ps8b-config.yaml> \
  --ckpt_path <checkpoint.ckpt>
```

Do not launch the new baseline or LORO suite directly from the historical config
paths. Tasks 011–016 will materialize the datasets, establish W&B run context,
and provide the reproducible training runner.

## W&B

The active destination for new PS8B work is:

```text
entity: kdorman90-ucla
project: kelpseg
```

The new experiment group and run-name convention will be selected in Task 013.
W&B values in legacy configs are not the active tracking contract.
