#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

ARCHIVE_NAME="planet8b_all_regions_1024_512_v2.zip"
CHECKSUM_NAME="${ARCHIVE_NAME}.sha256"
ARCHIVE_FILE_ID="1wbkecoaC8MTJu3X_wV7jnyv62UWJv2QH"
CHECKSUM_FILE_ID="1nPPYapJlNwsnJ19SuA4BEuT0p4rCXVub"
EXPECTED_ARCHIVE_BYTES=44859496084
EXPECTED_CHECKSUM_BYTES=103
EXPECTED_SHA256="1244ecfe2cc4cee624bb5661087f0126ea239367bda60efd823b4fcb9b7399db"

STAGING_DIR="${HAKAI_REMOTE_STAGING_DIR:-$HOME/dataset-staging}"
DATA_PARENT="${HAKAI_REMOTE_DATA_PARENT:-$HOME/data}"
COMPAT_DATA_ROOT="${HAKAI_COMPAT_DATA_ROOT:-}"
DOWNLOAD_MISSING=0

log() {
  printf '\n==> %s\n' "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: scripts/prepare_remote_planet8b_dataset.sh [options]

Prepare the Task 009A v2 canonical archive on a remote Linux host. Existing
files are never overwritten silently. Downloads use a resumable .partial file;
extraction is promoted to the final dataset root only after full verification.

Options:
  --download-missing       Download the ZIP and checksum when absent.
  --staging-dir PATH       Download directory. Default: $HOME/dataset-staging
  --data-parent PATH       Parent of the extracted dataset root. Default: $HOME/data
  --compat-data-root PATH  Optional symlink to DATA_PARENT, for example /home/taylor/data
  --help                   Show this help.

Environment equivalents:
  HAKAI_REMOTE_STAGING_DIR
  HAKAI_REMOTE_DATA_PARENT
  HAKAI_COMPAT_DATA_ROOT
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --download-missing)
      DOWNLOAD_MISSING=1
      ;;
    --staging-dir)
      [[ $# -ge 2 ]] || die "--staging-dir requires a path"
      STAGING_DIR="$2"
      shift
      ;;
    --data-parent)
      [[ $# -ge 2 ]] || die "--data-parent requires a path"
      DATA_PARENT="$2"
      shift
      ;;
    --compat-data-root)
      [[ $# -ge 2 ]] || die "--compat-data-root requires a path"
      COMPAT_DATA_ROOT="$2"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "Unknown option: $1"
      ;;
  esac
  shift
done

ARCHIVE="$STAGING_DIR/$ARCHIVE_NAME"
CHECKSUM_FILE="$STAGING_DIR/$CHECKSUM_NAME"
DATASET_ROOT="$DATA_PARENT/${ARCHIVE_NAME%.zip}"
EXTRACTION_PARENT="$DATA_PARENT/.${ARCHIVE_NAME%.zip}.extracting"
VERIFICATION_TMP="$STAGING_DIR/${ARCHIVE_NAME%.zip}.verification.json.partial"
VERIFICATION_RECEIPT="$DATASET_ROOT/metadata/remote_archive_verification.log"

file_bytes() {
  wc -c < "$1" | tr -d '[:space:]'
}

require_file_size() {
  local path="$1"
  local expected="$2"
  local actual
  actual="$(file_bytes "$path")"
  [[ "$actual" == "$expected" ]] || \
    die "Unexpected size for $path: expected $expected bytes, found $actual"
}

download_file() {
  local file_id="$1"
  local destination="$2"
  local expected_bytes="$3"

  if [[ -f "$destination" ]]; then
    require_file_size "$destination" "$expected_bytes"
    log "Using existing file: $destination"
    return
  fi
  [[ ! -e "$destination" ]] || die "Refusing non-file destination: $destination"
  [[ "$DOWNLOAD_MISSING" == "1" ]] || \
    die "Missing $destination; rerun with --download-missing"

  local partial="${destination}.partial"
  [[ ! -e "$partial" || -f "$partial" ]] || \
    die "Refusing non-file partial download: $partial"

  log "Downloading $(basename "$destination")"
  curl --fail --location --retry 5 --retry-delay 5 \
    --continue-at - --output "$partial" \
    "https://drive.usercontent.google.com/download?id=${file_id}&export=download&confirm=t"
  require_file_size "$partial" "$expected_bytes"
  mv "$partial" "$destination"
}

create_compat_symlink() {
  [[ -n "$COMPAT_DATA_ROOT" ]] || return 0
  [[ "$COMPAT_DATA_ROOT" != "$DATA_PARENT" ]] || return 0
  if [[ -L "$COMPAT_DATA_ROOT" && "$(readlink "$COMPAT_DATA_ROOT")" == "$DATA_PARENT" ]]; then
    return
  fi
  [[ ! -e "$COMPAT_DATA_ROOT" ]] || \
    die "Compatibility path already exists: $COMPAT_DATA_ROOT"

  local parent
  parent="$(dirname "$COMPAT_DATA_ROOT")"
  if [[ -w "$parent" ]]; then
    mkdir -p "$parent"
    ln -s "$DATA_PARENT" "$COMPAT_DATA_ROOT"
  elif command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
    sudo mkdir -p "$parent"
    sudo ln -s "$DATA_PARENT" "$COMPAT_DATA_ROOT"
  else
    die "Cannot create compatibility symlink: $COMPAT_DATA_ROOT -> $DATA_PARENT"
  fi
}

main() {
  command -v curl >/dev/null 2>&1 || die "curl is required"
  command -v uv >/dev/null 2>&1 || die "uv is required; run scripts/bootstrap_skypilot.sh first"

  if [[ -f "$VERIFICATION_RECEIPT" ]]; then
    log "Dataset already extracted and verified: $DATASET_ROOT"
    create_compat_symlink
    return
  fi
  [[ ! -e "$DATASET_ROOT" ]] || \
    die "Dataset root exists without a verification receipt: $DATASET_ROOT"
  [[ ! -e "$EXTRACTION_PARENT" ]] || \
    die "Partial extraction exists and requires inspection: $EXTRACTION_PARENT"

  mkdir -p "$STAGING_DIR" "$DATA_PARENT"
  download_file "$CHECKSUM_FILE_ID" "$CHECKSUM_FILE" "$EXPECTED_CHECKSUM_BYTES"
  download_file "$ARCHIVE_FILE_ID" "$ARCHIVE" "$EXPECTED_ARCHIVE_BYTES"

  local sidecar_sha sidecar_name
  read -r sidecar_sha sidecar_name < "$CHECKSUM_FILE"
  [[ "$sidecar_sha" == "$EXPECTED_SHA256" ]] || \
    die "Checksum sidecar does not contain the approved v2 SHA-256"
  [[ "$sidecar_name" == "$ARCHIVE_NAME" ]] || \
    die "Checksum sidecar names an unexpected archive: $sidecar_name"

  log "Verifying and extracting the v2 archive"
  cd "$REPO_ROOT"
  uv run python scripts/package_planet8b_dataset.py verify \
    --archive "$ARCHIVE" \
    --checksum-file "$CHECKSUM_FILE" \
    --extraction-parent "$EXTRACTION_PARENT" \
    --sample-count 12 > "$VERIFICATION_TMP"

  [[ -d "$EXTRACTION_PARENT/${ARCHIVE_NAME%.zip}" ]] || \
    die "Verifier did not create the expected dataset root"
  sed "s|$EXTRACTION_PARENT/${ARCHIVE_NAME%.zip}|$DATASET_ROOT|g" \
    "$VERIFICATION_TMP" > "${VERIFICATION_TMP}.promoted"
  mv "$EXTRACTION_PARENT/${ARCHIVE_NAME%.zip}" "$DATASET_ROOT"
  rmdir "$EXTRACTION_PARENT"
  mv "${VERIFICATION_TMP}.promoted" "$VERIFICATION_RECEIPT"
  rm "$VERIFICATION_TMP"
  create_compat_symlink

  log "Remote canonical dataset is ready"
  printf 'Dataset root: %s\n' "$DATASET_ROOT"
  printf 'Verification receipt: %s\n' "$VERIFICATION_RECEIPT"
}

main "$@"
