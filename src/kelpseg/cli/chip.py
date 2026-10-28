"""Thin chipping command; plain reusable functions live in prepare."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def chip_command(
    images: Annotated[
        Path, typer.Option("--images", help="Cleaned image TIFF directory.")
    ],
    output: Annotated[Path, typer.Option("--output", help="Fresh output directory.")],
    recipe: Annotated[Path, typer.Option("--recipe", help="Explicit chipping TOML.")],
    labels: Annotated[
        Path | None,
        typer.Option("--labels", help="Optional aligned label TIFF directory."),
    ] = None,
    metadata: Annotated[
        Path | None,
        typer.Option("--metadata", help="Optional exact-key source identity CSV."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Inspect headers and window counts; no pixel reads or writes.",
        ),
    ] = False,
) -> None:
    """Chip cleaned imagery once, keeping native bands and true edge sizes."""
    from kelpseg.prepare.check import PreparationError
    from kelpseg.prepare.chip import chip_dataset
    from kelpseg.prepare.chip_inputs import build_chip_plan, load_chip_recipe

    handler, previous = start_preparation_logging()
    try:
        settings = load_chip_recipe(recipe)
        plan = build_chip_plan(images, labels, output, settings, metadata=metadata)
        typer.echo(
            f"Images: {plan.images}\nLabels: {plan.labels or 'none (image-only)'}"
        )
        typer.echo(
            f"Sources: {len(plan.pairs)}; candidate windows: {plan.window_count}; input bytes: {plan.source_bytes}"
        )
        typer.echo(
            f"Native bands (recipe declaration): {', '.join(settings.source_band_names)}"
        )
        typer.echo(
            f"Size: {settings.chip_size}; stride: {settings.stride}; maximum nodata: {settings.max_nodata_pct}%\nOutput: {plan.output}"
        )
        if dry_run:
            typer.echo(
                "Dry run valid: headers only; pixel values and threshold retention not checked."
            )
        else:
            typer.echo(f"Complete chip output: {chip_dataset(plan)}")
    except (PreparationError, OSError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous)
