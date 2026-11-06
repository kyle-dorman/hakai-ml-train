"""Installed command for source-aligned land and shore-distance preparation."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def prepare_shoreline_command(
    recipe: Annotated[
        Path, typer.Option("--recipe", help="Shoreline preparation TOML recipe.")
    ],
) -> None:
    """Prepare geometry-only source rasters and print the output path or error."""
    from kelpseg.prepare.shoreline import load_settings, prepare_shoreline

    handler, previous = start_preparation_logging()
    try:
        typer.echo(str(prepare_shoreline(load_settings(recipe))))
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous)
