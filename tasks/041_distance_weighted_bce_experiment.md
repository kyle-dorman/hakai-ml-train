# Task 041: Distance-weighted BCE for nearshore kelp recall

Status: Complete. Alpha 0 selected as the baseline and final code review passed on 2026-11-10.
Starting revision: `9f742637cecaabd7f8a0a90eff0517f977f05b9b`.
Depends on Task 034 B0/B1 baselines and Task 040 aligned shoreline artifacts.

## Abstract

Test whether giving labeled kelp nearer mapped land more BCE weight improves
nearshore recall without an unacceptable precision or offshore-performance cost.
Use a smooth distance curve, keep regional/window exposure unchanged, and compare
against a fresh unweighted control. This targets a training priority, not proof
that distance or underrepresentation causes the observed errors. Small-cluster
weighting is an optional later experiment, not part of the initial comparison.

## Read and inputs

Read AGENTS, docs/index.md, docs/todo.md, tasks/README.md, then this contract.
Read docs/experiments.md for run/checkpoint rules, docs/architecture.md for
alignment/scoring, docs/data_artifacts.md for paths/backup, and the training and
shore-distance sections of docs/quickstart.md. Read docs/documentation.md before
editing durable guidance. Task 040 was committed before implementation began.

Inputs:

- `configs/train/model_size/b0.toml`: B0 with B's settings, eight-band with-BC
  data, reduced Gaussian noise, unsmoothed BCE/Dice and EMA.
- `/home/sky/data/analyses/task040_shoreline_v1/`: existing aligned land/distance
  grids and source manifest; do not rechip or modify canonical inputs.
- `/home/sky/data/analyses/task040_shore_inventory_size5000_v5/`: source cluster
  IDs, full-source sizes, region/split inventory and training-window exposure.
- `/home/sky/data/analyses/task040_b0_chip_validation_clusters_v3/`: historical
  B0 reference report.
- `/home/sky/data/analyses/task040_b0_joint_shore_size_v2/joint_report.html`:
  completed joint diagnostic and adjacent source/date/region comparison CSVs.
- Existing train/validation/test assignments and current model/report helpers.

Shared regions 001–010 have 12.20% nearshore selected training kelp versus
18.61% validation at <120 m; actual preaugmentation training appearances are
12.03% nearshore. B0 recall is 64.1% nearshore versus 84.1% offshore. These are
pooled associations; regional behavior differs and small clusters occur often
in windows despite contributing few pixels. Earlier <60 m results are a
different summary and must not be mixed with these numbers.

## User decisions and fixed experiment

The completed joint report strengthens the distance-first experiment without
changing its settings. In region 008, nearshore recall remains lower in every
size class; for interior full-source components of 1,001–5,000 and >5,000 pixels,
recall is 54.2% versus 89.3%, and 20.1% versus 89.5%, respectively. These are
nearshore/offshore portions of clusters, not necessarily distinct whole beds.
Deficits occur on 7/9 and 4/4 paired dates and survive largest-source removal.
Regions 004/007 show size-dependent deficits; 006 has a clear 11–100-pixel
deficit but mixed, acquisition-sensitive larger classes. Size alone therefore
does not explain all nearshore misses. This remains descriptive evidence, not
proof that loss weighting will solve them.

Predefined evaluation priorities: recovery of nearshore portions of large
clusters in 008; small/medium-class recovery across dates in 004/006/007; and
the resulting false-positive, offshore and global-score tradeoffs. Keep all
regions in the reports and small-cluster weighting optional. No additional
broad descriptive study is required before implementation verification.

Agreed design: labeled-positive BCE weighting with half-distance 120 m;
mapped land receives distance zero. Proposed initial screen: alpha 0, 1 and 2,
with no simultaneous small-cluster weighting. No blocking choice is needed to
write the implementation. Actual launch remains a later user instruction.
Numeric acceptable precision/IoU tradeoffs have not been agreed: report the
tradeoffs for review rather than inventing an automatic winner rule.

For each valid pixel with hard target y and effective distance d:

