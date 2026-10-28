"""Thin metadata-only source split command."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def split_command(
    recipe: Annotated[Path, typer.Option("--recipe", help="Split recipe TOML.")],
    output: Annotated[Path, typer.Option("--output", help="Fresh output directory.")],
    cleaned: Annotated[
        Path | None,
        typer.Option("--cleaned", help="Cleaned release root with sources.json."),
    ] = None,
    release_id: Annotated[
        str | None,
        typer.Option("--release-id", help="Explicit cleaned release version."),
    ] = None,
    sources: Annotated[
        Path | None, typer.Option("--sources", help="Declared source identity CSV.")
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Validate metadata only, without writes or image reads."
        ),
    ] = False,
) -> None:
    """Assign original sources and LORO folds; keep chips in one collection."""
    from kelpseg.prepare.check import PreparationError
    from kelpseg.prepare.split_inputs import load_split_recipe, read_collection
    from kelpseg.prepare.splits import (
        assign_sources,
        check_split_output,
        summarize_assignments,
        write_splits,
    )

    handler, previous = start_preparation_logging()
    try:
        settings = load_split_recipe(recipe)
        collection = read_collection(
            cleaned=cleaned, release_id=release_id, sources=sources
        )
        target = check_split_output(output)
        rows = assign_sources(collection, settings)
        summary = summarize_assignments(collection, rows)
        typer.echo(
            f"Input: {(cleaned or sources).expanduser().resolve()}\nRecipe: {recipe.resolve()}\nOutput: {target}"
        )
        typer.echo(
            f"Original sources: {summary['original_sources']}; crop rows: {summary['crop_rows']}; regions: {len(summary['regions'])}; UTC dates: {summary['distinct_dates']}"
        )
        for scope, values in summary["assignments"].items():
            counts = values["source_counts"]
            typer.echo(
                f"{scope}: "
                + "; ".join(f"{name} {count}" for name, count in counts.items())
            )
        if dry_run:
            typer.echo("Dry run valid: metadata only; no writes or image reads.")
        else:
            typer.echo(
                f"Complete split output: {write_splits(collection, rows, settings, target)}"
            )
    except (PreparationError, OSError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous)
