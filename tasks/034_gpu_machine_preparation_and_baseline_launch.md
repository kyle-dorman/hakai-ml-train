# Task 034: GPU machine preparation and baseline launch

Status: In progress — 2026-11-03. Linux setup, CUDA/bf16, staged data,
tiny training, portable loading and deterministic completed-epoch continuation
pass. The user stopped the ten-epoch pilot and requested throughput tuning.
Seventeen benchmark cases and ordinary multiworker GPU resume checks pass;
the user completed the twenty-epoch fast pilot and validation/EMA review.
Logging diagnostics are ready with changes uncommitted; longer-run recipe
selection and Box backup remain pending.
The user selected remote-first implementation: finish the small entry checklist
locally, then test and iterate on the external machine.
Depends on: Completed Task 033A–G, published CA/BC chips and tiny v2.

## Abstract

Make the current installed baseline runnable on an external GPU machine before
waiting for tiled inference, scoring or the final researcher handoff. Replace
the old machine/data setup path with a short, explicit procedure using the
locked package, published Box chips and flat training recipes. Draft the entry checklist and simple bootstrap locally, then test and iterate on the actual host
and start one baseline once its hardware checks pass. Local Task 035 development
can proceed while that baseline trains against its pinned code and settings.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then this contract and:

- [Quickstart](../docs/quickstart.md): installation, machine paths, full-release
  Box restore, tiny-v2 walkthrough, train previews, portable models and resume.
- [Experiments](../docs/experiments.md), [architecture](../docs/architecture.md),
  [data artifacts](../docs/data_artifacts.md) and [Box backup](../docs/box_backup.md).
- [Shared 033 decisions](033_baseline_training_and_portable_models.md), the
  [033E](033e_training_validation_and_ema.md),
  [033F](033f_portable_models_and_resume.md) and
  [033G](033g_tiny_walkthrough_and_handoff.md) outcomes.
- `pyproject.toml`, `uv.lock`, `configs/paths.example.toml`, `configs/train/`,
  `src/kelpseg/training/settings.py`, `run.py`, `resume.py` and the CI workflow.
- Audit `scripts/bootstrap_skypilot.sh` and
  `scripts/prepare_remote_planet8b_dataset.sh` as legacy references only.
  Read Tasks 010/014A/014B only for useful setup/launch lessons, not current
  dataset paths, environments, credentials or evidence that an old host exists.

The published Box inputs are `data/chips/ca_bc/v1`, `data/splits/ca_bc/v1`,
`data/collections/ca_bc/v1` and `data/examples/tiny_ca_bc/v2`, beneath
`kelp-box:kelpseg`. Training does not require restoring raw ZIPs or cleaned TIFFs.
The full chips occupy about 65.6 GB; budget additional environment/cache, run and
checkpoint space using the actual host. G's smoke bundles/checkpoints are
recreatable test artifacts and are not required uploads or relocation inputs.

## Outputs and planned interface

- `bootstrap_gpu.sh`: simple post-clone Ubuntu/Debian package updates and tool
  installation, explicitly requested by the user; no new `scripts/` directory.
- `docs/gpu_setup.md`: one short operating guide from fresh host to a running
  baseline, with machine settings, expected results, failure actions, completed-
  epoch continuation and explicit output backup. Link it from quickstart/index.
- Ordinary tracked settings examples where needed, using the existing
  `configs/paths.example.toml` and `configs/train/*.toml` conventions. Keep real
  machine roots in ignored local TOML; any new GPU smoke recipe belongs under
  `configs/train/`. Do not copy normalization into another schema.
- Small package/test/lockfile fixes only where setup rehearsal demonstrates a
  real gap. No replacement shell-script directory or provisioning framework.
- A committed local handoff, followed by recorded remote corrections, exact
  setup/code versions, smoke results and the selected production run location.
  Runtime logs/checkpoints remain external; concise evidence belongs here.

Reuse `kelpseg check-paths --paths <file>` and
`kelpseg train --recipe <file> --dry-run`, then the same command without dry-run.
Use existing `--resume <run>/checkpoints/last.ckpt` for completed-epoch resume.
These commands exist. The setup guide is a locally checked draft; hardware
validation and tested GPU launch commands remain remote work.

## Plan/spec and implementation contract

Before editing implementation, mark local work in progress and record a bounded
plan of files, commands and checks here. Keep local readiness and remote
validation/launch as separate milestones; do not claim CUDA success from Mac tests.

### Local checklist and remote-first handoff

1. Write `docs/gpu_setup.md` in the user's order: Tailscale login, Sky API login
   to `http://skypilot01.tail8e8be8.ts.net:30050`, `sky launch --gpus RTX3090`,
   SSH using the allocated alias, clone the repository, bootstrap Linux, Box
   login, tiny/full data download, and W&B login. Mark `sky-79fd-kyledorman` as
   an example rather than an existing allocation.
2. Add one root `bootstrap_gpu.sh`: apt update/upgrade (explicitly requested),
   Linux dependencies, rclone, tmux, uv, Codex, Python 3.12 and frozen sync.
   Keep authentication interactive in the guide. No driver replacement or
   production launch in the bootstrap. Validate syntax, platform refusal and
   fail-fast sequencing with mocks; do not run machine updates on the Mac.
3. Reuse published Box paths with fresh destinations and explicit machine roots.
   Do not carry over old Google Drive archives, receipt machinery, compatibility
   symlinks or class-path configurations. Preserve original/source assignments.
   No Task 033G smoke-model uploads are needed. Retire legacy setup consumers
   only when their replacements have been checked on the actual host.
4. Commit/push the local entry guide before cloning remotely. Linux dependency
   installation, CUDA, batch sizing and integrated rehearsal belong on the GPU
   host. Reuse Task 033G CPU evidence rather than repeating it to imply Linux
   readiness. Keep host corrections in Git and bring them back locally.

### Remote validation, iteration and one baseline

1. On the selected host, record OS/architecture, GPU/VRAM, driver, Torch/CUDA,
   Python/uv versions, persistent storage roots and available space. Install the
   committed environment; check CUDA allocation and bf16 support on that device.
   Verify the generic ImageNet initialization download/cache required for a new
   baseline. Use documented fixes and commit any changes before production.
2. Run bounded real training/validation/save/load on tiny v2, then a representative
   full-size training batch. Measure peak VRAM and step time to establish feasible
   microbatch/accumulation and a time/disk estimate. Include a bounded CUDA smoke
   reaching optimizer update 101 and subsequent validation to verify delayed EMA
   and its exported weights on the actual device. Preserve effective batch 24
   and the approved epoch/schedule policy when fitting hardware; report changed
   update/partial-batch counts and settle any scientific-policy change explicitly.
3. Use `num_workers=0` and `persistent_workers=false` from the outset for the
   resumable launch recipe. Existing production examples have eight workers;
   copying them unchanged cannot satisfy exact resume. Rehearse interruption at a
   completed epoch and continuation with the same total schedule and saved run ID.
   Report CUDA/mixed-precision agreement with an explicit appropriate tolerance;
   do not promise CPU-style bitwise CUDA equivalence or mid-batch recovery.
