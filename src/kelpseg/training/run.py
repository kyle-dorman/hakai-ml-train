"""Resolve one baseline run and hand fitting to Lightning's native Trainer."""

import csv
import json
import math
import platform
import re
import subprocess
from dataclasses import asdict, replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import torch
from lightning.pytorch import Trainer, seed_everything
from lightning.pytorch.callbacks import (
    EarlyStopping,
    LearningRateMonitor,
    ModelCheckpoint,
)
from lightning.pytorch.loggers import CSVLogger, WandbLogger
from torch.utils.data import DataLoader, default_collate

from kelpseg.augmentation_pipeline import build_training_augmentation
from kelpseg.model_bundle import export_model_bundle
from kelpseg.paths import PathSettings
from kelpseg.training.data import build_training_inputs
from kelpseg.training.ema import DelayedEMA
from kelpseg.training.module import TrainingModule
from kelpseg.training.resume import TrainingResume, build_resume_identity, load_resume
from kelpseg.training.settings import TrainingSettings


def collate_chips(samples):
    """Stack tensors and keep original source/window metadata as ordinary rows."""
    return {
        "image": default_collate([sample["image"] for sample in samples]),
        "target": default_collate([sample["target"] for sample in samples]),
        "valid_mask": default_collate([sample["valid_mask"] for sample in samples]),
        "metadata": [sample["metadata"] for sample in samples],
    }


def seed_worker(worker_id):
    """Give each worker's Albumentations pipeline its own seeded random stream."""
    worker = torch.utils.data.get_worker_info()
    worker.dataset.transform.set_random_seed(torch.initial_seed() % (2**32))


def _limited_batches(available, limit):
    count = min(available, limit) if type(limit) is int else int(available * limit)
    if count < 1:
        raise ValueError(
            "Batch limit selects no batches; increase the fraction or use an integer."
        )
    return count


def _write_json(path, values):
    path.write_text(json.dumps(values, indent=2, default=str) + "\n", encoding="utf-8")


