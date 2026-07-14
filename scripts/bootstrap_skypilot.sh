#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHON_VERSION="${HAKAI_PYTHON_VERSION:-3.12}"
UV_SYNC_ARGS="${HAKAI_UV_SYNC_ARGS:---frozen}"
DATA_ROOT="${HAKAI_DATA_ROOT:-$HOME/data}"
COMPAT_DATA_ROOT="${HAKAI_COMPAT_DATA_ROOT:-/home/taylor/data}"
EXTRACT_DIR="${HAKAI_EXTRACT_DIR:-$DATA_ROOT/PlanetScope/pre-chipped-8b}"
DATASET_NAME="${HAKAI_DATASET_NAME:-1024_512_20250814_cali_bc}"
ARCHIVE="${HAKAI_DATA_ARCHIVE:-}"

FORCE_EXTRACT=0
SKIP_DATA=0
SKIP_UV_SYNC=0
SKIP_WANDB=0

usage() {
  cat <<EOF
Usage: scripts/bootstrap_skypilot.sh [options]

Options:
  --archive PATH      Tarball copied to the instance. Default: ~/${DATASET_NAME}.tar.gz
  --data-root PATH    Data root. Default: \$HOME/data
  --extract-dir PATH  Extraction parent. Default: \$HAKAI_DATA_ROOT/PlanetScope/pre-chipped-8b
  --force-extract     Re-extract even if the dataset directory already exists.
  --skip-data         Do not extract the dataset archive.
  --skip-uv-sync      Do not run uv sync.
  --skip-wandb        Do not run wandb login.
  --help              Show this help.

Useful environment variables:
  WANDB_API_KEY       Used for non-interactive W&B login.
  HAKAI_UV_SYNC_ARGS  Extra uv sync flags. Default: --frozen
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --archive)
      [[ $# -ge 2 ]] || die "--archive requires a path"
      ARCHIVE="$2"
      shift
      ;;
    --data-root)
      [[ $# -ge 2 ]] || die "--data-root requires a path"
      DATA_ROOT="$2"
      EXTRACT_DIR="$DATA_ROOT/PlanetScope/pre-chipped-8b"
      shift
      ;;
    --extract-dir)
      [[ $# -ge 2 ]] || die "--extract-dir requires a path"
      EXTRACT_DIR="$2"
      shift
      ;;
    --force-extract)
      FORCE_EXTRACT=1
      ;;
    --skip-data)
      SKIP_DATA=1
      ;;
    --skip-uv-sync)
      SKIP_UV_SYNC=1
      ;;
    --skip-wandb)
      SKIP_WANDB=1
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

ensure_uv() {
  if have_cmd uv; then
    return
  fi

  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  have_cmd uv || die "uv is not on PATH after install"
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

default_archive_path() {
  local home_archive="$HOME/${DATASET_NAME}.tar.gz"
  local repo_archive="$REPO_ROOT/${DATASET_NAME}.tar.gz"

  if [[ -n "$ARCHIVE" ]]; then
    printf '%s\n' "$ARCHIVE"
  elif [[ -f "$home_archive" ]]; then
    printf '%s\n' "$home_archive"
  elif [[ -f "$repo_archive" ]]; then
    printf '%s\n' "$repo_archive"
  else
    printf '%s\n' "$home_archive"
  fi
}

extract_dataset() {
  [[ "$SKIP_DATA" == "1" ]] && return

  local archive_path
  archive_path="$(default_archive_path)"
  archive_path="${archive_path/#\~/$HOME}"

  local dataset_dir="$EXTRACT_DIR/$DATASET_NAME"
  if [[ -d "$dataset_dir/train" && -d "$dataset_dir/val" && -d "$dataset_dir/test" && "$FORCE_EXTRACT" != "1" ]]; then
    log "Dataset already extracted: $dataset_dir"
    return
  fi

  [[ -f "$archive_path" ]] || die "Archive not found: $archive_path"

  log "Extracting dataset"
  mkdir -p "$EXTRACT_DIR"
  tar -xzf "$archive_path" -C "$EXTRACT_DIR"

  [[ -d "$dataset_dir/train" && -d "$dataset_dir/val" && -d "$dataset_dir/test" ]] || \
    die "Expected train/val/test under $dataset_dir after extraction"
}

create_compat_symlink() {
  [[ -n "$COMPAT_DATA_ROOT" ]] || return
  [[ "$COMPAT_DATA_ROOT" != "$DATA_ROOT" ]] || return

  if [[ -L "$COMPAT_DATA_ROOT" && "$(readlink "$COMPAT_DATA_ROOT")" == "$DATA_ROOT" ]]; then
    return
  fi
  if [[ -e "$COMPAT_DATA_ROOT" ]]; then
    warn "$COMPAT_DATA_ROOT already exists; leaving it unchanged."
    return
  fi

  local parent
  parent="$(dirname "$COMPAT_DATA_ROOT")"
  if [[ -w "$parent" ]]; then
    mkdir -p "$parent"
    ln -s "$DATA_ROOT" "$COMPAT_DATA_ROOT"
  elif have_cmd sudo && sudo -n true >/dev/null 2>&1; then
    sudo mkdir -p "$parent"
    sudo ln -s "$DATA_ROOT" "$COMPAT_DATA_ROOT"
  else
    warn "Could not create compatibility symlink: $COMPAT_DATA_ROOT -> $DATA_ROOT"
  fi
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

  ensure_uv
  sync_python_environment
  extract_dataset
  create_compat_symlink
  wandb_login

  cat <<EOF

Done.

Dataset:
  $EXTRACT_DIR/$DATASET_NAME

Compatibility data root:
  $COMPAT_DATA_ROOT
EOF
}

main "$@"
