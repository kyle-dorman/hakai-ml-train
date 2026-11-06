"""Installed label-only shore-distance inventory command."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def shore_inventory_command(
    recipe: Annotated[
        Path, typer.Option("--recipe", help="Label inventory TOML recipe.")
    ],
) -> None:
    """Read settings, generate the inventory and print its HTML path or an error."""
    from kelpseg.reporting.shore_inventory import shore_inventory
    from kelpseg.reporting.shore_inventory_inputs import load_settings

    handler, previous = start_preparation_logging("kelpseg")
    try:
        typer.echo(str(shore_inventory(load_settings(recipe))))
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous, "kelpseg")
