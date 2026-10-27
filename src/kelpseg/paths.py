"""Load explicit machine paths without creating or modifying files."""

import tomllib
from dataclasses import dataclass
from pathlib import Path


class PathSettingsError(ValueError):
    """A machine-path setting cannot be read, resolved, or used."""


@dataclass(frozen=True)
class PathSettings:
    """Resolved locations from one explicitly selected settings file."""

    settings_file: Path
    data_root: Path
    runs_root: Path


def _resolve_path(value: str | Path, *, base: Path, context: str) -> Path:
    try:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = base / path
        return path.resolve()
    except (OSError, RuntimeError, ValueError) as error:
        raise PathSettingsError(
            f"{context}: cannot resolve this path ({error}). "
            "Use an absolute path, ~, or a path relative to the settings file."
        ) from error


def load_paths(settings_file: str | Path) -> PathSettings:
    """Read strict TOML settings; relative roots use the settings directory.

    Root existence is checked separately by :func:`check_paths`. Environment
    variables in strings are literal; only a leading home-directory ~ expands.
    """
    config = _resolve_path(
        settings_file, base=Path.cwd(), context=f"Settings file {settings_file}"
    )
    try:
        contents = config.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise PathSettingsError(
            f"{config}: settings must be UTF-8 text. Save the TOML file as UTF-8."
        ) from error
    except OSError as error:
        raise PathSettingsError(
            f"{config}: cannot read settings ({error.strerror or error}). "
            "Select a readable TOML file with --paths; copy configs/paths.example.toml "
            "to paths.local.toml if you need a starting point."
        ) from error
    try:
        document = tomllib.loads(contents)
    except tomllib.TOMLDecodeError as error:
        raise PathSettingsError(
            f"{config}: invalid TOML ({error}). Correct the TOML syntax."
        ) from error

    unknown = document.keys() - {"paths"}
    if unknown:
        raise PathSettingsError(
            f"{config}: unknown settings: {', '.join(sorted(unknown))}. "
            "Use only [paths] with data_root and runs_root."
        )
    values = document.get("paths")
    if not isinstance(values, dict):
        raise PathSettingsError(
            f"{config}: missing or invalid [paths] table. "
            "Add [paths] with data_root and runs_root strings."
        )
    unknown = values.keys() - {"data_root", "runs_root"}
    if unknown:
        raise PathSettingsError(
            f"{config}: unknown [paths] keys: {', '.join(sorted(unknown))}. "
            "Use only data_root and runs_root."
        )
    resolved = {}
    for key in ("data_root", "runs_root"):
        value = values.get(key)
        if not isinstance(value, str) or not value.strip():
            raise PathSettingsError(
                f"{config}: paths.{key} must be a nonempty string. "
                f'Set {key} = "your/directory" under [paths].'
            )
        resolved[key] = _resolve_path(
            value, base=config.parent, context=f"{config}: paths.{key}"
        )
    return PathSettings(settings_file=config, **resolved)


def check_paths(settings: PathSettings) -> PathSettings:
    """Require existing directories, allowing nested roots; never write or scan."""
    for key in ("data_root", "runs_root"):
        path = getattr(settings, key)
        try:
            valid = path.is_dir()
        except OSError as error:
            raise PathSettingsError(
                f"{settings.settings_file}: paths.{key} cannot be checked: {path} "
                f"({error}). Select an accessible directory."
            ) from error
        if not valid:
            raise PathSettingsError(
                f"{settings.settings_file}: paths.{key} is not an existing directory: "
                f"{path}. Create the intended directory or correct paths.{key}."
            )
    return settings
