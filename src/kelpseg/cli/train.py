"""Training command; heavy model dependencies are imported only on execution."""

import json
from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def train_command(
    recipe: Annotated[
        Path,
        typer.Option(
            "--recipe", help="Training recipe TOML with optional [[losses]] terms."
        ),
    ],
    resume: Annotated[
        Path | None,
        typer.Option(
            "--resume",
            help="Resume from completed-epoch last.ckpt; worker random streams restart.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview metadata and budget without reading chip arrays or fitting.",
        ),
    ] = False,
) -> None:
    """Train the baseline with Lightning, or preview inputs without fitting."""
    from kelpseg.paths import check_paths, load_paths
    from kelpseg.training.run import run_training
    from kelpseg.training.settings import load_settings

    handler, previous = start_preparation_logging()
    try:
        settings = load_settings(recipe)
        report = run_training(
            settings,
            check_paths(load_paths(settings.paths_file)),
            dry_run=dry_run,
            resume=resume,
        )
        typer.echo(json.dumps(report, indent=2, default=str))
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous)
