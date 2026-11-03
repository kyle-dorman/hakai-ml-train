# Task 033G: Tiny walkthrough and researcher handoff

Status: Complete and approved for commit — 2026-11-03.
Depends on: Completed 033A–033F with recorded outcomes.

Current routing update — 2026-11-03: new
[Task 034](034_gpu_machine_preparation_and_baseline_launch.md) owns GPU-machine
preparation and baseline launch. The former 034–038 roadmap is now 035–039.
Completed outcomes below retain their historical numbering; the operative
prediction handoff below is updated to 035.

## Abstract

Integrate the finished baseline workflow into a short fresh-directory researcher
walkthrough, verify package portability and close the task family. Stop before
Task034 implementation or production training.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
Shared parent and child outcomes, [quickstart](../docs/quickstart.md),
[architecture](../docs/architecture.md), [experiments](../docs/experiments.md),
[data artifacts](../docs/data_artifacts.md) and published tiny v2.

## Outputs and planned interface

Concise actual recipes, final package/legacy-consumer cleanup as replacements
permit, recorded tiny runs/bundles and a Task034 handoff. No new CLI family,
runner framework or extra dataset copies.

## Plan/spec

From an unrelated installed-package directory, fetch/use tiny v2 with fresh
outputs and explicit machine paths. Exercise chosen individual previews,
pixel stats, train/validation/save/load/resume and copied-bundle image-array
probabilities. Cover every spectral path and both training-variant selections;
preview all eight production combinations (four spectral recipes × two variants) without executing production training.
Report eligibility separately from canonical counts and geometry separately
from valid labels. Retire only obsolete code whose consumers have replacements.
Keep remaining legacy dependencies documented until later workflows replace them.
Update current docs and both queues using compact outcomes, with detailed
evidence here and external artifacts identified plainly.

## Implementation plan — 2026-11-03

1. Rehearse the installed package from an unrelated directory against tiny v2,
   using explicit machine paths, fresh outputs and sequential spectral cases.
2. Verify all four recipes and both variants, selected previews/statistics,
   bounded CPU fitting, completed-epoch resume and copied-bundle probabilities.
   Preserve the total schedule/run identity and require zero workers for resume.
3. Preview eight full-data combinations using metadata only; do not train them.
   Measure shared smoke storage and retain one representative bundle/resume pair.
4. Audit legacy consumers, run focused/package/lazy-import and repository checks,
   then update the guide and close the queues with a Task 034 handoff.

## User decisions required

No new experimental policy. Fix instructions where another researcher would
need undocumented help; do not infer authorization for GPU or production runs.

## Smoke and validation

Installed wheel/sdist outside the checkout, meaningful regression tests,
Ruff format/check, broad pre-commit and Markdown/link/diff checks. Bounded real
CPU walkthrough, fresh copied bundle and all-band/variant dry-runs pass.
Keep new training artifacts within the shared 4GiB smoke budget, running cases
sequentially and retaining one representative durable bundle/recovery pair.
Record preexisting unrelated failures and local/CUDA validation limits.

## Acceptance and non-goals

A researcher can follow short settings-based recipes without Python edits;
all child outcomes and portability limits are recorded and Task034 has a clear
bundle/preprocessing handoff. No production training, tiled inference or scoring.
Do not start another numbered task in this window. All planned commands/modules
are future interfaces until this task implements and verifies them.

## Task 035 handoff

After Task 034's local handoff, select and write the Task 035 contract in a new
chat. Its scope is image-only
tiled/georeferenced prediction from the copied `model/` bundle, not training or
scientific scoring. Start with `kelpseg.model_bundle.load_model_bundle` and
`PortableModel.predict_probabilities`; the latter already returns original-size
float32 HW probabilities from HWC native uint16 arrays up to 512×512.

- Preserve the bundle's named band order, approved cap/normalization, current/EMA
  selection and threshold .5. Detect all-native-band-zero nodata before selecting
  channels; retain NaN at invalid output pixels. Do not use legacy normalization.
- Make full source-edge coverage and small-image bottom/right padding explicit.
  Invert padding before placement, preserve source windows/CRS/transform, and
  average overlapping probabilities before thresholding once. Do not infer
  georeferencing or padding from labels; unlabeled mapping must stand alone.
- Use the local G copied bundle if available, or regenerate a tiny smoke bundle
  for offline fresh-directory checks. It is a randomly initialized bounded CPU
  smoke model, not a scientific baseline.
  The separate last checkpoint is training recovery state, not prediction input.
- Keep label scoring, source confusion counts and scientific figures in 036;
  LORO comparisons/fold-specific normalization remain 037. Retire legacy consumers
  only when their replacement workflow is present. CUDA/bf16, hardware sizing,
  optional live W&B and production fitting remain unverified locally.

Task 035 has not been implemented or started here.

## Outcome 2026-11-03

### Implementation and researcher interface

