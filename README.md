# Planet kelp segmentation

A local rebuild of this fork into a small toolkit for binary kelp segmentation
on Planet 8/4/3-band imagery. The workflow covers data preparation and chipping,
training, evaluation, unlabeled inference, leave-one-region-out comparisons,
and adaptation to new regions.

The installed `kelpseg` package currently provides help/version and read-only
machine-path checks, byte-preserving raw organization from explicit catalogs,
quick/full directory checks, shared cleanup, native-band chipping with optional
labels, and source-level baseline/LORO split manifests. The chip loader selects
8/4/3 bands and pads partial edges. Window selection keeps overlap for training;
chip validation/test selection is disjoint and reports geometric coverage gaps.
The `pixel-stats` command computes raw training-band means and sample standard
deviations with an optional cap and manifest-based kelp-only chip filter.
Installed `preview-augmentations` and `preview-pipeline` commands preview real
Albumentations classes on training
examples, with exact capped normalization and separately labeled backgrounds;
see the [isolated previews](docs/quickstart.md#preview-individual-augmentations)
and [combined pipeline preview](docs/quickstart.md#preview-the-combined-augmentation-pipeline).
Preparation runs once into a fresh output and stops on failure, with no restart
support. Installed Python helpers connect training/validation tensors to
SegFormer B3, the selected loss and pooled confusion metrics; see
[model inputs](docs/quickstart.md#model-and-training-inputs-python).
The installed `train` command uses Lightning for fitting, validation, checkpoints
and completed-epoch resume; see [training recipes](docs/quickstart.md#train-and-validate).
[Portable bundles](docs/quickstart.md#copy-and-use-a-portable-model) predict supplied
image arrays offline. [Tiled prediction](docs/quickstart.md#predict-cleaned-source-tiffs)
writes georeferenced probabilities and masks from cleaned imagery without labels.
`predict-chips` saves disjoint evaluation-chip predictions; both paths feed the
shared [`report` command](docs/quickstart.md#post-training-validation-diagnostics),
which produces labeled diagnostics without rerunning inference.
[`temporal-report`](docs/quickstart.md#temporal-canopy-change) compares proportional
canopy change against labels on common valid footprints using saved reports.
The obsolete Planet scripts, class-path configs and checkout-only `src.*`
implementation are retired. Historical Tasks 000–023 and starting commit
`ac933fd667c2ddb445b8a622d8404387a2d056e2` remain as evidence;
[Task 037](tasks/037_baseline_comparisons_and_loro.md#037d--retire-legacy-code)
records replacements and source recovery. Current portable LORO bundles use
the installed prediction commands.

## Start here

Use the [researcher quickstart](docs/quickstart.md) for installation, local
settings, command output, and fixes for common errors. For the external Linux
GPU instance, follow the [GPU setup checklist](docs/gpu_setup.md); installation
and GPU validation will be tested and refined on that machine. Development context is
routed through [docs/index.md](docs/index.md) and [the roadmap](docs/todo.md).
The legacy reference and provenance audit are complete;
[Task 027](tasks/027_verify_box_and_back_up_raw_reference_audit.md) owns the
raw/reference/audit backup and its verification status.

The toolkit uses one installable Python package, short explicit recipes,
a locked uv environment, and no `scripts/` directory. Test as much of the workflow as
practical on the Mac with small examples before moving to a GPU host. Full
training is not intended for the Mac.

## Environment

Use Python 3.12 and the locked uv environment:

```bash
uv python install 3.12
uv sync --python 3.12 --frozen
uv run kelpseg --help
uv run kelpseg --version
```

Create your local path settings as described in the quickstart, then run:

```bash
uv run kelpseg check-paths --paths paths.local.toml
```

The Typer command calls reusable Python functions. Workflow settings
live in recipe files. The training command is
`uv run kelpseg train --recipe <recipe-file>`.
The recipe selects the variant and machine-paths file; each fit gets an automatic run ID.
Use `--dry-run` to preview the inputs and update budget before fitting.

Development checks use synthetic CPU fixtures, including fresh wheel/sdist
installation outside the checkout:

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
```

`pytest` includes repository hygiene checks for tracked and nonignored untracked
files: YAML/JSON/TOML syntax, conflict markers, the 500 KiB file-size limit,
mixed line endings, trailing whitespace and final newlines. Deleted files,
symlinks and lockfiles are skipped. Run just these checks with
`uv run pytest -q tests/test_repository_hygiene.py`. Ruff checks Python syntax
and debugger statements as well as formatting/lint. Checks report errors without
rewriting files; no Git hooks or pre-commit installation are needed. CI runs the
same pytest and Ruff commands. Historical task records retain their original
validation commands as evidence.

Use `uv build` to create the wheel and source distribution. The default
checkout environment includes the `dev` dependency group. Runtime dependencies
include the optional W&B tracking integration used by training recipes; no
legacy dependency group remains.

## Data and experiments

Raw archives, organized and cleaned intermediates, chips, generated split
assignments, checkpoints, and results live outside Git. Keep preparation rules,
configs, focused tests, and human-readable cleanup documentation in Git.
UCLA Box through rclone is
the target backup/transfer store; the existing local root is
`/Volumes/x10pro/kelpseg`.

The three dataset stages are **1 raw sources**, **2 organized intermediate**,
and **3 cleaned intermediate**. Both intermediates stay unsplit; organization
preserves source bytes, while cleanup records explicit transformations. The
scoped audit is complete; existing repaired datasets remain historical evidence.
See [docs/data_artifacts.md](docs/data_artifacts.md) for variant/provenance rules
and [docs/cleanup_provenance.md](docs/cleanup_provenance.md) for established facts
and remaining evidence limits. The organized and cleaned CA/BC releases are
complete. The native-band CA/BC chip release, both baseline variants and all ten
LORO folds are published with portable controls; the 13-crop tiny v2 is available
from Box for offline split/chip/load and bounded training practice. See the
[researcher guide](docs/quickstart.md#restore-and-use-the-full-cabc-chip-release).

The local working set keeps cleaned imagery/chips and small controls/evidence.
Raw ZIPs and organized payloads can be restored from Box; obsolete local datasets
were evicted after archiving their small historical records. See
[storage policy](docs/data_artifacts.md#current-local-working-set).

The spectral comparison uses native 8 bands, RGB+NIR, NIR/red/green and RGB
from the same acquisitions, each with and without the BC training regions. Start with the working SegFormer recipe; a possible RGB
DINOv3 variant follows separately. New-region work compares direct transfer,
kelp-checkpoint fine tuning, generic-pretrained fine tuning, and combined
old/new training on fixed held-out test data.

W&B remains `kdorman90-ucla/kelpseg`; new work uses new experiment identities.
See [docs/product.md](docs/product.md) for the research contract and
[docs/experiments.md](docs/experiments.md) for run and checkpoint rules.
