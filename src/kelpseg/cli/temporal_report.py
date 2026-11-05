"""Installed temporal diagnostics from saved labeled reports."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def temporal_report_command(
    recipe: Annotated[
        Path, typer.Option("--recipe", help="Temporal report TOML recipe.")
    ],
) -> None:
    """Read a flat recipe and print the report HTML path, or an actionable error."""
    from kelpseg.reporting.temporal import temporal_report
    from kelpseg.reporting.temporal_inputs import load_settings

    handler, previous = start_preparation_logging("kelpseg.reporting")
    try:
        typer.echo(str(temporal_report(load_settings(recipe))))
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous, "kelpseg.reporting")
