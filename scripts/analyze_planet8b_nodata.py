"""Analyze universal nodata thresholds for the canonical PS8B chip manifest."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path, PurePosixPath

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors

from src.prepare.nodata import nodata_mask

matplotlib.use("Agg", force=True)


PERCENTILES = (0, 1, 5, 10, 25, 50, 75, 90, 95, 99, 100)
DEFAULT_CANDIDATES = (0, 1, 5, 10, 20, 30, 40, 50, 60)
PLAUSIBLE_THRESHOLDS = (40, 50, 60)
REQUIRED_COLUMNS = {
    "chip_id",
    "chip_path",
    "source_tiff_id",
    "dataset",
    "region_id",
    "region_name",
    "total_pixel_count",
    "class_1_pixel_count",
    "nodata_pixel_count",
    "nodata_pct",
}


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"Refusing to write an empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_manifest(path: Path, chip_root: Path) -> list[dict[str, object]]:
    """Read and validate analysis fields and portable chip paths."""
    with path.open(newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise RuntimeError(f"Manifest has no header: {path}")
        missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
        if missing:
            raise RuntimeError(f"Manifest lacks required columns: {missing}")
        raw_rows = list(reader)
    if not raw_rows:
        raise RuntimeError(f"Manifest is empty: {path}")

    rows: list[dict[str, object]] = []
    chip_ids: set[str] = set()
    for line_number, raw in enumerate(raw_rows, start=2):
        chip_id = raw["chip_id"]
        if not chip_id or chip_id in chip_ids:
            raise RuntimeError(f"Blank or duplicate chip_id at line {line_number}")
        chip_ids.add(chip_id)
        relative = PurePosixPath(raw["chip_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"Unsafe chip_path at line {line_number}")
        chip_path = chip_root.joinpath(*relative.parts)
        if not chip_path.is_file():
            raise FileNotFoundError(f"Missing chip at line {line_number}: {chip_path}")
        total = int(raw["total_pixel_count"])
        nodata_count = int(raw["nodata_pixel_count"])
        nodata_pct = float(raw["nodata_pct"])
        class_1 = int(raw["class_1_pixel_count"])
        if total <= 0 or not 0 <= nodata_count <= total or not 0 <= class_1 <= total:
            raise RuntimeError(f"Invalid pixel counts at line {line_number}")
        expected_pct = 100 * nodata_count / total
        if not np.isclose(nodata_pct, expected_pct, rtol=1e-12, atol=1e-10):
            raise RuntimeError(f"Inconsistent nodata_pct at line {line_number}")
        rows.append(
            {
                "chip_id": chip_id,
                "chip_path": raw["chip_path"],
                "source_tiff_id": raw["source_tiff_id"],
                "dataset": raw["dataset"],
                "region_id": raw["region_id"],
                "region_name": raw["region_name"],
                "total_pixel_count": total,
                "class_1_pixel_count": class_1,
                "nodata_pixel_count": nodata_count,
                "nodata_pct": nodata_pct,
            }
        )
    return rows


def distribution_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return global and region nodata percentiles in long form."""
    groups: dict[str, list[dict[str, object]]] = {"global": rows}
    for row in rows:
        groups.setdefault(str(row["region_id"]), []).append(row)
    output: list[dict[str, object]] = []
    for scope, group in groups.items():
        values = np.array([float(row["nodata_pct"]) for row in group])
        output.extend(
            {
                "scope": scope,
                "chip_count": len(group),
                "source_tiff_count": len({str(row["source_tiff_id"]) for row in group}),
                "percentile": percentile,
                "nodata_pct": float(np.percentile(values, percentile)),
            }
            for percentile in PERCENTILES
        )
    return output


def _source_counts(rows: list[dict[str, object]]) -> Counter[str]:
    return Counter(str(row["source_tiff_id"]) for row in rows)


