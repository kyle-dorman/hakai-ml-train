#!/usr/bin/env bash
# Run after cloning, as the normal user who will own the environment and runs.
set -euo pipefail

if [[ "${1:-}" == "--help" && $# -eq 1 ]]; then
  printf 'Usage: bash bootstrap_gpu.sh\n\n'
  printf 'Ubuntu/Debian setup: apt update/upgrade, dependencies, uv, Python 3.12,\n'
  printf 'frozen project environment, rclone, tmux and Codex. Requires sudo.\n'
  exit 0
fi
if [[ $# -ne 0 ]]; then
  printf 'Unknown argument. Use bash bootstrap_gpu.sh --help.\n' >&2
  exit 2
fi

if [[ "$(uname -s)" != "Linux" ]] || ! command -v apt-get >/dev/null; then
  printf 'Run this setup on an Ubuntu/Debian Linux GPU host with apt-get.\n' >&2
  exit 1
fi
if [[ ! -r /etc/os-release ]]; then
  printf 'Cannot identify this Linux host: /etc/os-release is missing.\n' >&2
  exit 1
fi
. /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) printf 'Unsupported Linux distribution: %s. Use Ubuntu or Debian.\n' "${ID:-unknown}" >&2; exit 1 ;;
esac
if [[ "$(id -u)" -eq 0 ]]; then
  printf 'Run as your normal login user, not root or sudo; only apt uses sudo.\n' >&2
  exit 1
fi
if ! command -v sudo >/dev/null; then
  printf 'sudo is required for apt; ask the host administrator to enable it.\n' >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$repo_root"
if [[ ! -f pyproject.toml || ! -f uv.lock ]]; then
  printf 'Keep bootstrap_gpu.sh at the root of the cloned repository.\n' >&2
  exit 1
fi

printf '\n==> Updating Ubuntu/Debian packages\n'
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl git build-essential pkg-config unzip rclone tmux vim

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null; then
  printf '\n==> Installing uv for this user\n'
  curl --fail --show-error --silent --location https://astral.sh/uv/install.sh | sh
fi
uv --version
printf '\n==> Installing the frozen Python 3.12 environment\n'
uv python install 3.12
uv sync --python 3.12 --frozen

if ! command -v codex >/dev/null; then
  printf '\n==> Installing Codex for this user\n'
  curl --fail --show-error --silent --location https://chatgpt.com/codex/install.sh | \
    CODEX_NON_INTERACTIVE=1 sh
fi
codex --version
rclone version
tmux -V

printf '\nSetup complete. Follow docs/gpu_setup.md for Box authentication,\n'
printf 'machine paths, CUDA checks and the separate training launch.\n'
if [[ -f /var/run/reboot-required ]]; then
  printf 'The operating system requests a reboot before continuing.\n'
fi