- Ocean with known distance: `d = min(distance_m, 500)`.
- Mapped land: `d = 0`, including labeled kelp on imperfect land masks.
- Unknown distance: neutral weight 1; report its positive support separately.
- Known-distance labeled kelp: `w = 1 + alpha * 2**(-d / 120)`.
- Background: `w = 1` everywhere, including mapped land.
- Ignore target -100, nodata and artificial padding: no numerator/denominator
  contribution. Hard labels determine weight membership, not predicted class.

Distances >=500 m are right-censored: use 500 m explicitly, not a fabricated
exact distance. At alpha 2 their weight is approximately 1.111; disclose this
constant residual offshore boost. Do not add a second distance policy mid-screen.

Compute unreduced float32 BCE and reduce over all valid pixels of each actual
training microbatch:

`weighted_bce = sum(w * bce_pixel) / sum(w)`

Total training loss remains `0.7 * weighted_bce + 0.3 * existing_dice`.
Keep smoothing=0 and pos_weight=1 in all three recipes. An all-ignored batch
returns differentiable zero. Alpha zero must equal current BCE in value and
gradients. Preserve batch pooling and gradient accumulation; do not introduce
per-image normalization or normalize across accumulation steps. Normalization
stabilizes scale but does not make gradient balance identical to the control.

| Run | Alpha | Half-distance | Maximum positive weight |
|---|---:|---:|---:|
| Fresh control | 0 | 120 m | 1 |
| Moderate | 1 | 120 m | 2 |
| Stronger | 2 | 120 m | 3 |

All runs use the same data selection, window order policy, seed 42, B0 ImageNet
initialization, augmentation, EMA, batch 12, accumulation 2, WD 0.01, peak LR 1.5e-4,
minimum LR 3e-6, five warmup epochs and 70-epoch schedule. Keep patience 20,
checkpoint epochs 4–12, best/last and existing checkpoint selection by pooled
validation IoU at threshold0.5. Early stopping can produce different run lengths;
record them. Do not resume historical B0 with a different loss.

## Implementation contract

Implementation files: `prepare/chip_distances.py` and its CLI handler,
`chips.py`, and the existing training data, transforms, run, module, loss and
loss settings files. Focused tests and three recipes accompany the change.
The command takes `--chips`, `--shoreline` and `--output`. The `distance_bce`
term exposes `alpha` and `half_distance_m` and records the fixed cap, land and
unknown policies alongside its resolved settings.

1. Add the one-pass `prepare/chip_distances.py` step exposed as
   `kelpseg prepare-chip-distances`.
   The user prefers distance information embedded in chip payloads, not runtime
   TIFF reads. Produce a fresh derived chip dataset containing the existing
   image/label arrays plus aligned distance_m and land arrays. Preserve native
   image/label values, window identities, metadata and split assignments; do not
   mutate the canonical chips or select new windows. Reuse the existing shoreline
   manifest/grid conventions and exact source/window offsets, handling original
   versus crop-local coordinates explicitly. Group work by source so its rasters
   are opened once during preparation. Keep unknown distance and native nodata
   explicit and separate from land. Missing/misaligned required source artifacts
   are actionable errors. Refuse existing output, log source/chip progress and
   counts, and publish the completed manifest atomically; no partial-work reuse.
   Account for the storage cost of a derived copy before preparing the full set.
   Use the same derived data for control and treatments. Store distances, not
   alpha-specific weights, so changing scale does not require preparing again.
   No standalone scripts/ directory or general preparation framework is needed.
2. Extend the current dataset/transform path to carry a spatial emphasis map.
   Read distance/land arrays from the same chip payload as imagery and labels;
   training must not open shoreline TIFFs. The loader resolves effective distances and the loss converts them into
   positive-pixel weights. Transform the effective distance mask with the same D4/affine geometry as image/labels, using nearest
   interpolation and neutral padding. Photometric/noise transforms must not
   alter weights. Coarse-dropout and ignored pixels are excluded using the final
   transformed target. Do not recompute distances from chip-local land masks.
   Preserve the existing random transform sequence; adding a map must not change
   the augmentation distribution between control and treatments.
3. Integrate a loss-specific distance-BCE option through the existing
   type/name/weight/parameters convention, not a parallel objective framework.
   Expose alpha and half_distance_m; the preparation recipe owns the shoreline
   input location and training selects the derived chip root;
   record cap/land/unknown policies in resolved metadata and resume identity.
   Leave Dice and all unrelated losses unchanged. Ordinary inference bundles
   must remain independent of shoreline files and training-only weights.
