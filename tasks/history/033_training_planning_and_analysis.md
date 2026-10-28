# Archived Task 033 planning and analysis

Archived 2026-10-28 when the user split implementation into Tasks 033A–033G.
Use [the current parent plan](../033_baseline_training_and_portable_models.md)
and the selected child contract. The earlier broad augmentation catalog and
implementation proposal below are superseded; the numerical analyses remain
historical evidence. No implementation or preview generation occurred here.

# Task 033: Simple baseline training and portable saved models

Status: Planning draft — 2026-10-28. Implementation has not started.
Depends on: Task 032B's completed publication and bounded restore/load handoff.
This prerequisite is satisfied; Task 032B completed publication on 2026-10-28.

## Abstract

Replace the legacy training interface with one small installed SegFormer B3
workflow. Train from the existing chip/split manifests, validate on disjoint
chips, save a portable best model and a separate same-run recovery checkpoint,
and verify the workflow locally for 8/4/3 bands. Simplify the existing pixel
statistics utility into `kelpseg.prepare` and verify augmentation previews.
Supply matched with/without-BC recipes and extend tiny v2 through training.
Stop before production training, tiled inference, scientific scoring, LORO
orchestration or regional adaptation.

This is a plan, not an assertion that training commands are installed. Build
the shared augmentation functions and their preview tool using explicit trial
settings first. Review those previews before finalizing production augmentation
parameters; their open values must not prevent constructing the preview tool.

## Read and inputs

Follow the entry route, then read [product](../../docs/product.md),
[architecture](../../docs/architecture.md), [experiments](../../docs/experiments.md),
[documentation](../../docs/documentation.md), the chip/split/tiny sections of
[quickstart](../../docs/quickstart.md), and [Task 032B](../032b_produce_and_publish_chip_release.md)'s
final outcome when available. Use [artifact policy](../../docs/data_artifacts.md)
for local roots, portability and the Git boundary.

Inspect the retained `trainer.py`, `src/data.py`, `src/models/smp.py`,
`src/models/__init__.py`, `src/losses.py`, `src/schedulers.py`, `src/callbacks.py`
and `configs/kelp-ps8b/generalization/segformer_b3_v3.yaml` as migration inputs.
They do not define replacement defaults automatically. Task 025's preserved
legacy reference remains historical evidence; exact reproduction is unnecessary.

Inputs relative to the explicit machine `data_root`:

- `data/chips/ca_bc/v1/`: one native-band collection, true-size NPZ payloads,
  `windows.csv`, `sources.json`, `recipe.json` and `summary.json`.
- `data/splits/ca_bc/v1/`: existing assignments and collection metadata.
- `data/collections/ca_bc/v1/collection.json`: portable release declaration.
- `data/examples/tiny_ca_bc/v2/`: existing 13-crop walkthrough inputs; use its
  documented fresh split/chip outputs for the real smoke.
- Existing `load_paths`, `select_windows`, `load_chip` and band-name selection.

Use Task 032B's final counts rather than re-auditing the release. Its current
local baseline selection is 15,621 base / 18,311 augmented training windows,
with the same 933 validation and 1,262 test windows. Tiny v2 has 8 / 20 training
windows and two validation windows. These are scope/count checks, not scores.

## User decisions required

### Recorded on 2026-10-28

- **Equal epochs** for with/without-BC comparisons. Visit every eligible
  training chip once per epoch in seeded shuffled order, retaining overlap.
  Apply the selected kelp-positive training filter below; no replacement or
  balancing sampler.
  Keep epoch count, effective batch, spectral recipe, initialization policy,
  optimizer settings and validation/checkpoint rules matched. Including BC adds
  data and optimizer updates; this is not a fixed-compute comparison. Record
  actual examples and optimizer updates, including the final partial batch.
- Continue discussing the training recipe in chat. The proposed simultaneous
  switch to BCE, spatial-only augmentation, raw weights and scale-only
  normalization is **not approved**.

### Follow-up decisions and analysis authorization, 2026-10-28

- **Keep the working loss:** 0.7 label-smoothed BCE / 0.3 Lovasz, with the
  existing smoothing 0.1 and ignore index -100. Handle empty valid support
  explicitly rather than inheriting the legacy empty-mean NaN behavior.
- **Reject scale-only normalization.** The legacy constants exactly match
  [Clay's PlanetScope configuration](https://github.com/Clay-foundation/model/blob/main/configs/metadata.yaml#L52-L85).
  Its `/4000` input scale and correspondingly scaled means/stds cancel, giving
  `(raw - mean_raw) / std_raw`. Direct raw-unit standardization is equivalent;
  it is not division by 4000 alone.
- The user authorizes running their statistics method on current training data
  and comparing its values with Clay before selecting normalization. Compute
  both baseline variants from their active training windows, using true-size
  native imagery, excluding all-band-zero nodata, with no validation/test
  payload access. Preserve the method's pixel weighting (including repeated
  overlap) and sample standard deviation, using float64 for numerical accuracy.
  Labels do not select pixels for these image statistics. This analysis is
  authorized while training implementation remains a draft.
- Additional augmentations are welcome for discussion. **Visual preview tooling
  is required** before settling their parameter ranges; the actual transforms
  used for training must produce the previews. No new augmentation ranges are
  approved yet.