4. Select one production baseline, verify its metadata-only preview and launch
   using a distinct new identity. Recommended starting case is `planet8` with
   `variant="augmented"`; confirm the user's intended case at launch. Use all
   selected training/validation batches for production, not smoke limits. Keep
   approved preprocessing, 70 total epochs, validation-only checkpoint selection,
   threshold .5, native TorchMetrics and delayed EMA unchanged.
5. Verify the process remains running outside the interactive login, logs advance,
   the first validation completes, and distinct best/last checkpoints are written.
   Record paths, recipe and commit plus ordinary explicit backup/restore commands
   for production settings, logs, checkpoints and final bundle. Use completed,
   stable output files for copies. Production artifacts need preservation; G's
   disposable tests do not. No custom synchronization/recovery service.
6. Keep the running job on its fixed checkout/environment/recipe. Use a separate
   checkout for later code changes; do not pull local Task 035 changes into a live
   run. Commit remote setup corrections and integrate them back locally. Closing
   the remote milestone requires a healthy first epoch and clear monitoring/backup
   handoff, not waiting for all 70 epochs or scoring held-out data.

## User decisions required

The user selected the lab SkyPilot API via Tailscale and an RTX3090 request.
Resolve the actual allocated SSH alias, OS/architecture, persistent mount and
available space on the machine. Authenticate Box and W&B there. At launch,
settle the baseline case and resource budget; recommend native-eight with BC,
one GPU, the existing approved schedule and zero workers.
Hardware incompatibility or a required scientific-policy change blocks launch,
not independent local documentation work. Creating this task does not provision
or access a host, transfer data or start production training now.

## Smoke and validation

Locally: bootstrap syntax and mocked platform/failure checks, Markdown links,
Ruff and `git diff --check`; pre-commit for the changed script/tests. No actual
Linux installation, downloads or CUDA validation on the Mac. Existing Task 033G
CPU evidence remains valid for unchanged training behavior. Packaging checks
are needed only if subsequent remote fixes affect packaging.

Remotely: frozen install on actual host, CUDA/bf16 and ImageNet initialization,
bounded train/validation/bundle and completed-epoch resume, measured full-size
memory/step time, final production preview and first healthy epoch. Preserve
zero test-payload reads. Record failures and corrections plainly; local success
alone is not remote validation. Production runs/checkpoints have a separately
agreed storage budget, not the 4 GiB disposable smoke allowance.

## Acceptance and non-goals

- Another researcher can follow the committed setup guide using settings without
  Python edits. Checklist-ready, remote-validated and baseline-started status are distinct.
- The remote run is reproducible from a recorded commit, locked environment,
  published data and resolved recipe; remote fixes return to the local repository.
- Task 035 may proceed after the committed checklist milestone while remote
  setup or training continues. Production itself waits for the remote gate. No
  dependency on finished inference, scoring, LORO or Task 039 is introduced.
- Task 034 owns machine setup, data staging, GPU sizing and the initial baseline
  launch. Task 039 reuses that procedure for final researcher usability checks;
  it does not repeat relocation/bootstrap or gate this first production run.
- No full comparison suite, LORO, new-region training, test scoring, tiled mapping,
  new augmentation selection, multi-GPU training or cloud provisioning framework.

## Outcome template

- Local preparation: changed files, obsolete consumers retired, checks and commit.
- Remote handoff: unresolved host details, exact commands and next action.
- Remote validation: actual environment/hardware, measured smoke/batch evidence,
  resume limits, corrections and integration commits.
- Baseline launch: selected recipe/identity, committed revision, first-epoch
  evidence, persistent job/log/output locations and backup plan.
- Queue: mark local milestone complete when ready; record remote status separately.
  Next local task is 035 (image-only tiled inference). Stop before implementing it.

## Planning outcome — 2026-11-03

Created this contract and moved the existing 034–038 roadmap to 035–039. Moved
initial GPU relocation/readiness and baseline-launch ownership out of the final
researcher handoff. No setup code, environment, data, remote host or experiment
was changed. All 211 relative file/anchor links in the changed Markdown and
`git diff --check` pass; no runtime tests were needed for this docs-only change.
Exact next action: implement Task 034's local preparation milestone,
commit it, then use the same task for remote validation and iteration.

## Local setup draft — 2026-11-03

Added the remote-first entry guide and root bootstrap; updated current routers
and shifted former Tasks 034–038 to 035–039. Initial setup/data staging/baseline
launch belongs here; Task 039 reuses it for final usability checks. No remote
host, package installation, Box transfer or production run has been performed.
Legacy scripts remain pending validation of their replacement on Linux.

Validation: `bash -n bootstrap_gpu.sh`, seven mocked bootstrap tests, Ruff
format/check, pre-commit and `git diff --check` pass. All 234 relative file/anchor
links in changed Markdown and the guide's Bash block syntax pass review. No training/package code
changed; Linux installation and CUDA checks remain pending.
Exact next action: commit/push the setup draft, follow `docs/gpu_setup.md` on
the allocated instance, then iterate there through this task's remote gate.

### Remote Box authentication correction

The user reported that UCLA Box must already be signed in in the Mac browser
before opening rclone's terminal link; otherwise it led to the regular Box login.
Updated the guide to forward port 53682 over SSH, answer yes to browser
authentication, and open the link in that same authenticated browser profile.
This replaces the token-copy instructions. Documentation/diff checks only;
the remaining remote installation and GPU validation status is unchanged.

### Remote storage choice

The user selected `/home/sky/data` because `/mnt/persistent` is unavailable.
The guide now uses that artifact root and `/home/sky/data/runs`, preserves the
project-relative release layout, and permits an existing root while refusing
existing release destinations before copying. Capacity and instance-lifecycle
persistence still need confirmation on the host. No data was moved locally.

## Remote execution plan — 2026-11-03

User authorized completing the remote checks and preparing the baseline launch.
Treat `/home/sky/data` as temporary and back up production outputs to Box, per
the user's explicit choice. Starting revision is
`f459a66798bde3e9cd290deacae21d66496a0eea`; checkout initially clean.

Bounded work: generate tiny chips using existing commands; add ordinary GPU
smoke/production TOML recipes under `configs/train/`; run metadata previews,
real CUDA/bf16 train/validation, EMA after update 101, copied-bundle prediction,
completed-epoch continuation comparison, and representative batch timing/VRAM.
Evidence and disposable harnesses belong under
`/home/sky/data/analyses/task034_gpu_v1`, outside Git, within the 4 GiB smoke
artifact allowance. Fix demonstrated issues only; run focused tests/Ruff and
pre-commit for code changes. Update this record, GPU guide and current routers;
retire the two legacy setup scripts once replacements pass. Commit fixes before
production. Present the measured launch recipe/resource budget to the user, then
launch and verify the first epoch, with explicit stable-output Box backup.
Stop before Task 035.

## Remote validation evidence — 2026-11-03

