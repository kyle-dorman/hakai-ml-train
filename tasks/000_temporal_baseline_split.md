# Task 000: Create the temporal baseline split

Status: Complete

## Outcome

Create a deterministic train/validation/test assignment for every source TIFF,
with every region represented and acquisition dates kept intact.

## Completed artifacts

- `planet8b_temporal_image_splits.csv`
- `scripts/create_temporal_baseline_split.py`
- `region_006_007_011_sample_points.geojson`

## Recorded result

- 369 TIFFs across 12 region IDs.
- Train: 247 TIFFs.
- Validation: 68 TIFFs.
- Test: 54 TIFFs.
- All regions have strictly chronological train, validation, and test dates.
- No region-date group crosses a split.

## Important note

The optimizer targets 70/15/15, prefers year boundaries, and then prefers larger
temporal gaps. Strict whole-year splitting was impossible for all regions.

## Validation recorded

- 369 case-insensitively unique source TIFF stems.
- Every region has nonempty train, validation, and test assignments.
- Within every region, the latest train date precedes the earliest validation
  date, which precedes the earliest test date.
- No acquisition-date group within a region crosses splits.
- Global counts: 247 train, 68 validation, 54 test.

## Handoff

Task 001 must reuse this file's region mapping but must not use either split CSV
to decide which raw source pairs are included in the expanded dataset.
