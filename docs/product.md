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

## California target and temporal consistency

The immediate application is mapping the California coast beyond the small
labeled geographic sample. Geographic generalization is the main concern;
future-date/year testing and stable errors through time at each location also
matter. A location-specific under/overestimate is more acceptable than an error
that changes with year and creates an artificial trend. Real kelp changes should
remain visible; temporal consistency is evaluated against supplied labels.

Regions 001–010, including both Baja regions, are eligible for validation/test.
Regions 011 (Calvert Island) and 012 (BC tiles) are training-only. Compare runs
with both 011/012 included versus both excluded, keeping the evaluation-region
training/validation/test assignments fixed. Neither training-only region creates
a LORO test fold or contributes to validation/checkpoint selection. The run
including both BC regions is the primary baseline; without both is the comparison.
The manifest names remain `augmented` and `base`, respectively. Report
California and Baja results explicitly so geographic scope remains clear.

Within each experiment/fold, group by physical spacecraft ID plus UTC acquisition
date across regions and crops. Each group can contribute to only one of train,
validation and test; the same spacecraft on different days may cross partitions.
Keep regional date groups intact too. The approved baseline uses reverse
chronology for 001–008 and forward for 009/010; exact assignments are locked
in Task 032A before model evaluation.
The baseline is then a region-specific temporal holdout, not a uniform future-
year benchmark. LORO still supplies the primary geographic generalization test.

The temporal split must reflect the actual sparse year/month support. Keep
later-date generalization distinct from a strict future-year claim. Low-kelp
dates remain part of the declared evaluation scope; expose label prevalence,
false positives/negatives and temporal error patterns rather than dropping
those dates to improve F1. Detailed evaluation requirements live in
[experiments.md](experiments.md#evaluation-and-comparison).

## New regions

All datasets, including the current CA/BC scope, follow the same raw → organized
→ cleaned stages under their own dataset/release identities. Preserve every
published release; select any dataset or combination with an explicit collection
manifest. "Baseline" and "new region" describe roles in a particular experiment,
not privileged dataset storage or ingestion paths. The ingestion and
provenance flow is owned by
[data_artifacts.md](data_artifacts.md#adding-regions-and-combined-datasets).

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
- During training, use non-overlapping existing validation chips for loss and
  aggregate confusion counts, with explicit uncovered edge/gap reporting. Test
  stays held out until model selection is finished; chip-based test uses the
  same disjoint-window rule. Training chips may overlap.
- For post-training tiled/source scoring, reconstruct overlapping probabilities
  before scoring each source pixel once; report ignored and uncovered pixels.
  Keep chip-scope and full-TIFF results distinct. Never average chip IoUs as
  region IoU.
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
