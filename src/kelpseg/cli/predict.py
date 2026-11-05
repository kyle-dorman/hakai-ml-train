"""Thin installed interface for image-only tiled prediction."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def predict_command(
    recipe: Annotated[Path, typer.Option("--recipe", help="Prediction TOML recipe.")],
) -> None:
    """Read recipe and predict into its fresh output; print the path or an error."""
    from kelpseg.prediction.predict import predict
    from kelpseg.prediction.settings import load_settings

    handler, previous = start_preparation_logging("kelpseg.prediction")
    try:
        typer.echo(str(predict(load_settings(recipe))))
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous, "kelpseg.prediction")
