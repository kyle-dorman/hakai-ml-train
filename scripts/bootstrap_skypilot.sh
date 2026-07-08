#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a disposable SkyPilot instance for this repository.
# The script is intentionally idempotent: rerunning it should repair missing
# setup pieces without forcing a full redownload unless requested.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEFAULT_DATA_URL="https://caltech.app.box.com/s/d5vg0b8h613vvlsawms9yo8p2pc3tplw"

DATA_URL="${HAKAI_DATA_URL:-$DEFAULT_DATA_URL}"
DATA_ROOT="${HAKAI_DATA_ROOT:-$HOME/data}"
COMPAT_DATA_ROOT="${HAKAI_COMPAT_DATA_ROOT:-/home/taylor/data}"
DOWNLOAD_DIR="${HAKAI_DOWNLOAD_DIR:-$DATA_ROOT/.downloads}"
ARCHIVE_NAME="${HAKAI_DATA_ARCHIVE_NAME:-hakai-data-archive}"
UV_SYNC_ARGS="${HAKAI_UV_SYNC_ARGS:---frozen}"

DRY_RUN=0
FORCE_DOWNLOAD="${HAKAI_FORCE_DOWNLOAD:-0}"
FORCE_EXTRACT="${HAKAI_FORCE_EXTRACT:-0}"
SKIP_APT="${HAKAI_SKIP_APT:-0}"
SKIP_UV_SYNC="${HAKAI_SKIP_UV_SYNC:-0}"
SKIP_DATA="${HAKAI_SKIP_DATA:-0}"
SKIP_WANDB_LOGIN="${HAKAI_SKIP_WANDB_LOGIN:-0}"
CREATE_COMPAT_SYMLINK="${HAKAI_CREATE_COMPAT_SYMLINK:-1}"

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap_skypilot.sh [options]

Options:
  --dry-run          Print the actions without changing the instance.
  --force-download   Redownload the data archive even if it already exists.
  --force-extract    Extract the data archive again even if the marker exists.
  --skip-apt         Do not install missing apt packages.
  --skip-uv-sync     Do not run uv sync.
  --skip-data        Do not download or extract the data archive.
  --help             Show this help.

Environment overrides:
  HAKAI_DATA_URL                  Data archive/share URL.
  HAKAI_DATA_ROOT                 Extracted data root. Default: $HOME/data
  HAKAI_COMPAT_DATA_ROOT          Compatibility symlink path. Default: /home/taylor/data
  HAKAI_UV_SYNC_ARGS              uv sync flags. Default: --frozen
  WANDB_API_KEY                   If set, run wandb login after uv sync.
  HAKAI_FORCE_DOWNLOAD=1          Same as --force-download.
  HAKAI_FORCE_EXTRACT=1           Same as --force-extract.
  HAKAI_SKIP_APT=1                Same as --skip-apt.
  HAKAI_SKIP_UV_SYNC=1            Same as --skip-uv-sync.
  HAKAI_SKIP_DATA=1               Same as --skip-data.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    --force-download)
      FORCE_DOWNLOAD=1
      ;;
    --force-extract)
      FORCE_EXTRACT=1
      ;;
    --skip-apt)
      SKIP_APT=1
      ;;
    --skip-uv-sync)
      SKIP_UV_SYNC=1
      ;;
    --skip-data)
      SKIP_DATA=1
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

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

have_sudo() {
  have_cmd sudo && sudo -n true >/dev/null 2>&1
}

install_system_packages() {
  [[ "$SKIP_APT" == "1" ]] && return

  if ! have_cmd apt-get; then
    return
  fi

  local missing=()
  for cmd in curl file unzip; do
    if ! have_cmd "$cmd"; then
      missing+=("$cmd")
    fi
  done

  if [[ "${#missing[@]}" -eq 0 ]]; then
    return
  fi

  if [[ "$(id -u)" -eq 0 ]]; then
    log "Installing missing system packages: ${missing[*]}"
    run apt-get update
    run apt-get install -y ca-certificates curl file unzip
  elif have_sudo; then
    log "Installing missing system packages: ${missing[*]}"
    run sudo apt-get update
    run sudo apt-get install -y ca-certificates curl file unzip
  else
    warn "Missing system commands (${missing[*]}), and passwordless sudo is unavailable."
    warn "Install ca-certificates, curl, file, and unzip manually, or rerun with HAKAI_SKIP_APT=1 after they exist."
  fi
}

