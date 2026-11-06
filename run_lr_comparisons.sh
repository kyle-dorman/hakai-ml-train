#!/usr/bin/env bash
# Run four fresh LR experiments and report each selected EMA model; stop on failure.
# New outputs stay outside the directories scanned by the current Box backup.
set -euo pipefail
if (( $# != 0 )); then
  echo 'Usage: bash run_lr_comparisons.sh' >&2
  exit 2
fi
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$repo_dir"
run_path_file=$(mktemp)
trap 'rm -f -- "$run_path_file"' EXIT
for recipe in \
  configs/train/lr_comparison/a_reference.toml \
  configs/train/lr_comparison/b_half_lr.toml \
  configs/train/lr_comparison/c_lower_lr.toml \
  configs/train/lr_comparison/d_half_lr_wd005.toml; do
  echo "Training $recipe"
  # Write the exact completed run path for the following, separate processes.
  uv run --frozen python - "$recipe" "$run_path_file" <<'PY'
import sys
from dataclasses import replace
from pathlib import Path

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging
from kelpseg.paths import check_paths, load_paths
from kelpseg.training.run import run_training
from kelpseg.training.settings import load_settings

settings = load_settings(sys.argv[1])
paths = check_paths(load_paths(settings.paths_file))
paths = replace(paths, runs_root=paths.data_root / "lr-comparison-runs")
paths.runs_root.mkdir(exist_ok=True)
handler, previous = start_preparation_logging()
try:
    result = run_training(settings, paths)
    Path(sys.argv[2]).write_text(result["output"])
finally:
    stop_preparation_logging(handler, previous)
PY
  completed_run=$(cat "$run_path_file")
  uv run --frozen kelpseg predict-chips \
    --run "$completed_run" --output "$completed_run/validation-predictions" \
    --device cuda
  # Relative paths keep the report recipe usable when the complete run is copied.
  cat > "$completed_run/validation-report.toml" <<'TOML'
predictions = "validation-predictions"
output = "validation-report"
max_examples = 12
TOML
  uv run --frozen kelpseg report --recipe "$completed_run/validation-report.toml"
  echo "Completed: $completed_run/validation-report/report.html"
done
echo 'All four LR comparisons and validation reports are complete.'
