# Researcher quickstart

The installed `kelpseg` command checks machine paths and organizes explicit
raw image/label catalogs without changing payload bytes. Cleanup, training,
prediction, and evaluation arrive in later tasks; see [the roadmap](todo.md). The retained legacy Planet
code is development/reference material, outside the installed package.

## Install

From the repository, use Python 3.12 and the locked environment:

```bash
uv python install 3.12
uv sync --python 3.12 --frozen
uv run kelpseg --help
uv run kelpseg --version
```

Normal checkout setup includes developer tools and dependencies needed by the
retained Planet correctness tests. The installed package itself currently needs
Typer and Rasterio (including their dependencies). Rasterio inspects copied
TIFF headers; help/version and dry-run do not import the geospatial stack.

## Set paths once per machine

```bash
cp configs/paths.example.toml paths.local.toml
```

Edit the two strings in `paths.local.toml`:

```toml
[paths]
data_root = "~/kelpseg"
runs_root = "~/kelpseg/runs"
```

`data_root` is your artifact root. The existing research root on this Mac is
`/Volumes/x10pro/kelpseg`; select it when working with that mounted volume.
`runs_root` is the location for future experiment outputs and can be beneath
the artifact root. Neither path goes into tracked machine-specific settings.

Both roots must already exist. To try the home-directory example without any
research data, create its empty directories yourself:

```bash
mkdir -p "$HOME/kelpseg/runs"
uv run kelpseg check-paths --paths paths.local.toml
```

The output lists the absolute settings-file location, `data_root`, and
`runs_root`, followed by `Both roots are existing directories.` This checks
directory existence only. It does not fetch data, scan imagery, check write
permissions, or verify a dataset or Box backup.

The required `--paths` option chooses exactly one file. There is no search for
a settings file in parent folders or automatic fallback. `~` expands to your
home directory; relative paths inside the TOML resolve against that file's
directory. Environment-variable expressions such as `$DATA_ROOT` stay literal.
Quote paths containing spaces. The local settings file is ignored by Git.

If invoking the installed command from elsewhere, pass the settings file's
absolute path. Within the repository, prefer the `uv run kelpseg ...` recipes
above. `python -m kelpseg` in the installed environment uses the same interface.

## Fix a failed check

| Message | Action |
|---|---|
| Cannot read settings | Check the `--paths` filename and read permissions; copy the example if needed |
| Invalid TOML or non-UTF-8 text | Save the file as UTF-8 and correct the reported syntax |
| Unknown setting/key | Keep only `[paths]`, `data_root`, and `runs_root`; check spelling |
| Missing/non-string value | Give each root a nonempty quoted string |
| Not an existing directory | Select an existing directory, mount the intended drive, or create the intended directory yourself |
| No such command | Use `uv run kelpseg --help` for the commands currently implemented |

Success returns exit status 0. Expected settings errors go to stderr with a
nonzero status and a corrective message. The check never creates or changes
files, on success or failure.

## Use the functions from Python

```python
from kelpseg.paths import check_paths, load_paths

settings = check_paths(load_paths("paths.local.toml"))
print(settings.data_root)
```

These functions return immutable `PathSettings` values and raise
`PathSettingsError` for invalid settings. They do not print, exit, or depend on
CLI context; the command handles presentation separately.

## Organize raw sources

Organization copies declared imagery, labels, masks and sidecars into an
unsplit release with stable names. Source grids, classes, nodata and band order
stay unchanged. A valid plan checks declarations and member listings; it does
not establish verified member bytes until copying succeeds.

```bash
uv run kelpseg organize --recipe configs/organize/ca_bc.toml --paths paths.local.toml --dry-run
```

The current CA/BC recipe needs the reconstructed external input catalog. Its
369-pair plan is reconciled; full materialization and Box publication belong to
Task 030A. The metadata-only reconstruction is reproducible from the existing
Task 026/027 evidence:

