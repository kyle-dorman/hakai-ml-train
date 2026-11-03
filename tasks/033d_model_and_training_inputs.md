# Task 033D: Model and training inputs

Status: Complete — 2026-11-02; affine previews approved and commit authorized. Implementation explicitly authorized by the user,
superseding the original documentation-only status.
Depends on: Completed 033A–033C and selected 033B augmentation policy.

## Abstract

Connect manifest-selected data and shared preprocessing to one SegFormer B3.
Implement loss/confusion helpers and bounded updates; stop before an epoch runner,
tracking, checkpoints or resume.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
Shared parent, selected augmentation recipe, 033A preprocessing/functions,
`chips.py`, `bands.py`, `select_windows`, retained model/loss code and
[architecture](../docs/architecture.md), [experiments](../docs/experiments.md).

## Outputs and interface

Implemented `src/kelpseg/models.py`, `training/data.py`, `training/loss.py` and
`training/metrics.py`; focused model/data/loss tests. Promote actual Torch/SMP
runtime dependencies and update installed-distribution expectations. No new
public train command or model zoo yet.

## Plan/spec

Reuse the shared cap/normalization/augmentation path; never copy it into a
second loader. Select `train` plus positive kelp count, retain disjoint val and
metadata-only test identities. Preserve native validity, -100, true extents,
band order and source identity. Construct only SegFormer B3/mit_b3, one logit;
record actual pretrained channel adaptation. Keep the selected smoothed-BCE /
Lovasz objective, handle empty support and sum confusion counts before ratios.
Do not remove retained legacy evaluator imports before their replacement exists.

## User decisions required

Model family, loss, band selections and preprocessing are settled. Use
no-download initialization in automated cases; verify generic ImageNet loading
separately with cached weights or an explicitly recorded initial fetch.

## Smoke and validation

Synthetic CPU float32 forward/backward for real B3 on 8/4/3 paths; partial
edges, background-only/ignored loss cases, pooled confusion counts and a test
payload access guard. Verify training positivity affects train only. Run affected
installed-distribution and lazy-import checks, Ruff format/check and broad
pre-commit if this is a broad code change. Record limits; no CUDA claims.

## Acceptance and non-goals

All spectral inputs can make a bounded optimizer update through the shared
path without test reads, legacy class-path config or a training runner.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Outcome — 2026-11-02

- **Implementation:** `models.py` constructs only SMP SegFormer B3/mit_b3,
  3/4/8 inputs, one full-resolution logit. `training/data.py` joins the existing
  selector to Torch datasets, keeps only positive training rows, preserves
  representative validation and returns test identities as metadata only.
  `training/loss.py` implements 0.7 smoothed BCE / 0.3 batch-pooled Lovasz hinge
  with smoothing 0.1, -100 handling and differentiable zero for empty support.
  `training/metrics.py` builds a native TorchMetrics MetricCollection for pooled
  confusion/IoU/precision/recall/F1/accuracy. Undefined ratios use library zero
  semantics; the confusion matrix records scored support.
- **Shared preprocessing:** native validity is computed by `load_chip` before
  band selection. Stock augmentation receives only selected model-input bands,
  restricting dropout without a custom transform. Band-named normalization
  retains the approved constants and final 5000 cap. `training/transforms.py`
  builds a full Albumentations Compose with ToFloat, approved augmentation,
  raw-unit cap, Normalize, invalid-fill restoration and ToTensorV2. The dataset
  calls this pipeline once; `apply_augmentation` remains a preview adapter.
  Source identity, true extents and original padding stay in sample metadata;
  transformed validity handles training D4 movement. No debug-package imports.
- **Packaging/documentation:** Torch, TorchMetrics and SMP are promoted from legacy to runtime
  dependencies in `pyproject.toml`/`uv.lock`; installed wheel/sdist expectations
  cover the new modules and objective/metric execution. Updated the quickstart,
  README, index, architecture/experiment descriptions, shared Task 033 and queue.
  Retained legacy evaluators and their imports remain needed by later tasks;
  no legacy implementation or compatibility option was removed here.
- **Focused checks:** 15 data tests, 17 model/objective tests, and 119 existing
  augmentation/split/CLI tests pass. Real B3 optimizer updates ran sequentially
  for all/eight, RGB+NIR/four and RGB/three with CPU float32, synthetic 57×61
  native chips padded to 64×64, approved augmentation, finite gradients and
  changed first-layer parameters after SGD. Automated cases block download
  entry points and explicitly use `encoder_weights=None`.
