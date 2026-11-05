"""Exercise Bash sequencing with fake commands; never train or access a GPU."""

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "run_loss_comparisons.sh"
STAGES = [
    "predict:current run",
    "report:current run",
    "train:bce_dice",
    "predict:bce_dice-test",
    "report:bce_dice-test",
    "train:boundary_bce_dice",
    "predict:boundary_bce_dice-test",
    "report:boundary_bce_dice-test",
    "train:focal_dice",
    "predict:focal_dice-test",
    "report:focal_dice-test",
]


@pytest.fixture
def commands(tmp_path: Path) -> tuple[dict[str, str], Path, Path, Path]:
    """Return fake-command environment, current run, report root and event log."""
    current = tmp_path / "current run"
    current.mkdir()
    (current / "run.json").write_text(json.dumps({"status": "complete"}))
    reports = tmp_path / "report output"
    events = tmp_path / "events.jsonl"
    commands = tmp_path / "bin"
    commands.mkdir()
    uv = commands / "uv"
    uv.write_text("""#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
assert args[:2] == ["run", "--frozen"]
if args[2] == "python":
    code = sys.stdin.read()
    compile(code, "script-heredoc", "exec")
    if "run_training" not in code:
        sys.argv = ["-", *args[4:]]
        exec(compile(code, "script-heredoc", "exec"))
        sys.exit(0)
    candidate = Path(args[4]).stem
    stage = "train:" + candidate
    run = Path(os.environ["COMPARISON_TEST_ROOT"]) / (candidate + "-test")
elif args[2:4] == ["kelpseg", "predict-chips"]:
    assert args[-2:] == ["--device", "cuda"]
    run = Path(args[args.index("--run") + 1])
    stage = "predict:" + run.name
else:
    import tomllib
    assert args[2:4] == ["kelpseg", "report"]
    recipe = tomllib.loads(Path(args[args.index("--recipe") + 1]).read_text())
    run = Path(Path(recipe["predictions"]).joinpath("run-path.txt").read_text())
    stage = "report:" + run.name
with Path(os.environ["COMPARISON_TEST_EVENTS"]).open("a") as stream:
    stream.write(json.dumps({"stage": stage, "run": str(run)}) + "\\n")
if os.environ.get("COMPARISON_TEST_FAIL") == stage:
    print("Deliberate test failure", file=sys.stderr)
    sys.exit(7)
if stage.startswith("train:"):
    run.mkdir()
    (run / "run.json").write_text(json.dumps({"status": "complete"}))
    Path(args[5]).write_text(str(run))
elif stage.startswith("predict:"):
    assert json.loads((run / "run.json").read_text())["status"] == "complete"
    output = Path(args[args.index("--output") + 1])
    output.mkdir()
    (output / "run-path.txt").write_text(str(run))
else:
    Path(recipe["output"]).mkdir()
""")
    uv.chmod(0o755)
    sleep = commands / "sleep"
    sleep.write_text("""#!/usr/bin/env python3
import json
import os
from pathlib import Path

with Path(os.environ["COMPARISON_TEST_EVENTS"]).open("a") as stream:
    stream.write(json.dumps({"stage": "wait"}) + "\\n")
Path(os.environ["COMPARISON_TEST_CURRENT"]).joinpath("run.json").write_text(json.dumps({"status": "complete"}))
""")
    sleep.chmod(0o755)
    env = dict(os.environ, PATH=f"{commands}:{os.environ['PATH']}")
    env.update(
        COMPARISON_TEST_ROOT=str(tmp_path),
        COMPARISON_TEST_EVENTS=str(events),
        COMPARISON_TEST_CURRENT=str(current),
    )
    return env, current, reports, events


def invoke(
    commands: tuple[dict[str, str], Path, Path, Path],
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run the real Bash script against fake commands and return its recorded order."""
    env, current, reports, events = commands
    result = subprocess.run(
        ["bash", str(SCRIPT), str(current), str(reports)],
        env=env,
        cwd=current.parent,
        capture_output=True,
        text=True,
        timeout=15,
    )
    stages = (
        [json.loads(line)["stage"] for line in events.read_text().splitlines()]
        if events.exists()
        else []
    )
    return result, stages


def test_reports_current_then_each_selected_training(commands):
    result, stages = invoke(commands)
    assert result.returncode == 0, result.stderr
    assert stages == STAGES
    assert len(list(commands[2].iterdir())) == 4


@pytest.mark.parametrize("failed_stage", STAGES)
def test_any_failure_stops_later_stages(commands, failed_stage):
    commands[0]["COMPARISON_TEST_FAIL"] = failed_stage
    result, stages = invoke(commands)
    assert result.returncode != 0
    assert stages == STAGES[: STAGES.index(failed_stage) + 1]
    assert "no later stages" in result.stderr


def test_waits_until_current_run_completes(commands):
    (commands[1] / "run.json").write_text(json.dumps({"status": "running"}))
    result, stages = invoke(commands)
    assert result.returncode == 0, result.stderr
    assert stages == ["wait", *STAGES]


def test_failed_current_run_stops_before_creating_outputs(commands):
    (commands[1] / "run.json").write_text(json.dumps({"status": "failed"}))
    result, stages = invoke(commands)
    assert result.returncode != 0
    assert stages == []
    assert not commands[2].exists()


def test_existing_report_root_is_refused(commands):
    commands[2].mkdir()
    result, stages = invoke(commands)
    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert stages == []
