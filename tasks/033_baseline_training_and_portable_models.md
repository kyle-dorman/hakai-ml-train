# Task 033: Baseline training plan and shared decisions

Status: All seven children complete — 2026-11-03. Task 033A uses verified stock
Albumentations previews; 033A/033B are complete with the user-approved recipe.
033C reproduces the approved statistics; 033D implements model/input helpers
and bounded updates. 033E implements Lightning training/validation and EMA;
033F implements verified portable bundles and completed-epoch resume; 033G
completes the installed tiny walkthrough and Task 035 prediction handoff.
Task 032B's publication/restore prerequisite is satisfied. Task 032C is separate.

## Abstract and route

Build the researcher-facing baseline through small sequential tasks. This file
owns shared decisions and the exact normalization reference; child contracts own
implementation and acceptance. Read the entry route, this file, and only the
selected child plus its routed owner docs. Select one child per window, record
its outcome and exact next action, update the queue, and stop.

**033A: individual augmentation previews** and **033B: recipe selection and
combined previews** are complete. The user approved the stock augmentation
policy; later tasks consume that saved recipe. Preview implementation remains
independent of the later model/training runner.

## Ordered tasks

| Task | Deliverable and stop point |
|---|---|
| [033A](033a_individual_augmentation_previews.md) | Shared limited transforms and individual strength previews; no stacking/model/training |
| [033B](033b_review_augmentation_settings.md) | Review isolated previews with the user, select settings, then check approved combinations |
| [033C](033c_simplify_pixel_statistics.md) | Small NumPy pixel-statistics utility under prepare/; reproduce the selected reference |
| [033D](033d_model_and_training_inputs.md) | Manifest tensors, preprocessing, SegFormer B3 and loss/confusion helpers; bounded update only |
| [033E](033e_training_validation_and_ema.md) | Single-device training/validation, EMA, strict recipes and local records; no exact resume yet |
| [033F](033f_portable_models_and_resume.md) | Self-contained model bundle and completed-epoch resume; no tiled inference |
| [033G](033g_tiny_walkthrough_and_handoff.md) | Installed fresh-directory tiny walkthrough, production previews and Task 035 prediction handoff |

033A–033G are complete. Do not treat this table as permission to
execute several tasks together. Each later child may be refined when selected
without reopening settled scientific/data decisions.

## Shared inputs and scientific decisions

Use the published `ca_bc/v1` chip, split and collection declarations and tiny v2.
The normal local root is `/Volumes/x10pro/kelpseg`; resolve explicit local roots
as in [quickstart](../docs/quickstart.md). Task 032B owns publication evidence.
Generated previews, run records, models and reports stay outside Git.
Keep real checks bounded; run spectral cases sequentially, with at most 4 GiB
of new model-smoke artifacts and one representative durable bundle/recovery pair.

- One native eight-band collection supplies `planet8` (native eight), `planet4`
  (red/green/blue/nir), `planet3` (nir/red/green false color), and `planet_RGB`
  (red/green/blue). These recipe names were confirmed for 033E; existing `rgb`
  selection still means RGB. Keep source assignments and identity matched; no
  fold/band copies.
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
- The user selected PyTorch Lightning for 033E and historical starting settings:
  70 epochs, seed 42, AdamW 3e-4 (betas .9/.95, decay .01 excluding bias/norm),
  batch 3 × accumulation 8, five warmup epochs then cosine to 3e-5, norm clipping
  .8 and CUDA bf16-mixed. The [033E contract](033e_training_validation_and_ema.md)
  owns the detailed translation and separate CPU smoke settings. Keep current
  preprocessing and test isolation; no production Mac training.

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
Later fold-specific normalization is resolved with Task 037.

