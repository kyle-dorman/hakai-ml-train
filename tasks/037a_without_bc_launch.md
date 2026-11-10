# Task 037A — Equal-budget B0 comparison without British Columbia

Status: Complete. The user selected the with-BC epoch-16 EMA baseline.

## Launch contract

Compare the selected EMA bundle from
`planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z` with a fresh
8-band B0 run using the canonical CA/BC v1 chips and `variant = "base"`.
The source assignments outside regions 011 and 012 must agree exactly,
including validation and held-out membership. Training uses kelp-positive
windows. Shared normalization was estimated using kelp-positive with-BC
training imagery capped at 5000.

Keep plain 0.7 BCE + 0.3 Dice, ImageNet initialization, approved augmentations,
batch size 12, two-microbatch accumulation, EMA from update 101, and maximum
pooled chip validation foreground IoU at threshold 0.5. Match the five-epoch
warmup and 70-epoch schedule. Stop after 20 validation checks without a strict
IoU gain. Export the selected checkpoint and record completed optimizer updates
separately from planned updates.

Each epoch uses all 7,280 eligible windows, takes 1,238 from one shuffled repeat
of the same pool, and shuffles all 8,518 draws. The sampler uses the recipe
seed and restored epoch number. This matches 710 microbatches, 355 updates per
epoch and a cap of 24,850 updates. Persistent workers restart augmentation
streams after resume. Sampling order is independent of those streams.

Use one launcher to train, produce float32 tiled predictions for both models
(512 window, 256 stride, 20% native valid fraction), then run segmentation and
temporal reports. Use a single locked validation manifest from the canonical
cleaned sources and assignments. Reuse reference predictions only for the
selected bundle on the matching TIFF scope, grid, and coverage. Confirm exact
finite coverage equality before reporting, so both models use the same
scoreable pixels, including at both dates of each temporal pair. Stop on grid
or coverage disagreement. Use existing 1–13 and 29–47 day intervals and keep
unsupported and undefined cases visible. Write paired tables by source, region
and California (003–010) versus Baja (001–002).

## Acceptance and handoff

Verify the production metadata-only dry run against saved reference settings,
assignments, and chip windows. Run deterministic sampling and completed-epoch
resume tests, a tiny train-to-paired-reports smoke, launcher failure checks,
formatting and lint. Save the launch command, external output locations and
evidence here. The user launches production and chooses the baseline after
reviewing validation. Test scoring and Task 037B are outside this contract.

## Historical launch

