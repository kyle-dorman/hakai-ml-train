"""Fixed training diagnostics using the validation window-selection procedure."""

import csv
import random
from collections import defaultdict
from typing import Any

from kelpseg.prepare.split_inputs import original_key
from kelpseg.prepare.splits import select_windows


def training_sample(
    run: dict[str, Any], sources_per_region: int, seed: int
) -> list[dict[str, Any]]:
    """Return disjoint unaugmented training windows for seeded source samples.

    Sample original TIFF identities uniformly within each training region without
    inspecting labels. Apply the existing validation grid to those sources using
    an in-memory assignment copy; never write or change the experiment split.
    Include background-only windows. Returned rows retain split='train'.
    """
    if sources_per_region < 1:
        raise ValueError("sources_per_region must be positive.")
    with open(run["assignments"], newline="") as stream:
        assignments = list(csv.DictReader(stream))
    groups = defaultdict(list)
    for row in assignments:
        if (row["experiment"], row["variant"], row["split"]) == (
            run["experiment"],
            run["variant"],
            "train",
        ):
            groups[row["region"]].append(row)
    rng = random.Random(seed)
    selected = set()
    for region in sorted(groups):
        candidates = sorted(groups[region], key=original_key)
        for row in rng.sample(candidates, min(sources_per_region, len(candidates))):
            selected.add(original_key(row))
    for row in assignments:
        key = original_key(row)
        row["split"] = (
            "val" if key in selected and row["split"] == "train" else "unused"
        )
    rows = select_windows(
        run["chips"], assignments, experiment=run["experiment"], variant=run["variant"]
    )
    return [dict(row, split="train") for row in rows if row["split"] == "val"]


def fixed_validation_samples(rows: list[dict]) -> list[str]:
    """One positive chip per region where possible, then two background chips."""
    ordered = sorted(
        rows,
        key=lambda row: (
            row["region"],
            row["source_id"],
            int(row["row"]),
            int(row["col"]),
        ),
    )
    by_region = {}
    for row in ordered:
        by_region.setdefault(row["region"], []).append(row)
    keys = []
    for candidates in by_region.values():
        selected = candidates[0]
        for row in candidates:
            if int(row["kelp_pixels"]) > 0:
                selected = row
                break
        keys.append(str(selected["payload"]))
    extra_background = 0
    for row in ordered:
        key = str(row["payload"])
        if int(row["kelp_pixels"]) == 0 and key not in keys:
            keys.append(key)
            extra_background += 1
            if extra_background == 2:
                break
    return keys
