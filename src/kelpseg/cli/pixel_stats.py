"""Thin training-image statistics command; the computation uses NumPy only."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def pixel_stats_command(
    chips: Annotated[
        Path, typer.Option("--chips", help="Canonical chip collection root.")
    ],
    assignments: Annotated[
        Path, typer.Option("--assignments", help="Source split assignment CSV.")
    ],
    output: Annotated[
        Path, typer.Option("--output", help="Fresh statistics JSON file.")
    ],
    experiment: Annotated[
        str,
        typer.Option(
            "--experiment", help="Assignment experiment, e.g. baseline or loro_001."
        ),
    ] = "baseline",
    variant: Annotated[
        str,
        typer.Option("--variant", help="Assignment variant, e.g. base or augmented."),
    ] = "augmented",
    kelp_only: Annotated[
        bool,
        typer.Option(
            "--kelp-only",
            help="Select entire training chips with manifest kelp_pixels > 0.",
        ),
    ] = False,
    clip_value: Annotated[
        float | None,
        typer.Option(
            "--clip-value",
            help="Optional upper cap in raw units before moments; omit for uncapped statistics.",
        ),
    ] = None,
) -> None:
    """Compute raw band means and sample standard deviations from training images."""
    from kelpseg.prepare.channel_stats import compute_channel_stats
    from kelpseg.prepare.check import PreparationError

    handler, previous = start_preparation_logging()
    try:
        report = compute_channel_stats(
            chips,
            assignments,
            output,
            experiment=experiment,
            variant=variant,
            kelp_only=kelp_only,
            clip_value=clip_value,
        )
        typer.echo(f"Complete pixel statistics: {output.expanduser().resolve()}")
        typer.echo(
            f"Training chips: {report['selected_training_windows']:,} selected / "
            f"{report['available_training_windows']:,} available; "
            f"non-nodata pixel exposures: {report['pixels']:,}"
        )
        for name, mean, std in zip(
            report["band_names"], report["mean"], report["std_sample"], strict=True
        ):
            typer.echo(f"{name}: mean {mean:.12g}; sample std {std:.12g}")
    except (PreparationError, OSError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous)
