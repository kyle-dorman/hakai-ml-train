# Project TODO

## Current phase

Local rebuild of the Planet binary kelp toolkit. Task 024 recorded the scope,
working decisions, and small-task sequence. Task 025 preserved a verified legacy
checkpoint reference outside Git. Task 026 completed the scoped original-data
inventory and six cleanup-provenance traces. Task 028 established the installed
Typer package/path checks, researcher guide, automated CPU checks, and first
unrelated-code removal. Data workflows still use retained legacy code until
their replacement tasks; originals remain immutable.

Current active task: none.

Next action: select and scope Task 029A’s generic raw → organized contract when requested. Task 027 verified the Box backup; see its [outcome](../tasks/027_verify_box_and_back_up_raw_reference_audit.md#outcome-2026-10-27).
Task 026's artifacts, validation, and unresolved evidence limits are recorded in
[its outcome](../tasks/026_inventory_originals_and_cleanup_provenance.md#outcome-2026-10-26)
and [cleanup_provenance.md](cleanup_provenance.md).

[Task 028](../tasks/028_package_guide_and_first_removal.md#outcome-2026-10-27)
was completed independently while Task 027 was transferring.

The agreed dataset variants are **1 raw**, **2 organized intermediate**, and
**3 cleaned intermediate**. Both intermediates are unsplit; generated
train/validation/test assignments remain Task 032. The full variant and
provenance contract lives in [data_artifacts.md](data_artifacts.md#planned-raw-intermediate-and-cleaned-releases).

## Ordered roadmap

Tasks through 028 are complete. Remaining later rows are ordered scope slots, not
permission to execute multiple tasks in one window. Create and refine each
contract when selected; split further if needed.

| Task | Deliverable | Local completion gate |
|---|---|---|
| [024](../tasks/024_scope_local_rebuild.md) | Scope and rebuild plan — complete | Owned docs agree; usability requirements and example sequencing recorded |
| [025](../tasks/025_capture_legacy_reference.md) | Legacy checkpoint gut check — complete | Six original pairs, probabilities, masks, visually checked panels, and verified provenance outside Git |
| [026](../tasks/026_inventory_originals_and_cleanup_provenance.md) | Inventory originals and reconstruct cleanup provenance — complete | Read-only inventory, six CA/BC traces, previous decisions and evidence limits recorded |
| [027](../tasks/027_verify_box_and_back_up_raw_reference_audit.md) | Organize Box project and back up raw variant 1, reference, and audit — complete | Box native checksums, small round trip, and package restores verified |
| [028](../tasks/028_package_guide_and_first_removal.md) | Installable uv package, researcher guide, and first removal pass — complete | Installed Typer/path checks; wheel/sdist isolation; 139 CPU tests; guide and bounded removal |
| 029A | Implement raw variant 1 → organized intermediate 2 | One configurable organizer for every dataset; current 369-pair scope plus independent dataset fixture; byte preservation, region/alias/collision/hash/restart checks without Python edits |
| 029B | Implement organized intermediate 2 → cleaned intermediate 3 | Same preparation interface for every dataset, family-appropriate recipes, alignment/nodata/coverage checks and parent identities; guide's add-dataset/region recipe |
| 030A | Build and publish organized intermediate 2 | Full 369-pair membership, unchanged source bytes, provenance tables, QA, hashes, and verified Box copy |
| 030B | Build and publish cleaned intermediate 3 | Separate unsplit release, recorded transformations and parent hashes, QA, and verified Box copy |
| 031 | Simplify chipping/band selection and start the tiny walkthrough | After Box and cleaned release: small real-data example, source identity, edge windows, nodata, and 8/RGB+NIR/RGB inputs |
| 032 | Produce chip releases and collection-aware external split assignments | Any declared dataset/region/combination; exact release references, temporal/LORO groups, renamed-duplicate checks and fixed test scopes; Box verification |
| 033 | Simple baseline recipes and portable saved models | Ordinary recipe values; local update/validation/save/load/resume for 8/4/3 bands; weights plus prediction settings |
| 034 | Image-only tiled inference | Predict from copied model bundle and imagery in a fresh directory; georeferencing, edge coverage, explicit padding, no label dependency |
| 035 | Labeled scoring and qualitative figures | Unique-pixel overlap metrics, ignored/uncovered accounting, reusable image prediction |
| 036 | LORO runner and matching-TIFF comparisons | All folds resolve; tiny suite and comparison checks pass locally |
| 037 | New-region experiment recipes | Use prepared regional and combined collection versions; four cases, fixed test scopes, explicit initialization and reset/resume behavior |
| 038 | Researcher handoff and relocation rehearsal | Another researcher follows short recipes; fresh-directory Box fetch through full workflow; production plans resolve; no scripts directory |

## Usability acceptance across tasks

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
