"""Full-region and matched unseen-source reports for one LORO fold."""

import json
from pathlib import Path

import numpy as np

from kelpseg.reporting.inputs import ReportSettings, read_csv, read_probability
from kelpseg.reporting.report import report, write_csv
from kelpseg.reporting.temporal import temporal_report
from kelpseg.reporting.temporal_inputs import TemporalSettings


def _subset_predictions(root: Path, output: Path, keys: set[str]) -> None:
    """Write a small prediction view referencing unchanged absolute raster paths."""
    output.mkdir()
    rows = [r for r in read_csv(root / "sources.csv") if r["source_key"] in keys]
    for row in rows:
        row["probability"] = str((root / row["probability"]).resolve())
    write_csv(output / "sources.csv", rows)
    write_csv(
        output / "windows.csv",
        [r for r in read_csv(root / "windows.csv") if r["source_key"] in keys],
    )
    for name in ("settings.json", "summary.json"):
        value = json.loads((root / name).read_text())
        if name == "summary.json":
            value = dict(
                status="complete", sources=len(rows), parent_predictions=str(root)
            )
        (output / name).write_text(json.dumps(value, indent=2) + "\n")


def check_matched_coverage(
    predictions: Path, baseline_predictions: Path, keys: set[str]
) -> list[dict]:
    """Require identical native grids and finite coverage for the paired sources.

    The suite uses identical image-only tiling settings for both models. A
    mismatch stops reporting rather than silently changing evaluation support.
    Return per-source predicted coverage counts; raster inputs remain unchanged.
    """
    fold = {r["source_key"]: r for r in read_csv(predictions / "sources.csv")}
    baseline = {
        r["source_key"]: r for r in read_csv(baseline_predictions / "sources.csv")
    }
    if set(baseline) != keys or not keys <= set(fold):
        raise ValueError(
            "Baseline predictions must exactly match the paired source keys."
        )
    result = []
    for key in sorted(keys):
        left, right = fold[key], baseline[key]
        for name in (
            "image",
            "dataset_id",
            "release_id",
            "original_source_id",
            "region_id",
            "acquisition_date",
            "row_offset",
            "col_offset",
        ):
            if left.get(name, "") != right.get(name, ""):
                raise ValueError(f"{key}: paired source {name} differs.")
        first, transform, crs = read_probability(predictions / left["probability"])
        second, other_transform, other_crs = read_probability(
            baseline_predictions / right["probability"]
        )
        if (
            first.shape != second.shape
            or transform != other_transform
            or crs != other_crs
        ):
            raise ValueError(f"{key}: paired prediction grids differ.")
        finite = np.isfinite(first)
        if not np.array_equal(finite, np.isfinite(second)):
            raise ValueError(
                f"{key}: paired finite-pixel coverage differs; use identical tiling settings."
            )
        result.append(
            dict(
                source_key=key,
                total_pixels=first.size,
                common_predicted_pixels=int(finite.sum()),
            )
        )
    return result


def _verify_unseen(
    assignments: Path,
    experiment: str,
    sources: list[dict],
    labels: list[dict],
    keys: set[str],
) -> None:
    """Check paired originals and spacecraft/day groups against both selection pools."""
    rows = [r for r in read_csv(assignments) if r["variant"] == "augmented"]
    scopes = {}
    for scope in ("baseline", experiment):
        selected = [r for r in rows if r["experiment"] == scope]
        indexed = {}
        for row in selected:
            identity = tuple(row[k] for k in ("dataset_id", "release_id", "source_id"))
            if identity in indexed:
                raise ValueError(f"Duplicate {scope} assignment: {identity}.")
            indexed[identity] = row
        used_days = {
            (r["satellite_id"], r["acquisition_date"])
            for r in selected
            if r["split"] in ("train", "val")
        }
        scopes[scope] = indexed, used_days
    label_index = {r["source_key"]: r for r in labels}
    for source in sources:
        key = source["source_key"]
        if key not in keys:
            continue
        source_id = label_index[key].get("source_id") or source["original_source_id"]
        identity = source["dataset_id"], source["release_id"], source_id
        for scope, (indexed, used_days) in scopes.items():
            row = indexed.get(identity)
            if (
                row is None
                or row["split"] in ("train", "val")
                or (row["satellite_id"], row["acquisition_date"]) in used_days
            ):
                raise ValueError(
                    f"{key}: paired source was used for {scope} training/selection or has a used spacecraft/day companion."
                )
            if scope == experiment and row["split"] != "test":
                raise ValueError(f"{key}: paired LORO source must be held out.")


def report_fold(
    output: Path,
    predictions: Path,
    baseline_predictions: Path,
    labels: Path,
    label_root: Path,
    matched_keys: set[str],
    *,
    assignments: Path,
    experiment: str,
) -> Path:
    """Write full held-out and paired segmentation/change reports in a fresh folder.

    Labels describe all fold predictions. Baseline predictions contain exactly
    the unseen paired subset. Check membership and equal finite coverage before
    reporting. Use threshold 0.5, test scope and the existing temporal intervals.
    Empty paired scopes remain explicit without inventing scores or date pairs.
    """
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a fresh directory.")
    sources, label_rows = read_csv(predictions / "sources.csv"), read_csv(labels)
    _verify_unseen(assignments, experiment, sources, label_rows, matched_keys)
    coverage = (
        check_matched_coverage(predictions, baseline_predictions, matched_keys)
        if matched_keys
        else []
    )
    for root in [predictions, baseline_predictions] if matched_keys else [predictions]:
        metadata = json.loads((root / "settings.json").read_text())
        if metadata["model"]["threshold"] != 0.5:
            raise ValueError("LORO comparison fixes the threshold at 0.5.")
    output.mkdir(parents=True)
    write_csv(output / "pairing-coverage.csv", coverage)
    write_csv(
        output / "unmatched.csv",
        [
            dict(
                source_key=r["source_key"],
                reason="baseline training/selection or spacecraft/day companion",
            )
            for r in sources
            if r["source_key"] not in matched_keys
        ],
    )
    report(
        ReportSettings(
            predictions,
            output / "full-segmentation",
            labels=labels,
            label_root=label_root,
            assignments=assignments,
            experiment=experiment,
            variant="augmented",
            split="test",
        )
    )
    temporal_report(
        TemporalSettings(output / "full-segmentation", output / "full-temporal")
    )
    if matched_keys:
        paired_labels = output / "paired-labels.csv"
        write_csv(
            paired_labels, [r for r in label_rows if r["source_key"] in matched_keys]
        )
        paired_predictions = output / "paired-loro-predictions"
        _subset_predictions(predictions, paired_predictions, matched_keys)
        for arm, root in (
            ("loro", paired_predictions),
            ("baseline", baseline_predictions),
        ):
            segmentation = output / f"paired-{arm}-segmentation"
            report(
                ReportSettings(
                    root,
                    segmentation,
                    labels=paired_labels,
                    label_root=label_root,
                    external_scope=f"{experiment}: common unseen TIFFs, identical finite coverage",
                    split="test",
                )
            )
            temporal_report(
                TemporalSettings(segmentation, output / f"paired-{arm}-temporal")
            )
    (output / "summary.json").write_text(
        json.dumps(
            dict(
                status="complete",
                experiment=experiment,
                full_sources=len(sources),
                matched_sources=len(matched_keys),
                unmatched_sources=len(sources) - len(matched_keys),
            ),
            indent=2,
        )
        + "\n"
    )
    return output
