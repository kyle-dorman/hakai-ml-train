"""Run the fixed 037B comparison using the installed training and report functions."""

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path
from shutil import copyfile
from statistics import mean

import numpy as np
import rasterio

from kelpseg.paths import PathSettings, check_paths, load_paths
from kelpseg.prediction.predict import predict
from kelpseg.prediction.settings import PredictionSettings
from kelpseg.reporting.inputs import ReportSettings, read_csv, read_probability
from kelpseg.reporting.metrics import COUNT_KEYS, scores
from kelpseg.reporting.report import pooled, report, write_csv
from kelpseg.reporting.temporal import temporal_report
from kelpseg.reporting.temporal_inputs import TemporalSettings
from kelpseg.training.run import run_training
from kelpseg.training.settings import TrainingSettings, load_settings

RECIPE_DIR = Path(__file__).resolve().parents[1] / "configs/train/baseline_comparisons"
REFERENCE = "planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z"
SPECTRAL_BANDS = {
    "planet4": ("red", "green", "blue", "nir"),
    "planet3": ("nir", "red", "green"),
}
TILING = {"stride": 256, "min_valid_fraction": 0.2, "batch_size": 1}
logger = logging.getLogger(__name__)


def read_json(path: Path) -> dict:
    """Read saved run or prediction metadata."""
    return json.loads(path.read_text())


def load_arm(arm: str) -> tuple[TrainingSettings, PathSettings]:
    """Resolve one spectral recipe and its machine paths."""
    settings = load_settings(RECIPE_DIR / f"b0_{arm}.toml")
    return settings, check_paths(load_paths(settings.paths_file))


def check_reference(saved: Path, model: Path, assignments: Path) -> None:
    """Verify the completed 8-band predictions, validation membership and grids."""
    predictions = saved / "with-bc-predictions"
    metadata = read_json(predictions / "settings.json")
    expected = read_json(model / "model.json")
    if (
        (
            expected["run_id"],
            expected["checkpoint_epoch"],
            expected["weight_kind"],
            expected["threshold"],
            expected["input_size"],
        )
        != (REFERENCE, 15, "ema", 0.5, 512)
        or metadata["model"] != expected
        or metadata.get("scope", "tiff_tiled") != "tiff_tiled"
        or any(metadata["recipe"].get(key) != value for key, value in TILING.items())
        or read_json(predictions / "summary.json")["status"] != "complete"
    ):
        raise ValueError(
            "Expected the completed Task 037A epoch-16 EMA tiled predictions."
        )
    validation = read_csv(saved / "validation.csv")
    rows = read_csv(predictions / "sources.csv")
    indexed = {row["source_key"]: row for row in rows}
    if (
        len(rows) != len(indexed)
        or len(validation) != 53
        or indexed.keys() != {row["source_key"] for row in validation}
    ):
        raise ValueError(
            "Reference predictions must cover the 53 distinct validation TIFFs."
        )
    membership = {
        (
            row["dataset_id"],
            row["release_id"],
            row["source_id"],
            row["region"],
            row["acquisition_date"],
        )
        for row in read_csv(assignments)
        if (row["experiment"], row["variant"], row["split"])
        == ("baseline", "augmented", "val")
    }
    if membership != {
        (
            row["dataset_id"],
            row["release_id"],
            row["original_source_id"],
            row["region_id"],
            row["acquisition_date"],
        )
        for row in validation
    }:
        raise ValueError(
            "The saved TIFF scope differs from the current validation assignments."
        )
    for source in validation:
        key = source["source_key"]
        predicted = indexed[key]
        if any(predicted[column] != value for column, value in source.items()):
            raise ValueError(
                f"{key}: reference TIFF metadata differs from the validation manifest."
            )
        with (
            rasterio.open(source["image"], GEOREF_SOURCES="INTERNAL") as image,
            rasterio.open(predictions / predicted["probability"]) as probability,
        ):
            if (probability.shape, probability.transform, probability.crs) != (
                image.shape,
                image.transform,
                image.crs,
            ):
                raise ValueError(
                    f"{key}: the saved reference probability grid differs from the native TIFF."
                )
    logger.info(
        "Reusing epoch-16 EMA predictions for %d validation TIFFs in %s",
        len(validation),
        predictions,
    )