4. Validation loss remains the ordinary unweighted BCE/Dice diagnostic for
   comparable curves; validation confusion metrics are unweighted. Clearly log
   the optimized weighted BCE separately from unweighted training BCE so curves
   are not mislabeled. Document this training/evaluation distinction explicitly.
5. Prepare three standalone TOMLs under
   `configs/train/distance_weighting/`, with distinct names and the same
   derived chip root for alpha zero and treatments. Only alpha/name differ. Use W&B
   `kdorman90-ucla/kelpseg`. Do not change global defaults or existing recipes.
6. Provide a short explicit sequential train → predict-chips → report recipe,
   optionally a user-requested bounded launcher. Use a fresh output root outside
   any actively uploaded tree. Stop on failure; do not add sweep recovery,
   concurrent runs, scheduler machinery, hashes or receipts.

## Verification before production

- Preparation fixtures verify exact source-window distance/land values, unchanged
  image/label arrays, metadata/selection parity, partial edges and unknown/nodata
  handling. A bounded real preparation smoke precedes the full derived dataset.
  Verify no shoreline TIFF opens occur during training; ordinary NPZ loading
  reads the added arrays. Record disk size and preparation/loader throughput.
- Hand-calculated weights at land/0, 120, 240, 500 m, unknown and background;
  alpha zero, finite bounds, invalid settings and exact ignore behavior.
- Hand-calculated weighted BCE numerator/denominator; alpha-zero value/gradient
  parity; all-background and all-ignored batches; unchanged Dice and AMP safety.
- Fixture with spatially varying distances proves chip offsets, partial edges,
  nodata, D4 and affine alignment. Dropout/ignored support cannot contribute.
  Photometric augmentation cannot alter the weight map. No label/weight leakage
  into image channels or portable inference.
- Real bounded GPU forward/backward smoke for control and nonzero alpha;
  ordinary checkpoint save/load/resume and copied-bundle inference checks.
  Verify current recipe metadata and rejection of changed weighting on resume.
- Preview matched false-color, labels and weights before/after augmentation on
  fixed training examples, including regions 004/006/007/008 and mapped-land kelp.
- Summarize effective positive/background weight mass and normalized shares by
  region and distance using training inputs only. Distinguish raw appearances
  from weights and gradients. Check loader throughput before scheduling long runs.
- Focused tests plus Ruff format/check and all-file pre-commit. Document any
  unrelated failures. Do not run production until the user requests launch.

## Result verification and decision

Use the same 53-source/933-window disjoint validation selection, float32 inference,
EMA-selected best checkpoint and threshold0.5 for each run. Reconcile scored
support, source identities, TP/FP/FN totals and coverage across reports. Reuse
Task 040 shoreline and joint full-source-cluster diagnostics; no test predictions
or test-performance summaries. Test composition must not guide experiment choices.

Primary comparison: ocean nearshore <120 m recall and precision versus control.
Keep mapped-land kelp separate in results even though it receives maximum weight
in training. Also show unknown support, offshore recall/precision, overall IoU,
FP/FN area, predicted-area bias and wholly missed components where supported.
Use existing distance bands to reveal whether benefit extends beyond 120 m.

Read joint region × distance × full-source-size results, with source/date support
and boundary-fragment sensitivity. Emphasize 004/006/007/008 without selecting
only favorable examples. Keep FP by distance/region, not assigned to true cluster
size. Show per-source changes, dominant-acquisition sensitivity and fixed matched
log false-color examples. Evaluate the same fixed unaugmented training sample
(seed 42, three TIFFs/region) with each selected model; report shared regions 001–010
separately from training-only 011/012. A reduced gap alone is not success.

Interpretation and next decision:

- Nearshore recall rises with modest FP cost across several regions/sizes:
  candidate for confirmation, not proof of a representation cause.
- Gains confined to mapped-land labels, one source/date, or a few regions:
  inspect alignment/conditions and report the limitation.