def _git_commit():
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def run_training(
    settings: TrainingSettings,
    paths: PathSettings,
    *,
    run_id: str | None = None,
    dry_run: bool = False,
    resume: str | Path | None = None,
) -> dict:
    """Preview, start fresh, or resume a completed epoch; never construct test data."""
    chips = (paths.data_root / settings.chips).resolve()
    assignments = (paths.data_root / settings.assignments).resolve()
    inputs = build_training_inputs(
        chips,
        assignments,
        selection=settings.band_names,
        experiment=settings.experiment,
        variant=settings.variant,
        seed=settings.seed,
    )
    identity = build_resume_identity(settings, inputs)
    if resume is not None:
        resume = Path(resume).expanduser().resolve()
        saved = load_resume(resume, identity)
        if run_id is not None and run_id != saved["run_id"]:
            raise ValueError(
                "Resume preserves the saved run ID; do not supply another."
            )
        run_id = saved["run_id"]
    if run_id is None:
        run_id = f"{settings.name}-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        raise ValueError(
            "run-id must be a simple name using letters, digits, '.', '_' or '-'."
        )
    output = paths.runs_root / run_id
    if output.exists() and resume is None:
        raise ValueError(
            f"Run output already exists: {output}. Start a new run with a fresh name."
        )
    if resume is not None and resume != output / "checkpoints" / "last.ckpt":
        raise ValueError(
            "Resume from <runs_root>/<saved-run-id>/checkpoints/last.ckpt; copy the complete run folder when relocating."
        )
    if resume is not None and (output / "model").exists():
        raise ValueError(
            "This run already exported model/. Resume is for interrupted training only."
        )
    if not len(inputs["val"]):
        raise ValueError("No validation windows; check the collection and assignments.")
    if inputs["train"].chip_size != 512:
        raise ValueError("Training recipes require a 512-pixel chip canvas.")
    train_batches = math.ceil(len(inputs["train"]) / settings.batch_size)
    val_batches = math.ceil(len(inputs["val"]) / settings.batch_size)
    train_batches = _limited_batches(train_batches, settings.limit_train_batches)
    val_batches = _limited_batches(val_batches, settings.limit_val_batches)
    updates = math.ceil(train_batches / settings.accumulate_grad_batches)
    # Canonical windows counts every manifest candidate, including omissions.
    canonical_windows = canonical_retained_payloads = 0
    with (chips / "windows.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            canonical_windows += 1
            canonical_retained_payloads += bool(row["payload"])
    sources = json.loads((chips / "sources.json").read_text())
    train_rows = inputs["train"].rows
    val_rows = inputs["val"].rows
    report = {
        "run_id": run_id,
        "output": str(output),
        "status": "preview",
        "name": settings.name,
        "experiment": settings.experiment,
        "variant": settings.variant,
        "chips": str(chips),
        "assignments": str(assignments),
        "settings": asdict(settings),
        "counts": {
            **inputs["counts"],
            "canonical_windows": canonical_windows,
            "canonical_retained_payloads": canonical_retained_payloads,
            "canonical_sources": len(sources),
            "assigned_training_sources": len(
                {r["source_key"] for r in train_rows + inputs["excluded_training_rows"]}
            ),
            "eligible_training_sources": len({r["source_key"] for r in train_rows}),
            "validation_sources": len({r["source_key"] for r in val_rows}),
        },
        "regions": sorted({r["region"] for r in train_rows}),
        "releases": sorted({(r["dataset_id"], r["release_id"]) for r in train_rows}),
        "held_out_region": None,
        "adaptation_case": None,
        "augmentation": build_training_augmentation(settings.seed).to_dict(),
        "normalization_scope": "kelp-positive with-BC training, capped at 5000",
        "model": "SegFormer B3 / mit_b3",
        "selection": "maximum pooled validation foreground IoU, earliest ties, threshold 0.5",
        "validation_weights": "current before optimizer update 101; EMA thereafter",
        "ema": {"decay": 0.999, "first_optimizer_update": 101},
        "loss": {
            "reduction": "weighted_sum",
            "terms": [asdict(term) for term in settings.losses],
        },
        "budget": {
            "epochs": settings.epochs,
            "training_batches_per_epoch": train_batches,
            "validation_batches_per_epoch": val_batches,
            "optimizer_updates_per_epoch": updates,
            "optimizer_updates_total": updates * settings.epochs,
            "effective_batch": settings.batch_size * settings.accumulate_grad_batches,
            "final_accumulation_microbatches": (train_batches - 1)
            % settings.accumulate_grad_batches
            + 1,
            "partial_accumulation": "Lightning steps the final partial group; loss remains divided by the configured accumulation count",
        },
        "git_commit": _git_commit(),
        "runtime": {name: version(name) for name in ("torch", "lightning", "kelpseg")},
        "python": platform.python_version(),
        "deterministic_algorithms": settings.deterministic,
        "resume_randomness": (
            "worker augmentation streams restart; sample order may differ"
            if settings.num_workers
            else "main-process and augmentation random states restored"
        ),
    }
    if dry_run:
        return report
    seed_everything(settings.seed, workers=True)
    output.mkdir(parents=True, exist_ok=resume is not None)
    report["status"] = "running"
    _write_json(output / "settings.json", asdict(settings))
    _write_json(output / "run.json", report)
    loader_options = dict(
        batch_size=settings.batch_size,
        num_workers=settings.num_workers,
        pin_memory=settings.pin_memory,
        persistent_workers=settings.persistent_workers,
        collate_fn=collate_chips,
        worker_init_fn=seed_worker,
    )
    train_loader = DataLoader(
        inputs["train"],
        shuffle=True,
        generator=torch.Generator().manual_seed(settings.seed),
        **loader_options,
    )
    val_loader = DataLoader(
        inputs["val"],
        shuffle=False,
        generator=torch.Generator().manual_seed(settings.seed + 1),
        **loader_options,
    )
    checkpoint = ModelCheckpoint(
        dirpath=output / "checkpoints",
        filename="best",
        monitor="val/iou",
        mode="max",
        save_top_k=1,
        save_last=False,
        save_on_train_epoch_end=False,
        enable_version_counter=False,
    )
    last_checkpoint = ModelCheckpoint(
        dirpath=output / "checkpoints",
        filename="last",
        monitor=None,
        save_top_k=1,
        save_last=False,
        save_on_train_epoch_end=True,
        enable_version_counter=False,
    )
    metric_version = (
        f"resume-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}" if resume is not None else ""
    )
    loggers = [CSVLogger(str(output), name="metrics", version=metric_version)]
    if settings.wandb:
        loggers.append(
            WandbLogger(
                project="kelpseg",
                entity="kdorman90-ucla",
                name=run_id,
                id=run_id,
                resume="must" if resume is not None else "never",
                save_dir=str(output),
                log_model=False,
            )
        )
    try:
        model = TrainingModule(
            replace(settings, encoder_weights=None) if resume is not None else settings
        )
        model.configure_diagnostics(inputs["val"].rows)
        callbacks = [
            DelayedEMA(),
            TrainingResume(run_id, identity, train_loader, val_loader),
            LearningRateMonitor(logging_interval="step"),
            checkpoint,
            last_checkpoint,
        ]
        early_stopping = None
        if settings.early_stopping_patience:
            early_stopping = EarlyStopping(
                monitor="val/iou",
                mode="max",
                patience=settings.early_stopping_patience,
                min_delta=settings.early_stopping_min_delta,
                check_on_train_epoch_end=False,
            )
            callbacks.append(early_stopping)
        trainer = Trainer(
            default_root_dir=output,
            accelerator=settings.accelerator,
            devices=1,
            precision=settings.precision,
            # Strict replay costs GPU throughput; the recipe makes that choice.
            deterministic=settings.deterministic,
            max_epochs=settings.epochs,
            accumulate_grad_batches=settings.accumulate_grad_batches,
            gradient_clip_val=settings.gradient_clip_val,
            gradient_clip_algorithm="norm",
            callbacks=callbacks,
            logger=loggers,
            num_sanity_val_steps=0,
            check_val_every_n_epoch=1,
            limit_train_batches=settings.limit_train_batches,
            limit_val_batches=settings.limit_val_batches,
            log_every_n_steps=1,
            enable_model_summary=False,
        )
        trainer.fit(
            model,
            train_dataloaders=train_loader,
            val_dataloaders=val_loader,
            ckpt_path=resume,
            weights_only=False,
        )
        bundle = export_model_bundle(
            checkpoint.best_model_path, output / "model", settings, run_id=run_id
        )
        report.update(
            status="complete",
            stopped_early=early_stopping is not None
            and early_stopping.stopped_epoch > 0,
            model_bundle=str(bundle),
            optimizer_updates_actual=trainer.global_step,
            best_checkpoint=checkpoint.best_model_path,
            last_checkpoint=last_checkpoint.best_model_path,
            best_validation_iou=float(checkpoint.best_model_score)
            if checkpoint.best_model_score is not None
            else None,
            validation_csv=str(Path(loggers[0].log_dir) / "metrics.csv"),
        )
    except Exception as error:
        report.update(status="failed", error=str(error))
        _write_json(output / "run.json", report)
        raise
    _write_json(output / "run.json", report)
    return report
