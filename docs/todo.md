# Project TODO

## Current status and next action

Task **038A CI help-text checks is complete**; its
[outcome](../tasks/038a_ci_help_text.md#outcome) records the fix and 20 passing
checks with terminal styling forced. The user authorized committing the fix;
push remains a user action.
The pending roadmap is unchanged.

Task **038 methods documentation and review are complete**. [Methods](methods.md) now owns
the implemented scientific workflow; its [task outcome](../tasks/038_methods_documentation.md#outcome--2026-11-12)
records the claim audit, review corrections and validation. The user approved
committing the complete documentation, including the [paper summary](paper_methods.md).
The selected model remains the
[with-BC 8-band B0 BCE + Dice epoch-16 EMA baseline](experiments.md#current-planet-8-band-b0-baseline).

Next select and bound **039: New-region recipes** in a separate task window.
Task 042 remains the final researcher handoff. Neither begins in 038.

## Pending roadmap

| Order | Task | Completion gate |
|---|---|---|
| 1 | 039: New-region recipes | Contract when selected; direct transfer, kelp/generic initialization and combined training with fixed held-out scopes |
| 2 | 042: Final researcher handoff | Contract when selected; rehearse the complete workflow, reusing existing GPU setup |

Completed 040/041 retain their numbers. 039 and 042 replace the older roadmap
slots 038 and 039; historical task numbering is retained as evidence.

## Open follow-ups

- Earlier external experiment/analysis backups have not all been verified;
  [Task 034](../tasks/034_gpu_machine_preparation_and_baseline_launch.md) records
  the affected roots. This is not an instruction to transfer artifacts in 038.
- New-region recipes and the final usability rehearsal remain pending above.
  There is no documentation blocker requiring new data analysis.

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
  Task 042 rehearses the finished example. Task 025's legacy capture and focused
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
  logging shows phases, files, counts/bytes and long-running
  work by default in the CLI; avoid custom frameworks or clever shorthand.
- Each implementation task records its simplicity check: routine changes use
  documented settings, the implementation remains traceable through plain
  functions, and obsolete options/imports/dependencies are removed as replaced.
  Keep Box as plain folders/manifests with documented rclone operations; do not
  build a custom storage service or synchronization framework.

## Completed work

See [history](history.md) for milestones, published releases, completed studies
and recovery references; [task navigation](../tasks/README.md) links individual
contracts and outcomes. Detailed results belong in those records, not this queue.
