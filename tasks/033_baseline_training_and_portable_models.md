# Task 033: Baseline training plan and shared decisions

Status: Split planning complete — 2026-10-28. Implementation has not started.
The user's latest instruction authorizes documentation only: do not build the
preview tool, generate previews, run data analyses or begin training yet.
Task 032B's publication/restore prerequisite is satisfied. Task 032C is separate.

## Abstract and route

Build the researcher-facing baseline through small sequential tasks. This file
owns shared decisions and the exact normalization reference; child contracts own
implementation and acceptance. Read the entry route, this file, and only the
selected child plus its routed owner docs. Select one child per window, record
its outcome and exact next action, update the queue, and stop.

The first implementation task, when explicitly selected, is **033A: individual
augmentation previews**. Its production parameters remain open. Do not make
preview implementation depend on the later model/training runner.

## Ordered tasks

| Task | Deliverable and stop point |
|---|---|
| [033A](033a_individual_augmentation_previews.md) | Shared limited transforms and individual strength previews; no stacking/model/training |
| [033B](033b_review_augmentation_settings.md) | Review isolated previews with the user, select settings, then check approved combinations |
| [033C](033c_simplify_pixel_statistics.md) | Small NumPy pixel-statistics utility under prepare/; reproduce the selected reference |
| [033D](033d_model_and_training_inputs.md) | Manifest tensors, preprocessing, SegFormer B3 and loss/confusion helpers; bounded update only |
| [033E](033e_training_validation_and_ema.md) | Single-device training/validation, EMA, strict recipes and local records; no exact resume yet |
| [033F](033f_portable_models_and_resume.md) | Self-contained model bundle and completed-epoch resume; no tiled inference |
| [033G](033g_tiny_walkthrough_and_handoff.md) | Installed fresh-directory tiny walkthrough, production previews and Task 034 handoff |

All seven are planned, not started. Do not treat this table as permission to
execute several tasks together. Each later child may be refined when selected
without reopening settled scientific/data decisions.

## Shared inputs and scientific decisions

Use the published `ca_bc/v1` chip, split and collection declarations and tiny v2.
The normal local root is `/Volumes/x10pro/kelpseg`; resolve explicit local roots
as in [quickstart](../docs/quickstart.md). Task 032B owns publication evidence.
Generated previews, run records, models and reports stay outside Git.
Keep real checks bounded; run spectral cases sequentially, with at most 4 GiB
of new model-smoke artifacts and one representative durable bundle/recovery pair.

- One native eight-band collection supplies all/ RGB+NIR/ RGB variants. Keep
  source assignments, identity and spectral ordering matched; no fold/band copies.
- The baseline including 011/012 (`augmented`) is primary; `base` excludes both.
  Use **equal epochs**, seeded shuffled passes without replacement, matching
  optimizer/augmentation policy. Including BC adds data and optimizer updates.
- Train rows must have `kelp_pixels > 0`. With BC, 8,518 of 18,311 candidate
  training chips are eligible, representing 254 of 258 assigned sources.
  Keep canonical backgrounds and validation/test membership unchanged. This
  training filter requires no Task 032B rebuild or upload change.
- Keep 512-pixel native-resolution inputs, bottom/right loading-time padding,
  native-band nodata detection, target ignore -100 and disjoint chip validation.
  Do not open test payloads for training, augmentation selection or checkpoint
  selection. Aggregate confusion counts before calculating metrics.
- Keep SegFormer B3 / mit_b3, generic ImageNet initialization for new baselines,
  0.7 smoothed BCE plus 0.3 Lovasz (smoothing 0.1), and EMA decay 0.999.
  EMA first copies current weights after optimizer update 101; use current
  weights for earlier validation, then EMA for validation/best export. Recovery
  retains ordinary weights and averaging state separately.
- Threshold 0.5 is fixed before test; select best aggregate validation foreground
  IoU with earliest ties. Use distinct rebuild identities and local records;
  optional W&B stays `kdorman90-ucla/kelpseg`.
- Production epoch count, effective batch and schedule remain recipe decisions
  when training is scoped. Historical 70 epochs / AdamW 3e-4 are proposals,
  not silently approved new production settings. No production Mac training.

## Selected training normalization

Use `(min(raw_pixel, 5000) - mean) / std` with these full-precision values in
native order. They were measured after the cap on all nonnodata pixels within
8,518 kelp-positive with-BC chips: 2,052,580,518 pixel exposures, including overlap.

```toml
clip_value = 5000
band_names = ["coastal_blue", "blue", "green_i", "green", "yellow", "red", "rededge", "nir"]
mean = [323.64878219651854, 389.5317689154827, 438.39646268775465, 465.35795980452735, 459.9420472595575, 451.3045100567385, 536.2606342593172, 799.2215816851071]
std = [294.97881315006885, 336.1495661091302, 401.6870189255488, 459.22170495895057, 541.9194107884493, 575.3320083210876, 637.0868757507536, 994.5695551762033]
```

Select entries by band name; RGB+NIR is red/green/blue/nir. Store the selected
values and cap directly in flat recipes/model bundles. Detect native nodata
before clipping or channel selection. The final 5000 cap follows photometric
augmentation and precedes fixed standardization; preserve invalid/padding fill.
Use the same deterministic cap/normalization for validation and prediction.

This is a substantial change from Clay: its means are about 4.5–5.3 times larger.
Keep legacy checkpoints on their original preprocessing. The reference is shared
between baseline variants with its with-BC origin explicit; it cannot be called
training-only for a LORO fold whose held-out region contributed to these estimates.
Later fold-specific normalization is resolved with Task 036.

The full result is outside Git at
`/Volumes/x10pro/kelpseg/analyses/task033_normalization_positive_with_bc_clip5000_v1/statistics.json`.
The [archived planning/analysis record](history/033_training_planning_and_analysis.md)
preserves the unclipped comparisons, high-value counts, legacy clipping audit,
exact source paths and validation. Current choices in this file supersede its
older proposals.

## Selected augmentation-preview scope

Limit this work to the familiar legacy operations plus the two additions:

- Square rotations/reflections, applied jointly to images, labels and masks.
- Legacy-style additive brightness, with explicit scale and no incidental 4000 cap.
- Spatial coarse dropout, with ignored targets under erased holes.
- Small independent channel shifts, keyed by physical band name.
- Band dropout: initially preview one selected band at a time, named explicitly.

Skip smooth illumination/plasma fields, Gaussian noise/blur, fog/haze,
misregistration, posterization, synthetic rain, RGB hue/Planckian jitter and
per-image power/percentile normalization in this task family. The estuary code
is read-only inspiration; do not copy its framework or repair that project.

Preview operations **individually** at identity and multiple strengths first.
Do not stack operations or choose training probabilities/ranges in 033A.
Band dropout preserves labels and original validity, unlike spatial dropout;
it must never remove every selected channel. Compare raw-zero and neutral
normalized-zero fill before choosing the rule. Keep native-band draws explicit
across spectral views; show when a dropped band is absent from a view rather
than silently drawing a different corruption.

## Planning outcome and next action

Only documentation changed: narrowed scope, split contracts, preserved exact
constants and archived earlier evidence. No code, dependencies, data, previews
or training were executed. Next action, when the user selects implementation:
start 033A only. After all seven children close, select Task 034 in a new window.
