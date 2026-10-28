"""Source assignments and metadata-only selection of existing chip windows."""

from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from pathlib import Path

from kelpseg.prepare.check import PreparationError
from kelpseg.prepare.chip import _write_json
from kelpseg.prepare.chip_inputs import IDENTITY_COLUMNS
from kelpseg.prepare.split_inputs import (
    COLLECTION_COLUMNS,
    ORIGINAL_COLUMNS,
    original_key,
)

logger = logging.getLogger(__name__)
ASSIGNMENT_COLUMNS = (*ORIGINAL_COLUMNS, "experiment", "variant", "split", "reason")


def _temporal_role(source: dict, rule: dict) -> str:
    day = source["acquisition_date"]
    # Reverse chronology swaps the early/late roles, keeping the same inclusive
    # cutoffs. The approved per-region recipe decides the direction.
    roles = (
        ("train", "val", "test")
        if rule["direction"] == "forward"
        else ("test", "val", "train")
    )
    if day <= rule["first_cutoff"]:
        return roles[0]
    if day <= rule["second_cutoff"]:
        return roles[1]
    return roles[2]


def _satellite_day(source: dict) -> tuple[str, str]:
    return source["satellite_id"], source["acquisition_date"]


def validate_assignments(rows: list[dict]) -> None:
    """Each experiment/variant isolates original TIFFs and physical groups."""
    logger.info(
        "Validating %d source assignments for original/date/spacecraft isolation",
        len(rows),
    )
    originals, days, region_days = set(), {}, {}
    for row in rows:
        scope = row["experiment"], row["variant"]
        key = (*scope, *original_key(row))
        if key in originals:
            raise PreparationError(f"Duplicate source assignment: {key}")
        originals.add(key)
        split = row["split"]
        if split not in ("train", "val", "test", "unused"):
            raise PreparationError(f"Unknown split: {split}")
        if split == "unused":
            # Excluded companions contribute to no partition in this fold.
            continue
        for groups, group, description in (
            (days, _satellite_day(row), "satellite/day"),
            (region_days, (row["region"], row["acquisition_date"]), "region/date"),
        ):
            group = (*scope, *group)
            if group in groups and groups[group] != split:
                raise PreparationError(
                    f"Conflicting {description} partitions for {group}: {groups[group]} / {split}"
                )
            groups[group] = split
    logger.info(
        "Assignment validation complete: %d spacecraft/day groups across experiment/variant scopes",
        len(days),
    )