The full result is outside Git at
`/Volumes/x10pro/kelpseg/analyses/task033_normalization_positive_with_bc_clip5000_v1/statistics.json`.
Task [033C](033c_simplify_pixel_statistics.md#outcome-2026-11-02) reproduced this
reference with the installed NumPy command: exact chip/pixel counts and maximum
absolute mean/std differences of 1.14e-13 / 1.47e-11 raw units. The approved
constants above remain unchanged.
The [archived planning/analysis record](history/033_training_planning_and_analysis.md)
preserves the unclipped comparisons, high-value counts, legacy clipping audit,
exact source paths and validation. Current choices in this file supersede its
older proposals.

## Selected augmentation-preview scope

The user's 2026-11-02 direction is to use **stock Albumentations 2.0.8** and
its actual parameter meanings. The earlier custom implementations are replaced.
The exploratory Python example is separate from the installed preparation CLI;
its literal native constructors live in `src/kelpseg/augmentation_debug/trials.py`.

- `D4`: square symmetries applied jointly to images, labels and validity.
- `RandomBrightnessContrast`: separate fixed brightness and gain/contrast
  sweeps. Stock contrast multiplies by `1 + contrast_limit`; it is not the old
  per-band-mean transform, and the duplicate gain implementation is removed.
- `GaussianBlur`, `GaussNoise` and Gaussian-method `Sharpen`: actual library
  kernels, native sigma/std/alpha parameters and seeded library sampling.
- `CoarseDropout`: isolated size and count sweeps, zero image fill, -100 mask
  fill. Compare 1/2/4/8/16 holes at side 0.25, and sides 0.05 through 0.5 at
  four holes; these are exploratory values, not selected production maxima.
- `AdditiveNoise`: independent uniform offsets constant within each native band.
- `ChannelDropout`: full red/NIR diagnostic drops with zero fill. Custom partial
  fades and speculative mean-fill previews are removed.

A small adapter converts native uint16 to float32 / 65535, calls the real class,
restores raw units and invalid fill, then applies the existing final 5000 model
cap/normalization. It never pre-caps at 5000. Stock pixel kernels clip to their
unit domain where implemented, including raw-zero lower clipping; stock blur
sees zero nodata/padding and can affect neighboring valid pixels. No custom
mask-normalized replacement is used. Validity is preserved through an int8 mask
target, with -100 holes becoming invalid; augmented zeros never redefine nodata.

Keep the same 16 training examples and raw 0–2000 display ceiling. Show exact
native constructor and realized parameters, seed and pinned library version.
Only named D4 elements or red/NIR diagnostic channels override the stock
sampler's parameters; their actual application functions remain unchanged.

### Limits selected after isolated review

The user selected these limits after viewing the wider stock sweeps. They
supersede the earlier proposed maxima and the exploratory gallery endpoints.

| Operation | Selected limit |
|---|---|
| Additive brightness | `brightness_limit=(-0.0025, 0.005)`; keep the original range |
| Gaussian blur | Sigma **0.5–1.5 pixels**, `blur_limit=0` |
| Gaussian noise | Standard deviation **0–0.002** in the unit float domain; independent pixel/channel noise, mean zero |
| Independent channel shifts | Uniform offsets within **-0.01 to +0.01** per band |
| Coarse dropout | **1–4 holes**, independently sampled height/width fractions **0.05–0.25**; image fill zero, mask fill -100 |
| Channel dropout | Drop **one band** when selected, chosen uniformly from the model's selected spectral bands; zero fill |

Gain uses multipliers **0.8–1.2** (`contrast_limit=(-0.2, 0.2)`, brightness
zero). Gaussian-method Sharpen uses **alpha 0–1**, kernel size 5 and sigma 1.
The user approved these remaining ranges, including ordinary uniform library
sampling. The configured extra-operation order is brightness, gain, blur, noise,
Sharpen, coarse dropout, channel shifts, channel dropout. The selected composition
is **D4(p=1), Affine(p=0.5), then SomeOf(n=2, replace=False, p=1)**. Affine is
a separate spatial stage, outside the additional-operation pool. Set each
child's `p=1` so both selected operations run. Stock SomeOf selects uniformly
without replacement and applies selections in configured list order; it does
not shuffle their execution order. D4's eight symmetries include identity.

The user added light affine jitter during Task 033D review: shared-axis scale
0.95–1.05, independent x/y translations from -16 to +16 pixels, no additional
rotation or shear. Keep `fit_output=False` and `keep_ratio=True`: the canvas
remains 512×512 for normal training inputs. Imagery uses bilinear interpolation;
labels and validity use nearest-neighbor. Constant image fill is zero and mask
fill is -100, so exposed borders are ignored. Validation has no affine jitter.
The updated combined previews expose affine alone and in the full pipeline.

Channel shifts use stock uniform noise constant within each band. Only model-
input bands are eligible for channel dropout; the current native-eight-band
preview can drop any one of its eight bands. The 4/3-band loader restricts eligibility to its selected inputs while
preserving physical identity.
Blur starts at 0.5 because zero sigma is not a valid GaussianBlur identity in
this pinned release.

The user approved the initial combined outputs and the updated affine previews. The recipe is
saved as [native Albumentations JSON](../configs/augment/baseline.json), generated
from the readable [stock factory](../src/kelpseg/augmentation_pipeline.py) and
checked for exact serialization parity. The factory remains the implementation
used by previews and training; do not hand-maintain a second schema.
Training includes these operations in a full Albumentations Compose with
raw-domain scaling/cap, Normalize using the same constants and ToTensorV2.
The wider isolated gallery remains exploratory and does not change this policy.
No model training was performed.
Skip smooth illumination, haze, misregistration, posterization, synthetic rain,
RGB hue/Planckian jitter and per-image power/percentile normalization.

## Historical planning outcome

Only documentation changed: narrowed scope, split contracts, preserved exact
constants and archived earlier evidence. No code, dependencies, data, previews
or training were executed. At that point the next action was explicit selection of 033A.

## Current next action

033A–033G are complete. The [G outcome](033g_tiny_walkthrough_and_handoff.md#outcome-2026-11-03)
records all eight tiny CPU cases, eight metadata-only production previews,
installed package checks and the durable copied bundle/completed-epoch resume
pair. Exact resume requires zero data-loader workers and the same total schedule;
production/CUDA training remains unverified locally.
Select [Task 034](034_gpu_machine_preparation_and_baseline_launch.md) for local
GPU-machine preparation, followed by remote setup iteration and baseline launch.
The previous 034–038 slots are now 035–039: G's bundle/preprocessing handoff
belongs to image-only tiled prediction in 035; scientific scoring remains 036.
No implementation of Task 034 or later work has started.
