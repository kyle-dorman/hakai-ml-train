"""Build a non-destructive training selection from a canonical chip manifest.

The historical entry point deleted background-only NPZ files. That behavior is
intentionally disabled. This module classifies chips from manifest pixel counts
and writes an auditable selection that later training-view materializers may
join by ``chip_id``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

CLASS_PRESENCE_ORDER = [
    "positive",
    "clean_background_only",
    "mixed_background_nodata",
    "ignore_only",
]
BACKGROUND_CLASS_PRESENCE = set(CLASS_PRESENCE_ORDER[1:])
POLICIES = {"exclude_all", "retain_fraction"}
REQUIRED_MANIFEST_COLUMNS = [
    "chip_id",
    "source_tiff_id",
    "region_id",
    "total_pixel_count",
    "class_0_pixel_count",
    "class_1_pixel_count",
    "ignore_pixel_count",
    "nodata_pixel_count",
]
SELECTION_COLUMNS = [
    "chip_id",
    "source_tiff_id",
    "region_id",
    "class_0_pixel_count",
    "class_1_pixel_count",
    "ignore_pixel_count",
    "nodata_pixel_count",
    "class_presence",
    "selected_for_training",
    "selection_reason",
    "policy",
    "retain_fraction",
    "seed",
]
PIXEL_COLUMNS = [
    "total_pixel_count",
    "class_0_pixel_count",
    "class_1_pixel_count",
    "ignore_pixel_count",
    "nodata_pixel_count",
]
SUMMARY_COLUMNS = [
    "scope",
    "region_id",
    "source_tiff_id",
    "class_presence",
    "chip_count",
    "selected_chip_count",
    "excluded_chip_count",
    *PIXEL_COLUMNS,
    *[f"selected_{column}" for column in PIXEL_COLUMNS],
    *[f"excluded_{column}" for column in PIXEL_COLUMNS],
    "policy",
    "retain_fraction",
    "seed",
]


@dataclass(frozen=True)
class ClassifiedChip:
    """Validated manifest identity, counts, and derived presence class."""

    chip_id: str
    source_tiff_id: str
    region_id: str
    counts: dict[str, int]
    class_presence: str


@dataclass(frozen=True)
class SelectionResult:
    """Paths and counts produced by one selector invocation."""

    policy: str
    retain_fraction: str
    seed: str
    total_count: int
    selected_count: int
    excluded_count: int
    output_manifest: Path | None
    summary_output: Path


def parse_retain_fraction(value: str | Decimal | float | int) -> Decimal:
    """Parse one finite fraction in the inclusive range [0, 1]."""
    try:
        fraction = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("--retain-fraction must be a number in [0, 1]") from error
    if not fraction.is_finite() or fraction < 0 or fraction > 1:
        raise ValueError("--retain-fraction must be a finite number in [0, 1]")
    return fraction


def _argparse_fraction(value: str) -> Decimal:
    try:
        return parse_retain_fraction(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _decimal_text(value: Decimal) -> str:
    normalized = format(value.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Manifest does not exist: {path}")
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise RuntimeError(f"Manifest has no header: {path}")
        fieldnames = reader.fieldnames
        if len(fieldnames) != len(set(fieldnames)):
            raise RuntimeError(f"Manifest contains duplicate columns: {path}")
        rows = list(reader)
    if any(None in row for row in rows):
        raise RuntimeError(f"Manifest row has more values than columns: {path}")
    return fieldnames, rows


def _classify(class_0: int, class_1: int, nodata: int) -> str:
    if class_1 > 0:
        return "positive"
    if class_0 > 0 and nodata == 0:
        return "clean_background_only"
    if class_0 > 0:
        return "mixed_background_nodata"
    return "ignore_only"


def _read_and_classify_manifest(manifest: Path) -> list[ClassifiedChip]:
    fieldnames, rows = _read_csv(manifest)
    missing_columns = sorted(set(REQUIRED_MANIFEST_COLUMNS) - set(fieldnames))
    if missing_columns:
        raise RuntimeError(
            f"Manifest lacks required columns {missing_columns}: {manifest}"
        )

    seen_chip_ids: set[str] = set()
    classified: list[ClassifiedChip] = []
    for line_number, row in enumerate(rows, start=2):
        identities = {
            column: row[column].strip()
            for column in ("chip_id", "source_tiff_id", "region_id")
        }
        for column, value in identities.items():
            if not value:
                raise RuntimeError(f"Blank {column} at manifest line {line_number}")
        folded_id = identities["chip_id"].casefold()
        if folded_id in seen_chip_ids:
            raise RuntimeError(
                "Duplicate chip_id at manifest line "
                f"{line_number}: {identities['chip_id']}"
            )
        seen_chip_ids.add(folded_id)

        try:
            counts = {column: int(row[column]) for column in PIXEL_COLUMNS}
        except ValueError as error:
            raise RuntimeError(
                f"Invalid pixel count at manifest line {line_number}"
            ) from error
        if counts["total_pixel_count"] <= 0:
            raise RuntimeError(
                f"total_pixel_count must be positive at manifest line {line_number}"
            )
        if any(value < 0 for value in counts.values()):
            raise RuntimeError(
                f"Pixel counts must be nonnegative at line {line_number}"
            )
        stored_total = sum(
            counts[column]
            for column in (
                "class_0_pixel_count",
                "class_1_pixel_count",
                "ignore_pixel_count",
            )
        )
        if stored_total != counts["total_pixel_count"]:
            raise RuntimeError(
                "class and ignore counts do not equal total_pixel_count at "
                f"manifest line {line_number}"
            )
        if counts["nodata_pixel_count"] > counts["ignore_pixel_count"]:
            raise RuntimeError(
                "nodata_pixel_count exceeds ignore_pixel_count at manifest line "
                f"{line_number}"
            )

        classified.append(
            ClassifiedChip(
                **identities,
                counts=counts,
                class_presence=_classify(
                    counts["class_0_pixel_count"],
                    counts["class_1_pixel_count"],
                    counts["nodata_pixel_count"],
                ),
            )
        )
    return classified


def _sample_rank(seed: int, chip: ClassifiedChip) -> bytes:
    payload = "\0".join(
        (
            str(seed),
            chip.region_id,
            chip.source_tiff_id,
            chip.class_presence,
            chip.chip_id,
        )
    )
    return hashlib.sha256(payload.encode()).digest()


def _fractional_background_ids(
    chips: list[ClassifiedChip], fraction: Decimal, seed: int
) -> set[str]:
    groups: dict[tuple[str, str, str], list[ClassifiedChip]] = defaultdict(list)
    for chip in chips:
        if chip.class_presence in BACKGROUND_CLASS_PRESENCE:
            groups[(chip.region_id, chip.source_tiff_id, chip.class_presence)].append(
                chip
            )

    selected_ids: set[str] = set()
    for group in groups.values():
        retain_count = int(Decimal(len(group)) * fraction)
        ranked = sorted(
            group,
            key=lambda chip: (
                _sample_rank(seed, chip),
                chip.chip_id.casefold(),
                chip.chip_id,
            ),
        )
        selected_ids.update(chip.chip_id for chip in ranked[:retain_count])
    return selected_ids


def _selection_rows(
    chips: list[ClassifiedChip],
    *,
    policy: str,
    fraction: Decimal | None,
    seed: int,
) -> list[dict[str, str]]:
    fraction_text = "" if fraction is None else _decimal_text(fraction)
    seed_text = "" if fraction is None else str(seed)
    fractional_ids = (
        set() if fraction is None else _fractional_background_ids(chips, fraction, seed)
    )
    output: list[dict[str, str]] = []
    for chip in chips:
        if chip.class_presence == "positive":
            selected = True
            reason = "positive"
        elif policy == "exclude_all":
            selected = False
            reason = f"excluded_{chip.class_presence}"
        elif chip.chip_id in fractional_ids:
            selected = True
            reason = f"retained_{chip.class_presence}_fraction"
        else:
            selected = False
            reason = f"excluded_{chip.class_presence}_fraction"
        output.append(
            {
                "chip_id": chip.chip_id,
                "source_tiff_id": chip.source_tiff_id,
                "region_id": chip.region_id,
                **{
                    column: str(chip.counts[column])
                    for column in PIXEL_COLUMNS
                    if column != "total_pixel_count"
                },
                "class_presence": chip.class_presence,
                "selected_for_training": str(selected).lower(),
                "selection_reason": reason,
                "policy": policy,
                "retain_fraction": fraction_text,
                "seed": seed_text,
            }
        )
    return output


def _empty_summary_counts() -> dict[str, int]:
    return {
        "chip_count": 0,
        "selected_chip_count": 0,
        "excluded_chip_count": 0,
        **{column: 0 for column in PIXEL_COLUMNS},
        **{f"selected_{column}": 0 for column in PIXEL_COLUMNS},
        **{f"excluded_{column}": 0 for column in PIXEL_COLUMNS},
    }


def _summary_rows(
    chips: list[ClassifiedChip],
    selection_rows: list[dict[str, str]],
    *,
    policy: str,
    fraction: Decimal | None,
    seed: int,
) -> list[dict[str, str | int]]:
    selected_by_id = {
        row["chip_id"]: row["selected_for_training"] == "true" for row in selection_rows
    }
    regions = sorted({chip.region_id for chip in chips})
    sources = sorted({(chip.region_id, chip.source_tiff_id) for chip in chips})
    scope_keys = [
        ("global", "", ""),
        *(("region", region_id, "") for region_id in regions),
        *(("source_tiff", region_id, source_id) for region_id, source_id in sources),
    ]
    summaries: dict[tuple[str, str, str, str], dict[str, int]] = {}
    for scope, region_id, source_id in scope_keys:
        for class_presence in CLASS_PRESENCE_ORDER:
            summaries[(scope, region_id, source_id, class_presence)] = (
                _empty_summary_counts()
            )

    for chip in chips:
        selected = selected_by_id[chip.chip_id]
        keys = [
            ("global", "", "", chip.class_presence),
            ("region", chip.region_id, "", chip.class_presence),
            (
                "source_tiff",
                chip.region_id,
                chip.source_tiff_id,
                chip.class_presence,
            ),
        ]
        for key in keys:
            values = summaries[key]
            values["chip_count"] += 1
            chip_count_key = (
                "selected_chip_count" if selected else "excluded_chip_count"
            )
            values[chip_count_key] += 1
            for column in PIXEL_COLUMNS:
                count = chip.counts[column]
                values[column] += count
                prefix = "selected" if selected else "excluded"
                values[f"{prefix}_{column}"] += count

    fraction_text = "" if fraction is None else _decimal_text(fraction)
    seed_text = "" if fraction is None else str(seed)
    output: list[dict[str, str | int]] = []
    for scope, region_id, source_id in scope_keys:
        for class_presence in CLASS_PRESENCE_ORDER:
            output.append(
                {
                    "scope": scope,
                    "region_id": region_id,
                    "source_tiff_id": source_id,
                    "class_presence": class_presence,
                    **summaries[(scope, region_id, source_id, class_presence)],
                    "policy": policy,
                    "retain_fraction": fraction_text,
                    "seed": seed_text,
                }
            )
    return output


def select_training_chips(
    manifest: Path,
    *,
    policy: str,
    retain_fraction: str | Decimal | float | int | None = None,
    seed: int = 0,
) -> tuple[list[dict[str, str]], list[dict[str, str | int]]]:
    """Return one selection row per manifest chip plus auditable summaries."""
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {sorted(POLICIES)}")
    if policy == "exclude_all":
        if retain_fraction is not None:
            raise ValueError("--retain-fraction is only valid with retain_fraction")
        fraction = None
    else:
        if retain_fraction is None:
            raise ValueError("--retain-fraction is required with retain_fraction")
        fraction = parse_retain_fraction(retain_fraction)

    chips = _read_and_classify_manifest(manifest)
    selections = _selection_rows(
        chips,
        policy=policy,
        fraction=fraction,
        seed=seed,
    )
    summaries = _summary_rows(
        chips,
        selections,
        policy=policy,
        fraction=fraction,
        seed=seed,
    )
    return selections, summaries


def _temporary_path(path: Path) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(descriptor)
    return Path(name)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv_atomic(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
    *,
    overwrite: bool,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(path)
    try:
        with temporary.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())
        if path.exists() and not overwrite:
            if _sha256(path) == _sha256(temporary):
                return
            raise FileExistsError(
                f"Refusing to overwrite existing artifact with different content: {path}"
            )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _default_summary_path(output_manifest: Path) -> Path:
    return output_manifest.with_name(f"{output_manifest.stem}_summary.csv")


def build_training_selection(
    manifest: Path,
    *,
    policy: str,
    output_manifest: Path | None,
    summary_output: Path,
    retain_fraction: str | Decimal | float | int | None = None,
    seed: int = 0,
    overwrite: bool = False,
) -> SelectionResult:
    """Classify manifest rows and atomically write selection/report artifacts."""
    manifest_resolved = manifest.resolve()
    targets = [summary_output, *([] if output_manifest is None else [output_manifest])]
    if len({path.resolve() for path in targets}) != len(targets):
        raise RuntimeError("Selection and summary outputs must be different paths")
    if any(path.resolve() == manifest_resolved for path in targets):
        raise RuntimeError("Refusing to replace the canonical input manifest")

    selections, summaries = select_training_chips(
        manifest,
        policy=policy,
        retain_fraction=retain_fraction,
        seed=seed,
    )
    _write_csv_atomic(
        summary_output,
        summaries,
        SUMMARY_COLUMNS,
        overwrite=overwrite,
    )
    if output_manifest is not None:
        _write_csv_atomic(
            output_manifest,
            selections,
            SELECTION_COLUMNS,
            overwrite=overwrite,
        )

    selected_count = sum(row["selected_for_training"] == "true" for row in selections)
    if policy == "exclude_all":
        fraction_text = ""
    else:
        if retain_fraction is None:
            raise AssertionError("retain_fraction validation did not run")
        fraction_text = _decimal_text(parse_retain_fraction(retain_fraction))
    return SelectionResult(
        policy=policy,
        retain_fraction=fraction_text,
        seed="" if policy == "exclude_all" else str(seed),
        total_count=len(selections),
        selected_count=selected_count,
        excluded_count=len(selections) - selected_count,
        output_manifest=output_manifest,
        summary_output=summary_output,
    )


def remove_bg_only_tiles(input_dir: Path) -> None:
    """Reject the historical destructive API without touching ``input_dir``."""
    raise RuntimeError(
        "Destructive background deletion has been removed. Use "
        "build_training_selection() or the manifest-driven CLI instead; no files "
        f"were changed under {input_dir}."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a non-destructive training selection from chip counts."
    )
    parser.add_argument(
        "legacy_input_dir",
        nargs="?",
        type=Path,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-manifest", type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--policy", choices=sorted(POLICIES))
    parser.add_argument("--retain-fraction", type=_argparse_fraction)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Write only the required summary report, not a selection manifest.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace differing generated outputs.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.legacy_input_dir is not None:
        parser.error(
            "the positional destructive directory mode was removed; use "
            "--manifest, --policy, and --output-manifest"
        )
    if args.manifest is None:
        parser.error("--manifest is required")
    if args.policy is None:
        parser.error("--policy is required")
    if args.report_only:
        if args.output_manifest is not None:
            parser.error("--output-manifest cannot be used with --report-only")
        if args.summary_output is None:
            parser.error("--summary-output is required with --report-only")
        output_manifest = None
        summary_output = args.summary_output
    else:
        if args.output_manifest is None:
            parser.error("--output-manifest is required unless --report-only is used")
        output_manifest = args.output_manifest
        summary_output = args.summary_output or _default_summary_path(output_manifest)

    try:
        result = build_training_selection(
            args.manifest,
            policy=args.policy,
            output_manifest=output_manifest,
            summary_output=summary_output,
            retain_fraction=args.retain_fraction,
            seed=args.seed,
            overwrite=args.overwrite,
        )
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(
        f"Training selection: policy={result.policy}, total={result.total_count}, "
        f"selected={result.selected_count}, excluded={result.excluded_count}"
    )
    if result.output_manifest is not None:
        print(f"Selection manifest: {result.output_manifest}")
    print(f"Summary: {result.summary_output}")


if __name__ == "__main__":
    main()
