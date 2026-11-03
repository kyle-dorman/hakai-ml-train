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

Use the alias from your launch, for example:

```bash
ssh sky-79fd-kyledorman
```

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

```bash
rclone config
```

Create a remote named `kelp-box`, choose storage type `box`, and use the default
client ID/secret unless the lab provides its own. Choose ordinary browser OAuth,
not service-account authentication. Answer **no** when asked to open a browser
on the headless instance. Run the authorization command it prints on your Mac
(typically `rclone authorize "box"`), log in with the UCLA Box account that can
access `kelpseg`, then paste the returned token into the instance's prompt.
Keep credentials out of Git and chat. See [rclone headless setup](https://rclone.org/remote_setup/)
and [Box configuration](https://rclone.org/box/).

Check access:

```bash
rclone lsd kelp-box:kelpseg/data
```

## 8. Download testing and training data — on the instance

Choose a persistent mounted disk with space for **65.6 GB of chips**, the small
controls/tiny example, the Python environment/model cache, and future checkpoints.
Confirm the mount survives the instance lifecycle; `$HOME` is not automatically
persistent. Below, replace `/mnt/persistent/kelpseg` with the chosen absolute path.
Use a fresh artifact directory outside the checkout. The copy block stops at the
first error; for an incomplete transfer, inspect the failure before continuing.

```bash
(
  set -e
  data_root=/mnt/persistent/kelpseg
  test ! -e "$data_root"
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

Create ignored `paths.local.toml` in the checkout, using your actual paths:

```toml
[paths]
data_root = "/mnt/persistent/kelpseg"
runs_root = "/mnt/persistent/kelpseg/runs"
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
