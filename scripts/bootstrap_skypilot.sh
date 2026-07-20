#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON_VERSION="${HAKAI_PYTHON_VERSION:-3.12}"
UV_SYNC_ARGS="${HAKAI_UV_SYNC_ARGS:---frozen}"

SKIP_SYSTEM_UPGRADE="${HAKAI_SKIP_SYSTEM_UPGRADE:-0}"
SKIP_NVIDIA_CHECK="${HAKAI_SKIP_NVIDIA_CHECK:-0}"
SKIP_UV_SYNC=0
SKIP_WANDB=0
SKIP_CODEX="${HAKAI_SKIP_CODEX:-0}"

log() {
  printf '\n==> %s\n' "$*"
}

warn() {
  printf 'WARN: %s\n' "$*" >&2
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

usage() {
  cat <<EOF
Usage: scripts/bootstrap_skypilot.sh [options]

Options:
  --skip-upgrade      Do not run apt-get update/upgrade.
  --skip-nvidia-check Do not check nvidia-smi or PyTorch CUDA.
  --skip-uv-sync      Do not run uv sync.
  --skip-wandb        Do not run wandb login.
  --skip-codex        Do not install or check the Codex CLI.
  --help              Show this help.

Useful environment variables:
  WANDB_API_KEY       Used for non-interactive W&B login.
  HAKAI_UV_SYNC_ARGS  Extra uv sync flags. Default: --frozen
  HAKAI_SKIP_SYSTEM_UPGRADE=1
  HAKAI_SKIP_NVIDIA_CHECK=1
  HAKAI_SKIP_CODEX=1
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-upgrade)
      SKIP_SYSTEM_UPGRADE=1
      ;;
    --skip-nvidia-check)
      SKIP_NVIDIA_CHECK=1
      ;;
    --skip-uv-sync)
      SKIP_UV_SYNC=1
      ;;
    --skip-wandb)
      SKIP_WANDB=1
      ;;
    --skip-codex)
      SKIP_CODEX=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

run_as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif have_cmd sudo && sudo -n true >/dev/null 2>&1; then
    sudo "$@"
  else
    return 1
  fi
}

upgrade_system_packages() {
  [[ "$SKIP_SYSTEM_UPGRADE" == "1" ]] && return
  have_cmd apt-get || {
    warn "apt-get not found; skipping system package upgrade."
    return
  }

  log "Upgrading system packages"
  if ! run_as_root apt-get update; then
    warn "Could not run apt-get update; skipping system package upgrade."
    return
  fi
  run_as_root env DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
  run_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git gzip tar
}

ensure_uv() {
  if have_cmd uv; then
    return
  fi

  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  have_cmd uv || die "uv is not on PATH after install"
}

ensure_codex() {
  [[ "$SKIP_CODEX" == "1" ]] && return

  export PATH="$HOME/.local/bin:$PATH"
  if ! have_cmd codex; then
    have_cmd curl || die "curl is required to install the Codex CLI"
    log "Installing Codex CLI"
    curl -fsSL https://chatgpt.com/codex/install.sh | \
      CODEX_NON_INTERACTIVE=1 sh
    export PATH="$HOME/.local/bin:$PATH"
    have_cmd codex || die "codex is not on PATH after install"
  fi

  log "Checking Codex CLI"
  codex --version
  if ! codex login status >/dev/null 2>&1; then
    warn "Codex is not authenticated. Run: codex login --device-auth"
  fi
}

sync_python_environment() {
  [[ "$SKIP_UV_SYNC" == "1" ]] && return

  log "Syncing Python environment"
  cd "$REPO_ROOT"

  # shellcheck disable=SC2206
  local uv_args=($UV_SYNC_ARGS)
  uv python install "$PYTHON_VERSION"
  uv sync --python "$PYTHON_VERSION" "${uv_args[@]}"
}

check_nvidia_setup() {
  [[ "$SKIP_NVIDIA_CHECK" == "1" ]] && return

  log "Checking NVIDIA driver"
  have_cmd nvidia-smi || die "nvidia-smi was not found. Use a GPU image/instance or rerun with --skip-nvidia-check."
  nvidia-smi

  [[ "$SKIP_UV_SYNC" == "1" ]] && {
    warn "Skipping PyTorch CUDA check because uv sync was skipped."
    return
  }

  log "Checking PyTorch CUDA"
  cd "$REPO_ROOT"
  uv run python - <<'PY'
import torch

print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("cuda version:", torch.version.cuda)
print("device count:", torch.cuda.device_count())
if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
    raise SystemExit("PyTorch cannot see CUDA.")
for i in range(torch.cuda.device_count()):
    print(f"{i}: {torch.cuda.get_device_name(i)}")
x = torch.randn(1024, 1024, device="cuda")
print("cuda allocation test:", float(x.mean()))
PY
}

wandb_login() {
  [[ "$SKIP_WANDB" == "1" ]] && return

  local key="${WANDB_API_KEY:-}"
  if [[ -z "$key" && -t 0 ]]; then
    printf 'W&B API key (leave blank to skip): '
    read -r -s key
    printf '\n'
  fi
  [[ -n "$key" ]] || {
    warn "Skipping W&B login; WANDB_API_KEY was not provided."
    return
  }

  log "Logging into Weights & Biases"
  cd "$REPO_ROOT"
  uv run wandb login --relogin "$key"
}

main() {
  log "Bootstrapping Hakai ML Train"
  printf 'Repo: %s\n' "$REPO_ROOT"

  upgrade_system_packages
  ensure_codex
  ensure_uv
  sync_python_environment
  check_nvidia_setup
  wandb_login

  cat <<EOF

Done.
EOF
}

main "$@"
