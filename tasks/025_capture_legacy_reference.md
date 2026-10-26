# Task 025: Capture a small legacy checkpoint reference

Status: Pending

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
