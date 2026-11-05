"""Select and render bounded qualitative examples from a scored source canvas."""

from pathlib import Path

import numpy as np

from kelpseg.reporting.views import example


def write_examples(
    canvas: dict,
    windows: list[dict],
    selected: set[str],
    scope: str,
    output: Path,
    examples: list[dict],
    threshold: float,
    limit: int,
    seen_regions: set[str],
    background_sources: set[str],
) -> None:
    """Write selected figures, appending captions and updating TIFF selection sets.

    Chip selections are recorded payload paths. TIFF selections include the first
    observed source per region and at most two zero-kelp sources. The figure limit
    affects display only; source and background scoring happen independently.
    """
    if len(examples) >= limit:
        return
    source = canvas["source"]
    labels, probability = canvas["labels"], canvas["probability"]
    top, left = int(source.get("row_offset") or 0), int(source.get("col_offset") or 0)
    candidates = []
    if scope == "chip_disjoint":
        for row in windows:
            y, x = int(row["original_row"]) - top, int(row["original_col"]) - left
            h, w = int(row["height"]), int(row["width"])
            if row["payload"] in selected:
                candidates.append((y, x, h, w))
    else:
        valid = (labels != -100) & np.isfinite(probability)
        positive = valid & (labels == 1)
        region_id = source.get("region_id", "")
        has_kelp = positive.any()
        extra_background = not has_kelp and valid.any() and len(background_sources) < 2
        if region_id not in seen_regions or extra_background:
            observed = positive if has_kelp else valid
            if observed.any():
                cy, cx = np.unravel_index(np.argmax(observed), observed.shape)
                h, w = min(512, labels.shape[0]), min(512, labels.shape[1])
                y = min(max(int(cy) - h // 2, 0), labels.shape[0] - h)
                x = min(max(int(cx) - w // 2, 0), labels.shape[1] - w)
                candidates.append((y, x, h, w))
                seen_regions.add(region_id)
                if not has_kelp:
                    background_sources.add(source["source_key"])
    for y, x, h, w in candidates:
        if len(examples) >= limit:
            break
        filename = f"examples/{len(examples):02d}.png"
        caption = f"{source.get('original_source_id') or source['source_key']} | region {source.get('region_id') or 'unknown'} | {source.get('acquisition_date') or 'unknown date'} | r{y + top} c{x + left}"
        region = np.s_[y : y + h, x : x + w]
        bands = source["band_names"].split(";")
        if not {"nir", "red", "green"}.issubset(bands):
            raise ValueError(
                "False-color reports require native nir, red and green imagery."
            )
        example(
            output / filename,
            canvas["image"][region],
            bands,
            labels[region],
            probability[region],
            caption,
            threshold,
        )
        examples.append(dict(file=filename, caption=caption))
