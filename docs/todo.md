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
contracts. Its first implementation step, when explicitly selected, is
[033A's individual augmentation previews](../tasks/033a_individual_augmentation_previews.md).
The current instruction is documentation only; no Task 033 implementation starts.
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
| [033A](../tasks/033a_individual_augmentation_previews.md) | Individual augmentation previews — planned first | Legacy transforms plus small channel shifts/band dropout; isolated strengths only; no stacking or training |
| [033B](../tasks/033b_review_augmentation_settings.md) | Review and select augmentation settings — planned | User reviews isolated outputs before strengths/probabilities and requested combination checks |
| [033C](../tasks/033c_simplify_pixel_statistics.md) | Simplify pixel statistics — planned | Small NumPy prepare/ utility reproduces selected capped reference |
| [033D](../tasks/033d_model_and_training_inputs.md) | Model and training inputs — planned | Shared preprocessing, kelp-only tensors, real B3 update and loss/confusion checks |
| [033E](../tasks/033e_training_validation_and_ema.md) | Training, validation and EMA — planned | Flat recipes, equal epochs, validation-only selection, local records and saved states |
| [033F](../tasks/033f_portable_models_and_resume.md) | Portable models and resume — planned | Copied bundle and completed-epoch recovery verified independently |
| [033G](../tasks/033g_tiny_walkthrough_and_handoff.md) | Tiny walkthrough and handoff — planned | Installed fresh-directory rehearsal, all six production previews and Task 034 handoff |
| 034 | Image-only tiled inference | Predict from copied model bundle and imagery in a fresh directory; georeferencing, edge coverage, explicit padding, no label dependency |
| 035 | Labeled scoring and qualitative figures | Unique-pixel overlap metrics; region/date/year/month prevalence and errors; signed area bias and supported matched-footprint change checks; see experiments.md |
| 036 | LORO runner and matching-TIFF comparisons | Ten 001–010 folds; paired with/without-011/012 CA/Baja results; temporal-consistency and later-date scopes reported separately; tiny suite checks |
| 037 | New-region experiment recipes | Use prepared regional and combined collection versions; four cases, fixed test scopes, explicit initialization and reset/resume behavior |
| 038 | Researcher handoff and relocation rehearsal | Another researcher follows short recipes; fresh-directory Box fetch through full workflow; production plans resolve; no scripts directory |

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
  Task 038 rehearses the finished example. Task 025's legacy capture and focused
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
- Tasks 033–034 produce a model bundle with weights, architecture, band order,
  normalization, and prediction settings. Verify fresh-directory prediction
  without the old training registry or original config-directory paths.
- Keep preparation code explicit and grouped in `kelpseg.prepare`. Standard
  logging shows phases, files, counts/bytes, resume decisions and long-running
  work by default in the CLI; avoid custom frameworks or clever shorthand.
- Each implementation task records its simplicity check: routine changes use
  documented settings, the implementation remains traceable through plain
  functions, and obsolete options/imports/dependencies are removed as replaced.
  Keep Box as plain folders/manifests with documented rclone operations; do not
  build a custom storage service or synchronization framework.

Task 038 is the local readiness gate, not a claim that CUDA behavior or
production memory use can be validated on the Mac. Full training starts only
on the selected GPU host after its hardware-specific checks.

## Historical work

Tasks 000–023 completed the preceding PS8B baseline/LORO study. Keep their task
records and starting commit `ac933fd667c2ddb445b8a622d8404387a2d056e2` as
historical evidence. Old artifact locations and repairs are described in
[data_artifacts.md](data_artifacts.md); do not treat a lost remote host as live.
