# CA/BC release and recovery reference

This reference preserves release-specific locations, verification values and
restoration instructions. For ordinary new backups, use [Box operations](../box_backup.md).

## Raw sources, legacy reference and audit

The verified project root is `kelp-box:kelpseg`, [Box folder 431635691068](https://app.box.com/folder/431635691068), under the UCLA account `kdorman90@ucla.edu`. Task 027 backed up the current delivery as an ordinary raw source bundle:

- `data/1_raw/ca_bc_sources_v1/`: the three unchanged source ZIPs.
- `references/legacy_ps8b_v1/`: complete legacy reference package.
- `audits/task026_originals_v1/`: complete original-data audit package.
- `transfers/task027_raw_reference_audit_v1/`: round-trip fixture, receipts, and completion marker.

Task 030A also verified the organized release at
`data/2_organized/ca_bc/v1/`, with its separate evidence at
`transfers/task030a_organized_ca_bc_v1/`; see the recovery recipe below.

Local raw ZIPs and organized v1 payloads were evicted in
[Task 032C](../../tasks/032c_archive_legacy_and_evict_local_data.md); their Box copies
remain unchanged. Current cleaned imagery/chips stay local. The small historical
archive is local at `history/legacy_pre_rebuild_v1/`; it was not uploaded by that
cleanup. Normal organization uses the retained `preparation_inputs/ca_bc/v1/`
catalog, so restoring raw ZIPs does not require the retired catalog bootstrap.
Use the [raw restore recipe](../guides/preparation.md#organize-raw-sources) to populate
that catalog's declared `zip_archive/` paths.

To restore into a new local project-shaped directory, choose a fresh `DEST` and run:

```bash
(
set -e
DEST='/path/to/fresh/kelpseg-restore'
test ! -e "$DEST"
rclone copy kelp-box:kelpseg/data/1_raw/ca_bc_sources_v1 "$DEST/data/1_raw/ca_bc_sources_v1"
rclone copy kelp-box:kelpseg/references/legacy_ps8b_v1 "$DEST/references/legacy_ps8b_v1"
rclone copy kelp-box:kelpseg/audits/task026_originals_v1 "$DEST/audits/task026_originals_v1"
rclone copy kelp-box:kelpseg/transfers/task027_raw_reference_audit_v1/receipts "$DEST/receipts"
(cd "$DEST" && shasum -a 256 -c receipts/payload.sha256)

# The checksum check reads every restored ZIP. Verify the two packages too.
cd /tmp
uv run --no-sync --project /path/to/kelpseg python -I "$DEST/references/legacy_ps8b_v1/verify_package.py"
uv run --no-sync --project /path/to/kelpseg python -I "$DEST/audits/task026_originals_v1/verify_package.py"
)
```

For new work, follow the [current artifact policy](../data_artifacts.md#box-project-organization-and-upload-verification): ordinary copies, path/count/size checks and bounded restore/load examples, with no new hashing or receipt machinery. Avoid overwriting versioned releases. The recipes above and below retain historical checksum workflows for the older releases; they are not new-task requirements. Task 027's evidence remains in its [outcome](../../tasks/027_verify_box_and_back_up_raw_reference_audit.md#outcome-2026-10-27).

## Restore the organized CA/BC release

The exact unsplit organized release is at
`kelp-box:kelpseg/data/2_organized/ca_bc/v1`, with 369 pairs, 418 companions and
1,163 total files (28,568,499,959 bytes). Its root manifest SHA-256 is
`435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8`.
QA/transfer evidence lives separately at
`kelp-box:kelpseg/transfers/task030a_organized_ca_bc_v1`. Its authenticated
`completion.json` SHA-256 is
`471cfb2902287ee10e9a92b2a54ae46c568a029decf92eb2f5e843bab63b39ae`;
the marker references evidence-catalog SHA-256
`c73ab72e6fac3b619ac4e82100108c739e0c3678717d33edb9f6727e519b9cf1`.
The [Box release folder](https://app.box.com/folder/431680482261) is an exact
copy; all 1,163 paths, sizes and native SHA-1 values matched.

From this repository, choose a fresh destination, fetch all release files,
authenticate the manifest, then run the installed read-only verifier. This block
stops on a failed command:

```bash
(
  set -e
  DEST='/path/to/fresh/organized-ca-bc-v1'
  test ! -e "$DEST"
  rclone copy kelp-box:kelpseg/data/2_organized/ca_bc/v1 "$DEST" --immutable --checksum --transfers 1 --checkers 2
  printf '%s  %s\n' 435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8 "$DEST/manifest.json" | shasum -a 256 -c -
  uv run --no-sync python -c 'import sys; from kelpseg.prepare.organize import verify_organized_release; print(verify_organized_release(sys.argv[1]))' "$DEST"
)
```

The verifier reads every restored file and checks the exact inventory, SHA-256
and logical-input identity. It does not repair inputs. Keep receipts outside
`DEST`; an extra file there fails the inventory check. For a missing file or
checksum mismatch, stop, retain the evidence and fetch a new separate copy;
never modify the closed release to make verification pass. The 90,741,406-byte
payload sample tested during publication was a bounded restoration with all
controls, not a full release restore.

Source QA decoded every primary image and native label grid. The preserved
release still has 34 image/label grid mismatches, 355 label nodata declarations
requiring correction, and 326 paired nodata findings. Task 030B corrected them
in the separate cleaned release. Valid class zero remains background; source
checks observed classes 0–3 within the allowed 0–4 vocabulary.

## Cleaned CA/BC v1

The immutable unsplit cleaned release is
`kelp-box:kelpseg/data/3_cleaned/ca_bc/v1`: 369 pairs across 12 regions,
747 files / 18,662,320,805 bytes. All paths, sizes and Box SHA-1 values matched
the finalized local catalog; no checksum fallback was needed. Full local QA
checked 2,905,415,276 image pixels and the same number of aligned label pixels,
with no issues or skipped required checks.

Trusted root `manifest.json` SHA-256:
`43815a8a7e412d0f0ed021c813c6c3b4f3a9a532a4fcbb3f9624a91bbdd5ba61`.
Organized parent root SHA-256:
`435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8`.
Transfer evidence: `kelp-box:kelpseg/transfers/task030b_cleaned_ca_bc_v1`.
Its `completion.json` SHA-256 is
`1b044c5b851eb35ed379c4e52a1c9ba4a7df0077da3c3d261bd539d65e78730d`;
the marker authenticates `evidence_catalog.json` SHA-256
`d53bfe8113d82bbb21ad4a3327d6b1346606e6d300a1078d2221b5c971f26b4a`.
The final marker was uploaded last and read back.

From the repository environment, choose an absent destination. This sequence
stops on failure, authenticates the root, then checks every restored file:

```bash
(
  set -e
  DEST='/path/to/fresh/cleaned-ca-bc-v1'
  test ! -e "$DEST"
  rclone copy kelp-box:kelpseg/data/3_cleaned/ca_bc/v1 "$DEST" --immutable --checksum --transfers 1 --checkers 2
  printf '%s  %s\n' 43815a8a7e412d0f0ed021c813c6c3b4f3a9a532a4fcbb3f9624a91bbdd5ba61 "$DEST/manifest.json" | shasum -a 256 -c -
  uv run --frozen --no-sync python -c 'import sys; from pathlib import Path; from kelpseg.prepare.clean import verify_cleaned_release; print(verify_cleaned_release(Path(sys.argv[1])))' "$DEST"
)
```

Keep receipts outside `DEST`. The verifier authenticates file bytes against the
already trusted root; it does not establish root authenticity itself or resume
cleaning. Extra/missing files or disagreeing hashes fail. Retain failure evidence
and fetch a fresh separate copy rather than repairing a closed release in place.
A full pixel scan is also available with the implemented cleaned-profile `check`
recipe; the published `check.json` already records the production full scan.

The restored TIFFs use their own grids and paths. Operational absolute paths in
`sources.json` are history, not loading dependencies. `parent/` snapshots retain
all 369 identities, 3,919 aliases and 418 inactive companion associations; original
companion payloads remain in the organized parent. No stale masks/sidecars were
copied beside rewritten TIFFs. Labels preserve categories 0–4 with ignore 3;
image nodata is 0, and outside annotation is image 0/label 3. Existing label 3 may
remain over valid imagery. This release remains unsplit.

Publication tested a bounded restore of three complete pairs: ordinary CA,
extra-archive/declared-65535, and BC alignment/outside coverage. It restored
108,284,380 payload bytes (within 128 MiB) plus all nine controls (7,149,393 bytes),
authenticated every selected SHA-256, and full-checked 23,444,214 image and label
pixels without original source paths. This was a sample, not a full restored
release. Exact selection and results are in `restore_selection.json` and
`restore_result.json`; [Task 030B's outcome](../../tasks/030b_build_and_publish_cleaned.md#outcome-2026-10-27)
owns detailed evidence.

## Chip, split and collection CA/BC v1

The matching local/Box paths below are relative to the artifact/project root:

| Artifact | Path | Files | Bytes |
|---|---|---:|---:|
| Native-band chips and controls | `data/chips/ca_bc/v1/` | 26,577 | 65,565,628,953 |
| Both baseline variants and ten LORO folds | `data/splits/ca_bc/v1/` | 5 | 935,947 |
| Portable declaration | `data/collections/ca_bc/v1/collection.json` | 1 | 539 |
| Tiny v2 inputs | `data/examples/tiny_ca_bc/v2/` | 28 | 82,537,678 |

The [chip restore recipe](#restore-and-use-the-full-cabc-chip-release)
fetches chips, assignments and declaration into a fresh root with explicit
reader paths. The declaration references the separate cleaned release too;
cleaned TIFFs are needed only for workflows that use those sources. Preserve the
project-relative layout so its paths remain portable. Use `augmented` for the
primary with-BC baseline, `base` for the comparison, and `loro_001`–`loro_010`
for the ten held-out-region folds. One canonical chip collection supplies every
fold and spectral choice; select active windows through the manifests.

Copies use `--immutable --size-only --ignore-checksum`. Complete local/Box
relative paths, file counts and sizes were compared. Bounded restoration loads
and compares actual selected 8/4/3-band arrays; this is not checksum verification
or a full restored-release payload audit. See
[Task 032B](../../tasks/032b_produce_and_publish_chip_release.md#outcome-2026-10-28)
for the exact restore scope, geometry and evidence. The separate
[tiny v2 fetch/offline walkthrough](../quickstart.md)
provides the small reproducible operating example.


## Historical cleaned-release production

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

Use [cleaned recovery](#cleaned-cabc-v1) for the trusted manifest hash,
fresh-directory fetch and byte verification. A restored release loads from its
own `images/` and `labels/`; historical absolute source paths in provenance are
not required. Continue with [chipping](../guides/preparation.md#chip-cleaned-imagery) and the
[tiny walkthrough](../quickstart.md).


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
[Task 032B](../../tasks/032b_produce_and_publish_chip_release.md) for actual release
counts, bytes, coverage and the bounded restore/load validation scope.

Missing manifests or payloads usually mean the artifact root or relative layout
is wrong, or the copy stopped early. Check the selected root and copy exit status.
A failed copy or preparation attempt needs a fresh destination; existing releases
are preserved. No per-fold or per-band copies are needed.


## Historical local cleanup and retained controls

Keep current cleaned imagery, canonical chips, split/collection controls and tiny
inputs under `data/`, plus analyses, references, audits, preparation inputs,
backup evidence and small historical experiment results. Local raw ZIPs and
organized v1 payloads were evicted after verified Box publication; restore them
from Box only when needed for reconstruction. Box releases remain immutable.

Small historical controls, the 31 pre-repair label snapshots and retired
bootstrap source/tests are at
`/Volumes/x10pro/kelpseg/history/legacy_pre_rebuild_v1/`, preserving their former
relative paths. The finished `preparation_inputs/ca_bc/v1/` catalog stays active.
The installed preparation/loading workflows do not require the obsolete
merge/chip directory layout. Bulk old datasets,
ZIP/TAR copies, local smoke checkpoints and generated smoke/restore/example runs
were removed. The [Task 032C record](../../tasks/032c_archive_legacy_and_evict_local_data.md)
contains the pre-execution deletion plan, archive scope and measured results.
The archive is local only; this cleanup performed no Box operation.


## Chip coverage reference

The canonical release has 369 sources, 40,571 candidate windows, 26,573 retained
payloads (14,386 background-only and 2,982 partial edges), and 13,998 nodata
omissions. All 6,067 retained evaluation-overlap exclusions remain canonical.
Baseline active train/val/test counts are 18,311/933/1,262 with BC and
15,621/933/1,262 without BC. No per-fold or spectral payload copies are needed.

The baseline evaluation input footprint is 906,445,909 geometric pixels:
disjoint nominal grid 872,744,371, retained area 557,094,374, uncovered edges/gaps
33,701,538, and nodata-omitted grid area 315,649,997. These are geometric counts,
not valid-label support, geographic area or model scores. Complete fold counts
and restoration evidence remain in [Task 032B](../../tasks/032b_produce_and_publish_chip_release.md).

## Shoreline reference location

Immutable supplied exports are at `kelp-box:kelpseg/data/1_raw/shorelines_v1/`:
`mainlands.gpkg`, `big_islands.gpkg`, and `small_islands.gpkg`, all EPSG:4326.
The recorded GPU copy is `/home/sky/data/data/1_raw/shorelines_v1/`.
[Task 040](../../tasks/040_shore_distance_diagnostics.md) owns acquisition,
feature-count and geometry-verification evidence.