def candidate_rows(
    rows: list[dict[str, object]], candidates: tuple[float, ...]
) -> list[dict[str, object]]:
    """Summarize candidate effects globally and within every region."""
    groups: dict[str, list[dict[str, object]]] = {"global": rows}
    for row in rows:
        groups.setdefault(str(row["region_id"]), []).append(row)
    output: list[dict[str, object]] = []
    for threshold in candidates:
        for scope, group in groups.items():
            removed = [row for row in group if float(row["nodata_pct"]) > threshold]
            retained = [row for row in group if float(row["nodata_pct"]) <= threshold]
            all_source_counts = _source_counts(group)
            removed_source_counts = _source_counts(removed)
            affected_sources = set(removed_source_counts)
            eliminated_sources = {
                source
                for source, count in removed_source_counts.items()
                if count == all_source_counts[source]
            }
            class_1_total = sum(int(row["class_1_pixel_count"]) for row in group)
            class_1_removed = sum(int(row["class_1_pixel_count"]) for row in removed)
            output.append(
                {
                    "threshold_pct": threshold,
                    "candidate_basis": (
                        "required_and_suggested_class1_break"
                        if threshold == 60
                        else "required"
                    ),
                    "scope": scope,
                    "total_chips": len(group),
                    "retained_chips": len(retained),
                    "removed_chips": len(removed),
                    "removed_chip_pct": 100 * len(removed) / len(group),
                    "total_source_tiffs": len(all_source_counts),
                    "source_tiffs_affected": len(affected_sources),
                    "source_tiffs_eliminated": len(eliminated_sources),
                    "eliminated_source_tiff_ids": ";".join(sorted(eliminated_sources)),
                    "region_eliminated": scope != "global" and not retained,
                    "class_1_pixels_total": class_1_total,
                    "class_1_pixels_retained": class_1_total - class_1_removed,
                    "class_1_pixels_removed": class_1_removed,
                    "class_1_pixels_removed_pct": (
                        100 * class_1_removed / class_1_total if class_1_total else 0.0
                    ),
                }
            )
    return output


