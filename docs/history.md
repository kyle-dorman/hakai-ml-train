# History and recovery

This page routes completed work and historical evidence. For instructions to use
the maintained toolkit, start with the [quickstart](quickstart.md).

## Studies and milestones

| Work | Evidence owner |
|---|---|
| Original PS8B baseline/LORO study, Tasks 000–023 | [Historical task index](../tasks/README.md#historical-queue-tasks-000023) |
| Legacy checkpoint reference and six-example capture | [Task 025](../tasks/025_capture_legacy_reference.md) |
| Original collection audit and cleanup traces | [Historical provenance](cleanup_provenance.md), [Task 026](../tasks/026_inventory_originals_and_cleanup_provenance.md) |
| Raw/reference/audit backup verification | [Task 027](../tasks/027_verify_box_and_back_up_raw_reference_audit.md) |
| Organized and cleaned publication | [Task 030A](../tasks/030a_build_and_publish_organized.md), [Task 030B](../tasks/030b_build_and_publish_cleaned.md) |
| Chip/split/tiny-v2 publication | [Task 032B](../tasks/032b_produce_and_publish_chip_release.md) |
| Local eviction and retained small historical controls | [Task 032C](../tasks/032c_archive_legacy_and_evict_local_data.md) |
| Tiny training and portable model rehearsal | [Task 033G](../tasks/033g_tiny_walkthrough_and_handoff.md) |
| GPU setup, loss/LR/model-size comparisons and checkpoint checks | [Task 034](../tasks/034_gpu_machine_preparation_and_baseline_launch.md) |
| Prediction, shared reports and temporal analysis | [Task 035](../tasks/035_image_only_tiled_inference.md), [036](../tasks/036_shared_scoring_and_reports.md), [036B](../tasks/036b_temporal_error_analysis.md) |
| Shore-distance diagnostics and weighting screen | [Task 040](../tasks/040_shore_distance_diagnostics.md), [041](../tasks/041_distance_weighted_bce_experiment.md) |
| With/without-BC and spectral comparisons | [Task 037A](../tasks/037a_without_bc_launch.md), [037B](../tasks/037b_spectral_comparison_launch.md) |
| Ten-fold LORO results, normalization provenance, claim qualifications and saved illustrated summary | [Task 037C outcome](../tasks/037_baseline_comparisons_and_loro.md#037c-production-results-and-researcher-summary--2026-11-12) |
| Legacy retirement and replacement validation | [Task 037D outcome](../tasks/037_baseline_comparisons_and_loro.md#037d-cleanup-outcome--2026-11-12) |

Detailed launch commands formerly in current guides are retained as
[historical experiment recipes](reference/historical_recipes.md) and
[historical GPU recipes](reference/historical_gpu_recipes.md). They record prior
runs; use the maintained guides for new work. Historical task-specific approval
decisions remain in [their reference](../tasks/historical_decisions.md).

## Recovery

- Current published data and trusted release-specific verification commands:
  [CA/BC release reference](reference/ca_bc_release.md).
- Routine transfer and backup: [Box operations](box_backup.md).
- Original implementation: starting commit
  `ac933fd667c2ddb445b8a622d8404387a2d056e2`; see
  [037D dependency and recovery notes](../tasks/037_baseline_comparisons_and_loro.md#dependencies-and-historical-recovery).
- One-off LORO implementation: preservation commit
  `609aa22fe27f2c0f41098b7055321da3ceb62f94`; exact inspection/export commands
  remain in [037C retirement](../tasks/037_baseline_comparisons_and_loro.md#037c-implementation-retirement--2026-11-12).
  Portable LORO bundles work with current prediction commands.
- Legacy cleanup implementation: `4152cc8`; documentation task setup: `4799dad`.

Historical host paths identify evidence locations at the recorded time, not a
promise that a host or local copy still exists. Do not overwrite current outputs
or restore retired code into the maintained package to inspect old work.
