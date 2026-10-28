# Researcher quickstart

The installed `kelpseg` command checks machine paths, organizes raw catalogs,
checks ordinary image directories, and cleans imagery with optional paired
labels into separate derived outputs. Training, prediction, and evaluation
arrive in later tasks; see [the roadmap](todo.md). Retained legacy Planet code
is development/reference material, outside the installed package.

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
Typer, NumPy, and Rasterio (including their dependencies). Help/version do not
import the geospatial stack. Organization dry-run reads declarations only;
check and clean dry-run inspect TIFF headers.

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

For a first build into a fresh destination, preview before copying. The current
CA/BC `v1` is already closed, so this recipe now refuses that existing output;
fetch the published release below or select a fresh release ID for a new build.

```bash
uv run kelpseg organize --recipe configs/organize/ca_bc.toml --paths paths.local.toml --dry-run
```

The current CA/BC recipe uses the existing reconstructed external input catalog.
Task 030A built and verified the full 369-pair organized release; use the
[Box recovery recipe](box_backup.md#restore-the-organized-cabc-release) to fetch
it into a fresh directory. Do not rerun organization against the closed release.
The metadata-only catalog reconstruction is reproducible from Task 026/027
evidence:

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

Catalog construction is a one-pass operation into a fresh destination; it does
not resume or reuse an existing catalog. Existing catalogs retain their original
producer/code hashes after a source-code move. Use the existing catalog directly; do not regenerate or rewrite it just to
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

Preview, then copy once into a fresh declared release:

```bash
uv run kelpseg organize --recipe configs/organize/coast.toml --paths paths.local.toml --dry-run
uv run kelpseg organize --recipe configs/organize/coast.toml --paths paths.local.toml
```

Progress appears on stderr by default, with timestamps, preparation phases,
current filenames, completed/total files and MiB, verification and publication. A large copy or hash reports bytes about every
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

Organization must finish in one run. It writes into a fresh sibling
`.<release_id>.incomplete` directory, then renames that directory to the final
release after all checks pass. Both paths must be absent before starting. There
are no writer locks, saved receipts, recovery journals or resume mode.

A failure stops the sequence and leaves that incomplete directory for inspection.
The next attempt starts from the beginning: deliberately move/remove the failed
attempt or choose a fresh release ID. Completed releases are not reused by the
organizer; use `verify_organized_release` to inspect their recorded bytes without
rewriting them. No failure automatically deletes or replaces existing work.

The preparation code lives in `src/kelpseg/prepare/`: start with
`organize_inputs.py` for table/recipe validation and `organize.py` for the
one-pass copy flow. `legacy_catalog.py` is only the historical CA/BC conversion.
Reusable functions have no CLI context:

```python
from kelpseg.prepare.organize_inputs import load_organize_recipe
from kelpseg.prepare.organize import (
    build_organization_plan, organize_dataset, verify_organized_release,
)

plan = build_organization_plan(load_organize_recipe("configs/organize/coast.toml"), paths)
release = organize_dataset(plan)
result = verify_organized_release(release, plan)
```

They return typed values and raise `OrganizeError`; the command prints expected
errors to stderr with a nonzero exit status, without a traceback. Common fixes:
correct the named table/region/member, mount the intended source volume, restore
unchanged inputs from verified backup, or select a new release identity.

## Check ordinary image directories

`check` and `clean` accept image directories directly. No path settings file,
organizer catalog, CA/BC filename, or published release is required. Directory
paths resolve from your working directory; choose the recipe explicitly.
Files pair by their case-sensitive relative TIFF stem: `north/scene.TIF` pairs
with `north/scene.tiff`. Case-folded collisions, duplicate stems, empty image
scopes, symlinks, and missing or extra labels fail. Omit `--labels` for an
image-only scope; a supplied label directory must pair every image.

```bash
uv run kelpseg check --images /data/coast/images --labels /data/coast/labels --recipe configs/check/planet8_source.toml
uv run kelpseg check --images /data/coast/images --recipe configs/check/planet8_source.toml --full --report /data/reports/coast-full.json
```

The default quick check enumerates the complete scope and checks TIFF headers,
bands, dtype, CRS, affine grid, nodata declarations and paired grids. It does
not read pixels, validate classes, establish full readability, or hash files.
`--full` reads every selected image and native-label pixel in bounded blocks,
including full shared label mosaics. This can take substantial time for large
BC labels. A full scan establishes pixel evidence, not checksum identity.
Reports distinguish passed, failed, skipped, repairable and unknown evidence.
Repairable source grid/nodata issues still return a nonzero status; `clean`
can repair supported cases. Neither check level changes source files.

No report is created unless `--report` names a fresh file outside the input
directories. Reports publish atomically and refuse replacement. Keep generated
reports outside Git. The concise terminal summary states the requested level;
an exit status of 0 means that level and recipe passed.

The supplied Planet source recipe declares 8-band `uint16` imagery, category
values 0–4, and the audited missing-image-nodata fallback 0. That fallback is
explicit dataset policy; new data must establish its own policy. A declared
65535 takes precedence. The cleaned profile expects image nodata 0, label
nodata 3, matching grids, and image all-band zero implying label 3. A channel
count does not establish physical band names. Unknown region/date/band identity
stays unknown unless supplied evidence establishes it.

For another explicitly supported dataset, copy the recipe and edit ordinary
values. No dataset-specific Python branch or class mapping is selected by name:

```toml
schema_version = 1
profile = "source"
image_band_counts = [4]
image_dtypes = ["uint16"]
label_values = [0, 1, 3]
block_size = 512
# missing_image_nodata = 0  # Set only with evidence for this input scope.
# band_names = ["blue", "green", "red", "nir"]  # Requires matching header evidence.
```

Unknown keys fail. Leave `missing_image_nodata` absent to reject missing image
metadata, and leave `band_names` absent when names are unestablished. For cleaned
checks use `profile = "cleaned"`. Class vocabulary is explicit; checking values
does not establish what unfamiliar categories mean.

Full checking stops expensive scanning after unsupported headers, a read failure
or a failed pixel check. The report lists skipped work and completed scan counts;
failed reads are not retried. Quick checking still inventories the whole scope
and reports its header findings without reading arrays.

## Clean into a separate directory

The cleaner accepts CA/BC sources and ordinary TIFF directories that meet the
explicit recipe. It detects original image nodata first, nearest-aligns stored
label categories onto the exact image grid, and computes annotation coverage
independently of class zero or source masks. It preserves all image bands, dtype and valid values. Image
nodata and, for paired inputs, outside-annotation pixels become zero in every
band with metadata `nodata=0`; corresponding labels become 3 with metadata
`nodata=3`. Label 0 remains water/background. Existing label 3 can remain over
valid imagery. Labels are not remapped to binary here.

Paired alignment supports one-band `uint8` labels and north-up, unrotated image
and label grids in the same CRS. Different pixel sizes, offsets and extents are
allowed. Other CRSs, rotated/south-up grids and label dtypes are rejected with a
clear error; prepare separate compatible inputs before cleaning them. Image-only
cleanup does not need a label grid.

Matching image/label grids are read directly, with no reprojection. When grids
differ, alignment reads only the native label crop needed for each image window
and uses ordinary Rasterio nearest-neighbor reprojection on those stored values.
Source nodata metadata, masks and overviews do not decide label categories or
coverage. A crop over 16,777,216 source pixels is rejected; reduce the recipe's
`block_size` instead of loading the entire annotation mosaic into memory.

```bash
uv run kelpseg clean --images /data/coast/images --labels /data/coast/labels --output /data/derived/coast-v1 --recipe configs/clean/planet8.toml --dry-run
uv run kelpseg clean --images /data/coast/images --labels /data/coast/labels --output /data/derived/coast-v1 --recipe configs/clean/planet8.toml
uv run kelpseg check --images /data/derived/coast-v1/images --labels /data/derived/coast-v1/labels --recipe configs/check/planet8_cleaned.toml --full
```

Image-only cleanup uses the same command without `--labels`; it normalizes
source nodata, retains valid imagery and creates no labels:

```bash
uv run kelpseg clean --images /data/new-coast/images --output /data/derived/new-coast-v1 --recipe configs/clean/planet8.toml
```

Clean recipes contain the same expectation fields as source check recipes,
without `profile`, plus `qa_masks = false` and `compression = "deflate"`.
The declared vocabulary must include ignore 3 and exclude 255, which is
reserved as an unused temporary warp fill; lossless Deflate is the supported
output compression.
Detailed QA masks are off by default. Enable `qa_masks = true` in an explicit
recipe to retain coverage/reason evidence; this does not alter core output
pixels. Compact counts, original/output grids, nodata decisions, hashes and
provenance remain automatic. Outputs include `recipe.json`, `sources.json`
(source paths/hashes, original/output grids and counts), `check.json`
(independent full-check evidence), and `manifest.json` (the completion root
with exact file hashes). Relative filenames are retained under `images/`
and, when paired, `labels/`; directory names do not become invented scientific
identities. Original companions are recorded as hashed inactive provenance,
not copied beside changed TIFFs where stale masks or metadata could override
the new content. Unknown companion-mask meanings remain unused.

Dry-run resolves the scope and supported header repairs without writes; it is
not a completed pixel audit or cleaned release. Actual cleanup reads all source
pixels, hashes inputs and outputs, and runs the independent full cleaned check
before atomic publication. Use a fresh separate output outside all input roots.
Originals and organized inputs remain unchanged. Progress logs on stderr show
phases, files, counts/bytes and verification results; notebook functions use
normal Python logging.

An optional `--parent /data/2_organized/coast/v1` verifies an existing organized
release and carries its supplied identities/crosswalks into cleanup provenance.
It is unnecessary for ordinary directories. Production releases keep exact
variant-2 parent identities. The CA/BC parent is
`/Volumes/x10pro/kelpseg/data/2_organized/ca_bc/v1`; its authenticated release
identity and fetch/check recipe are in [Box recovery](box_backup.md#restore-the-organized-cabc-release).
Task 030B completed the separate full cleaned release; see the production recipe below.

Cleanup must finish in one run. It writes directly into a fresh sibling
`.<output-name>.incomplete` directory, then renames that directory to the final
output after all checks pass. Both paths must be absent before starting.

If a run fails or is interrupted, the incomplete directory stays available for
inspection and the final output is not published. The next run starts from the
beginning. Inspect and deliberately move or remove the incomplete directory,
or choose a fresh output name. There is no `clean --resume`, automatic cleanup,
per-source receipt, recovery journal or reuse of a completed cleaned output.
Do not run two cleaners against the same output name.

| Reported issue | Corrective action |
|---|---|
| Missing/ambiguous pair or name collision | Correct explicit relative filenames or supply a complete paired directory; omit labels only for a wholly image-only scope |
| Unsupported bands/dtype/classes or missing CRS | Establish the input format/semantics and use an appropriate explicit recipe; cleanup cannot infer them |
| Missing/inconsistent nodata | Restore valid declarations or document an evidence-backed missing-value fallback; inconsistent or unrepresentable declarations are rejected |
| Repairable grid or label nodata | Use shared cleanup into a fresh output, then full-check with the cleaned profile |
| Different CRS, rotated/south-up grids or non-uint8 labels | Prepare separate supported paired TIFFs; originals remain unchanged |
| Label crop exceeds the pixel limit | Reduce `block_size` so each native source crop stays within the supported memory bound |
| Retained all-band-zero collision | Review the original nodata policy/input; valid all-zero imagery cannot be silently reclassified by the requested output representation |
| Existing report/output or incomplete cleanup | Select a fresh destination; for failed cleanup, inspect and deliberately move/remove the incomplete directory before rerunning from the beginning |

The same functions work from Python:

```python
from pathlib import Path
from kelpseg.prepare.check import check_inputs, load_check_recipe
from kelpseg.prepare.clean_inputs import build_clean_plan, load_clean_recipe
from kelpseg.prepare.clean import clean_dataset

images, labels = Path("/data/coast/images"), Path("/data/coast/labels")
result = check_inputs(images, labels, load_check_recipe("configs/check/planet8_source.toml"))
print(result.passed, result.to_dict())
plan = build_clean_plan(images, labels, Path("/data/derived/coast-v1"),
                        load_clean_recipe("configs/clean/planet8.toml"))
release = clean_dataset(plan)  # fresh output; the entire run must complete
```

For image-only use pass `None` for labels. These plain functions return typed values; CLI handlers supply presentation and
exit codes. Source-aware nodata and nearest-alignment functions are shared with
the retained correctness coverage. See [Task 029B](../tasks/029b_clean_organized_sources.md)
for the migration map and bounded verification evidence.

## Full CA/BC cleaned release

Task 030B used the following commands on all 369 pairs after authenticating the
organized parent's local-ready handoff. These commands are implemented; `v1`
is now closed, so do not rerun into it. For a new production attempt, choose a
fresh final/staging name and keep separate evidence.

```bash
organized_root='/Volumes/x10pro/kelpseg/data/2_organized/ca_bc/v1'
cleaned_root='/Volumes/x10pro/kelpseg/data/3_cleaned/ca_bc/v1'
uv run --frozen --no-sync kelpseg clean --images "$organized_root/images" --labels "$organized_root/labels" --parent "$organized_root" --output "$cleaned_root" --recipe configs/clean/planet8.toml --dry-run
uv run --frozen --no-sync kelpseg clean --images "$organized_root/images" --labels "$organized_root/labels" --parent "$organized_root" --output "$cleaned_root" --recipe configs/clean/planet8.toml
```

Run the second step only after the preview succeeds. The cleaner performs full
source and output QA automatically. Production retained eight uint16 bands and
categories 0–4, image nodata 0/label ignore 3, and all parent identities. Its
747-file release includes 369 aligned pairs and compact provenance/QA, with no
active original sidecars. All 418 companion associations remain inactive
references in the immutable organized parent.

Use [Box recovery](box_backup.md#cleaned-cabc-v1) for the trusted manifest hash,
fresh-directory fetch and byte verification. A restored release loads from its
own `images/` and `labels/`; historical absolute source paths in provenance are
not required. Chipping and the tiny walkthrough remain Task 031.

## Follow the preparation code

Start at `clean_dataset` in `src/kelpseg/prepare/clean.py`. Follow one run:
check the inputs, clean each source, independently check the outputs, and
publish. `_clean_pair` opens one source; `_write_cleaned_windows` contains the
pixel rules. `aligned_label` in `alignment.py` is a plain function returning
label values and coverage for one window; it uses a raw crop and Rasterio
`reproject`, with no custom XML or generator. `check.py` separates directory
discovery, source/header checks and full pixel scanning. Comments explain the
scientific choices. Routine dataset changes use recipe values rather than Python
edits.

Cleanup logs identify four phases (hash inputs, check source pixels, clean,
then verify/publish), source dimensions/bands, original nodata,
paired versus image-only decisions, QA mask settings, pixel changes and final
verification. Long scans and hashes give periodic progress updates. Save the
ordinary Python logs by appending `2> clean.log` to a command.

Every preparation write needs a fresh output. Existing completed releases can
still be checked with `verify_organized_release` or `verify_cleaned_release`
without rebuilding a plan, repeating the command or rewriting them.

## Later workflows and outputs

The selected future training style is
`uv run kelpseg train --recipe <recipe-file>`. It is not available yet.
Band/chip selection, training, prediction, scoring, LORO, and
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
