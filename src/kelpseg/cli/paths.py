"""Presentation for the read-only machine-path check."""

from pathlib import Path
from typing import Annotated

import typer


def check_paths_command(
    paths: Annotated[
        Path,
        typer.Option("--paths", help="Explicit TOML file containing [paths] settings."),
    ],
) -> None:
    """Resolve settings and check that both roots are existing directories."""
    from kelpseg.paths import PathSettingsError, check_paths, load_paths

    try:
        settings = check_paths(load_paths(paths))
    except PathSettingsError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"Settings: {settings.settings_file}")
    typer.echo(f"data_root: {settings.data_root}")
    typer.echo(f"runs_root: {settings.runs_root}")
    typer.echo("Both roots are existing directories.")