- Environment: Ubuntu 20.04.6 x86_64; RTX 3090, 24 GiB, driver 590.48.01;
  Python 3.12.11, uv 0.8.15, Torch 2.12.0+cu130/CUDA 13.0, Lightning 2.6.1,
  SMP 0.5.0. Frozen sync, CUDA allocation/matmul and bf16 support pass.
  About 329 GiB was available at entry. User chose temporary-storage treatment
  and explicit production backups to Box. No driver/OS update was repeated.
- All four staged releases match documented file counts and aggregate sizes:
  chips 26,577 / 65,565,628,953 bytes; splits 5 / 935,947; collection 1 / 539;
  tiny v2 28 / 82,537,678. Box listing and authenticated W&B project read pass.
  No new checksum/catalog machinery; no training/test payload audit.
- Existing split/chip commands generated 54 tiny chips under
  `/home/sky/data/examples/runs/my-tiny-v2-01-{splits,chips}`. This canonical
  preparation includes declared tiny source TIFFs; all subsequent fitting and
  prediction checks use training/validation selections only.
- Added `configs/train/tiny_gpu.toml` and `planet8_gpu.toml`, reusing the same
  strict schema. Tiny eight-band ImageNet-initialized CUDA/bf16 training passes
  two epochs, save/export and copied-model validation-image prediction
  (`max_abs_error=0`). ImageNet cache/download works. Tiny disposable weights
  were removed after verification; logs/records and generated tiny data remain.
- Eight full-release metadata-only previews pass. Eligible training counts are
  8,518 with BC and 7,280 without; validation 933, test metadata 1,262. Native
  eight-band with BC retains microbatch 3 × accumulation 8, 2,840 training and
  311 validation batches per epoch, 355 updates/epoch and 24,850 total updates.
  Final training microbatch has one sample; the final accumulation group has
  eight microbatches. No memberships, preprocessing or scientific schedule changed.
- Representative full-data sizing (64 training batches, 16 validation batches
  over two smoke epochs) uses the production batch/accumulation, zero workers,
  bf16 and real B3. Peak allocated 3.838 GiB, reserved 4.018 GiB; steady mean
  0.351 seconds/microbatch. Training alone projects to 16.6 minutes/epoch and
  19.4 hours/70 epochs. Allow roughly 20–25 hours including validation/saving;
  this is a short-sample estimate, not a guarantee. Reserve 10 GiB for run files
  and backup snapshots; measured pre-EMA best+last total 1.09 GB, bundle 179 MB;
  EMA checkpoints are larger. Sizing weights removed after recording evidence.
- External evidence: `/home/sky/data/analyses/task034_gpu_v1/` contains environment,
  eight previews, tiny/sizing reports and logs, bounded rehearsal Python harnesses,
  and verification logs. These harnesses call the installed runner; no new
  training framework or repository script directory was added.
- Removed `scripts/bootstrap_skypilot.sh` and
  `scripts/prepare_remote_planet8b_dataset.sh` after their replacement setup and
  Box staging were exercised. Historical task references remain historical.
- Focused bootstrap/settings/runner/resume/loop/bundle tests: 74 passed.
  Ruff format/check and all-file pre-commit passed; native warnings remain
  warnings. No dependency change was needed; the later GPU comparison below required
  enabling native deterministic training.

### CUDA repeatability issue found during rehearsal

The first 202-update full/interrupted comparison failed the predeclared
`atol=1e-5, rtol=1e-4` weight tolerance (first tensor max difference 0.005703).
Comparison of logs showed the runs diverged at batch 2, before interruption;
first-epoch validation IoU differed .4250 versus .2415. Final Torch/CUDA/loader
RNG, update count, schedule and EMA count agreed. This is not evidence that
resume itself lost state. Failed comparison/logs are retained in
`task034_gpu_v1`; its disposable weights were removed to preserve the 4 GiB
smoke allowance. Production remains gated.

Test native `Trainer(deterministic=True)` with the same real B3/CUDA/bf16
rehearsal in `/home/sky/data/analyses/task034_gpu_deterministic_v1`. The minimal
runner correction enables native deterministic algorithms and records the policy
in `run.json`; no custom kernel, new recipe schema or scientific-policy change.
Repeat full/interrupted/resumed comparison and production sizing before launch.

### Deterministic GPU continuation passed

The corrected real B3 run completed two epochs of 101 updates each, with a
separate stop immediately after the epoch-0 last checkpoint and continuation
under the same two-epoch budget and saved identity. All 2,936 compared tensors
matched exactly (`max_abs_error=0`) within the predeclared `atol=1e-5, rtol=1e-4`.
This includes ordinary/selected/EMA weights, optimizer, scheduler, loop state,
Torch/CUDA/loader/augmentation RNG and EMA callback state. Final update count
202, EMA count 102. Exported weights exactly match the selected EMA checkpoint;
a copied bundle loads offline and predicts a 512×512 validation image.
This bounded result does not promise bitwise equivalence across other devices
or software versions. Failed nondeterministic evidence remains separately.

The native deterministic setting is the sole training-code correction. After
it, 67 focused settings/runner/resume/loop/bundle tests pass, Ruff passes and
all-file pre-commit passes. The initial seven bootstrap tests also passed.
External retained evidence/model/recovery pair is under
`/home/sky/data/analyses/task034_gpu_deterministic_v1`; redundant reference and
sizing weights are removed after verification to keep disposable smoke artifacts
below 4 GiB. No held-out test arrays were used for these checks.

Final deterministic sizing: 0.438 seconds per training
microbatch, 3.815 GiB peak allocated and
3.941 GiB reserved. Training alone projects to
20.7 minutes/epoch and
24.2 hours for 70 epochs. Budget 25–30 hours
including validation/checkpointing and normal host variation, and 10 GiB
for active run plus backup snapshots. The retained EMA best+last total
1,448,110,138 bytes. Production recipe remains unchanged
at batch 3 × accumulation 8. Review caught and fixed initial launch-log
overwrite refusal; guide links/shell syntax and diff checks pass.

Exact next action: confirm native-eight with BC, one RTX 3090, 70 epochs,
25–30 hours and 10 GiB run/snapshot budget; launch the committed recipe in
tmux, observe the first validation/checkpoints, back up a stable snapshot to
Box, then close Task 034 with monitoring details.

### Committed prelaunch handoff

Implementation and evidence were committed as
`e76722327dc550a5f82ee860070a6e27d6dc49ab` on
`codex/task034-gpu-validation` and pushed to origin. The fresh host lacked a Git
identity; repository-local identity was set to match the existing commit author.
Two pushes failed with SSH broken pipe despite successful authentication; the
push succeeded with `git -c core.sshCommand='ssh -o IPQoS=none -o ControlMaster=no'`.
No global SSH configuration was changed. Fetch this branch on the Mac to bring
back the remote corrections; no main-branch merge or Task 035 work was performed.

An explicit launch choice is pending: recommended Planet eight-band with BC,
one RTX 3090, 70 epochs, 25–30 hours, 10 GiB for run/snapshots, and Box backup.
No production process has started. Task 034 remains in progress until its first
epoch, stable-output backup and monitoring handoff are verified.

