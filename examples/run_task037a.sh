#!/usr/bin/env bash
# Run from any directory with a fresh comparison output path.
set -euo pipefail

if (( $# < 1 || $# > 2 )); then
    echo "Usage: bash examples/run_task037a.sh OUTPUT [SAVED_REFERENCE_TIFF_PREDICTIONS]" >&2
    exit 2
fi
output=$1
[[ $output = /* ]] || output=$PWD/$output
reference_predictions=()
if (( $# == 2 )); then
    candidate=$2
    [[ $candidate = /* ]] || candidate=$PWD/$candidate
    reference_predictions=(--reference-predictions "$candidate")
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
recipe=configs/train/baseline_comparisons/b0_without_bc.toml

uv run --frozen python examples/task037a_prepare.py "$recipe" "$output" "${reference_predictions[@]}"
uv run --frozen python examples/task037a_prepare.py "$recipe" "$output" --fit
if [[ -f "$output/with-bc-predict.toml" ]]; then
    uv run --frozen kelpseg predict --recipe "$output/with-bc-predict.toml"
fi
uv run --frozen kelpseg predict --recipe "$output/no-bc-predict.toml"
uv run --frozen python examples/task037a_compare.py check "$output"
uv run --frozen kelpseg report --recipe "$output/with-bc-report.toml"
uv run --frozen kelpseg report --recipe "$output/no-bc-report.toml"
uv run --frozen kelpseg temporal-report --recipe "$output/with-bc-temporal.toml"
uv run --frozen kelpseg temporal-report --recipe "$output/no-bc-temporal.toml"
uv run --frozen python examples/task037a_compare.py summarize "$output"
printf 'Paired validation tables and reports: %s\n' "$output"