- **Keep EMA**, as explicitly approved after the legacy baseline audit. Use
  decay 0.999 and the documented update start below. Validation/best-model
  export use averaged weights once available; recovery stores ordinary weights
  and averaging state separately.
- **Use the newly calculated kelp-positive with-BC statistics for training**,
  replacing Clay's constants in the new baseline. The exact raw-unit values
  are recorded below. They are a fixed shared baseline reference for both BC
  variants and all three spectral selections, not recalculated per run.
- **Clip raw band values at 5000 before normalization.** The user selected
  this cap after reviewing >4000/>5000 rates and authorized recomputing the
  same training reference with it applied. Use the capped statistics below,
  superseding the earlier unclipped values. Apply the cap consistently for
  training, validation and prediction without rewriting source payloads.
- **Train only on chips containing kelp:** after ordinary manifest selection,
  require `split == "train"` and `kelp_pixels > 0`. One kelp pixel suffices.
  This is a training-only eligibility setting, separate from source assignments
  and canonical retention; no validation/test filtering or payload deletion.
  Task 032B already publishes the required foreground counts and stays unchanged.
  With BC this yields 8,518 eligible chips from 254 sources and excludes 9,793
  zero-kelp training candidates. Report eligible/excluded counts separately from
  canonical/source-assignment counts and apply the same rule to both variants.
  The actual model input/normalization still includes all nonnodata pixels
  inside eligible chips, including their background.
- **Clean up the pixel-statistics utility in this task.** Replace the old
  `src/prepare/channel_stats.py` and one-off analysis complexity with a small
  NumPy implementation under `src/kelpseg/prepare/`, ordinary functions and
  default progress logs. Do not copy the analysis-specific bookkeeping into
  the installed package. This is planned implementation, not an installed
  command yet.

### Selected training normalization

Use `(min(raw_pixel, 5000) - mean) / std` with these **full-precision** values, in the
declared native band order. Values are from the 8,518 kelp-positive with-BC
training chips, over all their nonnodata pixels; overlap counts per exposure.
The source is the `statistics` entry in
`/Volumes/x10pro/kelpseg/analyses/task033_normalization_positive_with_bc_clip5000_v1/statistics.json`.

```toml
clip_value = 5000
band_names = ["coastal_blue", "blue", "green_i", "green", "yellow", "red", "rededge", "nir"]
mean = [323.64878219651854, 389.5317689154827, 438.39646268775465, 465.35795980452735, 459.9420472595575, 451.3045100567385, 536.2606342593172, 799.2215816851071]
std = [294.97881315006885, 336.1495661091302, 401.6870189255488, 459.22170495895057, 541.9194107884493, 575.3320083210876, 637.0868757507536, 994.5695551762033]
```

Select entries by band name: RGB+NIR is red/green/blue/nir, and RGB is
red/green/blue. Store the selected values directly in each flat training recipe
and portable bundle; no dependency on this external analysis folder at runtime.
Use the same transform for training, validation and later prediction, without
per-image standardization. Detect native-band nodata before clipping or band
selection and preserve the declared invalid/padding fill. In training, apply
the final 5000 cap after any photometric augmentation and before standardizing;
augmentation previews must verify this order and avoid an incidental 4000 cap.
Store the cap as well as means/stds directly in recipes and portable bundles.

This is a substantial input-distribution change: Clay's means are about
4.5–5.3 times larger. Standard deviations also change, with NIR slightly larger
than Clay. Record this as a new recipe identity; the legacy checkpoint retains
its original preprocessing. These selected values were measured **after the
5000 cap**. Earlier unclipped values remain historical evidence below and must
not populate the new model recipes.

Training-chip eligibility follows the separately selected kelp-positive rule
above. Canonical backgrounds remain available. LORO must use a reference
estimated without its held-out region; the baseline reference above cannot be
called training-only for every fold. That policy is resolved in Task 036.

### Open before implementation

**Augmentation:** review shared spectral gain/offset, noise, blur and dropout
candidates through previews before choosing ranges. Keep joint spatial
flips/quarter rotations explicit. Avoid accidental float-input clipping,
RGB-only color assumptions, changes to spectral identity and invalid/padded
pixels becoming valid. All geometric operations transform images, targets
and masks together; validation is deterministic. The 5000 cap and matching
normalization values are settled.

The legacy EMA uses decay 0.999 and first accepts an update after optimizer
step 101; that first update copies the current model. Lightning validates with
averaged weights and saves them as `state_dict`, with ordinary training weights
under `current_model_state`. Task 025 verified this in the captured checkpoint.
Define sensible pre-EMA validation explicitly: use current weights until an
average exists, rather than accidentally validating initialization weights.

Safe planning defaults: SegFormer B3 (`mit_b3`), one foreground logit, generic
ImageNet initialization for new baselines, seed 42, threshold 0.5 fixed before
test, best aggregate validation foreground IoU, earliest checkpoint on ties.
Use a distinct rebuild recipe identity. Draft production values may start from
70 epochs and AdamW LR 3e-4 / weight decay 0.01 / betas 0.9,0.95, with
warmup/cosine scheduling; finalize the schedule and effective batch alongside
the recipe, before any production run. CPU smoke values are explicitly separate.

GPU host, CUDA precision and production batch sizing are later host checks.
Do not seek decisions about LORO orchestration or adaptation in this task.

## Expected outputs and planned interface

