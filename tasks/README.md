# Task contracts and history

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

Planning drafts may retain explicitly open user choices and remain unauthorized
for implementation until those choices and their contracts are finalized.
All tasks follow the simplicity direction in `AGENTS.md`: plain manifests,
ordinary functions, minimal bookkeeping, and no new hashing or receipt machinery.

Implementation task acceptance must include the relevant cross-task usability
checks in `docs/todo.md`. Outcomes record how routine use stays simple and which
obsolete code/options were removed. The deferred tiny walkthrough does not
postpone focused correctness tests or the Task 025 legacy reference capture.

Do not ask the user to decide later-task details early. When a task reaches a
blocking choice, present the recorded recommendation and evidence from prior
tasks, obtain the decision, write it into the task, and then continue.

## Current rebuild

[docs/todo.md](../docs/todo.md) owns the ordered rebuild roadmap. Only the next
selected slot needs a full contract; do not pre-decide details that depend on
the original-data audit. Breaking changes and removal of unrelated workflows
are authorized by Task 024.

| Task | Execution | Status | Outcome / next action |
|---|---|---|---|
| [024](024_scope_local_rebuild.md) | Local/docs | Complete | Scope, owned contracts, and small-task roadmap recorded |
| [025](025_capture_legacy_reference.md) | Local inference | Complete | Six verified legacy examples outside Git; capture and validation recorded |
| [026](026_inventory_originals_and_cleanup_provenance.md) | Local read-only audit | Complete | Inventory/traces and three-variant design recorded |
| [027](027_verify_box_and_back_up_raw_reference_audit.md) | Local/Box transfer | Complete | Three raw ZIPs, reference and audit verified on Box; restore checks passed |
| [028](028_package_guide_and_first_removal.md) | Local package/code/docs | Complete | Installed Typer/path package, guide, 139 tests and isolated distributions; next scope Task 029A |
| [029A](029a_organize_raw_sources.md) | Local implementation/fixtures | Complete | Generic organizer under prepare/, default progress logs; 369-pair plan, bounded smoke, 244 tests; next Task 029B |
| [029B](029b_clean_organized_sources.md) | Local implementation/fixtures | Complete | All installed preparation one-pass, redundant work/recovery removed; 344 tests; [current outcome](029b_clean_organized_sources.md#preparation-wide-simplification-outcome-2026-10-27); next Task 030A |
| [030A](030a_build_and_publish_organized.md) | Local production/Box | Complete | Immutable 369-pair local parent; all 1,163 Box checksums, 90.7 MB bounded restore and final evidence marker verified; 030B also complete |
| [030B](030b_build_and_publish_cleaned.md) | Local production/Box | Complete | 369 aligned pairs/12 regions; full QA, 747 Box checksums, 108.3 MB bounded restore and final marker verified; next existing Task 031 planning |
| [031](031_chipping_bands_and_tiny_walkthrough.md) | Local implementation/smoke | Complete | Installed 512/256/50 chipper, native 8/4/3 selection, partial-edge loading and nine-crop Box fetch/offline walkthrough; correctness/simplicity review passed; next Task 032 |
| [032A](032a_collection_and_split_implementation.md) | Local implementation/tiny smoke | Complete | Approved memberships/ten folds and tiny v2 pass; readability, errors and progress follow-up complete; next 032B |
| [032B](032b_produce_and_publish_chip_release.md) | Local production/Box | Ready | Next: full chips/splits, portable collection declaration, Box copy and bounded restore/load |

## Historical queue: Tasks 000–023

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
| [009A](009a_repair_metadata_nodata_and_repackage.md) | Local | Complete | 002–009 | Metadata-aware nodata repair and v2 archive |
| [010](010_transfer_and_verify_remote.md) | Remote | Complete | 009A | Verified remote dataset copy |
| [011](011_materialize_baseline_dataset.md) | Remote | Complete | 010 | Baseline train/val/test views |
| [012](012_materialize_loro_datasets.md) | Remote | Complete | 010, 011 | One dataset view per held-out region |
| [013](013_add_wandb_run_context.md) | Remote/code | Complete | 011, 012 | Consistent W&B context and artifacts |
| [014](014_build_training_runner.md) | Remote/code | Complete | 013, 014A, 014B | Verified 13-entry tiered EMA smoke suite |
| [014A](014a_move_to_new_machine.md) | Remote/data | Complete | 010–013 | Verified replacement host, data, and hard-linked views |
| [014B](014b_correct_generalization_model_config.md) | Remote/config | Complete | 013, 014A | Dedicated config, batch benchmark, and tiered EMA smoke |
| [015](015_run_new_baseline.md) | Remote | Complete | 014 | Verified expanded-data baseline checkpoint |
| [016](016_run_loro_training.md) | Remote/code | Complete | 015 | Closed partial v1 suite and prepared clean v2 identity |
| [017](017_run_v3_training_cycle.md) | Remote | Complete | 014–016 | Completed baseline plus 12 LORO v3 checkpoint suite |
| [018](018_build_prediction_evaluator.md) | Remote/code | Complete | 003, 017 | Chip- and TIFF-level prediction metrics |
| [019](019_run_prediction_suite.md) | Remote | Complete | 017, 018 | Predictions for every v3 run |
| [020](020_compare_matching_tiffs.md) | Remote/analysis | Complete | 019 | Paired cross-run accuracy comparison |
| [021](021_restructure_project_docs.md) | Local/docs | Complete | — | PS8B-focused documentation structure |
| [022](022_evaluate_all_retained_test_chips.md) | Remote/code | Complete | 018–020 | All-retained-chip overlap-stitched evaluation |
| [023](023_fix_center_padded_prediction_alignment.md) | Remote/code | Complete | 022 | Corrected center-padded prediction suite and report |

## Historical user decision checkpoints

These checkpoints belong to the completed PS8B study. They are historical
evidence, not new approval gates for the rebuild. Consult each original task
for its actual decision and outcome.

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
| 009A | None; metadata-aware counting, in-place manifest repair, and prior chip-hash reuse are approved. |
| 010 | Remote SSH alias/user, staging path, extracted root, compatibility path, and repo branch/commit. |
| 011 | Baseline view root; split policy is already fixed by Task 000. |
| 012 | Non-held-out LORO train/validation policy, separate `ca_005`/`ca_006` folds, and view root. |
| 013 | W&B group, run names, checkpoint upload policy, and smoke-run grouping. |
| 014 | Base model config, seed policy, training budget, execution mode, and failure policy. |
| 014A | Replacement host, repo commit, storage roots, and disposition of recoverable old-host evidence. |
| 014B | None; ImageNet initialization, constant-effective-batch benchmark, and baseline/BC deep-smoke plus shallow remaining folds are approved. |
| 015 | Confirm resolved full baseline only if it differs from the approved Task 014 matrix. |
| 016 | Complete; user chose a clean v2 restart after closing partial v1. |
| 017 | None; 70-epoch v3 identity, `3e-5` LR floor, policy, order, and user execution are approved. |
| 018 | Overlap combination confirmation, binary threshold, prediction-raster retention, and raster dtype/compression. |
| 019 | None unless approved prediction outputs exceed remote storage. |
| 020 | Complete; user approved kelp IoU, descriptive paired bootstrap summaries, all proposed plots, and an external report. |
| 021 | None; completed documentation maintenance. |
| 022 | Complete decision; use every valid post-nodata test chip and overlap-average source probabilities. |
| 023 | Complete decision; correct center-padded prediction alignment and republish the evaluation. |

## Task sizing

Keep each task narrow enough to complete and verify in one window. If new work
materially expands scope, write a new task rather than silently widening the
active one. Analysis-only threshold or policy tasks should stop for user review
when their acceptance criteria require a decision.
