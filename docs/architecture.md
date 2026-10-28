# Architecture contract

## Current implementation and replacement target

The installed `src/kelpseg/` package provides the Typer command and read-only
machine-path checks, generic byte-preserving organization, quick/full directory
checks, shared cleanup, native-band chipping with optional labels, and source
assignment/window-selection functions. The checkout retains legacy Planet
`src.*` modules, root `trainer.py`, `scripts/`, relevant configs, and focused tests until their
replacements land. Unrelated application/model/export families are removed.
The legacy recipe is `configs/kelp-ps8b/generalization/segformer_b3_v3.yaml`.

The package uses uv and `uv_build`. The completed replacement will have no
`scripts/` directory, plugin framework, generic model zoo, or manual per-fold
config copies.
Task contracts introduce commands as they are implemented; this design is not
an assertion that they already work.

```text
variant 1: raw, immutable source deliveries
  -> variant 2: organized, unsplit intermediate; unchanged TIFFs and name/region crosswalks
  -> variant 3: cleaned, unsplit intermediate; documented repairs and parent provenance
  -> one canonical chip collection and chip statistics
  -> external temporal/LORO assignments and training eligibility
  -> explicit band selection and training recipe
  -> checkpoint
  -> image-only tiled prediction and georeferenced reconstruction
  -> optional label scoring, comparisons, and visual review
```

Prefer small functions with explicit inputs/outputs and a limited supported
scope. Preparation runs once from beginning to end; a failure stops the sequence
and an interruption requires a fresh attempt. There is no preparation restart,
resume or partial-output reuse. Publish complete manifests atomically and refuse
silent overwrites. The current one-pass cleaner is the upper bound on file
complexity; prefer smaller functions and files with one clear purpose.

## Researcher interface

The CLI uses Typer with `uv run kelpseg <command>` recipes. Keep a small root
app and separate thin command handlers, backed by ordinary workflow
functions callable from notebooks/tests without CLI context. Import heavy
workflow code only when its command runs. Preparation modules live together in
`src/kelpseg/prepare/`: `organize_inputs.py` loads/validates explicit declarations,
`organize.py` copies/verifies bytes, `check.py` validates directory scopes,
`clean_inputs.py` defines cleanup settings/plans, and `clean.py` writes/verifies
separate derived outputs. `nodata.py` and `alignment.py` hold shared scientific
functions. The one-time historical catalog bootstrap is retired; existing
explicit catalog tables are normal organizer inputs. Keep these as explicit
functions and ordinary loops;
the CLI uses standard Python logging for progress, without a custom logging
or orchestration layer. Later tasks add model workflow commands. The selected
training command style is `uv run kelpseg train --recipe <recipe-file>`;
it remains planned until the training task implements it. See
[quickstart.md](quickstart.md) for working setup and preparation recipes.

The preparation surface is `organize`, `check`, shared `clean`, `chip`, and `split`;
there is no BC-specific command or intermediate. Task 029B implements
direct-directory
checking/cleanup for imagery with optional paired labels, without requiring an
organizer catalog. Quick checks inspect structure/headers; full checks scan all
selected pixels and state any unavailable checks. Both are read-only. Cleanup
uses the same functions for CA, BC and other explicitly supported inputs.

Runtime dependencies cover implemented workflows: Typer, NumPy and Rasterio.
Checkout-only dependencies for retained code live in the default `legacy`
group alongside `dev`; plain frozen setup includes both. New workflows promote
their dependencies into runtime as implemented. Distribution checks install
only frozen runtime dependencies, independently of legacy checkout tests.
Reusable functions return typed values and raise ordinary exceptions; CLI
handlers own output and exit status. Organizer/path-file workflows use an
explicit `--paths` file, with no discovery; relative roots resolve against that
file. Direct-directory check/clean paths resolve from the working
directory, with recipe references relative to the recipe file.

Use short recipes with ordinary values for bands, learning rate, augmentations,
dataset, and checkpoint. Keep machine-specific paths in one place; changing
datasets or machines must not require source edits. Avoid Python class paths
and config inheritance chains in the researcher interface. Keep most settings
in recipes, with a few deliberate CLI options for recipe/path/output inputs.

Use one documented run-folder convention for resolved settings, checkpoints,
metrics, and figures. Before expensive work, show resolved input/output paths,
band order, and relevant dataset counts. Reject unknown settings and explain
how to fix invalid inputs; keep technical context in logs.

