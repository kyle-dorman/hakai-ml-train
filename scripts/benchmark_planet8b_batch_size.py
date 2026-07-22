#!/usr/bin/env python3
"""Benchmark constant-effective-batch PS8B training candidates on one GPU."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import lightning.pytorch as pl
import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CANDIDATES = ((3, 8), (4, 6), (6, 4), (8, 3), (12, 2), (24, 1))
EFFECTIVE_BATCH_SIZE = 24
torch.set_float32_matmul_precision("medium")


def _class(path: str) -> type:
    module, name = path.rsplit(".", 1)
    return getattr(importlib.import_module(module), name)


class BenchmarkTimer(pl.Callback):
    """Measure optimizer-step wall time after a fixed warmup."""

    def __init__(self, warmup_updates: int, measured_updates: int) -> None:
        self.warmup_updates = warmup_updates
        self.measured_updates = measured_updates
        self.started_at: float | None = None
        self.elapsed_seconds: float | None = None

    def on_train_batch_start(self, trainer, pl_module, batch, batch_idx) -> None:
        del pl_module, batch, batch_idx
        if trainer.global_step == self.warmup_updates and self.started_at is None:
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            self.started_at = time.perf_counter()

    def on_train_end(self, trainer, pl_module) -> None:
        del trainer, pl_module
        torch.cuda.synchronize()
        if self.started_at is not None:
            self.elapsed_seconds = time.perf_counter() - self.started_at


def worker(config_path: Path, micro_batch: int, accumulation: int) -> dict[str, Any]:
    if micro_batch * accumulation != EFFECTIVE_BATCH_SIZE:
        raise ValueError("candidate does not preserve effective batch size 24")
    config = yaml.safe_load(config_path.read_text())
    data_args = dict(config["data"]["init_args"])
    data_args["batch_size"] = micro_batch
    data = _class(config["data"]["class_path"])(**data_args)
    model = _class(config["model"]["class_path"])(**config["model"]["init_args"])
    timer = BenchmarkTimer(warmup_updates=1, measured_updates=3)
    ema = _class("src.callbacks.EMAWeightAveraging")()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    trainer = pl.Trainer(
        accelerator="gpu",
        devices=1,
        precision=config["trainer"]["precision"],
        max_steps=4,
        max_epochs=100,
        accumulate_grad_batches=accumulation,
        gradient_clip_val=config["trainer"]["gradient_clip_val"],
        callbacks=[ema, timer],
        logger=False,
        enable_checkpointing=False,
        enable_model_summary=False,
        enable_progress_bar=False,
        num_sanity_val_steps=0,
        limit_val_batches=0,
    )
    trainer.fit(model, datamodule=data)
    if timer.elapsed_seconds is None:
        raise RuntimeError("benchmark timer did not start")
    device = torch.cuda.current_device()
    total = torch.cuda.get_device_properties(device).total_memory
    allocated = torch.cuda.max_memory_allocated(device)
    reserved = torch.cuda.max_memory_reserved(device)
    measured_samples = timer.measured_updates * EFFECTIVE_BATCH_SIZE
    return {
        "status": "ok",
        "micro_batch_size": micro_batch,
        "accumulate_grad_batches": accumulation,
        "effective_batch_size": EFFECTIVE_BATCH_SIZE,
        "warmup_optimizer_updates": timer.warmup_updates,
        "measured_optimizer_updates": timer.measured_updates,
        "measured_samples": measured_samples,
        "elapsed_seconds": timer.elapsed_seconds,
        "samples_per_second": measured_samples / timer.elapsed_seconds,
        "optimizer_step_seconds": timer.elapsed_seconds / timer.measured_updates,
        "peak_allocated_bytes": allocated,
        "peak_reserved_bytes": reserved,
        "device_total_bytes": total,
        "reserved_headroom_fraction": 1.0 - (reserved / total),
    }


def orchestrate(config_path: Path, output: Path) -> int:
    results: list[dict[str, Any]] = []
    for micro_batch, accumulation in CANDIDATES:
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--config",
            str(config_path.resolve()),
            "--worker",
            str(micro_batch),
            str(accumulation),
        ]
        with tempfile.TemporaryDirectory(prefix="planet8b-batch-benchmark-") as temp:
            completed = subprocess.run(
                command,
                cwd=temp,
                text=True,
                capture_output=True,
                check=False,
            )
        if completed.returncode:
            try:
                result = json.loads(completed.stdout.strip().splitlines()[-1])
            except (IndexError, json.JSONDecodeError):
                result = {"status": "failed"}
            result.update(
                micro_batch_size=micro_batch,
                accumulate_grad_batches=accumulation,
                effective_batch_size=EFFECTIVE_BATCH_SIZE,
                returncode=completed.returncode,
            )
            if result["status"] != "oom":
                result["error"] = completed.stderr.strip()[-4000:]
        else:
            result = json.loads(completed.stdout.strip().splitlines()[-1])
        results.append(result)
        print(json.dumps(result, sort_keys=True), flush=True)
    eligible = [
        result
        for result in results
        if result["status"] == "ok" and result["reserved_headroom_fraction"] >= 0.15
    ]
    selected = max(
        eligible, key=lambda result: result["samples_per_second"], default=None
    )
    report = {
        "config": str(config_path.resolve()),
        "effective_batch_size": EFFECTIVE_BATCH_SIZE,
        "selection_rule": "fastest stable candidate with >=15% reserved-memory headroom",
        "results": results,
        "selected": selected,
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if selected is not None else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", nargs=2, type=int, metavar=("MICRO", "ACCUM"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.worker:
        try:
            result = worker(args.config, *args.worker)
        except torch.cuda.OutOfMemoryError as exc:
            print(json.dumps({"status": "oom", "error": str(exc)}))
            return 2
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.output is None:
        raise SystemExit("--output is required unless --worker is used")
    return orchestrate(args.config, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
