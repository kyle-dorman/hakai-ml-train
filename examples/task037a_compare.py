"""Check matched tiled footprints and write side-by-side Task 037A tables."""

import argparse
import logging
from collections import defaultdict
from pathlib import Path
from statistics import mean

import numpy as np
from task037a_prepare import check_prediction_scope, grid, read_json

from kelpseg.reporting.inputs import load_settings, read_csv, read_probability
from kelpseg.reporting.metrics import COUNT_KEYS, scores
from kelpseg.reporting.report import pooled, write_csv

ARMS = ("with-bc", "no-bc")
# Region identities come from configs/regions.csv.
BAJA_REGIONS = ("001", "002")
CALIFORNIA_REGIONS = tuple(f"{code:03}" for code in range(3, 11))
logger = logging.getLogger(__name__)


def check_coverage(output: Path, reference: Path, no_bc: Path) -> None:
    """Require the same grid and exact finite prediction pixels for both arms."""
    sources = read_csv(output / "validation.csv")
    settings = [load_settings(output / f"{arm}-report.toml") for arm in ARMS]
    indexed = [
        check_prediction_scope(
            recipe.predictions, sources, read_json(run / "model/model.json")
        )
        for recipe, run in zip(settings, (reference, no_bc), strict=True)
    ]
    for source in sources:
        key = source["source_key"]
        logger.info("Checking matched pixel coverage for %s", key)
        expected_grid = grid(Path(source["image"]))
        finite = []
        for recipe, rows in zip(settings, indexed, strict=True):
            path = recipe.predictions / rows[key]["probability"]
            probability, transform, crs = read_probability(path)
            if (probability.shape, transform, crs) != expected_grid:
                raise ValueError(
                    f"{path}: probability grid differs from {source['image']}."
                )
            finite.append(np.isfinite(probability))
            del probability
        if not np.array_equal(finite[0], finite[1]):
            raise ValueError(f"{key}: finite prediction coverage differs between arms.")


def geography(region: str) -> str:
    """Label the locked evaluation regions as California or Baja."""
    if region in BAJA_REGIONS:
        return "Baja"
    if region in CALIFORNIA_REGIONS:
        return "California"
    raise ValueError(f"Unexpected evaluation region: {region!r}.")


def pair_rows(
    reference: list[dict],
    candidate: list[dict],
    keys: tuple[str, ...],
    shared: tuple[str, ...],
    metrics: tuple[str, ...],
) -> list[dict]:
    """Join two tables by identity, keeping shared support and per-arm measurements."""
    right = {tuple(row[key] for key in keys): row for row in candidate}
    if len(right) != len(candidate) or len(right) != len(reference):
        raise ValueError(
            f"Paired results must have identical unique identities: {keys}."
        )
    result = []
    for left in reference:
        identity = tuple(left[key] for key in keys)
        other = right.pop(identity, None)
        if other is None or any(left[key] != other[key] for key in shared):
            raise ValueError(
                f"Paired results differ in identity or common support: {identity}."
            )
        record = {key: left[key] for key in (*keys, *shared)}
        for prefix, row in zip(("with_bc", "no_bc"), (left, other), strict=True):
            record.update({f"{prefix}_{key}": row[key] for key in metrics})
        result.append(record)
    return result


def segmentation_tables(output: Path) -> None:
    """Publish paired source, pooled-region and California/Baja confusion and scores."""
    support = (
        "scoreable_pixels",
        "valid_pixels",
        "uncovered_valid_pixels",
        "ignored_valid_pixels",
        "labeled_kelp_pixels",
    )
    metrics = (*COUNT_KEYS, "iou", "precision", "recall")
    sources = []
    for arm in ARMS:
        rows = read_csv(output / f"{arm}-segmentation/sources.csv")
        for row in rows:
            row["geography"] = geography(row["region"])
            for key in (*COUNT_KEYS, *support):
                row[key] = int(row[key])
        sources.append(rows)
    write_csv(
        output / "paired-sources.csv",
        pair_rows(
            *sources,
            ("source_keys",),
            ("original_tiff", "region", "geography", "acquisition_date", *support),
            metrics,
        ),
    )
    for group in ("region", "geography"):
        tables = []
        for rows in sources:
            table = pooled(rows, (group,), (*COUNT_KEYS, *support))
            for row in table:
                row.update(scores({key: row[key] for key in COUNT_KEYS}))
            tables.append(table)
        write_csv(
            output / f"paired-{group}.csv",
            pair_rows(*tables, (group,), support, metrics),
        )


