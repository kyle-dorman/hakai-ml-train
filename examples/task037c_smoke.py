"""Tiny synthetic Task 037C rehearsal with a real B0 update and copied models."""

import json
import shutil
from dataclasses import replace
from pathlib import Path

import numpy as np
import rasterio
import torch
from rasterio.transform import from_origin
from task037c import ROOT, read_json, stage_fold, write_json

from kelpseg.paths import PathSettings
from kelpseg.prediction.predict import predict
from kelpseg.prediction.settings import PredictionSettings
from kelpseg.preprocessing import BAND_NAMES
from kelpseg.reporting.inputs import read_csv
from kelpseg.reporting.loro import report_fold
from kelpseg.reporting.loro_summary import summarize_suite
from kelpseg.reporting.report import write_csv
from kelpseg.training.run import run_training
from kelpseg.training.settings import load_settings


def make_fixture(output: Path) -> tuple[PathSettings, list[dict], list[dict]]:
    """Write tiny georeferenced imagery, labels, chips and scientifically isolated assignments."""
    chips = output / "chips"
    chips.mkdir()
    cleaned = output / "cleaned"
    (cleaned / "images").mkdir(parents=True)
    (cleaned / "labels").mkdir()
    (output / "runs").mkdir()
    paths_file = output / "paths.toml"
    paths_file.write_text(
        f"[paths]\ndata_root = {json.dumps(str(output))}\nruns_root = {json.dumps(str(output / 'runs'))}\n"
    )
    sources, windows, assignments = [], [], []
    for index, (region, split) in enumerate(
        (
            ("011", "train"),
            ("012", "train"),
            ("002", "val"),
            ("001", "test"),
            ("001", "test"),
            ("001", "test"),
        )
    ):
        name = f"smoke-{index}"
        day = (1, 2, 3, 4, 10, 15)[index]
        source = dict(
            source_key=name,
            source_id=name,
            original_tiff=f"{name}.tif",
            image=f"{name}.tif",
            label=f"{name}.tif",
            dataset_id="smoke",
            release_id="v1",
            region=region,
            acquisition_date=f"2020-01-{day:02d}",
            satellite_id="fixture",
            row_offset=0,
            col_offset=0,
            height=32,
            width=32,
        )
        sources.append(source)
        image = np.random.default_rng(index).integers(
            100, 7000, (32, 32, 8), dtype=np.uint16
        )
        image[:2] = 0
        label = np.zeros((32, 32), dtype=np.uint8)
        label[8 : 16 + index, 8:24] = 1
        label[:2] = 3
        profile = dict(
            driver="GTiff",
            height=32,
            width=32,
            crs="EPSG:32610",
            transform=from_origin(500000, 5500000, 3, 3),
        )
        with rasterio.open(
            cleaned / "images" / f"{name}.tif",
            "w",
            **profile,
            count=8,
            dtype="uint16",
            nodata=0,
        ) as raster:
            raster.write(image.transpose(2, 0, 1))
        with rasterio.open(
            cleaned / "labels" / f"{name}.tif",
            "w",
            **profile,
            count=1,
            dtype="uint8",
            nodata=3,
        ) as raster:
            raster.write(label, 1)
        target = label.astype(np.int8)
        target[label == 3] = -100
        np.savez(chips / f"{name}.npz", image=image, label=target)
        windows.append(
            dict(
                source_key=name,
                row=0,
                col=0,
                original_row=0,
                original_col=0,
                height=32,
                width=32,
                kelp_pixels=int((label == 1).sum()),
                disposition="retained",
                payload=f"{name}.npz",
            )
        )
        assignments.append(
            dict(
                source,
                experiment="loro_001",
                variant="augmented",
                split=split,
                reason="tiny fold",
            )
        )
        assignments.append(
            dict(
                source,
                experiment="baseline",
                variant="augmented",
                split="train" if index == 5 else split,
                reason="synthetic baseline membership for exclusion check",
            )
        )
    write_json(chips / "recipe.json", dict(source_band_names=BAND_NAMES, chip_size=512))
    write_json(chips / "sources.json", sources)
    write_csv(chips / "windows.csv", windows)
    write_csv(output / "assignments.csv", assignments)
    return PathSettings(paths_file, output, output / "runs"), sources, assignments


def smoke(output: Path) -> None:
    """Exercise fixed normalization, one B0 update, copied inference and matched reports."""
    if output.exists():
        raise ValueError(f"Output already exists: {output}")
    output.mkdir(parents=True)
    torch.set_num_threads(2)
    paths, sources, assignments = make_fixture(output)
    settings = replace(
        load_settings(ROOT / "configs/train/model_size/b0.toml"),
        paths_file=str(paths.settings_file),
        chips="chips",
        assignments="assignments.csv",
        epochs=1,
        warmup_epochs=0,
        checkpoint_epochs=(),
        batch_size=1,
        accumulate_grad_batches=1,
        accelerator="cpu",
        precision="32-true",
        num_workers=0,
        persistent_workers=False,
        pin_memory=False,
        encoder_weights=None,
        wandb=False,
        limit_train_batches=1,
        limit_val_batches=1,
    )
    fold = output / "loro_001"
    stage_fold(
        fold, "loro_001", settings, paths, sources, assignments, output / "cleaned"
    )
    settings = load_settings(fold / "train.toml")
    run = run_training(settings, paths, run_id="tiny-fold")
    copied = output / "copied-model"
    shutil.copytree(run["model_bundle"], copied)
    # Identical fixture weights isolate reporting/membership mechanics; this is
    # a pipeline check, never a scientific baseline-versus-LORO comparison.
    for name, manifest in (("loro", "full"), ("baseline", "paired")):
        predict(
            PredictionSettings(
                model=copied,
                manifest=fold / f"{manifest}.csv",
                image_root=fold,
                output=fold / f"{name}-predictions",
                device="cpu",
            )
        )
    matched = {row["source_key"] for row in read_csv(fold / "paired.csv")}
    assert matched == {"smoke-3", "smoke-4"}
    report_fold(
        fold / "reports",
        fold / "loro-predictions",
        fold / "baseline-predictions",
        fold / "labels.csv",
        fold,
        matched,
        assignments=output / "assignments.csv",
        experiment="loro_001",
    )
    summarize_suite([fold / "reports"], output / "summary")
    metadata = read_json(copied / "model.json")
    stats = read_json(fold / "normalization.json")
    assert metadata["mean"] == stats["mean"] and metadata["std"] == stats["std"]
    assert run["optimizer_updates_actual"] == 1
    write_json(
        output / "smoke.json",
        dict(
            status="complete",
            optimizer_updates=1,
            full_sources=3,
            paired_sources=2,
            excluded_source="smoke-5",
            copied_bundle=str(copied),
            note="Synthetic pipeline check uses the same copied model in both reporting arms; no scientific comparison claimed.",
        ),
    )
