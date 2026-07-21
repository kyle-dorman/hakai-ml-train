# Documentation index

This page routes humans and agents to the smallest useful set of documents. It
does not own project decisions or implementation detail.

Start with `AGENTS.md`, then read `docs/todo.md` and the selected numbered task.
Do not read every task file or every source module before beginning narrow work.

## Current project

The active project is expanded-region PlanetScope 8-band binary kelp
segmentation. It will compare a temporally separated standard baseline with
leave-one-region-out models and evaluate them on matching source TIFFs.

Tasks 000–009A completed the temporal raster split, canonical raw merge,
manifested chipper, full unfiltered chip collection, manifest-driven nodata
filter, transactional application of the selected universal 50% threshold, and
the non-destructive training-only background selector, then packaged and
clean-extraction verified the source-aware v2 portable canonical archive after
repairing one California and all 30 BC label/source fragments. Task 010 then
downloaded, checksum-verified, and fully validated that archive remotely. Task
011 materialized the temporal baseline view; Task 012 is next to materialize
the LORO views.
`docs/todo.md` owns the current queue and status.

## Document roles

- Read `docs/product.md` when work may change the research question, split
  interpretation, claims, evaluation criteria, or project boundary. Skip it for
  narrow mechanical changes.
- Read `docs/architecture.md` when work changes pipeline stages, manifests,
  source/chip identity, split materialization, training, prediction, or metric
  aggregation.
- Read `docs/data_artifacts.md` when work creates, moves, deletes, filters,
  archives, transfers, or interprets data and generated artifacts.
- Read `docs/experiments.md` when work changes W&B, run names, training
  orchestration, checkpoints, prediction artifacts, or cross-run comparison.
- Read `docs/documentation.md` before editing, adding, moving, or deleting
  durable documentation.
- Read `docs/todo.md` for the active queue, current task, and next action.
- Read `docs/backlog.md` only for unselected future ideas. It is not an active
  queue or a decision record.
- Read `tasks/README.md` for task-file structure, then read only the selected
  numbered task.

## Active source and config surface

The current workflow primarily touches:

```text
scripts/create_temporal_baseline_split.py
scripts/merge_planet8b_regions.py
scripts/validate_planet8b_raw_merge.py
src/prepare/make_chip_dataset.py
src/prepare/remove_bg_only_tiles.py
src/prepare/remove_tiles_with_nodata_areas.py
src/data.py
src/models/smp.py
trainer.py
configs/kelp-ps8b/california/segformer_b3.yaml
```

Other config families and deployment modules remain in the repository but are
outside the active project unless a task explicitly brings them into scope.

## Current happy path

```text
all paired PS8B source TIFFs
  -> canonical raster manifest
  -> canonical chips and chip statistics
  -> universal nodata filtering
  -> temporal baseline and LORO views
  -> comparable training runs
  -> chip/TIFF confusion counts
  -> paired matching-TIFF analysis
```

## Validation

Use task-specific behavioral checks. The current common static checks are:

```bash
uv run ruff format --check .
uv run ruff check .
git diff --check
```

There is no general test suite yet. Add focused tests with new data-contract,
selection, or metric logic.
