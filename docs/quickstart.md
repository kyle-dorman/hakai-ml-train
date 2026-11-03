# Researcher quickstart

The installed `kelpseg` command checks machine paths, organizes raw catalogs,
checks ordinary image directories, cleans imagery with optional paired labels,
chips cleaned TIFFs into one native-band collection, assigns source splits,
and computes training-image pixel statistics.
Training, prediction, and evaluation arrive in later tasks; see [the roadmap](todo.md). Retained legacy Planet code
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
Typer, NumPy, Rasterio, Albumentations and Matplotlib (including their dependencies). Help/version do not
import the geospatial stack. Organization dry-run reads declarations only;
check and clean dry-run inspect TIFF headers. Split dry-run reads metadata only.

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

For preparation commands, the required `--paths` option chooses exactly one file.
Training selects that same machine-paths file through `paths_file` in its recipe. There is no search for
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

The current CA/BC recipe uses the finished input catalog at
`<data_root>/preparation_inputs/ca_bc/v1/`. Its `deliveries.csv`, `membership.csv`,
`aliases.csv`, `assets.csv` and `catalog_manifest.json` remain available. Use
those declarations directly; normal organization does not read old merge CSVs
or import a historical bootstrap. That one-time converter has been retired.
Historical controls/source are archived locally under
`<data_root>/history/legacy_pre_rebuild_v1/`.

