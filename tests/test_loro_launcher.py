"""The tmux launcher runs folds in order and stops at the first failed stage."""

import os
import subprocess
from pathlib import Path

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "examples/run_task037c.sh"


@pytest.mark.parametrize(
    "failed_stage", ["loro_001", "loro_005", "loro_010", "summary", ""]
)
def test_launcher_stops_on_failure(tmp_path: Path, failed_stage: str) -> None:
    """Substitute only uv, retaining the real Bash control flow and exit code."""
    fake_uv = tmp_path / "uv"
    fake_uv.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$4" >> "$LAUNCH_LOG"\n'
        'if [[ "$4" == "$FAIL_STAGE" ]]; then exit 19; fi\n'
    )
    fake_uv.chmod(0o755)
    log = tmp_path / "calls.txt"
    result = subprocess.run(
        ["bash", str(LAUNCHER), str(tmp_path / "suite")],
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "LAUNCH_LOG": str(log),
            "FAIL_STAGE": failed_stage,
        },
        check=False,
        capture_output=True,
        text=True,
    )
    stages = [f"loro_{number:03d}" for number in range(1, 11)] + ["summary"]
    expected = stages[: stages.index(failed_stage) + 1] if failed_stage else stages
    assert log.read_text().splitlines() == expected
    assert result.returncode == (19 if failed_stage else 0)
