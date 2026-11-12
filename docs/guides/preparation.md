# Preparation reference

For the scientific rationale and evaluation scopes, see [methods](../methods.md).

Use the [tiny walkthrough](../quickstart.md) first. These sections provide detailed options and reusable recipes. Run steps sequentially and stop if a command fails. Use fresh output names.

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

`data_root` is your artifact root. Choose a mounted volume with sufficient space for the selected release.
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

For `organize` and `check-paths`, the required `--paths` option chooses exactly one file.
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
`aliases.csv`, `assets.csv` and `catalog_manifest.json` remain available. On another machine, copy that retained catalog into the same project-relative
location before running the raw restore example below. The raw ZIP download
does not include the catalog. Its preserved local copy is recorded in
[Task 032C](../../tasks/032c_archive_legacy_and_evict_local_data.md#outcome-2026-10-28);
if it is unavailable, restore the published organized release instead. Use
those declarations directly; normal organization does not read old merge CSVs
or import a historical bootstrap. That one-time converter has been retired.
Historical catalog/recovery evidence is linked from [history](../history.md).
Training uses canonical chips; full-TIFF work uses the cleaned release. To obtain organized v1, use the
[Box recovery recipe](../reference/ca_bc_release.md#restore-the-organized-cabc-release).

To rebuild organization instead, first restore the three original ZIPs into the
paths declared by the existing catalog. This is a download recipe, not a step
needed for training. Choose the artifact root in your local settings:

```bash
(
  set -e
  data_root='/path/to/artifact-root'
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
from kelpseg.paths import check_paths, load_paths
from kelpseg.prepare.organize_inputs import load_organize_recipe
from kelpseg.prepare.organize import (
    build_organization_plan, organize_dataset, verify_organized_release,
)

paths = check_paths(load_paths("paths.local.toml"))
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
nodata 3, matching grids, and image all-band zero implying label 3. Declare the band order for each input collection; preserve known region/date identities.

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
`/path/to/artifact-root/data/2_organized/ca_bc/v1`; its authenticated release
identity and fetch/check recipe are in [Box recovery](../reference/ca_bc_release.md#restore-the-organized-cabc-release).
Task 030B completed the separate full cleaned release; see the [release reference](../reference/ca_bc_release.md).

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
the retained correctness coverage. See [Task 029B](../../tasks/029b_clean_organized_sources.md)
for the migration map and bounded verification evidence.

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

The recipe declares the current CA/BC band order. Contradictory explicit
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
uv run kelpseg split --cleaned /path/to/artifact-root/data/3_cleaned/ca_bc/v1 --release-id v1 --recipe configs/split/ca_bc_v1.toml --output /path/to/artifact-root/examples/runs/my-source-splits-v1 --dry-run
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

## Compute training pixel statistics

Use the existing chip collection and source assignments. To reproduce the
approved kelp-positive with-BC normalization reference:

```bash
uv run kelpseg pixel-stats --chips /path/to/artifact-root/data/chips/ca_bc/v1 --assignments /path/to/artifact-root/data/splits/ca_bc/v1/assignments.csv --experiment baseline --variant augmented --kelp-only --clip-value 5000 --output /path/to/artifact-root/analyses/my-training-statistics-01.json
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
[shared normalization contract](../../tasks/033_baseline_training_and_portable_models.md#selected-training-normalization).

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
[release restore recipe](../reference/ca_bc_release.md#restore-and-use-the-full-cabc-chip-release);
model training is covered in the [training guide](training.md);
post-training evaluation is implemented in the [prediction/reporting guide](prediction_reporting.md).
