# Tiny researcher walkthrough

Follow this sequence from the repository in the same Bash shell. It fetches
about 83 MB of cleaned tiny-v2 inputs, prepares chips, runs a bounded CPU smoke,
copies its portable model, predicts one validation TIFF, and makes a labeled
report. Allow space for roughly 152 MB of prepared chips plus model/checkpoint
files. This demonstrates execution, not segmentation quality. No production
training or held-out test inference is part of this walkthrough.

The selected research model is the **8-band SegFormer B0, plain BCE plus Dice,
epoch-16 EMA, with BC training data**; see [model details](experiments.md#current-planet-8-band-b0-baseline).
The tiny CPU recipe uses three bands, no downloaded weights and two short
epochs; it is deliberately a smoke recipe rather than that production model.

## 1. Install

Start in a local checkout of this repository. You need access to the project's
UCLA Box folder, [uv](https://docs.astral.sh/uv/getting-started/installation/)
and [rclone](https://rclone.org/install/). Install those tools first, then open
Bash in the repository directory (on a Mac, run `bash` if your terminal uses zsh).
Confirm the tools are available before installing the locked Python environment:

```bash
(
  set -e
  uv --version
  rclone version
  uv python install 3.12
  uv sync --python 3.12 --frozen
  uv run --frozen kelpseg --help
)
```

Configure the authenticated `kelp-box` remote using
[local Box access](box_backup.md#connect-box-on-a-local-machine).
Box access is needed only for the fetch. After installation/fetch, use
`uv run --offline --no-sync` in place of `uv run --frozen` to work offline.

## 2. Fetch the tiny inputs

Choose a fresh artifact root outside Git. Keep this variable set for subsequent
blocks; if a command fails, stop and fix the reported problem before proceeding.
Preparation has no resume or partial-output reuse: choose a fresh destination
for another attempt. The blocks stop on their first error.

```bash
data_root="$HOME/kelpseg-tiny-v2-01"
(
  set -e
  test ! -e "$data_root"
  mkdir -p "$data_root/runs" "$data_root/examples/runs" "$data_root/work"
  rclone copy kelp-box:kelpseg/data/examples/tiny_ca_bc/v2 \
    "$data_root/data/examples/tiny_ca_bc/v2" \
    --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
  cat > "$data_root/work/paths.toml" <<TOML
[paths]
data_root = "$data_root"
runs_root = "$data_root/runs"
TOML
  uv run --frozen kelpseg check-paths --paths "$data_root/work/paths.toml"
)
```

The release contains 13 paired crops across regions 002, 003 and 012, including
a partial edge. These inputs are already cleaned: image nodata is zero, stored
label ignore is 3, and outside annotation coverage is excluded. Loading maps
ignored labels to -100. To prepare other inputs, use the
[organization, check and cleanup guide](guides/preparation.md).

## 3. Assign sources and chip

```bash
(
  set -e
  tiny="$data_root/data/examples/tiny_ca_bc/v2"
  splits="$data_root/examples/runs/my-tiny-v2-01-splits"
  chips="$data_root/examples/runs/my-tiny-v2-01-chips"
  uv run --frozen kelpseg split --sources "$tiny/metadata.csv" \
    --recipe configs/split/ca_bc_v1.toml --output "$splits" --dry-run
  uv run --frozen kelpseg split --sources "$tiny/metadata.csv" \
    --recipe configs/split/ca_bc_v1.toml --output "$splits"
  uv run --frozen kelpseg chip --images "$tiny/images" --labels "$tiny/labels" \
    --metadata "$splits/chip_metadata.csv" --recipe configs/chip/planet8.toml \
    --output "$chips" --dry-run
  uv run --frozen kelpseg chip --images "$tiny/images" --labels "$tiny/labels" \
    --metadata "$splits/chip_metadata.csv" --recipe configs/chip/planet8.toml \
    --output "$chips"
)
```

Expect 54 retained windows, including 31 without kelp. The with-BC `augmented`
baseline has 5 training / 2 validation / 6 test sources; active windows are
20 training / 2 validation / 7 test / 25 unused. Training keeps overlap;
validation/test select disjoint windows. Canonical background payloads remain
stored, while training selects 11 positive windows. Preparation reads the tiny
collection; training and the following predictions use training/validation only.
See [selection and padding details](guides/preparation.md#tiny-v2-split-chip-and-load-locally)
for loading arrays and interpreting uncovered edges.

## 4. Train the bounded CPU model

Copy the maintained smoke recipe to the external work directory, changing only
its machine-paths reference. Its default chip/assignment paths match step 3.

```bash
(
  set -e
  test ! -e "$data_root/work/tiny.toml"
  sed 's|^paths_file = .*|paths_file = "paths.toml"|' \
    configs/train/tiny_cpu.toml > "$data_root/work/tiny.toml"
  uv run --frozen kelpseg train --recipe "$data_root/work/tiny.toml" --dry-run
  uv run --frozen kelpseg train --recipe "$data_root/work/tiny.toml"
)
```

The preview reports resolved paths and update budget. Fitting prints a unique
run directory under `runs/`. It uses two training microbatches and one validation
batch per epoch, zero loader workers and no W&B or weight download. Keep its
fixed normalization; tiny statistics are not replacement training constants.

The run contains `settings.json`, `run.json`, metrics, `checkpoints/best.ckpt`,
`checkpoints/last.ckpt` and the selected portable `model/`. A completed smoke is
not a quality evaluation. [Training options](guides/training.md) cover spectral
recipes, losses, completed-epoch resume and an optional isolated installation
rehearsal. Use [GPU setup](gpu_setup.md) for production readiness.

## 5. Copy the model and predict a validation TIFF

Set `run` below to the exact completed directory printed by training (the
`output` field of its final JSON). Copy the entire
model directory, which contains `model.json` and `weights.pt`. The copied bundle
supplies bands, normalization, weights and threshold without labels or a training
registry. The validation image below is a 768 × 768 multiwindow example.

```bash
run='/absolute/completed/run-directory'
(
  set -e
  test ! -e "$data_root/work/copied-model"
  cp -R "$run/model" "$data_root/work/copied-model"
  cat > "$data_root/work/sources.csv" <<'CSV'
source_key,image,band_names,dataset_id,release_id,region_id,acquisition_date,original_source_id,row_offset,col_offset
tiny_val,002_20210228_182240_2406_tiny.tif,coastal_blue;blue;green_i;green;yellow;red;rededge;nir,ca_bc,v1,002,2021-02-28,002_20210228_182240_2406,1024,768
CSV
  cat > "$data_root/work/predict.toml" <<TOML
model = "copied-model"
manifest = "sources.csv"
image_root = "$data_root/data/examples/tiny_ca_bc/v2/images"
output = "$data_root/work/tiff-predictions"
stride = 256
min_valid_fraction = 0.20
batch_size = 1
device = "cpu"
TOML
  uv run --frozen kelpseg predict --recipe "$data_root/work/predict.toml"
)
```

Under `$data_root`, open `work/tiff-predictions/probabilities/tiny_val.tif` and
`work/tiff-predictions/masks/tiny_val.tif` in a GIS; they retain source dimensions, CRS and transform.
Probabilities are averaged across overlapping windows before thresholding once.
NaN probabilities and mask value 255 mean no prediction. Inspect the output
`work/tiff-predictions/sources.csv`
for covered and uncovered valid pixels. These outputs are maps, not scores.

## 6. Report agreement with the matching label

Prediction needed no labels. Reporting now pairs the saved validation prediction
with the same cleaned crop's label; it does not rerun inference. The assignment
reference checks that this source belongs to the with-BC baseline validation
split created in step 3.

```bash
(
  set -e
  cat > "$data_root/work/labels.csv" <<'CSV'
source_key,label
tiny_val,002_20210228_182240_2406_tiny.tif
CSV
  cat > "$data_root/work/report.toml" <<TOML
predictions = "tiff-predictions"
output = "tiff-report"
labels = "labels.csv"
label_root = "$data_root/data/examples/tiny_ca_bc/v2/labels"
assignments = "$data_root/examples/runs/my-tiny-v2-01-splits/assignments.csv"
experiment = "baseline"
variant = "augmented"
split = "val"
max_examples = 1
TOML
  uv run --frozen kelpseg report --recipe "$data_root/work/report.toml"
)
```

Open `$data_root/work/tiff-report/report.html` in a browser with its sibling figures and `examples/`
directory present. Counts and metrics describe covered valid labeled pixels,
with nodata, ignored labels and missing predictions excluded explicitly. Tiny
smoke scores do not establish scientific performance. Keep the inputs and saved
predictions available for report regeneration, and choose a fresh report output.

For disjoint chip predictions, full-source reporting, outputs and common errors,
see [prediction and reporting](guides/prediction_reporting.md). Optional
[augmentation, shoreline and temporal diagnostics](guides/diagnostics.md) are
separate; tiny v2 lacks the kelp-rich examples required by the preview galleries.
Restore the full published data using the
[CA/BC release reference](reference/ca_bc_release.md), and follow
[storage and backup policy](data_artifacts.md) for durable artifacts.

## If a step fails

Stop before running the next block. A missing `kelp-box` remote or access-denied
message requires fixing Box authentication/access before fetching. Missing input
files usually mean a failed copy or a `data_root` pointing at a different folder;
check the exact path in the error. An existing output is deliberately refused:
choose fresh output names for a full new attempt, without reusing partial work.
Do not replace the published inputs or turn on training resume for preparation.

The final training JSON must say `"status": "complete"` before step 5. Use its
printed run path, not a checkpoint file or a guessed latest folder. A report
identity/grid error means its label, source metadata or assignment is not the
matching crop; correct the declaration, rather than relabeling a test source as
validation. For detailed errors and supported alternatives, use the
[preparation](guides/preparation.md), [training](guides/training.md) and
[prediction/reporting](guides/prediction_reporting.md) references.