The existing installed functions and recipe-led CLI cover G; no new runner,
CLI family, dependency, hash or receipt machinery was added. Changed
`configs/train/tiny_cpu.toml` to target the guide's actual tiny-v2 outputs instead
of silently selecting full production data. The guide now includes an isolated
locked-runtime wheel installation, explicit paths, tiny statistics/training,
preview scope, copied models and the installed resume command. README/index,
architecture and queues describe the same four-recipe matrix and task boundary.
Focused tests now exercise all eight recipe/variant previews with absent payloads
and blocked model construction. Tiny-default CLI fixtures were updated.

The old “six production combinations” wording in G and its queues was stale:
four spectral recipes × two variants means **eight**. Earlier child outcomes
remain historical records; this outcome supplies their corrected handoff.
Approved preprocessing, native TorchMetrics, validation-only selection, W&B
identity and resume semantics are unchanged.

No legacy implementation could yet be retired safely. The old evaluator consumes
`src.models.smp` and its loss/optimizer helpers; the historical suite launcher
still consumes `trainer.py`, data, EMA and scheduler classes. Architecture now
records these consumers and their 034–036 replacement boundary.

### Installed data and preview rehearsal

External root: `/Volumes/x10pro/kelpseg/analyses/task033g_walkthrough_v1/`.
The wheel was installed with locked runtime dependencies under
`/tmp/task033g-installed`; commands ran from the unrelated external root.
`prepare.sh`, distribution files, `runtime.txt`, recipes, machine paths and logs
record the execution. The temporary environment can be recreated; it is not a
durable model dependency. Existing E/F evidence was left unchanged.

Old tiny output folders contained controls only, so the installed splitter and
chipper generated fresh `splits/` and `chips/` from the complete published local
tiny-v2 TIFF inputs. No new dataset download or full-data copy was needed.
There are 13 source crops and 54 retained canonical windows (31 backgrounds),
with 151,535,749 payload bytes. Preparation reads declared TIFFs; all subsequent
training/statistics/prediction accesses were restricted to active train/validation
NPZs, and preview accesses to training NPZs. Test NPZ read count is zero.

Tiny `base` has 8 candidate / 3 eligible / 5 excluded training windows;
`augmented` has 20 / 11 / 9. Both have two disjoint validation windows and seven
test windows represented only by metadata. `statistics.json` uses the 11
positive augmented training windows and 2,807,276 nonnodata pixel exposures,
capped at 5000. It does not replace the full-data normalization reference.
The existing tiny geometry remains 4,719,360 validation/test footprint pixels,
2,228,736 selected and 2,490,624 uncovered; these are geometric areas, not
valid-label support or scientific scores.

The unchanged showcase sampler correctly rejects tiny v2: zero windows meet
its visible-kelp criteria, even with `positive_samples=1`. The refusal log is
retained. Selected isolated D4/brightness/spatial-dropout previews and two
combined draws instead use one eligible full-collection training example and
two background controls, with training-only read guards. Their self-contained
galleries are `individual-previews/index.html` and `pipeline-previews/index.html`.
The guide discloses this full-data prerequisite instead of weakening criteria.
An actual combined false-color label overlay was visually inspected.

### Production planning only

All four recipes (`planet8`, `planet4`, `planet3`, `planet_RGB`) pass both
variants without opening arrays, building models or creating production runs.
Valid JSON reports and separate logs are named `production-<recipe>-<variant>`.

| Metadata | base | augmented |
|---|---:|---:|
| Candidate training windows | 15,621 | 18,311 |
| Eligible positive windows | 7,280 | 8,518 |
| Background exclusions | 8,341 | 9,793 |
| Assigned / eligible training sources | 216 / 213 | 258 / 254 |
| Validation windows | 933 | 933 |
| Test metadata windows | 1,262 | 1,262 |
| Updates per epoch / 70-epoch total | 304 / 21,280 | 355 / 24,850 |

All eight retain the same 40,571 canonical candidates, 26,573 payloads and 369
sources. Equal epochs intentionally produce different update budgets when BC
is included. No production training was executed.

### Validation

218 focused checks pass: 130 training/data/model/objective/loop/settings/runner/
resume/bundle/statistics/distribution tests plus 88 CLI/augmentation checks.
The final tiny-default settings/runner recheck passes all 46 tests. Wheel and
rebuilt-sdist runtime-only installs execute outside the checkout, including
copied-bundle probabilities and fresh-process lazy-import blockers for help,
version and every subcommand. Existing resume checks verify exact CPU state,
same schedule, zero workers, relocation and preserved run identity. Only native
CPU/worker/checkpoint notices and a Lightning pytree deprecation were observed.


### CPU fitting, save/load and completed-epoch resume

All eight tiny recipe/variant cases ran sequentially with real SegFormer B3,
512 canvas, approved preprocessing, CPU float32, no pretrained download, zero
workers, two total epochs, one training/validation batch per epoch and one
optimizer update per epoch. `result-<recipe>-<variant>.json`, resolved recipes,
run records and CSV logs retain the exact settings. Each completed model was
loaded and produced real validation-image probabilities with correct shape,
finite range and native-nodata NaNs. These two-update checks do not reach EMA
update 101; the focused tests and E/F outcomes retain that separate evidence.

