# Task 037B — Matched B0 spectral comparison

Status: Complete. The user selected 8-band for 037C and skipped DINOv3.

## Launch contract

Compare Planet RGB+NIR (red, green, blue, NIR) and false-color (NIR, red, green)
with the [selected with-BC 8-band epoch-16 EMA model](037a_without_bc_launch.md#baseline-decision).
Train fresh B0 models using the canonical native eight-band chips, augmented
baseline assignments, and the approved fixed with-BC normalization subset for
each band order. Match the reference's plain 0.7 BCE plus 0.3 Dice, ImageNet
initialization policy, augmentations, EMA, threshold 0.5, and pooled chip
validation IoU for checkpoint selection. Preserve the 20-check early-stopping
rule. Both recipes use the same 8,518 eligible windows, 710 microbatches and
355 optimizer updates per epoch, with five warmup epochs and a 70-epoch cap of
24,850 updates. Report actual updates and selected checkpoints separately.

Reuse the completed Task 037A with-BC tiled predictions, validation and label
manifests after verifying the selected bundle, scope, TIFF grids and tiling
settings. Predict both new models on those same native TIFFs with a 512-pixel
canvas, 256 stride, 20% native-valid rule and float32 inference. Check exact
finite-pixel coverage before scoring. Stop on a mismatch. Run the installed
segmentation and temporal reporters for all three arms using the common
validation footprint. Include the established shoreline bands, source and
region results, and 1–13 and 29–47 day pairs. Keep California (003–010) and
Baja (001–002) visible separately. Temporal comparisons must show support and
retain undefined pairs. Use no test imagery for selection.

## Verification and handoff

Dry-run both production recipes and check the shared validation membership,
band order and planned budget against the 8-band run. Run bounded CPU fits
and copied-bundle TIFF predictions with both spectral recipes, followed by
the reports on tiny common dates. Check the launcher stops on failure.
The user launches production in tmux. Review the validation results before
any DINOv3 or 037C work. The 8-band model remains the default baseline.

## Historical launch

The launcher and Python driver used for production are preserved in commit
`b76b976`. Recover the source with:

```bash
git show b76b976:examples/run_task037b.sh
git show b76b976:examples/task037b.py
```

Training runs are under
`/home/sky/data/runs/planet4-cabc-b0-spectral-037b-70ep-*` and
`/home/sky/data/runs/planet3-cabc-b0-spectral-037b-70ep-*`. The exact run paths
are in `planet4-preview.json` and `planet3-preview.json` in the comparison folder.

The comparison folder also contains the two new prediction sets, each arm's
`*-segmentation/report.html` and `*-temporal/report.html`, source and region
tables, and shoreline tables including the 120 m nearshore cutoff. Start with
`segmentation-geography.csv`, `temporal-geography.csv`, and
`training-comparison.csv`. The temporal summary compares errors on the subset
with defined changes in all three arms. Individual reports retain undefined
and unsupported pairs. The 8-band probability rasters stay in the completed
037A `with-bc-predictions/` folder.

## Outcome

- Added the [4-band recipe](../configs/train/baseline_comparisons/b0_planet4.toml)
  and [3-band recipe](../configs/train/baseline_comparisons/b0_planet3.toml),
  a short Bash launcher and a task-local Python driver that calls the existing
  training, prediction and report functions. The shared training and sampling
  code needed no changes.
- Both production dry runs matched the reference settings, augmentation, EMA,
  counts and schedule. All 933 chip validation windows matched the saved
  reference by source, offset and shape. The saved 8-band probabilities matched
  the selected bundle, tiling policy, native grids and current validation
  assignments for all 53 TIFFs. Preflight records are in
  `/home/sky/data/analyses/task037b-preflight-20261110T195407Z`.
- The tiny Bash smoke ran real CPU B0 training for both reduced-band arms, one
  optimizer update each, then predicted four TIFFs using copied bundles with
  the requested band orders. The three segmentation and temporal reports used
  the same 3,968 scoreable pixels and two supported date pairs. A shoreline
  replay reconciled the same pixels for all arms and a one-pixel finite-mask
  mismatch was rejected. Smoke outputs are in
  `/home/sky/data/analyses/task037b-smoke-20261110T195444Z`.
- Injected failures at all four launcher stages returned the failure code and
  stopped the sequence. All 248 focused tests, Bash syntax, Ruff, pre-commit
  and `git diff --check` passed.

## Production results

Across the same 53 validation TIFFs, 8-, 4-, and 3-band foreground IoU was
69.88%, 69.26%, and 69.11%. Nearshore recall below 120 m was 64.88%, 64.35%,
and 66.11%. Both reduced-band arms lost IoU in region 006 and gained IoU
in 007. For 26 matched California multiweek pairs, mean absolute proportional
change error was 235.71, 247.66, and 311.16 percentage points. Four-band had
the lowest median proportional error and mean absolute area-change error.
The arms stopped at 12,780, 17,395, and 23,430 updates and selected EMA epochs
16, 29, and 46. Detailed reports and bundle identities are in
`/home/sky/data/analyses/task037b-spectral-01`.

### Training curves

At epoch 36 (12,780 updates for all arms), 8-, 4-, and 3-band training
IoU was 78.29%, 75.60%, and 73.99%. Chip validation IoU at the same
epoch was 68.28%, 67.49%, and 66.99%. From epoch 16 to 36, training
IoU increased by 2.88, 2.78, and 3.20 percentage points, while chip
validation IoU changed by −0.28, +0.47, and +0.33 points. Peak chip
validation IoU was 68.56%, 67.79%, and 67.73%, respectively.

The runs plateaued on this validation split while training fit improved.
Suspected nearshore label noise could obscure small validation differences.
These curves alone cannot quantify how much of the plateau comes from labels.
Future headline reports pool the evaluation scope and retain per-region
results for inspection.

### Shareable results writeup

The Markdown writeup and its embedded six-panel figure are saved together in
`/home/sky/data/analyses/task037b-spectral-01/results-writeup/` as
`results.md` and `matched-train-validation.png`. The same directory contains
`figure-sources.json` with the source TIFFs, crop coordinates and pixel counts.

### Baseline decision

The user selected the with-BC 8-band B0 as the spectral reference for 037C and
skipped the false-color DINOv3 experiment. The reference is the [epoch-16 EMA
bundle selected in 037A](037a_without_bc_launch.md#baseline-decision).

Next action when selected: write the 037C launch contract for 8-band LORO.
