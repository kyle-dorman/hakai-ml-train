"""Summarize proportional canopy change from one saved labeled evaluation report."""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from kelpseg.reporting.canvases import canvases, source_groups
from kelpseg.reporting.inputs import ReportSettings, read_csv
from kelpseg.reporting.report import write_csv
from kelpseg.reporting.temporal_inputs import (
    TemporalSettings,
    read_report,
    select_pairs,
)
from kelpseg.reporting.temporal_pairs import compare_pair, unavailable_pair
from kelpseg.reporting.temporal_summary import summarize_pairs, summarize_sources
from kelpseg.reporting.temporal_views import write_temporal_report

logger = logging.getLogger(__name__)


def temporal_report(settings: TemporalSettings) -> Path:
    """Write tables and figures sequentially into a fresh external output directory.

    Group saved source tables first, then load at most two original-source
    canvases per pair using the existing chip/TIFF readers. No model is loaded.
    Unsupported pairs retain reasons; failures stop without partial-work reuse.
    """
    output = settings.output
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a fresh directory.")
    source_summary, rows = read_report(settings)
    tables = summarize_sources(rows)
    pairs = select_pairs(rows, settings)
    logger.info(
        "Temporal report: %s; scope %s/%s; %d sources, %d candidate pairs; output %s",
        settings.report,
        source_summary["scope"],
        source_summary["split"],
        len(rows),
        len(pairs),
        output,
    )
    # Completed report references are authoritative; do not replay split audits.
    inputs = read_csv(settings.report / "input_sources.csv")
    windows = read_csv(settings.report / "selected_windows.csv")
    groups = {
        ";".join(sorted(row["source_key"] for row in group)): group
        for group in source_groups(inputs)
    }
    recipe = json.loads((settings.report / "settings.json").read_text())
    reader_settings = ReportSettings(
        predictions=Path(source_summary["predictions"]),
        output=output,
        label_mapping={
            int(key): value for key, value in recipe["label_mapping"].items()
        },
    )
    threshold = source_summary["threshold"]
    output.mkdir(parents=True)
    for number, pair in enumerate(pairs, 1):
        logger.info(
            "Temporal pair %d/%d: %s → %s (%s days)",
            number,
            len(pairs),
            pair["earlier_source"],
            pair["later_source"],
            pair["days"],
        )
        if pair["interval"] not in ("short", "long"):
            pair.update(unavailable_pair(pair["interval"]))
            continue
        loaded = []
        for key in (pair["earlier_source"], pair["later_source"]):
            if key not in groups:
                raise ValueError(f"{key}: source is missing from input_sources.csv.")
            canvas, _ = next(
                canvases(groups[key], windows, source_summary["scope"], reader_settings)
            )
            # RGB/native imagery was needed by the shared loader, not by pair math.
            del canvas["image"]
            loaded.append(canvas)
        pair.update(
            compare_pair(
                loaded[0], loaded[1], threshold, settings.small_baseline_pixels
            )
        )
        del loaded, canvas
    pair_summaries = summarize_pairs(pairs)
    summary = dict(
        status="complete",
        input_report=str(settings.report),
        run_id=source_summary["run_id"],
        model=source_summary["model"],
        scope=source_summary["scope"],
        split=source_summary["split"],
        threshold=threshold,
        membership=source_summary.get("membership"),
        input_coverage=source_summary["coverage"],
        sources=len(rows),
        intervals=dict(
            short=[settings.short_min_days, settings.short_max_days],
            long=[settings.long_min_days, settings.long_max_days],
        ),
        small_baseline_pixels=settings.small_baseline_pixels,
        candidate_pairs=len(pairs),
        supported_pairs=sum(p["status"] == "supported" for p in pairs),
        percentage_defined_pairs=sum(p["change_error_pp"] is not None for p in pairs),
        same_day_pairs=sum(p["interval"] == "same_day" for p in pairs),
        source_exclusions=len(tables["source_exclusions"]),
        percentage_definition="100 * (after - before) / before, separately for labels and predictions; error is prediction minus label in percentage points",
        pairing="Explicit CSV"
        if settings.pairs
        else "All within-location source pairs in inclusive day ranges; same-day records kept separate",
        observation_totals="Counts/areas summed over acquisitions are observation totals, not unique geographic area. Repeated pairs are not independent samples.",
    )
    for name, records in tables.items():
        write_csv(output / f"{name}.csv", records)
    write_csv(output / "sources.csv", rows)
    write_csv(output / "pairs.csv", pairs)
    write_csv(output / "pair_summaries.csv", pair_summaries)
    write_temporal_report(output, summary, tables, pairs, pair_summaries)
    resolved = {
        key: str(value) if isinstance(value, Path) else value
        for key, value in asdict(settings).items()
    }
    for name, record in (("settings", resolved), ("summary", summary)):
        temporary = output / f"{name}.tmp"
        temporary.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
        temporary.replace(output / f"{name}.json")
    logger.info("Temporal report complete: %s", output / "report.html")
    return output / "report.html"
