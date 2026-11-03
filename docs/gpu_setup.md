# Set up the external GPU machine

Task 034 is remote-first: use this checklist to reach the Linux instance, then
validate and improve the setup there. This guide and bootstrap have local syntax
and mock checks only; the Linux installation and CUDA workflow remain unverified.
Commit and push this setup work before cloning it remotely.

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
`df -h /home/sky`. Confirm with the lab what survives instance shutdown or deletion;
this home-directory path is not a guarantee of persistent storage.

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

Record the OS, GPU/driver, installed versions, revision and storage paths in the
[Task 034 outcome](../tasks/034_gpu_machine_preparation_and_baseline_launch.md).
Then validate CUDA/bf16, tiny training/validation, save/load and completed-epoch
resume, and measure a representative training batch before launching one baseline.
Preview all four spectral recipes and both variants without production fitting.
Keep `num_workers=0`, `persistent_workers=false`, the same total schedule and the
saved run identity for resume. The existing production examples need worker
settings adjusted before that rehearsal.

Write the tested GPU recipe and launch/monitor/backup commands here as we verify
them remotely. Commit corrections before production, then keep the running job
on that fixed checkout/environment. Bring those commits back locally and use a
separate checkout for Task 035. Task 034 ends with a healthy first epoch and a
clear monitoring handoff; inference/scoring belong to later tasks.
