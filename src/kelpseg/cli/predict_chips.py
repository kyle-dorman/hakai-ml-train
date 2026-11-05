"""Thin installed interface for saved predictions on disjoint evaluation chips."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def predict_chips_command(
    run: Annotated[Path, typer.Option("--run", help="Completed training run folder.")],
    output: Annotated[
        Path, typer.Option("--output", help="Fresh prediction directory.")
    ],
    device: Annotated[str, typer.Option(help="cpu or cuda.")] = "cpu",
    split: Annotated[
        str, typer.Option(help="val or a fixed unaugmented train sample.")
    ] = "val",
    sources_per_region: Annotated[
        int, typer.Option(help="Training sample TIFFs per region.")
    ] = 3,
    seed: Annotated[int, typer.Option(help="Training source sampling seed.")] = 42,
) -> None:
    """Predict selected chips from run; print the saved output path or an error."""
    from kelpseg.prediction.chips import predict_chips

    handler, previous = start_preparation_logging("kelpseg")
    try:
        typer.echo(
            str(
                predict_chips(
                    run,
                    output,
                    device=device,
                    split=split,
                    sources_per_region=sources_per_region,
                    seed=seed,
                )
            )
        )
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous, "kelpseg")
