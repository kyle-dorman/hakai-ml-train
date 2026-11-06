"""Exercise the sequential launcher without training or accessing the GPU."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("failed_stage", ["", "train", "predict", "report"])
@pytest.mark.parametrize(
    "launcher,runs",
    [("run_lr_comparisons.sh", 4), ("run_model_size_comparisons.sh", 3)],
)
def test_launcher_sequence_and_failure(
    tmp_path: Path, failed_stage: str, launcher: str, runs: int
) -> None:
    """Run fake commands; verify exact run handoff and stop after any failed stage."""
    script = tmp_path / launcher
    shutil.copyfile(launcher, script)
    executable = tmp_path / "uv"
    executable.write_text(
        f"#!{sys.executable}\n"
        """import json, os, sys
from pathlib import Path
args = sys.argv[1:]
if args[2] == "python":
    stage = "train"
    run = Path(os.environ["FAKE_ROOT"]) / Path(args[4]).stem
else:
    stage = "predict" if args[3] == "predict-chips" else "report"
    run = Path(args[args.index("--run") + 1]) if stage == "predict" else Path(args[-1]).parent
with Path(os.environ["FAKE_LOG"]).open("a") as stream:
    stream.write(json.dumps([stage, str(run)]) + "\\n")
if stage == os.environ["FAIL_STAGE"]:
    sys.exit(1)
if stage == "train":
    run.mkdir(parents=True)
    Path(args[5]).write_text(str(run))
elif stage == "predict":
    assert Path(args[args.index("--output") + 1]) == run / "validation-predictions"
else:
    recipe = Path(args[-1]).read_text()
    assert 'predictions = "validation-predictions"' in recipe
    assert 'output = "validation-report"' in recipe
"""
    )
    executable.chmod(0o755)
    log = tmp_path / "calls.jsonl"
    result = subprocess.run(
        ["bash", str(script)],
        env=dict(
            os.environ,
            PATH=f"{tmp_path}:{os.environ['PATH']}",
            FAKE_ROOT=str(tmp_path / "runs"),
            FAKE_LOG=str(log),
            FAIL_STAGE=failed_stage,
        ),
        capture_output=True,
        text=True,
    )
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    if failed_stage:
        assert result.returncode != 0
        assert [stage for stage, _ in calls] == ["train", "predict", "report"][
            : ["train", "predict", "report"].index(failed_stage) + 1
        ]
    else:
        assert result.returncode == 0, result.stderr
        assert [stage for stage, _ in calls] == ["train", "predict", "report"] * runs
        for index in range(0, len(calls), 3):
            assert len({run for _, run in calls[index : index + 3]}) == 1
