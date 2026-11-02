"""Choose kelp-rich preview training windows without opening payloads."""

import json
from pathlib import Path

import numpy as np

from kelpseg.prepare.splits import select_windows


def _window_key(row: dict) -> tuple:
    return row["source_key"], int(row["row"]), int(row["col"])


def _foreground_fraction(row: dict) -> float:
    scoreable = int(row["kelp_pixels"]) + int(row["background_pixels"])
    return int(row["kelp_pixels"]) / max(scoreable, 1)


def select_preview_windows(
    chips: str | Path,
    assignments: str | Path,
    variant: str,
    positive_samples: int,
    seed: int,
) -> list[dict]:
    """Select positives plus two diagnostic backgrounds, using train metadata only.

    Positive examples have substantial supplied-label support, rather than
    tiny one-pixel positives. They are display diagnostics, not representative
    evaluation samples. Only returned training payloads are later opened.
    """
    if type(positive_samples) is not int or not 1 <= positive_samples <= 16:
        raise ValueError("positive_samples must be an integer in 1..16.")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a nonnegative integer.")
    chip_size = json.loads((Path(chips) / "recipe.json").read_text(encoding="utf-8"))[
        "chip_size"
    ]
    selected = select_windows(
        chips, assignments, experiment="baseline", variant=variant
    )
    training = [row for row in selected if row["split"] == "train" and row["payload"]]
    positives = []
    for row in training:
        area = int(row["height"]) * int(row["width"])
        if (
            int(row["kelp_pixels"]) / area >= 0.1
            and int(row["nodata_pixels"]) / area <= 0.25
            and 0.1 <= _foreground_fraction(row) <= 0.8
        ):
            positives.append(row)
    backgrounds = [row for row in training if int(row["kelp_pixels"]) == 0]
    if len(positives) < positive_samples:
        raise ValueError(
            f"Only {len(positives)} visibly kelp-positive training windows meet the preview criteria (at least 10% kelp area, at most 25% nodata and 80% labeled foreground); use a larger training subset or lower positive_samples from {positive_samples}."
        )
    if len(backgrounds) < 2:
        raise ValueError(
            "Preview needs two canonical background training windows; use a larger declared training subset."
        )

    # Stable source/window ordering precedes seeded tie breaks, so CSV order is
    # not a hidden source of changes in the preview sample.
    positives.sort(key=_window_key)
    backgrounds.sort(key=_window_key)
    generator = np.random.default_rng(seed)
    generator.shuffle(positives)
    generator.shuffle(backgrounds)
    backgrounds.sort(
        key=lambda row: (
            int(row["nodata_pixels"]) / (int(row["height"]) * int(row["width"]))
        )
    )
    result, seen, sources = [], set(), set()

    def add(pool: list[dict], reason: str, *, control: bool = False) -> None:
        available = [row for row in pool if _window_key(row) not in seen]
        if not available:
            return
        diverse = [row for row in available if row["source_id"] not in sources]
        row = (diverse or available)[0]
        count = sum(item["background_control"] == control for item in result) + 1
        name = f"background_control_{count:02d}" if control else f"training_{count:02d}"
        result.append(
            dict(
                row, preview_name=name, sample_reason=reason, background_control=control
            )
        )
        seen.add(_window_key(row))
        sources.add(row["source_id"])

    def quality(row: dict, target: float = 0.25) -> float:
        area = int(row["height"]) * int(row["width"])
        # Aim for a substantial kelp patch with surrounding context. Favoring
        # low nodata avoids spending most of the display on unavailable imagery.
        return (
            abs(int(row["kelp_pixels"]) / area - target)
            + 0.15 * int(row["nodata_pixels"]) / area
        )

    positives.sort(key=quality)
    # Start with visible kelp from each represented region; no sparse/count-
    # minimum slots. Regions without substantial kelp support are skipped.
    for region in sorted({row["region"] for row in positives}):
        if len(result) >= positive_samples:
            break
        add(
            [row for row in positives if row["region"] == region],
            f"visible_kelp_region_{region}",
        )
    features = (
        (
            [
                row
                for row in positives
                if int(row["height"]) < chip_size or int(row["width"]) < chip_size
            ],
            "visible_kelp_partial_edge",
        ),
        (
            [row for row in positives if int(row["nodata_pixels"]) > 0],
            "visible_kelp_native_nodata",
        ),
    )
    for pool, reason in features:
        if len(result) < positive_samples:
            add(pool, reason)
    while len(result) < positive_samples:
        add(positives, "visible_kelp_additional_source")

    bc_backgrounds = [row for row in backgrounds if row["region"] in ("011", "012")]
    add(bc_backgrounds or backgrounds, "canonical_background_diagnostic", control=True)
    add(backgrounds, "canonical_background_diagnostic", control=True)
    return result
