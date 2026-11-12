# Set up the external GPU machine

Use this checklist to reach the Linux instance and validate training there.
The Ubuntu 20.04 / RTX 3090 installation, frozen environment, CUDA/bf16, Box
data staging and tiny training have been checked on the allocated host.
For measured sizing and past launches, see [historical GPU recipes](reference/historical_gpu_recipes.md).
Repeat readiness checks on each new host before production.

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

Choose the intended committed revision and keep it fixed during a run. Confirm
`bootstrap_gpu.sh` exists before continuing.

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
  for release in data/chips/ca_bc/v1 data/splits/ca_bc/v1 data/collections/ca_bc/v1; do
    if test -e "$data_root/$release"; then
      printf 'Release destination already exists: %s\n' "$data_root/$release" >&2
      exit 1
    fi
  done
  mkdir -p "$data_root/runs"
  for release in data/chips/ca_bc/v1 data/splits/ca_bc/v1 data/collections/ca_bc/v1; do
    rclone copy "kelp-box:kelpseg/$release" "$data_root/$release" \
      --immutable --size-only --ignore-checksum --transfers 1 --checkers 2 --progress
  done
)
```

The [published release inventory](reference/ca_bc_release.md#chip-split-and-collection-cabc-v1)
owns expected counts/sizes. This fetch includes test chips as part of the
canonical release; setup and training checks must not open their arrays.
Raw archives and cleaned TIFFs are unnecessary for chip-based training;
source-TIFF prediction/reporting needs the separate cleaned release. Fetch and
prepare the tiny example separately under a fresh root using the
[tiny walkthrough](quickstart.md); step 10 uses that walkthrough root for its
bounded CUDA check. Production recipes use the full-release root above.

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

## 10. Check CUDA readiness

Follow the [tiny walkthrough](quickstart.md) through chipping first, using its
chosen fresh artifact root and `data_root` shell variable. Its chip and split
paths match `configs/train/tiny_gpu.toml`. Copy the GPU smoke recipe beside the
walkthrough's `paths.toml` and change only the machine-path reference:

```bash
(
  set -e
  nvidia-smi
  test ! -e "$data_root/work/tiny-gpu.toml"
  sed 's|^paths_file = .*|paths_file = "paths.toml"|' \
    configs/train/tiny_gpu.toml > "$data_root/work/tiny-gpu.toml"
  uv run --frozen kelpseg train --recipe "$data_root/work/tiny-gpu.toml" --dry-run
  uv run --frozen kelpseg train --recipe "$data_root/work/tiny-gpu.toml"
)
```

Run each command only after the preceding command succeeds. This checks
ImageNet weight access, CUDA/bf16 training and validation, best/last checkpoints,
and portable model export. It uses two epochs, two training batches and one
validation batch per epoch; it does not reach EMA and its scores are not research
results. Inspect the printed run directory and copy/load its bundle as in the
tiny walkthrough. For resume behavior and reproducibility limits, use the
[training guide](guides/training.md#resume-after-a-completed-epoch).

## Launch and monitor a new run

The [selected B0 model and recipe](experiments.md#current-planet-8-band-b0-baseline)
are the reference for production planning. Preview a copied recipe with
`train --dry-run` before launch. Use a distinct name and preserve the committed
code, resolved settings and full schedule for that experiment. Do not change a
running checkout. Production capacity and timing depend on the host and recipe;
old benchmarks are [historical measurements](reference/historical_gpu_recipes.md).

Start `tmux new -s kelp-training`, then run the chosen command inside it:

```bash
set -o noclobber
uv run --frozen kelpseg train --recipe /absolute/path/to/recipe.toml > /absolute/path/to/fresh-training.log 2>&1
```

Replace both paths first. Detach with Ctrl-b, then d; use `tmux attach -t
kelp-training` to return. Monitor `nvidia-smi`, the log, `metrics/metrics.csv`
and W&B when enabled. An existing tmux session alone does not establish progress.
`run.json` records run identity and revision. `checkpoints/best.ckpt` and
`checkpoints/last.ckpt` have different roles; `model/` is exported at completion.
Inspect failures before using the supported completed-epoch resume procedure.
Tmux survives a disconnected SSH session, not deletion of the instance.

## Back up completed outputs to Box

Treat host storage as temporary. For a completed run, copy its settings, run
record, checkpoints, metrics, exported `model/`, recipe and launch log to a fresh
external snapshot. For an interrupted run, use a stable checkpoint after the
process stops; do not copy a checkpoint while it is being written. Preserve
its run ID and Git revision.

```bash
(
  set -e
  snapshot='/absolute/path/to/completed-snapshot'
  backup='kelp-box:kelpseg/runs/UNIQUE_RUN/final'
  rclone copy "$snapshot" "$backup" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
  rclone size "$snapshot"
  rclone size "$backup"
)
```

Replace the paths with the prepared snapshot and a fresh destination. Compare
relative paths, counts and sizes, then restore/load a bounded sample before
relying on the backup. See [Box operations](box_backup.md) for storage policy and
release restoration. Do not copy an environment or duplicate the full chip release
inside every run backup.

Restore the complete interrupted-run folder, including both `best.ckpt` and
`last.ckpt`, under a fresh `runs_root/<saved-run-id>` on the new machine. A lone
`last.ckpt` is not a complete relocation: validation selection may still need
the previous best checkpoint. Restore data separately and update only machine
paths. Keep the original recipe and total schedule; use the [resume guide](guides/training.md#resume-after-a-completed-epoch).
Load a completed portable model directly for prediction. The supported increase
in early-stopping patience is documented in the training guide; it is not a new
experiment with altered data or preprocessing.
