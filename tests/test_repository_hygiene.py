"""Read-only repository checks, runnable with pytest and included in CI."""

import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml


def repository_files(root: Path) -> list[Path]:
    """List existing tracked/nonignored untracked files without following symlinks."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    paths = {root / name.decode() for name in result.stdout.split(b"\0") if name}
    return sorted(
        path
        for path in paths
        if path.is_file() and not path.is_symlink() and path.suffix != ".lock"
    )


def file_errors(path: Path) -> list[str]:
    """Return format, size and text-hygiene errors for a file without changing it."""
    if path.stat().st_size > 500 * 1024:
        return ["exceeds 500 KiB; keep generated artifacts outside Git"]
    content = path.read_bytes()
    structured = path.suffix in {".json", ".yaml", ".yml", ".toml"}
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        if structured:
            return [f"invalid {path.suffix} text: expected UTF-8"]
        return []  # Binary assets have no text whitespace rules.
    if "\0" in text and not structured:
        return []
    errors = []
    try:
        if path.suffix == ".json":
            json.loads(text)
        elif path.suffix in {".yaml", ".yml"}:
            yaml.safe_load(text)
        elif path.suffix == ".toml":
            tomllib.loads(text)
    except (ValueError, yaml.YAMLError) as error:
        errors.append(f"invalid {path.suffix} syntax: {error}")
    endings = set(re.findall(r"\r\n|\r|\n", text))
    if len(endings) > 1:
        errors.append("mixed line endings")
    if text and (not endings or not text.endswith(tuple(endings))):
        errors.append("missing final newline")
    if text.endswith(("\n\n", "\r\n\r\n", "\r\r")):
        errors.append("extra blank lines at end of file")
    for number, line in enumerate(text.splitlines(), start=1):
        if line.endswith((" ", "\t")):
            errors.append(f"line {number}: trailing whitespace")
        if re.match(r"^(<{7} |={7}$|>{7} )", line):
            errors.append(f"line {number}: merge conflict marker")
    return errors


def test_repository_hygiene() -> None:
    """Check the current checkout, including new files before they are staged."""
    root = Path(__file__).resolve().parents[1]
    errors = [
        f"{path.relative_to(root)}: {error}"
        for path in repository_files(root)
        for error in file_errors(path)
    ]
    assert not errors, "\n" + "\n".join(errors)


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("bad.json", b"{\n", "invalid .json"),
        ("bad.yaml", b"x: [\n", "invalid .yaml"),
        ("bad.toml", b"x = [\n", "invalid .toml"),
        ("notes.md", b"<<<<<<< branch\n", "merge conflict"),
        ("notes.md", b"one\r\ntwo\n", "mixed line endings"),
        ("notes.md", b"one \n", "trailing whitespace"),
        ("notes.md", b"one", "missing final newline"),
        ("notes.md", b"one\n\n", "extra blank lines"),
        ("large.bin", b"\0" * (500 * 1024 + 1), "exceeds 500 KiB"),
    ],
)
def test_hygiene_reports_bad_files_without_rewriting(
    tmp_path: Path, name: str, content: bytes, message: str
) -> None:
    """Ensure the standalone checks identify common mistakes and remain read-only."""
    path = tmp_path / name
    path.write_bytes(content)
    assert any(message in error for error in file_errors(path))
    assert path.read_bytes() == content


def test_repository_selection_handles_work_in_progress(tmp_path: Path) -> None:
    """Include new unstaged files while excluding ignored, deleted and linked paths."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("ignored/\n")
    deleted = tmp_path / "deleted.txt"
    deleted.touch()
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    deleted.unlink()
    (tmp_path / "new.json").write_text("{}\n")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored/artifact.txt").write_text("ignored")
    (tmp_path / "uv.lock").write_text("generated")
    (tmp_path / "link").symlink_to(tmp_path / "new.json")
    assert {path.name for path in repository_files(tmp_path)} == {
        ".gitignore",
        "new.json",
    }


@pytest.mark.parametrize("suffix", [".json", ".yaml", ".toml"])
@pytest.mark.parametrize("content", [b"invalid\xff\n", b"invalid\0\n"])
def test_structured_files_cannot_bypass_validation_as_binary(
    tmp_path: Path, suffix: str, content: bytes
) -> None:
    """Reject corrupted config text while preserving binary-asset support."""
    path = tmp_path / f"settings{suffix}"
    path.write_bytes(content)
    assert any("invalid" in error for error in file_errors(path))
    assert path.read_bytes() == content


def test_small_binary_assets_are_allowed(tmp_path: Path) -> None:
    """Binary assets should not receive text parsing or whitespace errors."""
    path = tmp_path / "image.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n\0")
    assert file_errors(path) == []
