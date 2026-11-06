"""Count label support by shore distance on explicit, unique-pixel footprints."""

import json
import logging
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from kelpseg.reporting.canvases import source_groups
from kelpseg.reporting.report import write_csv
from kelpseg.reporting.shore_clusters import cluster_source, write_cluster_ids
from kelpseg.reporting.shore_clusters_summary import (
    cluster_plot,
    pool_cluster_bands,
    pool_correlations,
)
from kelpseg.reporting.shore_distance import (
    NEARSHORE_CUTOFF_M,
    pixel_area_m2,
    read_shore_canvas,
)
from kelpseg.reporting.shore_exposure import (
    SMALL_CLUSTER_MAX_PIXELS,
    exposure_summary,
    exposure_windows,
)
from kelpseg.reporting.shore_inventory_counts import (
    add_fractions,
    band_counts,
    cumulative_counts,
    empty_region_groups,
    inventory_footprints,
    pool_inventory,
)
from kelpseg.reporting.shore_inventory_inputs import (
    ShoreInventorySettings,
    read_inventory_inputs,
    read_label_canvas,
)
from kelpseg.reporting.shore_inventory_views import write_inventory_views

logger = logging.getLogger(__name__)


def shore_inventory(settings: ShoreInventorySettings) -> Path:
    """Write label-only inventory tables and HTML into a fresh output directory."""
    if settings.output.exists():
        raise ValueError(
            f"Output already exists; choose a fresh directory: {settings.output}"
        )
    shore, sources, windows = read_inventory_inputs(settings)
    grouped = source_groups(sources)
    by_source = defaultdict(list)
    for window in windows:
        by_source[window["source_key"]].append(window)
    settings.output.mkdir(parents=True)
    rows, cumulative, coverage = [], [], []
    clusters, cluster_bands, cluster_moments, cluster_sources = [], [], [], []
    training_exposure = []
    (settings.output / "cluster_ids").mkdir()
    for index, group in enumerate(grouped, 1):
        logger.info(
            "Inventory source %d/%d: %s",
            index,
            len(grouped),
            group[0]["original_source_id"],
        )
        canvas = read_label_canvas(group, settings.label_mapping)
        land, distance = read_shore_canvas(settings.shoreline, shore, canvas)
        selected = [
            window for source in group for window in by_source[source["source_key"]]
        ]
        masks = inventory_footprints(canvas, selected, settings.training_positive_only)
        source = canvas["source"]
        identity = {
            name: source[name]
            for name in (
                "dataset_id",
                "release_id",
                "source_id",
                "acquisition_date",
                "split",
                "source_keys",
                "band_names",
            )
        }
        identity.update(
            region=source["region_id"],
            experiment=settings.experiment,
            variant=settings.variant,
        )
        area = pixel_area_m2(canvas["crs"], canvas["transform"])
        cap = min(
            float(shore[key]["cap_m"]) for key in source["source_keys"].split(";")
        )
        ids, components, bands, correlations = cluster_source(
            canvas, land, distance, area, cap, settings.distance_edges
        )
        cluster_path = Path("cluster_ids") / f"{source['source_id']}.tif"
        write_cluster_ids(settings.output / cluster_path, ids, canvas)
        cluster_sources.append(
            dict(
                identity,
                cluster_ids=str(cluster_path),
                clusters=len(components),
                truncated_clusters=sum(row["truncated"] for row in components),
                cap_m=cap,
            )
        )
        clusters.extend(dict(identity, **row) for row in components)
        cluster_bands.extend(dict(identity, **row) for row in bands)
        cluster_moments.extend(dict(identity, **row) for row in correlations)
        training_exposure.extend(
            dict(identity, **row)
            for row in exposure_windows(
                canvas,
                selected,
                ids,
                components,
                land,
                distance,
                settings.training_positive_only,
            )
        )
        del ids
        for scope, mask in masks.items():
            identity_scope = dict(identity, scope=scope)
            rows.extend(
                dict(identity_scope, **add_fractions(item))
                for item in band_counts(
                    canvas["labels"],
                    mask,
                    land,
                    distance,
                    settings.distance_edges,
                    area,
                )
            )
            cumulative.extend(
                dict(identity_scope, **item)
                for item in cumulative_counts(
                    canvas["labels"],
                    mask,
                    land,
                    distance,
                    settings.distance_edges[1:],
                    area,
                )
            )
            coverage.append(
                dict(
                    identity_scope,
                    footprint_pixels=int(mask.sum()),
                    native_valid_pixels=int((mask & canvas["valid"]).sum()),
                    ignored_valid_pixels=int(
                        (mask & canvas["valid"] & (canvas["labels"] == -100)).sum()
                    ),
                    labeled_pixels=int((mask & (canvas["labels"] != -100)).sum()),
                )
            )
    region_keys = ("experiment", "variant", "region", "split", "scope")
    split_keys = ("experiment", "variant", "split", "scope")
    regions = empty_region_groups(
        pool_inventory(rows, (*region_keys, "band")),
        sources,
        "band",
        list(dict.fromkeys(row["band"] for row in rows)),
    )
    splits = pool_inventory(rows, (*split_keys, "band"))
    cumulative_regions = empty_region_groups(
        pool_inventory(cumulative, (*region_keys, "cutoff_m")),
        sources,
        "cutoff_m",
        sorted({row["cutoff_m"] for row in cumulative}),
    )
    cumulative_splits = pool_inventory(cumulative, (*split_keys, "cutoff_m"))
    for name, records in (
        ("source_bands", rows),
        ("region_bands", regions),
        ("split_bands", splits),
        ("source_coverage", coverage),
        ("cumulative_regions", cumulative_regions),
        ("cumulative_splits", cumulative_splits),
    ):
        write_csv(settings.output / f"{name}.csv", records)
    cluster_regions = pool_cluster_bands(
        cluster_bands,
        ("region", "split", "component_scope", "distance_band", "size_bin"),
    )
    cluster_splits = pool_cluster_bands(
        cluster_bands, ("split", "component_scope", "distance_band", "size_bin")
    )
    correlation_groups = ("component_scope", "weighting", "cap_m")
    correlations = []
    for level, keys in (
        ("source", ("source_id", "region", "split")),
        ("region_split", ("region", "split")),
        ("split", ("split",)),
        ("global", ()),
    ):
        correlations.extend(
            pool_correlations(cluster_moments, (*keys, *correlation_groups), level)
        )
    for name, records in (
        ("clusters", clusters),
        ("cluster_sources", cluster_sources),
        ("cluster_distance_sources", cluster_bands),
        ("cluster_distance_regions", cluster_regions),
        ("cluster_distance_splits", cluster_splits),
        ("cluster_correlations", correlations),
    ):
        write_csv(settings.output / f"{name}.csv", records)
    exposure = exposure_summary(
        training_exposure,
        [row["region_id"] for row in sources if row["split"] == "train"],
    )
    write_csv(settings.output / "exposure_windows.csv", training_exposure)
    write_csv(settings.output / "exposure_summary.csv", exposure)
    cluster_plot(settings.output / "cluster_distance.png", cluster_splits)
    write_inventory_views(
        settings.output, regions, splits, cumulative_regions, cumulative_splits
    )
    resolved = {
        name: str(value) if isinstance(value, Path) else value
        for name, value in asdict(settings).items()
    }
    summary = dict(
        status="complete",
        original_sources=len(grouped),
        source_crops=len(sources),
        experiment=settings.experiment,
        variant=settings.variant,
        distance_edges=settings.distance_edges,
        nearshore_cutoff_m=NEARSHORE_CUTOFF_M,
        cluster_analysis=dict(
            scope="full_source",
            connectivity=8,
            clusters=len(clusters),
            truncated_clusters=sum(row["truncated"] for row in clusters),
            correlation="Pearson distance versus log10(full observed cluster area); uncapped ocean kelp only",
            component_scopes=["all_observed", "interior_only"],
            weightings=["pixel", "cluster"],
        ),
        training_exposure=dict(
            sampler="uniform shuffled eligible windows, without replacement, no drop-last",
            eligible_windows=len(training_exposure),
            full_epoch_draws=len(training_exposure),
            nearshore_cutoff_m=NEARSHORE_CUTOFF_M,
            small_cluster_max_pixels=SMALL_CLUSTER_MAX_PIXELS,
            stage="Preaugmentation; overlap counted repeatedly; not loss-weighted exposure",
            scope="Training windows in the declared inventory source subset",
        ),
        training_positive_only=settings.training_positive_only,
        claim="Observed labeled area summed over acquisitions; not unique habitat area or optimizer exposure.",
        scope="Explicit shoreline source subset joined to source assignments; no model predictions.",
    )
    for name, document in (("settings", resolved), ("summary", summary)):
        temporary = settings.output / f"{name}.tmp"
        temporary.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")
        temporary.replace(settings.output / f"{name}.json")
    logger.info("Inventory complete: %s", settings.output / "report.html")
    return settings.output / "report.html"
