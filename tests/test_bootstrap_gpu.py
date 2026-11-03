"""Exercise setup ordering and failure boundaries without changing the host."""

import os
import shlex
import subprocess
from pathlib import Path

import pytest

BOOTSTRAP = Path(__file__).resolve().parents[1] / "bootstrap_gpu.sh"


def _run(tmp_path, *, system="Linux", distro="ubuntu", user_id="1000", failure=""):
    release = tmp_path / "os-release"
    release.write_text(f"ID={distro}\n")
    script = tmp_path / "bootstrap_gpu.sh"
    # The only filesystem substitution is the OS identity fixture, for Mac CI.
    script.write_text(BOOTSTRAP.read_text().replace("/etc/os-release", str(release)))
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "uv.lock").write_text("")
    log = tmp_path / "commands.log"
    # Exported shell functions take precedence over executables, including the
    # user's existing uv/Codex. No package manager or installer can run here.
    mocks = """
record() { printf '%s\\n' "$*" >> "$PROBE_LOG"; }
uname() { printf '%s\\n' "$PROBE_SYSTEM"; }
id() { printf '%s\\n' "$PROBE_UID"; }
apt-get() { record "apt-get $*"; }
sudo() {
  record "sudo $*"
  if [[ "$PROBE_FAILURE" == apt && "$1" == apt-get ]]; then return 7; fi
}
uv() {
  record "uv $*"
  if [[ "$PROBE_FAILURE" == sync && "$1" == sync ]]; then return 8; fi
}
codex() { record "codex $*"; }
rclone() { record "rclone $*"; }
tmux() { record "tmux $*"; }
curl() { record "unexpected curl $*"; return 9; }
export -f record uname id apt-get sudo uv codex rclone tmux curl
"""
    env = dict(
        os.environ,
        PROBE_LOG=str(log),
        PROBE_SYSTEM=system,
        PROBE_UID=user_id,
        PROBE_FAILURE=failure,
    )
    result = subprocess.run(
        ["bash", "-c", mocks + "\nbash " + shlex.quote(str(script))],
        cwd=tmp_path.parent,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, log.read_text().splitlines() if log.exists() else []


@pytest.mark.parametrize("distro", ["ubuntu", "debian"])
def test_setup_uses_sudo_only_for_apt_and_frozen_user_environment(tmp_path, distro):
    result, commands = _run(tmp_path, distro=distro)
    assert result.returncode == 0, result.stderr
    assert commands == [
        "sudo apt-get update",
        "sudo env DEBIAN_FRONTEND=noninteractive apt-get upgrade -y",
        "sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y "
        "ca-certificates curl git build-essential pkg-config unzip rclone tmux",
        "uv --version",
        "uv python install 3.12",
        "uv sync --python 3.12 --frozen",
        "codex --version",
        "rclone version",
        "tmux -V",
    ]


@pytest.mark.parametrize(
    "settings", [{"system": "Darwin"}, {"distro": "fedora"}, {"user_id": "0"}]
)
def test_unsupported_host_or_root_refused_before_mutation(tmp_path, settings):
    result, commands = _run(tmp_path, **settings)
    assert result.returncode == 1
    assert not commands


@pytest.mark.parametrize("failure", ["apt", "sync"])
def test_failed_step_stops_later_setup(tmp_path, failure):
    result, commands = _run(tmp_path, failure=failure)
    assert result.returncode != 0
    assert not any(command.startswith("codex") for command in commands)
    if failure == "apt":
        assert commands == ["sudo apt-get update"]
    else:
        assert commands[-1] == "uv sync --python 3.12 --frozen"