- Recall rises while precision/offshore/global scores materially worsen:
  document the tradeoff; do not automatically adopt the stronger setting.
- Optional validation-only threshold curves may show whether reweighting mostly
  shifts the operating point. Keep 0.5 primary; do not deploy a tuned threshold
  or select using test performance in this task.
- If promising, propose one additional paired seed for control and the chosen
  alpha; obtain a separate launch instruction. The initial single-seed screen
  cannot establish a robust advantage. Keep half-distance fixed during the screen.

## Optional small-cluster follow-up

Not implemented or launched as part of the three-run screen. Revisit only after
joint results show residual size-specific misses that distance emphasis does not
address. Use saved full-source component sizes, not post-crop/post-augmentation
fragments. Start with a modest capped positive weight, not inverse-area weighting
that can overemphasize label specks. Specify size cutoff and combination rule
before running; do not silently multiply distance and size weights. Compare a
size-only treatment against the same control before interpreting a combined
intervention. Keep nearshore/size/regional effects distinguishable and record a
separate bounded follow-up contract and budget.

## Acceptance and non-goals

Acceptance: correct aligned weight maps and reductions, alpha-zero parity,
controlled recipes, portable models, readable diagnostics, and a reviewed
tradeoff summary with exact artifact paths. No promised gain is an acceptance
requirement; a negative result is valid. Keep typed functions and docstrings,
plain manifests and existing libraries. No re-chipping, new labels, sampler,
architecture/EMA/Dice changes, split changes, test scoring or automatic launch.

## Outcome

- Added `kelpseg prepare-chip-distances` with `--chips`, `--shoreline` and
  `--output`. It checks crop identities and grids, opens land/distance TIFFs
  once per source, preserves canonical image/label arrays and manifests, and
  publishes fresh NPZ payloads with float32 `distance_m` and uint8 `land`.
  Unknown distance is NaN in storage. Training loads an effective distance mask
  using a negative sentinel for unknown and padding and zero for mapped land.
- Extended the chip loader, training data/transforms, run and loss/module path.
  D4 and affine move the effective distance mask with nearest-neighbor mask
  interpolation. Final labels exclude dropout and ignore pixels. The same
  seeded image/label draws are preserved. Existing per-microbatch reduction
  and accumulation apply. Resolved loss settings and native resume identity
  record alpha, half-distance, cap, land and unknown policy. Validation uses
  ordinary BCE and Dice. Training logs both BCE components and unknown positive
  support. Portable exports keep the ordinary image-only format.
- Added the three standalone recipes in `configs/train/distance_weighting/`.
  The recipe parity test compares each with the existing B0 recipe. Read-only
  selection confirmed the reference 53 validation sources and 933 windows.
- 373 focused tests passed, including exact alpha-zero loss and gradient
  parity, hand-computed weighted BCE, ignore/nodata/partial-edge and geometry
  checks, and completed-epoch weighted resume with changed-alpha rejection.
  The weighted synthetic resume check crosses EMA activation and exactly
  matches uninterrupted current and averaged weights and optimizer/LR state.
  Ruff format, Ruff lint, all-file pre-commit and diff whitespace checks passed.
- Bounded artifacts are under `/tmp/kelpseg-task041.lnox7u/`. Five real chips
  from five TIFFs prepared in 2.57 s. Payloads grew from 10,590,788 to
  11,243,038 bytes. One timing pass took about 1.23 s for 15 canonical
  load/augment samples and 1.23 s for 15 enriched samples with zero workers.
  These are tiny local observations. A separate four-chip preview in
  `region-preview/fixed_alignment_preview.png` covers 004/006/007/008 with
  mapped-land positives and matched before/after panels. The adjacent
  `weight_mass_sample.csv` gives selected training-window appearances, weight
  mass and normalized shares by region and distance. These selected windows
  provide alignment evidence and have no population interpretation.
- RTX 3090 bf16 B0 smoke ran two optimizer updates each for alpha 0 and 2
  using batch 1, random initialization and local CSV logging. TIFF reads during
  fit were explicitly forbidden. Best/last and numbered checkpoints were
  saved. Both copied bundles predicted on CPU from a native image array.
  Both validation prediction/report paths completed on two chips each, and
  the alpha 2 fixed-train prediction/report path completed on three chips.
  The two validation smoke reports agree on source/window coverage, with
  407,394 scoreable pixels, 53,840 labeled positives and zero uncovered valid
  pixels. Per-source confusion totals reconcile with scored support.
  All three recipe previews ran on the tiny derived dataset.