ensure_uv() {
  if have_cmd uv; then
    return
  fi

  log "Installing uv"
  if [[ "$DRY_RUN" == "1" ]]; then
    printf '+ curl -LsSf https://astral.sh/uv/install.sh | sh\n'
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi

  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

  if [[ "$DRY_RUN" == "1" ]]; then
    return
  fi

  if ! have_cmd uv; then
    die "uv was installed, but it is not on PATH. Try: export PATH=\"\$HOME/.local/bin:\$HOME/.cargo/bin:\$PATH\""
  fi
}

sync_python_environment() {
  [[ "$SKIP_UV_SYNC" == "1" ]] && return

  log "Syncing Python environment"
  cd "$REPO_ROOT"

  # shellcheck disable=SC2206
  local uv_args=($UV_SYNC_ARGS)
  run uv sync "${uv_args[@]}"
}

wandb_login_if_configured() {
  [[ "$SKIP_WANDB_LOGIN" == "1" ]] && return

  if [[ -z "${WANDB_API_KEY:-}" ]]; then
    warn "WANDB_API_KEY is not set. Training can still run, but W&B configs may prompt for login."
    return
  fi

  if [[ "$SKIP_UV_SYNC" == "1" ]]; then
    warn "Skipping W&B login because uv sync was skipped."
    return
  fi

  log "Logging into Weights & Biases"
  cd "$REPO_ROOT"
  run uv run wandb login --relogin "$WANDB_API_KEY"
}

