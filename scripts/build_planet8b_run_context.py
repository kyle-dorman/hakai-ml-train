#!/usr/bin/env python3
"""Build a validated PlanetScope 8-band training run context."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.run_context import build_run_context, write_run_context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--fold-root", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--run-type", choices=("baseline_training", "loro_training"), required=True
    )
    parser.add_argument("--fold-id", required=True)
    parser.add_argument("--held-out-region")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    context = build_run_context(
        dataset_root=args.dataset_root,
        fold_root=args.fold_root,
        model_config_path=args.model_config,
        repo_root=args.repo_root,
        run_type=args.run_type,
        fold_id=args.fold_id,
        held_out_region=args.held_out_region,
        seed=args.seed,
        smoke=args.smoke,
        offline=args.offline,
    )
    write_run_context(context, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
