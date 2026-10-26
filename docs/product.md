# Product and research contract

## Purpose

Provide a small, understandable workflow for researchers training binary kelp
segmentation models on Planet imagery. Support data preparation, chipping,
training, labeled evaluation, unlabeled mapping, geographic generalization,
and adaptation to new regions. Remove unrelated applications and frameworks.

## Model comparisons

The initial reference is the downloaded eight-band SegFormer B3 kelp model.
Capture a handful of original chips, labels, predictions, and previews as a
visual gut check before removing legacy code. Exact historical training
reproduction and backward-compatible code/config APIs are not requirements.

The initial spectral comparison is interpreted as eight bands, RGB+NIR, and
RGB from the same eight-band acquisitions. Confirm actual band identity/order
from source metadata. Keep source membership and evaluation policy comparable.
Do not treat old multiclass RGB/RGBI configs as valid Planet binary recipes.

Keep the working SegFormer recipe as the first model family. Small controlled
changes to augmentations and learning rate are in scope. A possible RGB
DINOv3 initialization experiment follows a working baseline; broad model or
architecture sweeps are outside the core rebuild.

## New regions

Support four separately identified cases:

1. Evaluate an existing kelp checkpoint on new-region imagery without adaptation.
2. Fine-tune a kelp checkpoint on new-region training data and evaluate it.
3. Fine-tune generic pretrained weights on the same new-region training data
   and evaluate them.
4. Train with combined old/new training data and evaluate the resulting model.

The combined run's initialization, sampling, and budget must be explicit when
that experiment is selected; it is not implicitly a continuation of case 2.
Keep independent new-region test imagery fixed across cases and retain old
held-out evaluation for assessing effects on existing regions. Test imagery
never enters the training or validation pool after adaptation.

## Splits and claims

- Preserve source TIFF, region, acquisition date, and band identity.
- Never split chips from one source TIFF across train/validation/test.
- Start with a temporal baseline within regions; keep acquisition-date groups
  intact. LORO excludes the complete held-out region from train/validation.
- Repeat relevant baseline/LORO comparisons when the model or recipe changes;
  record which recipe/dataset the comparison represents.
- Select preprocessing, thresholds, and checkpoints without held-out results.
- Default cross-run comparisons use matching unseen source TIFFs. Report
  full-region LORO summaries separately from paired temporal-test comparisons.
- Reconstruct overlapping probabilities before scoring each source pixel once;
  report ignored and uncovered pixels. Never average chip IoUs as region IoU.
- Report agreement with supplied segmentation labels on the represented
  imagery, regions, dates, sensors, and preprocessing. Do not claim independent
  ecological truth or universal transfer performance.

## Practical success criteria

A successor with limited Python/ML fluency can follow short recipes to prepare
data, train, evaluate, map unlabeled imagery, and adapt a checkpoint. Original,
cleaned, and chipped datasets have recoverable documented provenance and Box
copies. Split assignments live with data outside Git. Most pipeline correctness
is tested locally before moving to a GPU host; production Mac training is not
a requirement.