download_url_for() {
  local url="$1"
  case "$url" in
    *box.com/s/*)
      if [[ "$url" == *\?* ]]; then
        printf '%s&download=1' "$url"
      else
        printf '%s?download=1' "$url"
      fi
      ;;
    *)
      printf '%s' "$url"
      ;;
  esac
}

archive_mime_type() {
  local archive="$1"
  if have_cmd file; then
    file -b --mime-type "$archive"
  else
    printf 'application/octet-stream'
  fi
}

download_data_archive() {
  [[ "$SKIP_DATA" == "1" ]] && return

  run mkdir -p "$DOWNLOAD_DIR"

  local archive_path="$DOWNLOAD_DIR/$ARCHIVE_NAME"
  local part_path="$archive_path.part"
  local resolved_url
  resolved_url="$(download_url_for "$DATA_URL")"

  if [[ -s "$archive_path" && "$FORCE_DOWNLOAD" != "1" ]]; then
    log "Using existing data archive: $archive_path"
  else
    log "Downloading data archive"
    printf 'URL: %s\n' "$DATA_URL"
    if ! run curl -fL --retry 5 --retry-delay 5 --continue-at - --output "$part_path" "$resolved_url"; then
      die "Could not download the data archive. If this is a Box share that returns 404 or requires auth, create/request a direct .zip/.tar archive URL and pass it with HAKAI_DATA_URL."
    fi
    run mv "$part_path" "$archive_path"
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    return
  fi

  local mime
  mime="$(archive_mime_type "$archive_path")"
  case "$mime" in
    text/html|text/plain)
      die "Downloaded $mime instead of a data archive. The Box share may be unavailable or not directly downloadable. Set HAKAI_DATA_URL to a direct .zip/.tar archive URL and rerun with --force-download."
      ;;
  esac
}

extract_data_archive() {
  [[ "$SKIP_DATA" == "1" ]] && return

  local archive_path="$DOWNLOAD_DIR/$ARCHIVE_NAME"
  local marker="$DATA_ROOT/.bootstrap-extracted"

  if [[ -f "$marker" && "$FORCE_EXTRACT" != "1" ]]; then
    log "Data already extracted: $DATA_ROOT"
    return
  fi

  [[ -f "$archive_path" || "$DRY_RUN" == "1" ]] || die "Data archive is missing: $archive_path"

  log "Extracting data archive into $DATA_ROOT"
  run mkdir -p "$DATA_ROOT"

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '+ extract archive based on file type\n'
    return
  fi

  local mime
  mime="$(archive_mime_type "$archive_path")"
  case "$mime" in
    application/zip|application/x-zip-compressed)
      unzip -q -o "$archive_path" -d "$DATA_ROOT"
      ;;
    application/gzip|application/x-gzip|application/x-tar|application/x-bzip2|application/x-xz|application/zstd)
      tar -xf "$archive_path" -C "$DATA_ROOT"
      ;;
    application/octet-stream)
      case "$archive_path" in
        *.zip)
          unzip -q -o "$archive_path" -d "$DATA_ROOT"
          ;;
        *.tar|*.tar.gz|*.tgz|*.tar.bz2|*.tbz2|*.tar.xz|*.txz)
          tar -xf "$archive_path" -C "$DATA_ROOT"
          ;;
        *)
          die "Could not identify archive type for $archive_path. Rename it with .zip/.tar.gz or set HAKAI_DATA_ARCHIVE_NAME with an extension."
          ;;
      esac
      ;;
    *)
      die "Unsupported archive MIME type for $archive_path: $mime"
      ;;
  esac

  date -u +%Y-%m-%dT%H:%M:%SZ > "$marker"
}

ensure_compat_data_root() {
  [[ "$CREATE_COMPAT_SYMLINK" == "1" ]] || return
  [[ -n "$COMPAT_DATA_ROOT" ]] || return

  if [[ "$COMPAT_DATA_ROOT" == "$DATA_ROOT" ]]; then
    run mkdir -p "$DATA_ROOT"
    return
  fi

  if [[ -L "$COMPAT_DATA_ROOT" ]]; then
    local target
    target="$(readlink "$COMPAT_DATA_ROOT")"
    if [[ "$target" == "$DATA_ROOT" ]]; then
      log "Compatibility data symlink already exists: $COMPAT_DATA_ROOT -> $DATA_ROOT"
      return
    fi
    warn "$COMPAT_DATA_ROOT already points to $target; leaving it unchanged."
    return
  fi

  if [[ -e "$COMPAT_DATA_ROOT" ]]; then
    warn "$COMPAT_DATA_ROOT already exists and is not a symlink; leaving it unchanged."
    return
  fi

  log "Creating compatibility symlink for existing config paths"
  local parent
  parent="$(dirname "$COMPAT_DATA_ROOT")"

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '+ mkdir -p %q\n' "$parent"
    printf '+ ln -s %q %q\n' "$DATA_ROOT" "$COMPAT_DATA_ROOT"
  elif [[ -w "$parent" ]]; then
    mkdir -p "$parent"
    ln -s "$DATA_ROOT" "$COMPAT_DATA_ROOT"
  elif have_sudo; then
    sudo mkdir -p "$parent"
    sudo ln -s "$DATA_ROOT" "$COMPAT_DATA_ROOT"
  else
    warn "Cannot create $COMPAT_DATA_ROOT without write access or passwordless sudo."
    warn "Either rerun with sudo, or pass Lightning overrides for data.init_args.*_chip_dir."
  fi
}

validate_config_data_paths() {
  log "Checking data paths referenced by configs"

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '+ grep config files for /home/taylor/data paths and report missing directories\n'
    return
  fi

  local paths_file
  paths_file="$(mktemp)"
  grep -RhoE '/home/taylor/data[^"[:space:]]+' "$REPO_ROOT/configs" | sort -u > "$paths_file" || true

  if [[ ! -s "$paths_file" ]]; then
    warn "No /home/taylor/data paths were found in configs."
    rm -f "$paths_file"
    return
  fi

  local present=0
  local missing=0
  local path
  while IFS= read -r path; do
    if [[ -d "$path" ]]; then
      local count
      count="$(find "$path" -maxdepth 1 -name '*.npz' | wc -l | tr -d ' ')"
      printf 'OK   %s (%s npz files)\n' "$path" "$count"
      present=$((present + 1))
    else
      printf 'MISS %s\n' "$path"
      missing=$((missing + 1))
    fi
  done < "$paths_file"
  rm -f "$paths_file"

  if [[ "$present" -eq 0 && "$SKIP_DATA" != "1" ]]; then
    warn "None of the hard-coded config data paths exist yet."
    warn "If the archive extracted under an extra top-level folder, move or symlink its dataset directories under $DATA_ROOT."
  elif [[ "$missing" -gt 0 ]]; then
    warn "$missing config data paths are still missing. This is fine if you only need a subset of configs."
  fi
}

print_next_steps() {
  cat <<EOF

Bootstrap complete.

Data root:
  $DATA_ROOT

Compatibility root used by existing configs:
  $COMPAT_DATA_ROOT

Example training command:
  uv run python trainer.py fit --config configs/kelp-rgb/segformer_b3.yaml

To use a fixed direct data archive URL:
  HAKAI_DATA_URL="https://..." scripts/bootstrap_skypilot.sh --force-download
EOF
}

main() {
  log "Bootstrapping Hakai ML Train for SkyPilot"
  printf 'Repo: %s\n' "$REPO_ROOT"

  install_system_packages
  ensure_uv
  sync_python_environment
  wandb_login_if_configured
  download_data_archive
  extract_data_archive
  ensure_compat_data_root
  validate_config_data_paths
  print_next_steps
}

main "$@"