At task completion, check that routine changes use documented settings, the
implementation is traceable through straightforward functions, and obsolete
options/imports/dependencies are removed as replacements land.

## Identity and preparation

Preserve dataset/release, region ID, source TIFF ID, acquisition date, chip ID,
source window, shape, CRS/transform, band names/order, dtype, label mapping, and
nodata interpretation. Paths in portable manifests resolve from an explicit
dataset root. Do not derive identity from mutable directories or list order.

Raw imagery and labels are immutable. Inventory originals and explain existing
repairs before implementing a new cleaning release. Historical CA/BC cleanup
included grid alignment, source-aware image nodata, and label repairs; those
rules require provenance, fixtures, and real examples rather than blind reuse.

Keep organization/renaming separate from cleanup. The implemented organizer for variant 2
contains the current 369 pair identities (339 CA-family sources and 30 BC tiles),
unchanged source image/label bytes, and no experimental split. Publish a stable
region-code table and source/member/filename aliases with separate image/label
hashes in the existing release; retain original paths even when long product
names are unavailable. New work follows the simpler artifact policy without
adding hashing or receipt machinery.
Original grids need not match until the cleaning stage. The repaired historical
merge supplies membership/provenance evidence, not original label payloads.
See [data_artifacts.md](data_artifacts.md#planned-raw-intermediate-and-cleaned-releases)
for stage boundaries and mapping requirements. Organization and cleanup are
implemented, and the full CA/BC releases are complete. Source assignments are
implemented. Task 032B produced and published one native-band chip release
with portable baseline/LORO controls and the collection declaration.

Cleanup writes into a fresh sibling `.<output-name>.incomplete` directory and
renames it to the requested output only after all checks pass. Failed runs leave
that incomplete directory for inspection. The cleaner never resumes or reuses it;
move or remove it deliberately before a full rerun, or choose a new output path.
There are no cleanup receipts, active-file journals or producer-matching resumes.

Cleaned imagery stores nodata as all-band zero and declares
`nodata=0`; labels retain valid class-zero background and use stored/metadata
ignore value 3. Detect original nodata before normalizing values. For paired
data, align labels and exclude outside-label coverage by writing image zero
plus label 3. Image-only cleanup never blanks valid imagery because labels are
absent. This deliberately changes derived image bytes and supersedes historical
BC outside-coverage background filling; raw/organized payloads stay unchanged.
Detect retained all-zero value collisions instead of silently changing validity.
Detailed coverage/reason rasters are optional and off by default; compact
counts, transformation records, source/output references and asset dispositions
remain required. Rewritten image and label sidecars must not reactivate stale
metadata/masks/overviews. Existing scientific logic and correctness tests are
reused, with explicit regression changes for the new policy. Task 029B records
the migration map and bounded verification evidence.

Paired labels on the exact image grid are read directly without resampling.
When grids differ, alignment reads the native label crop without masking,
nearest-reprojects the array onto the image window, and identifies coverage
using an unused value 255. This preserves stored class zero regardless of source
nodata metadata. Supported inputs have matching CRS, north-up unrotated grids
and single-band `uint8` labels. Other grids/dtypes fail explicitly. Each source
crop is limited to 16,777,216 pixels; a smaller processing window is required
above that limit. Image-only cleanup has no label-alignment requirement.

Preparation accepts declared deliveries, region mappings and recipes uniformly
for every dataset. The current 369-pair scope is the first ordinary dataset,
not an implicit base that subsequent data must extend. All datasets get their
own organized/cleaned release IDs and parent links; all published releases remain
unchanged. Region, delivery and dataset IDs are separate concepts. A collection
is a versioned manifest selecting one dataset, a region subset, or any combination
of exact cleaned releases/source identities, without another physical TIFF merge.
Only an experiment recipe assigns a dataset/collection the role of baseline.
See [the add-region flow](data_artifacts.md#adding-regions-and-combined-datasets).

A channel count is insufficient to specify a product. Select bands by explicit
validated names/indices; RGB and RGB+NIR are not the first three/four PS8B bands.
Record normalization and initialization appropriate to each band recipe.

Keep canonical background chips. Express nodata and training eligibility in
metadata, retaining excluded identities/reasons. The installed chipper uses
a configurable 512-pixel chip size, stride 256 and maximum of 50% image nodata;
omit payloads only above that limit and keep their manifest records. Count
actual source-window pixels, excluding artificial padding. The supporting
[Task 031 study](../tasks/031_chipping_bands_and_tiny_walkthrough.md#512-pixel-analysis-outcome-2026-10-27)
uses the approved 512/256 fixed grid with retained partial edge chips.
Historical 1024/512 geometry and positive-only training selection do not become
new defaults. Use ignore index `-100` for unscored labels and padding.

`chip_inputs.py` validates a flat recipe, optional exact-key identity CSV and
cleaned headers; `chip.py` reads windows sequentially without cleaning or
realigning labels. Stored labels map explicitly to 0/1/-100, with image nodata
forcing -100. Label masks/nodata metadata cannot erase stored background.
One native uint16 HWC NPZ collection supplies all spectral variants. `bands.py`
and `chips.py` select channels in declared order and pad while loading.

Chipping writes only `chips/`, `windows.csv`, `sources.json`, `recipe.json` and
`summary.json` (complete status), publishing the fresh incomplete directory by
rename. Window rows join source metadata by `source_key`; original TIFF identity,
crop offsets and dimensions allow reconstruction and later grouping. Crops of
one original must agree on CRS and their offset-adjusted grid. Input headers
are checked once during planning. Nodata and
valid-imagery ignored targets have separate window counts. Those counts overlap;
unique source coverage must be reconstructed from retained windows when needed.
There is no parent authentication, hashing, receipt or recovery step in chipping.
The [quickstart](quickstart.md#chip-cleaned-imagery) owns the recipe and CSV schema.

## Splits and loading

Store generated split assignments with the external dataset release. Keep split
algorithms/configs in Git. Load one canonical collection through manifests;
remove the requirement for hard-linked train/validation/test directory trees.

New-region and combined-data experiments select an explicit collection version.
Generate versioned assignments for that scope and preserve declared fixed test
identities. Check known declared aliases across deliveries as well as source
IDs so known renamed copies cannot leak between train, validation and test.
This uses identity declarations, without new content-hash discovery. Resolve
conflicting annotation versions before selecting a collection's scoring labels.

Chips inherit source-level assignments, and acquisition-date groups remain
intact in the temporal baseline. Match source assignments across spectral
variants. Within each experiment/fold, a `(satellite_id, UTC date)` group
contributes to only one of train/validation/test, including all regional crops.
The same spacecraft on different dates can cross partitions. Record spacecraft
ID explicitly in collection/split metadata using the declared filename convention
or supplied metadata; never mistake a crop suffix for it. Reconcile regional
cutoffs jointly. Forward/reverse chronology can vary by region, with choices
fixed before model results are seen.

LORO test is the complete held-out region; train/validation exclude
that region. Current LORO folds cover regions 001–010, including Baja. Reproduce
the historical source policy for the other evaluation regions: their temporal
training and validation sources retain those roles and their temporal test
sources remain unused. Regions 011/012 are training-only and toggled together
in the with/without comparison; neither contributes validation or a test fold.
The with-BC `augmented` variant is the primary baseline; `base` without both
regions is the comparison. These names identify membership, not scientific rank.
For every LORO fold, also leave other-region companions sharing a held-out
test spacecraft/date unused. Apply the same group-isolation rule to optional
training inputs. These are manifest exclusions; canonical imagery stays intact.
Keep 001–010 assignments identical across that comparison. The approved
baseline uses reverse chronology for 001–008 and forward for 009/010; Task
032A owns exact locked cutoffs and the approved external source assignments.
Historical hard-link views
implemented this policy; new workflows use portable manifests without requiring
link trees. Training background exclusions never
silently constrain evaluation. Validate all joins and leakage boundaries.

Audit actual region/year/month and label support before choosing chronological
boundaries; the sparse collection does not support a uniform annual design.
LORO geographic generalization is the primary California deployment concern.
Keep later-date/future-year tests and the temporal-consistency reporting in
[experiments.md](experiments.md#evaluation-and-comparison) explicit.

`split_inputs.py` reads trusted cleaned controls or explicit CSV rows without
opening TIFFs; full cleaned chip keys come from canonical image references.
`configs/split/ca_bc_v1.toml` contains the approved cutoffs. `splits.py` generates
one assignment per namespaced original/experiment/variant and validates region/
date and spacecraft/day isolation. Only present evaluation regions create folds.
The unresolved BC token `241` stays literal and is allowed only on dates without
evaluation imagery; explicit known Planet metadata must agree with its original ID.

The installed `split` command publishes only `collection.csv`,
`chip_metadata.csv`, `assignments.csv`, `recipe.json` and `summary.json` through
a fresh incomplete sibling. The chip metadata export reuses Task 031's exact
identity columns and excludes satellite ID. `select_windows(chip_root,
assignments, experiment="baseline", variant="base")` joins list-shaped chip
source controls to original assignments and returns window rows with roles/
reasons and paths resolved from the explicit chip root. Omitted windows stay
unused without payloads. Selection reads no arrays and creates no fold copies.

Training uses all canonical retained windows, including overlap. For chip-based
validation/test, the selector visits existing windows in crop-key then numeric
row/column order and reserves a disjoint subset in original TIFF coordinates.
Crops of the same original share this exclusion, so their pixels cannot repeat.
Retained overlapping candidates become `unused` with reason `evaluation_overlap`;
all canonical rows and payloads remain available. Nodata-omitted nominal windows
keep their omission reason and are not replaced by overlapping alternatives.

Reuse existing chips rather than adding edge payloads. Log geometric input
footprint (union of crops), disjoint-grid area, retained selected area, uncovered
edge/gap area and nodata-omitted window area. These areas exclude artificial
padding and are not valid-label or model scores. Existing strides can leave
interior gaps as well as edge strips. Keep source assignments separate from
this window selection; both BC and all spectral variants share evaluation scope.
See [the researcher recipes](quickstart.md#assign-sources-and-select-chip-windows).

## Prediction and scoring

During training, validate ordinary non-overlapping chips and aggregate their
confusion counts; validation alone selects checkpoints. Test remains held out
until model selection is complete. This chip scope is reported with its coverage
and does not claim a stitched full-TIFF score. Training/evaluation commands are
implemented by later tasks.

Post-training tiled prediction and source-level scoring use the separate rules
below. Share one image/window predictor between unlabeled inference and labeled
evaluation. Labels are optional for scoring and must not be required to infer
padding offsets or spatial alignment. Record padding placement explicitly and
invert it before placing predictions on the source grid.

For overlap, average foreground probabilities at each covered source pixel,
threshold once, and compute TIFF confusion counts. Sum those counts for region
and dataset metrics. Ignore-index and uncovered pixels do not contribute.
Preserve georeferencing and report source coverage, including omitted windows
or nodata exclusions. Labeled and unlabeled paths must predict identically for
the same image and recipe.

The old chip grid omits some trailing edge strips and has true-size undersized
chips. Preserve its behavior for the legacy reference. New unlabeled mapping
should cover the full intended valid source footprint; specify and test edge
windows in its own task rather than claiming old artifacts cover every pixel.

Training chips use a fixed regular grid without shifting trailing windows
inward. Store partial edge chips at their true source size; pad bottom/right
during loading with image fill 0 and label ignore -100, recording true extents
and padding offsets. Sliding-window inference may shift its final windows inward
to cover source edges with full-size inputs where possible. Training and inference grids
need not match. Record actual inference offsets, avoid duplicate windows, and
retain explicit padding/inversion for sources smaller than the input window.
Apply the same image-only window rules during labeled scoring.

## Local verification

Exercise cleaning, chipping, band selection, splitting, loading, a tiny optimizer
update, validation, checkpoint save/load/resume, prediction, scoring, and transfer
locally. Keep real bounded examples alongside focused fixtures. Preserve useful
existing tests for source-aware nodata, split leakage, manifest joins, overlap,
centered padding, and corruption handling as implementations are replaced.
CUDA behavior and production resource sizing remain remote-host checks.

Establish automated focused CPU checks with the package task. These use small
self-contained fixtures without Box/W&B access, a GPU, or large downloads.
Start the reusable real-data walkthrough only after Box setup and the cleaned
variant 3 are established (Task 031, after Tasks 027 and 030B). Extend it through
each later stage; the final handoff rehearses the complete workflow. Fetch its
small external subset once, then allow routine checks without online services.
