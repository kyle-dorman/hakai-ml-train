"""Thin presentation for read-only directory checking."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def check_command(
    images: Annotated[Path, typer.Option("--images", help="Image TIFF directory.")],
    recipe: Annotated[Path, typer.Option("--recipe", help="Explicit check TOML.")],
    labels: Annotated[
        Path | None, typer.Option("--labels", help="Optional paired label directory.")
    ] = None,
    full: Annotated[
        bool,
        typer.Option(
            "--full",
            help="Read all native image/label pixels; large mosaics may be expensive.",
        ),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report", help="Fresh JSON report outside inputs; no default sidecars."
        ),
    ] = None,
) -> None:
    """Check headers by default, or all selected pixels with --full."""
    from kelpseg.prepare.check import PreparationError, check_inputs, load_check_recipe

    handler, previous_logging = start_preparation_logging()
    try:
        settings = load_check_recipe(recipe)
        result = check_inputs(images, labels, settings, full=full, report=report)

        # The summary names the work actually requested: headers or pixels.
        status = "failed"
        if result.passed:
            status = "passed"
        typer.echo(
            f"{result.level.capitalize()} {result.profile} check {status}: "
            f"{result.source_count} sources, {result.payload_bytes} payload bytes."
        )
        typer.echo(
            f"Scanned pixels: images={result.scanned_image_pixels}, labels={result.scanned_label_pixels}. File hashes not checked."
        )
        for skipped in result.skipped_checks:
            typer.echo(f"Skipped: {skipped}.")
        for unknown in result.unknowns:
            typer.echo(f"Unknown: {unknown}")
        # Findings were already logged once on stderr during checking.
        if report is not None:
            typer.echo(f"Report: {report.expanduser().absolute()}")
        if not result.passed:
            raise typer.Exit(code=1)
    except (PreparationError, OSError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous_logging)
