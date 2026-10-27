"""Thin presentation for explicit organization plans and byte-preserving copies."""

import logging
from pathlib import Path
from typing import Annotated

import typer


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
    resume: Annotated[
        bool,
        typer.Option(
            "--resume", help="Resume only a matching verified incomplete release."
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

    # Keep CLI progress on stderr; notebooks can configure normal logging themselves.
    progress = logging.getLogger("kelpseg.prepare")
    previous_level = progress.level
    previous_propagation = progress.propagate
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    )
    progress.addHandler(handler)
    progress.setLevel(logging.INFO)
    progress.propagate = False
    try:
        if dry_run and resume:
            raise OrganizeError("Use --dry-run or --resume separately.")
        settings = check_paths(load_paths(paths))
        plan = build_organization_plan(load_organize_recipe(recipe), settings)
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
            f"Pairs: {len(plan.membership)}; deliveries: {len(plan.deliveries)}; regions: {len({r['region_code'] for r in plan.membership})}; companions: {len(plan.assets)}"
        )
        typer.echo(f"Selected payload bytes: {sum(f.bytes for f in plan.files)}")
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
            output = organize_dataset(plan, resume=resume)
            typer.echo(f"Complete verified release: {output}")
    except (OrganizeError, PathSettingsError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None
    finally:
        progress.removeHandler(handler)
        progress.setLevel(previous_level)
        progress.propagate = previous_propagation
        handler.close()