## User-selected ten-epoch pilot — 2026-11-04

The user superseded the proposed immediate 70-epoch launch with a ten-epoch
native-eight-band with-BC pilot. Added `configs/train/planet8_gpu_10ep.toml`,
with W&B enabled and distinct `planet8-cabc-10ep` identity. Preserve full
training/validation selections, batch 3 × accumulation 8, zero workers,
ImageNet initialization, preprocessing and five warmup epochs; cosine decay now
covers the remaining five epochs. This is its own ten-epoch schedule, not a
70-epoch run stopped early. The user will start training and share the log if
needed. Do not launch it from this chat. The user also requested no future
commits/pushes without explicit instruction; recorded in AGENTS.md.

Exact next action: user reviews these uncommitted changes and launches the
pilot using the GPU guide. Assess training/validation behavior before deciding
on the longer baseline. No pilot or production fitting was started here.

Pilot validation: installed metadata-only dry-run passes with 8,518 eligible
training chips, 933 validation chips and 3,550 optimizer updates over ten epochs.
W&B is enabled. Preview saved to
`/home/sky/data/analyses/task034_gpu_deterministic_v1/pilot-10ep-preview.log`.
Ruff format/check, guide shell syntax and `git diff --check` pass. No new
behavioral tests needed for this recipe/documentation-only change. All changes
remain uncommitted and unpushed.

## Performance benchmark plan — 2026-11-04

The user stopped the pilot and authorized benchmarking worker counts,
deterministic execution and larger microbatches. Keep existing methods when
measurements show they are not a bottleneck. Do not commit/push or start another
pilot. Benchmark only full-release training/validation selections on the RTX
3090, sequentially, with real model/loss/augmentation and effective batch 24.
Compare workers 0/2/4/8, native deterministic on/off, and microbatches 3/6/12/24
with matching accumulation. Measure steady samples/sec, loader wait, validation,
checkpoint time and peak VRAM, separating startup from steady throughput.
Use two short epochs to include persistent-worker behavior. Larger microbatches
change batch-pooled Lovasz semantics; report this separately from throughput-only
changes. Confirm leading settings on a longer bounded sample before choosing.
Evidence/harnesses stay outside Git under
`/home/sky/data/analyses/task034_performance_v1`; remove redundant benchmark
weights after each run to keep disposable smoke artifacts bounded. If workers
help, add ordinary completed-epoch continuation that restores training state
while explicitly allowing changed worker augmentation streams. If disabling
determinism helps, expose a plain setting while preserving the default. Run
focused correctness tests and GPU continuation checks for any implementation
change. Update researcher guidance and handoff, leaving all changes reviewable.

## Throughput results — 2026-11-04

The user accepted randomness on continuation and requested speed improvements
only where measurements identify a bottleneck. This supersedes the earlier
zero-worker/exact-replay launch requirement. No production restart is authorized
from this chat; the user reviews changes and starts the next pilot.

Method: real ImageNet-initialized SegFormer B3, native eight-band with-BC
training/validation selections, approved augmentation/loss/TorchMetrics, bf16,
CSV logging and normal best/last writes. Effective batch stays 24. Each case
runs two declared smoke epochs; short cases use 192 training and 48 validation
samples per epoch, longer confirmations 768/192. Exclude 24 warmup training
samples per epoch from steady throughput. Timings synchronize CUDA, and loader
wait includes transfer/loop time before the next training-batch callback.
Initialization, worker startup, full-epoch wall time and checkpoint time are
recorded separately. Cases run sequentially on the otherwise idle RTX 3090.
No test arrays were opened. W&B was off for benchmarks; live tracking overhead
is not included. Results establish throughput/operation, not scientific quality.

| Case | Workers | Microbatch | Deterministic | Train samples/s | Wait ms/batch | Peak GiB |
|---|---:|---:|---|---:|---:|---:|
| b3-w0-det | 0 | 3 | True | 6.70 | 261.5 | 3.82 |
| b3-w2-det | 2 | 3 | True | 15.62 | 1.9 | 3.82 |
| b3-w4-det | 4 | 3 | True | 15.63 | 2.0 | 3.82 |
| b3-w8-det | 8 | 3 | True | 15.69 | 1.9 | 3.82 |
| b3-w2-fast | 2 | 3 | False | 21.18 | 40.1 | 3.84 |
| b3-w4-fast | 4 | 3 | False | 29.02 | 1.9 | 3.84 |
| b3-w8-fast | 8 | 3 | False | 27.94 | 2.4 | 3.84 |
| b4-w4-fast | 4 | 4 | False | 35.30 | 2.7 | 4.79 |
| b6-w2-fast | 2 | 6 | False | 21.32 | 144.5 | 6.70 |
| b6-w4-fast | 4 | 6 | False | 42.88 | 4.0 | 6.70 |
| b12-w4-fast | 4 | 12 | False | 46.33 | 19.0 | 12.39 |
| b12-w8-fast | 8 | 12 | False | 47.82 | 8.4 | 12.39 |
| confirm-b6-w4-fast | 4 | 6 | False | 42.11 | 8.1 | 6.70 |
| confirm-b8-w4-fast | 4 | 8 | False | 42.51 | 18.3 | 8.60 |
| confirm-b12-w4-fast | 4 | 12 | False | 43.26 | 35.6 | 12.39 |
| confirm-b12-w8-fast | 8 | 12 | False | 47.61 | 8.2 | 12.39 |
| b24-w4-fast | 4 | 24 | False | OOM | — | >23 |

Batch 24 failed with 23.12 GiB allocated and only about 1 MiB free when another
192 MiB was needed. This was a capacity failure, not evidence for allocator
or recovery machinery; the failed run/log remain, and the process exited.

The selected fast candidate is microbatch 12 × accumulation 2, eight persistent
workers and `deterministic=false`: 47.61 samples/s in the longer confirmation,
12.39 GiB allocated / 12.88 GiB reserved. Four workers suffice for batch 3;
eight offered no benefit there. With batch 12, eight workers reduce the renewed
loader bottleneck enough to improve 43.26 to 47.61 samples/s. Batch 8 at four
workers and batch 6 at four workers were about 42 samples/s. The selected case
is about 7.1× the original 6.70 samples/s. Keep bf16, pinned memory, default
prefetching, augmentation, model, optimizer, schedule, metrics and checkpoint
frequency unchanged; no evidence justifies changing them. Validation is about
99 samples/s and best+last writes about 3.2 seconds/epoch, too small a runtime
share to justify reducing either.

The selected projection is 191.6 seconds/epoch: 31.9 minutes for ten epochs or
3.7 hours for seventy before normal variation. Budget 35–45 minutes and 4–5
hours respectively; these are bounded-sample estimates, not guarantees.

