from pathlib import Path

import pytest

from kelpseg.paths import PathSettings, PathSettingsError, check_paths, load_paths


def _write_settings(tmp_path: Path, contents: str) -> Path:
    settings = tmp_path / "paths.local.toml"
    settings.write_text(contents, encoding="utf-8")
    return settings


def test_relative_roots_resolve_from_settings_and_allow_nested_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    settings = _write_settings(
        tmp_path,
        '[paths]\ndata_root = "data with spaces"\nruns_root = "data with spaces/runs"\n',
    )
    data = tmp_path / "data with spaces"
    runs = data / "runs"
    runs.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    before = sorted(tmp_path.rglob("*"))
    resolved = load_paths(settings)
    assert resolved == PathSettings(settings, data, runs)
    assert check_paths(resolved) == resolved
    assert sorted(tmp_path.rglob("*")) == before
    assert capsys.readouterr() == ("", "")


def test_absolute_and_home_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    data = tmp_path / "data"
    runs = tmp_path / "runs"
    data.mkdir()
    runs.mkdir()
    config = _write_settings(
        tmp_path, f'[paths]\ndata_root = "~/data"\nruns_root = "{runs.as_posix()}"\n'
    )
    assert check_paths(load_paths(config)) == PathSettings(config, data, runs)


def test_environment_variables_remain_literal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KELPSEG_TEST_ROOT", "unexpected-expansion")
    root = tmp_path / "$KELPSEG_TEST_ROOT"
    root.mkdir()
    config = _write_settings(
        tmp_path,
        '[paths]\ndata_root = "$KELPSEG_TEST_ROOT"\nruns_root = "$KELPSEG_TEST_ROOT"\n',
    )
    assert check_paths(load_paths(config)).data_root == root


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("[paths", "invalid TOML"),
        ("", "[paths] table"),
        ('paths = "wrong"', "[paths] table"),
        ('unexpected = "value"\n[paths]\n', "unknown settings: unexpected"),
        ("[unexpected]\nvalue = 1\n[paths]\n", "unknown settings: unexpected"),
        ('[paths]\nextra = "value"\n', "unknown [paths] keys: extra"),
        ('[paths]\nruns_root = "runs"\n', "paths.data_root"),
        ('[paths]\ndata_root = "data"\n', "paths.runs_root"),
        ('[paths]\ndata_root = ""\nruns_root = "runs"\n', "paths.data_root"),
        ('[paths]\ndata_root = "   "\nruns_root = "runs"\n', "paths.data_root"),
        ('[paths]\ndata_root = 3\nruns_root = "runs"\n', "paths.data_root"),
        ('[paths]\ndata_root = false\nruns_root = "runs"\n', "paths.data_root"),
        ('[paths]\ndata_root = []\nruns_root = "runs"\n', "paths.data_root"),
        ('[paths]\ndata_root = "data"\nruns_root = {}\n', "paths.runs_root"),
        ('[paths]\ndata_root = "\\u0000"\nruns_root = "runs"\n', "paths.data_root"),
    ],
)
def test_invalid_settings_raise_ordinary_actionable_errors(
    tmp_path: Path, contents: str, message: str, capsys: pytest.CaptureFixture
) -> None:
    config = _write_settings(tmp_path, contents)
    before = config.read_bytes()
    with pytest.raises(PathSettingsError) as raised:
        load_paths(config)
    assert message in str(raised.value)
    assert str(config) in str(raised.value)
    assert config.read_bytes() == before
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("kind", ["missing", "directory", "invalid-utf8"])
def test_unusable_settings_file(tmp_path: Path, kind: str) -> None:
    config = tmp_path / "paths.local.toml"
    if kind == "directory":
        config.mkdir()
    elif kind == "invalid-utf8":
        config.write_bytes(b"\xff\xfe")
    with pytest.raises(PathSettingsError) as raised:
        load_paths(config)
    assert str(config) in str(raised.value)
    assert (
        "UTF-8" in str(raised.value)
        if kind == "invalid-utf8"
        else "read" in str(raised.value)
    )


def test_unreadable_settings_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _write_settings(tmp_path, "[paths]\n")

    def unreadable(*args, **kwargs):
        raise PermissionError("fixture denies reading")

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(PathSettingsError, match="readable TOML file"):
        load_paths(config)


@pytest.mark.parametrize("key", ["data_root", "runs_root"])
@pytest.mark.parametrize("kind", ["missing", "file"])
def test_bad_roots_fail_without_creating_or_changing_them(
    tmp_path: Path, key: str, kind: str
) -> None:
    data = tmp_path / "data"
    runs = tmp_path / "runs"
    data.mkdir()
    runs.mkdir()
    target = data if key == "data_root" else runs
    target.rmdir()
    if kind == "file":
        target.write_text("unchanged")
    config = _write_settings(
        tmp_path, '[paths]\ndata_root = "data"\nruns_root = "runs"\n'
    )
    settings = load_paths(config)
    before = sorted(tmp_path.rglob("*"))
    with pytest.raises(PathSettingsError, match=f"paths.{key}.*existing directory"):
        check_paths(settings)
    assert sorted(tmp_path.rglob("*")) == before
    if kind == "file":
        assert target.read_text() == "unchanged"
