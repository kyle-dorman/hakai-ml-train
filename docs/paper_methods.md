# Paper methods summary

## Imagery and labels

- We segmented kelp in Planet imagery as a binary pixel-classification task.
  Targets were encoded as 1 for kelp, 0 for non-kelp and -100 for ignored pixels
  (unlabeled areas or image nodata). Ignored pixels contributed neither to the
  training loss nor to evaluation metrics.
- In addition to the imagery used in the previous study, we included British
  Columbia data in training. BC imagery was excluded from validation and test
  because the target application was kelp mapping in California.

## Training and evaluation splits

- We divided imagery temporally within each evaluation region into training,
  validation and test sets. All crops and chips from an original source TIFF
  inherited its assignment. Date cutoffs were region-specific, with reverse
  chronology for regions 001–008 and forward chronology for regions 009–010.
- We kept acquisitions from the same physical satellite on the same UTC day
  from contributing to different partitions, including across regions. Regional
  acquisition-date groups were also kept together.
- For leave-one-region-out (LORO) evaluation, the entire held-out region formed
  the test set. Other regions retained their temporal training and validation
  assignments; their temporal test sources remained unused. Other-region
  acquisitions sharing a satellite and date with the held-out region were also
  excluded from training and validation.

## Image windows and preprocessing

- We extracted 512 × 512-pixel windows with a stride of 256 pixels. Windows
  containing more than 50% image nodata were excluded from the chip collection
  used for training, validation and chip-based test selection. Edge windows were
  padded as needed, with padded targets ignored.
- Training used only windows containing at least one labeled kelp pixel.
  Evaluation retained background-only windows. Training windows could overlap;
  chip validation used a non-overlapping subset so each evaluated source pixel
  was counted once.
- The primary model used all eight bands. We also evaluated performance changes
  with four bands (red, green, blue and near-infrared) and three bands
  (near-infrared, red and green), using matching source assignments.
- Image values were capped at 5000 before per-band standardization. Means and
  sample standard deviations were calculated after capping, using valid image
  pixels from kelp-positive training chips in the with-BC baseline. This included
  background pixels within those chips, but excluded background-only chips and
  image nodata. Overlapping windows contributed repeated pixel observations.
  The same fixed band-specific values were applied during validation and inference.

## Model and checkpoint selection

- We fine-tuned an eight-band SegFormer B0 model from ImageNet-pretrained encoder
  weights, with one output probability per pixel. The loss combined 0.7 binary
  cross-entropy and 0.3 Dice loss, without label smoothing.
- We selected the checkpoint with the highest pooled validation intersection-over-
  union (IoU), using a kelp probability threshold of 0.5. Test results did not
  determine checkpoint selection.
- We used delayed exponential moving averaging (EMA): weights were first copied
  after optimizer update 101 and subsequently averaged with decay 0.999.
  Validation used EMA weights after averaging began. The selected model used
  the EMA weights from completed epoch 16.

## Full-image inference

- We predicted complete TIFFs using 512 × 512-pixel windows with stride 256,
  independently of labels. Final windows shifted inward at the bottom and right
  edges to cover the image with full-size windows where possible. Padding for
  smaller images was removed before placing predictions on the source grid.
- Inference retained windows with at least 20% valid native imagery, measured
  before padding. This criterion was separate from the training-chip nodata rule.
- We averaged foreground probabilities from overlapping windows at each valid
  source pixel, then applied the 0.5 threshold once. Pixels without a prediction
  remained unclassified rather than being treated as background.

## Appendix settings

- Optimizer: AdamW; learning rate 0.00015; betas (0.9, 0.95); weight decay 0.01,
  excluding bias and normalization parameters.
- Schedule: five warmup epochs followed by cosine decay to 0.000003 over a
  configured maximum of 70 epochs. Early stopping used 20 validation checks
  without improved IoU.
- Batch size: 12, with gradient accumulation over two batches; gradient clipping:
  0.8; seed: 42; precision: bf16 mixed precision; deterministic execution disabled.

For implementation details and source references, see [methods](methods.md).
Study-specific LORO normalization provenance and claim qualifications remain in
[the LORO study record](../tasks/037_baseline_comparisons_and_loro.md).
