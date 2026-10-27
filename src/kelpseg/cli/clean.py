"""Thin directory cleanup presentation; reusable work lives under prepare."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def clean_command(
    images: Annotated[Path, typer.Option("--images", help="Image TIFF directory.")],
    output: Annotated[
        Path, typer.Option("--output", help="Fresh separate output directory.")
    ],
    recipe: Annotated[Path, typer.Option("--recipe", help="Explicit cleanup TOML.")],
    labels: Annotated[
        Path | None,
        typer.Option("--labels", help="Optional complete paired-label directory."),
    ] = None,
    parent: Annotated[
        Path | None,
        typer.Option("--parent", help="Optional entire verified organized release."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Check scope/headers without pixels, hashes or writes."
        ),
    ] = False,
) -> None:
    """Clean supported paired or image-only directories, preserving originals."""
    from kelpseg.prepare.check import PreparationError
    from kelpseg.prepare.clean import clean_dataset
    from kelpseg.prepare.clean_inputs import build_clean_plan, load_clean_recipe

    handler, previous_logging = start_preparation_logging()
    try:
        settings = load_clean_recipe(recipe)
        plan = build_clean_plan(images, labels, output, settings, parent=parent)
        typer.echo(
            f"Images: {plan.images}\nLabels: {plan.labels or 'none (image-only)'}"
        )
        typer.echo(
            f"Sources: {len(plan.pairs)}; source/asset bytes: {plan.source_bytes}"
        )
        typer.echo(
            f"Bands preserved; physical names unknown unless established in source evidence.\nOutput: {plan.output}"
        )
        if dry_run:
            typer.echo(
                "Dry run valid. Headers/scope only; no pixels read, hashes calculated or files written."
            )
        else:
            result = clean_dataset(plan)
            typer.echo(f"Complete verified cleaned output: {result}")
    except PreparationError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous_logging)
