# Task 033A: Individual augmentation previews

Status: Planned — 2026-10-28. Not started; the current user request is docs only.
Depends on: Completed Task 032B; shared Task 033 decisions. No model/stats-cleanup dependency.

## Abstract

Build the preview tool first, using the same small transform functions later
training will call. Show each operation independently at several strengths.
Stop with a gallery for user review; do not stack or select production settings.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
The shared parent and [experiments](../docs/experiments.md), implemented
chip/band/split portions of [quickstart](../docs/quickstart.md), and
[documentation](../docs/documentation.md). Use published chip/split metadata and
tiny v2 or a small declared subset of full training chips. The separate estuary
transforms file is reference only; no estuary package dependency or edits.

## Outputs and planned interface

- Planned `src/kelpseg/augmentations.py`: plain NumPy sampling/application
  functions for square symmetry, additive brightness, spatial coarse dropout,
  small independent channel shifts and band dropout. No generic policy framework.
- Planned `src/kelpseg/preprocessing.py`: shared native validity, 5000 cap,
  band selection and fixed normalization helpers, reused by later model tasks.
- Planned `src/kelpseg/augmentation_preview.py`, thin `cli/augmentations.py`
  registration and `configs/augment/preview.toml` with trial strengths/seeds.
- Future CLI (not installed):
  `uv run kelpseg preview-augmentations --chips <root> --assignments <csv> --variant augmented --recipe configs/augment/preview.toml --output <fresh-directory>`.
- PNG contact sheets, a small optional local HTML index, selected window list
  and plain realized-parameter metadata outside Git. No model or training import.

## Plan/spec

1. Before coding, write the compact trial schema and file plan in this task.
   Use a fixed roughly 12–16 training-window sample spanning BC, thin/dense/sparse
   kelp, nodata and partial edges. Add two named canonical training-background
   controls for diagnostics only; no validation/test reads.
2. Force one operation at a time; show original, identity and several strengths,
   including endpoints. Freeze geometry for intensity sweeps and reuse random
   draws/seeds across a strength sweep. Trial values are not training defaults.
3. Show RGB, NIR/false color, mask/ignore overlays and thin-kelp close-ups using
   one frozen training-derived display stretch. Record actual parameters, raw
   ranges, values below zero, clipping and remaining valid/foreground support.
4. For channel shifts use physical names and small raw-unit shifts. For band
   dropout enumerate one selected band at a time; compare raw-zero versus mean
   fill (neutral normalized zero), keep labels/validity unchanged and retain at
   least one selected band. Show spectral views unaffected by an absent band.
   Spatial dropout alone changes targets under holes to -100. Do not infer
   new nodata from values made zero by augmentation.
5. Apply the settled final 5000 cap and fixed normalization through the shared
   helpers. Keep original native validity and explicit true-size padding.
   Promote only implemented preview dependencies, keep CLI imports lazy and
   extend the quickstart with actual usage when the tool exists.

## User decisions required

No production augmentation ranges, probabilities, band-dropout fill or lower
bound for additive changes are selected. Use clearly labeled trial values and
show their consequences; ask the user to choose only after producing previews.
Do not add smooth illumination, noise, blur, haze, misregistration or stacking.

## Smoke and validation

Add focused augmentation/preview/CLI tests for paired geometry, label values,
photometric validity preservation, spatial-ignore versus band-dropout behavior,
no all-channel dropout, cap boundaries and seed replay across band selections.
Preview must call the shared application/preprocessing functions. Run one bounded
real-data gallery, visually inspect its panels and verify metadata. Run relevant
package checks, Ruff format/check and `git diff --check`; no model tests yet.

## Acceptance and non-goals

The user can inspect every allowed operation alone at multiple strengths.
Current settings, seeds, band identities, masks and clipping are visible;
canonical data is untouched. No combinations or training run occurred.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: 033B: review the isolated gallery with the user and record selected settings.
