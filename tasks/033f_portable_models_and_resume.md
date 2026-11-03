# Task 033F: Portable models and completed-epoch resume

Status: Complete and approved — 2026-11-03; user authorized closure and commit.
Depends on: Completed 033E training/state writing and 033D model construction.

## Abstract

Export a self-contained selected model and implement narrow same-run recovery.
Stop before georeferenced/tiled inference and scientific scoring.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
Shared parent, 033E saved-state layout, [experiments](../docs/experiments.md),
[architecture](../docs/architecture.md) and the legacy EMA save/load findings.

## Outputs and implemented interface

Implemented small bundle/checkpoint helpers and `tests/test_model_bundle.py`,
`tests/test_training_resume.py`. A copied `model/` holds `weights.pt` and
`model.json` with architecture, ordered bands, cap5000, normalization, input/
padding/nodata policy, threshold and EMA identity. The resume interface uses
the existing recipe-led CLI (`train --recipe ...`): TOML owns `name`,
`experiment`, `variant` and `paths_file`; fresh runs receive name-prefixed UTC IDs.
Resume preserves the saved run identity rather than generating a fresh one.
Current native Lightning states are `checkpoints/best.ckpt` and `last.ckpt`, with
validation weights in `state_dict`, ordinary weights in `current_model_state`
and separate `averaging_state`. Native Trainer/checkpoint mechanisms and
the distinct best/last callbacks remain in place. The researcher guide documents
save/load/resume.
The implemented interface is `train --recipe ... --resume <run>/checkpoints/last.ckpt`.
Exact resume requires `num_workers=0`; fresh multiworker training remains supported.

## Plan/spec

Bundle loading constructs the model with no pretrained fetch or original
recipe/registry path. Restore optimizer, scheduler, ordinary weights, EMA,
progress and relevant random/sampling state for same-run completed-epoch resume.
Saved settings own the run identity/budget; reject changed bands, memberships or
recipe. Restart a partial epoch from its last completed checkpoint; no mid-batch
recovery framework. Model-only initialization is distinct from resume and does
not restore optimizer/progress. No general adaptation recipes in this task.

## Implementation plan — 2026-11-03

- Add `model_bundle.py`: selected checkpoint export, self-contained JSON/weights,
  and offline image-array loading with shared preprocessing; no raster tiling.
- Add `training/resume.py`: a small Lightning callback for identity and RNG state,
  leaving optimizer, scheduler, progress and EMA restoration to native Lightning.
  Exact continuation supports `num_workers=0`; persistent worker augmentation
  streams cannot be restored through the native checkpoint. Fresh multiworker
  training remains supported. No alternate sampling or recovery framework.
- Extend the recipe-led train command with `--resume .../checkpoints/last.ckpt`.
  Preserve saved identity/budget and compare plain selected metadata, allowing
  explicit root relocation. Export `model/` from best after successful fitting.
- Verify copied bundles, early and active EMA continuation, identity errors,
  test isolation, installed distributions/lazy imports and required checks.

## User decisions required

No new scientific choice. Keep the selected inference weight kind and narrow
recovery boundary; machine roots can relocate explicitly without changing data
or recipe identity.

## Smoke and validation

Copy a bundle to a fresh unrelated directory and reproduce supplied image-array
probabilities without labels, original config paths, W&B or a weight download.
Compare uninterrupted two-epoch tiny training against a completed-epoch save/
resume with the same total schedule, including optimizer/scheduler/progress/RNG/
EMA state within documented CPU tolerance. Cover 8/4/3 bundles and meaningful
resume identity errors. Run affected distribution checks and required lint.

## Acceptance and non-goals

Copied models and completed-epoch resume are verified separately. No label
alignment dependency, hidden online service or georeferenced-inference claim.
Do not start another numbered task in this window. The bundle helpers and resume command are implemented; tiled/georeferenced
inference remains outside this task.

## Outcome template

- Changed repository files and removed obsolete options/dependencies:
- Durable external artifacts:
- Validation and limits:
- Simplicity check and unresolved issues:
- Exact next action: 033G: rehearse the installed tiny workflow and prepare the Task034 handoff.

