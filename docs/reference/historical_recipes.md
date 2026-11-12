# Historical recipes and recovery

These are preserved examples from completed studies, not a launch queue or current model recommendation. Original host paths identify historical artifacts. Do not rerun into completed outputs. See [history](../history.md) for results and recovery, and [training](../guides/training.md) for current supported options.

## Preserved v1 example

The earlier nine-pair example proves chipping/loading and remains on Box. It
has no CA train/validation sources under the approved split, so use v2 for
split practice. Fetch v1 once into a fresh directory, or skip the copy if that
local input already exists:

```bash
(
  set -e
  data_root='/Volumes/x10pro/kelpseg'
  tiny="$data_root/data/examples/tiny_ca_bc/v1"
  test ! -e "$tiny"
  mkdir -p "$(dirname "$tiny")"
  rclone copy kelp-box:kelpseg/data/examples/tiny_ca_bc/v1 "$tiny" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
)
```

The copy checks ordinary paths/sizes. To run offline, use the
[chipping recipe](../guides/preparation.md#chip-cleaned-imagery) with v1's `images`, `labels` and
`metadata.csv`, choosing a fresh output. Expect 9 sources, 38 retained windows
and about 102 MB of output. The same partial-edge loading example applies:
select a retained `windows.csv` row with width 257 and resolve its payload from
the v1 chip root. Original v1 paths and detailed results remain in
[Task 031](../../tasks/031_chipping_bands_and_tiny_walkthrough.md#outcome-2026-10-27).

## Increased weight-decay experiment

`configs/train/regularization/bce_dice_wd005.toml` changes weight decay from
0.01 to 0.05 with a distinct run name. It uses unsmoothed BCE, Dice, W&B and the same 70-epoch LR schedule.
Its stopping patience is 20 (the first attempt used 10). The completed experiment
selected epoch 19 and stopped after epoch 39. Its reduced-noise augmentation also
differs from the historical baseline, so the comparison does not isolate weight
decay alone. The one-off weight-decay launcher has been removed.

To repeat this recipe as a fresh experiment, use the installed command:

```bash
uv run --frozen kelpseg train --recipe configs/train/regularization/bce_dice_wd005.toml
```

Use `predict-chips` followed by `report` for post-training diagnostics, as
[documented below](../guides/prediction_reporting.md#post-training-validation-diagnostics).

## Controlled learning-rate comparison

The completed comparison and its recipes are recorded in the
[Task 034 sidecar](../../tasks/034_lr_followup_notes.md). To repeat an arm, train
with a recipe from `configs/train/lr_comparison/`, then run the post-training
validation commands. The historical runs are under
`/home/sky/data/lr-comparison-runs/` on the GPU host.

`checkpoint_epochs = [4, 5, 6, 7, 8, 9, 10, 11, 12]` saves full checkpoints
`checkpoints/epoch-04.ckpt` through `epoch-12.ckpt`, only when those epochs finish.
Numbers are one-based; the internal checkpoint epoch remains zero-based.
The default empty list retains existing best/last-only behavior. Extra snapshots
preserve validation-selected EMA weights and current training/optimizer state,
using the same native save hooks as best/last; model-bundle export can read them.
The supported training-resume entry remains `last.ckpt`. Expect roughly 6 GB
of extra snapshots per run. No per-TIFF epoch metrics are added.

## Smaller SegFormer comparison

`encoder_name` selects `mit_b0`, `mit_b1`, `mit_b2`, or `mit_b3` (the default).
The selected encoder is recorded in settings, checkpoints and portable models;
loading a bundle reconstructs its recorded size offline. Resume requires matching
current settings. Changing size requires a fresh training run.

The completed comparison used the B settings for B2, B1, and B0. To repeat an
arm, train with its recipe in `configs/train/model_size/` and run the
post-training validation commands. The historical runs are under
`/home/sky/data/model-size-runs/` on the GPU host.

## Run the B0 distance-weighted BCE screen

Historical Task 041 sequence. The screen is complete; plain BCE+Dice remains
the selected baseline. Commands below record that study and are not instructions
to launch another screen.

[Task 041](../../tasks/041_distance_weighted_bce_experiment.md) compares a fresh
alpha-zero control and alpha 1 and 2 treatments on the same derived chips and
existing assignments. At training time, the positive-pixel multiplier halves
its boost every 120 m. Mapped land receives the full boost. Unknown distance
and background have weight 1. Capped positives use 500 m, so alpha 2 still
gives them a weight of about 1.111. BCE divides by the sum of valid-pixel
weights in each microbatch. Dice, optimizer accumulation and checkpoint selection
use the B0 settings.

The following commands use the existing local CA/BC release and Task 040
rasters. Run them from the repository root in Bash when ready to launch the
screen. Change the roots for your machine. Use a fresh work directory outside
any active upload. The derived release duplicates about 66 GB of canonical
payloads and adds up to about 35 GB of uncompressed distance/land data before
NPZ compression. Allow about 101 GB for preparation plus space for the runs,
predictions and reports. Check the reported byte count after preparation.
Eight source workers suit the current GPU host. Omit `--workers` to use
one process, or lower it on a smaller machine.

```bash
uv run --frozen kelpseg prepare-chip-distances \
  --chips /home/sky/data/data/chips/ca_bc/v1 \
  --shoreline /home/sky/data/analyses/task040_shoreline_v1 \
  --output /home/sky/data/data/chips/ca_bc/v1-distance500 --workers 8
```

Once the derived dataset is published, set up the run folder and preview the
three recipes.

```bash
set -euo pipefail
data=/home/sky/data
work="$data/task041-distance-bce-v1"
shore="$data/analyses/task040_shoreline_v1"
inventory="$data/analyses/task040_shore_inventory_size5000_v5"

df -h "$data"
mkdir "$work"
mkdir "$work/runs"
cat > "$work/paths.toml" <<EOF
[paths]
data_root = "$data"
runs_root = "$work/runs"
EOF

for alpha in 0 1 2; do
  recipe="$work/alpha$alpha.toml"
  sed "s|^paths_file = .*|paths_file = \"$work/paths.toml\"|" \
    "configs/train/distance_weighting/alpha$alpha.toml" > "$recipe"
  uv run --frozen kelpseg train --recipe "$recipe" --dry-run
done
```

Each preview should show 53 validation sources and 933 validation windows, with
identical counts and update budgets across arms. The preparation output includes
the original chip recipe, source and window manifests and a new summary with
payload bytes and unknown-distance positive window pixels. Those counts include
overlapping appearances across the whole release. If preparation fails, inspect
the error and choose a fresh output before starting again. Keep each recipe's
`chips` setting in sync with the chosen derived path.

Run the following block in the same shell after reviewing the previews. Each
alpha finishes training, prediction and reporting before the next starts.
The exported best bundle drives float32 chip predictions at threshold 0.5.
The reports use disjoint validation windows and the same fixed unaugmented
training sample for each arm.

```bash
for alpha in 0 1 2; do
  uv run --frozen kelpseg train --recipe "$work/alpha$alpha.toml"
  runs=( "$work/runs/planet8-cabc-b0-distance-alpha${alpha}-70ep-"* )
  test "${#runs[@]}" -eq 1 && test -d "${runs[0]}" || exit 1
  for split in val train; do
    predictions="$work/alpha$alpha-$split-predictions"
    uv run --frozen kelpseg predict-chips --run "${runs[0]}" --device cuda \
      --split "$split" --seed 42 --sources-per-region 3 --output "$predictions"
    report_recipe="$work/alpha$alpha-$split-report.toml"
    cat > "$report_recipe" <<EOF
predictions = "$predictions"
output = "$work/alpha$alpha-$split-report"
shoreline = "$shore"
cluster_inventory = "$inventory"
max_examples = 12
EOF
    uv run --frozen kelpseg report --recipe "$report_recipe"
  done
done
```

In CSV and W&B, `train/distance_bce` is the optimized BCE component and
`train/distance_bce_unweighted` is ordinary BCE on the same augmented training
pixels. `train/unknown_distance_positive_pixels` counts surviving positive
appearances with unknown distance after augmentation. Validation logs
`val/distance_bce_unweighted` and ordinary BCE/Dice loss. Scoring uses ordinary
pixel counts. Compare nearshore recall and precision alongside mapped-land,
offshore and overall results. The joint report adds full-source cluster size
and source/date support. Compare support and coverage across arms before
interpreting any score changes.

### Additional distance-weighting arms

The user-requested alpha 4 and 8 recipes are in
`configs/train/distance_weighting/`. On the current GPU host, the prepared
launcher uses the local recipe copies and the same derived chips and source
assignments as alpha 0/1/2. Run it in tmux after the initial screen finishes.

```bash
bash /home/sky/data/task041-distance-bce-v1/run-alpha4-alpha8.sh
```

It runs alpha 4 then 8, with validation and fixed training-sample predictions
and shoreline/cluster reports after each arm. These stronger settings have
maximum positive weights of 5 and 9. At the fixed 500 m cap their positive
weights remain about 1.223 and 1.445.

## Completed LORO study

Task 037C completed ten 8-band B0 folds. Its normalization provenance and
claim qualifications belong in the linked task/write-up.
Its one-off launcher, smoke driver, suite reporting helpers and fold-specific
training integration are archived in commit
`609aa22fe27f2c0f41098b7055321da3ceb62f94`. They are no longer maintained in the
current checkout; `kelpseg train` supports baseline experiments. Existing
portable LORO bundles still work with the generic prediction commands.

The [task record](../../tasks/037_baseline_comparisons_and_loro.md#037c-implementation-retirement--2026-11-12)
contains the historical launch command, source recovery commands, methods,
results and illustrated researcher summary. Completed artifacts remain under
`/home/sky/data/analyses/task037c-loro-04/`. Start with the
[illustrated summary](/home/sky/data/analyses/task037c-loro-04/results-writeup/results.html)
or `summary/segmentation.csv` and `summary/temporal.csv` for pooled and regional
results. Do not relaunch into the completed output directories.


## Retired workflow replacements

Use the installed commands and flat TOML recipes above for current work:

| Retired workflow | Current interface |
|---|---|
| Raw merge and directory validation scripts | `kelpseg organize`, `kelpseg check`, `kelpseg clean` |
| Hard-linked baseline/fold datasets and destructive background filtering | `kelpseg split` and manifest selection; `train` selects kelp-positive training chips while retaining canonical backgrounds |
| Legacy nodata analysis | `kelpseg check --full` and chip manifests/coverage summaries |
| Root `trainer.py` and class-path YAML recipes | `kelpseg train --recipe <recipe.toml>`; use `--dry-run` before fitting |
| Prediction/evaluation scripts | `kelpseg predict` or `kelpseg predict-chips`, then `kelpseg report` |
| Historical suite comparisons | Saved segmentation/temporal tables and `kelpseg temporal-report`; recover the completed LORO source only for historical inspection |
| Archive and transfer scripts | Ordinary explicit rclone copies in the [Box recipes](../box_backup.md) |

The old `scripts/` directory, legacy `src.*` modules and YAML configs are no
longer part of the toolkit. The active `bootstrap_gpu.sh` and installed augmentation
preview commands remain supported. The [Task 037 cleanup record](../../tasks/037_baseline_comparisons_and_loro.md#037d--retire-legacy-code)
records removal details and Git recovery references. The immutable
[legacy checkpoint reference](../data_artifacts.md) and completed runs remain
outside Git; removing source does not convert those historical checkpoints
into current portable bundles.

### Loss screening recipes

[configs/train/losses/](../../configs/train/losses) contains 13 standalone recipes:

- Eight single-loss recipes: `bce`, `boundary_bce`, `lovasz`, `dice`, `jaccard`,
  `focal`, `tversky`, and `focal_tversky` (each filename ends in `.toml`).
- `baseline.toml`: the historical smoothed BCE/Lovasz objective at the same 70-epoch budget.
- `bce_lovasz_unsmoothed.toml`: matched control for removing BCE smoothing.
- `bce_dice.toml`, `boundary_bce_dice.toml`, `focal_dice.toml`: 0.7/0.3 combinations.

All use 70 epochs, five warmup epochs, full 8-band with-BC data, the current
3e-4/3e-6 LR endpoints, batch 12/accumulation 2, seed 42, initialization,
augmentation and W&B settings. Their paths resolve relative to each recipe.
They use batch pooling for a matched first comparison. The Tversky candidates
use alpha 0.3/beta 0.7, and focal Tversky uses gamma 0.75; these are candidate
settings, not selected winners. Single overlap losses have the background-only
behavior described above. Cosine decay spans the remaining 65 epochs.

These recipes preserve the completed comparison settings. A new experiment
requires a fresh identity; preview a copied recipe before any separately authorized launch:

```bash
uv run --frozen kelpseg train --recipe configs/train/losses/baseline.toml --dry-run
```


## Historical augmentation review artifacts

The affine review gallery is
`/Volumes/x10pro/kelpseg/analyses/task033d_affine_pipeline_previews_v1/index.html`.
The GPU noise review is at
`/home/sky/data/analyses/task034_noise_review_20261105/isolated/index.html` and
`/home/sky/data/analyses/task034_noise_review_20261105/pipeline/index.html`.
It compares Gaussian-noise upper bounds 0.0005 and 0.002 using the same four
positive windows and two backgrounds, seed 33, eight combined draws and fixed
0–2000 displays. These are visual checks, not evidence of improved validation
performance. Use the [diagnostic guide](../guides/diagnostics.md) to generate new
previews in fresh directories.
