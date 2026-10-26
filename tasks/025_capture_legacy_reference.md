# Task 025: Capture a small legacy checkpoint reference

Status: Complete

Depends on: Task 024.

Execution: Local CPU inference and external reference artifacts; no training.

## Abstract

Capture five or six representative chips, their original inputs and labels,
and the downloaded checkpoint's predictions before removing legacy code. This
is a visual gut check for the rebuild, not a requirement to reproduce a full
training run, match GPU arithmetic, or maintain the old APIs.

## Inputs

- Reference commit `ac933fd667c2ddb445b8a622d8404387a2d056e2`.
- Checkpoint:
  `/Users/kyledorman/Downloads/kelp_ps8b_segformer_b3_epoch-62_val-iou-0.7047.ckpt`.
- Existing chips and manifest at
  `/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1`.
- `configs/kelp-ps8b/generalization/segformer_b3_v3.yaml` test preprocessing.
- Legacy model, EMA callback, predictor, and centered-padding regression tests.

## Expected outputs

A new immutable package outside Git under
`/Volumes/x10pro/kelpseg/references/legacy_ps8b_v1` containing:

- An unchanged checkpoint copy and its hash, plus the reference config.
- Exact sample IDs, selection reasons, source windows, regions, and dimensions.
- Original eight-band inputs and labels, float32 probabilities, and masks.
- Per-chip RGB/label/probability/prediction panels distinguishing ignored pixels.
- A compact JSON manifest, payload hashes, runtime/device/precision details,
  exact producer invocation, and a short human-readable explanation.

## Implementation contract

1. Select samples using manifest properties before viewing predictions. Cover
   CA and BC, dense and sparse foreground, background, nodata, and at least one
   undersized chip. Prefer train/validation sources for implementation examples.
   These are diagnostic examples, not a representative accuracy estimate.
2. Record chosen IDs before inference. Keep complete source chips without
   resizing. Do not modify their inputs, labels, or existing manifests.
3. Use CPU float32 and batch size one as the required path. MPS is optional.
   Use `uv run --no-sync` for the bounded capture in the existing environment;
   ordinary `uv run` may synchronize it before executing. Record installed
   versions and differences from the lock. Repair the environment deliberately
   only if needed to run inference; avoid unrelated dependency upgrades.
4. Inspect the checkpoint/EMA semantics before loading. Legacy inference uses
   checkpoint `state_dict`; ordinary training weights may also be saved under
   `current_model_state` and must not be substituted silently. Constructing the
   architecture with `encoder_weights=None` avoids downloading ImageNet weights
   that the checkpoint will replace; load model state strictly and record it.
5. Use the legacy deterministic test transform, including band normalization,
   centered padding and ignore fill `-100`. Invert padding explicitly; verify
   the cropped transformed label equals the original. Save original-footprint
   probabilities and masks at threshold `0.5`.
6. Keep this bounded capture independent of a training registry or completed
   LORO suite. A recorded `uv run` Python invocation is sufficient; do not add
   a new `scripts/` workflow or prematurely build the production package here.
7. Refuse silent overwrites. On interrupted work, verify existing payload
   identities before continuing; publish a completion manifest only after QA.

## User decisions required

None by default. Use the stated local root and deterministic sample criteria.
If an ambiguous input or unavailable artifact prevents a trustworthy capture,
report the concrete discrepancy rather than inventing metadata.

## Plan/spec

Before running inference, record sample IDs, output layout, transform and
checkpoint-loading choice in this task. Keep execution notes here and large
results outside Git. Do not broaden into data cleanup or model refactoring.

## Smoke and validation

### Pre-inference execution plan (2026-10-26)

Selection was written to the external `sample_selection.json` before inference.
Only `TRAIN`/`VAL` sources from `planet8b_temporal_image_splits.csv` were eligible
(3,939 of 4,602 canonical chips). Deterministic manifest-only selection; ties
use chip ID in the same min/max direction as the ranking:

