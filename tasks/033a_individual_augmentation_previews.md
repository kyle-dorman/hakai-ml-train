# Task 033A: Individual augmentation previews

Status: Complete - 2026-11-02. Isolated previews and final quality pass complete; user-approved policy closed in 033B.
Depends on: Completed Task 032B; shared Task 033 decisions. No model/stats-cleanup dependency.

## Abstract

Build the preview tool first, using the same small transform functions later
training will call. Show each operation independently at several strengths.
Stop with a gallery for user review; do not stack or select production settings.

## Read and inputs

Follow AGENTS → docs/index → docs/todo → tasks/README, then the
[shared Task 033 decisions](033_baseline_training_and_portable_models.md).
The shared parent and [experiments](../docs/experiments.md), implemented
chip/band/split portions of [quickstart](../docs/quickstart.md), and
[documentation](../docs/documentation.md). Use published chip/split metadata and
tiny v2 or a small declared subset of full training chips. The separate estuary
transforms file is reference only; no estuary package dependency or edits.

## Current outputs and interface

- `src/kelpseg/augmentations.py`: small raw-data adapter around actual stock
  Albumentations class calls; no project-written augmentation kernels.
- `src/kelpseg/augmentation_debug/trials.py`: readable literal native class settings,
  fixed diagnostic parameters, class identity and realized-parameter recording.
- `src/kelpseg/augmentation_debug/preview.py` plus the sampler, display export,
  contact sheets and offline HTML viewer. `examples/augmentation_previews.py`
  is the short Python entry point. There is no installed preview CLI or custom
  TOML settings schema. The guide documents actual use.
- Preview-only helpers and HTML are grouped under `src/kelpseg/augmentation_debug/`;
  the approved raw adapter and training factory remain outside that folder.
- Training-only selected-window CSV, library/domain/version metadata, exact
  parameters and native PNG views outside Git. Existing sources are unchanged.

The current implementation and outcome are the **2026-11-02 stock
Albumentations replacement and wider stock sweeps** below. Earlier outcomes describe superseded custom
implementations and retained historical galleries; they do not define current
parameter meanings or APIs.

## Approved handoff