- Production batch throughput, dataset-wide weight
  mass, long-run EMA behavior and scientific tradeoffs remain for the production
  screen. The two-update smoke stays before EMA activation. No production run,
  schedule, Box transfer, commit or push occurred.

Code quality follow-up separated manifest validation from chip copying,
consolidated fixed BCE settings, and simplified the weighted reduction to work
on valid pixels with one plain BCE calculation for the alpha-zero control. The
loader skips a distance array copy for full-size chips. All 373 focused tests,
Ruff, pre-commit and diff checks passed again. Five prepared payloads and three
chip manifests were byte-identical to the earlier smoke. Both tiny CUDA arms
again passed training, copied-bundle CPU inference, and validation reporting
under `/tmp/kelpseg-task041-quality.WS0ey2/`.

The user requested full chip preparation and then an eight-worker run. Added
the optional `--workers` flag, with one process as the default. Workers copy
whole sources and the parent publishes the complete dataset once. A two-worker
CLI smoke reproduced all five real payloads and manifests byte for byte. The
stopped serial staging directory is `.v1-distance500.serial-stopped` beside the
canonical release. The fresh parallel run targets `v1-distance500`.

Full preparation published on 2026-11-06 in about 28 minutes with eight
workers. `/home/sky/data/data/chips/ca_bc/v1-distance500` contains 26,573
payloads from 369 sources, totaling 67,213,951,389 bytes. Its recipe, source,
and window manifests are byte-identical to the canonical release. Preparation
recorded zero unknown-distance positive window pixels. Progress log:
`/tmp/kelpseg-task041-parallel-prep.6t4GX3.log`.

Prepared local recipes and dry-run previews in
`/home/sky/data/task041-distance-bce-v1`. All three previews agree on 8,518
eligible training windows, 933 validation windows from 53 sources, and 355
optimizer updates per epoch. The user subsequently launched all three arms.

The local launcher `/home/sky/data/task041-distance-bce-v1/run-screen.sh` uses
the prepared recipes and runs training, validation prediction/reporting, and
fixed training-sample prediction/reporting for each alpha in order. Bash
syntax and simulated stage ordering, six report outputs, and failure stopping
were verified. The user runs the launcher when ready.

The user also requested removal of the retired root LR and model-size shell
launchers, their launcher-only test, and `planet8b_image_splits.csv`. The
temporal CSV is still the default for the retained legacy TIFF comparison.
The current quickstart routes historical comparisons through their saved TOMLs.

The user reported completion of alpha 2 and requested alpha 4 and 8.
Added `configs/train/distance_weighting/alpha4.toml` and `alpha8.toml`, plus
machine-local copies under `/home/sky/data/task041-distance-bce-v1/`.
Only alpha and run name differ from alpha 2. The new local launcher
`run-alpha4-alpha8.sh` trains alpha 4 then 8, generating validation and fixed
training-sample predictions and reports after each. The 500 m residual positive
weights are about 1.223 and 1.445, respectively; maximum weights are 5 and 9.
Dry-run previews verify matching memberships and budgets. Simulated commands
verify stage ordering, four report outputs and stopping on failure.
The extension was prepared for the user to start in tmux.

## Five-arm comparison — 2026-11-07

All five user-launched arms (alpha 0, 1, 2, 4, 8) completed. Each scored the
same 933 windows, 53 sources and 215,524,030 validation pixels, with matching
source label support and coverage. All selected bundles use EMA. Selected
completed epochs were 29, 28, 28, 28, 29; runs stopped after 49, 48, 48, 48,
49 epochs respectively.

| Alpha | Nearshore recall | Nearshore precision | Nearshore IoU | Overall IoU |
|---|---|---|---|---|
| 0 | 63.79% | 82.85% | 56.35% | 68.91% |
| 1 | 67.74% | 80.31% | 58.10% | 68.89% |
| 2 | 70.44% | 77.79% | 58.65% | 69.01% |
| 4 | 75.15% | 73.46% | 59.11% | 69.03% |
| 8 | 79.51% | 68.33% | 58.10% | 68.43% |

