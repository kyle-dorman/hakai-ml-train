# Task contracts and history

This folder contains one bounded work contract per task. Read
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
obsolete code/options were removed. The tiny walkthrough complements focused correctness tests; it does not
replace them.

Do not ask the user to decide later-task details early. When a task reaches a
blocking choice, present the recorded recommendation and evidence from prior
tasks, obtain the decision, write it into the task, and then continue.

## Current rebuild

[docs/todo.md](../docs/todo.md) owns the ordered rebuild roadmap. Only the next
selected slot needs a full contract; defer later-task implementation decisions
until that task is selected. Breaking changes and removal of unrelated workflows
are authorized by Task 024.

| Task | Execution | Status |
| --- | --- | --- |
| [024](024_scope_local_rebuild.md) | Local/docs | Complete |
| [025](025_capture_legacy_reference.md) | Local inference | Complete |
| [026](026_inventory_originals_and_cleanup_provenance.md) | Local read-only audit | Complete |
| [027](027_verify_box_and_back_up_raw_reference_audit.md) | Local/Box transfer | Complete |
| [028](028_package_guide_and_first_removal.md) | Local package/code/docs | Complete |
| [029A](029a_organize_raw_sources.md) | Local implementation/fixtures | Complete |
| [029B](029b_clean_organized_sources.md) | Local implementation/fixtures | Complete |
| [030A](030a_build_and_publish_organized.md) | Local production/Box | Complete |
| [030B](030b_build_and_publish_cleaned.md) | Local production/Box | Complete |
| [031](031_chipping_bands_and_tiny_walkthrough.md) | Local implementation/smoke | Complete |
| [032A](032a_collection_and_split_implementation.md) | Local implementation/tiny smoke | Complete |
| [032A.1](032a_1_nonoverlapping_chip_evaluation.md) | Local selection/tiny smoke | Complete |
| [032B](032b_produce_and_publish_chip_release.md) | Local production/Box | Complete |
| [032C](032c_archive_legacy_and_evict_local_data.md) | Local archive/code/data cleanup | Complete |
| [033](033_baseline_training_and_portable_models.md) | Shared planning | Split into 033A–033G |
| [033A](033a_individual_augmentation_previews.md) | Local preview implementation | Complete |
| [033B](033b_review_augmentation_settings.md) | User review/combined preview | Complete |
| [033C](033c_simplify_pixel_statistics.md) | Local NumPy utility | Complete |
| [033D](033d_model_and_training_inputs.md) | Local model/input checks | Complete |
| [033E](033e_training_validation_and_ema.md) | Local training/validation | Complete |
| [033F](033f_portable_models_and_resume.md) | Local bundle/recovery | Complete |
| [033G](033g_tiny_walkthrough_and_handoff.md) | Installed rehearsal/docs | Complete |
| [034](034_gpu_machine_preparation_and_baseline_launch.md) | Remote-first setup/validation/launch | Complete |
| [035](035_image_only_tiled_inference.md) | Local implementation/smoke | Complete |
| [036](036_shared_scoring_and_reports.md) | Local implementation/smoke | Complete |
| [036B](036b_temporal_error_analysis.md) | Local analysis implementation/smoke | Complete |
| [037A](037a_without_bc_launch.md) | Production comparison | Complete |
| [037B](037b_spectral_comparison_launch.md) | Production comparison | Complete |
| [037](037_baseline_comparisons_and_loro.md) | Comparison and cleanup | 037A–D closed |
| [037E](037e_documentation_cleanup.md) | Documentation only | Complete; reviewed |
| [038](038_methods_documentation.md) | Documentation only | Complete |
| [040](040_shore_distance_diagnostics.md) | Preparation/reporting | Complete |
| [041](041_distance_weighted_bce_experiment.md) | Training experiment | Complete |

038 is complete. Pending execution order
is **039 → 042**. Task 039 (new-region
recipes, formerly 038) and Task 042 (final handoff, formerly 039) remain roadmap
slots in [docs/todo.md](../docs/todo.md), to be contracted when selected.
Completed Tasks 040/041 retain their numbers. Historical task records retain
old numbering as evidence. Task 034 owns initial GPU setup; 042 reuses it.

Historical decision checkpoints are retained in [their own reference](historical_decisions.md).

## Historical queue: Tasks 000–023

| Task | Execution | Status |
| --- | --- | --- |
| [000](000_temporal_baseline_split.md) | Local | Complete |
| [001](001_build_raw_merge_organizer.md) | Local | Complete |
| [002](002_create_and_validate_raw_merge.md) | Local | Complete |
| [003](003_extend_chipper_and_write_manifest.md) | Local | Complete |
| [004](004_chip_all_regions_locally.md) | Local | Complete |
| [005](005_build_manifest_nodata_filter.md) | Local | Complete |
| [006](006_choose_nodata_threshold.md) | Local | Complete |
| [007](007_apply_nodata_filter.md) | Local | Complete |
| [008](008_build_background_filter.md) | Local | Complete |
| [009](009_package_dataset_archive.md) | Local | Complete |
| [009A](009a_repair_metadata_nodata_and_repackage.md) | Local | Complete |
| [010](010_transfer_and_verify_remote.md) | Remote | Complete |
| [011](011_materialize_baseline_dataset.md) | Remote | Complete |
| [012](012_materialize_loro_datasets.md) | Remote | Complete |
| [013](013_add_wandb_run_context.md) | Remote/code | Complete |
| [014](014_build_training_runner.md) | Remote/code | Complete |
| [014A](014a_move_to_new_machine.md) | Remote/data | Complete |
| [014B](014b_correct_generalization_model_config.md) | Remote/config | Complete |
| [015](015_run_new_baseline.md) | Remote | Complete |
| [016](016_run_loro_training.md) | Remote/code | Complete |
| [017](017_run_v3_training_cycle.md) | Remote | Complete |
| [018](018_build_prediction_evaluator.md) | Remote/code | Complete |
| [019](019_run_prediction_suite.md) | Remote | Complete |
| [020](020_compare_matching_tiffs.md) | Remote/analysis | Complete |
| [021](021_restructure_project_docs.md) | Local/docs | Complete |
| [022](022_evaluate_all_retained_test_chips.md) | Remote/code | Complete |
| [023](023_fix_center_padded_prediction_alignment.md) | Remote/code | Complete |

## Task sizing

Keep each task narrow enough to complete and verify in one window. If new work
materially expands scope, write a new task rather than silently widening the
active one. Analysis-only threshold or policy tasks should stop for user review
when their acceptance criteria require a decision.