Added `configs/train/planet8_gpu_10ep_fast.toml`, keeping the original pilot and
70-epoch reference untouched. W&B remains enabled in the pilot. It has a distinct
`planet8-cabc-10ep-fast` identity; preview reports 710 training / 78 validation
batches per epoch, 355 optimizer updates/epoch, 3,550 total, effective batch 24,
and the same 8,518/933 training/validation selections. Final training microbatch
has 10 samples, so the final optimizer group still has 22 samples. Five warmup
epochs and five cosine epochs are unchanged. Larger microbatches change the
batch-pooled Lovasz objective and batch-normalization statistics; this is an
explicit pilot variation, not numerical equivalence to batch 3. Comparisons
must use matching microbatch settings. The batch-3 alternative with four
workers and nondeterministic execution measured 29 samples/s without changing
the microbatch loss grouping.

Implementation: plain boolean `deterministic` (default true) in the existing
schema, passed to Lightning and recorded in run metadata; ordinary multiworker
completed-epoch continuation saves identity, progress and main/loader random
state while omitting unadvanced parent augmentation state. Native Lightning
restores model/optimizer/scheduler/EMA; worker streams restart and sample order
may differ. Existing strict identity/schedule checks remain. Missing deterministic
in immediately preceding checkpoints is interpreted as true; older nondeterministic
GPU smoke artifacts have no exact-replay guarantee. No worker-state capture,
new checkpoint framework, dependency, hashing or recovery service was added.

External evidence: `/home/sky/data/analyses/task034_performance_v1` contains the
benchmark harness, 17 case logs/reports, `summary.csv`, selected recipe preview
and check logs. Redundant case weights were removed after measurement; original
pilot outputs were untouched. Ordinary multiworker GPU continuation is exercised
separately under `/home/sky/data/analyses/task034_performance_resume_v1`.

### Fast continuation and final handoff

On real B3/CUDA/bf16 with batch 12 × accumulation 2, eight persistent workers
and deterministic execution off, ran a declared two-epoch smoke of 202 training
microbatches/epoch (101 updates/epoch). Deliberately stopped after the first
completed last checkpoint, then resumed with the same run identity and schedule.
Before resumed updates, ordinary model weights, optimizer, scheduler and EMA
state matched the saved checkpoint exactly. The checkpoint held EMA count 1 at
step 101; completion reached step 202 / EMA count 102. Worker transform state is
intentionally absent. No final-weight replay claim was made. Exported weights
match the validation-selected EMA state and offline bundle loading predicts a
512×512 validation image successfully. `verification.json` and
`restored-state.json` retain these results under the continuation evidence root.
Peak GPU allocation remained about 12.4 GiB. Original deterministic evidence
plus the new representative continuation artifacts occupy about 3.3 GiB total;
benchmark case weights are removed, and the user's stopped pilot is untouched.

Validation: 95 focused CPU resume/settings/runner/loop/bundle/CLI tests passed,
including state restoration with persistent workers and old zero-worker identity
compatibility. Ruff format/check, all-file pre-commit, 151 relative link targets,
GPU-guide shell syntax and `git diff --check` pass. Native Lightning/fork notices
remain warnings. Independent review found no restoration defect; clarified that
missing deterministic defaults to the immediately preceding true policy, not a
promise about older nondeterministic GPU smokes. No dependencies changed.

Changed repo files: the existing training settings/runner/resume and CLI help;
three focused test files; one separate fast pilot TOML; architecture/experiments,
quickstart/GPU guide, current queue and task records. No commit or push performed.
No replacement pilot or production training started; only bounded benchmarks
and verification fitting ran.

Exact next action: user reviews the uncommitted changes, commits/pushes when
ready, then launches `configs/train/planet8_gpu_10ep_fast.toml` in tmux using a
fresh log filename. Assess that pilot before selecting the longer baseline.
Task 034 remains in progress pending the user's launch/first-epoch monitoring
and stable-output Box backup; do not start Task 035 here.

## Twenty-epoch pilot update — 2026-11-04

User selected twenty epochs for the fast pilot. Renamed the uncommitted recipe
to `configs/train/planet8_gpu_20ep_fast.toml` and run name to
`planet8-cabc-20ep-fast`; changed epochs from 10 to 20. Five warmup epochs remain,
followed by fifteen cosine epochs. All other fast settings and W&B remain.
This supersedes the ten-epoch fast recipe and launch action above; the original
batch-3 ten-epoch reference remains available. User reviews and launches the new
recipe; do not commit, push or start training here.

Validation: metadata-only preview passes: 20 epochs, 355 updates/epoch, 7,100
total updates; W&B enabled. Ruff format/check and diff checks pass. No training
started; changes remain uncommitted.

## Slash-grouped metric logging plan — 2026-11-04

User requested `train/` and `val/` metric names for W&B sections and research
into W&B logging guidance. Keep native Lightning logging/global-step handling,
pooled metric/loss definitions, and logging frequency. Rename logged metrics
and checkpoint monitor together; preserve old `val_iou` checkpoint callback
selection state on continuation. Add focused logging/checkpoint tests, update
researcher docs, and leave changes uncommitted. The current 20-epoch process
continues using its already-loaded code; do not restart it or run GPU tests.

### Slash-grouped logging outcome

Renamed native Lightning metrics to `train/`, `val/` and `trainer/` prefixes
in the training module and switched best-checkpoint monitoring to `val/iou`.
The resume callback maps preceding `val_iou` callback state so the best score
and earliest selected checkpoint survive continuation and relocation. Loss and
pooled metric definitions, logging frequency and native global-step handling
are unchanged. Updated loop/runner tests, quickstart and experiment contract;
the latter links the official W&B panel-grouping and Lightning guidance.

Validation: 37 focused CPU loop/runner/resume/bundle tests pass, including CSV
names and legacy best-score restoration with zero and two workers. Ruff format,
Ruff check and all-file pre-commit pass. No new external training artifacts,
commits, pushes or training launches. The active pilot retains its already-loaded
metric names; the user can review these changes for the next start/continuation.
Task 034 remains open for pilot assessment and Box backup of stable outputs.

## Training batch IoU follow-up — 2026-11-04

User requested live batch IoU alongside pooled epoch metrics. Add a stateless
TorchMetrics `train/iou_step` calculation with the same threshold/ignore policy,
keep epoch accumulators unchanged, verify distinct batch and pooled values in
the CPU CSV integration test, and document logging cadence. Do not restart the
active pilot, commit or push.

Outcome: added `train/iou_step` using the existing TorchMetrics functional API;
pooled `train/iou` and all validation metrics remain unchanged. The CSV test
verifies batch IoUs [1, 0, 0, 2/3] versus pooled epoch IoUs [1/4, 1/2], including
ignored pixels and epoch resets. Updated runner metric-name assertion and
quickstart/experiment documentation. All 22 focused loop/runner CPU tests,
Ruff format/check and diff checks pass. No training launch, commit or push.
Next action: user reviews changes for their next start/resume; current pilot
continues with already-loaded code. Task 034 remains in progress.

## Completed-pilot validation analysis — 2026-11-04

