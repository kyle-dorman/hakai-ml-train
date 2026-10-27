# Project TODO

## Current phase

Local rebuild of the Planet binary kelp toolkit. Task 024 recorded the scope,
working decisions, and small-task sequence. Task 025 preserved a verified legacy
checkpoint reference outside Git. Task 026 completed the scoped original-data
inventory and six cleanup-provenance traces. The existing source and datasets
have not yet been replaced. Breaking changes and removal of unrelated code are
authorized; originals remain immutable.

Current active task: none.

Next action: scope Task 027's Box verification and backup contract for the
three unchanged raw ZIPs (variant 1), legacy reference, and audit. Task 026's
artifacts, validation, and unresolved evidence limits are recorded in
[its outcome](../tasks/026_inventory_originals_and_cleanup_provenance.md#outcome-2026-10-26)
and [cleanup_provenance.md](cleanup_provenance.md).

The agreed dataset variants are **1 raw**, **2 organized intermediate**, and
**3 cleaned intermediate**. Both intermediates are unsplit; generated
train/validation/test assignments remain Task 032. The full variant and
provenance contract lives in [data_artifacts.md](data_artifacts.md#planned-raw-intermediate-and-cleaned-releases).

## Ordered roadmap

Tasks through 026 are complete. Later rows are ordered scope slots, not
permission to execute multiple tasks in one window. Create and refine each
contract when selected; split further if needed.

| Task | Deliverable | Local completion gate |
|---|---|---|
| [024](../tasks/024_scope_local_rebuild.md) | Scope and rebuild plan — complete | Owned docs agree; usability requirements and example sequencing recorded |
| [025](../tasks/025_capture_legacy_reference.md) | Legacy checkpoint gut check — complete | Six original pairs, probabilities, masks, visually checked panels, and verified provenance outside Git |
| [026](../tasks/026_inventory_originals_and_cleanup_provenance.md) | Inventory originals and reconstruct cleanup provenance — complete | Read-only inventory, six CA/BC traces, previous decisions and evidence limits recorded |
| 027 | Verify Box and back up raw variant 1, reference, and audit | Small verified round trip, then three unchanged source ZIPs with hashes; plain folders/manifests and documented rclone copies |
| 028 | Installable uv package, researcher guide, and first removal pass | Build/frozen install/imports; simple recipe/path/output conventions; focused automated checks; retire unrelated families |
| 029A | Implement raw variant 1 → organized intermediate 2 | Byte-preserving unsplit 369-pair organization; stable short IDs, regions and filename/source crosswalks; collision/hash/restart checks |
| 029B | Implement organized intermediate 2 → cleaned intermediate 3 | Separate reproducible cleanup recipe; alignment/nodata/coverage fixtures and real checks; preserve variant-2 parents and identities |
| 030A | Build and publish organized intermediate 2 | Full 369-pair membership, unchanged source bytes, provenance tables, QA, hashes, and verified Box copy |
| 030B | Build and publish cleaned intermediate 3 | Separate unsplit release, recorded transformations and parent hashes, QA, and verified Box copy |
| 031 | Simplify chipping/band selection and start the tiny walkthrough | After Box and cleaned release: small real-data example, source identity, edge windows, nodata, and 8/RGB+NIR/RGB inputs |
| 032 | Produce chip release and external split assignments | Deterministic temporal/LORO memberships without source leakage; Box verification |
| 033 | Simple baseline recipes and portable saved models | Ordinary recipe values; local update/validation/save/load/resume for 8/4/3 bands; weights plus prediction settings |
| 034 | Image-only tiled inference | Predict from copied model bundle and imagery in a fresh directory; georeferencing, edge coverage, explicit padding, no label dependency |
| 035 | Labeled scoring and qualitative figures | Unique-pixel overlap metrics, ignored/uncovered accounting, reusable image prediction |
| 036 | LORO runner and matching-TIFF comparisons | All folds resolve; tiny suite and comparison checks pass locally |
| 037 | New-region experiment recipes | Four comparison cases, fixed test scopes, explicit initialization and reset/resume behavior |
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
