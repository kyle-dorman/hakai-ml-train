"""Thin presentation for explicit organization plans and byte-preserving copies."""

from pathlib import Path
from typing import Annotated

import typer

from kelpseg.cli._logging import start_preparation_logging, stop_preparation_logging


def organize_command(
    recipe: Annotated[
        Path, typer.Option("--recipe", help="Explicit organization TOML.")
    ],
    paths: Annotated[Path, typer.Option("--paths", help="Explicit local path TOML.")],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Validate scope without writing or hashing payloads."
        ),
    ] = False,
) -> None:
    """Organize declared pairs and companions without changing source bytes."""
    from kelpseg.paths import PathSettingsError, check_paths, load_paths
    from kelpseg.prepare.organize import organize_dataset
    from kelpseg.prepare.organize_inputs import (
        OrganizeError,
        build_organization_plan,
        load_organize_recipe,
    )

    handler, previous_logging = start_preparation_logging()
    try:
        settings = check_paths(load_paths(paths))
        recipe_settings = load_organize_recipe(recipe)
        plan = build_organization_plan(recipe_settings, settings)

        # Show the complete plan before copying any payloads.
        regions = set()
        payload_bytes = 0
        for member in plan.membership:
            regions.add(member["region_code"])
        for file in plan.files:
            payload_bytes += file.bytes
        typer.echo(f"Recipe: {plan.recipe.recipe_file}")
        typer.echo(f"Input catalog: {plan.catalog}")
        for delivery in plan.deliveries:
            typer.echo(
                f"Delivery {delivery['delivery_id']}: {plan.resolved_deliveries[delivery['delivery_id']]} ({delivery['kind']}; {delivery['evidence']})"
            )
        typer.echo(
            f"Dataset/release: {plan.recipe.dataset_id}/{plan.recipe.release_id}"
        )
        typer.echo(
            f"Pairs: {len(plan.membership)}; deliveries: {len(plan.deliveries)}; "
            f"regions: {len(regions)}; companions: {len(plan.assets)}"
        )
        typer.echo(f"Selected payload bytes: {payload_bytes}")
        typer.echo(
            "Band order: preserved unchanged; physical names remain unknown unless established by each TIFF header."
        )
        typer.echo(f"Destination: {plan.destination}")
        typer.echo(f"Logical plan SHA-256: {plan.plan_hash}")
        typer.echo(
            "Evidence: declarations and ZIP directory/file-catalog metadata; selected member bytes are verified during copying."
        )
        if dry_run:
            typer.echo(
                "Dry run valid. No files written; this is not a verified release."
            )
        else:
            output = organize_dataset(plan)
            typer.echo(f"Complete verified release: {output}")
    except (OrganizeError, PathSettingsError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        stop_preparation_logging(handler, previous_logging)