The representative RGB augmented run
`g-planet_RGB-augmented-20261103T135014288178Z` deliberately raised at the start
of epoch 1, after the epoch-0 checkpoint was complete (global step 1). The
installed CLI resumed with the identical two-epoch schedule and run ID to global
step 2. The harness is external; no interruption option was added to training.
A complete epoch-0 snapshot was copied while the rehearsal process was paused,
then validated for completed-epoch state and relocated installed resume preview
with NPZ reads forbidden. Durable representative pair:

- Selected portable bundle: `copied-model/` under the external root above.
- Resumable complete run:
  `completed-epoch-snapshot/g-planet_RGB-augmented-20261103T135014288178Z/`,
  including distinct `checkpoints/best.ckpt` and `checkpoints/last.ckpt`.
  `recipes/retained-resume.toml` selects its relocated paths; preview evidence is
  `retained-resume-preview.json`. This snapshot has one epoch remaining.

`image.npy` and `probabilities.npy` retain the representative 512×512 image-array
check. A separate installed Python `-I` process ran from
`/private/tmp/task033g-image-only`, blocking networking, recipe/checkout access
and NPZ reads. It loaded only the copied bundle and supplied image array and
matched saved probabilities bitwise (maximum error 0), recorded in
`copied-process-evidence.json`. No labels or original training configuration
were needed. `payload-reads.json` and `preview-evidence.json` record zero test
payload accesses in model/statistics/preview workflows.

Redundant completed-case checkpoints and model exports were removed after their
checks; compact case evidence remains. E/F evidence was untouched. Counting
**all E/F/G files**, not only model files, the monitored peak was
**4,181,996,292 bytes**, below **4,294,967,296 bytes (4 GiB)**. Final shared size
was **2,932,549,574 bytes**, including **1,503,246,431 bytes** for G. `budget.json`
records the scope and measured peak. Runtime environments are temporary tooling,
not smoke artifacts. No extra production dataset copies or uploads were made.

### Closure and limits

Ruff format/check, all-file pre-commit, Markdown file/anchor and shell syntax
checks, and `git diff --check` pass. Fixed three preexisting D/E/F outcome-anchor
links in the current queue and the README's stale three-recipe summary. No
unresolved correctness failure remains. The tiny showcase limitation is explicit
in the guide; the full-data selected preview is the bounded alternative.

Routine operation stays in ordinary TOML and installed commands. Task 033A–G is
complete; local checks establish CPU plumbing and portability, not scientific
accuracy, production CUDA/bf16 behavior, throughput, memory sizing or live W&B.
No production fitting, tiled/georeferenced inference or scientific scoring ran.
**Exact next action:** select Task 034 in a new chat, write its image-only tiled
prediction contract using the handoff above, and implement only after selection.
Stop here; the user approved task closure and committing the reviewed changes.

The user confirmed that the copied model and completed-epoch snapshot are
disposable test artifacts, not relocation dependencies. No Task 033G Box upload
is required. Existing published datasets and tiny inputs support a fresh smoke
on another machine after installing the committed package and updating machine
paths. Local smoke artifacts remain untouched; no deletion or upload was performed.


### CI follow-up — 2026-11-03

The user requested repair of the failing GitHub Checks workflow. The observed
[run](https://github.com/kyle-dorman/hakai-ml-train/actions/runs/41645083711)
tested the earlier 033E commit `59557f6`: 612 passed and six failed. Five help
assertions compared raw ANSI-colored output with literal option names; the
distribution test exported pinned requirements that still needed registry-index
metadata absent from the otherwise populated offline cache.

`tests/test_package_cli.py` now compares option names after Click removes ANSI
formatting. This preserves normal colored help and the existing lazy-import
checks. `tests/test_distribution.py` exports the same frozen runtime dependency
set as `pylock.toml`, preserving exact artifact URLs and hashes instead of
requiring registry rediscovery. Hash checking, offline execution, isolated wheel
and rebuilt-sdist installs remain enabled. CI already pins uv 0.12.12, which
supports this export/install format; no runtime code, lockfile, dependency or
workflow policy changed.

The five help failures were reproduced locally with `NO_COLOR` unset,
`TERM=xterm-256color`, `FORCE_COLOR=1` and `GITHUB_ACTIONS=true`; all 22 CLI tests
pass after the fix under those same settings. An isolated cache with wheel
artifacts but no simple-index metadata reproduces the requirements-file failure
and installs all 68 runtime packages offline from the pylock export.

Final follow-up validation: all **640 tests pass** with CI-like forced-color and
offline settings (230.63 seconds). The 23 focused distribution/CLI checks also
pass, and an independent complete wheel/sdist test passes with all simple-index
cache directories excluded (211.92 seconds). Ruff format/check, all-file
pre-commit and `git diff --check` pass. Existing dependency/Lightning warnings
remain warnings. GitHub has not rerun these local fixes; remote success remains
unverified until the changes are pushed and Checks completes. Task 034 remains
unstarted.