The selected ranges and composition live in the
[shared parent](033_baseline_training_and_portable_models.md#limits-selected-after-isolated-review).
The user approved the combined pipeline in 033B; the final native recipe is
saved in `configs/augment/baseline.json`. Model training remains later work.
The model normalization reference and final 5000 cap remain unchanged; stock
augmentation clipping is distinct from the model cap and 2000 display ceiling.

## Outcome — 2026-10-28

Implemented the five isolated families through plain NumPy functions. The
installed command reads training payloads only, renders original/identity and
trial strengths, and writes a plain selected-window CSV and realized-parameter
JSON alongside PNGs and a linked HTML index. Production ranges/probabilities,
additive lower bound and band-dropout fill remain undecided. No transforms were
stacked; no model imports, model training or later numbered task occurred.

### Repository changes and simplicity

- Added `preprocessing.py` with the parent's exact native-order means/stds and
  final upper cap 5000. The chip loader now computes native validity through
  that helper once before selection and exposes `valid_mask`, preserving the
  existing native-only `nodata_mask` and explicit true-size/padding metadata.
- Added `augmentations.py` for paired square symmetry, additive raw brightness,
  explicit spatial holes, native-name channel shifts and single-band fades to
  zero/mean. Inputs are copied; only spatial dropout erases targets to -100.
- Added small `augmentation_inputs.py`, `augmentation_trials.py`,
  `augmentation_panels.py` and `augmentation_preview.py`; no policy framework,
  hashing/receipts, recovery or partial reuse. The TOML schema lives in one
  loader. Existing source/window joins are reused. Each file has one role.
- Added lazy `cli/augmentations.py` registration and
  `configs/augment/preview.toml`. Promoted matplotlib from the temporary legacy
  dependency group to runtime solely for implemented PNG rendering; updated
  `pyproject.toml`/`uv.lock`. No legacy training implementation was replaced.
- Added three focused test modules; extended loader mask checks and repaired a
  CLI help assertion that confused the word “training” with an installed train
  command. Updated README, index, quickstart, experiments and task routing.

### Initial external gallery — superseded by the usability follow-up

`/Volumes/x10pro/kelpseg/analyses/task033a_individual_augmentation_previews_v4/`
contains `index.html`, `gallery.json`, `selected_windows.csv`, and one folder
per window with `parameters.json` plus twelve PNG contact sheets. The final
collection has **192 panels / 1,168 displayed settings** from 14 positive
training windows spanning all 12 regions and two separately labeled background
controls (BC012 and CA008). All 16 selected windows have distinct sources. The 211 files total
133,647,038 bytes.
Thin/sparse/dense descriptors are foreground-count sampling proxies, not
morphological classifications. Partial-edge and native-nodata cases are present.
Inputs are the existing `data/chips/ca_bc/v1` and
`data/splits/ca_bc/v1/assignments.csv` under the same external root.

Every operation starts from unmodified raw data; spectral views reuse the same
named draws. All eight band-dropout sheets include affected-band grayscale so
bands absent from RGB/false color remain visible. Display limits are frozen
1st/99th percentiles from subsampled positive training pixels after the cap;
this color display clips separately from model preprocessing. Raw negatives are
retained and counted. Records include original identity, true size/padding,
exact physical-band shifts, cap/negative counts, raw/capped/normalized ranges
and remaining support. Native validity is never redetected after augmentation.

### Validation and limits

- 151 focused augmentation/input/preview, chip-loader, package CLI, split and
  installed-distribution checks passed. After close-up and loader refinements,
  37 affected preview/loader checks passed; all eight preview checks passed
  again after final label-format changes.
- Ruff format/check, all pre-commit hooks and `git diff --check` passed.
- Real-gallery numerical audit verified training-only identities, all original/
  identity metrics, unchanged photometric/band-dropout label/valid support,
  exact normalization constants and the expected panel list. Original capped
  values are exercised in training_09 (198 values) and training_13 (3,436).
- Actual PNG review covered all five families, sparse support, partial-edge
  paired geometry, BC background, cap counts, NIR dropout and rededge dropout
  absent from both spectral composites. Fixed an edge-close-up omission and
  gave hidden spectral bands grayscale rows; improved long title wrapping.
- The guide explains ordinary settings, outputs, errors and Python helpers.
  No Box publication, accuracy claims or production policy selection occurred.
  Source data remain unchanged; focused fixtures verify byte preservation.

Exact next action: stop here. In a separately selected **033B**, review this
isolated gallery with the user and record production strengths, probabilities,
additive lower-bound and band-dropout decisions before any combination checks.

## Viewer usability follow-up plan — 2026-10-28

The user could not judge the small contact sheets and requested browsing one
augmentation family through all 16 examples. Improve the existing 033A viewer;
this is not production-policy review or Task 033B implementation. Keep the trial values, transforms and model normalization unchanged. The
user subsequently requested a raw 0–2000 display ceiling, stronger kelp
examples, clean/labeled zoom controls and red/NIR-only dropout previews; these
requests supersede the initial sample/stretch and all-band display plan. Add separate
full-resolution display PNGs, an offline HTML viewer with large paired original/
trial images, family/strength/view selection, previous/next and keyboard example
navigation, named-band selection, close-ups and accessible numeric details.
Keep contact sheets as optional exports. Use a plain packaged HTML template and
small display-export functions; no web framework or server requirement. Generate
a fresh external gallery and verify actual browser interactions and screenshots
before handing it back. No production decisions are inferred from this feedback.

## Viewer usability follow-up outcome — 2026-10-28

The initial sheets were too small and the low-support examples were not useful
to the user. The current gallery is:

`/Volumes/x10pro/kelpseg/analyses/task033a_individual_augmentation_previews_v5/index.html`

- Added `augmentation_display.py` for native-resolution view PNGs and a plain
  packaged `augmentation_viewer.html` template. `augmentation_preview.py` now
  embeds the records for offline `file://` browsing; no server, framework,
  CDN or separate installation is needed. Original/identity and unaffected
  spectral views reuse the same exported image paths. Contact sheets remain
  optional exports rather than the main review interface.
- The viewer shows one augmentation at a time with large paired original/trial
  images. Previous/next buttons, an example selector and arrow keys flip all
  16 examples while preserving strength, view and close-up. Enlarged comparison
  has its own navigation and clean/label controls. Labels toggle on the same
  RGB or NIR base, including at the 96-pixel close-up; geometry retains the
  corresponding transformed footprint.
- Per user feedback, display clipping is now fixed raw **0–2000**, shared by
  every example and strength. The model cap stays **5000** and all exact
  normalization values are unchanged. The default NIR/red/green view shows kelp
  as red without labels. This changes display only, not source data or the
  mathematical augmentation trials.
- Replaced tiny foreground examples with 14 training windows containing
  **28,029–68,498 labeled kelp pixels**, or **10.7–26.7%** of their true area.
  Sampling favors roughly 25% kelp, requires at least 10%, limits nodata to
  25%, and retains context by limiting labeled foreground to 80%. They span
  eight regions with BC, native nodata and a partial edge. Two separately
  labeled low-nodata background controls remain last. All 16 sources differ.
  This is showcase sampling for review, not evaluation sampling or a new
  training eligibility rule. Actual clean-image candidate montages were inspected.
- `band_dropout_bands` in the strict trial recipe now selects **red and NIR**,
  as requested. Shared functions still understand every native physical band;
  production eligibility/fill/probabilities remain undecided.
- Current artifacts: 96 optional contact sheets, 592 displayed settings, 1,696
  native-view PNGs, selected-window CSV and per-window parameter JSON. The
  initial 1,811 files total 523,861,627 bytes.
- Extended display/input/preview and installed-wheel checks, including exact
  quantized view pixels, same-base RGB/NIR label overlays, display ceiling
  versus model cap, meaningful foreground selection and packaged HTML access.
  Browser interaction/screenshot evidence and final checks are recorded below.

Exact next action: user reviews the improved viewer. No production choices
were recorded and 033B remains unstarted.

### Follow-up verification

101 focused display/input/preview/augmentation, loader, CLI and installed-
distribution tests passed. The wheel includes the HTML template. Real-gallery
metadata checks verified every native-view path, all original/identity
settings, unchanged label/valid support for photometric and band dropout, all
training identities, the red/NIR-only preview list and exact parent constants.

The actual offline page passed headless Chrome interaction checks with no
browser errors: five family tabs, red/NIR selection, previous/next and arrow
navigation, retained strengths/views, 677×677 desktop panes carrying native
512-pixel images, clean/labeled zoom, 96-pixel close-ups, navigation inside zoom,
explicit final background controls, and no horizontal overflow at 390-pixel
mobile width. Label toggles loaded the matching NIR overlay rather than switching
the underlying colors to RGB. Inspected browser screenshots are retained in
the gallery's `review_screenshots/` directory. Ruff, pre-commit, documentation
link checks and `git diff --check` passed.

Stop here for review of the improved viewer; no 033B policy selection occurred.

## Additional isolated preview ideas plan — 2026-10-29

The user explicitly authorized gain, blur, noise, RandomContrast and
RandomSharpness ideas in the preview tool, without selecting them for
production. This supersedes the earlier blur/noise exclusion for these isolated
previews only. Keep one spatial dropout hole, the same kelp-rich training
examples, red/NIR-only band dropout, 2000 display ceiling and 5000 model cap.
No combinations, training or production probabilities are authorized.

Add small shared functions in `augmentation_photometric.py`: uniform gain;
contrast around each physical band's original valid-pixel mean; masked
spatial Gaussian blur (no spectral mixing); seeded independent per-native-band
Gaussian noise; and sharpness as blurred + factor × (original − blurred), with
factor 1 identity. All preserve original labels/validity and invalid fill.
Spatial filters normalize by valid-pixel weights so nodata/padding never
bleed into valid pixels. Apply the existing final model cap and normalization
after each isolated trial, retain negative values, and disclose all parameters.

Trial-only strengths: gain/contrast [0.8, 0.9, 1, 1.1, 1.2]; blur sigma
[0, 0.4, 0.8, 1.2] source pixels; Gaussian noise standard deviation
[0, 10, 25, 50] raw units; sharpness [0, 0.5, 1, 1.5, 2] with a fixed
1-pixel Gaussian base. Draw noise in native band identity order with the same
seed/draws across strengths and spectral selections. These imitate familiar
contrast/sharpness factor semantics but are explicit multispectral functions,
not RGB-only library transforms or a random training policy.

Promote SciPy only for its implemented Gaussian spatial filter. Extend the
strict recipe schema, isolated trial generator and existing offline viewer.
Use focused scientific tests (constant fields/mask edges, isolated impulse,
paired masks, factor identities, native-name noise replay, raw negatives and
cap boundaries), then generate a fresh real gallery and inspect the added
families in actual browser comparisons and clean close-ups. Update the guide
and outcome; stop for user review before 033B.

## Additional preview ideas outcome — 2026-10-29

Added five exploratory options to the same offline comparison viewer: **gain,
contrast, blur, noise and sharpness**. They are visible ideas for review, not a
selected production policy. One spatial dropout hole remains; there are no
combinations, new model workflows or training runs.

- New `augmentation_photometric.py` contains five plain shared array functions.
  Gain applies one factor across bands. Contrast changes deviation from each
  band's original valid raw mean, with that mean recorded by physical name.
  Blur filters spatial axes only and normalizes by filtered native validity,
  excluding nodata/padding. Noise uses independent native-band Gaussian fields
  seeded by `SeedSequence([seed, native_band_index])` and replays the same draws
  across strengths and spectral selections. Sharpness is a masked Gaussian
  base plus factor × (original − base). Original targets/validity/fill and
  source arrays remain unchanged; raw negatives and overshoot are retained
  until the existing final upper cap.
- The strict flat recipe schema, `augmentation_trials.py`, display export and
  HTML template now expose all five additions independently at identity and
  multiple trial strengths, with short definitions and actual parameter/count
  records. Gain/contrast factors are 0.8/0.9/1/1.1/1.2, blur sigma is
  0/0.4/0.8/1.2 source pixels, Gaussian noise sigma is 0/10/25/50 raw units,
  and sharpness factors are 0/0.5/1/1.5/2 using a fixed one-pixel Gaussian base.
  Factors 1 are identity; blur/noise zero are identity. Production ranges and
  probabilities remain unselected.
- Promoted SciPy to runtime dependencies in `pyproject.toml`/`uv.lock` solely
  for the implemented Gaussian spatial filter. There is no Torchvision/ML
  dependency in preview execution; these are explicit multispectral operations
  rather than RGB-only contrast/sharpness wrappers. Added focused photometric
  tests, expanded recipe validation checks and an installed-runtime filter
  probe in both wheel/sdist environments. Updated quickstart and shared scope
  contracts to reflect the user's explicit extension.
- Improved automatic 96-pixel close-ups to favor visible kelp boundaries with
  surrounding water, rather than very sparse fringes. Geometry moves that
  same footprint with the labels/masks. Spatial dropout still uses one fixed
  foreground-anchored hole per nonidentity trial, with realized coordinates
  in metadata. A focused close-up regression covers this visibility requirement.

### Current external artifact

`/Volumes/x10pro/kelpseg/analyses/task033a_individual_augmentation_previews_v7/index.html`

The same 14 kelp-rich training windows and two background controls from v5
remain in the same order. The display ceiling remains raw **2000**; model
preprocessing retains the exact approved **5000 cap and normalization constants**.
Red and NIR remain the only band-dropout previews. Ten operation tabs correspond
to eleven per-example families because red/NIR have separate parameter records.
The gallery has **176 optional contact sheets / 1,040 displayed settings**, with
full-resolution clean/labeled PNGs and exact identity/parameter metadata.

### Validation

151 focused augmentation/input/preview/display tests passed, plus 51 loader,
CLI and installed-distribution tests. Both installed runtime probes verify that
masked Gaussian filtering works outside the checkout without the legacy ML
environment. After refining close-ups, all 14 affected preview/display checks
passed, including the new visible-boundary regression. Tests cover factor
identities, contrast mean preservation, spatial impulse filtering and constant
fields at mask edges, absence of band mixing, native-name noise replay, invalid
fill and source preservation, raw negatives/overshoot and final cap behavior.

Real-gallery checks verify the same selected training identities as v5, each
family's exact original/identity equivalence, preserved labels/validity for all
new photometric operations, one spatial hole, existing view paths and unchanged
model constants. Final generation wrote 3,043 core files / 973,360,453 bytes, including 2,848
native-view PNGs. Browser evidence is retained alongside them in
`review_screenshots/`.

Exact next action: review these ideas with the user. Do not infer production
selection or start 033B from their presence in the viewer.

Final v7 browser checks passed with zero browser errors: ten operation tabs;
all five new families at identity and two nonidentity strengths; exact original/
identity browser pixels; visible strength changes and preserved label/valid
counts; same-strength example navigation; clean/NIR-label zoom; red/NIR-only
dropout; both background controls; and 390-pixel mobile layout without overflow.
Actual strong-trial clean close-ups were inspected for all five additions. The
revised boundary crops visibly contain kelp and surrounding water. Ruff format/
check, all pre-commit hooks, documentation file links and `git diff --check`
passed. No production decision, combination or training was performed.

## Stock Albumentations replacement plan — 2026-11-02

The user explicitly requires off-the-shelf Albumentations implementations and
their actual parameter meanings, replacing the custom augmentation math. This
supersedes the earlier hand-written transforms, masked Gaussian kernels,
negative-preservation semantics and custom trial settings. Keep the large
exploratory viewer; no production policy or combined pipeline is selected.

Pin the installed `albumentations==2.0.8`. Replace `augmentations.py` with one
small data adapter: native uint16 → float32 / 65535, the actual stock class
call, then restore raw units and invalid fill. The final model cap remains
5000 after augmentation and display remains 2000. Stock pixel transforms clip
unit values to [0,1], including a raw-zero lower bound; stock spatial filters
see zero nodata/padding rather than a bespoke valid-weighted kernel. These
changes must be visible in the viewer/guide. Use int8 validity as an additional
mask target, so stock CoarseDropout's -100 target fill marks holes invalid too.
Only D4 elements and explicitly named dropped bands need fixed sampler
parameters; use the actual class parameter/application methods, no subclasses
or reimplemented kernels. Normal application calls the class directly.

Use literal stock constructors with fixed native parameter ranges in
`augmentation_trials.py`, and record public `albumentations.to_dict()` kwargs
plus realized parameters/seeds. Fixed strengths call the same methods that
random training will call. Stock RandomBrightnessContrast contrast-only is
gain: merge the duplicate gain/mean-centered-contrast ideas. Stock Sharpen uses
its native alpha; ChannelDropout removes full bands, so delete partial fades
and speculative mean-fill behavior. Keep one stock CoarseDropout hole and
red/NIR-only diagnostic drops. Use stock AdditiveNoise for independent constant
channel shifts, GaussNoise and GaussianBlur for their respective ideas.

Remove the custom photometric module and its implementation-specific tests,
strict custom TOML trial schema/config, and the installed preview CLI handler.
Keep the sampler and rendering helpers small. Add one readable
`examples/augmentation_previews.py` entry point with explicit paths and the
shared generator function; the guide points to the native constructor settings.
Replace mathematical unit tests with focused direct-stock parity/mask/scale
checks. Generate a fresh gallery on the same training examples and verify the
actual browser and pixels. A later combined-training-pipeline UI is deferred
until augmentation selection, as requested. Close 033A again and stop.

## Stock Albumentations replacement outcome - 2026-11-02

Replaced every project-written augmentation kernel with actual pinned
**Albumentations 2.0.8** classes/functions. The exploratory viewer now exposes
the real native constructor values; no later translation of custom gain,
contrast, noise or sharpness strengths is required. Production selection and
the later combined training-pipeline viewer remain unstarted.

### Readable implementation and removals

- `augmentations.py` is a 102-line raw-data adapter and compact parameter
  serializer. It calls the real class normally. Only explicit D4 elements and
  diagnostic red/NIR choices use stock parameter/application methods with fixed
  sampler values. No subclasses, patched methods or replacement kernels.
  Public `albumentations.to_dict()` supplies constructor metadata; actual
  applied parameters and seeds are saved.
- `augmentation_trials.py` contains literal native stock constructors and fixed
  ranges next to explanatory comments. The actual class handles sampling.
  Gain/contrast share one `RandomBrightnessContrast` sweep; old per-band-mean
  contrast is gone. `Sharpen(method="gaussian")` uses native alpha.
  `ChannelDropout` fully removes one band with zero fill, without half-fades
  or custom mean fill. `AdditiveNoise` replaces bespoke channel shifts.
- Removed `augmentation_photometric.py`, custom mathematical tests, the shadow
  TOML schema/config and schema tests, and installed preview CLI registration.
  Removed direct SciPy runtime promotion. The dependency is now pinned
  `albumentations==2.0.8`, moved out of the legacy group in pyproject/uv.lock.
  Shared cap/normalization and native chip validity stay separate and unchanged.
- `examples/augmentation_previews.py` is a 28-line exploratory entry point with
  explicit paths, seed and sample count. Run with `uv run python` after choosing
  fresh output. There is no policy framework, registry, recovery system or new
  CLI. The guide and shared contracts describe these readable sources.

### Explicit stock semantics

Native uint16 is converted to float32 / **65535**, preserving values above 5000
before augmentation. Native bands are processed before spectral view selection.
The adapter carries labels and int8 validity as mask targets; stock -100 hole
fill becomes false validity. It restores raw units and zero invalid fill.
The final model cap remains **5000** and the color display alone is **0-2000**.
Stock photometric clipping includes a raw-zero lower bound. Stock spatial
kernels include zero nodata/padding and can darken adjacent valid pixels.
These are disclosed library behaviors, not bespoke replacements. No nodata
is redetected after augmentation.

### Current external gallery

`/Volumes/x10pro/kelpseg/analyses/task033a_albumentations_previews_v1/index.html`

The same 14 kelp-rich training windows and two background controls retain their
v7 identities and ordering. The gallery has **nine tabs / ten per-window
records**, **160 optional sheets / 848 settings**, and **2,208 native-view PNGs**.
Core generation wrote **2,387 files / 796,343,165 bytes** before browser proof
images. Version, native constructor kwargs, realized/fixed parameters and seeds
are visible. Large clean/labeled views and navigation remain intact. Earlier
custom galleries are historical evidence; use this stock gallery for review.

### Validation and limits

- 101 focused adapter/sampler/display/preview/loader/CLI checks passed, plus
  the runtime-only wheel/sdist test. Adapter tests compare actual direct stock
  output for 8/4/3 bands rather than testing independent formulas. They cover
  source preservation, paired D4 masks/padding, named dropout, ignored holes,
  unchanged photometric targets/validity, stock clipping and blur boundaries,
  and no model pre-cap (raw 6000 times 0.8 becomes 4800).
- Installed probes compare real GaussianBlur output with the adapter, verify
  packaged HTML/source and exclude application-model imports. Default CLI help
  remains lightweight with no preview command.
- Real-gallery audit verified class/version, view paths, original/identity
  equivalence, unchanged photometric target support, one stock hole, full
  red/NIR drops, same training identities and exact model normalization.
- Actual file:// browser checks passed without errors: native parameters/version,
  identity pixel equivalence, nonidentity changes, all 16 examples, clean/label
  zoom and mobile layout without overflow. Stock blur/noise/Sharpen and native
  parameter screenshots were inspected and saved in `review_screenshots/`.
- Ruff, pre-commit, documentation links and `git diff --check` passed. No source
  data, Box publication, model/training run or production policy changed.

Exact next action: separately select 033B to review actual stock operations and
native ranges/probabilities. Build the requested combined training-pipeline
viewer only after those choices, using these real classes.

## Wider stock sweeps plan - 2026-11-02

The user requested broader brightness, blur, Gaussian noise and channel-shift
previews through the pinned library defaults, and more coarse-dropout holes
and sizes. This extends isolated exploration only; prior proposed training
values and N selection remain undecided. Keep actual Albumentations classes,
the same 16 training examples, 65535 input scale, final 5000 model cap and
2000 display ceiling. No combined pipeline or training is started.

Expand literal native sweeps gradually, retaining the earlier reference values:
brightness +/-0.0025/0.005/0.01/0.02/0.05/0.1/0.2 plus identity; blur sigma
0.4/0.5/0.8/1.2/1.5/2/3 plus NoOp; noise std 0/0.00015/0.0004/0.0008/
0.002/0.005/0.01/0.02/0.05/0.1/0.2/0.3/0.44; channel-shift amplitude
0/0.0004/0.001/0.002/0.005/0.01/0.02/0.05/0.1. Coarse dropout gets separate
size and count sweeps: sides 0.05/0.1/0.2/0.25/0.35/0.5 at four holes, and
1/2/4/8/16 holes at side 0.25. Each is one stock class, not transform stacking.

Keep the larger menus readable with a native-value selector for long sweeps
and a coarse size/count mode selector. Preserve seed and actual realized
parameters. Add focused endpoint/isolation/hole-mask checks, then generate a
fresh gallery and inspect browser interactions, extreme outputs and paired
masks. Update guide/outcome and stop for user review.


## Wider stock sweeps outcome - 2026-11-02

Expanded only the isolated stock previews requested by the user. Brightness
reaches +/-0.2, GaussianBlur sigma reaches 3 pixels, Gaussian noise standard
deviation reaches 0.44, and independent constant channel-shift amplitude reaches
0.1. Intermediate native values retain the earlier small reference strengths.
CoarseDropout now compares side fractions 0.05/0.1/0.2/0.25/0.35/0.5 at four
holes, and counts 1/2/4/8/16 at side fraction 0.25. Each trial still calls one
actual stock class on the original data; no stacked pipeline was added.

Changed `augmentation_trials.py`, `augmentation_viewer.html`, the small
parameter serializer in `augmentations.py`, the example output path and focused
preview tests. Longer strength sweeps use a dropdown, and CoarseDropout has
separate count/size modes. Sixteen realized hole rectangles remain explicit in
JSON. Updated quickstart, shared parent and task routing to match.

Current review gallery:
`/Volumes/x10pro/kelpseg/analyses/task033a_albumentations_previews_v2/index.html`.
The earlier v1 gallery is preserved. The same 14 kelp-rich training windows and
two separately labeled background controls produce nine tabs / eleven
per-example family records, **176 optional sheets / 1,456 settings / 4,512
native PNGs**. Core output is **4,707 files / 1,425,100,414 bytes**, before
browser evidence. Inputs, physical band identity, exact normalization and final
5000 cap are unchanged; display remains raw 0-2000, and stock input scale is
65535. No validation/test payloads are read.

All 53 focused adapter/input/display/preview tests pass. The real-gallery audit
verified every referenced asset, identical selected rows/order, identity
metrics/assets and unchanged nonspatial target support. Reconstructing every
recorded coarse hole against the 16 training payloads reproduces exact valid,
foreground, scoreable and ignored counts for all 176 nonidentity coarse trials.
All native endpoint kwargs and exact parent normalization constants match.
Ruff format/check and all pre-commit hooks pass. Actual generated extreme blur,
noise, channel shifts and labeled 16-hole images were inspected: the widest
noise/shift/brightness values overwhelm this dark imagery as expected; the
smaller steps remain available for review.

Earlier proposed maxima (brightness -0.0025..0.005, gain 0.2, blur 1.2px,
noise std 0.0008, Sharpen alpha 1, four holes/side 0.25, shift 0.002 and channel
dropout) are discussion references, not finalized production settings. The user
proposed always applying D4 and choosing N other operations; N remains
undecided. The wider sweeps do not silently replace those proposals.

Exact next action: review this wider isolated gallery with the user, then
separately select 033B to settle operations, native ranges and selection policy.
Build the requested combined-pipeline viewer after those choices. No 033B
implementation, combined transform policy, production probabilities or model
training was started.


Actual offline-browser checks also passed with zero browser errors: long native
value selectors, both coarse modes, strength/mode/view persistence across
examples, 16-hole and side-0.5 targets, clean/NIR-label close-up zoom, all 16
examples and 390-pixel mobile layout without horizontal overflow. Inspected
browser screenshots and check results are retained in the v2 gallery's
`review_screenshots/`. Documentation file links and `git diff --check` pass.

## User limit review - 2026-11-02

After inspecting the wider gallery, the user retained brightness
**-0.0025 to +0.005**, selected maximum blur sigma **1.5 px**, Gaussian noise
standard deviation **0.002**, channel-shift amplitude **0.01**, and retained
coarse-dropout maxima **4 holes / 0.25 side fraction**. Recorded these in the
shared parent; the wider exploratory gallery and literal trial sweeps remain
available for comparison. No new artifacts or pipeline code were needed.

Earlier gain/Sharpen/channel-dropout proposals are unchanged. N and remaining
sampling/dropout choices are still open. This records user feedback on 033A;
033B implementation and the combined-pipeline viewer remain unstarted.
Documentation links and `git diff --check` pass. Exact next action: finish
policy choices with the user before implementing the combined preview.

The user then selected **SomeOf(n=2)** after always-on D4. Record the exact
stock composition as `D4(p=1)` followed by
`SomeOf(..., n=2, replace=False, p=1)`, with child transforms at `p=1` so exactly
two distinct extras run. Verified pinned Albumentations 2.0.8 source: SomeOf
selects uniformly, honors child probabilities, and executes selected children
in configured list order. N is now settled; remaining strength sampling,
dropout eligibility and configured order are still later policy details.
This updates decisions only; the combined viewer and training remain unbuilt.

The user also selected any model-input band as eligible for channel dropout,
with at most one band removed. When this operation is chosen by SomeOf, use
stock `ChannelDropout(channel_drop_range=(1, 1), fill=0, p=1)` and restrict its
choice to the spectral bands actually used by that model. Record the physical
band identity; dropping an unused native band must not count as an applied
augmentation. Remaining minimum strengths and hole-size/count sampling are
being discussed; no additional ranges were approved by this decision.


## Final closeout - 2026-11-02

The user approved 033B's combined outputs and requested the final readability
review and local commit for both tasks. The isolated viewer source is now
formatted as ordinary readable HTML/CSS/JavaScript; operation labels are clearer,
and stale pending-policy text is removed. Shared image export uses one explicit
clean/overlay loop, with exact exported-pixel tests unchanged. Current external
viewer HTML was refreshed from the same saved data without regenerating PNGs.

Core review preserved the approved values, exact normalization, native bands,
labels and masks. The shared adapter now advances its existing random state by
default; every diagnostic preview still passes an explicit replay seed. The
final native recipe and parity check belong to 033B. All 157 relevant package,
loader, preview and installed-distribution checks pass, as do Ruff and diff
checks. Detailed final verification is recorded in 033B. 033A is closed.
Exact next action: separately select 033C; no 033C implementation is included.
