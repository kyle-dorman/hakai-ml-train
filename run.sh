set -o pipefail

CHIP_ROOT=/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1
mkdir -p "$CHIP_ROOT"

caffeinate -i uv run python -m src.prepare.make_chip_dataset \
  /Volumes/x10pro/kelpseg/merged_all_regions_v1 \
  "$CHIP_ROOT" \
  --splits all \
  --source-manifest /Volumes/x10pro/kelpseg/merged_all_regions_v1/raster_manifest.csv \
  --manifest-output "$CHIP_ROOT/chip_manifest.csv" \
  --size 1024 \
  --stride 512 \
  --num_bands 8 \
  --dtype uint16 \
  --remap 0 1 0 -100 0 \
  --num_workers 0 \
  --resume \
  2>&1 | tee -a "$CHIP_ROOT/chipping.log"