| Chip ID | Split | Selection reason |
|---|---|---|
| `008_20211001_185129_227b__r512_c512_h1024_w1024` | TRAIN | CA maximum foreground fraction among non-ignored pixels |
| `20210812_184548_90_2448_3B_AnalyticMS_SR_8b_harmonized_clip5__r1536_c512_h1024_w1024` | VAL | BC maximum foreground fraction among non-ignored pixels |
| `004_20210428_175742_2441__r1536_c4096_h1024_w1024` | TRAIN | CA positive foreground fraction closest to 1% of full footprint |
| `20210811_184459_09_245c_3B_AnalyticMS_SR_8b_harmonized_clip1__r0_c0_h1024_w1024` | TRAIN | BC zero foreground, minimum nodata then lexical ID |
| `20210812_184548_90_2448_3B_AnalyticMS_SR_8b_harmonized_clip1__r1024_c0_h1024_w1024` | VAL | BC maximum retained development-chip nodata (49.9557%) |
| `007_20210804_175250_2453__r0_c0_h672_w1024` | VAL | CA smallest undersized footprint then lexical ID (672 × 1024) |

The unchanged checkpoint/config, canonical chip manifest, temporal assignments,
lock/environment specification, and relevant legacy source snapshots are copied
under `legacy_ps8b_v1/provenance/`. Each `samples/<chip_id>/` will contain an
unchanged `original.npz` (eight-band input and label), float32 `probability.npy`,
uint8 `mask.npy`, `panel.png`, and a hash-bearing `receipt.json`. Repeat the
undersized chip with absolute tolerance `1e-6` and preserve its repeat output.
Publish `manifest.json` only after payload checks and recorded visual QA.

Construct `SMPBinarySegmentationModel` from checkpoint hyperparameters with
`encoder_weights=None` and `ckpt_path=None`; strictly load `state_dict`.
Inspection found 588 state entries, all differing from `current_model_state`.
Installed Lightning's `WeightAveraging.on_save_checkpoint` confirms that
`state_dict` holds EMA inference weights and `current_model_state` holds ordinary
training weights. Do not restore a Trainer or training callback.

Deserialize the config's deterministic `test_transforms`: centered constant
padding to 1024, image fill 0, label fill -100, eight-band normalization with
`max_pixel_value=4000`, then `ToTensorV2`. Use CPU float32, batch one, four CPU
threads, no autocast, eval/inference mode, sigmoid, and mask `probability >= 0.5`.
Use the existing checked center-crop helper and independently check normalized
image placement. The 672-row chip needs 176 rows of padding at both top/bottom.
Source TIFF descriptions are absent; keep source bands 1–8 unchanged. Previews
use bands 6/4/2 under the conventional Planet RGB ordering, with a display-only
2–98% stretch; this does not independently establish physical band identities.

Producer phases, invoked from the repository with the existing environment:

```bash
uv run --no-sync python /Volumes/x10pro/kelpseg/references/legacy_ps8b_v1/producer.py select
uv run --no-sync python /Volumes/x10pro/kelpseg/references/legacy_ps8b_v1/producer.py capture
uv run --no-sync python /Volumes/x10pro/kelpseg/references/legacy_ps8b_v1/producer.py finalize
```

All three phases completed. The producer refuses overwrites and
verifies existing completed sample receipts before reuse. Runtime provenance
includes installed versions and every difference from `uv.lock`; no
environment synchronization or repair occurred.

### Required checks

- Reopen every saved input/label and check unchanged array content and hashes.
- Probabilities must be finite in `[0,1]` and match original spatial dimensions.
- Masks must equal the documented threshold applied to saved probabilities.
- Check inverse padding on every undersized sample and visually inspect panels.
- Repeat one chip and record agreement within a documented small tolerance.
- Inspect artifact manifest completeness and run `git diff --check`.
- If source changes become necessary, run focused tests and required Ruff
  checks; document existing unrelated failures rather than hiding them.

## Acceptance criteria

The external package reopens independently and contains all inputs, labels,
predictions, previews, provenance, and payload hashes. No particular IoU or
GPU-equivalence result is a completion gate. No training is launched.

## Non-goals

Full baseline reproduction, model tuning, whole-dataset evaluation, Box
transfer, new package design, data cleanup, or legacy source removal.

## Outcome template

Record sample IDs, checkpoint hash and loading semantics, changed repo files,
external package path and verification, visual QA, unresolved issues, and exact
next action: scope Task 026's original-data and cleanup-provenance inventory.

## Outcome (2026-10-26)

Captured all six preselected chips at
`/Volumes/x10pro/kelpseg/references/legacy_ps8b_v1` and published its atomic
`manifest.json` after numerical and visual QA. `README.txt` explains the saved
arrays and previews; `verify_package.py` reopens the package using only relative
paths, NumPy, and Pillow. The 53-file package totals 807,971,035 bytes; files and
directories have read-only permissions. The original dataset and manifests were
unchanged. No training, model tuning, dependency repair, or Box transfer ran.

