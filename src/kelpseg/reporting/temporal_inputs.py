"""Flat temporal settings and date-based pairing of one completed labeled report."""

import json
import tomllib
from collections import defaultdict
from dataclasses import dataclass, fields
from datetime import date
from itertools import combinations
from pathlib import Path

from kelpseg.paths import _resolve_path
from kelpseg.reporting.inputs import read_csv

LOCATION_KEYS = ("dataset_id", "release_id", "region")


@dataclass(frozen=True)
class TemporalSettings:
    """Paths and inclusive elapsed-day intervals; no inference or model settings."""

    report: Path
    output: Path
    pairs: Path | None = None
    short_min_days: int = 1
    short_max_days: int = 13
    long_min_days: int = 29
    long_max_days: int = 47
    small_baseline_pixels: int = 10

    def __post_init__(self) -> None:
        """Reject overlapping/nonpositive intervals and invalid baseline flags."""
        days = (
            self.short_min_days,
            self.short_max_days,
            self.long_min_days,
            self.long_max_days,
        )
        if any(type(value) is not int for value in days) or not (
            1 <= days[0] <= days[1] < days[2] <= days[3]
        ):
            raise ValueError(
                "Day intervals must be positive integers with short_min <= short_max < long_min <= long_max."
            )
        if (
            type(self.small_baseline_pixels) is not int
            or self.small_baseline_pixels < 0
        ):
            raise ValueError(
                "small_baseline_pixels must be a nonnegative integer; zero disables small-baseline flags."
            )


def load_settings(recipe: str | Path) -> TemporalSettings:
    """Read one TOML recipe, resolving ordinary paths relative to that file."""
    recipe = Path(recipe).expanduser().resolve()
    values = tomllib.loads(recipe.read_text())
    unknown = values.keys() - {field.name for field in fields(TemporalSettings)}
    if unknown:
        raise ValueError(f"Unknown temporal settings: {', '.join(sorted(unknown))}.")
    for name in ("report", "output", "pairs"):
        if name == "pairs" and name not in values:
            continue
        value = values.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a nonempty path.")
        values[name] = _resolve_path(value, base=recipe.parent, context=name)
    return TemporalSettings(**values)


def read_report(settings: TemporalSettings) -> tuple[dict, list[dict]]:
    """Read completed Task 036 metadata and unique source rows, without payload reads."""
    summary = json.loads((settings.report / "summary.json").read_text())
    if summary.get("status") != "complete" or summary.get("scope") not in (
        "chip_disjoint",
        "tiff_tiled",
    ):
        raise ValueError(
            "Temporal reporting requires one completed Task 036 chip/TIFF report."
        )
    rows = read_csv(settings.report / "sources.csv")
    if not rows:
        raise ValueError("The input report has no sources.")
    seen = set()
    for row in rows:
        key = row.get("source_keys", "")
        if not key or key in seen:
            raise ValueError(
                "Report sources must have unique nonempty source_keys; regenerate with the current report command."
            )
        seen.add(key)
        if row.get("scope") != summary["scope"] or row.get("split") != summary["split"]:
            raise ValueError(
                f"{key}: source scope/split differs from the report summary."
            )
    return summary, rows


def interval_for(days: int, settings: TemporalSettings) -> str:
    """Classify an elapsed-day gap; interval endpoints are inclusive."""
    if days == 0:
        return "same_day"
    if settings.short_min_days <= days <= settings.short_max_days:
        return "short"
    if settings.long_min_days <= days <= settings.long_max_days:
        return "long"
    return "outside_intervals"


def select_pairs(rows: list[dict], settings: TemporalSettings) -> list[dict]:
    """Select within-location pairs by elapsed days or an explicit identity CSV.

    Default selection includes both configured intervals and separate same-day
    records. Explicit pairs outside intervals remain recorded as unavailable.
    No spatial matching, label-based selection or filename inference is performed.
    """
    indexed = {row["source_keys"]: row for row in rows}
    candidates = []
    if settings.pairs is None:
        locations = defaultdict(list)
        for row in rows:
            if row.get("region") and row.get("acquisition_date"):
                locations[tuple(row[key] for key in LOCATION_KEYS)].append(row)
        for location in sorted(locations):
            ordered = sorted(
                locations[location],
                key=lambda row: (row["acquisition_date"], row["source_keys"]),
            )
            candidates.extend(combinations(ordered, 2))
    else:
        seen = set()
        for record in read_csv(settings.pairs):
            keys = record.get("earlier_source", ""), record.get("later_source", "")
            identity = tuple(sorted(keys))
            if (
                keys[0] == keys[1]
                or identity in seen
                or any(key not in indexed for key in keys)
            ):
                raise ValueError(
                    f"Pair {keys}: use distinct, known report source_keys without duplicates."
                )
            seen.add(identity)
            candidates.append((indexed[keys[0]], indexed[keys[1]]))
    result = []
    for earlier, later in candidates:
        location = tuple(earlier.get(name, "") for name in LOCATION_KEYS)
        if location != tuple(later.get(name, "") for name in LOCATION_KEYS):
            raise ValueError("Temporal pairs must share dataset, release and region.")
        days = None
        if (
            not location[2]
            or not earlier.get("acquisition_date")
            or not later.get("acquisition_date")
        ):
            interval = "unknown_metadata"
        else:
            days = (
                date.fromisoformat(later["acquisition_date"])
                - date.fromisoformat(earlier["acquisition_date"])
            ).days
            if days < 0:
                raise ValueError(
                    "Pair dates are reversed; earlier_source must precede later_source."
                )
            interval = interval_for(days, settings)
        if settings.pairs is None and interval == "outside_intervals":
            continue
        result.append(
            dict(
                dataset_id=location[0],
                release_id=location[1],
                region=location[2],
                earlier_source=earlier["source_keys"],
                later_source=later["source_keys"],
                earlier_date=earlier.get("acquisition_date", ""),
                later_date=later.get("acquisition_date", ""),
                days=days,
                interval=interval,
            )
        )
    return result
