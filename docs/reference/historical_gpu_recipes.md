# Historical GPU launch recipes

These are the Task 034 setup-era pilots, measurements and launch instructions,
preserved as historical evidence. They are not the selected current baseline or
instructions to continue Task 034. Recipe defaults and retention settings may
have changed since these runs. Use [current GPU setup](../gpu_setup.md) and the
[selected model](../experiments.md#current-planet-8-band-b0-baseline) for new work.
The [Task 034 record](../../tasks/034_gpu_machine_preparation_and_baseline_launch.md)
owns outcomes and measured performance.

## Continue Task 034 on this machine

Use `paths.local.toml` from step 8. Generate tiny chips with the
[split/chip walkthrough](../guides/preparation.md#tiny-v2-split-chip-and-load-locally),
using `/home/sky/data` and `example_name=my-tiny-v2-01`.
Then run the checked eight-band CUDA/bf16 smoke:

```bash
uv run kelpseg train --recipe configs/train/tiny_gpu.toml --dry-run
uv run kelpseg train --recipe configs/train/tiny_gpu.toml
```

This uses ImageNet initialization, two epochs with two training batches and one
validation batch each, and writes a fresh `tiny_gpu-*` folder under `runs_root`.
It checks training, validation, best/last saving and portable model export;
its scores are not scientific results. Its short budget does not reach EMA.
Do not use its batch limits or schedule for production.

The full-data launch recipe is `configs/train/planet8_gpu.toml`: native eight
bands with BC (`augmented`), 70 epochs, microbatch 3 × accumulation 8, bf16,
zero loader workers, and W&B at `kdorman90-ucla/kelpseg`. This reference recipe
uses deterministic execution for repeatable GPU continuation. Ordinary
completed-epoch continuation also supports multiple workers; their augmentation
streams restart and sample order may differ. The faster pilot below trades exact
replay for throughput. The original
spectral examples remain available; this machine recipe makes those choices
explicit. Metadata previews open no test arrays.

```bash
uv run kelpseg train --recipe configs/train/planet8_gpu.toml --dry-run
```

The RTX 3090 rehearsal passed EMA and completed-epoch resume comparison
with maximum tensor difference zero (tolerance `atol=1e-5, rtol=1e-4`).
The deterministic batch uses about 4 GiB; budget 25–30 hours for 70 epochs
and 10 GiB for run files and backup snapshots. These are measured projections,
not guarantees. Settle that budget before launch; the task record owns evidence. Commit corrections before production and
keep the running job on that fixed checkout/environment. Use a separate checkout
for Task 035. Never pull code changes into a running experiment.

For completed-epoch continuation, keep the original recipe, total schedule and
saved run identity. Replace the example path with the actual interrupted run:

```bash
uv run kelpseg train --recipe configs/train/planet8_gpu.toml --resume /home/sky/data/runs/ACTUAL_RUN/checkpoints/last.ckpt --dry-run
uv run kelpseg train --recipe configs/train/planet8_gpu.toml --resume /home/sky/data/runs/ACTUAL_RUN/checkpoints/last.ckpt
```

This returns to the last completed epoch; partial-epoch work is discarded.
Resume is for interrupted runs, not runs that already exported `model/`.
CUDA agreement is bounded by the tolerance recorded in Task 034, not a promise
of bitwise reproducibility on every GPU/software combination.

## Twenty-epoch pilot

Use `configs/train/planet8_gpu_20ep_fast.toml` for the throughput-tested pilot:
eight native bands with BC, twenty epochs, W&B enabled, eight persistent workers,
`deterministic = false`, and microbatch 12 × accumulation 2 (effective batch 24).
It retains five warmup epochs and decays over the remaining fifteen. This is a
separate twenty-epoch schedule, not the first twenty epochs of the 70-epoch schedule.
The original `planet8_gpu_10ep.toml` remains available as the batch-3,
zero-worker deterministic reference.

The selected setting measured 47.6 training samples/second and 12.4 GiB peak
GPU allocation on the RTX 3090. Budget roughly **70–90 minutes for twenty epochs**
or **4–5 hours for 70**, including some allowance beyond the short measurements.
Live W&B/network overhead and full-run variation are not measured guarantees.
The benchmark covers 17 cases, including a batch-24 out-of-memory failure;
detailed evidence is in Task 034. More workers were useful only after faster
GPU computation and larger batches exposed a loading bottleneck again.

Larger microbatches change batch-pooled Lovasz loss and batch-normalization
statistics, even with the same effective batch. This is a separate pilot recipe,
not numerically equivalent to the original batch-3 run. Keep microbatch settings
matched when making scientific comparisons. If preserving batch 3 is preferred,
a copied recipe with four persistent workers and `deterministic = false` measured
29 samples/second (roughly four times the original throughput).

Review changes before launch; the user handles commits/pushes and starts the
run. Keep its code and recipe fixed while it runs. Start a fresh pilot with this
changed recipe; continuation of a saved run requires its original settings.
From the checkout, run inside tmux to survive SSH disconnects:

```bash
tmux new -s kelp-pilot-fast
```

Then in that session:

```bash
cd /home/sky/hakai-ml-train
set -o noclobber
uv run --frozen kelpseg train --recipe configs/train/planet8_gpu_20ep_fast.toml > /home/sky/data/runs/planet8-cabc-20ep-fast.log 2>&1
```

Detach with Ctrl-b, then d. Monitor from another terminal with
`tail -f /home/sky/data/runs/planet8-cabc-20ep-fast.log`, or use W&B. The run
creates its own `planet8-cabc-20ep-fast-*` output folder. Choose a fresh log
filename if repeating the pilot; `noclobber` refuses an existing log.
For continuation, use this same fast recipe with the run's `--resume` path.
Training state restores; identical future augmentation draws or weights are not
promised. Back up stable outputs to Box using the procedure below, substituting
this recipe and log filename when copying records.

## Launch and monitor the baseline

After the checks above pass and the run budget is agreed, launch from the fixed
checkout in tmux. This survives SSH disconnects, not instance deletion:

```bash
(
  set -e
  test ! -e /home/sky/data/runs/planet8-gpu-launch.log
  tmux new-session -d -s kelp-baseline -c /home/sky/hakai-ml-train 'uv run --frozen kelpseg train --recipe configs/train/planet8_gpu.toml > /home/sky/data/runs/planet8-gpu-launch.log 2>&1'
)
tmux list-sessions
tail -f /home/sky/data/runs/planet8-gpu-launch.log
```

Use a fresh log filename/session name for a different run. The trainer creates a
unique `planet8-cabc-gpu-*` output folder. `run.json` records its identity,
revision and resolved settings; `metrics/metrics.csv` and W&B show progress.
The first validation should produce distinct `checkpoints/best.ckpt` and
`checkpoints/last.ckpt`. `model/` is exported only when training completes.
Check `nvidia-smi`, advancing log/CSV entries and the W&B run, not just whether
the tmux session exists. A failed process needs inspection before continuation.

## Back up completed outputs to Box

Treat `/home/sky/data` as temporary. Just after an epoch completes and training
moves into the next epoch, copy its stable checkpoints plus current records to
a fresh snapshot directory. Use the actual run ID and completed epoch below;
change the snapshot name for each backup. Do not copy a checkpoint while it is
being saved. This is an explicit copy, not an automatic backup service.

```bash
(
  set -e
  run_id='ACTUAL_RUN'
  run="/home/sky/data/runs/$run_id"
  snapshot="/home/sky/data/backups/$run_id/epoch-001"
  test ! -e "$snapshot"
  mkdir -p "$snapshot"
  cp "$run/settings.json" "$run/run.json" "$snapshot/"
  cp -a "$run/checkpoints" "$run/metrics" "$snapshot/"
  cp configs/train/planet8_gpu.toml "$snapshot/recipe.toml"
  git rev-parse HEAD > "$snapshot/git-commit.txt"
  cp /home/sky/data/runs/planet8-gpu-launch.log "$snapshot/launch.log"
  rclone copy "$snapshot" "kelp-box:kelpseg/runs/$run_id/epoch-001" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
  rclone size "$snapshot"
  rclone size "kelp-box:kelpseg/runs/$run_id/epoch-001"
)
```

At completion, make another fresh `final` snapshot and include `model/` along
with settings, checkpoints, metrics and logs. Check local/Box file counts and
sizes. Keep the fixed Git revision and machine roots with the handoff. Avoid
copying the entire environment or regenerable chip data into each backup.

To restore an interrupted run, choose a fresh `runs_root/<saved-run-id>` and
copy the selected Box snapshot there. Keep the same run ID, original recipe and
total epochs; set the recipe's `paths_file` to the new machine's settings.
Restore the published data separately, then use the resume preview and command
above. A completed final model is loaded directly for prediction, not resumed.

## Seventy-epoch fast baseline

After reviewing the twenty-epoch pilot, use
`configs/train/planet8_gpu_70ep_fast.toml` for a fresh eight-band with-BC run.
It retains batch 12 × accumulation 2, eight workers, bf16 and EMA. Five warmup
epochs reach LR 0.0003, followed by 65 cosine-decay epochs ending at 0.000003.
W&B is enabled, including loss components, epoch image panels and regional metrics.
Checkpoint retention remains best and last; intermediate epochs are not archived.

Run directly inside your tmux session to retain the interactive progress display:

```bash
uv run --frozen kelpseg train --recipe configs/train/planet8_gpu_70ep_fast.toml
```

This starts from ImageNet weights with a fresh run identity, not from the completed
pilot. Metadata preview expects 710 training / 78 validation batches per epoch
and 24,850 optimizer updates. The run creates its own timestamped output folder.