One flat TOML recipe per spectral choice, without inheritance or Python class
paths: `configs/train/planet8.toml`, `planet4.toml`, `planet3.toml`, plus
`tiny_cpu.toml`. The band recipes differ only in declared band selection and
the corresponding preprocessing/input adaptation. Select `base` or `augmented`
with one explicit option; no six copied configs or per-band datasets.

Planned commands, to implement and document in this task:

```bash
uv run kelpseg train --recipe configs/train/planet8.toml --paths paths.local.toml --variant augmented --run-id baseline-8b-with-bc-01 --dry-run
uv run kelpseg train --recipe configs/train/planet8.toml --paths paths.local.toml --variant augmented --run-id baseline-8b-with-bc-01
uv run kelpseg train --recipe configs/train/planet8.toml --paths paths.local.toml --variant base --run-id baseline-8b-without-bc-01 --dry-run
uv run kelpseg train --resume /absolute/path/to/run/checkpoints/last.pt --paths paths.local.toml
uv run kelpseg preview-augmentations --recipe configs/train/planet8.toml --paths paths.local.toml --variant augmented --output /absolute/path/to/fresh-preview --seed 42
```

All commands above are future interfaces. Do not run production training on the
Mac. Resume uses saved settings, explicit relocated roots and the existing run;
it cannot silently change bands, assignments, recipe or total budget.

Use `<runs_root>/<run_id>/` with `settings.json`, `run.json`,
`checkpoints/last.pt`, `metrics/validation.csv` and `model/`. `model/` contains
`weights.pt` plus `model.json`: architecture, ordered bands, normalization,
input size, nodata/padding policy, threshold, weight kind and recipe identity.
Reserve `figures/` for later output; do not add placeholder reports. Runtime
records include release/split identities, seed, counts, budget, Git version,
runtime, status and selection result. Keep generated artifacts outside Git.

The copied model bundle is self-contained for model construction and supplied
image-array probabilities. Task 034 adds georeferenced tiled prediction.
Recovery includes model, optimizer, scheduler, epoch/update progress, random
state and EMA state. Support completed-epoch recovery only; a failed
partial epoch restarts from the last completed checkpoint. Do not promise exact
mid-batch recovery. Model-only loading must not restore optimizer/progress or
download initialization weights. Adaptation recipes remain Task 037.

## Implementation plan

Before coding, finalize the open choices and write a compact schema/file plan
here. Keep the following boundaries small; combine only where clearer:

| Planned file | Responsibility |
|---|---|
| `src/kelpseg/prepare/channel_stats.py` | Simple NumPy streaming pixel statistics over explicitly selected training chips |
| `src/kelpseg/cli/pixel_stats.py` | Thin training-scope statistics handler |
| `src/kelpseg/training/settings.py` | One strict recipe schema, input resolution and preview |
| `src/kelpseg/training/data.py` | Manifest-selected tensors using the shared augmentation functions |
| `src/kelpseg/training/augmentations.py` | Small explicit sampling/application functions shared by training and preview |
| `src/kelpseg/training/preview.py` | Training-only visual panels from those same transforms |
| `src/kelpseg/models.py` | Fixed B3 constructor and shared image preprocessing |
| `src/kelpseg/training/loss.py` | Chosen binary objective and ignore handling |
| `src/kelpseg/training/metrics.py` | Pixel confusion counts and explicit undefined ratios |
| `src/kelpseg/training/loop.py` | Plain training/validation sequence, schedule and progress |
| `src/kelpseg/training/checkpoints.py` | Portable best model and completed-epoch recovery |
| `src/kelpseg/cli/train.py` | Thin preview/train/resume handler; lazy heavy imports |
| `src/kelpseg/cli/augmentations.py` | Thin augmentation-preview handler |

1. Resolve recipe and explicit roots; consume the declaration's chip/split
   references without requiring restored cleaned TIFFs. Reuse `select_windows`
   once and retain identities/coverage. Preview train/val/test metadata counts,
   selected bands, preprocessing, initialization, effective batch, epoch/update
   budget and outputs. No payload scan, weights download or output creation in
   dry-run. Refuse unknown settings, invalid joins/bands and initial overwrite.
   Apply the explicit flat-recipe `kelp_only = true` setting only to selected
   train rows, using the existing manifest counts. Keep val/test rows as selected
   by the existing API. Record zero-kelp training exclusions in run counts;
   do not rewrite the canonical manifests, split assignments or payloads.
2. Reuse `load_chip` for native-band nodata and bottom/right padding. Convert
   HWC uint16 to float32 CHW after explicit band selection. Preserve true extents
   and `-100` targets; no resize, recleaning, label remap or centered padding.
   Specify padding/nodata input fill after normalization so Task 034 can use
   exactly the same image-only preprocessing. Do not infer validity from the
   selected RGB channels alone.
3. Construct B3 with declared input adaptation. Inspect the installed encoder's
   pretrained 3-to-4/8-channel adaptation and record its actual behavior; never
   imply RGB kernel positions are wavelength-specific weights. Synthetic tests
   use no-download initialization. Verify the real ImageNet path separately
   using available cached weights or one explicit initialization download.
4. Implement a plain single-device loop. Define the final partial-batch and
   gradient-accumulation behavior, valid-pixel loss weighting, all-ignored-batch
   handling and step-based scheduler totals from each variant's actual epoch
   length. Match schedule fractions across equal-epoch recipes. Validate every
   epoch without augmentation using active disjoint windows. Sum TP/FP/FN/TN
   before ratios; never average chip IoUs. Log valid-label support and geometry
   separately. Undefined selection metrics cannot silently win best selection.
   Training must never open test payloads, including after fitting finishes.