- **ImageNet check:** separate `HF_HUB_OFFLINE=1` construction/forward checks
  passed sequentially for 8/4/3. Compared the first input convolution exactly
  with cached RGB kernels repeated cyclically and scaled by 3/channel-count;
  three channels remain unchanged. Also checked a deeper encoder weight.
  This is positional initialization, not a physical-band pretrained mapping.
  Preexisting cache: `/Users/kyledorman/.cache/huggingface/hub/models--smp-hub--mit_b3.imagenet/snapshots/32558d12a65f1daa0ebcf4f4053c4285e2c1cbda/model.safetensors`
  (178,393,776 bytes). **No initial weight download was needed.**
- **Repository checks:** isolated wheel and sdist runtime installs and lazy CLI
  imports pass; Ruff format/check, broad pre-commit and `git diff --check` pass.
  Relative Markdown file links resolve in every changed document.
- **Real release check:** all three selections reproduce 18,311 training
  candidates, 8,518 eligible, 9,793 zero-kelp exclusions, 933 validation windows
  and 1,262 metadata-only test identities. Loaded one actual 512×512 training
  and validation sample per spectral selection, six total payload reads under
  an explicit train/validation-only access guard. No test payload was opened.
- **Durable external artifacts:** the affine review gallery below; no checkpoint
  or production run. The preexisting ImageNet cache was consumed without download.
- **Limits/simplicity:** small ordinary functions and one Dataset reuse the
  existing selector, loader, factory and normalization; no new schema, hashing,
  receipts or recovery machinery. No epoch runner, public train command, EMA,
  tracking, checkpoints/resume or production training. Bounded 64-square model
  checks do not establish 512-square training memory, CUDA or throughput.
  An independent review found no actionable correctness or scope issues.
- **User review revisions:** replaced custom metric counts/ratios with native
  TorchMetrics, including pooled state, reset and ignore tests. Replaced the
  dataset's direct adapter/NumPy/Torch conversion sequence with one full
  Albumentations pipeline using Normalize and ToTensorV2. Two small transforms
  restore raw units/cap and validity fill; stock operations own normalization
  and tensor conversion. Shared constants are unchanged; stock float32 output
  matches the prior NumPy reference within `rtol=atol=1e-6` (observed maximum
  absolute difference about 9.54e-7). The saved augmentation JSON still matches
  its stock factory exactly. Reran sequential real B3 updates and guarded real
  input checks after this revision. These revisions were reviewed before the user authorized a commit.
- **Exact next action:** start Task 033E in a new chat using Lightning and the
  confirmed band recipes/historical values in its updated contract. No 033E
  implementation was started here.

## Affine preview revision — 2026-11-02

The user selected a light stock Affine stage between D4 and SomeOf, outside
its eight-operation pool: p=0.5, isotropic scale 0.95–1.05, independent x/y
translations ±16 pixels, no extra rotation/shear, fixed output canvas, bilinear
imagery and nearest-neighbor masks. Constant fill is image zero / mask -100.
The same factory feeds training and previews, and `baseline.json` was regenerated.

Preview code now renders source, D4-only, D4+Affine and full-pipeline states.
Geometry references replay actual sampled stock parameters rather than drawing
again. Close-up footprints follow both geometric transforms. The viewer offers
**Inspect affine** and **Inspect full pipeline**, reports applied/skipped state,
actual scale and shifts, and starts on an affine-applied draw. The example,
shared decisions, researcher guide and experiment description reflect this order.

Gallery: `/Volumes/x10pro/kelpseg/analyses/task033d_affine_pipeline_previews_v1/index.html`.
It contains the identical 16 training examples used in Task 033B (14 positive
and two diagnostic backgrounds), eight draws each: 128 draws, 68 affine applied
and 60 skipped, 453,696,057 bytes total. No held-out payloads were opened.
Earlier galleries remain unchanged. The user approved these outputs.

Validation: 55 training-data/model/adapter tests, 20 pipeline/gallery tests,
and 28 geometry/display/CLI tests pass. The sequential real B3 update cases now
use seed 7, which applies affine, for every 8/4/3 input. Installed wheel/sdist
checks, Ruff, pre-commit and whitespace checks pass. Chromium rendered the real
gallery without runtime errors; isolated/full mode switching and enlarged
close-ups were exercised and screenshots visually inspected. The user authorized
committing the reviewed implementation based on `be2e8ce`.
No epoch runner or Task 033E implementation was added; only its handoff contract
was updated with the user's Lightning, spectral-recipe and historical-setting
directions. Existing three-channel RGB checks remain accurately recorded;
NIR/R/G recipe coverage belongs to 033E.