## Outcome — 2026-11-03

- **Implementation:** added `model_bundle.py` and `training/resume.py`; extended
  the recipe-led train CLI/runner and fixed the pre-EMA checkpoint counter to a
  tensor for native restoration. Added bundle/resume tests and expanded runner
  and installed-distribution checks. Updated README, guide, architecture,
  experiments, index, shared decisions and queues. No dependencies added or
  unrelated legacy implementations removed.
- **Portable models:** successful fitting exports best validation weights to
  `model/weights.pt` and `model/model.json`. JSON records architecture, named
  bands, exact cap/normalization, 512 bottom/right padding, native nodata,
  threshold, run identity and current/EMA selection. Offline loading constructs
  B3 without pretrained weights. Image-array prediction requires native HWC
  uint16 input up to 512 square, returns original-size probabilities and NaN
  at native nodata, and never requires labels. This is not tiled inference.
- **Resume:** native Lightning restores optimizer, scheduler, loops/progress and
  ordinary/EMA weights. A small callback saves missing global/loader/stock
  Albumentations random state and plain settings/membership/native-band identity.
  Resume rejects changed recipes/budgets/identities, best/partial/old checkpoints
  and exhausted runs. Relocated complete run folders retain best score/path and
  saved run ID. Separate native CSV logger folders preserve earlier metrics.
  No custom training loop, alternate sampling policy, hashing or recovery system.
- **Durable evidence:** `/Volumes/x10pro/kelpseg/analyses/task033f_checks_v1/`
  contains a real B3 model exported from the existing 033E best checkpoint,
  its unrelated-directory copy, synthetic native image, probability arrays and
  `bundle_smoke.json`/log. The copied model reproduces probabilities bitwise
  (`max_abs_error=0`) with networking blocked, missing original recipe paths
  and no labels. These artifacts use less than 400 MB before the tiny resume
  files. Existing 033E artifacts remain unchanged.
- **Resume evidence:** its `resume/` subfolder retains interrupted epoch-0,
  uninterrupted and resumed checkpoints plus `evidence.json`. A stochastic
  tiny CPU model completes two epochs of 102 updates: EMA counts 2 at
  interruption and 104 at completion. Ordinary/selected/EMA tensors, optimizer,
  scheduler, progress, Python/NumPy/Torch RNG, both loader generators and
  recursive augmentation RNG match bitwise (`atol=rtol=0`). A separate early
  EMA fixture verifies the same boundary before averaging starts. This proves
  bounded CPU continuation, not production CUDA equivalence.
- **Validation:** 115 focused bundle/resume/runner/settings/loop/data/objective,
  CLI and installed-distribution tests pass. Isolated wheel and rebuilt-sdist
  runtime installations both execute copied-bundle prediction; lazy CLI imports
  pass. Nine resume/runner tests also pass after tightening native-band/canvas
  identity checks. Coverage includes native8, RGB+NIR, NIR/R/G and RGB bundles,
  early/current versus EMA selection, zero test-payload reads, ordinary identity
  errors and copied-run relocation. Ruff format/check, broad pre-commit plus
  explicit new-file pre-commit checks, Markdown file links and `git diff --check`
  pass. No unrelated failure observed; warnings are native CPU/worker/checkpoint
  notices and a Lightning pytree deprecation.
- **Simplicity and limits:** routine use stays in flat TOML plus `--resume`.
  Exact continuation requires `num_workers=0`; live persistent-worker streams
  are not restored. Native multiworker fresh training remains available. Old
  033E checkpoints can export models but lack exact-resume state. Model-only
  bundle loading restores no optimizer/progress; adaptation recipes remain
  deferred. CUDA/bf16 and optional live W&B are unverified. No test payloads,
  production training, tiled inference or Task 033G work were introduced.
- **Exact next action:** select 033G in a new chat to rehearse the installed tiny
  workflow, prepare the six production previews and Task 034 handoff. Stop here.