User requested validation predictions and regional/background error analysis
while locating a representative historical W&B run. Ran a bounded external
analysis using existing validation datasets and epoch-18/20 EMA weights; no
Task 035/036 implementation or test-payload evaluation. Evidence and plain
analysis scripts are under `/home/sky/data/analyses/task034_pilot20_review`.
The validation subfolder retains best prediction arrays, identity-preserving
chip CSVs, region/source confusion summaries, visual examples and report.txt.

All 933 disjoint validation chips (53 sources, regions 001-010) reproduce logged
IoU/loss: best .68512695, last .68398852. Background-only FPR is .00426% across
546 chips. Region 004/006 recall and region 008 false positives warrant review.
Epoch 18→20 BCE and Brier improve slightly; increasing Lovasz explains the late
combined-loss rise. Earlier overfit wording is too strong without earlier
checkpoint comparisons. Visuals show missed fragmented labeled patches and
filled-in predicted patches in selected extremes; no label-correctness claim.
Only selected chip coverage is scored, not complete reconstructed TIFFs.

No training launch, commit, push or Box upload. Exact next action: compare the
user's representative W&B run with matched objective/data/EMA semantics before
selecting a further training change; back up stable run/analysis outputs to Box.
Task 034 remains in progress.

## Separate loss component logging — 2026-11-04

Add unweighted smoothed BCE and Lovasz step/epoch diagnostics without changing
the 0.7/0.3 objective, valid-pixel averaging, or checkpoint selection. Compute
components once, retain the scalar loss helper, test weighting/reset/ignored
pixels and native CSV logging, then update researcher docs. No launch or Git
commit/push; additional logging suggestions remain separate from implementation.

Outcome: training/validation now log unweighted `bce` and `lovasz` epoch means
and training `bce_step`/`lovasz_step`, alongside existing combined loss. BCE
retains 0.1 smoothing. Components are computed once per forward pass and detached
for logging; the scalar helper and training objective remain unchanged. Native
MeanMetric accumulation uses the same valid-pixel weights and epoch resets.
Changed loss/module, focused loop tests, quickstart and experiment contract.
All 37 objective/loop/runner/resume CPU tests pass, including ignored support,
component reconstruction, CSV output/reset and completed-epoch continuation.
Ruff format/check, all-file pre-commit and diff checks pass. No run launched,
recipe changed, commit or push. Next: user reviews logging and selects the
longer-run recipe/checkpoint policy; Task 034 remains in progress.

## W&B prediction panels and regional validation plan — 2026-11-04

Use existing batch predictions for bounded epoch media: one fixed positive
validation chip per region when available plus two background examples, and
four samples from shuffled augmented training. Native W&B image/mask logging
preserves identity captions and ignored pixels without extra inference. Pool
validation metrics per region from existing metadata and retain global selection.
Test media selection/alignment, native offline W&B serialization, regional pooling
and epoch reset. Keep implementation in a small diagnostics helper; no launch,
commit or push, and no changes to the training recipe.

Outcome: added `training/visuals.py` with deterministic region/background sample
selection and bounded CPU media collection from existing forwards. Runner
registers validation diagnostics before Trainer setup; module logs epoch media
through native WandbLogger and pools registered per-region TorchMetrics with
valid support. Images retain aligned augmented targets and ignored pixels;
validation removes loading padding. RGB or NIR/red/green captions explain display
stretch and retain source/date/window identity. No additional model pass or
random-number consumption. Global selection and loss remain unchanged.

Validation: 32 focused CPU media/loop/runner/resume tests pass. Offline native
W&B image/mask serialization passes; no online test run was created. Tests cover
stable selection, sample bounds, transformed-canvas masking, region pooling with
unequal valid support, epoch reset, and completed-epoch resume. Ruff format/check,
all-file pre-commit and diff checks pass. Quickstart/experiment docs describe
panel controls, sample policy, limits and regional metric interpretation. No
production training, recipe changes, commit or push. Exact next action: user
reviews changes and launches the selected future run with W&B enabled; that run
will upload epoch media and regional metrics. Task 034 remains in progress.

## Diagnostics simplicity review — 2026-11-04

Review the recent logging/media/regional changes against plain-function and
minimal-bookkeeping guidance. Initialize optional state explicitly, resolve the
W&B logger once at fit start, simplify sample selection, and separate W&B-free
sampling tests from optional native integration. Exercise actual epoch hooks
with a bounded offline CPU fit; preserve metrics/media policy and user changes.

Review outcome: replaced missing-attribute checks with explicitly initialized
empty metrics/optional media state, and resolve the native W&B logger once at
fit start instead of searching each batch. Sample selection now sorts once and
uses ordinary loops, stopping after two extra background chips; no generator
reads a list while extending it. Kept native TorchMetrics/WandbLogger and the
small media helper; no new configuration layer, dependency or framework.

Separated bounded sampling/reset checks from optional W&B availability, and
added a real two-epoch offline Trainer integration test proving both phase
panels carry epoch/global-step captions and clear their buffers. Across focused
objective/loop/runner/resume/media checks, 42 tests pass (41 in the initial
suite plus the corrected media integration case; all four media tests rerun).
Ruff format/check, all-file pre-commit and diff checks pass. Corrected stale
queue/task status to reflect the completed pilot. No further correctness issue
found in reviewed logging paths; online dashboard appearance remains unverified.
No training recipe changes, production launch, commit or push. Next action stays
user review and selection of the longer-run recipe/checkpoint policy, with Box
backup of stable outputs; Task 034 remains in progress.

## Reviewed commit and seventy-epoch recipe — 2026-11-04

User explicitly authorized committing reviewed changes. Created local commit
`670ed06` for throughput/resume and training diagnostics; no push. Subsequently
prepared `configs/train/planet8_gpu_70ep_fast.toml` with a distinct 70-epoch name,
five warmup epochs, peak LR 3e-4 and minimum 3e-6. Remaining fast settings,
with-BC native eight bands, ImageNet initialization and W&B are unchanged.
The new recipe and handoff docs remain uncommitted for review. Best/last-only
checkpoint retention is unchanged; epoch archive policy is not implemented.

Metadata-only CLI preview passes: 710 train / 78 validation batches each epoch,
355 optimizer updates per epoch and 24,850 total. No fitting or model download
was started. Exact next action: user starts the direct command in the GPU guide
inside tmux; no tee/tail/redirection needed. Back up stable outputs to Box.
Task 034 remains in progress.

## W&B image-size warning fix — 2026-11-04

User reported the native W&B image-list size warning during the 70-epoch run.
SDK inspection locates it in image-list serialization, not image/mask alignment.
Existing media contain 512x512 and 512x511 images because visualization cropped
partial validation windows. Keep the model canvas for media, with padding still
gray/ignored; no resampling or changes to predictions/metrics. Add mixed-size
source-window coverage to offline media tests. Do not restart the active run.

Outcome: removed display-only validation cropping, preserving the original
512-square model canvas and ignored padding without resizing. Four focused CPU
media tests pass, including two epochs of native offline W&B logging with mixed
true window sizes and an explicit absence-of-warning assertion. Ruff format,
Ruff check and diff checks pass. Updated quickstart. No commit/push or restart;
the active process retains old code and may continue warning until completion.
The fix applies on the next process start; current training/metrics are unaffected.

