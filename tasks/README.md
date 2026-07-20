# PlanetScope 8-band regional generalization task queue

This folder contains one resumable implementation contract per task. Read
`AGENTS.md`, `docs/index.md`, and `docs/todo.md` first; those files own the
project contract, documentation routing, and active queue.

Use one task per Codex window. At the start of a window, read this file and the
named task file. At completion, update the task's status and this table, record
the important outputs, and stop before starting the next task.

## Task contract

Use one numbered task per Codex window. Before editing, change its status to
`In progress` and align `docs/todo.md`. When it closes, add an outcome-focused
summary with changed files, external artifacts, validation, unresolved issues,
and exact next action. Then mark the next task in `docs/todo.md` and stop.

Project decisions live in `docs/product.md`, `docs/architecture.md`,
`docs/data_artifacts.md`, and `docs/experiments.md`; do not duplicate them in
this queue.

Each pending task must contain:

- an abstract explaining why the task exists and where it stops;
- explicit inputs and expected outputs;
- a concrete implementation contract, including planned filenames and CLI;
- a `User decisions required` section that distinguishes blocking choices from
  defaults the agent may safely use;
- a plan/spec requirement for ambiguous or multi-file work;
- exact smoke and validation checks;
- observable acceptance criteria and non-goals;
- an outcome template for the closing agent.

Do not ask the user to decide later-task details early. When a task reaches a
blocking choice, present the recorded recommendation and evidence from prior
tasks, obtain the decision, write it into the task, and then continue.

## Queue

| Task | Execution | Status | Depends on | Outcome |
|---|---|---|---|---|
| [000](000_temporal_baseline_split.md) | Local | Complete | — | Reproducible temporal raster split |
| [001](001_build_raw_merge_organizer.md) | Local | Complete | 000 | Organizer and raw-manifest writer |
| [002](002_create_and_validate_raw_merge.md) | Local | Complete | 001 | Complete merged raw dataset |
| [003](003_extend_chipper_and_write_manifest.md) | Local | Complete | 002 | Restartable chipper emits per-chip statistics |
| [004](004_chip_all_regions_locally.md) | Local | Complete | 003 | Canonical unfiltered chip collection |
| [005](005_build_manifest_nodata_filter.md) | Local | Complete | 004 | Configurable manifest-driven nodata tool |
| [006](006_choose_nodata_threshold.md) | Local | Complete | 005 | Approved universal 50% threshold |
| [007](007_apply_nodata_filter.md) | Local | Complete | 006 | Cleaned canonical chip collection |
| [008](008_build_background_filter.md) | Local | Complete | 004, 007 | Non-destructive training-only selector |
| [009](009_package_dataset_archive.md) | Local | Complete | 007, 008 | Portable verified archive |
| [010](010_transfer_and_verify_remote.md) | Remote | Pending | 009 | Verified remote dataset copy |
| [011](011_materialize_baseline_dataset.md) | Remote | Pending | 010 | Baseline train/val/test views |
| [012](012_materialize_loro_datasets.md) | Remote | Pending | 010 | One dataset view per held-out region |
| [013](013_add_wandb_run_context.md) | Remote/code | Pending | 011, 012 | Consistent W&B context and artifacts |
| [014](014_build_training_runner.md) | Remote/code | Pending | 013 | Resumable registry and training runner |
| [015](015_run_new_baseline.md) | Remote | Pending | 014 | Expanded-data baseline checkpoint |
| [016](016_run_loro_training.md) | Remote | Pending | 015 | Complete LORO checkpoint suite |
| [017](017_build_prediction_evaluator.md) | Remote/code | Pending | 015 | Chip- and TIFF-level prediction metrics |
| [018](018_run_prediction_suite.md) | Remote | Pending | 016, 017 | Predictions for every relevant run |
| [019](019_compare_matching_tiffs.md) | Remote/analysis | Pending | 018 | Paired cross-run accuracy comparison |
| [020](020_restructure_project_docs.md) | Local/docs | Complete | — | PS8B-focused documentation structure |

## User decision checkpoints

The task files contain the evidence and recommendation to show when each
decision is reached. This table is a routing summary, not a substitute for the
task contract.

| Task | Decision needed from user |
|---|---|
| 001 | None; implement the generic organizer contract. |
| 002 | Canonical raw-merge root and hard-link versus copy mode. |
| 003 | Approve overlap-aware TIFF reconstruction versus separate non-overlap evaluation chips. |
| 004 | Chip root, size, stride, eight-band confirmation, dtype, label remap, and worker count. |
| 005 | None; implement a required explicit threshold with no hidden default. |
| 006 | Select the universal nodata percentage after reviewing distributions and examples. |
| 007 | None if Task 006 records an approved numeric threshold. |
| 008 | Exclude all background-only training chips or retain a deterministic fraction. |
| 009 | Archive directory/name and whether compact QA evidence is included. |
| 010 | Remote SSH alias/user, staging path, extracted root, compatibility path, and repo branch/commit. |
| 011 | Baseline view root; split policy is already fixed by Task 000. |
| 012 | Non-held-out LORO train/validation policy, separate `ca_005`/`ca_006` folds, and view root. |
| 013 | W&B group, run names, checkpoint upload policy, and smoke-run grouping. |
| 014 | Base model config, seed policy, training budget, execution mode, and failure policy. |
| 015 | Confirm resolved full baseline only if it differs from the approved Task 014 matrix. |
| 016 | First full LORO fold, pause-versus-continue point, and run order. |
| 017 | Overlap combination confirmation, binary threshold, prediction-raster retention, and raster dtype/compression. |
| 018 | None unless approved prediction outputs exceed remote storage. |
| 019 | Primary metric, paired statistical summary, plot set, and report destination. |

## Task sizing

Keep each task narrow enough to complete and verify in one window. If new work
materially expands scope, write a new task rather than silently widening the
active one. Analysis-only threshold or policy tasks should stop for user review
when their acceptance criteria require a decision.
