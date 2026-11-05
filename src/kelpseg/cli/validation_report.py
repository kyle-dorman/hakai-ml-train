"""Read-only post-training validation diagnostics with a fresh report output."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def validation_report_command(
    run: Annotated[Path, typer.Option("--run", help="Completed training run folder.")],
    output: Annotated[
        Path, typer.Option("--output", help="Fresh report directory outside Git.")
    ],
    device: Annotated[
        str,
        typer.Option(help="cpu (default) or cuda; use CUDA after training finishes."),
    ] = "cpu",
    split: Annotated[
        str, typer.Option(help="val or a fixed unaugmented train sample.")
    ] = "val",
    sources_per_region: Annotated[
        int, typer.Option(help="Training sample TIFFs per region.")
    ] = 3,
    seed: Annotated[int, typer.Option(help="Training source sampling seed.")] = 42,
) -> None:
    """Write validation diagnostics from run into a fresh output directory.

    device selects cpu or cuda inference. Print the resulting HTML path and
    return nothing; report input/inference failures as CLI exit code 1.
    """
    from kelpseg.validation_report import validation_report

    handler, previous = start_preparation_logging("kelpseg")
    try:
        if device not in ("cpu", "cuda"):
            raise ValueError("device must be cpu or cuda.")
        result = validation_report(
            run,
            output,
            device=device,
            split=split,
            sources_per_region=sources_per_region,
            seed=seed,
        )
        typer.echo(str(result))
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous, "kelpseg")
