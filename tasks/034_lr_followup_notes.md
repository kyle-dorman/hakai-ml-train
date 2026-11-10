# Task 034 sidecar: next learning-rate experiment

Saved 2026-11-05; updated 2026-11-06 after completion of A–D and B2/B1/B0.
The recipes and launchers retain epochs 4–12. B0 with B's parameters and EMA
is now the working baseline. Per-TIFF epoch logging was explicitly declined;
existing global and regional metrics remain unchanged. The original plan follows.

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
   epochs 4–12 (counting from 1), plus best and last. Inspect acquisitions later
   through checkpoint inference; do not add per-TIFF epoch logging. Best/last
   checkpoints alone cannot reconstruct the transition.
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

Prepared recipes in `configs/train/lr_comparison/`:

| Recipe | Peak LR | Weight decay |
| --- | --- | --- |
| `a_reference.toml` | `3e-4` | `0.01` |
| `b_half_lr.toml` | `1.5e-4` | `0.01` |
| `c_lower_lr.toml` | `1e-4` | `0.01` |
| `d_half_lr_wd005.toml` | `1.5e-4` | `0.05` |

The retired `run_lr_comparisons.sh` launcher saved its outputs under
`<data_root>/lr-comparison-runs/` and followed each training run with validation
`predict-chips` and `report`. See the [current recipe](../docs/quickstart.md#controlled-learning-rate-comparison)
for repeating an arm. A second-seed reference/winner pair remains a later
decision.
See [Task 034](034_gpu_machine_preparation_and_baseline_launch.md) for run evidence.


## Approved overnight size comparison

The completed sequence ran B2 → B1 → B0 after D, using B's parameters unchanged
except encoder size and run name. The retired `run_model_size_comparisons.sh`
launcher retained epoch 4–12 snapshots and ran post-training validation-chip
reports. Outputs are under `/home/sky/data/model-size-runs/`. The saved recipes
are in `configs/train/model_size/`.

The completed LR and model-size output roots were verified against Box on
2026-11-10.
