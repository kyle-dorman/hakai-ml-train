"""Small installed command with explicitly registered workflow handlers."""

from importlib.metadata import version as distribution_version
from typing import Annotated

import typer

from kelpseg.cli.check import check_command
from kelpseg.cli.chip import chip_command
from kelpseg.cli.chip_distances import prepare_chip_distances_command
from kelpseg.cli.clean import clean_command
from kelpseg.cli.organize import organize_command
from kelpseg.cli.paths import check_paths_command
from kelpseg.cli.pixel_stats import pixel_stats_command
from kelpseg.cli.predict import predict_command
from kelpseg.cli.predict_chips import predict_chips_command
from kelpseg.cli.previews import preview_augmentations_command, preview_pipeline_command
from kelpseg.cli.report import report_command
from kelpseg.cli.shore_inventory import shore_inventory_command
from kelpseg.cli.shoreline import prepare_shoreline_command
from kelpseg.cli.split import split_command
from kelpseg.cli.temporal_report import temporal_report_command
from kelpseg.cli.train import train_command

app = typer.Typer(
    help="Tools for binary kelp segmentation on Planet imagery.",
    no_args_is_help=True,
    invoke_without_command=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed version.", is_eager=True),
    ] = False,
) -> None:
    if version:
        typer.echo(f"kelpseg {distribution_version('kelpseg')}")
        raise typer.Exit()


app.command("check-paths")(check_paths_command)

app.command("organize")(organize_command)

app.command("check")(check_command)
app.command("clean")(clean_command)

app.command("chip")(chip_command)

app.command("split")(split_command)
app.command("pixel-stats")(pixel_stats_command)

app.command("train")(train_command)

app.command("predict-chips")(predict_chips_command)
app.command("report")(report_command)

app.command("predict")(predict_command)

app.command("temporal-report")(temporal_report_command)

app.command("prepare-shoreline")(prepare_shoreline_command)
app.command("shore-inventory")(shore_inventory_command)
app.command("prepare-chip-distances")(prepare_chip_distances_command)

app.command("preview-augmentations")(preview_augmentations_command)
app.command("preview-pipeline")(preview_pipeline_command)
