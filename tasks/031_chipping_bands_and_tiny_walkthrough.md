# Task 031: Simplify chipping, select bands, and start the tiny walkthrough

Status: Complete — implementation and follow-up review, 2026-10-27.

Depends on: completed Tasks 030A/030B and the verified cleaned release. Both
publication tasks are complete; this implementation prerequisite is satisfied.

Execution: Local implementation, focused CPU checks, and a bounded real-data
smoke. Full chip production/publication and experimental splits remain Task 032.

## Abstract

Replace the legacy chipper with a small installed workflow that preserves source
identity, explicitly selects spectral inputs, and records every window and any
nodata exclusion. Start a short researcher walkthrough using small georeferenced
crops from several regions/dates. The same example will grow through later
split, training, inference and evaluation tasks.

Storage and slow GPU-host transfers matter. Do not require keeping or uploading
nodata-heavy chip payloads merely to preserve an audit trail: excluded windows
can retain metadata without payloads. Never remove original/cleaned TIFFs.
The configurable defaults are size 512, stride 256 and maximum nodata 50%.
Keep partial edge chips at their true size and pad during loading. Training
windows never shift inward; inference may shift final windows inward to cover
source edges.

## Reading route and inputs

Follow the entry path, then read [architecture.md](../docs/architecture.md),
[product.md](../docs/product.md), [data_artifacts.md](../docs/data_artifacts.md),
[documentation.md](../docs/documentation.md), and the implemented preparation
sections of [quickstart.md](../docs/quickstart.md). Read
[Task 030B's completion outcome](030b_build_and_publish_cleaned.md#outcome-2026-10-27)
and [Box recovery instructions](../docs/box_backup.md#cleaned-cabc-v1) before
selecting real inputs.

Historical evidence is in [Task 003](003_extend_chipper_and_write_manifest.md),
[Task 004](004_chip_all_regions_locally.md),
[Task 006](006_choose_nodata_threshold.md),
[Task 007](007_apply_nodata_filter.md), and
[Task 009A](009a_repair_metadata_nodata_and_repackage.md). Read only their relevant
geometry, threshold, correction and outcome sections. Inspect legacy chipper,
validator, their consumers, and focused tests before designing replacements.

Real inputs come from the authenticated Task 030B cleaned `ca_bc/v1` release,
normally `/Volumes/x10pro/kelpseg/data/3_cleaned/ca_bc/v1/`. Keep all real imagery,
generated manifests, crops and reports outside Git. Ordinary supported image
directories must remain usable without an organizer catalog; optional explicit
metadata adds scientific identities without fabricating missing dates/regions.

The cleaned root manifest SHA-256 is
`43815a8a7e412d0f0ed021c813c6c3b4f3a9a532a4fcbb3f9624a91bbdd5ba61`.
Task 030B verified all 747 Box files (18,662,320,805 bytes) and bounded restoration.
These are historical publication results. The implementation request forbids
new hashing, authentication-catalog or receipt work. Use the existing source
metadata to select bounded crops; check their arrays/grids without a release scan.

## User decisions required

### Agreed on 2026-10-27

- Keep Task 031 to implementation/tests and a short walkthrough/smoke; full
  production chipping and splits belong to Task 032.
- Use **512 x 512** as the configurable default native-resolution model/chip
  input size. The user's size question concerns model training and spatial
  context, separately from dataset storage. Keep a fixed regular training grid:
  the user explicitly rejects shifting final training windows inward as a
  sampling design. Use **configurable stride 256** (50% overlap). Keep true-size
  partial edge chips, then pad during loading with image fill 0 and target fill
  -100. Padding placement and inversion must be explicit.
- Use a **configurable maximum of 50% image nodata**, selected after reviewing
  the recorded 512-pixel study. Keep windows exactly at 50%; omit payloads only
  above the limit, retaining their identities/counts/exclusion reasons. Count
  actual source pixels, excluding artificial padding. Keep canonical background
  chips; this is not a foreground-presence filter.
- For this current eight-band CA/BC dataset, the user authorizes assuming the
  order `coastal_blue, blue, green_i, green, yellow, red, rededge, nir`. Record
  this as a user-declared collection assumption, not independently verified
  metadata for every source. Reject contradictory explicit source evidence.
  Other datasets require their own explicit band declarations. A future native
  four-band input may declare RGB+NIR; it is not the current production input.
- Current-family labels map `[0, 1, 2, 3, 4]` to `[0, 1, 0, -100, 0]`:
  kelp foreground, water/land/waves background, class 3 ignored. This is a
  recipe declaration, not a universal mapping for unrelated datasets.
- The walkthrough should favor more regions/dates using small georeferenced
  crops, and double as our real-data smoke test.
- Inference will use sliding windows independently of training-chip retention.
  The user explicitly allows shifting final inference windows inward to cover
  edges. This differs from the fixed training sampling grid; the prediction
  implementation remains Task 034. Actual offsets, deduplicated windows and
  explicit padding/inversion are required by the architecture contract.
  A nodata cutoff on stored training chips must not silently become the source
  prediction footprint; later scoring declares and reports its own coverage.

### Authorized 512-pixel analysis

The user authorized a read-only threshold analysis during planning and rejected
inward-shifted training windows. The study used fixed 512-pixel windows at stride
256, provisional at the time and now approved, clipping source extents at regular
grid positions and stopping when covered. Artificial padding was excluded from
nodata percentages; loading-time padding was approved afterward.

Task 030B was still building its incomplete output, which this analysis does not
read. Instead, project current cleaner semantics from all 369 immutable organized
pairs using the existing nodata/alignment/label-repair functions. Authenticate the
organized root and controls against the 030A local-ready handoff; inherit its
payload hashes, check input inventory/stats for stability, and do not claim a new
whole-payload hash verification or verification of the unfinished cleaned release.

Read each image once in nonoverlapping blocks. Keep compact per-source masks,
use prefix sums for candidate-window counts and union retained windows for
unique per-TIFF coverage. The target is 2,905,415,276 source pixels, about
49.39 GB of decoded eight-band image plus target-label values, with a 64 MiB
GDAL cache and several hundred MiB of per-source working arrays. Native label
reads are bounded crops, not repeated whole BC mosaic scans. Reports only are
budgeted below 64 MiB; no chip/raster payloads or transfer operations occur.

External producer and frozen plan are under
`/Volumes/x10pro/kelpseg/analyses/task031_nodata_512_s256_grid_v1/`.
Run once from the existing installed environment without synchronization;
stop on failure and use a fresh prefix for a later attempt. Focused synthetic
checks cover prefix sums, union coverage, fixed edges/undersized inputs,
nodata/ignore repair and exact threshold comparisons. Independent read-only
review found no blocking counting/mask/coverage issue.

### 512-pixel analysis outcome (2026-10-27)

Completed the authorized projection over all 369 source pairs and 12 regions
in 217 seconds, evaluating 40,571 fixed-grid 512/256 windows. Source pixels are
counted once per TIFF for coverage; geographic duplication across separate TIFFs
is not deduplicated. Artificial padding is absent. All source inventory/stats
remained unchanged; the organized root/controls authenticated successfully.

| Max nodata | Retained windows | Unique scoreable-pixel coverage | Unique foreground coverage | Sources with eligible windows |
|---|---:|---:|---:|---:|
| 50% | 26,573 | 99.971330% | 99.994947% | 369 |
| 60% | 27,743 | 99.987855% | 99.995403% | 369 |
| 70% | 28,751 | 99.995907% | 99.996381% | 369 |

The projected scope has 1,766,228,620 scoreable pixels and 38,376,350 foreground
pixels. Raising 50% to 70% adds 2,178 windows (8.20%) and 434,089 uniquely
covered scoreable pixels, of which 550 are foreground. Additional windows may
offer different training context even when they repeat already covered pixels;
this is not an accuracy comparison. No threshold eliminates a TIFF or region,
and no retained window has zero supervised pixels under the selected recipes.

At 50%, uncovered foreground is 1,939 pixels across four sources. At 70%, it is
1,389 pixels in BC source `012_20210813_193301_80_241_clip0` (91,236 foreground
pixels total). All other sources' foreground is covered at 70%. BC's regional
foreground coverage is 99.945930% at 70%; all other regions reach 100%.

Sliding-window inference can independently cover intended imagery. These
coverage statistics concern retained training windows, not a restriction on the
future predictor's footprint. The analysis supports keeping thresholds
configurable; it does not establish a model-accuracy advantage for any cutoff.
The user selected 50% after reviewing these results, then approved stride 256
and partial edge chips. The reported coverage applies specifically to that grid.

Durable external outputs under
`/Volumes/x10pro/kelpseg/analyses/task031_nodata_512_s256_grid_v1/`:
`analyze.py`, `plan.json`, `windows.csv`, `sources.csv`, `summary.json`,
`completion.json` and `scan.log` (about 5.48 MB total, no chip/raster payloads).
Authenticated parent root SHA-256:
`435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8`.
Analysis producer SHA-256:
`e0cbd1109dc91f99783152fe137965d093d1511bdcc37a217b8d10b758bfd44b`.

Validation passed: focused scientific/geometry self-checks; producer Ruff
format/check; independent methodology/code review; report SHA-256s; 40,571
window rows and 1,107 source/threshold rows; exact threshold recounts from
window records; per-source monotonicity; and per-region/global reconciliation.
No package code, environment, source data, Box payload or production preparation
output changed. This is a projection using shared cleaner functions. After
030B closed, authenticated final controls matched all 369 source identities,
regions, dates, valid-imagery counts, scoreable counts and foreground counts.
That control-only reconciliation did not reread imagery or verify the projected
spatial masks pixel by pixel. Its receipt is
`/Volumes/x10pro/kelpseg/analyses/task031_nodata_512_s256_grid_v1_reconciliation.json`.
Compressed chip-byte costs were not measured.

Study decision: retain the 50% maximum as the configurable starting recipe.
At the analyzed 512/256 fixed grid, it retains 99.994947% of unique foreground
pixels while using 2,178 fewer windows than 70%. This is a coverage/selection
decision, not evidence of equal model accuracy. Preserve the table, exact scope,
producer/parent hashes and external report paths above as the durable study
record. Later recipe changes must not silently inherit its numerical estimates.

### Remaining decisions and safe implementation choices

No blocking user decision remains. The user approved the stride, partial-edge
loading behavior and walkthrough plan on 2026-10-27. Do not reopen those choices
or add another routine approval gate.

The agent may select walkthrough identities after final 030B QA without another
scientific decision. Use nine georeferenced crops across
three regions (including CA and BC) and three acquisition dates per region,
normally 768 pixels square, with at least one 769-pixel axis to exercise partial
edge chips and loading-time padding. Keep the one-time downloaded payload below 128 MiB
and generated local example outputs below 1 GiB. This supports later tiny
temporal/LORO exercises without selecting sources by held-out model performance.
If actual availability/size cannot meet that scope, record a smaller concrete
selection/budget resolution before transfer rather than silently exceeding caps.

Safe implementation choices include thin handlers, strict plain TOML, explicit
fresh outputs, ordinary sequential functions, default progress logging, immutable
inputs, portable relative paths, and focused synthetic tests. No further choice
is needed for those conventions.

## Plan/spec before coding

Before coding, write a compact implementation checklist under this contract's
chosen CLI/files: recipe/identity schemas, window rules, loading/padding, band/
label semantics, eligibility, provenance, removal map and tests. The scientific
settings are resolved; routine code organization does not require new approval.
No repeat threshold study is required. Any newly necessary analysis must have
an explicit bounded scope and I/O budget.

Historical evidence to carry into the discussion:

- Task 003 selected 1024/512; no measured 256/512/768 accuracy comparison was
  found in the reviewed records. Task 014B benchmarked batches at fixed geometry.
- Task 007's 50% filter removed 1,366/6,003 chips (22.76%) but only
  3,245,804,422/48,157,853,832 compressed bytes (6.74%). It removed 4.54% of
  summed foreground chip pixels and eliminated two source TIFFs, no region.
- Those foreground counts repeat pixels across overlapping windows. They do
  not establish unique kelp area lost. Task 009A later corrected nodata and
  removed another 35 chips, leaving 4,602; the new cleaned release also changes
  outside-label coverage. Historical candidates are not current predictions.
- The recorded `/Volumes/x10pro/kelpseg/nodata_threshold_analysis_v1` directory
  was absent during this planning review. Task 006 records a 30% comparison,
  but its saved numerical table has not been located. The metadata-only review
  below independently recalculates historical candidates; it is not that missing
  artifact or a current 512-pixel analysis.
- Compare unique valid/labeled/foreground source coverage, per-region/source
  losses, window counts, and actual bounded compressed-byte estimates. A lower
  nodata cutoff need not save bytes in proportion to chip counts.
- Smaller chips at the same proportional overlap create more files and roughly
  similar stored pixel volume over large interiors. Discuss overlap explicitly
  as another storage setting; do not imply halving size quarters total transfer.

Keep analysis bounded within this task. Full production collection statistics
and publication remain Task 032; if a separate substantial study is needed,
split the contract before executing it.

### Historical threshold review (2026-10-27)

This historical comparison considered a maximum of 70% nodata before the current
512-pixel study and 50% decision above. An earlier incremental 30/40/50%
calculation answered the reverse question. The corrected historical active
collection has already omitted windows above 50%, so it cannot by itself measure
relaxing that limit.

Read-only recalculation from the original 6,003-row
`/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1/filter_history/nodata_50/pre_filter_manifest.csv`
gives the following **pre-correction historical** comparison:

| Maximum nodata | Minimum valid imagery | Retained chips | Retained sources | Foreground chip pixels removed |
|---|---:|---:|---:|---:|
| 50% | 50% | 4,637 | 367 | 4.538% |
| 60% | 40% | 4,919 | 368 | 0.923% |
| 70% | 30% | 5,157 | 368 | 0.209% |

Seventy percent retains 520 more historical windows than 50% (11.21% more),
including foreground-bearing windows; 60% already restores one source. These
counts reproduce Task 006's 50/60 results. No imagery/NPZ payloads were read,
no hashes computed, and no data changed. Compressed bytes for restoring excluded
windows have not been established; do not estimate them from chip counts alone.

All foreground figures count overlapping chip pixels, **not unique kelp area**.
These original statistics include the known five-TIFF nodata defect, use 1024/512
geometry and older cleaning semantics, and cannot predict current 512 coverage
or bytes. The later 512-pixel study supersedes these figures for the current
decision; the approved starting maximum is 50%.

Future comparisons must keep stride/edge rules fixed and report unique valid
labeled and foreground coverage, per-region/source losses, window counts and
bounded compressed-byte estimates when transfer costs are studied. Image nodata percentage
does not bound valid-imagery ignored-label percentage; report those separately.
Use source pixels as the denominator, excluding artificial padding. Preserve all
candidate-window/exclusion records while omitting excluded payloads. Do not
select the cutoff using held-out model performance.

## Implemented interface and scope

The implementation request superseded the heavier provenance/publication
requirements in the planning contract. Keep historical study evidence above;
no new hashing, checksums, authentication catalogs or transfer receipts.

- `src/kelpseg/cli/chip.py`: thin `kelpseg chip` command with `--images`, optional
  `--labels`, `--metadata`, `--output`, `--recipe`, and `--dry-run`. No `--parent`.
- `prepare/chip_inputs.py`: flat recipe, fixed-grid windows, one exact-key
  identity CSV schema and header-only plan. Reuse existing TIFF discovery,
  image-header/grid checks, path validation and nodata functions.
- `prepare/chip.py`: sequential native-window reads, explicit category mapping,
  inclusive nodata threshold, compressed payloads and atomic directory publication.
- `bands.py` and `chips.py`: ordered band selection and plain NumPy loading,
  native-band validity, optional labels, true dimensions and bottom/right padding.
- `configs/chip/planet8.toml`: configurable 512/256/50 defaults and the declared
  current-family band order and `[0,1,2,3,4] -> [0,1,0,-100,0]` mapping.

Keep one native uint16 HWC image per NPZ and optional int8 HW target. Do not pad,
normalize or resize stored chips. Label masks/nodata metadata do not erase stored
background; all-band image zero forces target -100 after mapping. Keep class-3
ignore over valid imagery. Background alone never excludes a canonical chip.

Use starts 0, stride, ... until the first window reaches/passes each axis end;
clip to true size without inward shifts. An axis 513 has starts 0/256 and widths
512/257. Count nodata over true source pixels, retaining threshold equality.

Output bookkeeping is limited to `chips/`, all-candidate `windows.csv`, portable
`sources.json`, resolved `recipe.json`, and `summary.json` with complete status.
The CSV joins source identity/grid metadata and records crop-local/original
windows, dimensions, nodata/label counts, disposition and optional payload path.
No paths exist for omitted payloads. Window counts overlap; unique coverage is
computed from retained windows only when needed. No manifest inventory/hash layer.

The optional identity CSV supplies original source, dataset/release, region/date,
crop offsets and dimensions. Require exact joins, reject duplicates/conflicts,
and retain unknown fields explicitly. All crops of one original remain one
source group for later splitting. The [quickstart](../docs/quickstart.md#chip-cleaned-imagery)
owns the exact columns and operating recipes.

Write once into fresh sibling `.<output>.incomplete`; stop on failure and rename
the complete directory to final. Existing final/staging paths fail; never resume,
retry or reuse partial outputs. No split/training/prediction implementation.

## Tiny walkthrough and validation

Use nine georeferenced crops across three regions (CA and BC), three dates per
region, normally 768 square and at least one 769-pixel axis. Preserve original
identity/windows and grids; do not repeat cleaning or the threshold study.
Keep one-time input payload below 128 MiB and each smoke output below 1 GiB.
Inputs live at `<data_root>/data/examples/tiny_ca_bc/v1/`; outputs use separate
fresh `<data_root>/examples/runs/<name>/`. Ordinary Box copy/fetch is sufficient;
check practical paths/sizes and bounded arrays without checksum/receipt work.
No study-evidence publication is needed. Repeat the walkthrough offline.

Focused tests prove fixed grids/full candidate coverage (including 511/512/513),
true-size edges/padding inversion, georeferencing/original offsets, 8/4/3 ordering,
native-band nodata, label mapping/background/ignore, inclusive threshold and
omitted rows without payloads, optional labels, strict identities/recipes/grids,
header-only dry-run, corruption/errors and fresh-output failure behavior. Isolated
wheel/sdist checks exercise new CLI/runtime without legacy imports. Preserve
useful shared scientific tests as obsolete code is removed.

Run focused pytest, Ruff format/check, broad-change pre-commit, Markdown link/
anchor checks and `git diff --check`. Record input/output bytes, bounded coverage,
partial-edge example, removed code and remaining limits. Update researcher docs,
close both queues and stop before Task 032.

## Non-goals

Full dataset chip production or publication; generated experimental splits;
training, normalization, GPU benchmarks, model accuracy selection, prediction,
scoring implementations, new ingestion, preparation recovery, or three spectral
payload copies. The approved numeric defaults are size 512, stride 256 and
maximum nodata 50%; changing them remains explicit and configurable.

## Outcome template and exact next action

At implementation closure record changed files, chosen settings and evidence,
code/recipe identities, exact example/source/crop lineage and byte budgets,
external artifacts, test/check results, scientific/coverage limits, usability and
removal checks, and unresolved issues. Update both queues and stop before Task 032.

## Historical planning closeout (2026-10-27)

The contract is finalized with no blocking user choices. All approved decisions,
the study, authenticated final-cleaned control reconciliation, scope, proposed
files/CLI, exact smoke checks, acceptance and non-goals are recorded here.
Queues and owned architecture/artifact contracts agree. Implementation remains
Pending; this planning turn does not build chips or run later numbered tasks.
Independent final review tightened the real example's partial-edge case and the
image-nodata target invariant; no blocking contract issue or user choice remains.
Planning validation: 90 local links/anchors resolve across the five owned
documents, fenced blocks are balanced, and `git diff --check` passes. The final
cleaned-control reconciliation above passed without another payload scan.

The next action recorded at planning time was: when implementation is requested, reread the
entry documents and this contract, mark it In progress, authenticate the completed
030B input controls, write the compact implementation checklist and implement
this bounded contract. At closure hand Task 032 the chip/identity schema, settings,
tiny example and exact next production/split action, then stop.

## Implementation checklist (2026-10-27)

The implementation request overrides heavier planning requirements above. No new
hashing, checksums, authentication catalogs, transfer receipts, repeated cleaning,
threshold study or full-data scan. Historical evidence above remains history.

- Reuse `discover_inputs`, `same_grid`, cleaned header checks, and `nodata_mask`.
  Keep one flat recipe; add optional exact-key identity CSV with source ID,
  region/date, crop offsets and original dimensions. No parent verifier or
  catalog machinery in the new command.
- Thin `chip` CLI, small recipe/planning module and sequential writer. Use the
  fixed 512/256 grid by default, clipping edges and omitting payloads only above
  50% nodata. Native uint16 HWC NPZ, optional explicitly mapped int8 target.
- Keep portable source metadata, all-window CSV, resolved recipe and one compact
  completion summary; publish the fresh incomplete directory by rename.
- Plain NumPy band selection/loading; detect validity before selecting bands,
  pad bottom/right only, return true dimensions and explicit offsets.
- Inspect legacy consumers before deleting superseded chip generation/validation
  and repair code. Keep later workflow dependencies until their replacements.
- Focused scientific, metadata, failure and installed-package tests, required
  lint/pre-commit, bounded nine-crop walkthrough including a 769-pixel edge,
  ordinary Box copy/fresh fetch and offline rerun without checksum work.
- Update researcher guide/owned contracts and queue; hand off to Task 032 and stop.

## Outcome (2026-10-27)

Implemented Task 031 under the user's simplified scope. The installed `chip`
command and reusable functions use ordinary sequential Rasterio/NumPy calls;
512 size, 256 stride and 50% maximum nodata are explicit configurable defaults.
Native-band NPZs keep true edge sizes. Loading selects 8/RGB+NIR/RGB and pads
bottom/right with image zero and target -100. Canonical backgrounds remain;
current stored labels map explicitly, and image nodata forces ignore. All-window
rows preserve omitted reasons without omitted payloads. The fresh directory is
published only after completion; no resume/reuse machinery was introduced.

### Changed files and simplicity/removal check

Added `src/kelpseg/{bands,chips}.py`, `src/kelpseg/cli/chip.py`,
`src/kelpseg/prepare/{chip_inputs,chip}.py`, `configs/chip/planet8.toml`, and
focused `tests/test_chip.py`, `tests/test_chip_loading.py`,
`tests/test_label_repair.py`. Registered the command in `cli/__init__.py`;
extended `tests/test_distribution.py` and `tests/test_package_cli.py`, and
ported shared scientific assertions in `tests/test_prepare_alignment.py`.
Recipe/planning reuses input discovery, cleaned image-header checks, grid/path
checks and shared nodata detection. Routine size/stride/cutoff/band/category
changes use ordinary TOML values; source metadata uses one CSV schema.

Removed superseded `src/prepare/make_chip_dataset.py`,
`src/prepare/remove_tiles_with_nodata_areas.py`,
`scripts/validate_chip_dataset.py`, `scripts/repair_planet8b_nodata_metadata.py`,
`run.sh`, and their obsolete chip/filter/repair test files. Useful label repair,
coverage, mapping, geometry and threshold assertions now exercise shared/new
functions. Kept the non-destructive legacy background selector, channel stats,
nodata compatibility wrapper and later workflow scripts until their replacements.
Removed TorchGeo from `pyproject.toml`; `uv lock --offline` pruned it and unused
transitive dependencies without synchronizing the active environment. No runtime
imports of the removed implementation remain.

Updated `README.md`, `docs/index.md`, `docs/quickstart.md`,
`docs/architecture.md`, `docs/data_artifacts.md`, `docs/todo.md`,
`tasks/README.md`, and this task. Preserved preexisting Task 031 planning edits
in architecture/artifact/queue documents and historical study evidence. The
researcher guide now owns working chip/metadata/loader recipes, a small fetch
and offline walkthrough, and the partial-edge padding example.

Output bookkeeping is only four small control files plus payloads. There is no
parent verifier, hash inventory, authentication catalog, transfer receipt,
framework, worker pool, split or model implementation in the new workflow.
No repeated cleaning, threshold study, full-collection scan, study upload or
real-data hashing/checksum work ran. Existing recorded evidence remains history.

### Durable external example and smoke

- Inputs: `/Volumes/x10pro/kelpseg/data/examples/tiny_ca_bc/v1/`.
- Ordinary Box copy: `kelp-box:kelpseg/data/examples/tiny_ca_bc/v1/`.
- Fresh fetched inputs: `/Volumes/x10pro/kelpseg/examples/fetched/task031_tiny_v1/`.
- First chips: `/Volumes/x10pro/kelpseg/examples/runs/task031_tiny_v1/`.
- Offline repeat: `/Volumes/x10pro/kelpseg/examples/runs/task031_tiny_offline_v1/`.
- Bounded crop producer: `/Volumes/x10pro/kelpseg/examples/make_tiny_ca_bc_v1.py`.

The input has 18 TIFFs plus `metadata.csv` and `selection.json`: 20 files,
54,463,809 bytes total, including 54,457,352 TIFF bytes, below 128 MiB.
The CSV retains canonical cleaned original TIFF IDs, dataset `ca_bc`, release
`v1`, region/date, crop offsets and original dimensions. Each crop's TIFF grid
and raw categories/values exactly matched its bounded cleaned source window.
Inputs were selected using existing metadata (including BC valid fractions),
never model results. Three dates per region and four background-only crops
support extending this same example in later tasks.

| Original cleaned source ID | Crop row | Crop column | Height x width |
|---|---:|---:|---:|
| `002_20200515_173152_2271` | 1024 | 768 | 768 x 769 |
| `002_20200614_173343_2277` | 1024 | 768 | 768 x 768 |
| `002_20200924_182639_241c` | 1024 | 768 | 768 x 768 |
| `003_20210407_183323_2401` | 1536 | 1024 | 768 x 768 |
| `003_20210419_183514_2307` | 1536 | 1024 | 768 x 768 |
| `003_20210429_175145_2231` | 1536 | 1024 | 768 x 768 |
| `012_20210811_184459_09_245c_clip4` | 1280 | 1280 | 768 x 768 |
| `012_20210812_184548_90_2448_clip5` | 1280 | 1280 | 768 x 768 |
| `012_20210813_193301_80_241_clip4` | 256 | 1280 | 768 x 768 |

Both chip runs completed in about six seconds, with 38 candidate/retained
windows, zero nodata omissions and 21 windows without kelp. Each output has
38 NPZs plus four controls: 101,980,989 bytes, including 101,969,301 payload
bytes, below 1 GiB. No failed chip write occurred. An initial header-only
preview correctly refused a missing output parent; creating that parent and
rerunning the preview succeeded without incomplete output.

Reconstructing the bounded crops from retained windows covered all 5,309,184
pixels once for coverage counting: 150,741 kelp, 57,329 image-nodata/ignored,
zero valid-imagery ignored and zero uncovered pixels. Counts concern source
pixels within these crops, not the full collection or model accuracy. The real
example has no windows above 50%; focused fixtures prove both sides and equality.

Every chip exactly matched its source crop window under all three band
selections. The 769-wide crop produced true 512-by-257 edge chips; loading
returned `(0, 0, 0, 255)` padding and 512-square arrays with 8/4/3 channels.
Removing padding exactly restored native values/labels and original grid
placement. Synthetic cases separately cover bottom padding and ignore over
valid imagery.

Before upload the Box destination was absent. Ordinary `rclone copy` with
`--immutable --size-only --ignore-checksum --transfers 1 --checkers 2` uploaded
the inputs; remote relative paths/sizes matched all 20 local files. Fresh fetch
used the same settings into an absent destination. All 18 fetched TIFF arrays,
profiles and two metadata files matched the small local input. The offline
chip rerun used only fetched inputs and the installed package, yielding identical
38 image/target arrays and all four control files. These checks do not claim
checksum authentication or verification of a whole cleaned release.

### Validation and handoff

Passed 138 focused tests across `test_chip`, `test_chip_loading`,
`test_label_repair`, `test_prepare_alignment`, `test_nodata`,
`test_alignment_boundaries`, `test_package_cli`, and `test_prepare_progress`.
The additional isolated wheel/sdist distribution test passed (139 tests total),
including new modules, lazy CLI help, external-directory dry-run/write/load and
absence of legacy/ML imports in installed runtime behavior. No unrelated test
failure was observed in these checks; the full legacy suite was not rerun.
Ruff format/check and all-file pre-commit passed, including an explicit pass
on new untracked files. Documentation links/anchors resolve across the eight
owned documents; fenced blocks are balanced and `git diff --check` passes.

Concurrent separate Task 032A/032B planning and no-hashing policy updates were
preserved; this task did not edit their contracts or start their implementation.

No unresolved implementation blocker remains. Physical band order remains the
explicit user-declared CA/BC assumption; labels remain supplied annotations.
The example is not a representative full-collection coverage estimate. No
production chips, experimental splits, training, inference or evaluation were
implemented or run.

Exact next action: reconcile the separately planned Task 032A/032B contracts
with this chip recipe, `source_key` window join, original `source_id`/dataset/
release grouping, metadata CSV and reusable tiny inputs. Finish the open temporal
policy before implementing assignments in 032A; full external production and
publication follow in 032B. Preserve source/date isolation, matching spectral
membership and known alias checks. Task 031 stops before either implementation.

## Follow-up review checklist (2026-10-27)

Review only Task 031: fix conflicting crop metadata,
extract the planner/writer's long responsibilities into small ordinary functions,
and remove duplicate band/window/header work. Preserve the flat recipe, minimal
metadata and one-pass behavior. Add tiny regressions, run focused/installed
checks and lint, update the outcome, then stop before Task 032.

## Follow-up review outcome (2026-10-27)

Reviewed correctness, duplicate work, long functions and unnecessary complexity.
Fixed conflicting shared-original crop grids and invalid large cutoffs.
Defensive checks for files changing after planning were added during review,
then removed at the user's direction as unnecessary. Inputs are assumed to stay
unchanged while preparation runs.

- `prepare/chip_inputs.py` checks shared-original CRS and the affine grid with
  crop offsets removed. Compatible crops with different offsets are accepted;
  incompatible placement is rejected. Ordinary format/alignment checks run once
  during planning. There is no writer-time source-change or recipe recheck.
- `prepare/check.py` now checks every explicitly known band description even
  when other descriptions are absent/generic. Chipping reuses that check rather
  than implementing a second band-header loop. `max_nodata_pct` uses its direct
  numeric range check; the redundant float-converting finiteness check is gone,
  so invalid large integers fail with the ordinary actionable recipe error.
- Split the long planner into source-record, inspection and original-identity
  functions. Split source/window writing from publication. These are small
  ordinary functions and loops, with the same recipe/output schema and one-pass
  behavior. Removed the extra header helper after dropping writer-time rechecks.
- `chips.py` uses the band indices already resolved, removing a second selection
  validation. Full-size chips avoid zero-width `np.pad` copies. `chip_windows`
  constructs each axis's start list once rather than once per grid row.

Changed only the Task 031 runtime files above, `tests/test_chip.py`,
`tests/test_check.py`, researcher/architecture instructions, this outcome and the
Task 031 queue wording. Added compact regressions for compatible/incompatible
crop grids, partial band descriptions and cutoff errors. Removed the four
source-edit timing tests with the unwanted guards.
Preserved existing coverage for threshold equality, true-size edges, padding,
backgrounds, native-band nodata, optional labels and atomic publication failures.
The guards add no hash/stat catalog, receipts, recovery feature or data scans.
No real-data or Box work was repeated; external artifacts from the implementation
remain unchanged. Concurrent Task 032 planning/docs were preserved.

Original review validation passed: 205 focused synthetic tests covering chipping/loading,
shared checking/cleanup, alignment/nodata, CLI and progress; the separate
wheel/sdist installed-package test also passed (206 total). Ruff format/check,
all-file pre-commit and explicit checks on new files passed. Documentation
links/fences and `git diff --check` passed. Independent final runtime review
found no remaining actionable regression. No unrelated failure was observed;
the full legacy suite was not rerun.

After removing the source-edit guards and four timing tests, all 93 focused
chip/loading/header tests, Ruff format/check and `git diff --check` passed.

Further simplification at the user's request removed repeated label-vocabulary
and image-nodata/target audits from every chip load, NPZ archive-type/exact-key
policing and custom corruption wrappers, the final concurrent-output appearance
check, and canonical numeric-key spelling enforcement. NumPy reads the arrays
directly; the chipper already guarantees mapped targets. Normal shape/band/
settings checks, scientific alignment/identity checks and initial overwrite
refusal remain. Removed four tests of the deleted archive/label policing.
No input scan, transfer or Task 032 implementation was added. All 109 focused
chip/loading/header/CLI tests, Ruff format/check and `git diff --check` pass.

Exact next action remains the separate Task 032A/032B contract reconciliation
and temporal-policy discussion. This review ends before their implementation.
