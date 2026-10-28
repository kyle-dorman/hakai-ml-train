"""Small installed command with explicitly registered workflow handlers."""

from importlib.metadata import version as distribution_version
from typing import Annotated

import typer

from kelpseg.cli.check import check_command
from kelpseg.cli.chip import chip_command
from kelpseg.cli.clean import clean_command
from kelpseg.cli.organize import organize_command
from kelpseg.cli.paths import check_paths_command
from kelpseg.cli.split import split_command

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
