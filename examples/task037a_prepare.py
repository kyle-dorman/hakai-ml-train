"""Resolve the locked Task 037A inputs and start the prepared training run."""

import argparse
import json
import logging
from pathlib import Path

import rasterio

from kelpseg.paths import check_paths, load_paths
from kelpseg.prediction.settings import IDENTITY_COLUMNS
from kelpseg.prepare.split_inputs import original_key, read_collection
from kelpseg.prepare.splits import select_windows
from kelpseg.reporting.inputs import _indexed, read_csv
from kelpseg.reporting.report import write_csv

REFERENCE_ID = "planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z"
TILING = {"stride": 256, "min_valid_fraction": 0.2}
logger = logging.getLogger(__name__)


def read_json(path: Path) -> dict:
    """Read saved workflow metadata."""
    return json.loads(path.read_text())


def grid(path: Path) -> tuple:
    """Read TIFF dimensions, affine transform and CRS without loading pixels."""
    with rasterio.open(path, GEOREF_SOURCES="INTERNAL") as raster:
        return raster.shape, raster.transform, raster.crs


def validation_assignments(path: Path) -> dict:
    """Return shared validation sources after comparing all non-BC assignments."""
    arms = {"base": {}, "augmented": {}}
    for row in read_csv(path):
        if row["experiment"] != "baseline" or row["variant"] not in arms:
            continue
        if row["region"] in ("011", "012"):
            expected = "unused" if row["variant"] == "base" else "train"
            if row["split"] != expected:
                raise ValueError(f"Unexpected BC assignment: {row}.")
            continue
        arm = arms[row["variant"]]
        key = original_key(row)
        if key in arm:
            raise ValueError(f"Duplicate assignment: {key}.")
        arm[key] = {key: value for key, value in row.items() if key != "variant"}
    if arms["base"] != arms["augmented"]:
        raise ValueError("Non-BC assignments differ between base and augmented.")
    return {key: row for key, row in arms["base"].items() if row["split"] == "val"}


def manifests(
    cleaned: Path, assignments: dict, bands: tuple[str, ...]
) -> tuple[list, list]:
    """Join canonical source identities to images and labels, checking exact grids."""
    sources, labels = [], []
    matched = set()
    for identity in read_collection(cleaned=cleaned, release_id="v1"):
        key = original_key(identity)
        if key not in assignments:
            continue
        matched.add(key)
        source_id = identity["source_id"]
        region, day = identity["region"], identity["acquisition_date"]
        assigned = assignments[key]
        if (region, day) != (assigned["region"], assigned["acquisition_date"]):
            raise ValueError(
                f"{source_id}: cleaned identity conflicts with assignment."
            )
        image = cleaned / "images" / identity["original_tiff"]
        label = cleaned / "labels" / identity["original_tiff"]
        logger.info("Checking validation TIFF %s", image)
        if grid(image) != grid(label):
            raise ValueError(f"{source_id}: image and label grids differ.")
        sources.append(
            dict(
                source_key=source_id,
                image=str(image),
                band_names=";".join(bands),
                dataset_id=identity["dataset_id"],
                release_id=identity["release_id"],
                region_id=region,
                acquisition_date=day,
                original_source_id=source_id,
                row_offset="0",
                col_offset="0",
            )
        )
        labels.append(dict(source_key=source_id, label=str(label), source_id=source_id))
    _indexed(sources, "source_key", "Cleaned validation sources")
    if matched != assignments.keys():
        raise ValueError(
            "Cleaned sources do not cover the exact validation assignment."
        )
    return sources, labels