def prepare(output: Path, saved: Path, reference_run: Path) -> None:
    """Dry-run both production recipes, then stage the common manifests."""
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a fresh directory.")
    reference = read_json(reference_run / "run.json")
    previews = {}
    for arm, bands in SPECTRAL_BANDS.items():
        settings, paths = load_arm(arm)
        preview = json.loads(json.dumps(run_training(settings, paths, dry_run=True)))
        actual = preview["settings"]
        spectral = {"name", "band_names", "mean", "std", "paths_file"}
        if settings.band_names != bands or any(
            actual[key] != value
            for key, value in reference["settings"].items()
            if key not in spectral
        ):
            raise ValueError(
                f"{arm}: expected {bands} with the reference training settings."
            )
        for key in (
            "chips",
            "assignments",
            "counts",
            "regions",
            "budget",
            "augmentation",
            "ema",
            "selection",
        ):
            if preview[key] != reference[key]:
                raise ValueError(f"{arm}: {key} differs from the reference run.")
        previews[arm] = preview
        logger.info(
            "%s: %s; %s; output %s", arm, bands, preview["budget"], preview["output"]
        )
    check_reference(saved, reference_run / "model", Path(reference["assignments"]))
    output.mkdir(parents=True)
    for filename in ("validation.csv", "labels.csv"):
        copyfile(saved / filename, output / filename)
    for arm, preview in previews.items():
        (output / f"{arm}-preview.json").write_text(
            json.dumps(preview, indent=2) + "\n"
        )


def train_and_predict(arm: str, output: Path, device: str) -> None:
    """Fit the planned arm and predict the staged TIFF manifest using its selected model."""
    settings, paths = load_arm(arm)
    preview = read_json(output / f"{arm}-preview.json")
    run = run_training(settings, paths, run_id=preview["run_id"])
    predict(
        PredictionSettings(
            model=Path(run["model_bundle"]),
            manifest=output / "validation.csv",
            image_root=output,
            output=output / f"{arm}-predictions",
            device=device,
            **TILING,
        )
    )


def check_coverage(predictions: dict[str, Path]) -> None:
    """Require identical TIFF membership, grids and finite pixels before scoring."""
    sources = {
        arm: {
            row["source_key"]: root / row["probability"]
            for row in read_csv(root / "sources.csv")
        }
        for arm, root in predictions.items()
    }
    reference = sources["planet8"]
    if any(rows.keys() != reference.keys() for rows in sources.values()):
        raise ValueError("Prediction source identities differ between arms.")
    for key, path in reference.items():
        logger.info("Checking common finite coverage for %s", key)
        probability, transform, crs = read_probability(path)
        expected_grid = probability.shape, transform, crs
        finite = np.isfinite(probability)
        del probability
        for arm in SPECTRAL_BANDS:
            other, transform, crs = read_probability(sources[arm][key])
            if (other.shape, transform, crs) != expected_grid or not np.array_equal(
                np.isfinite(other), finite
            ):
                raise ValueError(
                    f"{arm} {key}: grid or finite coverage differs from planet8."
                )
            del other


def geography(region: str) -> str:
    """Group the locked validation regions using the canonical region catalog."""
    return "Baja" if region in ("001", "002") else "California"