def temporal_tables(output: Path) -> None:
    """Publish paired dates and aggregate errors on pairs defined in both arms."""
    pairs = pair_rows(
        *(read_csv(output / f"{arm}-temporal/pairs.csv") for arm in ARMS),
        ("earlier_source", "later_source"),
        (
            "region",
            "earlier_date",
            "later_date",
            "days",
            "interval",
            "status",
            "common_pixels",
            "earlier_scoreable_pixels",
            "later_scoreable_pixels",
            "earlier_coverage_fraction",
            "later_coverage_fraction",
            "label_change_pct",
        ),
        ("prediction_change_pct", "change_error_pp", "percentage_status"),
    )
    for row in pairs:
        row["geography"] = geography(row["region"])
    write_csv(output / "paired-temporal-pairs.csv", pairs)
    for group in ("region", "geography"):
        groups = defaultdict(list)
        for row in pairs:
            groups[(row[group], row["interval"])].append(row)
        summary = []
        for (location, interval), rows in sorted(groups.items()):
            defined = [
                row
                for row in rows
                if row["with_bc_change_error_pp"] != ""
                and row["no_bc_change_error_pp"] != ""
            ]
            record = {
                group: location,
                "interval": interval,
                "pairs": len(rows),
                "supported_pairs": sum(row["status"] == "supported" for row in rows),
                "both_defined_pairs": len(defined),
                "common_pixel_observations": sum(
                    int(row["common_pixels"]) for row in rows
                ),
                "both_defined_common_pixel_observations": sum(
                    int(row["common_pixels"]) for row in defined
                ),
            }
            for arm in ("with_bc", "no_bc"):
                key = f"{arm}_change_error_pp"
                errors = [float(row[key]) for row in defined]
                record[f"{arm}_defined_pairs"] = sum(bool(row[key]) for row in rows)
                record[f"{arm}_mean_signed_error_pp"] = mean(errors) if errors else None
                record[f"{arm}_mean_absolute_error_pp"] = (
                    mean(map(abs, errors)) if errors else None
                )
            summary.append(record)
        write_csv(output / f"paired-temporal-{group}.csv", summary)


def summarize(output: Path, reference: Path, no_bc: Path) -> None:
    """Write paired validation tables and selected checkpoints with actual budgets."""
    segmentation_tables(output)
    temporal_tables(output)
    rows = []
    for arm, root in zip(ARMS, (reference, no_bc), strict=True):
        run = read_json(root / "run.json")
        model = read_json(root / "model/model.json")
        rows.append(
            dict(
                arm=arm,
                run_id=run["run_id"],
                variant=run["variant"],
                planned_updates=run["budget"]["optimizer_updates_total"],
                actual_updates=run["optimizer_updates_actual"],
                stopped_early=run["stopped_early"],
                selected_epoch=model["checkpoint_epoch"] + 1,
                selected_checkpoint_updates=model["optimizer_updates"],
                weight_kind=model["weight_kind"],
                checkpoint=run["best_checkpoint"],
                bundle=str(root / "model"),
            )
        )
    write_csv(output / "training-comparison.csv", rows)


def main() -> None:
    """Check saved coverage or summarize completed comparison reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("check", "summarize"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        with_bc = Path(read_json(args.output / "with-bc-model.json")["bundle"]).parent
        no_bc = Path(read_json(args.output / "no-bc-dry-run.json")["output"])
        action = check_coverage if args.stage == "check" else summarize
        action(args.output, with_bc, no_bc)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Task 037A {args.stage} failed: {error}\n")


if __name__ == "__main__":
    main()