def check_prediction_scope(root: Path, sources: list[dict], model: dict) -> dict:
    """Verify a saved tiled prediction set matches the selected bundle and scope."""
    metadata = read_json(root / "settings.json")
    recipe = metadata["recipe"]
    if (
        read_json(root / "summary.json")["status"] != "complete"
        or metadata.get("scope", "tiff_tiled") != "tiff_tiled"
        or metadata["model"] != model
        or any(recipe.get(key) != value for key, value in TILING.items())
    ):
        raise ValueError(
            f"{root}: expected completed tiled predictions for the selected bundle and 256/0.20 policy."
        )
    indexed = _indexed(read_csv(root / "sources.csv"), "source_key", str(root))
    if indexed.keys() != {row["source_key"] for row in sources}:
        raise ValueError(
            f"{root}: TIFF identities differ from the validation manifest."
        )
    for source in sources:
        key = source["source_key"]
        prediction = indexed[key]
        if any(
            prediction[column] != source[column]
            for column in (*IDENTITY_COLUMNS, "band_names", "image")
        ):
            raise ValueError(f"{root}: saved source metadata differs for {key}.")
    return indexed


def check_reference(preview: dict, reference: Path) -> None:
    """Compare resolved settings, compute and exact chip validation windows."""
    saved = read_json(reference / "run.json")
    if (saved["status"], saved["run_id"], saved["optimizer_updates_actual"]) != (
        "complete",
        REFERENCE_ID,
        12780,
    ):
        raise ValueError(f"{reference}: expected the completed 037A reference run.")
    current = json.loads(json.dumps(preview["settings"]))
    varying = {"name", "variant", "paths_file", "train_draws_per_epoch"}
    if {key: value for key, value in current.items() if key not in varying} != {
        key: value for key, value in saved["settings"].items() if key not in varying
    }:
        raise ValueError("No-BC recipe settings differ from the saved reference.")
    budget = preview["budget"]
    if (
        preview["variant"] != "base"
        or preview["counts"]["training_eligible"] != 7280
        or preview["counts"]["validation"] != 933
        or preview["counts"]["validation_sources"] != 53
        or preview["regions"] != [f"{code:03}" for code in range(1, 11)]
        or budget["training_draws_per_epoch"] != saved["counts"]["training_eligible"]
        or budget["training_draws_per_epoch"] != 8518
        or any(
            budget[key] != value
            for key, value in saved["budget"].items()
            if isinstance(value, int)
        )
    ):
        raise ValueError("No-BC source scope or planned budget differs from 037A.")
    windows = select_windows(
        preview["chips"], preview["assignments"], experiment="baseline", variant="base"
    )
    historical = read_csv(reference / "validation-predictions" / "windows.csv")
    keys = (
        "dataset_id",
        "release_id",
        "source_id",
        "original_row",
        "original_col",
        "height",
        "width",
    )
    current_windows = {
        tuple(str(row[key]) for key in keys) for row in windows if row["split"] == "val"
    }
    saved_windows = {tuple(row[key] for key in keys) for row in historical}
    if len(current_windows) != 933 or current_windows != saved_windows:
        raise ValueError("Chip validation windows differ from the saved reference.")


def write_recipe(path: Path, **values: str | Path | int | float) -> None:
    """Write a small flat TOML file with quoted string paths."""
    path.write_text(
        "".join(
            f"{key} = {json.dumps(str(value) if isinstance(value, Path) else value)}\n"
            for key, value in values.items()
        )
    )


def write_evaluation_recipes(
    output: Path,
    assignment_path: Path,
    models: dict[str, Path],
    *,
    device: str,
    reference_predictions: Path | None = None,
) -> None:
    """Write paired prediction, labeled segmentation and temporal recipes."""
    (output / "with-bc-model.json").write_text(
        json.dumps({"bundle": str(models["with-bc"])}) + "\n"
    )
    for arm, model in models.items():
        predictions = output / f"{arm}-predictions"
        if arm == "with-bc" and reference_predictions is not None:
            predictions = reference_predictions
        else:
            write_recipe(
                output / f"{arm}-predict.toml",
                model=model,
                manifest=output / "validation.csv",
                image_root=output,
                output=predictions,
                batch_size=1,
                device=device,
                **TILING,
            )
        report = output / f"{arm}-segmentation"
        write_recipe(
            output / f"{arm}-report.toml",
            predictions=predictions,
            output=report,
            labels=output / "labels.csv",
            label_root=output,
            assignments=assignment_path,
            experiment="baseline",
            variant="augmented" if arm == "with-bc" else "base",
            split="val",
        )
        write_recipe(
            output / f"{arm}-temporal.toml",
            report=report,
            output=output / f"{arm}-temporal",
        )