The raw ZIPs and organized v1 payloads were evicted locally after their verified
Box publication. Upcoming training uses the current chips; full-TIFF work uses
the retained
cleaned release. To obtain organized v1, use the
[Box recovery recipe](box_backup.md#restore-the-organized-cabc-release).

To rebuild organization instead, first restore the three original ZIPs into the
paths declared by the existing catalog. This is a download recipe, not a step
needed for training. Choose the artifact root in your local settings:

```bash
(
  set -e
  data_root='/Volumes/x10pro/kelpseg'
  test ! -e "$data_root/zip_archive"
  rclone copy kelp-box:kelpseg/data/1_raw/ca_bc_sources_v1 "$data_root/zip_archive" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
  uv run kelpseg organize --recipe configs/organize/ca_bc.toml --paths paths.local.toml --dry-run
)
```

Preview before any organization write. Local output must be fresh; choose a new
release ID when changing inputs/settings and preserve the published Box v1.
The finished catalog retains its original historical producer/evidence metadata;
retiring the converter does not require rewriting that catalog.

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
one-pass copy flow. Historical CA/BC catalog construction is retired; the
organizer consumes the existing explicit tables directly.
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
not required. Continue with [chipping](#chip-cleaned-imagery) and the
[tiny walkthrough](#tiny-real-data-walkthrough) below.

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

## Chip cleaned imagery

Use cleaned uint16 imagery with declared nodata 0, all-band-zero invalid pixels,
and 3, 4 or 8 explicitly named bands. Optional labels must be single-band uint8
on the exact same grid. Use `check`/`clean` above if these conditions are unmet;
chipping never realigns labels or repeats cleaning. Source TIFFs stay unchanged.

```bash
uv run kelpseg chip --images /data/cleaned/images --labels /data/cleaned/labels --output /data/chips/coast-v1 --recipe configs/chip/planet8.toml --dry-run
uv run kelpseg chip --images /data/cleaned/images --labels /data/cleaned/labels --output /data/chips/coast-v1 --recipe configs/chip/planet8.toml
```

Run the second command only if the preview succeeds. Omit `--labels` for wholly
image-only data. The preview shows input paths/bytes, native band order, window
count, settings and output. It reads headers only; retention and pixel values
are checked during chipping. Progress shows the current source, retained/omitted
windows and output bytes. Both final and sibling `.<name>.incomplete` paths must
be absent, and the output parent must exist. A failure stops immediately and
leaves incomplete work for inspection; the next attempt needs a fresh output.

Copy `configs/chip/planet8.toml` to change ordinary settings:

```toml
schema_version = 1
chip_size = 512
stride = 256
max_nodata_pct = 50
source_band_names = ["coastal_blue", "blue", "green_i", "green", "yellow", "red", "rededge", "nir"]

[label_mapping]
0 = 0
1 = 1
2 = 0
3 = -100
4 = 0
```

The band order is the user-declared assumption for the current CA/BC collection;
it is not independently established by every TIFF header. Contradictory explicit
header descriptions fail. Other collections need their own band declarations
and label mapping. Unknown settings, duplicate bands and invalid ranges fail.
For native four-band or RGB imagery, declare its actual order and use that same
order when loading; channel count alone never selects a physical band recipe.

The grid starts at zero and advances by `stride`, stopping at the first window
that reaches the end. An axis of length 513 yields starts 0/256 and widths
512/257. Windows never shift inward. Chips keep their true sizes without stored
padding. Nodata percentages use actual source pixels; exactly 50% is retained,
above 50% is omitted. Background-only chips remain. Mapping is explicit: label
1 is kelp, 0/2/4 background, and 3 ignore. Image nodata always forces target
-100; valid label zero stays background even when TIFF metadata calls it nodata.

Outputs are `chips/<source_key>/r<row>_c<col>.npz`, `windows.csv`, `sources.json`,
`recipe.json`, and `summary.json`. The final directory appears after the entire
run succeeds. NPZ files contain HWC `image` uint16 and optional HW `label` int8,
with no pickle or normalization. Every candidate window has a CSV row, including
omitted windows with an empty payload path. Source metadata plus local/original
row/column and true dimensions determine spatial placement; the crop transform
maps local coordinates to the CRS. Counts distinguish image nodata, mapped
background/kelp/ignore and ignore over valid imagery. Window counts overlap and
must not be interpreted as unique source coverage. No checksum, authentication
catalog or transfer receipt is produced.

For scientific identity, add `--metadata /data/identity.csv`. The optional UTF-8
CSV uses these columns (only `source_key` is required; omit or leave other
columns blank for unknown values):

```text
source_key,source_id,original_tiff,dataset_id,release_id,region,acquisition_date,row_offset,col_offset,original_height,original_width
```

`source_key` is the exact image path relative to `--images`, without `.tif` or
`.tiff`; all selected images must join once, with no extra rows. `source_id` and
`original_tiff` identify the original source, shared by all its crops. Dates use
`YYYY-MM-DD`. Offsets are nonnegative pixels on that original TIFF; default zero.
A nonzero offset requires the corresponding original dimension, and crops must
fit within it. Original dimensions otherwise default to the selected TIFF size.
Contradictory region/date/dimensions or geographic grids for one original
identity fail; crop offsets must lead back to the same original grid. Without
metadata, relative TIFF identity and grid remain known; region/date/dataset/
release stay null. Do not split crops of one original TIFF across partitions.

The same workflow and loading functions work in Python:

```python
from kelpseg.prepare.chip_inputs import build_chip_plan, load_chip_recipe
from kelpseg.prepare.chip import chip_dataset
from kelpseg.chips import load_chip

recipe = load_chip_recipe("configs/chip/planet8.toml")
plan = build_chip_plan("/data/cleaned/images", "/data/cleaned/labels",
                       "/data/chips/coast-v1", recipe,
                       metadata="/data/identity.csv")
output = chip_dataset(plan)
# Use a retained payload path from windows.csv:
chip = load_chip(output / "chips/scene/r0_c0.npz",
                 recipe.source_band_names, selection="rgbnir",
                 chip_size=recipe.chip_size)
```

`selection="all"` keeps native order; `rgbnir` selects red/green/blue/NIR and
`rgb` selects red/green/blue. Explicit ordered names or one-based indices also
work. For the current eight-band recipe RGB+NIR indices are `[6, 4, 2, 8]`,
RGB `[6, 4, 2]`. No spectral payload copies are needed. Label mapping happens
only during chipping. Image validity is computed
from all native bands before selection; a zero selected band alone is valid.
Loading pads bottom/right with image zero and label -100, returning true height/
width and `(top, bottom, left, right)` padding. The returned nodata mask marks
native nodata only; artificial padding stays separate. Remove padding with
`array[:true_height, :true_width]` before placing results on the source grid.

## Assign sources and select chip windows

`split` assigns original TIFFs before chipping; it never reads image pixels.
Use the approved `configs/split/ca_bc_v1.toml` for CA/BC. Preview the full
cleaned catalog with its explicit release version:

```bash
uv run kelpseg split --cleaned /Volumes/x10pro/kelpseg/data/3_cleaned/ca_bc/v1 --release-id v1 --recipe configs/split/ca_bc_v1.toml --output /Volumes/x10pro/kelpseg/examples/runs/my-source-splits-v1 --dry-run
```

Remove `--dry-run` to write the five controls into a fresh output. Its parent
must exist; neither the final directory nor its incomplete sibling may exist.
A failed run stops; choose a fresh output for the next attempt. The command
prints resolved paths, original-source/crop/region/date counts and all split
counts. Progress on stderr shows recipe/source reading, row counts, fold
assignment and validation, then each output file. Full CA/BC baseline `base`
has 216 train, 53 validation and 58 test sources; `augmented` adds 42 training-only sources from 011/012. There are ten
LORO folds, one per evaluation region 001–010.

For a subset, crops or a combined collection, use `--sources identity.csv`
instead of `--cleaned ... --release-id ...`. Its columns are the chipping
identity schema above plus optional `satellite_id`. Splitting requires
`source_key`, `source_id`, `dataset_id`, `release_id`, `region` and
`acquisition_date`. Keep zero-padded region codes as strings. Supply physical
`satellite_id` for other naming conventions; current Planet original source IDs
resolve it without using crop suffixes. Crops retain their original ID, offsets
and dimensions. Every crop/chip of `(dataset_id, release_id, source_id)` inherits
one assignment. Region/date and spacecraft/UTC-day groups stay together across
regions; a spacecraft may cross partitions on different dates.

Outputs are `collection.csv`, `chip_metadata.csv`, `assignments.csv`,
`recipe.json` and `summary.json`. `collection.csv` records crops and satellite
IDs; `assignments.csv` records each original source's experiment, variant,
split and reason. `chip_metadata.csv` exports exactly the chipping identity
columns above, without `satellite_id`; pass it to `chip --metadata`. For full
cleaned sources, its key is the canonical image stem. No per-fold copies or
link trees are needed. Generated rows stay outside Git.

Baseline uses the approved inclusive cutoffs. Each LORO fold tests every date
of its held-out region; other-region spacecraft/day companions are unused.
Remaining baseline train/validation roles persist, while remaining baseline
test sources are unused. The `base` variant excludes 011/012; `augmented`
includes them for training, subject to those companion exclusions. Both keep
evaluation-region source memberships fixed. With BC (`augmented`) is the
primary baseline; without both BC regions (`base`) is the comparison. Canonical
background chips remain.

Missing/duplicate keys, conflicting original metadata or known aliases, missing
region rules, unresolved spacecraft on evaluation dates and cross-partition
groups fail with an actionable error. Recipe errors name unknown/missing keys
and the affected region; source CSV errors identify the row/source to fix.
Correct the declaration before rerunning; do not adjust approved CA/BC dates or
partitions. Other datasets may use their own flat recipe with `schema_version`,
`training_only_regions` and `[[regions]]` rows containing `region`, `direction`, `first_cutoff`, `second_cutoff`.

The same source operations are ordinary Python functions:

```python
from kelpseg.paths import load_paths
from kelpseg.prepare.split_inputs import load_split_recipe, read_collection
from kelpseg.prepare.splits import assign_sources, write_splits

root = load_paths("paths.local.toml").data_root
collection = read_collection(cleaned=root / "data/3_cleaned/ca_bc/v1",
                             release_id="v1")
recipe = load_split_recipe("configs/split/ca_bc_v1.toml")
assignments = assign_sources(collection, recipe)
# Choose a fresh output whose parent exists:
output = write_splits(collection, assignments, recipe,
                      root / "examples/runs/my-source-splits-v1")
```

## Restore and use the full CA/BC chip release

The published release uses matching paths beneath your local artifact root and
`kelp-box:kelpseg`:

| Artifact | Relative path |
|---|---|
| Native eight-band chips and window controls | `data/chips/ca_bc/v1/` |
| Source collection and baseline/LORO assignments | `data/splits/ca_bc/v1/` |
| Portable collection declaration | `data/collections/ca_bc/v1/collection.json` |

Fetch into a fresh local root. Set `data_root` to your chosen destination;
these sequential copies stop on the first error. The chip copy downloads the
complete canonical collection, including background and overlapping payloads.
It needs about 65.6 GB: 26,573 NPZs plus four controls (26,577 files). The
separate split controls total 935,947 bytes; the declaration is 539 bytes.

```bash
(
  set -e
  data_root="$HOME/kelpseg-release-01"  # Choose a fresh directory.
  test ! -e "$data_root"
  mkdir -p "$data_root/runs" "$data_root/data/chips/ca_bc" "$data_root/data/splits/ca_bc" "$data_root/data/collections/ca_bc"
  rclone copy kelp-box:kelpseg/data/chips/ca_bc/v1 "$data_root/data/chips/ca_bc/v1" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
  rclone copy kelp-box:kelpseg/data/splits/ca_bc/v1 "$data_root/data/splits/ca_bc/v1" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
  rclone copy kelp-box:kelpseg/data/collections/ca_bc/v1 "$data_root/data/collections/ca_bc/v1" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
)
```

Set `data_root` in `paths.local.toml` to this artifact root and `runs_root` to
its `runs/` directory before using Python. The small
`collection.json` references the cleaned, chip and split dataset/release IDs,
their relative locations and the existing split `collection.csv`. Resolve its
paths from the declaration's directory, preserving the layout above when moving
the release. Readers take explicit local roots:

```python
import json
import logging
from collections import Counter
from kelpseg.paths import load_paths
from kelpseg.prepare.splits import select_windows
from kelpseg.chips import load_chip

logging.basicConfig(level=logging.INFO)
root = load_paths("paths.local.toml").data_root
chip_root = root / "data/chips/ca_bc/v1"
split_root = root / "data/splits/ca_bc/v1"
recipe = json.loads((chip_root / "recipe.json").read_text())
rows = select_windows(chip_root, split_root / "assignments.csv",
                      experiment="baseline", variant="augmented")
print(Counter(row["split"] for row in rows))
# Primary baseline: 18,311 train, 933 val, 1,262 test, 20,065 unused candidates.
training = [row for row in rows if row["split"] == "train"]
validation = [row for row in rows if row["split"] == "val"]
chip = load_chip(training[0]["payload"], recipe["source_band_names"],
                 "rgbnir", recipe["chip_size"])
print(chip["image"].shape, chip["padding"])
```

Use `augmented` for the primary with-BC baseline and `base` for the comparison
without both 011/012. Choose `loro_001` through `loro_010` for a held-out region;
both variants share evaluation memberships. Band choices `all`, `rgbnir` and
`rgb` load the same canonical payloads and assignments. Select an active
`split` before loading; retained overlapping validation/test candidates can have
`split="unused"` and `reason="evaluation_overlap"`. Coverage logs report the
geometric retained area, uncovered edges/gaps and nodata-window omissions.
Source assignments are independent of retained-window counts; all 369 sources
in this release have retained windows. See
[Task 032B](../tasks/032b_produce_and_publish_chip_release.md) for actual release
counts, bytes, coverage and the bounded restore/load validation scope.

Missing manifests or payloads usually mean the artifact root or relative layout
is wrong, or the copy stopped early. Check the selected root and copy exit status.
A failed copy or preparation attempt needs a fresh destination; existing releases
are preserved. No per-fold or per-band copies are needed.

## Tiny real-data walkthrough

Use tiny v2 below to practice splitting, chipping and loading. It contains
13 small CA/BC crop pairs across regions 002/003/012, including a 769-wide
crop that exercises partial-edge padding. V2 preserves all nine v1 pairs and
adds four 768-square crops for train/validation support. Inputs are about
83 MB; generated outputs are about 152 MB.

V2 is published at `kelp-box:kelpseg/data/examples/tiny_ca_bc/v2/`.
Fetch its 82,537,678 bytes once into a fresh local input directory, or use an
existing complete local v2. Set `data_root` to your chosen artifact root:

```bash
(
  set -e
  data_root="$HOME/kelpseg-tiny-v2-01"
  tiny="$data_root/data/examples/tiny_ca_bc/v2"
  test ! -e "$tiny"
  mkdir -p "$data_root/runs" "$data_root/data/examples/tiny_ca_bc"
  rclone copy kelp-box:kelpseg/data/examples/tiny_ca_bc/v2 "$tiny" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
)
```

The copy checks ordinary paths/sizes. After installation and this fetch, the
split/chip/load walkthrough runs offline. Use `uv run --offline --no-sync`
in place of `uv run` in the commands below; install the locked environment
before disconnecting. Choose fresh generated output names each time. No Box
access is needed during the walkthrough. The
[preserved v1 example](#preserved-v1-example) remains available separately.

## Compute training pixel statistics

Use the existing chip collection and source assignments. To reproduce the
approved kelp-positive with-BC normalization reference:

```bash
uv run kelpseg pixel-stats --chips /Volumes/x10pro/kelpseg/data/chips/ca_bc/v1 --assignments /Volumes/x10pro/kelpseg/data/splits/ca_bc/v1/assignments.csv --experiment baseline --variant augmented --kelp-only --clip-value 5000 --output /Volumes/x10pro/kelpseg/analyses/my-training-statistics-01.json
```

Change the paths for your machine and use a fresh output filename with an
existing parent directory. The default experiment/variant are `baseline` and
`augmented`; a declared LORO experiment such as `loro_001` uses its own training
assignment rows. The command logs selection, current file, progress counts and
payload bytes, then prints the resulting band means/sample standard deviations.

`--kelp-only` selects entire training chips with manifest `kelp_pixels > 0`.
Every nonnodata image pixel in those chips contributes, including background
and pixels whose labels are ignored. Omit the flag to include all active
training chips. Validation/test payloads and label arrays are never opened.
Native all-band-zero nodata is excluded before clipping; zero in just one band
is a valid observation. True-size edges are read directly without padding.
Overlapping training chips count repeated pixel exposures, as in the approved
reference.

`--clip-value` is an explicit optional raw-unit upper cap. Omit it for uncapped
statistics; the approved baseline requires **5000**. No scaling, augmentation or
standardization occurs. Float64 per-chip central moments and streaming merges
produce sample standard deviations (`ddof=1`). The declared band names/order
come from the collection, so other declared channel counts use the same code.

The one JSON report contains input/split/filter references, bands, cap,
`mean`, `std_sample`, valid pixel exposures, selected/excluded chip counts,
source count and elapsed time. `payload_bytes_read` sums the selected NPZ file
sizes for progress; it is not a measurement of physical disk reads. Existing
reports are refused before reading inputs. Empty selections, fewer than two
valid observations and zero-variance bands give an error; no partial report is
published. A failed calculation starts again with a fresh report name.

The same plain function works in Python:

```python
from kelpseg.prepare.channel_stats import compute_channel_stats

report = compute_channel_stats(
    "/data/chips/coast-v1", "/data/splits/assignments.csv",
    "/data/reports/fresh-statistics.json",
    experiment="baseline", variant="augmented",
    kelp_only=True, clip_value=5000,
)
print(report["band_names"], report["mean"], report["std_sample"])
```

The selected full-precision baseline values remain in the
[shared normalization contract](../tasks/033_baseline_training_and_portable_models.md#selected-training-normalization).

## Preview individual augmentations

This is an exploratory Python example, separate from the installed preparation
CLI. It uses the actual **Albumentations 2.0.8** classes and their native
parameters; there is no custom augmentation math or separate parameter schema.
The preview generators, display helpers, trial sweeps and HTML live together in
[`kelpseg/augmentation_debug/`](../src/kelpseg/augmentation_debug/). The approved
training factory and raw-data adapter stay outside that debug package.

Set `DATA_ROOT` and a fresh `OUTPUT` in
[`examples/augmentation_previews.py`](../examples/augmentation_previews.py), then run:

```bash
uv run python examples/augmentation_previews.py
```

Open its `index.html` in a browser. Choose one operation, then flip the 16
examples with the previous/next buttons or arrow keys while keeping the same
setting. The large original/trial views support clean RGB, clean NIR false
color, labels on either view and a kelp-boundary close-up, including in the
expanded comparison. Longer sweeps use a native-value dropdown. Coarse dropout
has separate size and hole-count selectors. The two labeled background controls
are last.

Read/edit the literal constructors in
[`trials.py`](../src/kelpseg/augmentation_debug/trials.py) to change trial
values. Equal range endpoints fix a library strength; the seed fixes its other
random choices. Library validation owns the parameter rules. The viewer shows
exact constructor arguments and realized parameters, plus the library version.

| Preview | Actual implementation and parameter |
|---|---|
| Rotations/reflections | `D4`, fixed `group_element` for the eight square symmetries |
| Additive brightness | `RandomBrightnessContrast`, `brightness_limit`, contrast zero |
| Gain / contrast | `RandomBrightnessContrast`, `contrast_limit`, brightness zero; stock contrast is multiplication by `1 + contrast_limit` |
| Blur | `GaussianBlur`, fixed `sigma_limit`, stock kernel; `NoOp` identity because sigma zero is invalid in this release |
| Noise | `GaussNoise`, fixed `std_range`, independent pixel/channel noise |
| Sharpening | `Sharpen(method="gaussian")`, native `alpha`, kernel size 5 and sigma 1 |
| Spatial holes | `CoarseDropout`, separate count/size sweeps, image fill 0 and mask fill -100 |
| Independent channel shifts | `AdditiveNoise`, uniform `noise_params.ranges` and `spatial_mode="constant"` |
| Red or NIR dropout | `ChannelDropout`, full removal with fill 0; fixed diagnostic channel index |

The old mean-centered contrast, custom masked blur/sharpness, partial channel
fades and mean-fill previews were removed. Gain and stock contrast share one
sweep because they duplicate each other. The user's
[selected strength limits](../tasks/033_baseline_training_and_portable_models.md#limits-selected-after-isolated-review)
and D4 plus `SomeOf(n=2)` composition are recorded separately from the wider
trial sweeps. The user approved the combined preview and its final recipe.

The wider exploratory sweeps retain earlier values and reach the library's
default brightness limits **-0.2 to 0.2**, blur sigma **3 px**, noise standard
deviation **0.44**, and uniform channel-shift amplitude **0.1**. Noise and
brightness/shift values use the library's unit float domain. These endpoints
can overwhelm this dark imagery; they are comparisons, not selected maxima.
Coarse dropout compares **1/2/4/8/16 holes at side 0.25**, and **sides
0.05/0.1/0.2/0.25/0.35/0.5 at four holes**. Side lengths are fractions of image
height/width; holes may overlap. Each trial is one stock transform.

[`augmentations.py`](../src/kelpseg/augmentations.py) contains the small data
adapter only. It converts native uint16 imagery to **float32 / 65535**, calls
the real class, restores raw units and zero invalid fill. It applies no model
pre-cap. Stock pixel functions clip to their native **[0,1]** domain where
implemented, including a raw-zero lower bound. Stock blur sees zero nodata and
padding, so neighboring valid pixels can darken; there is no hidden
validity-normalized replacement kernel. Labels and validity travel as mask
targets; -100 under a spatial hole makes it invalid. Validity is detected before
augmentation and never inferred again from augmented zero values.

After augmentation, model preprocessing still uses the approved **5000 upper
cap** and [exact fixed normalization](../tasks/033_baseline_training_and_portable_models.md#selected-training-normalization).
The viewer alone clips colors to **raw 0–2000**, consistently across examples.
The input scale, model cap and display ceiling have distinct purposes.

The same 14 kelp-rich training windows and two background controls are selected
from the canonical manifests before any arrays are opened. Positive examples
have at least 10% labeled kelp in their true footprint; this is showcase
sampling, not evaluation sampling or a new training eligibility rule. No
validation/test payload is opened. Native bands are augmented before choosing
RGB/NIR views, so their random draws stay consistent.

Outputs include `selected_windows.csv`, library/version/domain metadata in
`gallery.json`, per-window `parameters.json`, native-resolution view PNGs and
optional contact sheets. Full-image noise fields are represented by shape and
seed rather than copied into JSON. Source files remain unchanged. Existing
outputs are refused before payload reads; choose a new directory for each run.

## Preview the combined augmentation pipeline

Set `DATA_ROOT` and a fresh `OUTPUT` in
[`examples/augmentation_pipeline_preview.py`](../examples/augmentation_pipeline_preview.py),
then run:

```bash
uv run python examples/augmentation_pipeline_preview.py
```

Open its `index.html`. Flip the same 16 training examples or use **Next draw**
to inspect eight seeded draws per example. **Inspect affine** compares D4 alone
with the same D4 plus the sampled affine step. **Inspect full pipeline** compares
the geometry-only reference with the full result, so the remaining augmentation
can be assessed separately. Switch the left reference to **Source original**
when useful. The operation cards report affine applied/skipped, actual scale
and pixel shifts, alongside D4 and the two pool operations.

Clean RGB/NIR, label overlays, paired kelp close-ups and enlarged comparison
remain available. Close-ups follow the same source footprint through D4 and
affine. Two labeled background controls are diagnostics; training eligibility
is unchanged. The affine review output is
`/Volumes/x10pro/kelpseg/analyses/task033d_affine_pipeline_previews_v1/index.html`;
choose a new output name before generating another gallery.

The readable recipe is
[`build_training_augmentation`](../src/kelpseg/augmentation_pipeline.py): stock
`D4(p=1)`, then `Affine(p=0.5)`, then `SomeOf(n=2, replace=False, p=1)`,
with every pool child at `p=1`. Affine stays outside the SomeOf pool. It uses
0.95–1.05× shared-axis zoom, independent ±16-pixel x/y shifts, no extra rotation
or shear, and the original output size. Imagery is bilinear; labels/validity are
nearest-neighbor. New borders use zero image fill and ignored mask fill.
Children are selected uniformly and execute in listed order: brightness, gain,
blur, noise, Sharpen, coarse dropout, channel shifts, channel dropout. It uses
the [approved native ranges](../tasks/033_baseline_training_and_portable_models.md#limits-selected-after-isolated-review).
The final [native Albumentations recipe](../configs/augment/baseline.json) is a
saved snapshot of that factory, verified by a focused parity check. It can be
loaded directly with `albumentations.from_dict`; there is no custom parser.
Channel dropout removes exactly one of the eight physical input bands in this
preview. The RGB/RGB+NIR training loader restricts eligibility to that
model's selected input bands. D4 includes the identity square symmetry.

`pipeline.json` saves the stock serialized recipe. `gallery.json`, selected
windows and per-example parameter records save the input/domain/normalization
metadata, draw seeds, actual operations and support counts. Kernel/noise-map
records reflect what the stock classes expose: the blur sigma range and actual
kernel, and the noise std range plus explicitly empirical realized field std.
Full noise arrays are not copied into JSON. The cap remains 5000 after the
entire pipeline, using exact fixed normalization; display remains 0–2000.

The preview constructs a seeded pipeline for each reproducible draw. The
training loader reuses one seeded Albumentations pipeline that includes
normalization and tensor conversion. Its random state advances across samples;
explicit per-draw seeds are for replayable previews. This gallery runs no model and opens no held-out payloads.
Existing outputs are refused; failed generation needs a fresh output.

## Tiny v2: split, chip and load locally

Set `data_root` to the same artifact root used for the fetch, and update your
local `data_root` and `runs_root` path settings to match. Pick one `example_name` for this attempt; change
it for each repeat. Both output folders
must be fresh. These ordinary commands stop at the first failure:

```bash
(
  set -e
  data_root="$HOME/kelpseg-tiny-v2-01"
  example_name='my-tiny-v2-01'  # Change this for each new attempt.
  tiny="$data_root/data/examples/tiny_ca_bc/v2"
  splits="$data_root/examples/runs/${example_name}-splits"
  chips="$data_root/examples/runs/${example_name}-chips"
  mkdir -p "$data_root/examples/runs"
  uv run kelpseg split --sources "$tiny/metadata.csv" --recipe configs/split/ca_bc_v1.toml --output "$splits" --dry-run
  uv run kelpseg split --sources "$tiny/metadata.csv" --recipe configs/split/ca_bc_v1.toml --output "$splits"
  uv run kelpseg chip --images "$tiny/images" --labels "$tiny/labels" --metadata "$splits/chip_metadata.csv" --recipe configs/chip/planet8.toml --output "$chips" --dry-run
  uv run kelpseg chip --images "$tiny/images" --labels "$tiny/labels" --metadata "$splits/chip_metadata.csv" --recipe configs/chip/planet8.toml --output "$chips"
)
```

Expected **source** counts are 2 train / 2 validation / 6 test / 3 unused for
baseline `base`, and 5 / 2 / 6 / 0 for `augmented`. Only `loro_002` and
`loro_003` are generated for this subset. The chipper retains all 54 candidate
windows, including 31 without kelp. That is canonical payload retention;
`select_windows` subsequently excludes overlapping validation/test candidates.
Source counts, retained payload counts and active selection counts are separate.
After selection, baseline `base` has **8 train / 2 validation / 7 test / 37 unused**
windows; primary baseline `augmented` has **20 / 2 / 7 / 25**. Training overlap
is unchanged. The validation/test input footprint is 4,719,360 geometric pixels;
selected windows cover 2,228,736, leaving 2,490,624 uncovered. This small-crop
edge loss is explicit and does not estimate full-release coverage. Retained
window area can include nodata; it is not scoreable-label area. Overlapping
foreground counts are not unique area.

Select existing windows without opening arrays or copying payloads. Training
keeps all retained overlapping chips. Validation/test reserve a deterministic
disjoint subset in crop-key then numeric row/column order, using original TIFF
coordinates so crops of the same source cannot repeat pixels. Retained overlap
exclusions become `unused` with reason `evaluation_overlap`; their payloads stay
canonical. Nodata omissions keep their reason and empty payload, with no
replacement by overlapping alternatives.

Progress logs show manifest joins and geometric coverage: input crop-union
footprint, nominal disjoint-grid area, retained selected area, uncovered edges/
gaps and nodata-omitted window area. Reusing existing chips can leave edge strips
(and with some strides interior gaps). Geometry excludes padding but is not
valid-label area or model performance. All candidate rows retain `split` and
`reason`; use only the requested active split for model input. Paths resolve
from the explicit chip root; identity is `(chip_root, source_key, row, col)`.
Use the same `example_name` as the shell block:

```python
import json
import logging
from collections import Counter
from kelpseg.paths import load_paths
from kelpseg.prepare.splits import select_windows
from kelpseg.chips import load_chip

logging.basicConfig(level=logging.INFO)  # Show library progress in a notebook.
root = load_paths("paths.local.toml").data_root
example_name = "my-tiny-v2-01"  # Match the shell block above.
split_root = root / "examples/runs" / f"{example_name}-splits"
chip_root = root / "examples/runs" / f"{example_name}-chips"
recipe = json.loads((chip_root / "recipe.json").read_text())
for experiment in ("baseline", "loro_002", "loro_003"):
    for variant in ("base", "augmented"):
        rows = select_windows(chip_root, split_root / "assignments.csv",
                              experiment=experiment, variant=variant)
        print(experiment, variant, Counter(row["split"] for row in rows))
        validation = [row for row in rows if row["split"] == "val"]
        # Later training reads only this active list for chip validation.

# Inspect a canonical partial edge, which may be unused in this experiment.
# True-size edge chips get bottom/right padding only when loaded.
edge = next(row for row in rows if row["payload"] and int(row["width"]) == 257)
for selection in ("all", "rgbnir", "rgb"):
    chip = load_chip(edge["payload"], recipe["source_band_names"], selection,
                     recipe["chip_size"])
    print(selection, chip["image"].shape, chip["padding"])
    assert chip["padding"] == (0, 0, 0, 255)
    h, w = chip["true_height"], chip["true_width"]
    true_image = chip["image"][:h, :w]  # Remove padding before source placement.
    assert (chip["image"][:, w:] == 0).all()
    assert (chip["label"][:, w:] == -100).all()
```

Expected shapes are `(512, 512, 8)`, `(512, 512, 4)`, `(512, 512, 3)` from the
same payload. For model input, filter by the active `split`; a retained payload
may still be excluded from that experiment. During training, validation loss and
aggregate chip confusion counts use the disjoint list; test stays held out until
model selection ends. Post-training tiled prediction/source scoring can combine
overlapping probabilities separately. The full published release uses the
[restore recipe above](#restore-and-use-the-full-cabc-chip-release); model training is available below;
post-training evaluation arrives later.

## Preserved v1 example

The earlier nine-pair example proves chipping/loading and remains on Box. It
has no CA train/validation sources under the approved split, so use v2 for
split practice. Fetch v1 once into a fresh directory, or skip the copy if that
local input already exists:

```bash
(
  set -e
  data_root='/Volumes/x10pro/kelpseg'
  tiny="$data_root/data/examples/tiny_ca_bc/v1"
  test ! -e "$tiny"
  mkdir -p "$(dirname "$tiny")"
  rclone copy kelp-box:kelpseg/data/examples/tiny_ca_bc/v1 "$tiny" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
)
```

The copy checks ordinary paths/sizes. To run offline, use the
[chipping recipe](#chip-cleaned-imagery) with v1's `images`, `labels` and
`metadata.csv`, choosing a fresh output. Expect 9 sources, 38 retained windows
and about 102 MB of output. The same partial-edge loading example applies:
select a retained `windows.csv` row with width 257 and resolve its payload from
the v1 chip root. Original v1 paths and detailed results remain in
[Task 031](../tasks/031_chipping_bands_and_tiny_walkthrough.md#outcome-2026-10-27).

## Model and training inputs (Python)

The installed package now supplies manifest-selected tensors, one SegFormer B3
model, the binary objective, and pooled confusion helpers. The public `train`
command below connects these through Lightning. Use this notebook/Python example to
inspect the full published baseline inputs without reading test payloads:

```python
import logging
from kelpseg.paths import load_paths
from kelpseg.training.data import build_training_inputs

logging.basicConfig(level=logging.INFO)
root = load_paths("paths.local.toml").data_root
inputs = build_training_inputs(
    root / "data/chips/ca_bc/v1",
    root / "data/splits/ca_bc/v1/assignments.csv",
    selection="rgbnir",  # "all" = native eight; "rgb" = red/green/blue
    experiment="baseline",
    variant="augmented",  # primary with-BC baseline; "base" excludes BC
    seed=33,
)
print(inputs["counts"])
print(inputs["train"].band_names)  # red, green, blue, nir
sample = inputs["train"][0]
print(sample["image"].shape, sample["target"].shape, sample["metadata"])
```

For the full with-BC release, expect 18,311 candidate training windows, 8,518
eligible and 9,793 zero-kelp exclusions; validation retains 933 windows and
1,262 test identities remain metadata only. `excluded_training_rows` preserves
excluded identities. `val` uses representative disjoint windows, including
backgrounds. Neither input construction nor train/validation loading opens test
payloads; `test_rows` is deliberately a list of metadata, not a dataset.
Missing labels or training kelp counts raise errors naming the affected payload.

Each sample returns float32 `image` (channels/height/width), int64 `target`
(height/width), boolean `valid_mask`, and source/window `metadata`. Native-band
validity is detected before selecting channels. Training applies the approved
D4 + light Affine + SomeOf(2) factory to selected channels inside one
Albumentations `Compose`. Affine has a separate 50% chance, 0.95–1.05× zoom
and independent ±16-pixel shifts while keeping the 512×512 canvas.
The pipeline includes unit-scale conversion, restoration to raw units with the
shared 5000 cap, stock `Normalize` using the shared band-named constants, and
`ToTensorV2`. It restores zero invalid fill after normalization. Channel dropout
therefore always removes a model input. Augmented zero values never redefine nodata. One seeded pipeline advances
across calls; these bounded checks use ordinary single-process loading.

Targets use 0/1/-100. Nodata, padding, and coarse-dropout holes are ignored;
valid imagery with ignored labels stays image-valid but unscored. Metadata keeps
original source placement and true extents. D4 can move padding in training;
use the transformed validity mask there. Validation applies no augmentation and
keeps bottom/right padding, removable using `true_height`/`true_width`.

The model and objective are ordinary functions:

```python
from kelpseg.models import build_model
from kelpseg.training.loss import segmentation_loss
from kelpseg.training.metrics import build_metrics

# Construct one model at a time. None avoids any pretrained-weight download.
model = build_model(len(inputs["train"].band_names), encoder_weights=None)
metrics = build_metrics()  # Native TorchMetrics MetricCollection.
# Given B1HW logits and BHW targets from later validation batches:
# loss = segmentation_loss(logits, targets)
# metrics.update((logits[:, 0] >= 0).long(), targets)  # Each batch.
# report = metrics.compute()  # Once after the entire validation scope.
# metrics.reset()  # Before the next scope.
```

`build_model` always uses SegFormer B3 / `mit_b3` and one full-resolution logit.
Its default `encoder_weights="imagenet"` is the initialization for new baselines
and may download weights on first use. SMP retains RGB weights for three inputs;
for four/eight it repeats the RGB input kernels cyclically and multiplies by
3/channel-count. This positional initialization does not assign pretrained
spectral meaning to the native eight-band order.

The objective is 0.7 BCE with 0.1 label smoothing plus 0.3 batch-pooled Lovasz
hinge on hard labels. Both ignore -100; all-ignored support returns a
differentiable zero. TorchMetrics accumulates the confusion matrix, foreground
IoU, precision, recall, F1 and accuracy over updates. Explicit integer predictions
use probability >= 0.5 and avoid automatic logits/probability guessing. Each
metric ignores -100. Results are tensors; the confusion matrix is
`[[tn, fp], [fn, tp]]`. Undefined ratios use TorchMetrics' zero convention;
inspect `report["confusion_matrix"].sum()` for scored support, and never treat
zero-support output as evidence of model performance. These helpers provide no
epoch loop, optimizer policy or checkpoint selection.

## Train and validate

Preview each run before fitting. The preview reads manifests only and does not
create an output folder or open image arrays:

```bash
uv run kelpseg train --recipe configs/train/planet8.toml --dry-run
```

The four explicit recipes reuse the same native collection and assignments:

| Recipe | Ordered inputs |
|---|---|
| `planet8.toml` | coastal_blue, blue, green_i, green, yellow, red, rededge, nir |
| `planet4.toml` | red, green, blue, nir |
| `planet3.toml` | nir, red, green |
| `planet_RGB.toml` | red, green, blue |

The existing Python `selection="rgb"` still means red/green/blue. Set
`variant = "base"` in a copied recipe for the without-BC comparison; keep epochs
and optimizer policy matched. Production recipes default to `variant = "augmented"`.

`paths_file = "../../paths.local.toml"` selects your machine settings, relative
to the recipe's directory. Change it if you move the recipe, or use an absolute
path. Machine roots remain in that separate TOML so they need not be repeated
in every training recipe. Relative `chips` and `assignments` resolve against
its `data_root`. Each recipe has a `name` used as the run-ID prefix:

```toml
name = "planet3"
experiment = "baseline"
variant = "augmented"
paths_file = "../../paths.local.toml"
```

Each fit receives `<name>-<UTC timestamp>` automatically, printed with the
resolved output location. Rename a copied recipe in TOML to distinguish a
comparison; the filename itself does not determine the run name. `experiment`
selects the assignment scope and is recorded separately from the descriptive
name. This training stage supports `baseline`; LORO needs its later fold-specific
normalization work. Dry-run IDs are previews, not reservations;
a later fit gets its own ID. Unknown settings and empty validation produce
errors, and existing output folders are never overwritten. No resume command exists yet.

For a bounded local smoke, copy `configs/train/tiny_cpu.toml` and set its
`chips` and `assignments` to your tiny walkthrough outputs if desired. This
recipe uses NIR/red/green, float32 CPU, no weight download, two epochs, two
training microbatches and one validation batch per epoch. It still uses the
512 canvas and approved preprocessing; limited validation is smoke evidence
only. Preview and run it:

```bash
uv run kelpseg train --recipe configs/train/tiny_cpu.toml --dry-run
uv run kelpseg train --recipe configs/train/tiny_cpu.toml
```

Production recipes target CUDA bf16 mixed precision with float32 loss, 70
epochs, seed 42, microbatch 3 and accumulation 8. They use ImageNet-initialized
SegFormer B3, AdamW (3e-4, betas .9/.95, decay .01 except biases/normalization),
five warmup epochs, cosine decay to 3e-5 and norm clipping .8. Hardware sizing
and CUDA verification remain GPU-host work; do not run production on the Mac.
Workers, pinned memory and persistent workers are explicit machine settings.
The approved D4 → Affine(p=.5) → SomeOf(2), 5000 cap and exact band constants
remain fixed. Training uses positive chips; validation includes backgrounds;
test payloads are never loaded, including after fitting.

Lightning steps the scheduler once per optimizer update. Its initial LR is
zero; the scheduled LR reaches the peak after the warmup updates and the floor
after the final update. Thus the last applied update uses the preceding LR.
The final incomplete accumulation group still performs an optimizer update;
Lightning divides each microbatch loss by the configured accumulation factor,
including that final group. The preview reports actual update budget and
partial groups; effective batch 24 describes complete groups only.

Training and validation each log IoU, precision, recall, F1 and accuracy through
native TorchMetrics collections. Lightning computes pooled epoch metrics and
resets their state; these are not averages of per-batch IoUs. Training metrics
measure the augmented training pass with changing current weights, so they are
diagnostics, not directly comparable to deterministic validation with EMA.
`train_loss_step` records each logged training batch loss; `train_loss` and
`val_loss` are native TorchMetrics valid-pixel-weighted epoch means of batch
BCE/Lovasz losses. Lovasz is pooled within each batch, not recalculated over the
whole epoch. The scalar logger receives the collection directly; confusion
matrices remain available through the Python metric helper, without hand-split
TN/FP/FN/TP log columns. Validation uses fixed threshold .5.
Aggregate foreground IoU selects best weights, preserving the earliest tie.
Zero scored validation support fails rather than selecting a meaningless model.
EMA (.999) first copies weights after optimizer update 101; earlier validation
uses current weights. Afterward validation and selected weights use EMA.

Each run writes resolved settings and a run record under `<runs_root>/<run_id>`,
CSV metrics under `metrics/`, and distinct best/last Lightning checkpoints under
`checkpoints/`. The checkpoint `state_dict` contains validation weights;
`current_model_state` retains ordinary weights separately from averaging state.
These are local training checkpoints, not yet portable prediction bundles or
verified exact-resume artifacts. Keep them outside Git. Local records work
offline. `wandb = true` optionally adds native W&B logging to
`kdorman90-ucla/kelpseg` (install `wandb` in a runtime-only environment first).

## Later workflows and outputs

Portable prediction bundles, exact resume, prediction, scoring, LORO model
comparisons and adding a region remain later tasks. The reusable walkthrough
above covers chipping, loading and source splitting. Automated CPU fixtures
need no Box/W&B login, GPU or model-weight download.

See [data and artifacts](data_artifacts.md) for storage/backup rules and
[experiments](experiments.md) for model, checkpoint, and run identity rules.