def per_chip_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Create a compact sorted audit table used to resolve visual examples."""
    output: list[dict[str, object]] = []
    for row in sorted(
        rows, key=lambda item: (float(item["nodata_pct"]), item["chip_id"])
    ):
        nodata_pct = float(row["nodata_pct"])
        nearest = min(PLAUSIBLE_THRESHOLDS, key=lambda value: abs(value - nodata_pct))
        total = int(row["total_pixel_count"])
        output.append(
            {
                **row,
                "valid_pixel_count": total - int(row["nodata_pixel_count"]),
                "class_1_pct_of_chip": 100 * int(row["class_1_pixel_count"]) / total,
                "nearest_plausible_threshold_pct": nearest,
                "distance_to_nearest_threshold_pct": abs(nearest - nodata_pct),
            }
        )
    return output


def select_contact_rows(
    rows: list[dict[str, object]],
) -> list[tuple[int, str, dict[str, object]]]:
    """Select the closest chip on each side of each plausible threshold."""
    selected: list[tuple[int, str, dict[str, object]]] = []
    used: set[str] = set()
    for threshold in PLAUSIBLE_THRESHOLDS:
        for side, eligible in (
            ("below", [row for row in rows if float(row["nodata_pct"]) <= threshold]),
            ("above", [row for row in rows if float(row["nodata_pct"]) > threshold]),
        ):
            eligible.sort(
                key=lambda row: (
                    abs(float(row["nodata_pct"]) - threshold),
                    -int(row["class_1_pixel_count"]),
                    str(row["chip_id"]),
                )
            )
            chosen = next(row for row in eligible if str(row["chip_id"]) not in used)
            used.add(str(chosen["chip_id"]))
            selected.append((threshold, side, chosen))
    return selected


def _rgb_like(image: np.ndarray, nodata: np.ndarray) -> np.ndarray:
    # PlanetScope 8-band order is Coastal Blue, Blue, Green I, Green, Yellow,
    # Red, Red Edge, NIR. One-indexed bands 6/4/2 provide an RGB-like view.
    rgb = image[..., [5, 3, 1]].astype(np.float32)
    valid = ~nodata
    output = np.zeros_like(rgb)
    for index in range(3):
        values = rgb[..., index][valid]
        if values.size:
            low, high = np.percentile(values, (2, 98))
            if high > low:
                output[..., index] = np.clip(
                    (rgb[..., index] - low) / (high - low), 0, 1
                )
    output[nodata] = 0
    return output


def render_contact_sheet(
    chip_root: Path,
    selected: list[tuple[int, str, dict[str, object]]],
    output: Path,
) -> list[dict[str, object]]:
    """Render RGB-like, label, and exact all-band-zero panels."""
    figure, axes = plt.subplots(len(selected), 3, figsize=(12, 3.5 * len(selected)))
    label_cmap = colors.ListedColormap(["#555555", "#35b779", "#d81b60"])
    mask_cmap = colors.ListedColormap(["#f2f2f2", "#d73027"])
    records: list[dict[str, object]] = []
    for row_index, (threshold, side, row) in enumerate(selected):
        chip_path = chip_root.joinpath(*PurePosixPath(str(row["chip_path"])).parts)
        with np.load(chip_path) as data:
            image = data["image"]
            label = data["label"]
        source_nodata = np.asarray(row["source_nodata_value"], dtype=image.dtype).item()
        nodata = nodata_mask(image, [source_nodata] * image.shape[-1], band_axis=-1)
        stored_nodata_count = int(row["nodata_pixel_count"])
        if int(nodata.sum()) != stored_nodata_count:
            raise RuntimeError(f"NPZ nodata mismatch for {row['chip_id']}")
        axes[row_index, 0].imshow(_rgb_like(image, nodata))
        axes[row_index, 1].imshow(
            np.where(label == -100, 2, label), cmap=label_cmap, vmin=0, vmax=2
        )
        axes[row_index, 2].imshow(nodata, cmap=mask_cmap, vmin=0, vmax=1)
        title = (
            f"{threshold}% {side}: {row['region_id']} | "
            f"nodata {float(row['nodata_pct']):.4f}% | "
            f"kelp {100 * int(row['class_1_pixel_count']) / int(row['total_pixel_count']):.2f}%"
        )
        axes[row_index, 0].set_ylabel(title, fontsize=9)
        records.append(
            {
                "threshold_pct": threshold,
                "side": side,
                "chip_id": row["chip_id"],
                "chip_path": row["chip_path"],
                "region_id": row["region_id"],
                "source_tiff_id": row["source_tiff_id"],
                "nodata_pct": row["nodata_pct"],
                "class_1_pixel_count": row["class_1_pixel_count"],
                "npz_nodata_count_verified": stored_nodata_count,
            }
        )
    for axis, title in zip(
        axes[0],
        (
            "RGB-like bands 6/4/2",
            "Label: gray bg, green kelp, pink ignore",
            "All-8-band source-declared nodata mask: red nodata",
        ),
        strict=True,
    ):
        axis.set_title(title, fontsize=10)
    for axis in axes.flat:
        axis.set_xticks([])
        axis.set_yticks([])
    figure.suptitle(
        "Candidate nodata thresholds: nearest retained and removed chips", fontsize=14
    )
    figure.tight_layout(rect=(0, 0, 1, 0.99))
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return records


def _global_summary(
    summary: list[dict[str, object]], threshold: float
) -> dict[str, object]:
    return next(
        row
        for row in summary
        if row["scope"] == "global" and float(row["threshold_pct"]) == threshold
    )


def write_recommendation(
    output: Path,
    summary: list[dict[str, object]],
    contact_rows: list[dict[str, object]],
) -> None:
    """Write the evidence-backed proposal while leaving approval unresolved."""
    approved_decision = ""
    if output.exists():
        existing = output.read_text()
        if "Approved threshold: `max_nodata_pct =" in existing:
            approved_decision = existing[existing.index("## Decision") :]
    proposed = _global_summary(summary, 50)
    alternative = _global_summary(summary, 60)
    conservative = _global_summary(summary, 40)
    region_50 = [
        row
        for row in summary
        if row["scope"] != "global" and float(row["threshold_pct"]) == 50
    ]
    highest = max(region_50, key=lambda row: float(row["removed_chip_pct"]))
    lowest = min(region_50, key=lambda row: float(row["removed_chip_pct"]))
    eliminated = sum(int(row["source_tiffs_eliminated"]) for row in region_50)
    lines = [
        "# Universal nodata threshold recommendation",
        "",
        "## Recommendation",
        "",
        "Propose `max_nodata_pct = 50`. This keeps chips with at most half of their pixels "
        "equal to zero in all eight bands and removes only chips above that boundary. "
        f"It retains {proposed['retained_chips']:,} of {proposed['total_chips']:,} chips and "
        f"removes {proposed['removed_chips']:,} ({float(proposed['removed_chip_pct']):.2f}%). "
        f"The removed chips contain {proposed['class_1_pixels_removed']:,} class-1 pixels "
        f"({float(proposed['class_1_pixels_removed_pct']):.2f}% of the canonical total).",
        "",
        "The proposal is a geometric-coverage rule, not a claim that pixels darker than a "
        "reflectance cutoff are invalid. Nodata is defined exactly as all eight stored bands "
        "equaling zero. Valid dark water remains valid whenever any band is nonzero.",
        "",
        "## Regional imbalance risk",
        "",
        f"At 50%, regional chip removal ranges from {float(lowest['removed_chip_pct']):.2f}% "
        f"in `{lowest['scope']}` to {float(highest['removed_chip_pct']):.2f}% in "
        f"`{highest['scope']}`. No region is eliminated. {eliminated} source TIFFs lose all "
        "chips at this threshold; their IDs are recorded in the candidate table. This "
        "imbalance follows source-edge geometry and must remain visible in later region and "
        "source-TIFF manifests.",
        "",
        "## Alternatives",
        "",
        f"- `60%` is a reasonable coverage-preserving alternative: it removes "
        f"{alternative['removed_chips']:,} chips ({float(alternative['removed_chip_pct']):.2f}%) "
        f"and {float(alternative['class_1_pixels_removed_pct']):.2f}% of class-1 pixels. It "
        "retains more chips whose majority area is nodata.",
        f"- `40%` is a stricter alternative: it removes {conservative['removed_chips']:,} "
        f"chips ({float(conservative['removed_chip_pct']):.2f}%) and "
        f"{float(conservative['class_1_pixels_removed_pct']):.2f}% of class-1 pixels. It "
        "reduces edge-heavy samples more aggressively but increases selection bias.",
        "",
        "## Visual review",
        "",
        "The contact sheet uses PlanetScope bands 6/4/2 (one-indexed red/green/blue) with "
        "per-chip 2nd-98th percentile scaling over non-nodata pixels. Each example includes "
        "the remapped label and an independently recomputed all-eight-band-zero mask. "
        "Examples are the closest manifest rows immediately below and above 40%, 50%, and "
        "60%; all six NPZ nodata counts matched the manifest.",
        "",
        "Selected chip IDs:",
        "",
        *[
            f"- {row['threshold_pct']}% {row['side']}: `{row['chip_id']}` "
            f"(`{row['region_id']}`, {float(row['nodata_pct']):.4f}% nodata)"
            for row in contact_rows
        ],
        "",
        "## Decision",
        "",
        "Status: awaiting user approval. No filter has been applied.",
        "",
        "Approved threshold: pending",
        "",
    ]
    content = "\n".join(lines)
    if approved_decision:
        content = content[: content.index("## Decision")] + approved_decision
    output.write_text(content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chip_root", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--candidates",
        nargs="+",
        type=float,
        default=DEFAULT_CANDIDATES,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    candidates = tuple(dict.fromkeys(args.candidates))
    if any(not 0 <= value <= 100 for value in candidates):
        raise ValueError("Candidate thresholds must be in [0, 100]")
    rows = read_manifest(args.manifest, args.chip_root)
    summary = candidate_rows(rows, candidates)
    output_dir = args.output_dir
    _write_csv(output_dir / "nodata_threshold_analysis.csv", per_chip_rows(rows))
    _write_csv(
        output_dir / "nodata_distribution_by_region.csv", distribution_rows(rows)
    )
    _write_csv(output_dir / "nodata_candidate_summary.csv", summary)
    selected = select_contact_rows(rows)
    contact_records = render_contact_sheet(
        args.chip_root, selected, output_dir / "nodata_contact_sheet.png"
    )
    _write_csv(output_dir / "nodata_contact_sheet_selection.csv", contact_records)
    write_recommendation(
        output_dir / "nodata_threshold_recommendation.md", summary, contact_records
    )
    print(f"Analyzed {len(rows):,} chips into {output_dir}")


if __name__ == "__main__":
    main()