## Post-training validation report plan — 2026-11-04

User requests a simple post-training diagnostic report, false-color-only views,
no changes to active training and no commits. Add a separate validation-report
command requiring completed run.json and its selected portable bundle; CPU by
default. Reuse existing disjoint validation selection, join adjacent windows in
original coordinates, retain gaps/ignore masks, and score validation only.
Produce source/region area counts, threshold sweep and probability histograms,
boundary precision/recall at 1/2/3 pixels, near-boundary/interior errors, and
8-connected label-patch recall by size with coverage-truncated patches flagged
and excluded from size summaries. Static HTML/CSV/JSON and bounded false-color
examples; ordinary functions, no service, dependencies or training hooks.
Test synthetic geometry and a tiny CPU end-to-end command with test payloads
absent. No full GPU evaluation while the current run trains; no Task 035/036
full-TIFF inference implementation or held-out scoring in this bounded extension.

Post-training report outcome: added the independent installed `validation-report`
CLI and three small report modules (orchestration, metric functions, static views).
Requires completed run identity plus its exported selected bundle; defaults to
CPU, leaves W&B/training untouched and refuses an existing output. Native model
bundle inference uses float32 and the existing validation selection. Source
canvases join adjacent observed windows with unknown gaps, then calculate pooled
confusion/area, boundary tolerance scores, near/interior errors, patch-size recall
with truncation flags, threshold sweep and probability histograms. Source/window
identities and scoring support are retained in plain CSV/JSON. Static HTML links
all tables and fixed false-color-only label/prediction/probability/error examples.
No new dependencies, service, checkpoint-selection rule or training hooks.

Validation: 26 focused report/package CLI tests passed; after adding explicit
pixel error rates, all four report tests passed again. Tiny CPU command exercises
real portable preprocessing/inference with a fixture model, excludes missing test
payloads, writes plots/tables and rejects incomplete runs/overwrites. Geometry
fixtures cover one-pixel boundary displacement, unknown borders, patch truncation,
size recall and joining across adjacent chips. Ruff format/check, all-file
pre-commit and diff checks pass. No full-data or GPU analysis performed while the
70-epoch training runs. Changed report/CLI/tests and researcher documentation;
existing uncommitted work preserved, no commit/push. Exact next action: after
training exports model/, run the documented validation-report command into a fresh
external directory and open report.html; back up run/report outputs to Box.
Task 034 remains in progress; no full-TIFF/test evaluation task was started.

## Validation report quality review — 2026-11-04

Review metric arithmetic, source joins and static report simplicity without
changing active training or committing. Fix boundary matching at scoring margins:
score only safely interior contour pixels, but allow matches to every contour
with a fully observed immediate neighborhood. Add hand-computed CPU regressions
for that distinction, pooled confusion, threshold endpoints and patch connectivity.

Review outcome: fixed boundary matching references near scoring margins and
reused the two distance maps across tolerances. Consolidated patch-size bins into
one definition with an explicit loop. Updated HTML/quickstart metric explanations.
Reviewed canonical label mapping, native nodata, original-coordinate disjoint
joins, affine area calculation, count pooling and validation-only selection.
Added five independent regression cases: margin matches in both directions,
Euclidean partial matches, exact confusion/threshold/histogram values and undefined
ratios, pooled rather than mean-source metrics, and diagonal patch connectivity
with pixel-weighted recall. All 31 report/package CLI tests pass on CPU. Ruff
format/check, all-file pre-commit and diff checks pass after fixing a lint finding
in the simplified bin loop. No production evaluation or GPU work; running
training and its settings untouched, no commits. Exact next action remains the
post-completion report command above; real-data report inspection is pending.

## Report readability follow-up — 2026-11-04

User clarifies that simplicity means readable, explicit code, including types and
function documentation, rather than fewer lines. Add parameter/return annotations
and docstrings explaining inputs, outputs and side effects throughout report and
CLI functions. Preserve metric behavior, running training and uncommitted work.

Readability outcome: all 21 report/CLI functions (including the table formatter)
now have parameter/return annotations and purpose/input/output docstrings.
Documented array dimensions, ignore/nodata conventions, pooling semantics and
file-writing/list-mutation side effects. Added typed patch and analysis records;
heterogeneous manifest/export tables retain ordinary dictionaries. Recorded the
user's readability preference in AGENTS.md. No algorithm or training changes.
All 31 focused CPU tests, Ruff format/check, pre-commit and diff checks pass.
Exact next action: review these uncommitted changes, then run the report after
training completes. No commit, GPU evaluation or running-process changes.

## Configurable loss experiment support — 2026-11-04

User requests standard binary loss families and weighted combinations, excluding
distance-based boundary loss. Add explicit typed loss terms to recipes, validate
parameters, reuse installed SMP implementations, preserve default smoothed BCE /
Lovasz behavior, log active components and record resolved objective metadata.
Keep scientific ignore masks, float32 loss arithmetic and validation selection.
CPU arithmetic/gradient, recipe, logging and resume checks only; no active-run
settings edits, training launch or commits. Clarify any missing earlier candidates.

Configurable-loss outcome: user confirmed BCE, Lovasz, Dice, Jaccard, focal,
Tversky, focal Tversky and boundary-weighted BCE. Added typed LossTerm settings
and strict [[losses]] parsing in training/loss_settings.py/settings.py; literal
positive weights and resolved per-term parameters. training/loss.py builds stock
PyTorch/SMP modules once, masks ignored pixels before reduction, keeps float32
arithmetic and returns named components. Boundary BCE uses an explicit square
label-transition band, excludes unknown/chip-edge neighborhoods from boosts,
and divides weighted BCE by valid weight sum. Focal Tversky uses the literal
SMP-style exponent with finite zero-loss gradients for fractional gamma. No new
dependencies or distance-map implementation. Public baseline helpers and omitted
loss settings retain 0.7 BCE (smoothing 0.1) + 0.3 batch-pooled Lovasz.

TrainingModule logs only configured component names; run.py records resolved
terms. Existing resume identity now includes the loss settings, interpreting
missing fields in older checkpoints as the historical default. Changing an
objective requires a fresh run. Updated architecture, experiment contract,
quickstart (parameter table, example and scientific conventions) and queue.
No production config edited, no running-process interaction and no commits.

Validation: 198 focused CPU tests passed across objective/settings, new losses,
Lightning logging/reset, run metadata, resume, report and CLI. Tests cover hand
formulas, every pairwise combination plus all eight together, valid/ignored and
background-only support, boundary geometry/normalization, fractional exponent
zero gradients, bfloat16 inputs with float32 losses, invalid settings and dynamic
component logging. Ruff format/check, all-file pre-commit and git diff --check
pass. The 63 warnings are Lightning tiny-loader/checkpoint/logging notices and
Python multiprocessing fork deprecations; no test failures. No CUDA throughput
or full-data loss experiment was run. Exact next action: review uncommitted code;
after current training/report review, copy a recipe with a fresh name and chosen
[[losses]] terms for the next controlled experiment. Task 034 remains in progress.