5. Save best bundle and last recovery separately. Verify load and completed-epoch
   resume with seeded sampling/augmentation. Default local records require no
   tracking login. If W&B logging is enabled, use `kdorman90-ucla/kelpseg`, a new
   group identity and simple optional logging; no legacy registry/framework.
6. Promote implemented ML dependencies to runtime in `pyproject.toml`/`uv.lock`.
   Update distribution checks that currently require torch to be absent, while
   preserving lightweight CLI help and installed operation outside the checkout.
   Remove training-only obsolete options/imports/configs where replacement is
   complete. Inspect consumers first: retained legacy evaluation still imports
   `src.models.smp`, and other tools/tests use `src.data`. Do not break those
   workflows by blanket deletion. Full `scripts/` removal is a later end-state.
7. Extend the quickstart through tiny CPU train/validation/save/load/resume,
   six unexecuted production recipe previews, output interpretation and common
   errors. Update architecture/experiments only for finalized implemented
   behavior. Keep detailed smoke evidence in this task record.

### Pixel-statistics cleanup acceptance

Implement one small module under `prepare/` with ordinary functions for
selection, streaming mean/variance and report writing. Reuse existing manifest
selection; do not require Torch, a DataLoader, Albumentations, a model or labels
to read imagery. Handle variable true-size chips directly. Exclude all-band-zero
nodata before selecting bands; artificial padding contributes no observations.
Keep float64 arithmetic and sample standard deviation (`ddof=1`) matching the
approved analysis. Make clipping an explicit recorded optional setting; the
selected training reference uses `clip_value = 5000` before moments. No scaling
or normalization is performed while estimating. Keep native nodata detection
before the cap and never silently mix clipped model inputs with unclipped
statistics. Source payloads remain unchanged.

The planned CLI is:

```bash
uv run kelpseg pixel-stats --chips /absolute/path/to/chips --assignments /absolute/path/to/assignments.csv --experiment baseline --variant augmented --kelp-only --clip-value 5000 --output /absolute/path/to/fresh-statistics.json
```

This command is not installed yet. Its scope is training only. `--kelp-only`
uses the manifest's foreground count to select entire chips; without the flag,
all active training chips contribute. Report bands, raw means/stds, valid pixel
count, selected/excluded chip counts, cap and input/split/filter references in one
plain JSON result. Do not hardcode CA/BC paths, band counts, Clay comparisons,
per-region analysis tables or historical output versions into the implementation.
Use standard logging for the phase, current file, counts/bytes and elapsed
progress. Refuse an existing output initially and publish the completed small
report atomically; no resume, parallel workers, hashes or receipts.

Retire `src/prepare/channel_stats.py` after checking its remaining consumers.
Keep earlier external producers/results as historical evidence. Test known
pixel moments against NumPy, nodata/true-size edges, raw-unit output, training
and kelp-only selection, exact clip boundaries, overlap weighting and insufficient/zero-variance
support errors. A generic utility must work on declared band counts without
copying the one-off script's eight-band assumptions or its legacy imports.
Verify the selected production scope and reproduce the approved values in one
bounded-memory pass after focused synthetic checks; no repeated release audit.

### Augmentation preview acceptance

#### Legacy baseline and reference audit

The v3 recipe used 1024-pixel `RandomCrop` with centered padding, followed by
`SquareSymmetry` at probability 1 (one of the eight square rotations/reflections,
including identity). It applied additive brightness up to +/-20% of image mean
at probability 0.3, with contrast change zero. `CoarseDropout` ran at probability
0.5: 1–8 holes, height/width up to 32 pixels, image fill zero and label fill -100.
No noise, blur or smooth illumination transform appears in that recipe.
Scaling/normalization are preprocessing, not additional random augmentations.
The new 512 input size and bottom/right padding remain fixed. A 32-pixel hole
occupies a larger relative width in the new inputs; do not copy dimensions
without previewing their effect on thin kelp and remaining foreground.

Read-only ideas were taken from the separate project at
`/Users/kyledorman/Documents/UCLA_kelp/estuary/src/estuary/util/transforms.py`,
especially `basic_train_augs`, `RandomChannelShift`, `RandomPlasmaFog` and
`MisalignedImage`, with `util/config.py` and the actual model/low-quality
consumers checked. Borrow bounded ideas without importing the estuary package
or its nested random-policy framework. No estuary files were changed.

Important reference limitations: `bands.num_channels` is a method but several
RGB guards compare it directly with 3, so those branches are not enabled as
written. Custom fog and misregistration assume three bands; channel shifting
clamps to [0,1]. `ScaledRandomGaussianNoise` rescales each noisy band to its
original per-image min/max, so it is not plain additive noise. A 0.15 channel
shift on a 5000-scaled range is 750 raw units, larger than most current band
means. Power/percentile transforms would change the selected normalization.
These are audit findings, not requests to repair the separate project.

#### Candidate order and trial settings

The following are **preview proposals**, not approved production transforms,
parameter ranges or probabilities:

| Candidate | Priority and initial preview |
|---|---|
| Square rotations/reflections | Retain as the geometric reference; enumerate all eight once and verify paired labels/masks without interpolation |
| Shared spectral gain/offset | First photometric candidate; inspect gains 0.8/1/1.2 and offsets -50/0/+50 raw units separately |
| Smooth spatial illumination | Borrow the linear/corner/plasma-field idea; start with one field shared across native bands, showing +/-10%,20%,30% gain variation |
| Additive Gaussian noise | Compare raw-unit standard deviations 10/30/100 plus identity; specify inter-band noise correlation explicitly |
| Gaussian blur | Compare sigma 0.3/0.7/1.2 source pixels plus identity, using one spatial kernel across bands; zoom on narrow kelp |
| Coarse dropout | Compare 8/16/32-pixel holes, then hole counts separately; fill dropped targets -100 and report erased foreground |
| Independent channel shifts | Separate spectral stress test; preview small raw-unit offsets before considering the estuary 750-unit equivalent |
| Inter-band misregistration | Separate stress test; start with translations 0.25/0.5/1 source pixel and one declared red-band/label anchor, not the full three-channel affine implementation |
| Fog/haze or strong plasma effects | Separate experimental gallery; eight-band behavior and treatment of genuinely obscured labels require explicit design |

Do not enable posterization, Planckian/RGB hue operations, synthetic rain,
per-image power/percentile normalization or the complete strong corruption chain
by default. A real request to explore one can add a bounded preview later.
Candidates are hypotheses about useful variation; their visual plausibility
does not establish improved model accuracy.

#### Review sequence

1. Select a fixed small manifest of roughly 12–16 eligible training windows
   spanning regions/dates, BC, large/thin/sparse kelp, nodata and partial edges.
   Add two explicitly labeled canonical training-background controls for
   diagnostics; they do not become eligible training inputs. No validation/test
   imagery is needed to choose initial augmentation ranges.
2. Produce one-transform-at-a-time panels: original, identity, increasing
   strength and parameter endpoints. Force the displayed operation to run so
   random non-application cannot hide its effects. Freeze spatial transforms
   when inspecting photometric changes. For stochastic fields/noise, reuse a
   seed across the strength sweep and show several additional seeds.
3. Inspect RGB, NIR/false color, label/ignore overlays and close-up boundaries.
   Use one display stretch derived from the unaugmented training preview set
   and freeze it across the gallery. Never independently stretch augmented
   panels. Display stretching is separate from the model's 5000 cap and fixed
   normalization.
4. Record realized parameters, per-band raw ranges/quantiles, values below zero,
   additional upper/lower clipping, valid/ignored support and foreground erased
   by dropout. Do not recompute nodata from pixels made dark by augmentation;
   preserve the original validity mask and transform it jointly with geometry.
   Review the lower-bound policy explicitly for additive offsets/noise. For
   resampling, use nearest-neighbor labels and exclude newly unsupported borders.
   Misregistration must declare the label/reference-band anchor and each band's
   support; do not silently reuse ordinary joint-geometry assumptions.
5. Choose acceptable strength ranges from the isolated panels. Then preview
   random draws from each proposed range and small combinations using the
   exact production order, with a visible list of applied operations. Choose
   application probabilities only after that review; avoid hidden nested
   selection probabilities and compulsory stacks of every corruption.
6. Freeze the recipe values and run focused mask/band/cap/replay checks, followed
   by the bounded training smoke. Any accuracy comparison uses validation and
   a declared recipe identity; test remains held out. No production training
   or final augmentation selection is authorized by this preview proposal.

Native bands receive the same sampled transform realization before selecting
RGB/RGB+NIR views. Shared gains/fields use the same values across spectral
variants; independent band perturbations are keyed by band name. Keep the
chosen 5000 cap after photometric augmentation and before fixed standardization.
Previews must exercise the same path, with no incidental [0,1] clamp in raw units.

#### Tool outputs and correctness

Implement the planned `preview-augmentations` command using training's shared
transform functions, before finalizing additional augmentation settings. It
creates no model and reads only selected training images/labels. Use a small
declared sample covering kelp-rich, low-kelp, background-only, nodata and partial
edges, including BC when selected. Record source/window identities, settings,
seed and realized transform values in plain JSON beside PNG panels.

Show original and augmented RGB, NIR or false color, plus target/ignore overlays.
Use identical display limits for each before/after pair and across parameter
comparisons; independently stretching panels must not hide a gain or clipping.
Show multiple seeds and parameter extremes, any clipped-value fraction and
remaining foreground/valid-label support. Apply the same sampled transform to
the native bands before selecting spectral views so comparisons remain matched.
After photometric changes, nodata/padding keep their declared fill and targets
remain unchanged; dropout uses explicit ignore behavior. Test label alignment,
mask preservation and reproducible previews. Preview images diagnose parameter
behavior; they do not establish a model-accuracy benefit. Keep plotting small
and promote its dependency when this installed command arrives.

Save readable PNG contact sheets plus a small optional local HTML index, plain
parameter/seed metadata and the fixed selected-window list. A notebook may call
the same functions; no notebook-only implementation or hosted app is required.
Keep a forced-transform strength sweep distinct from the random recipe preview.
Add `tests/test_augmentations.py` for image/label/validity alignment, label values,
photometric mask preservation, dropout-ignore behavior, band-consistent seeded
replay and the final cap. Verify that preview and training produce the same
model input for the same image and realized parameters. Use both numerical
checks and visual review before accepting the settings.

