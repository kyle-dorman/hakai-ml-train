"""Prepare and launch the fixed Task 037C eight-band B0 LORO suite."""

import argparse
import json
import logging
from dataclasses import asdict, replace
from pathlib import Path

from kelpseg.paths import PathSettings, check_paths, load_paths
from kelpseg.prediction.predict import predict
from kelpseg.prediction.settings import PredictionSettings, read_sources
from kelpseg.prepare.splits import validate_assignments, validate_loro_assignments
from kelpseg.preprocessing import BAND_NAMES
from kelpseg.reporting.inputs import read_csv
from kelpseg.reporting.report import write_csv
from kelpseg.training.data import build_training_inputs
from kelpseg.training.resume import build_resume_identity
from kelpseg.training.run import run_training
from kelpseg.training.settings import TrainingSettings, load_settings

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z"
FOLDS = tuple(f"loro_{number:03d}" for number in range(1, 11))
logger = logging.getLogger(__name__)


def read_json(path: Path) -> dict:
    """Read a saved settings or run record."""
    return json.loads(path.read_text())


def write_json(path: Path, value: dict) -> None:
    """Publish one complete JSON control file atomically."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def key(row: dict) -> tuple[str, str, str]:
    """Return the original TIFF identity used by assignment joins."""
    return row["dataset_id"], row["release_id"], row["source_id"]


def matched_sources(rows: list[dict], experiment: str) -> set[tuple[str, str, str]]:
    """Select fold test TIFFs unseen in baseline training or validation, including companions."""
    baseline = [
        r for r in rows if (r["experiment"], r["variant"]) == ("baseline", "augmented")
    ]
    fold = [
        r for r in rows if (r["experiment"], r["variant"]) == (experiment, "augmented")
    ]
    validate_assignments(baseline)
    validate_loro_assignments(fold, experiment)
    if {key(r) for r in baseline} != {key(r) for r in fold}:
        raise ValueError(
            "Baseline and fold assignments must cover identical source identities."
        )
    used = [r for r in baseline if r["split"] in ("train", "val")]
    used_keys = {key(r) for r in used}
    used_days = {(r["satellite_id"], r["acquisition_date"]) for r in used}
    return {
        key(r)
        for r in fold
        if r["split"] == "test"
        and key(r) not in used_keys
        and (r["satellite_id"], r["acquisition_date"]) not in used_days
    }


def write_recipe(path: Path, settings: TrainingSettings) -> None:
    """Write a flat editable TOML recipe preserving the explicit loss configuration."""
    values = asdict(settings)
    losses = values.pop("losses")
    lines = []
    for name, value in values.items():
        lines.append(f"{name} = {json.dumps('none' if value is None else value)}")
    for loss in losses:
        lines.append("\n[[losses]]")
        for name, value in loss.items():
            if name == "parameters":
                value = (
                    "{ "
                    + ", ".join(f"{k} = {json.dumps(v)}" for k, v in value.items())
                    + " }"
                )
            else:
                value = json.dumps(value)
            lines.append(f"{name} = {value}")
    path.write_text("\n".join(lines) + "\n")


def stage_fold(
    output: Path,
    experiment: str,
    settings: TrainingSettings,
    paths: PathSettings,
    sources: list[dict],
    assignments: list[dict],
    cleaned: Path,
) -> dict:
    """Verify membership and stage a fold with unchanged baseline normalization."""
    output.mkdir()
    rows = [
        r
        for r in assignments
        if (r["experiment"], r["variant"]) == (experiment, "augmented")
    ]
    matched = matched_sources(assignments, experiment)
    heldout = {key(r) for r in rows if r["split"] == "test"}
    manifests, labels = [], []
    for source in sources:
        if key(source) not in heldout:
            continue
        manifest = dict(
            source_key=source["source_key"],
            image=str(cleaned / "images" / source["image"]),
            band_names=";".join(BAND_NAMES),
            dataset_id=source["dataset_id"],
            release_id=source["release_id"],
            region_id=source["region"],
            acquisition_date=source["acquisition_date"],
            original_source_id=source["source_id"],
            row_offset=source["row_offset"],
            col_offset=source["col_offset"],
        )
        manifests.append(manifest)
        label = cleaned / "labels" / source["label"]
        if not label.is_file():
            raise ValueError(f"Missing cleaned label: {label}")
        labels.append(
            dict(
                source_key=source["source_key"],
                label=str(label),
                source_id=source["source_id"],
            )
        )
    if {
        (r["dataset_id"], r["release_id"], r["original_source_id"]) for r in manifests
    } != heldout:
        raise ValueError(
            f"{experiment}: cleaned sources do not cover the held-out region."
        )
    paired = [
        r
        for r in manifests
        if (r["dataset_id"], r["release_id"], r["original_source_id"]) in matched
    ]
    if not paired:
        raise ValueError(f"{experiment}: no common unseen TIFFs.")
    write_csv(output / "full.csv", manifests)
    write_csv(output / "paired.csv", paired)
    write_csv(output / "labels.csv", labels)
    read_sources(
        PredictionSettings(
            model=output, manifest=output / "full.csv", image_root=output, output=output
        ),
        BAND_NAMES,
    )
    write_json(
        output / "normalization.json",
        dict(
            band_names=list(settings.band_names),
            mean=list(settings.mean),
            std=list(settings.std),
            clip_value=settings.clip_value,
            scope="Fixed baseline kelp-positive with-BC training statistics, unchanged by explicit user instruction; includes held-out-region imagery and is not fold-independent preprocessing.",
        ),
    )
    settings = replace(
        settings, name=f"planet8-cabc-b0-037c-{experiment}-70ep", experiment=experiment
    )
    write_recipe(output / "train.toml", settings)
    preview = run_training(load_settings(output / "train.toml"), paths, dry_run=True)
    write_json(output / "preview.json", preview)
    record = dict(
        experiment=experiment,
        full_sources=len(manifests),
        paired_sources=len(paired),
        unmatched_sources=len(manifests) - len(paired),
        bc_training_sources=sum(
            r["region"] in ("011", "012") and r["split"] == "train" for r in rows
        ),
        training_eligible=preview["counts"]["training_eligible"],
        **preview["budget"],
    )
    logger.info("Prepared %s: %s", experiment, record)
    return record


def verify_baseline(
    reference: Path, settings: TrainingSettings, paths: PathSettings
) -> dict:
    """Match the selected bundle and saved checkpoint memberships to current inputs."""
    import torch

    model = read_json(reference / "model/model.json")
    if (model["encoder"], model["experiment"], model["variant"]) != (
        "mit_b0",
        "baseline",
        "augmented",
    ):
        raise ValueError("Expected the selected augmented baseline B0 model.")
    checkpoint = torch.load(
        reference / "checkpoints/best.ckpt", map_location="cpu", weights_only=False
    )
    if checkpoint["epoch"] != model["checkpoint_epoch"]:
        raise ValueError("Baseline selected checkpoint epoch differs from the bundle.")
    inputs = build_training_inputs(
        paths.data_root / settings.chips,
        paths.data_root / settings.assignments,
        selection=settings.band_names,
        experiment="baseline",
        variant="augmented",
    )
    expected = build_resume_identity(settings, inputs)
    if (
        checkpoint["training_resume"]["identity"]["memberships"]
        != expected["memberships"]
    ):
        raise ValueError(
            "Baseline saved train/validation/test memberships differ from current assignments/chips."
        )
    return dict(
        checkpoint=str(reference / "checkpoints/best.ckpt"),
        checkpoint_epoch=checkpoint["epoch"],
        membership_check="exact saved/current window metadata equality",
        training_windows=len(inputs["train"]),
        validation_windows=len(inputs["val"]),
    )


def prepare(output: Path) -> None:
    """Prepare all ten folds once, without production training or held-out prediction."""
    if output.exists():
        raise ValueError(
            f"Output already exists: {output}. Choose a fresh suite directory."
        )
    settings = load_settings(ROOT / "configs/train/model_size/b0.toml")
    paths = check_paths(load_paths(settings.paths_file))
    reference = paths.data_root / "model-size-runs" / REFERENCE
    model = read_json(reference / "model/model.json")
    if (
        model["run_id"],
        model["checkpoint_epoch"],
        model["weight_kind"],
        model["threshold"],
        model["band_names"],
    ) != (REFERENCE, 15, "ema", 0.5, list(BAND_NAMES)):
        raise ValueError(
            "Expected the selected with-BC eight-band B0 epoch-16 EMA baseline."
        )
    baseline_run = read_json(reference / "run.json")
    expected = json.loads(json.dumps(asdict(settings)))
    if any(
        value != baseline_run["settings"][name]
        for name, value in expected.items()
        if name not in ("paths_file",)
    ):
        raise ValueError(
            "B0 recipe differs from the selected baseline's training settings."
        )
    assignments = read_csv(paths.data_root / settings.assignments)
    sources = read_json(paths.data_root / settings.chips / "sources.json")
    baseline_check = verify_baseline(reference, settings, paths)
    output.mkdir(parents=True)
    write_json(output / "baseline-check.json", baseline_check)
    records = [
        stage_fold(
            output / fold,
            fold,
            settings,
            paths,
            sources,
            assignments,
            paths.data_root / "data/3_cleaned/ca_bc/v1",
        )
        for fold in FOLDS
    ]
    write_csv(output / "fold-plan.csv", records)
    write_json(
        output / "suite.json",
        dict(
            status="prepared",
            baseline_model=str(reference / "model"),
            assignments=str(paths.data_root / settings.assignments),
            folds=list(FOLDS),
        ),
    )


def run_fold(output: Path, experiment: str, device: str = "cuda") -> None:
    """Train one prepared fold, infer full/paired scopes, and report before the next fold."""
    from kelpseg.reporting.loro import report_fold

    suite = read_json(output / "suite.json")
    fold = output / experiment
    settings = load_settings(fold / "train.toml")
    paths = check_paths(load_paths(settings.paths_file))
    preview = read_json(fold / "preview.json")
    run = run_training(settings, paths, run_id=preview["run_id"])
    for name, model, manifest in (
        ("loro", Path(run["model_bundle"]), "full"),
        ("baseline", Path(suite["baseline_model"]), "paired"),
    ):
        predict(
            PredictionSettings(
                model=model,
                manifest=fold / f"{manifest}.csv",
                image_root=fold,
                output=fold / f"{name}-predictions",
                device=device,
            )
        )
    report_fold(
        fold / "reports",
        fold / "loro-predictions",
        fold / "baseline-predictions",
        fold / "labels.csv",
        fold,
        {r["source_key"] for r in read_csv(fold / "paired.csv")},
        assignments=Path(suite["assignments"]),
        experiment=experiment,
    )


def summarize(output: Path) -> None:
    """Pool completed fold reports and record actual update counts and selections."""
    from kelpseg.reporting.loro_summary import summarize_suite

    suite = read_json(output / "suite.json")
    summarize_suite(
        [output / fold / "reports" for fold in suite["folds"]], output / "summary"
    )
    records = []
    for fold in suite["folds"]:
        preview = read_json(output / fold / "preview.json")
        run = read_json(Path(preview["output"]) / "run.json")
        model = read_json(Path(run["model_bundle"]) / "model.json")
        records.append(
            dict(
                experiment=fold,
                run_id=run["run_id"],
                model=run["model_bundle"],
                eligible_windows=run["counts"]["training_eligible"],
                planned_updates=run["budget"]["optimizer_updates_total"],
                actual_updates=run["optimizer_updates_actual"],
                selected_epoch=model["checkpoint_epoch"] + 1,
                weight_kind=model["weight_kind"],
            )
        )
    write_csv(output / "summary/training.csv", records)


def main() -> None:
    """Execute one explicit stage; any failure stops the shell launcher."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "summary", "smoke", *FOLDS))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    try:
        output = args.output.resolve()
        if args.stage == "prepare":
            prepare(output)
        elif args.stage == "summary":
            summarize(output)
        elif args.stage == "smoke":
            from task037c_smoke import smoke

            smoke(output)
        else:
            run_fold(output, args.stage)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        parser.exit(1, f"Task 037C {args.stage} failed: {error}\n")


if __name__ == "__main__":
    main()
