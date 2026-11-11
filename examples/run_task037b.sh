#!/usr/bin/env bash
# Launch the spectral comparison and reports in a fresh output directory.
set -euo pipefail

if (( $# != 1 )); then
    echo "Usage: bash examples/run_task037b.sh OUTPUT" >&2
    exit 2
fi
output=$1
[[ $output = /* ]] || output=$PWD/$output
cd "$(dirname "${BASH_SOURCE[0]}")/.."

uv run --frozen python examples/task037b.py prepare "$output"
uv run --frozen python examples/task037b.py planet4 "$output"
uv run --frozen python examples/task037b.py planet3 "$output"
uv run --frozen python examples/task037b.py report "$output"
