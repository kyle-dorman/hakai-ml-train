"""Pool source confusion counts and paired canopy-change errors across LORO folds."""

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

from kelpseg.reporting.inputs import read_csv
from kelpseg.reporting.metrics import COUNT_KEYS, scores
from kelpseg.reporting.report import write_csv
from kelpseg.reporting.temporal_summary import AREA_KEYS, COVERAGE_KEYS


def matched_pairs(left: list[dict], right: list[dict]) -> list[dict]:
    """Join identical date pairs and verify their scoreable footprints and labels.

    Return both arms' errors with an explicit jointly-defined flag. Unsupported
    and undefined pairs remain in the table; only jointly-defined percentage
    errors enter paired headline summaries.
    """

    def index(rows: list[dict]) -> dict[tuple[str, str], dict]:
        """Index temporal rows by the ordered original-source pair."""
        indexed = {(r["earlier_source"], r["later_source"]): r for r in rows}
        if len(indexed) != len(rows):
            raise ValueError("Duplicate temporal pair.")
        return indexed

    first, second = index(left), index(right)
    if first.keys() != second.keys():
        raise ValueError("Paired models have different temporal date pairs.")
    result = []
    shared = (
        "status",
        "common_pixels",
        "common_area_m2",
        "label_before_pixels",
        "label_after_pixels",
        "earlier_scoreable_pixels",
        "later_scoreable_pixels",
    )
    for key, row in first.items():
        other = second[key]
        if any(row[name] != other[name] for name in shared):
            raise ValueError(
                f"{key}: temporal coverage or label support differs between models."
            )
        defined = all(r.get("change_error_pp") not in (None, "") for r in (row, other))
        result.append(
            dict(
                region=row["region"],
                interval=row["interval"],
                earlier_source=key[0],
                later_source=key[1],
                **{name: row[name] for name in shared},
                jointly_defined=defined,
                loro_change_error_pp=row["change_error_pp"],
                baseline_change_error_pp=other["change_error_pp"],
            )
        )
    return result


def pool_segmentation(rows: list[dict]) -> list[dict]:
    """Pool counts for all regions and each region; never average source IoUs."""
    grouped = defaultdict(list)
    for row in rows:
        for region in ("all", row["region"]):
            grouped[row["scope"], row["arm"], region].append(row)
    result = []
    for (scope, arm, region), members in sorted(grouped.items()):
        counts = {key: sum(int(r[key]) for r in members) for key in COUNT_KEYS}
        result.append(
            dict(
                scope=scope,
                arm=arm,
                region=region,
                sources=len(members),
                **scores(counts),
                **{key: sum(float(r[key]) for r in members) for key in AREA_KEYS},
                **{key: sum(int(r[key]) for r in members) for key in COVERAGE_KEYS},
            )
        )
    return result


def pool_temporal(rows: list[dict]) -> list[dict]:
    """Summarize the declared pair scope by interval, pooled and by region."""
    grouped = defaultdict(list)
    for row in rows:
        for region in ("all", row["region"]):
            grouped[row["scope"], row["arm"], region, row["interval"]].append(row)
    result = []
    for (scope, arm, region, interval), members in sorted(grouped.items()):
        supported = [r for r in members if r["status"] == "supported"]
        defined = [r for r in supported if r.get("change_error_pp") not in (None, "")]
        headline = [r for r in defined if r["headline_eligible"]]
        errors = [float(r["change_error_pp"]) for r in headline]
        result.append(
            dict(
                scope=scope,
                arm=arm,
                region=region,
                interval=interval,
                candidate_pairs=len(members),
                supported_pairs=len(supported),
                percentage_defined_pairs=len(defined),
                headline_pairs=len(headline),
                common_pixel_observations=sum(
                    int(r["common_pixels"]) for r in supported
                ),
                mean_change_error_pp=mean(errors) if errors else None,
                median_change_error_pp=median(errors) if errors else None,
                mean_absolute_change_error_pp=mean(abs(v) for v in errors)
                if errors
                else None,
                median_absolute_change_error_pp=median(abs(v) for v in errors)
                if errors
                else None,
            )
        )
    return result


def summarize_suite(fold_outputs: list[Path], output: Path) -> Path:
    """Write pooled and per-region tables from completed per-fold report folders.

    Full-region LORO results remain separate from the baseline comparison.
    Percentage headlines compare only jointly-defined pairs, while all supported,
    undefined and unavailable pairs remain inspectable in the detailed tables.
    """
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a fresh directory.")
    sources, pairs, comparisons, unmatched = [], [], [], []
    for folder in fold_outputs:
        summary = json.loads((folder / "summary.json").read_text())
        if summary["status"] != "complete":
            raise ValueError(f"Incomplete fold report: {folder}.")
        experiment = summary["experiment"]
        arms = [("full", "loro", "full")]
        comparison = []
        if summary["matched_sources"]:
            comparison = matched_pairs(
                read_csv(folder / "paired-loro-temporal/pairs.csv"),
                read_csv(folder / "paired-baseline-temporal/pairs.csv"),
            )
            comparisons.extend(dict(experiment=experiment, **r) for r in comparison)
            arms.extend(
                ("paired", arm, f"paired-{arm}") for arm in ("loro", "baseline")
            )
        jointly_defined = {
            (r["earlier_source"], r["later_source"])
            for r in comparison
            if r["jointly_defined"]
        }
        for scope, arm, prefix in arms:
            for row in read_csv(folder / f"{prefix}-segmentation/sources.csv"):
                sources.append(dict(row, scope=scope, arm=arm, experiment=experiment))
            for row in read_csv(folder / f"{prefix}-temporal/pairs.csv"):
                key = row["earlier_source"], row["later_source"]
                pairs.append(
                    dict(
                        row,
                        scope=scope,
                        arm=arm,
                        experiment=experiment,
                        headline_eligible=scope == "full" or key in jointly_defined,
                    )
                )
        unmatched.extend(
            dict(experiment=experiment, **r) for r in read_csv(folder / "unmatched.csv")
        )
    output.mkdir(parents=True)
    for name, rows in (
        ("segmentation", pool_segmentation(sources)),
        ("temporal", pool_temporal(pairs)),
        ("sources", sources),
        ("pairs", pairs),
        ("paired-changes", comparisons),
        ("unmatched", unmatched),
    ):
        write_csv(output / f"{name}.csv", rows)
    (output / "summary.json").write_text(
        json.dumps(
            dict(
                status="complete",
                folds=len(fold_outputs),
                fold_reports=[str(p) for p in fold_outputs],
                segmentation="Confusion counts pooled across source observations; full and paired scopes remain separate.",
                temporal="Paired headlines use jointly-defined identical source/date pairs on equal pixel support. Repeated pairs are not independent samples.",
            ),
            indent=2,
        )
        + "\n"
    )
    return output
