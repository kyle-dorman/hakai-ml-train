#!/usr/bin/env bash
# Wait for the current run, report it, then train/report three loss comparisons.
# Usage: bash run_loss_comparisons.sh [CURRENT_RUN_DIRECTORY] [NEW_REPORT_ROOT]
# Run inside tmux. All output stays interactive; Ctrl-C stops the sequence.
set -euo pipefail

if [[ ${1:-} == --help ]]; then
  cat <<'HELP'
Usage: bash run_loss_comparisons.sh [CURRENT_RUN_DIRECTORY] [NEW_REPORT_ROOT]

Wait for the current run.json status to become complete, then:
  1. Generate its validation report using CUDA.
  2. Train BCE + Dice (70 epochs), then generate its report.
  3. Train boundary-weighted BCE + Dice (70 epochs), then generate its report.
  4. Train focal + Dice (70 epochs), then generate its report.

Defaults target the current planet8-cabc-70ep-fast run and a fresh timestamped
folder under /home/sky/data/analyses. Training follows each recipe's paths file.
Stops on failure; no automatic resume or skipping of partial work. Nothing is
queued until you run this script. Use tmux to preserve the terminal session.
HELP
  exit 0
fi
if (( $# > 2 )); then
  echo "Expected at most CURRENT_RUN_DIRECTORY and NEW_REPORT_ROOT; see --help." >&2
  exit 2
fi

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
current_run=${1:-/home/sky/data/runs/planet8-cabc-70ep-fast-20261104T203544160104Z}
report_root=${2:-/home/sky/data/analyses/loss-comparisons-$(date -u +%Y%m%dT%H%M%SZ)}
# Resolve supplied paths before changing directories, including paths with spaces.
current_run=$(realpath -e -- "$current_run")
report_root=$(realpath -m -- "$report_root")
cd -- "$repo_dir"
if [[ -e "$report_root" ]]; then
  echo "Report root already exists: $report_root. Choose a fresh directory." >&2
  exit 1
fi

# Input: completed/running run directory. Output: waits or fails; never trains.
echo "Waiting for completion: $current_run"
while true; do
  status=$(uv run --frozen python - "$current_run/run.json" <<'PY'
import json
import sys
from pathlib import Path

record = json.loads(Path(sys.argv[1]).read_text())
print(record["status"])
PY
  )
  case "$status" in
    complete) break ;;
    running) sleep 30 ;;
    *) echo "Current run has status '$status'; stopping before reports/training." >&2; exit 1 ;;
  esac
done

mkdir -p -- "$(dirname -- "$report_root")"
mkdir -- "$report_root"
run_path_file=$(mktemp)
trap 'rm -f -- "$run_path_file"' EXIT
trap 'echo "Sequence interrupted; no later stages will run." >&2; exit 130' INT
trap 'echo "Sequence terminated; no later stages will run." >&2; exit 143' TERM
trap 'echo "Sequence failed; no later stages will run. See the error above." >&2' ERR

echo "Validation reports: $report_root"
uv run --frozen kelpseg validation-report \
  --run "$current_run" --output "$report_root/$(basename -- "$current_run")" --device cuda

for candidate in bce_dice boundary_bce_dice focal_dice; do
  recipe="configs/train/losses/$candidate.toml"
  echo "Starting training: $recipe"
  # The installed Python entry point returns the exact run directory on success.
  # Only that small path goes to a temporary file; progress stays on the terminal.
  uv run --frozen python - "$recipe" "$run_path_file" <<'PY'
import sys
from pathlib import Path

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging
from kelpseg.paths import check_paths, load_paths
from kelpseg.training.run import run_training
from kelpseg.training.settings import load_settings

settings = load_settings(sys.argv[1])
paths = check_paths(load_paths(settings.paths_file))
handler, previous = start_preparation_logging()
try:
    result = run_training(settings, paths)
    Path(sys.argv[2]).write_text(result["output"])
finally:
    stop_preparation_logging(handler, previous)
PY
  completed_run=$(cat -- "$run_path_file")
  echo "Reporting completed run: $completed_run"
  uv run --frozen kelpseg validation-report \
    --run "$completed_run" --output "$report_root/$(basename -- "$completed_run")" --device cuda
done

echo "All three comparisons and all four validation reports completed: $report_root"
