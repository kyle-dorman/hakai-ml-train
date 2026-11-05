# Task 034 sidecar: next learning-rate experiment

Saved 2026-11-05. Plan only: these runs, intermediate-checkpoint retention and
per-TIFF epoch logging are not yet configured or implemented.

1. **Test half the peak LR: `3e-4 → 1.5e-4`.** Keep the minimum at `3e-6`,
   warmup at 5 epochs, schedule length at 70 epochs, and stopping patience at 20.
   Measure both the size of the early prediction shift and the best validation
   IoU; greater stability need not improve the best IoU.
2. **Make the comparison controlled.** Use WD `0.01`, unsmoothed BCE/Dice
   (weights 0.7/0.3), and the same reduced-noise augmentation for both the
   reference (`3e-4`) and lower-LR runs. Keep the other settings, data assignments
   and seed fixed. The historical baseline used stronger Gaussian noise, so it
   cannot isolate the LR change. AdamW's decay update is also scaled by LR;
   changing LR is not perfectly independent of regularization. See the
   [PyTorch AdamW documentation](https://docs.pytorch.org/docs/stable/generated/torch.optim.AdamW.html).
3. **Save evidence around the early transition.** Retain checkpoints around
   epochs 4–12 (counting from 1) and record per-TIFF validation confusion counts
   each epoch. This will locate acquisition-specific spikes and allow direct
   inspection. Best/last checkpoints alone cannot reconstruct the transition.
4. **Investigate training representation before adding regularization.** Compare
   region 004's training acquisitions, kelp coverage and imagery conditions with
   its validation scenes. Establish any underrepresented condition before
   trying additional representative training examples or source-balanced
   sampling. Keep validation imagery out of training and preserve split rules.

Context: the WD `0.05` run selected epoch 19 and stopped after epoch 39. Its
selected-checkpoint report IoU was 68.64%, versus 68.98% for the original WD
`0.01` BCE/Dice EMA baseline (epoch 18). Noise also changed, so this was not an
isolated weight-decay test. Keep that original model as the working baseline.
The early region 004 collapse was mainly a precision drop; later deterioration
was mainly declining recall. Diagnose those separately.

Next action: inspect the completed full-TIFF baseline report, then prepare the
controlled pair and the additional checkpoint/metric recording before launch.
See [Task 034](034_gpu_machine_preparation_and_baseline_launch.md) for run evidence.