The completed experiment ran with the launcher and exact recipe preserved in
commit `4ac0a31`. See [Code retirement](#code-retirement) for recovery commands.

The Bash launcher used a fresh comparison folder and a UTC-stamped training
directory under `/home/sky/data/runs/planet8-ca-baja-b0-without-bc-70ep-*`.
The comparison's `no-bc-dry-run.json` contains its exact path. Training writes
`run.json`, `checkpoints/`, `model/` and `metrics/` there. The comparison
folder contains the locked TIFF/label manifests, resolved recipes,
`with-bc-predictions/`, `no-bc-predictions/`, both `*-segmentation/report.html`
and `*-temporal/report.html` pages, plus paired source, region, California/Baja
and temporal CSVs. `training-comparison.csv` records the actual optimizer counts
and selected checkpoint for each arm. The with-BC reference stopped at 12,780
updates and selected the EMA checkpoint at epoch 16 (5,680 updates).

The launcher supported reuse of completed full-TIFF reference predictions.
At launch, the saved predictions for the selected B0 EMA bundle were on a
disjoint chip grid, and the earlier full-TIFF predictions used B3 weights.
The comparison generated tiled predictions for both B0 bundles and verified
exact finite-mask equality before scoring.

## Outcome

- Added an equal-budget recipe, a Bash launcher and two workflow entry points
  for preparing the locked scope and combining reports. The repeat budget was
  opt-in, and ordinary sampling used the existing checkpoint format.
- Production dry run matched the saved reference settings and schedule.
  All non-BC assignments agreed, with 933 identical validation chip windows
  and 53 cleaned TIFFs on exact image/label grids. The full TIFF list also
  matched the prior Task 036B scope, with 47 California and six Baja TIFFs.
  The no-BC preview, manifest and recipes are in
  `/home/sky/data/analyses/task037a-preflight-20261110T174057Z`.
- Focused tests passed (247). The sampler test checked all 7,280 indices and
  exactly 1,238 distinct repeats. Bounded Lightning resume reproduced the
  uninterrupted epoch orders with zero and two persistent workers, and the
  zero-worker final model and optimizer states matched exactly. Persistent
  workers restart their augmentation streams after resume.
- Tiny smoke artifacts are in
  `/home/sky/data/analyses/task037a-smoke-20261110T174120Z`.
  Two real B0 CPU fits completed one optimizer update each. Four tiny TIFFs
  produced both segmentation and temporal reports. The short and long pairs
  each used the same 992 scoreable pixels in both arms.
  The saved-reference path reused its predictions, and a deliberately
  altered finite mask was rejected before reporting. The Bash launcher was
  also replayed with tiny inputs and the installed prediction and reporting
  commands, reusing the saved reference.
- Bash syntax and fail-fast checks passed. Injected preparation, training,
  prediction, coverage and reporting failures propagated their exit code
  and stopped the sequence. A stubbed successful launch exercised both
  reference-inference and reuse branches. Ruff format/check, pre-commit,
  and `git diff --check` passed.
- A conventional 7,280-draw epoch would use 607 microbatches and 304 updates.
  About 82 epochs would reach a similar update cap, with a different
  validation cadence in optimizer steps. The repeat sampler matches cadence
  for this comparison. A longer ordinary-sampling run could be considered
  separately if no-BC wins and simpler routine training is preferred.

## Production comparison

Both models finished and were scored on the same 53 validation TIFFs and
234,786,210 common scoreable pixels. The with-BC model stopped at 12,780
updates and selected EMA epoch 16. The no-BC model stopped at 13,845 updates
and selected EMA epoch 19. The latter bundle is at
`/home/sky/data/runs/planet8-ca-baja-b0-without-bc-70ep-20261110T174955Z/model`.

The production launcher grouped the geography incorrectly. The checked-in
[region catalog](../configs/regions.csv) identifies 001–002 as Baja and 003–010
as California. The grouping in the launcher and contract is corrected.
The production arm reports and predictions are preserved in
`/home/sky/data/analyses/task037a-without-bc-01`. Use the regenerated paired
tables under its `geography-corrected/` directory. Source scores, numbered
region scores and pair measurements stayed identical.

| Tiled validation | With-BC foreground IoU | No-BC foreground IoU |
|---|---:|---:|
| All 53 TIFFs | 69.88% | 69.94% |
| California, 47 TIFFs | 67.00% | 67.16% |
| Baja, 6 TIFFs | 77.91% | 77.45% |

No-BC traded California recall for precision. It removed 20,104 false
positives while adding 9,790 false negatives. Region 006 had the largest IoU
drop (50.35% to 46.77%) and recall fell from 53.08% to 48.66%.
Baja recall increased and precision fell, driven by region 002.

| Matched temporal interval | Defined pairs | Mean absolute proportional change error with BC | Without BC |
|---|---:|---:|---:|
| California, 1–13 days | 32 | 38.16 pp | 34.38 pp |
| California, 29–47 days | 26 | 235.71 pp | 361.70 pp |
| Baja, 1–13 days | 3 | 10.07 pp | 9.91 pp |

No Baja long pairs were available. For California long pairs, the with-BC
model had lower absolute proportional error in 19 of 26 pairs. Median error
was 87.46 pp with BC and 123.61 pp without. One region 008 pair with a small
starting canopy widened the mean gap. Excluding the pair left 160.10 pp with
BC and 214.46 pp without. Mean absolute error in canopy area change was nearly
the same (6.67 ha for both arms). The 26 pairs come from three regions and
reuse acquisitions. Across all intervals there were 62 spatially supported
pairs, 61 with defined changes for both arms.

California segmentation was close, and the represented multiweek pairs favored
with-BC for proportional change. This result describes agreement with supplied
labels on these validation acquisitions.

### Nearshore follow-up

Reused both arms' saved tiled predictions and the aligned Task 040 shoreline
grids. Both reports use the same threshold of 0.5 and the same labeled
validation pixels. Each source's land, unknown and ocean band counts reconcile
to its original segmentation counts. Outputs are in
`/home/sky/data/analyses/task037a-without-bc-01/nearshore`, including
`paired-shore-region.csv`, `paired-shore-geography.csv` and
`paired-distance-bands.csv`.

On mapped ocean within 120 m of shore (exclusive), with-BC versus no-BC IoU
was 57.57% versus 57.00% and recall was 64.88% versus 64.13%. Offshore recall
was 84.96% versus 85.18%. California nearshore recall declined from 66.19% to
64.99%, with 5,592 additional misses. Region 006 accounted for 3,582 of those
misses. Its nearshore IoU declined from 54.78% to 50.26%. Region 008 remained
weak for both arms nearshore, with recall of 35.36% and 34.68%, respectively.
Baja nearshore recall improved from 49.77% to 54.21% while precision fell
from 78.84% to 69.01%. The nearshore comparison also favors retaining the
with-BC reference for California.

## Baseline decision

The user selected the with-BC B0 epoch-16 EMA bundle on 2026-11-10.
Use run `planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z`,
`variant = "augmented"`, threshold 0.5, and bundle
`/home/sky/data/model-size-runs/planet8-cabc-size-b0-bparams-70ep-20261106T085748896218Z/model`.
The bundle records `checkpoint_epoch = 15` and 5,680 optimizer updates.
The decision reflects the near tie on whole-TIFF segmentation, higher
California nearshore recall and lower multiweek proportional change error.

## Code quality follow-up

The launcher uses the trainer's standard run ID and shares the fixed tiling
policy between recipe generation and saved-reference checks. Coverage validation
reads each probability raster once and checks its grid and finite pixels in
the same pass. The opt-in sampler keeps the same seeded draws and completed-
epoch behavior. A regression test checks the California/Baja grouping against
the canonical region catalog.

The production preflight accepted the saved reference predictions, all 53
tiled footprints passed the coverage check, and replay reproduced all seven
paired CSVs byte for byte. A tiny launcher replay exercised saved-reference
reuse, training and reporting. Injected stage failures stopped the launcher.
The focused suite passed 248 tests. Ruff format/check, pre-commit and
`git diff --check` passed.

## Code retirement

The repeat sampler was built for this one comparison. Matching draws per
epoch matched both the optimizer schedule and the number of updates between
validation checks. The experiment is complete, so the repeat sampler, its
resume integration and the one-off launcher and reporting helpers were
removed from the maintained code. The exact implementation and recipe remain
in commit `4ac0a316cd19fce11877d5075d9bb06e59ebcabf`.

```bash
git show 4ac0a31:configs/train/baseline_comparisons/b0_without_bc.toml
git show 4ac0a31:examples/run_task037a.sh
git show 4ac0a31:src/kelpseg/training/sampling.py
```

The [retained no-BC recipe](../configs/train/baseline_comparisons/b0_without_bc.toml)
uses ordinary sampling and a distinct run name. Its 7,280 eligible windows
produce 607 microbatches and 304 updates per epoch, with a 21,280-update
cap over 70 epochs. Use the commit above for the historical equal-budget recipe.
The retained recipe passed a production metadata dry run. The focused suite
passed 242 tests, along with Ruff, pre-commit and `git diff --check`.

Next action when selected: write the 037B contract for matched 4-band and
3-band comparisons using this reference.