```python
from pathlib import Path
import logging

from kelpseg.prepare.legacy_catalog import build_legacy_ca_bc_catalog
from kelpseg.paths import load_paths

logging.basicConfig(level=logging.INFO, format="%(message)s")
paths = load_paths("paths.local.toml")
build_legacy_ca_bc_catalog(
    paths, Path("configs/regions.csv"),
    paths.data_root / "preparation_inputs/ca_bc/v1",
)
```

Existing catalogs retain their original producer/code hashes after a source-code
move. Use the existing catalog directly; do not regenerate or rewrite it just to
change Python import paths. A new reconstruction with changed producer code
needs a new catalog version and an explicit recipe change.

For a new independent dataset, create a catalog under your `data_root` and
supply its own tables; no CA/BC mapping or Python edits are needed. Example
`configs/organize/coast.toml`:

```toml
schema_version = 1
dataset_id = "coast"
release_id = "v1"
input_catalog = "preparation_inputs/coast/v1"
regions = "../coast_regions.csv"
```

Use UTF-8 CSV with a header. Unknown columns/settings, blank required values,
and duplicate table keys fail. Optional hash/stat fields may be omitted or
blank. Dates are `YYYY-MM-DD`. These are the table columns:

| Table | Columns |
|---|---|
| `deliveries.csv` | `delivery_id,kind,path,sha256,file_catalog,evidence,verified_bytes,verified_mtime_ns` |
| `membership.csv` | `source_key,region_code,acquisition_date,legacy_source_id,image_delivery_id,image_member,label_delivery_id,label_member,image_sha256,label_sha256` |
| `aliases.csv` | `source_id,asset_id,role,alias,alias_type,evidence` |
| Optional `assets.csv` | `source_id,asset_id,parent_role,kind,delivery_id,member_relative_path,destination,sha256` |
| Recipe's region CSV | `region_code,legacy_region_id,region_name` |
| Directory file catalog | `member_relative_path,bytes,sha256` |

`delivery_id`, dataset/release IDs, asset IDs and kinds use lowercase ASCII
letters/digits, underscores or hyphens, starting with a letter/digit. Region
codes use lowercase letters/digits. A source key starts with its acquisition
date `YYYYMMDD` and uses lowercase letters/digits separated by underscores,
e.g. `20260115_scene2_tile3`. Canonical `source_id` is
`<region_code>_<source_key>`. Primary destinations are
`images/<source_id>.tif` and `labels/<source_id>.tif`.

Each membership row gives both exact delivery IDs and member paths. Repeated
locators are allowed: different pairs can share source bytes. `legacy_source_id`
and image/label SHA-256 values may be blank; supplied hashes are checked.
Regions have unique codes; names may repeat. Every alias names its owning
source, role (`image`, `label` or `pair`), optional asset ID, exact name/path,
`alias_type` and evidence reference. Alias text may repeat across owners.
For no aliases, keep the CSV header alone. Missing historical names stay absent.

A delivery `path` is relative to `data_root`. For `kind=zip`, `sha256` is the
archive identity and `file_catalog` is blank. Ordinarily the copy operation
hashes the archive before reading selected members. Only trusted prior hash
evidence with matching `verified_bytes` and `verified_mtime_ns` permits reuse;
never fill those fields from an unverified file. Changed evidence triggers a
fresh archive hash. Dry-run only reads the ZIP directory.
For `kind=directory`, `file_catalog` is relative to the input catalog, `sha256`
is that CSV's hash, and every selected file needs its own byte size and SHA-256
in that CSV. Copy verifies those source bytes. Do not use a folder timestamp
as content identity.

Assets explicitly name their source/parent role, unique owner-scoped asset ID,
kind, delivery/member and destination. Example mask destination:
`masks/<source_id>.tif`; image sidecar: `images/<source_id>.tif.aux.xml`.
Sidecar contents stay unchanged, including internal old filenames; header
records describe the internal TIFF without applying sidecars. Asset expected
`sha256` may be blank for ZIP sources. No mask semantics are inferred.
All input/destination paths use forward slashes, no absolute paths, drive
prefixes, backslashes, dot/dot-dot components or symlinks. The recipe's region
path alone may use `..` to reach a tracked sibling table. Control names,
temporary suffixes and colliding destination subtrees are reserved.