def prepare(recipe: Path, output: Path, reference_predictions: Path | None) -> None:
    """Verify production inputs and save recipes and dry-run evidence into fresh output."""
    from kelpseg.training.run import run_training
    from kelpseg.training.settings import load_settings

    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a fresh path.")
    settings = load_settings(recipe)
    paths = check_paths(load_paths(settings.paths_file))
    reference = paths.data_root / "model-size-runs" / REFERENCE_ID
    preview = run_training(settings, paths, dry_run=True)
    check_reference(preview, reference)
    native_bands = tuple(
        read_json(Path(preview["chips"]) / "recipe.json")["source_band_names"]
    )
    if settings.band_names != native_bands:
        raise ValueError("Canonical native bands differ from the eight-band recipe.")
    assignment_path = Path(preview["assignments"])
    assignments = validation_assignments(assignment_path)
    if len(assignments) != 53:
        raise ValueError("Expected 53 shared validation TIFFs.")
    sources, labels = manifests(
        paths.data_root / "data/3_cleaned/ca_bc/v1", assignments, settings.band_names
    )
    model = reference / "model"
    metadata = read_json(model / "model.json")
    if (
        metadata["run_id"],
        metadata["weight_kind"],
        metadata["checkpoint_epoch"],
        metadata["threshold"],
    ) != (REFERENCE_ID, "ema", 15, 0.5) or not (model / "weights.pt").is_file():
        raise ValueError("Reference must contain the selected epoch-16 EMA bundle.")
    if reference_predictions is not None:
        saved = check_prediction_scope(reference_predictions, sources, metadata)
        for source in sources:
            key = source["source_key"]
            if grid(reference_predictions / saved[key]["probability"]) != grid(
                Path(source["image"])
            ):
                raise ValueError(f"{key}: saved reference probability grid differs.")
        logger.info(
            "Using saved tiled reference predictions: %s", reference_predictions
        )
    output.mkdir(parents=True)
    write_csv(output / "validation.csv", sources)
    write_csv(output / "labels.csv", labels)
    (output / "no-bc-dry-run.json").write_text(json.dumps(preview, indent=2) + "\n")
    write_evaluation_recipes(
        output,
        assignment_path,
        {"with-bc": model, "no-bc": Path(preview["output"]) / "model"},
        device="cuda",
        reference_predictions=reference_predictions,
    )
    logger.info(
        "%d eligible windows; %d draws, %d microbatches and %d updates per epoch; %d planned updates",
        preview["counts"]["training_eligible"],
        preview["budget"]["training_draws_per_epoch"],
        preview["budget"]["training_batches_per_epoch"],
        preview["budget"]["optimizer_updates_per_epoch"],
        preview["budget"]["optimizer_updates_total"],
    )
    logger.info("Ready: %s; training output: %s", output, preview["output"])


def main() -> None:
    """Run one preparation or fitting stage for the Bash launcher."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("output", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fit", action="store_true", help="Fit the prepared run.")
    mode.add_argument("--reference-predictions", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.fit:
            from kelpseg.training.run import run_training
            from kelpseg.training.settings import load_settings

            preview = read_json(args.output / "no-bc-dry-run.json")
            settings = load_settings(args.recipe)
            paths = check_paths(load_paths(settings.paths_file))
            run_training(settings, paths, run_id=preview["run_id"])
            return
        prepare(
            args.recipe,
            args.output.resolve(),
            args.reference_predictions.resolve()
            if args.reference_predictions
            else None,
        )
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Task 037A failed: {error}\n")


if __name__ == "__main__":
    main()