## Loss configuration convention follow-up — 2026-11-04

Separate implementation type from unique logging name, permit repeated types,
and expose installed-library experimental options plus correct per-image pooling.
Keep shared binary/logit/ignore/float32 contracts, typed settings and docstrings.
Prepare individual full training recipes and matched combination controls for
later sequential screening; no launch/scheduling, active recipe edits or commits.

Convention follow-up outcome: LossTerm now separates type/name/weight/parameters;
type is required, name defaults to type, names are unique and types may repeat.
A small typed build_loss function constructs stock modules. Experimental options
include per-image versus microbatch pooling, BCE positive weighting and scalar
reduction, overlap smooth/epsilon/log loss, Tversky exponents, focal normalization
and reduced focal, and boundary BCE normalization. Per-image grouping occurs
before ignore filtering and averages valid images only. Independent loss-module
and component-metric storage prevents custom logging names from replacing model
attributes or phase metrics. Default objective remains unchanged and adds no
new checkpoint tensor state. Distance-based boundary loss remains deferred.

Added 13 standalone configs/train/losses/*.toml recipes: all eight single losses,
a smoothed BCE/Lovasz baseline, an unsmoothed BCE/Lovasz control and three
combinations (BCE/Dice, boundary BCE/Dice, focal/Dice). Draft budget is 10 epochs,
five warmup epochs; otherwise matched to the current 70-epoch 8-band with-BC run,
including 3e-4/3e-6 LR, batch12/accumulation2, seed42 and W&B. The optional budget
question had no reply during implementation; 10 epochs is the stated assumption.
Each recipe has a distinct run name. Existing production recipes are unchanged.
Updated quickstart/experiment contract/queue and CLI recipe help. Quickstart
contains the parameter table, pooling/reduction semantics, candidate descriptions,
preview command and a manual sequential stop-on-failure sweep command for use
only after the active training finishes. No scheduler or sweep was launched.

Validation: 229 focused CPU tests pass (66 existing tiny-Trainer/fork/checkpoint
warnings). Tests cover repeated/renamed types including name collisions, independent
per-image versus batch calculations, ignored-image exclusion, exposed options
against installed libraries, default checkpoint state, all candidate recipe
settings and forward/backward results, phase logging/reset, resume and prior
report/CLI behavior. Ruff format/check, all-file pre-commit and diff checks pass.
No CUDA benchmarking, active-run modification or commits. Exact next action:
review the uncommitted implementation and candidate/budget choices; after the
current run completes, select the overnight comparison set and run it sequentially.
Task 034 remains in progress.

Budget clarification: user selected 70 epochs per comparison run. Updated all
13 configs/train/losses recipes, run-name suffixes and quickstart budget text.
Five warmup epochs and LR endpoints remain unchanged; cosine spans 65 epochs.
The focused matched-recipe forward/backward test passes, all 13 parsed settings
explicitly verify 70 epochs/5 warmup/-70ep names, and git diff --check passes.
No code changes, launches, scheduling, commits or active-training modifications.
Next action remains review/select the comparison set after current training ends.

## Sequential comparison script plan — 2026-11-04

User selects BCE/Dice, boundary BCE/Dice and focal/Dice and requests a Bash
script: wait for current training completion, report that run, then train/report
each selected 70-epoch candidate in sequence. Prepare only, no launch or commits.
Keep interactive training output, stop on any failure, and use the returned run
path rather than guessing the newest directory. Reports use fresh external paths.
Test orchestration with fake commands only; no GPU/full-data evaluation now.

Sequential-script outcome: added executable repository-root
run_loss_comparisons.sh as explicitly requested. It polls the specified current
run's JSON every 30 seconds, refuses unsuccessful statuses, reports the completed
baseline, then trains/reports bce_dice, boundary_bce_dice and focal_dice in order.
Uses installed run_training/settings/path helpers in a short Python invocation;
only its exact returned run path is captured to a temporary file, while progress
remains interactive. Each report runs as a separate CUDA CLI process after its
training subprocess exits. Reports use a fresh external timestamped root and
per-run subfolders; no newest-directory guessing, tee/tail, implicit resume,
automatic backup or time-of-day stopping. Any failure prevents later stages.
Optional current-run/report-root arguments and --help are documented in quickstart.
Updated queue to the selected sequence rather than an all-13 sweep.

Validation: bash -n and help pass. Eleven fake-command orchestration tests pass,
covering the exact train/report order and returned paths, waiting for completion,
failed initial status, existing-output refusal, and failure at each of seven
stages. Tests compile embedded Python but perform no training, report inference,
GPU work or production writes. Ruff format/check, all-file pre-commit and diff
checks pass. Nothing launched, scheduled or committed; active training untouched.
Exact next action: user starts bash run_loss_comparisons.sh in a separate tmux
session (now to wait, or after completion). Inspect all four reports and back up
stable external outputs to Box after the sequence. Task 034 remains in progress.

## Noise-strength visual review — 2026-11-05

After the four completed comparisons, user requests weaker noise and viewer
verification without retraining. Reduce Gaussian std_range from (0,0.002) to
(0,0.0005) in the shared factory (raw sigma maximum 131.07 to 32.7675).
Preserve selection frequency and all other augmentation parameters. Update the
serialized snapshot and isolated viewer trials, retaining the old strength for
comparison. Generate training-only galleries with fixed display limits and seeds;
inspect exported previews and run focused parity checks. No commits or fitting.

Noise-review outcome: changed only Gaussian std_range to (0,0.0005), retaining
per-channel independent noise, SomeOf selection and all other transforms. Updated
configs/augment/baseline.json, parity assertion and isolated viewer sweep (new
0.0005 default; former 0.002 retained). Current docs distinguish this future-run
setting from the four completed runs and their saved augmentation metadata.

Generated /home/sky/data/analyses/task034_noise_review_20261105/isolated/index.html
and pipeline/index.html using the same four positive training windows plus two
background controls, seed33 and fixed raw 0–2000 display. Pipeline has 48 draws;
16 include Gaussian noise with empirical raw sigma 1.26–30.42. Verified identical
selected-window lists, all referenced viewer assets, and old/new isolated noise
settings. Visually inspected the exported fixed-scale original/new/old NIR panels
(noise_comparison.png) and an actual full-pipeline noise draw: reduced noise
preserves visibly clearer texture/small patches. Browser interaction itself was
not automated; the existing offline viewer and its assets were generated, and
requested opening the comparison image and viewer in Codex. No model inference
or retraining was needed; this does not establish a performance improvement.

Validation: 49 focused augmentation pipeline/preview/training-data tests pass;
Ruff format/check and diff checks pass. No commits or training launches. Exact
next action: user reviews Gaussian noise in isolated/index.html at 0.0005 versus
0.002 and the reduced-strength combined pipeline, then decides whether further
adjustment is needed. Task 034 follow-up complete; broader run/artifact review
and Box backup remain outside this visual check.
