#!/usr/bin/env python3
"""Evaluate one recorded PlanetScope v3 checkpoint on unique source pixels."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import albumentations as A
import numpy as np
import rasterio
import torch
import yaml
from rasterio import Affine

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.planet8b import (
    EVALUATION_SCHEMA_VERSION,
    SourceAccumulator,
    binary_metrics,
    sum_confusion,
)
from src.models.smp import SMPBinarySegmentationModel
from src.run_context import sha256_file

METRIC_FIELDS = [
    "true_negative",
    "false_positive",
    "false_negative",
    "true_positive",
    "ignored_pixel_count",
    "uncovered_pixel_count",
    "covered_pixel_count",
    "scored_pixel_count",
    "total_source_pixel_count",
    "accuracy",
    "kelp_precision",
    "kelp_recall",
    "kelp_f1",
    "kelp_iou",
    "background_iou",
    "macro_iou",
    "dice",
]


class EvaluatorError(RuntimeError):
    """Raised when evaluator inputs or durable output identity are unsafe."""


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise EvaluatorError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _atomic_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _identity_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _latest_completed_run(registry: Path, run_key: str) -> dict[str, Any]:
    events = [json.loads(line) for line in registry.read_text().splitlines() if line]
    matches = [event for event in events if event.get("run_key") == run_key]
    if not matches or matches[-1].get("status") != "completed":
        raise EvaluatorError(f"Run {run_key} is not currently completed in {registry}")
    event = matches[-1]
    for key in (
        "checkpoint_path",
        "checkpoint_sha256",
        "fold_manifest_path",
        "fold_manifest_sha256",
    ):
        if not event.get(key):
            raise EvaluatorError(f"Completed run {run_key} is missing {key}")
    checkpoint = Path(event["checkpoint_path"])
    if (
        not checkpoint.is_file()
        or sha256_file(checkpoint) != event["checkpoint_sha256"]
    ):
        raise EvaluatorError(f"Checkpoint identity failed for {run_key}")
    return event


def _model_predictor(
    checkpoint: Path, config: Path, device: str
) -> Callable[[np.ndarray, np.ndarray], np.ndarray]:
    """Return a predictor that applies the recorded deterministic test transform."""
    config_value = yaml.safe_load(config.read_text())
    transform = A.from_dict(config_value["data"]["init_args"]["test_transforms"])
    model = SMPBinarySegmentationModel.load_from_checkpoint(
        str(checkpoint), map_location=device
    )
    model.eval().to(device)

    def predict(image: np.ndarray, label: np.ndarray) -> np.ndarray:
        augmented = transform(image=image, mask=label)
        tensor = augmented["image"].unsqueeze(0).to(device)
        with torch.inference_mode():
            logits = model(tensor)
            probability = torch.sigmoid(logits).squeeze().float().cpu().numpy()
        return probability[: image.shape[0], : image.shape[1]]

    return predict


def _write_rasters(
    root: Path,
    source: str,
    probability: np.ndarray,
    mask: np.ndarray,
    covered: np.ndarray,
    metadata: dict[str, str],
) -> tuple[Path, Path]:
    destination = root / "source_predictions"
    destination.mkdir(parents=True, exist_ok=True)
    transform = Affine(*(float(metadata[f"transform_{key}"]) for key in "abcdef"))
    profile: dict[str, Any] = {
        "driver": "GTiff",
        "height": probability.shape[0],
        "width": probability.shape[1],
        "count": 1,
        "crs": metadata["crs"],
        "transform": transform,
        "compress": "lzw",
        "BIGTIFF": "IF_SAFER",
    }
    if min(probability.shape) >= 16:
        profile.update(
            tiled=True,
            blockxsize=256 if probability.shape[1] >= 256 else 16,
            blockysize=256 if probability.shape[0] >= 256 else 16,
        )
    probability_path = destination / f"{source}_probability.tif"
    mask_path = destination / f"{source}_mask.tif"
    raster_probability = probability.copy()
    raster_probability[~covered] = np.nan
    with rasterio.open(
        probability_path, "w", dtype="float32", nodata=np.nan, **profile
    ) as output:
        output.write(raster_probability, 1)
    raster_mask = mask.copy()
    raster_mask[~covered] = 255
    with rasterio.open(mask_path, "w", dtype="uint8", nodata=255, **profile) as output:
        output.write(raster_mask, 1)
    return probability_path, mask_path


def evaluate(
    *,
    dataset_root: Path,
    fold_manifest: Path,
    chip_manifest: Path,
    raster_metadata: Path,
    output_root: Path,
    run_identity: dict[str, Any],
    threshold: float,
    predictor: Callable[[np.ndarray, np.ndarray], np.ndarray],
    save_rasters: bool,
    resume: bool,
) -> list[dict[str, Any]]:
    """Evaluate all selected test chips. ``predictor`` makes this function testable."""
    if not 0 <= threshold <= 1:
        raise EvaluatorError("threshold must be in [0, 1]")
    folds = _read_csv(
        fold_manifest,
        {
            "chip_id",
            "source_tiff_id",
            "region_id",
            "acquisition_date",
            "experiment_split",
            "selected",
        },
    )
    chips = _read_csv(
        chip_manifest,
        {
            "chip_id",
            "chip_path",
            "source_tiff_id",
            "row_off",
            "col_off",
            "chip_width",
            "chip_height",
        },
    )
    metadata_rows = _read_csv(
        raster_metadata,
        {
            "source_tiff_id",
            "width",
            "height",
            "crs",
            *(f"transform_{key}" for key in "abcdef"),
        },
    )
    chip_by_id = {row["chip_id"]: row for row in chips}
    if len(chip_by_id) != len(chips):
        raise EvaluatorError("Canonical chip manifest contains duplicate chip IDs")
    metadata = {row["source_tiff_id"]: row for row in metadata_rows}
    selected = [
        row
        for row in folds
        if row["experiment_split"] == "test" and row["selected"].lower() == "true"
    ]
    if not selected:
        raise EvaluatorError("Fold manifest has no selected test chips")
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for fold in selected:
        chip = chip_by_id.get(fold["chip_id"])
        if chip is None or chip["source_tiff_id"] != fold["source_tiff_id"]:
            raise EvaluatorError(f"Fold chip identity failed for {fold['chip_id']}")
        groups[fold["source_tiff_id"]].append(fold)
    identity = {
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "threshold": threshold,
        **run_identity,
    }
    identity["evaluation_identity_sha256"] = _identity_hash(identity)
    output_root.mkdir(parents=True, exist_ok=True)
    existing_metadata = output_root / "evaluation_metadata.json"
    if existing_metadata.is_file():
        existing = json.loads(existing_metadata.read_text())
        if existing.get("evaluation_identity_sha256") == identity[
            "evaluation_identity_sha256"
        ] and existing.get("prediction_wandb_run_id"):
            identity["prediction_wandb_run_id"] = existing["prediction_wandb_run_id"]
    _atomic_json(output_root / "evaluation_metadata.json", identity)
    result: list[dict[str, Any]] = []
    for source, rows in sorted(groups.items()):
        completion = output_root / "source_predictions" / f"{source}.completion.json"
        if resume and completion.is_file():
            saved = json.loads(completion.read_text())
            if (
                saved.get("evaluation_identity_sha256")
                == identity["evaluation_identity_sha256"]
            ):
                metrics = saved["metrics"]
                raster_paths = (
                    metrics.get("probability_raster"),
                    metrics.get("mask_raster"),
                )
                if not save_rasters or all(
                    path and Path(path).is_file() for path in raster_paths
                ):
                    result.append(metrics)
                    continue
        source_metadata = metadata.get(source)
        if source_metadata is None:
            raise EvaluatorError(f"Missing raster metadata for {source}")
        accumulator = SourceAccumulator(
            int(source_metadata["height"]), int(source_metadata["width"])
        )
        chip_diagnostics: list[dict[str, Any]] = []
        for fold in rows:
            chip = chip_by_id[fold["chip_id"]]
            archive = np.load(dataset_root / chip["chip_path"])
            image, label = archive["image"], archive["label"]
            probability = predictor(image, label)
            height, width = int(chip["chip_height"]), int(chip["chip_width"])
            probability, label = probability[:height, :width], label[:height, :width]
            accumulator.add(
                probability,
                label,
                row_off=int(chip["row_off"]),
                col_off=int(chip["col_off"]),
            )
            covered = np.ones(label.shape, dtype=bool)
            chip_diagnostics.append(
                {
                    "chip_id": chip["chip_id"],
                    "source_tiff_id": source,
                    "diagnostic_only_non_additive": True,
                    **run_identity,
                    **binary_metrics(
                        label, (probability >= threshold).astype(np.uint8), covered
                    ),
                }
            )
        probability, mask, covered = accumulator.finalize(threshold)
        metrics: dict[str, Any] = {
            "source_tiff_id": source,
            "region_id": rows[0]["region_id"],
            "acquisition_date": rows[0]["acquisition_date"],
            **run_identity,
            **binary_metrics(accumulator.label, mask, covered),
        }
        if save_rasters:
            probability_path, mask_path = _write_rasters(
                output_root, source, probability, mask, covered, source_metadata
            )
            metrics.update(
                probability_raster=str(probability_path), mask_raster=str(mask_path)
            )
        _atomic_json(
            completion,
            {
                "evaluation_identity_sha256": identity["evaluation_identity_sha256"],
                "metrics": metrics,
                "chip_diagnostics": chip_diagnostics,
            },
        )
        result.append(metrics)
    tiff_fields = list(result[0])
    _atomic_csv(output_root / "tiff_metrics.csv", result, tiff_fields)
    diagnostics: list[dict[str, Any]] = []
    for completion in sorted(
        (output_root / "source_predictions").glob("*.completion.json")
    ):
        saved = json.loads(completion.read_text())
        if (
            saved.get("evaluation_identity_sha256")
            == identity["evaluation_identity_sha256"]
        ):
            diagnostics.extend(saved["chip_diagnostics"])
    _atomic_csv(output_root / "chip_diagnostics.csv", diagnostics, list(diagnostics[0]))
    regions: list[dict[str, Any]] = []
    for region in sorted({row["region_id"] for row in result}):
        grouped = [row for row in result if row["region_id"] == region]
        regions.append(
            {
                "region_id": region,
                **run_identity,
                **sum_confusion(grouped),
                "source_tiff_count": len(grouped),
            }
        )
    _atomic_csv(output_root / "region_metrics.csv", regions, list(regions[0]))
    _atomic_json(
        output_root / "test_summary.json",
        {
            **identity,
            **sum_confusion(result),
            "test_tiff_count": len(result),
            "test_chip_count": len(selected),
        },
    )
    return result


def log_wandb_artifact(
    output_root: Path, identity: dict[str, Any], mode: str
) -> str | None:
    """Log compact evaluation evidence, never the full raster collection, to W&B."""
    if mode == "disabled":
        return None
    import wandb

    run = wandb.init(
        entity="kdorman90-ucla",
        project="kelpseg",
        group=identity["experiment_version"],
        name=f"{identity['run_key']}-prediction",
        job_type="prediction",
        tags=[identity["experiment_version"], "prediction", identity["fold_id"]],
        config=identity,
        mode=mode,
    )
    artifact = wandb.Artifact(
        name=f"{identity['run_key']}-prediction-results",
        type="planet8b-prediction-results",
        metadata=identity,
    )
    for name in (
        "evaluation_metadata.json",
        "chip_diagnostics.csv",
        "tiff_metrics.csv",
        "region_metrics.csv",
        "test_summary.json",
    ):
        artifact.add_file(str(output_root / name), name=name)
    probability = sorted((output_root / "source_predictions").glob("*_probability.tif"))
    mask = sorted((output_root / "source_predictions").glob("*_mask.tif"))
    if probability and mask:
        artifact.add_file(str(probability[0]), name=f"qa/{probability[0].name}")
        artifact.add_file(str(mask[0]), name=f"qa/{mask[0].name}")
    run.log_artifact(artifact)
    run.finish()
    return run.id


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-key", required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--fold-manifest", type=Path, required=True)
    parser.add_argument("--chip-manifest", type=Path, required=True)
    parser.add_argument("--raster-metadata", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--threshold", type=float, required=True)
    parser.add_argument("--save-rasters", action="store_true", default=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--wandb-mode", choices=("online", "offline", "disabled"), default="online"
    )
    parser.add_argument(
        "--device", default="cuda" if torch.cuda.is_available() else "cpu"
    )
    args = parser.parse_args()
    log_path = args.output_root / "logs" / "evaluation.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_path)],
    )
    event = _latest_completed_run(args.registry, args.run_key)
    if sha256_file(args.fold_manifest) != event["fold_manifest_sha256"]:
        raise EvaluatorError("Explicit fold manifest does not match registry identity")
    logging.info("validated registry/checkpoint/fold identity for %s", args.run_key)
    predictor = _model_predictor(
        Path(event["checkpoint_path"]), args.model_config, args.device
    )
    identity = {
        key: event.get(key)
        for key in (
            "experiment_version",
            "run_key",
            "wandb_run_id",
            "fold_id",
            "held_out_region",
            "checkpoint_sha256",
            "fold_manifest_sha256",
        )
    }
    evaluate(
        dataset_root=args.dataset_root,
        fold_manifest=args.fold_manifest,
        chip_manifest=args.chip_manifest,
        raster_metadata=args.raster_metadata,
        output_root=args.output_root,
        threshold=args.threshold,
        predictor=predictor,
        save_rasters=args.save_rasters,
        resume=args.resume,
        run_identity=identity,
    )
    prediction_wandb_run_id = log_wandb_artifact(
        args.output_root, identity, args.wandb_mode
    )
    if prediction_wandb_run_id:
        metadata_path = args.output_root / "evaluation_metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["prediction_wandb_run_id"] = prediction_wandb_run_id
        _atomic_json(metadata_path, metadata)
    logging.info("completed evaluation for %s", args.run_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
