"""Installed command for deriving shoreline-enriched chip payloads."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def prepare_chip_distances_command(
    chips: Annotated[Path, typer.Option(help="Canonical labeled chip directory.")],
    shoreline: Annotated[Path, typer.Option(help="Prepared shoreline directory.")],
    output: Annotated[Path, typer.Option(help="Fresh derived chip directory.")],
    workers: Annotated[
        int, typer.Option(min=1, help="Processes copying separate sources.")
    ] = 1,
) -> None:
    """Publish a fresh derived dataset, or report the preparation error."""
    from kelpseg.prepare.chip_distances import prepare_chip_distances

    handler, previous = start_preparation_logging()
    try:
        typer.echo(
            str(prepare_chip_distances(chips, shoreline, output, workers=workers))
        )
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous)