def assign_sources(collection: list[dict], recipe: dict) -> list[dict]:
    """Assign originals once; all their crops and spectral variants inherit it."""
    logger.info(
        "Building baseline and LORO assignments from %d collection rows",
        len(collection),
    )
    originals = {}
    # Input normalization already checked agreement between crops. Collapse
    # them here so one original TIFF receives one role per experiment/variant.
    for row in collection:
        originals[original_key(row)] = {name: row[name] for name in ORIGINAL_COLUMNS}
    sources = list(originals.values())
    rules = {rule["region"]: rule for rule in recipe["regions"]}
    optional = set(recipe["training_only_regions"])
    regions = {row["region"] for row in sources}
    missing = regions - optional - rules.keys()
    if missing:
        raise PreparationError(
            f"Selected evaluation regions need split rules: {sorted(missing)}"
        )
    evaluation_dates = {
        row["acquisition_date"] for row in sources if row["region"] not in optional
    }
    for row in sources:
        satellite = row["satellite_id"]
        # The historical BC token is unresolved. Keep it literally only when
        # no evaluation imagery shares its day; never guess its full identity.
        unresolved = satellite in ("unknown", "unresolved", "?") or (
            len(satellite) == 3 and all(c in "0123456789abcdef" for c in satellite)
        )
        if unresolved and row["acquisition_date"] in evaluation_dates:
            raise PreparationError(
                f"{row['source_id']}: unresolved satellite_id {satellite!r} on an evaluation date; supply the physical spacecraft ID."
            )
    baseline = {}
    for source in sources:
        baseline[original_key(source)] = (
            "optional"
            if source["region"] in optional
            else _temporal_role(source, rules[source["region"]])
        )
    assignments = []
    for heldout in [None, *sorted(regions - optional)]:
        experiment = "baseline" if heldout is None else f"loro_{heldout}"
        logger.info(
            "Assigning %s: %d original sources; base and augmented variants",
            experiment,
            len(sources),
        )
        # All held-out dates enter test. Exclude their physical spacecraft/day
        # companions before considering optional training or baseline roles.
        test_days = {_satellite_day(row) for row in sources if row["region"] == heldout}
        for variant in ("base", "augmented"):
            for source in sources:
                role = baseline[original_key(source)]
                if heldout is not None and source["region"] == heldout:
                    split, reason = "test", "held_out_region_test"
                elif heldout is not None and _satellite_day(source) in test_days:
                    split, reason = "unused", "held_out_satellite_day"
                elif role == "optional":
                    split, reason = (
                        ("train", "training_only_included")
                        if variant == "augmented"
                        else ("unused", "training_only_excluded")
                    )
                elif heldout is None:
                    split, reason = role, "baseline_temporal"
                elif role == "test":
                    # Other regions' temporal test data cannot enter training
                    # or validation simply because this is a different fold.
                    split, reason = "unused", "nonheldout_temporal_test_unused"
                else:
                    split, reason = role, f"nonheldout_temporal_{role}"
                assignments.append(
                    dict(
                        source,
                        experiment=experiment,
                        variant=variant,
                        split=split,
                        reason=reason,
                    )
                )
    validate_assignments(assignments)
    logger.info(
        "Assignments ready: %d originals, %d LORO folds, %d rows",
        len(sources),
        len(regions - optional),
        len(assignments),
    )
    return assignments


def summarize_assignments(collection: list[dict], assignments: list[dict]) -> dict:
    """Source counts, never overlapping chip foreground totals or model scores."""
    scopes = {}
    for row in assignments:
        key = f"{row['experiment']}/{row['variant']}"
        if key not in scopes:
            scopes[key] = {
                "source_counts": dict.fromkeys(("train", "val", "test", "unused"), 0),
                "unused_reasons": {},
            }
        scopes[key]["source_counts"][row["split"]] += 1
        if row["split"] == "unused":
            reasons = scopes[key]["unused_reasons"]
            reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
    return dict(
        status="complete",
        crop_rows=len(collection),
        original_sources=len({original_key(row) for row in collection}),
        regions=sorted({row["region"] for row in collection}),
        distinct_dates=len({row["acquisition_date"] for row in collection}),
        satellite_day_groups=len({_satellite_day(row) for row in collection}),
        assignments=scopes,
    )


def _write_csv(path: Path, columns, rows) -> None:
    logger.info("Writing %s: %d rows", path.name, len(rows))
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def check_split_output(output: str | Path) -> Path:
    output = Path(output).expanduser().resolve()
    for target in (output, output.with_name(f".{output.name}.incomplete")):
        if target.exists():
            raise PreparationError(
                f"Output already exists; choose a fresh directory: {target}"
            )
    if not output.parent.is_dir():
        raise PreparationError(f"Output parent must exist: {output.parent}")
    return output


def write_splits(
    collection: list[dict], assignments: list[dict], recipe: dict, output: str | Path
) -> Path:
    """Publish five controls together. Failed work is not resumed or reused."""
    output = check_split_output(output)
    work = output.with_name(f".{output.name}.incomplete")
    work.mkdir()
    logger.info("Writing collection, chip metadata and source assignments: %s", output)
    _write_csv(work / "collection.csv", COLLECTION_COLUMNS, collection)
    _write_csv(work / "chip_metadata.csv", IDENTITY_COLUMNS, collection)
    _write_csv(work / "assignments.csv", ASSIGNMENT_COLUMNS, assignments)
    logger.info("Writing recipe.json")
    _write_json(work / "recipe.json", recipe)
    logger.info("Writing summary.json")
    _write_json(work / "summary.json", summarize_assignments(collection, assignments))
    # Publish the five controls together only after all writes succeed.
    logger.info("Publishing complete split directory: %s", output)
    work.rename(output)
    logger.info("Complete split output: %s", output)
    return output


