# Set up the external GPU machine

Use this checklist to reach the Linux instance and validate training there.
The Ubuntu 20.04 / RTX 3090 installation, frozen environment, CUDA/bf16, Box
data staging and tiny training have been checked on the allocated host.
Deterministic EMA/resume and copied-model checks also pass; Task 034 records
the measured sizing and production-launch evidence.

## 1. Log in to Tailscale — on your Mac

Open Tailscale, sign in to the lab network and connect. You need the lab's
SkyPilot client installed locally and access to its API server for the next step.

## 2. Log in to SkyPilot — on your Mac

```bash
sky api login -e http://skypilot01.tail8e8be8.ts.net:30050
```

Complete the login prompted by the client. See the
[SkyPilot CLI reference](https://docs.skypilot.ai/en/latest/reference/cli.html)
if your installed client differs from the server.

## 3. Get a GPU instance — on your Mac

```bash
sky launch --gpus RTX3090
```

Keep the cluster name and SSH command printed by SkyPilot. Confirm the allocation
and storage with the lab; an SSH alias from a previous run is only an example.

## 4. SSH into the instance — on your Mac

Use the alias from your launch and forward rclone's authentication port to your
Mac, for example:

```bash
ssh -L localhost:53682:localhost:53682 sky-79fd-kyledorman
```

Keep this SSH connection open through Box authentication. If already connected
without forwarding, reconnect with the command above before the Box step.
All remaining commands run on the Linux instance unless explicitly labeled Mac.

## 5. Clone the repository — on the instance

The instance needs Git and GitHub SSH access. If cloning reports `Permission
denied (publickey)`, configure your GitHub SSH access there before continuing.

```bash
git clone git@github.com:kyle-dorman/hakai-ml-train.git
cd hakai-ml-train
git rev-parse HEAD
```

Check out the committed setup branch if it has not been merged into the default
branch. Confirm `bootstrap_gpu.sh` exists before continuing.

## 6. Update Linux packages and install tools — on the instance

Use an Ubuntu/Debian instance with sudo access. Run as your regular login user:

```bash
bash bootstrap_gpu.sh
export PATH="$HOME/.local/bin:$PATH"
```

The script updates and upgrades apt packages, installs Linux dependencies,
rclone and tmux, installs uv and Codex, then installs Python 3.12 and the frozen
project environment (including W&B). It stops on a failed command. It does not
configure the GPU driver; use the instance's provided NVIDIA driver. If the OS
requests a reboot after package updates, arrange that before GPU validation.
The installers follow the official [uv instructions](https://docs.astral.sh/uv/getting-started/installation/)
and [Codex CLI instructions](https://developers.openai.com/codex/cli/).

To work on this checkout with Codex:

```bash
codex login --device-auth
codex
```

Complete the device-code login in your Mac's browser. Enable device-code login
in your ChatGPT security settings if needed; see
[Codex authentication](https://developers.openai.com/codex/auth/).

## 7. Log in to Box — on the instance, with your Mac's browser

**First, sign in to UCLA Box in your Mac's browser using UCLA's login flow.**
Confirm you can access the project's `kelpseg` folder. Keep that browser session
open: opening rclone's link before signing in to UCLA Box can send you to the
regular Box login instead of the UCLA login, as observed during remote setup.

Then, in the SSH session with port 53682 forwarded, run:

```bash
rclone config
```

Create a remote named `kelp-box`, choose storage type `box`, and use the default
client ID/secret unless the lab provides its own. Choose ordinary browser OAuth,
not service-account authentication. Answer **yes** when asked to use a browser
for authentication. Copy the complete `http://127.0.0.1:53682/auth?...` link
printed in the terminal into the **same Mac browser/profile already signed in
to UCLA Box**. Approve access there, then return to the terminal and finish
saving the remote. The SSH tunnel carries the browser callback to rclone on
the instance; no token-copy step is needed.

If the link sends you to the regular Box login, sign in to UCLA Box first in
that browser/profile, then reopen the terminal link while rclone is waiting.
Keep credentials out of Git and chat. See [rclone SSH tunnel setup](https://rclone.org/remote_setup/#configuring-using-ssh-tunnel)
and [Box configuration](https://rclone.org/box/).

Check access:

```bash
rclone lsd kelp-box:kelpseg/data
```

## 8. Download testing and training data — on the instance

Use `/home/sky/data` as the artifact root on this instance, outside the checkout.
Allow space for **65.6 GB of chips**, the small controls/tiny example, the Python
environment/model cache, and future checkpoints. Check available space with
`df -h /home/sky`. Treat this home-directory storage as temporary. Back up production outputs
to Box before stopping or deleting the instance.

The root may already exist, but each release destination below must be fresh.
The copy block stops at the first error; for an incomplete transfer, inspect the
failure before continuing.

```bash
(
  set -e
  data_root=/home/sky/data
  for release in data/examples/tiny_ca_bc/v2 data/chips/ca_bc/v1 data/splits/ca_bc/v1 data/collections/ca_bc/v1; do
    if test -e "$data_root/$release"; then
      printf 'Release destination already exists: %s\n' "$data_root/$release" >&2
      exit 1
    fi
  done
  mkdir -p "$data_root/runs"
  for release in data/examples/tiny_ca_bc/v2 data/chips/ca_bc/v1 data/splits/ca_bc/v1 data/collections/ca_bc/v1; do
    rclone copy "kelp-box:kelpseg/$release" "$data_root/$release" \
      --immutable --size-only --ignore-checksum --transfers 1 --checkers 2 --progress
  done
)
```

The [published release inventory](box_backup.md#chip-split-and-collection-cabc-v1)
owns expected counts/sizes. This fetch includes test chips as part of the
canonical release; setup and training checks must not open their arrays.
Raw archives, cleaned TIFFs and Task 033G smoke models are unnecessary for this
baseline. The tiny example contains source inputs; generate its tiny chips with
the [existing walkthrough](quickstart.md#tiny-v2-split-chip-and-load-locally)
after installation, using the same chosen artifact root.

The project-relative release layout is preserved, so chips live at
`/home/sky/data/data/chips/ca_bc/v1`; the repeated `data` is intentional.
Training outputs live under `/home/sky/data/runs`.

Create ignored `paths.local.toml` in the checkout:

```toml
[paths]
data_root = "/home/sky/data"
runs_root = "/home/sky/data/runs"
```

```bash
uv run kelpseg check-paths --paths paths.local.toml
```

## 9. Log in to W&B — on the instance

From the checkout, authenticate interactively:

```bash
uv run wandb login
```

Set `wandb = true` in the training recipe to enable tracking; the installed
trainer uses `kdorman90-ucla/kelpseg`. See [experiment settings](experiments.md).

## Continue Task 034 on this machine

Use `paths.local.toml` from step 8. Generate tiny chips with the
[split/chip walkthrough](quickstart.md#tiny-v2-split-chip-and-load-locally),
using `/home/sky/data` and `example_name=my-tiny-v2-01`.
Then run the checked eight-band CUDA/bf16 smoke:

```bash
uv run kelpseg train --recipe configs/train/tiny_gpu.toml --dry-run
uv run kelpseg train --recipe configs/train/tiny_gpu.toml
```

This uses ImageNet initialization, two epochs with two training batches and one
validation batch each, and writes a fresh `tiny_gpu-*` folder under `runs_root`.
It checks training, validation, best/last saving and portable model export;
its scores are not scientific results. Its short budget does not reach EMA.
Do not use its batch limits or schedule for production.

The full-data launch recipe is `configs/train/planet8_gpu.toml`: native eight
bands with BC (`augmented`), 70 epochs, microbatch 3 × accumulation 8, bf16,
zero loader workers, and W&B at `kdorman90-ucla/kelpseg`. This reference recipe
uses deterministic execution for repeatable GPU continuation. Ordinary
completed-epoch continuation also supports multiple workers; their augmentation
streams restart and sample order may differ. The faster pilot below trades exact
replay for throughput. The original
spectral examples remain available; this machine recipe makes those choices
explicit. Metadata previews open no test arrays.

```bash
uv run kelpseg train --recipe configs/train/planet8_gpu.toml --dry-run
```

The RTX 3090 rehearsal passed EMA and completed-epoch resume comparison
with maximum tensor difference zero (tolerance `atol=1e-5, rtol=1e-4`).
The deterministic batch uses about 4 GiB; budget 25–30 hours for 70 epochs
and 10 GiB for run files and backup snapshots. These are measured projections,
not guarantees. Settle that budget before launch; the task record owns evidence. Commit corrections before production and
keep the running job on that fixed checkout/environment. Use a separate checkout
for Task 035. Never pull code changes into a running experiment.

For completed-epoch continuation, keep the original recipe, total schedule and
saved run identity. Replace the example path with the actual interrupted run:

```bash
uv run kelpseg train --recipe configs/train/planet8_gpu.toml --resume /home/sky/data/runs/ACTUAL_RUN/checkpoints/last.ckpt --dry-run
uv run kelpseg train --recipe configs/train/planet8_gpu.toml --resume /home/sky/data/runs/ACTUAL_RUN/checkpoints/last.ckpt
```

This returns to the last completed epoch; partial-epoch work is discarded.
Resume is for interrupted runs, not runs that already exported `model/`.
CUDA agreement is bounded by the tolerance recorded in Task 034, not a promise
of bitwise reproducibility on every GPU/software combination.

## Twenty-epoch pilot

Use `configs/train/planet8_gpu_20ep_fast.toml` for the throughput-tested pilot:
eight native bands with BC, twenty epochs, W&B enabled, eight persistent workers,
`deterministic = false`, and microbatch 12 × accumulation 2 (effective batch 24).
It retains five warmup epochs and decays over the remaining fifteen. This is a
separate twenty-epoch schedule, not the first twenty epochs of the 70-epoch schedule.
The original `planet8_gpu_10ep.toml` remains available as the batch-3,
zero-worker deterministic reference.

The selected setting measured 47.6 training samples/second and 12.4 GiB peak
GPU allocation on the RTX 3090. Budget roughly **70–90 minutes for twenty epochs**
or **4–5 hours for 70**, including some allowance beyond the short measurements.
Live W&B/network overhead and full-run variation are not measured guarantees.
The benchmark covers 17 cases, including a batch-24 out-of-memory failure;
detailed evidence is in Task 034. More workers were useful only after faster
GPU computation and larger batches exposed a loading bottleneck again.

Larger microbatches change batch-pooled Lovasz loss and batch-normalization
statistics, even with the same effective batch. This is a separate pilot recipe,
not numerically equivalent to the original batch-3 run. Keep microbatch settings
matched when making scientific comparisons. If preserving batch 3 is preferred,
a copied recipe with four persistent workers and `deterministic = false` measured
29 samples/second (roughly four times the original throughput).

Review changes before launch; the user handles commits/pushes and starts the
run. Keep its code and recipe fixed while it runs. Start a fresh pilot with this
changed recipe; continuation of a saved run requires its original settings.
From the checkout, run inside tmux to survive SSH disconnects:

```bash
tmux new -s kelp-pilot-fast
```

Then in that session:

```bash
cd /home/sky/hakai-ml-train
set -o noclobber
uv run --frozen kelpseg train --recipe configs/train/planet8_gpu_20ep_fast.toml > /home/sky/data/runs/planet8-cabc-20ep-fast.log 2>&1
```

Detach with Ctrl-b, then d. Monitor from another terminal with
`tail -f /home/sky/data/runs/planet8-cabc-20ep-fast.log`, or use W&B. The run
creates its own `planet8-cabc-20ep-fast-*` output folder. Choose a fresh log
filename if repeating the pilot; `noclobber` refuses an existing log.
For continuation, use this same fast recipe with the run's `--resume` path.
Training state restores; identical future augmentation draws or weights are not
promised. Back up stable outputs to Box using the procedure below, substituting
this recipe and log filename when copying records.

## Launch and monitor the baseline

After the checks above pass and the run budget is agreed, launch from the fixed
checkout in tmux. This survives SSH disconnects, not instance deletion:

```bash
(
  set -e
  test ! -e /home/sky/data/runs/planet8-gpu-launch.log
  tmux new-session -d -s kelp-baseline -c /home/sky/hakai-ml-train 'uv run --frozen kelpseg train --recipe configs/train/planet8_gpu.toml > /home/sky/data/runs/planet8-gpu-launch.log 2>&1'
)
tmux list-sessions
tail -f /home/sky/data/runs/planet8-gpu-launch.log
```

Use a fresh log filename/session name for a different run. The trainer creates a
unique `planet8-cabc-gpu-*` output folder. `run.json` records its identity,
revision and resolved settings; `metrics/metrics.csv` and W&B show progress.
The first validation should produce distinct `checkpoints/best.ckpt` and
`checkpoints/last.ckpt`. `model/` is exported only when training completes.
Check `nvidia-smi`, advancing log/CSV entries and the W&B run, not just whether
the tmux session exists. A failed process needs inspection before continuation.

## Back up completed outputs to Box

Treat `/home/sky/data` as temporary. Just after an epoch completes and training
moves into the next epoch, copy its stable checkpoints plus current records to
a fresh snapshot directory. Use the actual run ID and completed epoch below;
change the snapshot name for each backup. Do not copy a checkpoint while it is
being saved. This is an explicit copy, not an automatic backup service.

```bash
(
  set -e
  run_id='ACTUAL_RUN'
  run="/home/sky/data/runs/$run_id"
  snapshot="/home/sky/data/backups/$run_id/epoch-001"
  test ! -e "$snapshot"
  mkdir -p "$snapshot"
  cp "$run/settings.json" "$run/run.json" "$snapshot/"
  cp -a "$run/checkpoints" "$run/metrics" "$snapshot/"
  cp configs/train/planet8_gpu.toml "$snapshot/recipe.toml"
  git rev-parse HEAD > "$snapshot/git-commit.txt"
  cp /home/sky/data/runs/planet8-gpu-launch.log "$snapshot/launch.log"
  rclone copy "$snapshot" "kelp-box:kelpseg/runs/$run_id/epoch-001" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
  rclone size "$snapshot"
  rclone size "kelp-box:kelpseg/runs/$run_id/epoch-001"
)
```

At completion, make another fresh `final` snapshot and include `model/` along
with settings, checkpoints, metrics and logs. Check local/Box file counts and
sizes. Keep the fixed Git revision and machine roots with the handoff. Avoid
copying the entire environment or regenerable chip data into each backup.

To restore an interrupted run, choose a fresh `runs_root/<saved-run-id>` and
copy the selected Box snapshot there. Keep the same run ID, original recipe and
total epochs; set the recipe's `paths_file` to the new machine's settings.
Restore the published data separately, then use the resume preview and command
above. A completed final model is loaded directly for prediction, not resumed.
