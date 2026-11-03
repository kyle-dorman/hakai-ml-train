# Task 034: GPU machine preparation and baseline launch

Status: In progress — 2026-11-03. Local setup checklist/bootstrap authored;
actual Linux installation, GPU validation and baseline launch remain pending.
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

### Linux CI follow-up

Changed `.github/workflows/checks.yml` to Ubuntu 24.04 x86_64 after GitHub
failed to allocate a macOS ARM runner. Keep the same frozen Python 3.12
environment, CPU tests, offline wheel/sdist checks, Ruff and pre-commit.
The platform assertion now verifies Linux x86_64. The Linux dependency dry
run, lock check, Ruff and pre-commit pass locally; execution on the hosted
Linux runner is pending the next push. CUDA validation remains GPU-host work.
