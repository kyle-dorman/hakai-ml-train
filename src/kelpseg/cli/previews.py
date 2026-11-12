"""Installed launchers for the existing training-only augmentation galleries."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def preview_augmentations_command(
    chips: Annotated[
        Path,
        typer.Option("--chips", help="Canonical native eight-band chip collection."),
    ],
    assignments: Annotated[
        Path, typer.Option("--assignments", help="Source split assignment CSV.")
    ],
    output: Annotated[
        Path, typer.Option("--output", help="Fresh output gallery directory.")
    ],
    variant: Annotated[
        str,
        typer.Option(
            "--variant", help="Baseline assignment variant: base or augmented."
        ),
    ] = "augmented",
    seed: Annotated[
        int,
        typer.Option(
            "--seed", min=0, help="Seed for repeatable preview samples and draws."
        ),
    ] = 33,
    positive_samples: Annotated[
        int,
        typer.Option(
            "--positive-samples",
            min=1,
            max=16,
            help="Kelp-rich training examples, plus two background controls.",
        ),
    ] = 14,
) -> None:
    """Preview individual stock augmentations on training examples.

    Read chips and assignments from the supplied paths, write a fresh gallery,
    and print its index path. Existing preview functions own rendering behavior.
    """
    from kelpseg.augmentation_debug.preview import preview_augmentations

    handler, previous = start_preparation_logging("kelpseg")
    try:
        gallery = preview_augmentations(
            chips=chips,
            assignments=assignments.expanduser().resolve(),
            variant=variant,
            output=output,
            seed=seed,
            positive_samples=positive_samples,
        )
        typer.echo(f"Open in your browser: {gallery / 'index.html'}")
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous, "kelpseg")


def preview_pipeline_command(
    chips: Annotated[
        Path,
        typer.Option("--chips", help="Canonical native eight-band chip collection."),
    ],
    assignments: Annotated[
        Path, typer.Option("--assignments", help="Source split assignment CSV.")
    ],
    output: Annotated[
        Path, typer.Option("--output", help="Fresh output gallery directory.")
    ],
    variant: Annotated[
        str,
        typer.Option(
            "--variant", help="Baseline assignment variant: base or augmented."
        ),
    ] = "augmented",
    seed: Annotated[
        int,
        typer.Option(
            "--seed", min=0, help="Seed for repeatable preview samples and draws."
        ),
    ] = 33,
    positive_samples: Annotated[
        int,
        typer.Option(
            "--positive-samples",
            min=1,
            max=16,
            help="Kelp-rich training examples, plus two background controls.",
        ),
    ] = 14,
    draws: Annotated[
        int,
        typer.Option(
            "--draws", min=1, max=32, help="Seeded pipeline draws per example."
        ),
    ] = 8,
) -> None:
    """Preview seeded draws of the combined training augmentation pipeline.

    Read chips and assignments from the supplied paths, write a fresh gallery,
    and print its index path. Existing preview functions own rendering behavior.
    """
    from kelpseg.augmentation_debug.pipeline import preview_pipeline

    handler, previous = start_preparation_logging("kelpseg")
    try:
        gallery = preview_pipeline(
            chips=chips,
            assignments=assignments.expanduser().resolve(),
            variant=variant,
            output=output,
            seed=seed,
            positive_samples=positive_samples,
            draws=draws,
        )
        typer.echo(f"Open in your browser: {gallery / 'index.html'}")
    except (OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous, "kelpseg")
