"""Thin installed interface for reports from saved chip or TIFF predictions."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def report_command(
    recipe: Annotated[
        Path, typer.Option("--recipe", help="Labeled report TOML recipe.")
    ],
) -> None:
    """Read recipe and summarize saved predictions; print the HTML path or an error."""
    from kelpseg.reporting.inputs import load_settings
    from kelpseg.reporting.report import report

    handler, previous = start_preparation_logging("kelpseg.reporting")
    try:
        typer.echo(str(report(load_settings(recipe))))
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous, "kelpseg.reporting")
