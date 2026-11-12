#!/usr/bin/env bash
# Launch a prepared suite once from an existing tmux session. Stop on any failure.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ $# != 1 ]]; then
    echo "Usage: bash examples/run_task037c.sh /absolute/prepared-suite-directory" >&2
    exit 2
fi
suite=$1
for region in 001 002 003 004 005 006 007 008 009 010; do
    uv run python examples/task037c.py "loro_${region}" "$suite"
done
uv run python examples/task037c.py summary "$suite"