def write_comparisons(output: Path, runs: dict[str, Path]) -> None:
    """Publish pooled geography scores, matched temporal errors and actual budgets."""
    segmentation, training = [], []
    pair_groups = {}
    for arm, root in runs.items():
        rows = read_csv(output / f"{arm}-segmentation/sources.csv")
        for row in rows:
            row["geography"] = geography(row["region"])
            row.update(
                {key: int(row[key]) for key in (*COUNT_KEYS, "uncovered_valid_pixels")}
            )
        for row in pooled(
            rows, ("geography",), (*COUNT_KEYS, "uncovered_valid_pixels")
        ):
            segmentation.append(
                dict(
                    arm=arm,
                    geography=row["geography"],
                    **scores({key: row[key] for key in COUNT_KEYS}),
                    uncovered_valid_pixels=row["uncovered_valid_pixels"],
                )
            )
        pairs = read_csv(output / f"{arm}-temporal/pairs.csv")
        pair_groups[arm] = {(r["earlier_source"], r["later_source"]): r for r in pairs}
        run, model = read_json(root / "run.json"), read_json(root / "model/model.json")
        training.append(
            dict(
                arm=arm,
                run_id=run["run_id"],
                planned_updates=run["budget"]["optimizer_updates_total"],
                actual_updates=run["optimizer_updates_actual"],
                selected_epoch=model["checkpoint_epoch"] + 1,
                weight_kind=model["weight_kind"],
                bundle=str(root / "model"),
            )
        )
    reference = pair_groups["planet8"]
    if any(pairs.keys() != reference.keys() for pairs in pair_groups.values()):
        raise ValueError("Temporal reports differ in date-pair identities.")
    groups = defaultdict(list)
    for key, first in reference.items():
        for pairs in pair_groups.values():
            if any(
                pairs[key][field] != first[field]
                for field in (
                    "region",
                    "interval",
                    "status",
                    "common_pixels",
                    "label_change_pct",
                )
            ):
                raise ValueError(
                    f"Temporal pair {key} differs in common support or labels."
                )
        groups[(geography(first["region"]), first["interval"])].append(key)
    temporal = []
    for (location, interval), keys in sorted(groups.items()):
        defined = [
            key
            for key in keys
            if all(
                pairs[key]["change_error_pp"] != "" for pairs in pair_groups.values()
            )
        ]
        for arm, pairs in pair_groups.items():
            errors = [float(pairs[key]["change_error_pp"]) for key in defined]
            temporal.append(
                dict(
                    arm=arm,
                    geography=location,
                    interval=interval,
                    pairs=len(keys),
                    supported=sum(
                        reference[key]["status"] == "supported" for key in keys
                    ),
                    all_arms_defined=len(defined),
                    arm_defined=sum(
                        pairs[key]["change_error_pp"] != "" for key in keys
                    ),
                    common_pixel_observations=sum(
                        int(reference[key]["common_pixels"]) for key in defined
                    ),
                    mean_signed_error_pp=mean(errors) if errors else None,
                    mean_absolute_error_pp=mean(map(abs, errors)) if errors else None,
                )
            )
    write_csv(output / "segmentation-geography.csv", segmentation)
    write_csv(output / "temporal-geography.csv", temporal)
    write_csv(output / "training-comparison.csv", training)


def evaluate(
    output: Path, saved: Path, reference_run: Path, shoreline: Path | None
) -> None:
    """Check matched predictions and run the standard reports for all three arms."""
    predictions = {"planet8": saved / "with-bc-predictions"}
    runs = {"planet8": reference_run}
    for arm in SPECTRAL_BANDS:
        predictions[arm] = output / f"{arm}-predictions"
        runs[arm] = Path(read_json(output / f"{arm}-preview.json")["output"])
    check_coverage(predictions)
    assignments = Path(read_json(reference_run / "run.json")["assignments"])
    for arm, root in predictions.items():
        segmentation = output / f"{arm}-segmentation"
        report(
            ReportSettings(
                predictions=root,
                output=segmentation,
                labels=output / "labels.csv",
                label_root=output,
                assignments=assignments,
                experiment="baseline",
                variant="augmented",
                split="val",
                shoreline=shoreline,
            )
        )
        temporal_report(
            TemporalSettings(report=segmentation, output=output / f"{arm}-temporal")
        )
    write_comparisons(output, runs)
    logger.info("Comparison tables and reports: %s", output)


def main() -> None:
    """Run one sequential launcher stage, reporting input failures to stderr."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "planet4", "planet3", "report"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S"
    )
    try:
        output = args.output.resolve()
        _, paths = load_arm("planet4")
        saved = paths.data_root / "analyses/task037a-without-bc-01"
        reference_run = paths.data_root / "model-size-runs" / REFERENCE
        if args.stage == "prepare":
            prepare(output, saved, reference_run)
        elif args.stage == "report":
            evaluate(
                output,
                saved,
                reference_run,
                paths.data_root / "analyses/task040_shoreline_v1",
            )
        else:
            train_and_predict(args.stage, output, device="cuda")
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        parser.exit(1, f"Task 037B {args.stage} failed: {error}\n")


if __name__ == "__main__":
    main()