- Checkpoint SHA-256:
  `5bfb20d1b388fe76a97d7a6d9e8ab728c1cef52c5763968751eeec79c14b437f`.
  The copied checkpoint matches the download. All 588 `state_dict` entries
  loaded strictly and equal the loaded module state; the 588 differing
  `current_model_state` entries were unused. Epoch 62, global step 5,544,
  saved Lightning 2.6.1. No pretrained-weight download occurred.
- Runtime: Python 3.12.11, PyTorch 2.12.0, torchvision 0.27.0, SMP 0.5.0,
  Albumentations 2.0.8, Lightning 2.6.1, NumPy 2.4.4; CPU float32, batch one,
  four computation threads, one interop thread, deterministic algorithms.
  All installed distributions match versions where present in the lock.
  `runtime.json` enumerates 233 installed distributions and 31 absent lock
  entries (CUDA/Windows-specific packages and the uninstalled local project);
  no additional distributions or installed-version mismatches were found.
- Reopened each saved `original.npz`, compared both arrays to source content,
  and verified byte hashes. Label counts, nodata counts, dimensions, and dtypes
  match the selected canonical rows. Saved probabilities are finite float32 in
  `[0,1]`, at the original footprint; masks exactly equal `probability >= 0.5`.
  Ignored pixels remain identifiable from labels and magenta preview overlays;
  raw predictions are preserved even on ignored pixels.
- Verified the transformed label crop equals the original for every chip,
  image normalization/placement independently matches source pixels, and
  padded image/label fills are correct. The undersized chip uses top/bottom
  padding of 176 rows and saves 672 × 1024 outputs. Its saved repeat probability
  is bit-for-bit identical (maximum absolute difference `0`, tolerance `1e-6`)
  with identical threshold masks.
- Visually inspected all six saved panels through `view_image`. Dense beds,
  sparse patches, and nodata boundaries align without an apparent translation;
  the background example has an entirely background prediction. Local boundary
  and small-component disagreements are preserved. The undersized preview has
  its original aspect ratio and no residual padded strip or vertical shift.
  Per-sample observations are recorded in `visual_qa.json`; this records agent
  visual inspection, not human sign-off or an accuracy estimate.
- Focused regression:
  `uv run --no-sync pytest -q tests/test_evaluate_planet8b_run.py -k center_padded`
  → **4 passed, 8 deselected**. Model, EMA callback, predictor, reference config,
  and alignment tests have an empty diff against reference commit
  `ac933fd667c2ddb445b8a622d8404387a2d056e2`; execution commit was
  `fdff6c1ef41d211169dbaacad56ea4dce935bfdd`.
- Standalone verification from `/private/tmp`, with isolated Python import paths:
  `uv run --no-sync --project /Users/kyledorman/Documents/UCLA_kelp/hakai-ml-train python -I /Volumes/x10pro/kelpseg/references/legacy_ps8b_v1/verify_package.py`
  → **PASS: 51 payload hashes**, six original pairs/probabilities/masks/previews,
  and repeat tolerance; no repository imports or original-data access.
  `manifest.sha256` separately protects the completion record. No partial
  payloads remain. Exact producer phases are preserved above and in provenance.
- Changed repository files: this task, `tasks/README.md`, `docs/todo.md`, and
  `docs/data_artifacts.md`. Implementation, environment, and configuration files
  were unchanged. Documentation links and `git diff --check` passed.

Limitations: TIFF band descriptions are absent, so the display's RGB 6/4/2
convention is not an independent physical-band verification. The saved inputs
retain all eight source bands unchanged. Producer re-execution needs the legacy
repository and original paths; artifact reopening/verification is independent.
No unresolved issue blocks this bounded reference. These development examples
support no held-out accuracy or CUDA-equivalence claim.

Simplicity check: the capture stays an external one-off Python invocation and
plain files; no new repository `scripts/` workflow, package, registry dependency,
or obsolete-code removal was introduced. The reusable researcher walkthrough
remains deferred until Box and the cleaned release are established.

Exact next action: scope Task 026's original-data and cleanup-provenance
inventory. Stop here; Task 026 has not started.