def select_windows(
    chip_root, assignments, experiment="baseline", variant="base"
) -> list[dict]:
    """Join windows -> source_key -> original assignment, without opening NPZs.

    Returned payloads are absolute paths rooted at chip_root. Omitted windows
    have no payload and are unused, preserving their disposition as the reason.
    Window identity is (chip_root, source_key, row, col), not a chip_id.
    """
    chip_root = Path(chip_root).expanduser().resolve()
    logger.info("Selecting windows for %s/%s from %s", experiment, variant, chip_root)
    if isinstance(assignments, (str, Path)):
        logger.info("Reading assignments: %s", Path(assignments).resolve())
        with Path(assignments).open(newline="", encoding="utf-8") as stream:
            assignments = list(csv.DictReader(stream))
    selected = {}
    for row in assignments:
        if (row["experiment"], row["variant"]) != (experiment, variant):
            continue
        key = original_key(row)
        if key in selected:
            raise PreparationError(f"Duplicate source assignment: {key}")
        selected[key] = row
    if not selected:
        raise PreparationError(f"No assignments for {experiment}/{variant}.")
    logger.info(
        "Matched %d original assignments for %s/%s", len(selected), experiment, variant
    )
    sources = {}
    logger.info("Reading chip source identities: %s", chip_root / "sources.json")
    for row in json.loads((chip_root / "sources.json").read_text(encoding="utf-8")):
        key = row["source_key"]
        if key in sources:
            raise PreparationError(f"Duplicate chip source_key: {key}")
        original = original_key(row)
        if original not in selected:
            raise PreparationError(f"Missing source assignment for {original}.")
        assignment = selected[original]
        if any(
            row[name] != assignment[name] for name in ("region", "acquisition_date")
        ):
            raise PreparationError(f"Conflicting chip source identity: {key}")
        sources[key] = row
    logger.info("Joined %d chip sources to original assignments", len(sources))
    result, windows = [], set()
    logger.info("Reading window manifest: %s", chip_root / "windows.csv")
    with (chip_root / "windows.csv").open(newline="", encoding="utf-8") as stream:
        for window in csv.DictReader(stream):
            key = window["source_key"]
            if key not in sources:
                raise PreparationError(f"Missing chip source_key join: {key}")
            coordinates = (key, int(window["row"]), int(window["col"]))
            if coordinates in windows:
                raise PreparationError(f"Duplicate window: {coordinates}")
            windows.add(coordinates)
            source = sources[key]
            assignment = selected[original_key(source)]
            # Keep original/crop placement alongside the local window. Payloads
            # belong to the chip root, independent of any experiment/fold.
            record = dict(source, **window)
            record.update(
                {
                    name: assignment[name]
                    for name in (
                        *ORIGINAL_COLUMNS,
                        "experiment",
                        "variant",
                        "split",
                        "reason",
                    )
                }
            )
            record["chip_root"] = str(chip_root)
            retained = window["disposition"] == "retained"
            if retained != bool(window["payload"]):
                raise PreparationError(
                    f"{coordinates}: retained windows need payloads; omitted windows have none."
                )
            record["payload"] = str(chip_root / window["payload"]) if retained else ""
            if not retained:
                # A source may be assigned to train/test even when this window
                # was omitted by chipping and therefore has no array to load.
                record.update(split="unused", reason=window["disposition"])
            result.append(record)
            if len(result) % 10000 == 0:
                logger.info(
                    "Joined %d windows for %s/%s; current source %s",
                    len(result),
                    experiment,
                    variant,
                    key,
                )
    logger.info(
        "Selected %s/%s: %s windows",
        experiment,
        variant,
        dict(Counter(row["split"] for row in result)),
    )
    return result
