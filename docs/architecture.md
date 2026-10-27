# Architecture contract

## Current implementation and replacement target

The installed `src/kelpseg/` package provides the Typer command and read-only
machine-path checks plus generic byte-preserving organization. The checkout retains legacy Planet `src.*` modules, root
`trainer.py`, `scripts/`, relevant configs, and focused tests until their
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

Prefer small functions with explicit inputs/outputs. Keep expensive stages
restartable; check existing input/output identities before resuming. Publish
complete deterministic manifests atomically and refuse silent overwrites.

## Researcher interface

The CLI uses Typer with `uv run kelpseg <command>` recipes. Keep a small root
app and separate thin command handlers, backed by ordinary workflow
functions callable from notebooks/tests without CLI context. Import heavy
workflow code only when its command runs. Preparation modules live together in
`src/kelpseg/prepare/`: `organize_inputs.py` loads/validates explicit declarations,
`organize.py` copies/verifies bytes, and `legacy_catalog.py` converts only the
historical CA/BC metadata. Keep these as explicit functions and ordinary loops;
the CLI uses standard Python logging for progress, without a custom logging
or orchestration layer. Task 028 establishes the installed
entry point and path checks; later tasks add their commands. The selected
training command style is `uv run kelpseg train --recipe <recipe-file>`;
it remains planned until the training task implements it. See
[quickstart.md](quickstart.md) for working setup, path-check and organization recipes.

Runtime dependencies cover implemented workflows: Typer and Rasterio.
Checkout-only dependencies for retained code live in the default `legacy`
group alongside `dev`; plain frozen setup includes both. New workflows promote
their dependencies into runtime as implemented. Distribution checks install
only frozen runtime dependencies, independently of legacy checkout tests.
Reusable functions return typed values and raise ordinary exceptions; CLI
handlers own output and exit status. Machine paths come from the explicit
`--paths` file, with no discovery; relative roots resolve against that file.

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
hashes; retain original paths even when long product names are unavailable.
Original grids need not match until the cleaning stage. The repaired historical
merge supplies membership/provenance evidence, not original label payloads.
See [data_artifacts.md](data_artifacts.md#planned-raw-intermediate-and-cleaned-releases)
for stage boundaries and mapping requirements. Organization is implemented; full release construction/publication and cleaning
remain later tasks.

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
metadata, retaining excluded identities/reasons; avoid destructive filtering
machinery where an explicit manifest selection suffices. The historical
1024/512 geometry, 50% nodata cutoff, and positive-only training selection are
reference policies to re-examine during the data audit, not unexplained new
defaults. Use ignore index `-100` for unscored labels and padding.

## Splits and loading

Store generated split assignments with the external dataset release. Keep split
algorithms/configs in Git. Load one canonical collection through manifests;
remove the requirement for hard-linked train/validation/test directory trees.

New-region and combined-data experiments select an explicit collection version.
Generate versioned assignments for that scope and preserve declared fixed test
identities. Check aliases/content overlap across deliveries as well as source
IDs so renamed copies cannot leak between train, validation and test. Resolve
conflicting annotation versions before selecting a collection's scoring labels.

Chips inherit source-level assignments, and acquisition-date groups remain
intact in the temporal baseline. Match source assignments across spectral
variants. LORO test is the complete held-out region; train/validation exclude
that region. Document the remaining regions' train/validation selection when
the replacement split task is selected. Training background exclusions never
silently constrain evaluation. Validate all joins and leakage boundaries.

## Prediction and scoring

Share one image/window predictor between unlabeled inference and labeled
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
