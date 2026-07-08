#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a disposable SkyPilot instance for this repository.
# The script is intentionally idempotent: rerunning it should repair missing
# setup pieces without forcing a full redownload unless requested.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEFAULT_BOX_SHARED_NAME="d5vg0b8h613vvlsawms9yo8p2pc3tplw"
DEFAULT_DATA_URL="https://caltech.app.box.com/s/$DEFAULT_BOX_SHARED_NAME"

DATA_URL="${HAKAI_DATA_URL:-$DEFAULT_DATA_URL}"
DATA_ROOT="${HAKAI_DATA_ROOT:-$HOME/data}"
COMPAT_DATA_ROOT="${HAKAI_COMPAT_DATA_ROOT:-/home/taylor/data}"
DOWNLOAD_DIR="${HAKAI_DOWNLOAD_DIR:-$DATA_ROOT/.downloads}"
ARCHIVE_NAME="${HAKAI_DATA_ARCHIVE_NAME:-hakai-data-archive}"
UV_SYNC_ARGS="${HAKAI_UV_SYNC_ARGS:---frozen}"
PYTHON_VERSION="${HAKAI_PYTHON_VERSION:-3.12}"

STATIC_BOX_ARCHIVES=(
  "2302681616868|Planet8bSR_BC_Labelled.zip|5092052520"
  "2302601053819|ca_data.zip|15966180991"
)

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
  HAKAI_DOWNLOAD_DIR              Download cache directory. Default: $HAKAI_DATA_ROOT/.downloads
  HAKAI_PYTHON_VERSION            Python version for uv. Default: 3.12
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
  run uv python install "$PYTHON_VERSION"
  run uv sync --python "$PYTHON_VERSION" "${uv_args[@]}"
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

archive_mime_type() {
  local archive="$1"
  if have_cmd file; then
    file -b --mime-type "$archive"
  else
    printf 'application/octet-stream'
  fi
}

file_size_bytes() {
  local file_path="$1"
  if stat -c '%s' "$file_path" >/dev/null 2>&1; then
    stat -c '%s' "$file_path"
  else
    stat -f '%z' "$file_path"
  fi
}

uses_static_box_archives() {
  [[ "$DATA_URL" == *"$DEFAULT_BOX_SHARED_NAME"* ]]
}

box_download_url_for() {
  local file_id="$1"
  printf 'https://caltech.app.box.com/index.php?rm=box_download_shared_file&shared_name=%s&file_id=f_%s' \
    "$DEFAULT_BOX_SHARED_NAME" \
    "$file_id"
}

direct_download_url_for() {
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

validate_downloaded_archive() {
  local archive_path="$1"
  local expected_size="${2:-}"

  if [[ "$DRY_RUN" == "1" ]]; then
    return
  fi

  [[ -s "$archive_path" ]] || die "Downloaded archive is empty or missing: $archive_path"

  local mime
  mime="$(archive_mime_type "$archive_path")"
  case "$mime" in
    text/html|text/plain)
      die "Downloaded $mime instead of a data archive for $archive_path."
      ;;
  esac

  if [[ -n "$expected_size" ]]; then
    local actual_size
    actual_size="$(file_size_bytes "$archive_path")"
    if [[ "$actual_size" != "$expected_size" ]]; then
      die "Unexpected size for $archive_path: got $actual_size bytes, expected $expected_size bytes. Rerun with --force-download to try again."
    fi
  fi
}

download_file() {
  local url="$1"
  local output_path="$2"
  local expected_size="${3:-}"
  local label="${4:-$output_path}"
  local part_path="$output_path.part"

  run mkdir -p "$DOWNLOAD_DIR"

  if [[ -s "$output_path" && "$FORCE_DOWNLOAD" != "1" ]]; then
    validate_downloaded_archive "$output_path" "$expected_size"
    log "Using existing data archive: $output_path"
    return
  fi

  if [[ "$FORCE_DOWNLOAD" == "1" ]]; then
    run rm -f "$output_path" "$part_path"
  fi

  log "Downloading $label"
  if ! run curl -fL --retry 5 --retry-delay 5 --continue-at - --output "$part_path" "$url"; then
    die "Could not download $label. Check that the Box share is still public and allows downloads. If an interrupted resume failed, rerun with --force-download."
  fi
  run mv "$part_path" "$output_path"
  validate_downloaded_archive "$output_path" "$expected_size"
}

download_static_box_archives() {
  local spec
  for spec in "${STATIC_BOX_ARCHIVES[@]}"; do
    local file_id
    local filename
    local expected_size
    IFS='|' read -r file_id filename expected_size <<< "$spec"

    download_file \
      "$(box_download_url_for "$file_id")" \
      "$DOWNLOAD_DIR/$filename" \
      "$expected_size" \
      "$filename"
  done
}

download_direct_archive() {
  local archive_path="$DOWNLOAD_DIR/$ARCHIVE_NAME"
  local resolved_url
  resolved_url="$(direct_download_url_for "$DATA_URL")"

  if [[ -s "$archive_path" && "$FORCE_DOWNLOAD" != "1" ]]; then
    validate_downloaded_archive "$archive_path"
    log "Using existing data archive: $archive_path"
  else
    printf 'URL: %s\n' "$DATA_URL"
    download_file "$resolved_url" "$archive_path" "" "$DATA_URL"
  fi
}

download_data_archives() {
  [[ "$SKIP_DATA" == "1" ]] && return

  if uses_static_box_archives; then
    download_static_box_archives
  else
    download_direct_archive
  fi
}

archive_paths_to_extract() {
  if uses_static_box_archives; then
    local spec
    for spec in "${STATIC_BOX_ARCHIVES[@]}"; do
      local file_id
      local filename
      local expected_size
      IFS='|' read -r file_id filename expected_size <<< "$spec"
      printf '%s\n' "$DOWNLOAD_DIR/$filename"
    done
  else
    printf '%s\n' "$DOWNLOAD_DIR/$ARCHIVE_NAME"
  fi
}

extract_one_archive() {
  local archive_path="$1"

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
}

extract_data_archives() {
  [[ "$SKIP_DATA" == "1" ]] && return

  local marker="$DATA_ROOT/.bootstrap-extracted"

  if [[ -f "$marker" && "$FORCE_EXTRACT" != "1" && "$FORCE_DOWNLOAD" != "1" ]]; then
    log "Data already extracted: $DATA_ROOT"
    return
  fi

  log "Extracting data archives into $DATA_ROOT"
  run mkdir -p "$DATA_ROOT"

  if [[ "$DRY_RUN" == "1" ]]; then
    printf '+ extract downloaded archives based on file type\n'
    return
  fi

  local archive_path
  while IFS= read -r archive_path; do
    [[ -f "$archive_path" ]] || die "Data archive is missing: $archive_path"
    validate_downloaded_archive "$archive_path"
    extract_one_archive "$archive_path"
  done < <(archive_paths_to_extract)

  date -u +%Y-%m-%dT%H:%M:%SZ > "$marker"
}

ensure_compat_data_root() {
  [[ "$CREATE_COMPAT_SYMLINK" == "1" ]] || return 0
  [[ -n "$COMPAT_DATA_ROOT" ]] || return 0

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

Default Box archives:
  Planet8bSR_BC_Labelled.zip
  ca_data.zip

To override with one direct archive URL:
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
  download_data_archives
  extract_data_archives
  ensure_compat_data_root
  validate_config_data_paths
  print_next_steps
}

main "$@"
