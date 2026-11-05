"""Descriptive temporal tables from existing source scores and matched pairs."""

from collections import defaultdict
from datetime import date
from statistics import mean, median

from kelpseg.reporting.metrics import COUNT_KEYS, scores
from kelpseg.reporting.report import pooled
from kelpseg.reporting.temporal_inputs import LOCATION_KEYS

AREA_KEYS = (
    "scoreable_area_m2",
    "labeled_area_m2",
    "predicted_area_m2",
    "area_bias_m2",
    "false_positive_area_m2",
    "false_negative_area_m2",
)
COVERAGE_KEYS = (
    "total_pixels",
    "valid_pixels",
    "nodata_pixels",
    "predicted_valid_pixels",
    "uncovered_valid_pixels",
    "ignored_valid_pixels",
    "scoreable_pixels",
)


def summarize_sources(rows: list[dict]) -> dict[str, list[dict]]:
    """Pool existing report rows by region and represented date/year/month.

    Accept CSV string values or numeric records. Missing dates/regions produce
    explicit exclusions; malformed declared dates raise ValueError. Totals count
    observations, not unique spatial area across acquisitions. Return tables
    without reading imagery or changing the input records.
    """
    records, excluded = [], []
    for row in rows:
        identity = {key: row.get(key, "") for key in LOCATION_KEYS}
        day = row.get("acquisition_date", "")
        try:
            acquired = date.fromisoformat(day) if day else None
        except ValueError as error:
            raise ValueError(
                f"{row['source_keys']}: acquisition_date must be an ISO YYYY-MM-DD date."
            ) from error
        reasons = []
        if not identity["region"]:
            reasons.append("missing_region")
        if not day:
            reasons.append("missing_date")
        if reasons:
            excluded.append(
                dict(
                    **identity,
                    source_keys=row["source_keys"],
                    acquisition_date=day,
                    reason=";".join(reasons),
                )
            )
            continue
        values = {key: int(row[key]) for key in COUNT_KEYS}
        values.update({key: int(row.get(key, 0)) for key in COVERAGE_KEYS})
        values.update({key: float(row.get(key, 0)) for key in AREA_KEYS})
        records.append(
            dict(
                **identity,
                acquisition_date=day,
                year=acquired.year,
                month=acquired.month,
                source_observations=1,
                **values,
            )
        )
    tables = {"source_exclusions": excluded}
    for name, time_keys in (
        ("dates", ("acquisition_date",)),
        ("years", ("year",)),
        ("year_months", ("year", "month")),
        ("months", ("month",)),
    ):
        keys = (*LOCATION_KEYS, *time_keys)
        represented_dates = defaultdict(set)
        for row in records:
            represented_dates[tuple(row[key] for key in keys)].add(
                row["acquisition_date"]
            )
        totals = pooled(
            records,
            keys,
            (*COUNT_KEYS, *AREA_KEYS, *COVERAGE_KEYS, "source_observations"),
        )
        result = []
        for row in sorted(totals, key=lambda r: tuple(r[key] for key in keys)):
            dates = sorted(represented_dates[tuple(row[key] for key in keys)])
            result.append(
                dict(
                    **{key: row[key] for key in keys},
                    source_observations=row["source_observations"],
                    represented_dates=";".join(dates),
                    represented_date_count=len(dates),
                    **scores({key: row[key] for key in COUNT_KEYS}),
                    **{key: row[key] for key in (*AREA_KEYS, *COVERAGE_KEYS)},
                )
            )
        tables[name] = result
    return tables


def summarize_pairs(rows: list[dict]) -> list[dict]:
    """Summarize finite pair errors within each location and elapsed-day interval.

    Percentages are never pooled across baselines. Counts retain unsupported and
    undefined pairs; medians/means describe repeated, non-independent pairs.
    Same-day rows remain a separate interval with no temporal percentage error.
    """
    keys = (*LOCATION_KEYS, "interval")
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key, "") for key in keys)].append(row)
    result = []
    for identity, members in sorted(groups.items()):
        supported = [row for row in members if row["status"] == "supported"]
        errors = [
            float(row["change_error_pp"])
            for row in supported
            if row.get("change_error_pp") not in (None, "")
        ]
        absolute = [abs(value) for value in errors]
        result.append(
            dict(
                **dict(zip(keys, identity, strict=True)),
                pairs=len(members),
                supported_pairs=len(supported),
                percentage_defined_pairs=len(errors),
                percentage_undefined_pairs=len(supported) - len(errors),
                unavailable_pairs=len(members) - len(supported),
                median_change_error_pp=median(errors) if errors else None,
                mean_absolute_change_error_pp=mean(absolute) if absolute else None,
                median_absolute_change_error_pp=median(absolute) if absolute else None,
            )
        )
    return result
