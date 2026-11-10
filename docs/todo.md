# Project TODO

## Current phase

Local rebuild of the Planet binary kelp toolkit. Task 024 recorded the scope,
working decisions, and small-task sequence. Task 025 preserved a verified legacy
checkpoint reference outside Git. Task 026 completed the scoped original-data
inventory and six cleanup-provenance traces. Task 028 established the installed
Typer package/path checks, researcher guide, automated CPU checks, and first
unrelated-code removal. Task 029A implemented byte-preserving organization,
reconciled the 369-pair metadata plan and verified a separate two-pair smoke.
Task 029B added quick/full directory checking and shared cleanup, verified with
ordinary-directory fixtures, installed distributions and the two-pair real smoke.
Preparation code is grouped in `kelpseg.prepare` with clearly commented small
functions and default phase/file/count progress logs.
Later workflows retain legacy code until their replacements; originals remain immutable.

Task 030B is [complete](../tasks/030b_build_and_publish_cleaned.md#outcome-2026-10-27):
all 369 cleaned pairs passed full QA, exact Box checksums, bounded restoration
and final evidence-marker authentication. Task 030A's independent
[organized publication](../tasks/030a_build_and_publish_organized.md#outcome-2026-10-27)
is also complete; its immutable parent remains unchanged.

[Task 031 is complete](../tasks/031_chipping_bands_and_tiny_walkthrough.md#outcome-2026-10-27):
installed chipping, 8/4/3-band loading and the nine-crop real walkthrough passed.
The follow-up correctness/simplicity review also passed; details remain in its
[review outcome](../tasks/031_chipping_bands_and_tiny_walkthrough.md#follow-up-review-outcome-2026-10-27).
[Task 032A is complete](../tasks/032a_collection_and_split_implementation.md#outcome-2026-10-28):
installed source assignments/window selection reproduce all 369 approved
memberships and ten folds; the 13-crop local tiny-v2 walkthrough passes.
Its [usability follow-up](../tasks/032a_collection_and_split_implementation.md#researcher-usability-follow-up-outcome-2026-10-28)
adds clearer comments/errors, progress logs and fresh-name example recipes.
[Task 032A.1 is complete](../tasks/032a_1_nonoverlapping_chip_evaluation.md#outcome-2026-10-28):
training keeps overlap; chip validation/test use disjoint existing windows with
reported geometric coverage gaps. Source assignments are unchanged; with BC is
the primary baseline.
[Task 032B is complete](../tasks/032b_produce_and_publish_chip_release.md#outcome-2026-10-28):
26,573 canonical chips, both variants and ten folds are published on Box with
portable controls. Exact path/size comparisons, the bounded restore and fetched
tiny-v2 offline walkthrough pass. Task 033 is now split into seven bounded
contracts. [Task 033A](../tasks/033a_individual_augmentation_previews.md) and
[033B](../tasks/033b_review_augmentation_settings.md) are complete: the user
approved the stock D4 + SomeOf(2) pipeline, the final native recipe is saved,
and the readability review and focused checks pass.
[033C is complete](../tasks/033c_simplify_pixel_statistics.md#outcome-2026-11-02):
the installed NumPy pixel-statistics command reproduces all eight approved
normalization bands to floating-point precision. Augmentation preview/debug
code is grouped under `kelpseg/augmentation_debug/`.
[033D is complete](../tasks/033d_model_and_training_inputs.md#outcome--2026-11-02):
manifest-selected inputs, shared preprocessing, one B3 model and loss/confusion
helpers pass bounded 8/4/3 CPU updates. Inputs use a full Albumentations tensor
pipeline and metrics use TorchMetrics. The added light affine step has
[updated previews](quickstart.md#preview-the-combined-augmentation-pipeline)
approved by the user. [033E is complete](../tasks/033e_training_validation_and_ema.md#outcome--2026-11-02):
Lightning training/validation, explicit spectral recipes, delayed EMA and distinct
best/last checkpoints pass bounded CPU checks. [033F is complete](../tasks/033f_portable_models_and_resume.md#outcome--2026-11-03):
copied bundles and zero-worker completed-epoch resume pass offline CPU checks.
[033G is complete](../tasks/033g_tiny_walkthrough_and_handoff.md#outcome-2026-11-03):
installed tiny CPU checks cover all eight recipe/variant cases, copied models and
completed-epoch resume; eight production metadata previews pass.
**[Task 034: GPU machine preparation and baseline launch](../tasks/034_gpu_machine_preparation_and_baseline_launch.md)
is complete — 2026-11-06.** RTX 3090 setup, throughput tuning, production
baselines, loss/LR/model-size comparisons and post-training diagnostics are
complete. B0/B1 were the baseline models at handoff. B0 with B's parameters and
EMA was the starting recipe for Task 041. Epoch 4–12 retention and current
checkpoint loading/resume are validated. Small-bed recovery and the sampled
train/validation gap remain research questions, not setup blockers.
See Task 034 for results, validation and artifact locations. Operational handoff:
back up the separate LR/model-size runs and recent analyses to Box; backup of
these new roots is not yet verified. Continue representation diagnostics in the
separate chat; no further experiment is scheduled under Task 034.
Task 027 verified the Box backup; see its
[outcome](../tasks/027_verify_box_and_back_up_raw_reference_audit.md#outcome-2026-10-27).
Task 026's artifacts, validation, and unresolved evidence limits are recorded in
[its outcome](../tasks/026_inventory_originals_and_cleanup_provenance.md#outcome-2026-10-26)
and [cleanup_provenance.md](cleanup_provenance.md).

[Task 028](../tasks/028_package_guide_and_first_removal.md#outcome-2026-10-27)
was completed independently while Task 027 was transferring.

[Task 029B](../tasks/029b_clean_organized_sources.md#preparation-wide-simplification-outcome-2026-10-27) is complete.
Quick/full checks and shared cleanup support optional labels and ordinary
directories, with optional verified organizer provenance. All preparation runs once into
fresh outputs; interrupted work is not resumed. No BC stage exists.

The agreed dataset variants are **1 raw**, **2 organized intermediate**, and
**3 cleaned intermediate**. Both intermediates are unsplit; generated
train/validation/test assignments are implemented separately in Task 032A.
The full chip/split release is published; the approved mixed temporal split
stays unchanged. The full variant and
provenance contract lives in [data_artifacts.md](data_artifacts.md#planned-raw-intermediate-and-cleaned-releases).

Local cleanup follow-up [Task 032C is complete](../tasks/032c_archive_legacy_and_evict_local_data.md#outcome-2026-10-28):
small historical records are archived, the catalog bootstrap is retired and
about 410 GB of obsolete local data/raw/organized copies were removed. Current
cleaned/chips/analyses/references stay local; Box was untouched. Task 033 stays
separate.

## Selected local task

[Task 035](../tasks/035_image_only_tiled_inference.md#outcome--2026-11-04) is complete:
installed image-only tiled prediction and local spatial/copied-model checks pass.
[Task 036](../tasks/036_shared_scoring_and_reports.md#outcome--2026-11-05) is complete:
separate `predict-chips` and shared `report` commands preserve the existing chip
diagnostics and score saved TIFF predictions with unique-pixel coverage.
Installed local checks, reference parity and the maintainability review pass.
[Task 036B](../tasks/036b_temporal_error_analysis.md#outcome--2026-11-05) is complete:
`temporal-report` compares short/long interval percentage changes against labels
on common valid footprints. Installed checks and bounded report smokes pass.
[Task 040](../tasks/040_shore_distance_diagnostics.md#outcome--2026-11-06) is complete:
369 source land/distance grids, region/split label inventories and chip/TIFF
validation distance reports are implemented and verified. Nearshore representation
and recall gaps vary by region; detailed findings remain in the task record.
The label-cluster/distance and log-imagery display follow-up is complete.
Expected exposure under the existing training-window sampler is complete.
The 5,000-pixel cluster boundary and distance-band line plot follow-up is also
complete, with all prior counts reconciled.
The joint B0 recall follow-up is complete: region/distance/full-source-size
counts reconcile, with acquisition-support and truncation comparisons. The
deficit persists most consistently in 008 and selectively in other regions.
Task 040 final code quality review is complete: 114 regression tests pass and
a fresh 53-TIFF B0 check reproduces all 25 data CSVs exactly. Task 040 is closed
and the user has authorized its commit.
All Task 040 report pages now use concise plots/tables without written analysis;
detailed diagnostics remain collapsed or downloadable.
[Task 041](../tasks/041_distance_weighted_bce_experiment.md) is complete.
The [alpha 0 run](experiments.md#current-planet-8-band-b0-baseline) is the current
Planet 8-band B0 baseline for California and British Columbia. Review researcher
feedback on suspected nearshore label omissions before revisiting weighting.
Task 037 remains the next general roadmap contract.
The completed full 53-TIFF validation predictions have now been analyzed with
Task 036B: 62 spatially supported pairs, 61 with defined percentage errors.
See its task record for results and coverage limits. Task 034 remote setup and experiment handoff is complete.

## Ordered roadmap

Tasks through 032C are complete. Remaining later rows are ordered scope slots, not permission
to execute multiple tasks in one window. Create and refine each contract when
selected; split further if needed.

| Task | Deliverable | Local completion gate |
|---|---|---|
| [024](../tasks/024_scope_local_rebuild.md) | Scope and rebuild plan — complete | Owned docs agree; usability requirements and example sequencing recorded |
| [025](../tasks/025_capture_legacy_reference.md) | Legacy checkpoint gut check — complete | Six original pairs, probabilities, masks, visually checked panels, and verified provenance outside Git |
| [026](../tasks/026_inventory_originals_and_cleanup_provenance.md) | Inventory originals and reconstruct cleanup provenance — complete | Read-only inventory, six CA/BC traces, previous decisions and evidence limits recorded |
| [027](../tasks/027_verify_box_and_back_up_raw_reference_audit.md) | Organize Box project and back up raw variant 1, reference, and audit — complete | Box native checksums, small round trip, and package restores verified |
| [028](../tasks/028_package_guide_and_first_removal.md) | Installable uv package, researcher guide, and first removal pass — complete | Installed Typer/path checks; wheel/sdist isolation; 139 CPU tests; guide and bounded removal |
| [029A](../tasks/029a_organize_raw_sources.md) | Implement raw variant 1 → organized intermediate 2 — complete | One organizer for independent datasets; complete 369-pair metadata plan; bounded byte-preserving smoke, companion/alias and restart checks |
| [029B](../tasks/029b_clean_organized_sources.md) | Two-tier check and shared cleanup → variant 3 — complete | Direct directories, optional labels/catalogs; reused logic/tests; image nodata 0, label ignore 3; optional QA masks |
| [030A](../tasks/030a_build_and_publish_organized.md) | Build and publish organized intermediate 2 — complete | 369 pairs/418 companions; all 1,163 Box checksums, bounded restore and final evidence marker verified |
| [030B](../tasks/030b_build_and_publish_cleaned.md) | Build and publish cleaned intermediate 3 — complete | All 369 pairs/12 regions; full cleaned QA, 747 Box checksums, bounded restore and final evidence marker verified |
| [031](../tasks/031_chipping_bands_and_tiny_walkthrough.md) | Simplify chipping/band selection and start the tiny walkthrough — complete | Configurable 512/256/50, native bands, partial-edge loading; nine-crop Box fetch/offline smoke and focused checks pass |
| [032A](../tasks/032a_collection_and_split_implementation.md) | Implement source assignments/window selection and grow tiny v2 — complete | Locked 216/53/58; spacecraft/day isolation; both training variants; ten folds; 13-crop example; no full production |
| [032A.1](../tasks/032a_1_nonoverlapping_chip_evaluation.md) | Non-overlapping chip validation/test — complete | Reuse existing chips; preserve source assignments; report geometric coverage |
| [032B](../tasks/032b_produce_and_publish_chip_release.md) | Produce full chips/assignments and publish to Box — complete | 26,573 canonical payloads; both variants/ten folds; Box path/size comparisons, bounded restore and fetched tiny-v2 offline checks |
| [032C](../tasks/032c_archive_legacy_and_evict_local_data.md) | Archive historical controls, retire bootstrap and evict obsolete local copies — complete | Prewritten plan; 34 MB historical archive; about 410 GB reclaimed; current data/evidence retained and Box untouched |
| [033](../tasks/033_baseline_training_and_portable_models.md) | Shared baseline decisions and split plan | Exact 5000-capped normalization and family routing; no umbrella implementation |
| [033A](../tasks/033a_individual_augmentation_previews.md) | Individual augmentation previews — complete | Stock native sweeps through defaults; separate coarse size/count modes; no stacking or training |
| [033B](../tasks/033b_review_augmentation_settings.md) | Review and select augmentation settings — complete | Combined outputs approved; final native recipe, readable viewers and package checks pass |
| [033C](../tasks/033c_simplify_pixel_statistics.md) | Simplify pixel statistics — complete | Installed NumPy command; exact chip/pixel scope; approved constants reproduced within 1.5e-11 raw units |
| [033D](../tasks/033d_model_and_training_inputs.md) | Model and training inputs — complete | Shared preprocessing, kelp-only tensors, real B3 update and loss/confusion checks |
| [033E](../tasks/033e_training_validation_and_ema.md) | Training, validation and EMA — complete | Flat recipes, equal epochs, validation-only selection, local records and saved states |
| [033F](../tasks/033f_portable_models_and_resume.md) | Portable models and resume — complete | Copied bundle and completed-epoch resume verified independently (zero workers) |
| [033G](../tasks/033g_tiny_walkthrough_and_handoff.md) | Tiny walkthrough and handoff — complete | Eight tiny CPU cases, installed distributions, copied bundle/resume pair and eight metadata-only previews; next 034 |
| [034](../tasks/034_gpu_machine_preparation_and_baseline_launch.md) | GPU machine preparation and baseline launch — complete | RTX 3090 validation, throughput tuning, completed comparisons, B0/B1 handoff and current checkpoint checks; artifact backup follow-up recorded |
| [035](../tasks/035_image_only_tiled_inference.md) | Image-only tiled inference — complete | Copied bundle and cleaned TIFFs; shifted edge windows, explicit sparse-window coverage, georeferenced probabilities/masks; no label dependency |
| [036](../tasks/036_shared_scoring_and_reports.md) | Separate inference and shared labeled reports — complete | Saved chip/TIFF predictions; one report command; existing diagnostic parity, unique-pixel scoring and explicit coverage |
| [036B](../tasks/036b_temporal_error_analysis.md) | Temporal error and change analysis — complete | Region/date/year/month support, signed bias and explicit supported common-footprint pairs; reuse 036 outputs |
| [040](../tasks/040_shore_distance_diagnostics.md) | Shore-distance coverage and pixel-level evaluation — complete | Aligned land/distance rasters; region/split label support; distance-binned validation metrics with unique-pixel and coverage reconciliation |
| [041](../tasks/041_distance_weighted_bce_experiment.md) | Distance-weighted BCE recall experiment — complete | Alpha 0 selected as baseline pending nearshore label feedback |
| 037 | LORO runner and matching-TIFF comparisons | Ten 001–010 folds; paired with/without-011/012 CA/Baja results; temporal-consistency and later-date scopes reported separately; tiny suite checks |
| 038 | New-region experiment recipes | Use prepared regional and combined collection versions; four cases, fixed test scopes, explicit initialization and reset/resume behavior |
| 039 | Final researcher handoff and complete-workflow rehearsal | Another researcher follows the finished preparation/train/predict/score/transfer recipes; reuse 034 setup; finish no-scripts cleanup; no repeated GPU bootstrap or first-launch gate |

## Usability acceptance across tasks

- All tasks use plain manifests, ordinary functions, and minimal bookkeeping.
  Do not add new hashing, checksum, authentication-catalog, or receipt machinery.
  This user instruction supersedes heavier requirements in older contracts;
  existing historical evidence remains recorded.
- Start a short quickstart/researcher guide in Task 028 and extend it whenever
  an implemented workflow arrives. Include copyable recipes for training,
  prediction, evaluation, and adding a region. Development task records remain
  separate from everyday operating instructions.
- Begin the reusable tiny walkthrough in Task 031, after Task 027's verified
  Box setup and Task 030B's cleaned intermediate. Grow the same example through
  splitting, training smoke, prediction, and evaluation as those stages arrive.
  Task 039 rehearses the finished example. Task 025's legacy capture and focused
  correctness fixtures are separate and retain their existing sequence.
- Keep small synthetic fixtures and automated CPU checks independent of Box,
  W&B login, GPUs, and large downloads. Establish automation with Task 028 and
  extend it with each implementation; the real walkthrough uses a small external
  dataset subset fetched once and runnable locally afterward.
- Use ordinary recipe values, one place for machine-specific paths, and a
  consistent run-folder layout for settings, checkpoints, metrics, and figures.
  Switching datasets/machines or routine bands/LR/checkpoint settings requires
  no Python edits. Avoid class-path configs and inheritance chains.
- Before expensive work, show resolved inputs, band order, relevant counts,
  and output location; fail on unknown settings and explain how to fix invalid
  inputs. Retain useful technical details in logs.
- Task 033 provides the model bundle with weights, architecture, band order,
  normalization and prediction settings; Task 035 adds tiled prediction. Verify
  fresh-directory prediction without the old training registry or original
  config-directory paths.
- Keep preparation code explicit and grouped in `kelpseg.prepare`. Standard
  logging shows phases, files, counts/bytes, resume decisions and long-running
  work by default in the CLI; avoid custom frameworks or clever shorthand.
- Each implementation task records its simplicity check: routine changes use
  documented settings, the implementation remains traceable through plain
  functions, and obsolete options/imports/dependencies are removed as replaced.
  Keep Box as plain folders/manifests with documented rclone operations; do not
  build a custom storage service or synchronization framework.

Task 034 owns the initial machine preparation, data staging, CUDA/bf16 checks,
production sizing and baseline launch. Its checklist handoff can complete while
remote checks remain pending; production starts only after those host checks
pass. Task 039 owns final end-to-end researcher usability, not initial relocation
or permission to start the baseline. Later local development uses a separate
checkout from the fixed code/environment of the running experiment.

## Historical work

Tasks 000–023 completed the preceding PS8B baseline/LORO study. Keep their task
records and starting commit `ac933fd667c2ddb445b8a622d8404387a2d056e2` as
historical evidence. Old artifact locations and repairs are described in
[data_artifacts.md](data_artifacts.md); do not treat a lost remote host as live.