The installed Albumentations 2.0.8 brightness/contrast float path clips to
`[0, 1]`. A bounded check with brightness/contrast both zero mapped raw-equivalent
`[0, 1000, 4000, 8000]` to `[0, 1000, 4000, 4000]` after the legacy `/4000`
scale. Do not preserve that incidental cap as an implicit augmentation policy.
Use explicit supported raw-unit operations/ranges and preview them before
selection; do not silently replace them with a new unreviewed transform.

### Legacy clipping and earlier normalization audit

No explicit 5000 radiometric cap or scientific rationale was found in current
or starting-commit Planet code, relevant configuration history or tracked
documentation. Historical preview clipping was display-only. Do not describe
an intentional 5000 policy as established evidence.

The user subsequently identified the origin of the **4000** choice as
[Planet's ARPS units guidance](https://docs.planet.com/data/imagery/arps/#units).
The page specifies DN/10000 to convert to reflectance, lists 0–4000 as a
**typical** range, and permits highly reflective pixels up to 10000. This
explains the reference value but does not make 4000 a physical maximum or
recommend discarding higher values. The cited page describes ARPS products;
it is not proof of every radiometric property of this eight-band collection.
Record the user's rationale separately from the actual legacy code behavior
below. This guidance does not itself choose a cap; the user's later decision
selects 5000 and the matching rerun recorded below.

The actual v3 training sequence divides by 4000 with `ToFloat` (no clipping),
then applies `RandomBrightnessContrast` with probability **0.3**. That
augmentation's float path clips to `[0, 1]`, so the modified raw-equivalent
values are capped at 4000 when it runs. Validation/test directly standardize
the raw imagery and have no corresponding cap. `Normalize` itself does not
clip, and current cleaning/chipping do not impose a high-value cap.

Git history also records a dataset-specific normalization change at
`0596f77956b92af606d0f50ba739f5746a6ac433` (2026-05-22), using `/10000` with
raw-equivalent means `[226, 272, 318, 338, 324, 272, 444, 1065]` and standard
deviations `[267, 264, 295, 315, 342, 330, 444, 1114]`. Commit
`116164077fd00690da611d9306aabffeb33a589d` (2026-06-01) reverted that change
to Clay's values. The revert message does not explain why, and the inspected
history does not establish the exact input scope used for those estimates.

## Exact smoke and validation

- Add focused tests in `tests/test_training_settings.py`,
  `test_training_data.py`, `test_training_loop.py`, `test_model_bundle.py` and
  `test_training_resume.py`, plus `test_channel_stats.py`; extend package
  CLI/distribution checks for training, pixel statistics and augmentation previews.
- Synthetic CPU float32 cases cover each 8/4/3-band path: a real B3 forward/
  backward update, disjoint validation, save/load and resume. Keep cheap logic
  fixtures separate from bounded model integration checks; no miniature model
  may stand in for all B3 evidence. Automated cases require no network/Box/W&B.
- Exercise ignored/padded/nodata pixels, background-only targets, an all-ignored
  batch, final partial accumulation, no repeated evaluation pixels and pooled
  confusion counts with deliberately unequal chip supports. Test payload access
  fails the test immediately if attempted by training.
- Verify kelp-only eligibility excludes zero-kelp training rows while preserving
  positive rows, source assignments and background-only validation rows. Preview
  source/canonical counts separately from eligible training counts; no extra
  dataset copies or canonical-manifest rewrites are needed.
- Compare uninterrupted two-epoch tiny training with one completed epoch saved
  and resumed through epoch two, using the same total planned schedule. Compare
  model/optimizer/scheduler/progress and any averaging state within documented
  CPU tolerance. Test that model-only loading does not restore training state.
- Copy `model/` into a fresh directory and reproduce probabilities for supplied
  image arrays with no labels, original recipe path, registry, tracking service
  or pretrained download. Verify band order, normalization and true-size padding.
- Extend tiny v2 offline through a bounded real CPU update/validation/save/load/
  resume. Exercise all three spectral inputs, both variant selections and at
  least one partial edge. Small epoch/update settings must be declared; its two
  validation windows establish execution correctness, not accuracy. Run spectral
  checks sequentially, budget at most 4 GiB for new training artifacts and record
  actual bytes; optimizer/EMA checkpoints are larger than weights alone. Retain
  one representative durable bundle/recovery pair and compact results for all
  cases. Existing tiny preparation budgets stay unchanged. Do not rebuild the
  full release.
- Preview all six full-data band/variant combinations without training. Confirm
  equal evaluation membership and epoch budgets, and explicitly different
  training counts/update totals between BC variants. Metadata selection does
  not authorize reopening test arrays or repeating production QA.
- Run the focused new tests, affected existing tests and distribution checks,
  then `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run pre-commit run --all-files` and `git diff --check`. Record any
  preexisting unrelated failures. Inspect changed Markdown and relative links.

## Acceptance and non-goals

Acceptance: finalized recipe choices, one installed manifest-based training
path, portable best models and separate completed-epoch recovery pass bounded
8/4/3 checks; BC comparisons follow the user's equal-epoch policy; test arrays
stay unopened; routine bands/LR/paths/variant/checkpoint choices need no Python
edits. The installed wheel works outside the checkout. Tiny v2 demonstrates the
implemented workflow through short researcher recipes. No new hashes, receipts,
storage framework, generic model zoo or preparation recovery features.

Non-goals: production Mac/GPU training, CUDA/mixed-precision validation,
scientific accuracy claims, tuning against test results, tiled reconstruction,
threshold search, Task 035 reports, LORO suite runner, regional fine-tuning
recipes, DINOv3 or exact legacy checkpoint/training compatibility.

## Planning handoff

### Authorized normalization comparison, 2026-10-28

Completed a read-only pass over all active baseline training image payloads:
**15,621 windows / 216 sources without BC**, **18,311 / 258 with BC**. Read
shared windows once and merge their moments into both estimates. Training chip
exposures contribute 3,664,483,509 valid pixels without BC and 4,294,913,282 with
BC; these include repeated overlap, not unique source/geographic area. All-band
zero nodata and artificial padding are excluded; labels are not read, so valid
imagery with ignored targets is included. No validation/test arrays were opened.

Raw-unit mean ± sample standard deviation, rounded for discussion:

| Band | Clay | Without BC | With BC |
|---|---:|---:|---:|
| coastal_blue | 1720 ± 747 | 354 ± 294 | 323 ± 298 |
| blue | 1715 ± 698 | 411 ± 347 | 381 ± 341 |
| green_i | 1913 ± 739 | 462 ± 418 | 430 ± 409 |
| green | 2088 ± 768 | 492 ± 480 | 456 ± 467 |
| yellow | 2274 ± 849 | 498 ± 571 | 461 ± 549 |
| red | 2290 ± 868 | 500 ± 605 | 454 ± 581 |
| rededge | 2613 ± 849 | 567 ± 676 | 540 ± 651 |
| nir | 3970 ± 914 | 817 ± 1027 | 834 ± 1034 |

Clay's fixed values exactly match the legacy config after multiplying its
means/stds by 4000. The current training distribution is substantially darker
on average. This establishes a distribution difference, not which normalization
will yield better accuracy or its physical cause. The later decision above
selects the filtered with-BC reference. A reference shared between BC variants
keeps normalization fixed while changing training membership; these are
baseline-only statistics and cannot automatically become training-only LORO
statistics.

Full-precision pooled and per-region results, comparison CSV, selected training
window identities, progress log and the one-off producer are outside Git under
`/Volumes/x10pro/kelpseg/analyses/task033_normalization_train_v2/`:
`statistics.json`, `comparison.csv`, `train_windows.csv`, `progress.log`,
`compute_stats.py`. The pass read 45,139,216,937 payload bytes in 267.2 seconds
from the existing `ca_bc/v1` chip/split releases at checkout `0596ab7` plus its
current docs changes. Outputs total below 3 MiB; no new data release, model or
transfer was created. The first launcher failed on a checkout import before
reading payloads; it was corrected for the fresh `v2` analysis directory.

Validation: direct NumPy and the existing `compute_channel_stats_fast_stable`
agree on synthetic data at relative tolerance 1e-6; empty-nodata handling,
float64 raw moments, sample variance, scale cancellation and every selected
window's nonnodata count pass. Independent review found no material arithmetic
or training-scope issue. This is the user's pixel-weighted method with a
float64 calculation and explicit manifest selection, not per-chip averaging.
The older statistics entrypoint's scaling/path and variable-shape limitations
were avoided; no reusable normalization CLI is claimed to exist.

### Kelp-positive with-BC normalization follow-up, 2026-10-28

The user requested a rerun excluding chips without kelp and restricted this
analysis to the with-BC (`augmented`) variant. The modified one-off script
selects active training rows with manifest `kelp_pixels > 0`, then computes
statistics over **all nonnodata imagery pixels inside those chips**, not just
kelp pixels. Canonical payloads and training eligibility/settings are unchanged;
this analysis alone did not select the eventual normalization or training policy.
The user's subsequent decision above selects these normalization values for
training; chip eligibility remains a separate setting.

Of 18,311 available training chips, **8,518** contain kelp and **9,793** are
excluded. Selected chips represent **254 of 258 training sources** and
**2,052,580,518 nonnodata pixel exposures**, including repeated overlap.
Labels, zero-kelp chips and validation/test arrays were not opened. True-size
arrays exclude artificial padding; the same float64 pixel-weighted method and
sample standard deviation are retained.

Raw-unit mean ± sample standard deviation, rounded:

| Band | All with-BC training | Kelp-positive with-BC training |
|---|---:|---:|
| coastal_blue | 323 ± 298 | 324 ± 295 |
| blue | 381 ± 341 | 390 ± 337 |
| green_i | 430 ± 409 | 438 ± 402 |
| green | 456 ± 467 | 465 ± 460 |
| yellow | 461 ± 549 | 460 ± 543 |
| red | 454 ± 581 | 451 ± 576 |
| rededge | 540 ± 651 | 536 ± 638 |
| nir | 834 ± 1034 | 800 ± 997 |

The change is modest: means change by -4.09% to +2.28% and standard deviations
decrease by 0.91% to 3.65%. The filtered estimates remain substantially different
from Clay. This is a distribution comparison, not a model-performance result.

The updated producer and fresh outputs are under
`/Volumes/x10pro/kelpseg/analyses/task033_normalization_positive_with_bc_v1/`:
`compute_stats.py`, `statistics.json`, `comparison.csv`, `train_windows.csv` and
`progress.log`. Earlier unfiltered results are preserved. The pass read
22,000,295,988 selected payload bytes in 127.9 seconds. The comparison CSV
includes Clay, the previous unfiltered with-BC estimates and the new filtered
estimates at full precision. No without-BC rerun, transfer or model run occurred.

Validation: synthetic agreement with direct NumPy and the legacy estimator,
explicit selection checks for one kelp pixel versus zero and train versus
val/test/unused, and each selected window's nonnodata count all pass.
Independent script review found no material selection/arithmetic issue.
Repository Ruff formatting/lint and `git diff --check` pass.

### High-value counts for clipping selection, 2026-10-28

The requested pass reused the exact 8,518 kelp-positive with-BC training chips
and reconciled the same **2,052,580,518 nonnodata pixel exposures**. Counts are
strictly **greater than** each threshold, before scaling, normalization or
augmentation. Overlap repeats observations as in training; these are not unique
geographic pixel counts. Per-band percentages divide by nonnodata pixel
exposures; the any-band row counts each exposure once when one or more bands
exceed the cap. Artificial padding contributes no observations.

| Band / scope | >4000 | >5000 |
|---|---:|---:|
| coastal_blue | 0.0276% | 0.0038% |
| blue | 0.0491% | 0.0089% |
| green_i | 0.0566% | 0.0125% |
| green | 0.0618% | 0.0140% |
| yellow | 0.0602% | 0.0123% |
| red | 0.0539% | 0.0102% |
| rededge | 0.0508% | 0.0098% |
| nir | 0.5716% | 0.0681% |
| Any band | 0.6338% | 0.0846% |

Across all eight band values pooled, the rates are 0.1165% and 0.0174%; that
denominator is eight times the pixel count. NIR has the largest affected share.
These rates quantify changed inputs, not whether clipping improves accuracy.
No cap was applied or selected by this analysis.

Durable outputs and the one-off producer are under
`/Volumes/x10pro/kelpseg/analyses/task033_high_value_counts_positive_with_bc_v1/`:
`counts.json`, `comparison.csv`, `progress.log`, `count_high_values.py`.
The pass read 22,000,295,988 selected image-payload bytes in 149.6 seconds,
opening no labels, excluded chips or validation/test arrays. Counts reconcile
with the normalization scope. Synthetic exact-threshold/nodata/denominator
checks and monotonicity between caps pass; independent review found no material
scope/arithmetic issue.

The kelp-positive training requirement does **not** require changing the running
Task 032B: its canonical release already carries `kelp_pixels` for every window.
Its published train counts remain the assignment-based available windows, with
Task 033 reporting eligible/excluded training counts separately. No re-chipping,
manifest rewrite, per-fold data copy or upload change is needed. Background-only
canonical chips and validation/test selection stay intact.

### Selected 5000-capped normalization outcome, 2026-10-28

The user selected an upper cap of **5000** and requested a new normalization
pass. The same **8,518 kelp-positive with-BC training chips / 254 sources**
contribute **2,052,580,518 nonnodata pixel exposures**. All nonnodata image
pixels in selected chips contribute, including their background and repeated
overlap. Detect native all-band-zero nodata first, cap temporary image values
at 5000, then accumulate float64 moments and sample standard deviation.

| Band | Mean after cap | Sample std after cap |
|---|---:|---:|
| coastal_blue | 323.648782 | 294.978813 |
| blue | 389.531769 | 336.149566 |
| green_i | 438.396463 | 401.687019 |
| green | 465.357960 | 459.221705 |
| yellow | 459.942047 | 541.919411 |
| red | 451.304510 | 575.332008 |
| rededge | 536.260634 | 637.086876 |
| nir | 799.221582 | 994.569555 |

Full-precision selected values are in the current normalization block above;
these six-decimal table entries are for reading. Relative to the earlier
unclipped positive-chip estimate, means decrease by 0.0044–0.0365% and standard
deviations decrease by 0.0767–0.2160%. Earlier estimates are preserved for
comparison and superseded for the new recipes.

The updated producer, exact selected-window CSV, full-precision results,
comparison CSV and log are under
`/Volumes/x10pro/kelpseg/analyses/task033_normalization_positive_with_bc_clip5000_v1/`:
`compute_stats.py`, `train_windows.csv`, `statistics.json`, `comparison.csv`,
`progress.log`. The pass read 22,000,295,988 selected image-payload bytes in
130.4 seconds. It opened no labels, excluded chips or validation/test arrays,
and made no source-payload changes. It did not rerun the without-BC variant.

Checks pass: exact cap boundaries 4999/5000/5001/65535, nodata handling,
agreement with direct clipped NumPy and the legacy estimator on clipped
synthetic values, unchanged selected chip/pixel scope, and normal decreased
means/standard deviations under the cap. Independent script review found no
material numerical or scope issue. The selected constants and cap in this
task are checked against the completed result at full precision.

Task 032B's final publication/restore handoff has been read and the prerequisite
is satisfied. Finalize the remaining augmentation settings/preview plan, then
select this task for implementation in a new window. Only then change this task
to `In progress` and align the current queue. No training implementation or
production model run was started during these planning analyses.

## Outcome template

- Final recipe decisions and any bounded scope adjustment:
- Changed repo files and removed obsolete code/options/dependencies:
- External tiny runs, portable bundles and recovery checkpoints:
- Focused/installed/real-data validation and limits:
- Simplicity check and remaining issues:
- Exact next action: select Task 034 to implement image-only tiled inference
  from this bundle and shared preprocessing; do not start it in this window.
