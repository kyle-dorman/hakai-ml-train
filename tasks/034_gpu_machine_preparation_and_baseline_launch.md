# Task 034: GPU machine preparation and baseline launch

Status: In progress — 2026-11-03. Linux setup, CUDA/bf16, staged data,
tiny training, portable loading and deterministic completed-epoch continuation
pass. Final sizing passes; production launch awaits baseline/budget confirmation.
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