Preview, then copy or explicitly resume the same declared release:

```bash
uv run kelpseg organize --recipe configs/organize/coast.toml --paths paths.local.toml --dry-run
uv run kelpseg organize --recipe configs/organize/coast.toml --paths paths.local.toml
uv run kelpseg organize --recipe configs/organize/coast.toml --paths paths.local.toml --resume
```

Progress appears on stderr by default, with timestamps, preparation phases,
current filenames, completed/total files and MiB, resume checks/reused files,
verification and publication. A large copy or hash reports bytes about every
ten seconds. For a saved progress log, add `2> organize.log` to the command.
The library uses ordinary Python logging; in a notebook, enable it once with
`logging.basicConfig(level=logging.INFO, format="%(message)s")`.

The preview prints resolved catalog/delivery locations, dataset/release,
counts, selected bytes, destination and logical plan hash before any copies.
Outputs go to `data_root/data/2_organized/<dataset_id>/<release_id>/`:
TIFFs/companions, `regions.csv`, `sources.csv`, `filename_aliases.csv`, optional
`assets.csv`, portable `recipe.json`/`inputs.json`, and `manifest.json`.
Source rows record original locators, parent delivery hashes, separate image/
label hashes and sizes, and internal header metadata. No delivery train/val
path becomes a new experimental assignment.

A sibling `.<release_id>.incomplete` holds staging, frozen state and per-file
receipts; `.<release_id>.lock` prevents concurrent writers. Interrupted work
requires `--resume`; every completed staged file is byte-verified. Only an
unfinished payload temporary identified by the command's copying record may
be recreated. Unknown files, partial control records, changed plans or corrupt
outputs stop and retain evidence. Inspect such failures; do not delete receipts
or overwrite files to bypass them. Correct the input or choose a new explicit
release ID. Completed matching releases are verified and returned without
rewriting. Final publication renames the verified directory atomically.

The preparation code lives in `src/kelpseg/prepare/`: start with
`organize_inputs.py` for table/recipe validation and `organize.py` for the
copy/resume flow. `legacy_catalog.py` is only the historical CA/BC conversion.
Reusable functions have no CLI context:

```python
from kelpseg.prepare.organize_inputs import load_organize_recipe
from kelpseg.prepare.organize import (
    build_organization_plan, organize_dataset, verify_organized_release,
)

plan = build_organization_plan(load_organize_recipe("configs/organize/coast.toml"), paths)
release = organize_dataset(plan)  # resume=True only for matching interrupted work
result = verify_organized_release(release, plan)
```

They return typed values and raise `OrganizeError`; the command prints expected
errors to stderr with a nonzero exit status, without a traceback. Common fixes:
correct the named table/region/member, mount the intended source volume, restore
unchanged inputs from verified backup, or select a new release identity.

## Later workflows and outputs

The selected future training style is
`uv run kelpseg train --recipe <recipe-file>`. It is not available yet.
Preparation, band/chip selection, training, prediction, scoring, LORO, and
adding a region will gain copyable recipes here when implemented. Most settings
will live in those recipes, with a few explicit command options.

Later run-producing commands will use `<runs_root>/<run_id>/`, with resolved
settings/input identities at the root and `checkpoints/`, `metrics/`, and
`figures/` underneath. This is an agreed layout, not an implemented run manager.
The reusable real-data walkthrough begins after Box and cleaned-data
establishment in Task 031. Current automated fixtures use temporary synthetic
data, requiring no Box/W&B login, GPU, model weights, or research-data download.

See [data and artifacts](data_artifacts.md) for storage/backup rules and
[experiments](experiments.md) for model, checkpoint, and run identity rules.