Nearshore means ocean below 120 m. Alpha 4 has the highest pooled nearshore
IoU in this screen. Alpha 8 further recovers kelp but adds 46,525 nearshore
false positives for 20,883 additional true positives relative to alpha 4.
Its total nearshore false positives are 176,616, versus 63,255 at alpha 0.
Regional tradeoffs differ. Region 004 nearshore IoU rises from 61.66% to
66.93% at alpha 8, and 006 rises from 49.45% to 59.36%. Region 008 peaks at
alpha 1 (42.08%) and falls to 38.85% at alpha 8, while region 009 falls from
64.15% at alpha 0 to 56.02% at alpha 8.

Recovery extends to nearshore portions of interior large clusters in 008.
For size 1,001–5,000, recall is 54.97/77.43/76.02/85.25/91.57%; for >5,000
it is 24.40/32.68/37.19/50.36/61.69%. Alpha 4 and 8 improve pooled nearshore
recall versus control on all four dates in 004, all six in 006, all five in
007, and ten of eleven in 008 (one tie). Recall gains persist after excluding
the largest-support source within each of those regions. Their false-positive
cost remains part of the assessment.

Comparison CSVs, selected examples and the one-off plotting code are under
`/home/sky/data/analyses/task041_five_arm_comparison_v1/`. Typical matched
examples use the chip closest to the regional median alpha8-minus-alpha0
recall/precision changes among windows with at least 500 nearshore labeled
kelp pixels and at least 100 control misses. The 008 adverse example is
explicitly the largest added false-positive count among the eligible windows.
All figures use log-stretched NIR/red/green and threshold 0.5, with full-chip
nearshore precision and recall stated in captions. These examples describe
selected nearshore chips, not the population distribution.

## Baseline decision

The user selected the completed alpha 0 control as the current Planet 8-band
B0 baseline for California and British Columbia. It uses ordinary BCE plus Dice.
Use the portable EMA bundle from completed epoch 29 (`checkpoint_epoch = 28`
in the bundle metadata) with probability threshold 0.5.

- Run ID: `planet8-cabc-b0-distance-alpha0-70ep-20261106T213240953792Z`
- Local bundle: `/home/sky/data/task041-distance-bce-v1/runs/planet8-cabc-b0-distance-alpha0-70ep-20261106T213240953792Z/model`
- Box bundle path: `kelp-box:kelpseg/runs/task041-distance-bce-v1/runs/planet8-cabc-b0-distance-alpha0-70ep-20261106T213240953792Z/model`
- Validation report: `/home/sky/data/task041-distance-bce-v1/alpha0-val-report/report.html`

Box verification on 2026-11-10 matched the portable bundle and all 12,433
in-scope files under the experiment root, including the five runs and their
reports. The check skipped symlinks and excluded incomplete and stopped-run
folders.

The four-region review at
`/home/sky/data/analyses/task041_matched_shore_review_v1/matched-shore-four-regions.pdf`
shows selected locations where kelp may be missing from the supplied labels.
The PDF matches its Box copy. These examples identify areas for review. The
extent of label omissions and their effect on measured recall are still open
questions.

### Final code review

Removed the unused generated `planet8b_region_footprints.geojson` and updated
the LR and model-size handoff notes for the retired launchers. Ordinary BCE
uses a direct mean or sum, distance BCE keeps its weight-sum normalization,
and training and validation share one objective call.

All 385 focused tests passed, including exact alpha-zero loss and gradient
parity, alignment, checkpoint resume, and portable inference. Ruff formatting,
lint, pre-commit, and whitespace checks passed. A two-worker preparation smoke
reproduced five real chip payloads and their manifests byte for byte. A copy
of the selected alpha-zero bundle predicted one of those chips on CPU,
producing probabilities for 203,697 valid pixels. Smoke artifacts are under
`/tmp/kelpseg-task041-close.Tfrdx4`.

The final push-readiness check passed the full suite of 1,018 tests.

Next action: review researcher feedback on the four examples before revisiting
distance weighting.
