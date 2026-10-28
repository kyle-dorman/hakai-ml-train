# Task 030B: Build and publish cleaned intermediate 3

Status: Complete — local cleaned QA and verified Box publication on 2026-10-27.

Depends on: completed Task 029B and Task 030A's verified **local-ready** handoff.
Task 030A's Box upload/completion is not a prerequisite.

Execution: Local production cleanup, QA review, and verified Box publication.
Execution and Box publication are authorized by the user after the verified local-ready handoff; no further routine approval is required.

## Abstract

Run the implemented shared cleaner on the entire local organized `ca_bc/v1`
release to produce a separate, unsplit variant 3. Preserve all 369 pair identities
and their parent lineage while applying the already approved alignment, coverage
and nodata rules. Review the automatic validation and publish the exact completed
cleaned release to Box with verified checksums and a bounded restoration check.

This task primarily executes existing code. No new preparation command or
general framework is planned. Stop after verified publication and the researcher
handoff; chipping and the tiny walkthrough begin in Task 031.

## Inputs and reading route

Follow the normal entry path, then read
[data_artifacts.md](../docs/data_artifacts.md),
[box_backup.md](../docs/box_backup.md),
[documentation.md](../docs/documentation.md), and the checking/cleaning sections of
[quickstart.md](../docs/quickstart.md). Read
[Task 029B's current outcome](029b_clean_organized_sources.md#preparation-wide-simplification-outcome-2026-10-27)
and the matching-grid/alignment outcomes above it for the actual supported scope.
Its implementation is committed in `203c5a7`; record the actual execution revision.
Use [cleanup_provenance.md](../docs/cleanup_provenance.md) to interpret historical
differences, not to restore superseded BC outside-coverage background filling.

Read [Task 030A](030a_build_and_publish_organized.md), its current local outcome,
and `/Volumes/x10pro/kelpseg/backups/task030a_organized_ca_bc_v1/local_ready.json`.
That handoff must identify the completed parent, root-manifest/plan hashes,
membership, successful local QA and known repairable findings. The default parent
is `/Volumes/x10pro/kelpseg/data/2_organized/ca_bc/v1/`. Authenticate its manifest
against the handoff before cleanup; directory existence alone is insufficient.
If local readiness is absent or a local gate failed, do not start cleaning.

Expected parent scope is 369 pairs (339 CA and 30 BC tiles), 12 region codes,
418 companions and 3,919 alias rows. Verify these against the actual handoff;
do not fabricate future hashes or discard rows to match expectations. Keep
regions 005/006 distinct, repeated-image/different-label associations and shared
BC mosaic lineage. Six BC full scenes remain outside scope. Raw train/val paths
remain provenance; this release has no experimental assignments.

## Expected outputs

| Location | Deliverable |
|---|---|
| `/Volumes/x10pro/kelpseg/data/3_cleaned/ca_bc/v1/` | Complete immutable cleaned release with all 369 image/label pairs, automatic validation and parent provenance |
| `kelp-box:kelpseg/data/3_cleaned/ca_bc/v1/` | Exact verified copy, with no extra transfer files inside the release |
| `/Volumes/x10pro/kelpseg/backups/task030b_cleaned_ca_bc_v1/` | Operational plan, logs, QA summary, dual-hash catalog, remote checks, bounded restore and publication evidence |
| `kelp-box:kelpseg/transfers/task030b_cleaned_ca_bc_v1/` | Explicitly allowlisted portable evidence and final publication marker |
| `docs/quickstart.md`, `docs/box_backup.md`, `docs/data_artifacts.md` | Actual production/fetch/verify recipes, trusted release/parent identities and evidence limits |
| This task, `docs/todo.md`, `tasks/README.md` | Outcome, checks, unresolved issues and exact next action |

Actual cleaner output is `images/`, `labels/`, `recipe.json`, `sources.json`,
`check.json` and `manifest.json`, plus inactive parent control snapshots under
`parent/`: `manifest.json`, `sources.csv`, `regions.csv`, `filename_aliases.csv`
and `assets.csv` when present. Cleaned source records embed parent identities
and keep separate input/output hashes, headers, changes and counts.

The 418 original companions remain hashed **inactive references**, preserved in
the immutable parent; they are not 418 copied payloads in variant 3. Require
their complete dispositions/associations. Do not copy stale masks, overviews,
XML or world files beside rewritten TIFFs. Do not require the organized release's
file count or byte total to carry over to the cleaned output. Source records may
contain absolute operational paths; portable lineage uses the parent root hash,
relative paths and crosswalk snapshots, not continued access to those old paths.

## User decisions required

None blocking for this plan. Use the existing audited recipe
`configs/clean/planet8.toml`: eight `uint16` image bands, label values 0–4,
explicit missing-image-nodata fallback 0, block size 512, lossless Deflate and
`qa_masks = false`. Declarations take precedence over the fallback. No new
annotation, mask, physical-band, filtering or split policy is selected here.

Unexpected semantics, identity conflicts, valid all-zero/nodata collisions,
unsupported grids/classes or insufficient capacity require an explicit recorded
resolution. Never silently drop a pair, alter scientific rules or repair the
parent in place. A substantial implementation gap becomes a separate bounded
task. Routine documented settings changes, such as a smaller block size to meet
the existing crop limit, can be recorded without another policy decision.

## Execution contract

### 1. Establish the local parent and freeze a simple operational plan

When execution is requested, reread the entry documents, this task and the
actual 030A handoff. Record this task In progress without replacing Task 030A's
continuing upload status. Both chats only read the immutable parent and write
different output/evidence prefixes. Preserve concurrent edits and never
synchronize an environment the other chat is using. Use the installed frozen
environment without synchronization, or a separate environment if needed.

Confirm the volume is mounted before creating output directories. Both final
`v1/` and sibling `.v1.incomplete/` must be absent for a new cleaning attempt.
No overwrite, preparation resume, partial-work reuse, recovery journal or retry
framework is authorized. A failure stops the sequence and preserves incomplete
evidence. A later attempt starts from the beginning at an explicitly fresh
destination; do not automatically delete failed output.

Freeze `plan.json` outside the release with authenticated parent identity,
exact pair/asset scope, code/runtime and recipe identity, resolved paths,
intended corrections, settings, space/I/O estimates and transfer mapping.
Budget output from target image dimensions, eight `uint16` image bands plus
one `uint8` label band, tile/control overhead and working headroom. Shared-mosaic
source compression is not an output-space estimate. Allow separately for logs,
hash catalogs and at most 128 MiB of restored payload. No full second output
tree is needed for publication; staging is renamed on the same filesystem.

Dry-run all 369 pairs before pixel work. Supported paired inputs are single-band
`uint8` labels and same-CRS, north-up unrotated image/label grids. Different
offsets, pixel sizes and extents are supported. Native label crops may not exceed
16,777,216 pixels per window; reduce `block_size` in an explicit recipe if needed,
record it and rerun planning before the full fresh attempt. Do not add arbitrary
reprojection/dtype support or silently transform the parent to pass planning.

### 2. Execute the existing cleaner once

These are implemented commands; the first previews the complete scope:

```bash
organized_root='/Volumes/x10pro/kelpseg/data/2_organized/ca_bc/v1'
cleaned_root='/Volumes/x10pro/kelpseg/data/3_cleaned/ca_bc/v1'
uv run --frozen --no-sync kelpseg clean --images "$organized_root/images" --labels "$organized_root/labels" --parent "$organized_root" --output "$cleaned_root" --recipe configs/clean/planet8.toml --dry-run
uv run --frozen --no-sync kelpseg clean --images "$organized_root/images" --labels "$organized_root/labels" --parent "$organized_root" --output "$cleaned_root" --recipe configs/clean/planet8.toml
```

Stop if the preview fails; do not execute the second command. If an explicit
recipe adjustment is needed, use that same recorded recipe in both commands.
Keep normal phase/file/byte logs outside the release. `--parent` is required for
this production task and must cover the entire parent images/labels directories.

The scientific rules are already implemented:

- Detect original all-band image nodata before changing values/metadata;
  declared 65535 takes precedence over the audited missing-value fallback 0.
- Keep all eight image bands, their order, dtype, grid and retained valid values.
  Read matching labels directly; use nearest sampling for differing supported
  grids, preserving stored class zero and calculating footprint independently.
- Exclude original image nodata plus outside-label footprint. Write zero in
  every image band there and label 3; metadata declares image 0 and label 3.
  Preserve existing label 3 over valid imagery without automatically blanking it.
- Preserve supported categories 0–4. No binary remap or ignore-index -100 yet;
  no background-only exclusion, percentage filtering or source deduplication.
- Reject retained original-valid all-band-zero collisions. Do not reclassify
  them or edit the parent to make the new nodata representation pass.

All outputs are fresh lossless rasters, including semantically unchanged cases;
byte changes do not by themselves imply changed image values. Optional QA masks
stay off. The exact completed tree appears atomically only after validation.

### 3. Review automatic QA and close the local release

The cleaner already verifies parent file bytes, performs a full native source
scan, cleans every pair, runs the independent full cleaned checker, reconciles
counts, checks source stability and publishes atomically. Budget those reads,
including full repeated BC mosaics; do not add another identical whole-dataset
scan or new caching machinery merely for this task.

Use the generated `check.json`, `sources.json` and captured logs. Require all
requested full checks completed with no failed/skipped required output checks;
do not treat a partial scan as complete. Source findings may be repairable;
nonrepairable failures stop processing. Confirm all 369 image/label identities
and per-region counts match the parent, with every output label on its image
grid and all parent alias/member/companion associations retained in provenance.

Reconcile target-grid counts per source and in aggregate:
`final_exclusions = original_image_nodata + outside_label_footprint - nodata_and_outside`,
and `total_pixels = retained_valid_imagery + final_exclusions`. Check changed
image/label counts, existing ignored labels, class transitions and label audit
results. Label 3 may cover valid imagery; image nodata must imply label 3.
Distinguish native shared-mosaic scan counts from target-image pixel changes.

Review the 030A findings and documented CA/BC edge cases in these reports:
declared-65535 sources, offset grids, preserved class-zero/ignored labels and
outside-annotation exclusion. Historical BC fill-0 labels are not the expected
new output. No annotation-truth or unknown-band/mask claim follows from passing QA.

Authenticate the new root `manifest.json` SHA-256 separately. Keep all additional
summaries outside the closed release. `verify_cleaned_release(Path(...))` is an
available read-only library byte verifier for an existing/restored complete
release; it neither resumes cleaning nor establishes manifest authenticity by
itself. Do not rerun verification without a new evidence need when the next
transfer-catalog pass can perform the required hash comparison.

### 4. Publish and prove bounded recovery

Apply the existing [Box checksum policy](../docs/data_artifacts.md#box-project-organization-and-upload-verification)
and [Task 030A's publication gates](030a_build_and_publish_organized.md#4-finalize-local-hashes-announce-readiness-then-publish-to-box),
using this task's separate variant-3 and transfer prefixes. Do not wait for or
claim completion of Task 030A's upload. Recheck current account/root, quota and
largest-file limits; use modest transfer concurrency if uploads overlap.

Freeze `payload_hashes.csv` for every finalized cleaned file, including parent
snapshots and the root manifest, with relative path, size, SHA-256 and SHA-1.
Calculate both hashes together in one intentional read where no trusted dual-hash
catalog exists; compare SHA-256 with the cleaned manifest/root identity. This
pass supplies independent byte comparison without another redundant full pass.

Use a small isolated round trip (at most 4 MiB), then a direct rclone copy with
immutable/checksum guards and bounded concurrency. No sync/move/deletion or
custom recovery system. Compare exact remote inventory, sizes and nonempty SHA-1
for every file. Missing/disagreeing native hashes require diagnosis and affected-
file streamed SHA-256 readback; retain the failed native evidence and per-file
verification method. Actual byte mismatches stop publication. Do not require
whole-release remote readback by default or accept size-only evidence.

Freeze a metadata-selected restore list before download: all cleaned controls
and parent snapshots plus complete cleaned pairs covering CA, extra-archive,
declared-65535 and BC outside-coverage/alignment cases when present. Default
payload cap is 128 MiB; budget small controls separately. Choose by finalized
sizes and QA evidence without new full scans. If the declared sample cannot fit,
record a concrete selection/budget resolution before downloading; do not silently
increase it or claim omitted coverage. Original companion payloads are not part
of this cleaned sample; verify their inactive parent references instead.

Restore into a fresh directory, authenticate the root/controls and compare every
selected path/size/SHA-256. Run the existing full cleaned checker on only the
restored paired sample to prove usability without original absolute source paths;
write its report outside the restore inputs. Do not run the whole-release byte
verifier on an incomplete sample or fabricate a subset completion manifest.
State the exact bounded restoration scope.

Upload an explicit evidence allowlist: frozen plan/recipes, closed logs, QA
summary, checksum catalogs, remote checks, restore selection/results, receipt
producers and recovery instructions. Exclude restored payload copies, temporary
files and live state. Verify every evidence file and exact remote inventory.
Upload and read back transfer `completion.json` last, with noncircular references
to the release-root/evidence-catalog hashes; verify the evidence catalog directly.
Only then publish local transfer completion atomically and mark this task Complete.

Extend the researcher guide/Box instructions with actual production and fresh-
directory fetch/verify recipes and recorded trusted hashes. A complete restored
release can be checked through the library verifier after authenticating its root;
parent operational absolute paths must not be needed to load its cleaned TIFFs.

## Smoke and validation

Use Task 029B's completed synthetic, installed-package and two-pair real smoke
as implementation evidence; do not build another smoke release by default.
Production evidence is the full cleaner's checks, count/lineage reconciliation,
finalized hash comparisons, verified Box inventory and bounded restored sample.
Do not deliberately interrupt/corrupt production to re-demonstrate tested failure
behavior. If a step fails, stop; preparation reruns start fresh from the beginning.

For docs-only changes, check Markdown links/anchors, fences/diffs and
`git diff --check`. If a small code fix is necessary, run relevant focused tests,
`uv run ruff format --check .` and `uv run ruff check .`; broad changes also need
`uv run pre-commit run --all-files`. Record unrelated failures. No production
training, GPU, W&B login or new model validation belongs here.

## Acceptance criteria

- All 369 pairs and 12 region identities remain with exact variant-2 lineage;
  all 418 companion dispositions/aliases are recoverable without active stale
  assets beside changed TIFFs. No original or organized file was modified.
- Cleaned pixel/grid/nodata rules pass the independent full checker; counts and
  class transitions reconcile, with explicit QA scope and original evidence limits.
- Output provenance and exact file hashes are authenticated; the complete local
  release, exact Box copy, bounded restoration and final publication marker pass.
- Routine production/fetch/verify uses existing functions, small settings and
  documented commands. No new framework, resume path or unnecessary scans are
  added. Record the simplicity check; no code removal is expected in this task.
- Concurrent 030A work/status is preserved; neither cleaning nor cleaned
  publication depends on its Box completion. Task 031 is not started here.

## Non-goals

Changing cleanup science or adding unsupported input formats; interpreting masks
or guessing physical bands; original-delivery completeness/annotation-truth claims;
binary mapping, filtering, deduplication, chips, splits, model work, new regions,
raw repackaging, preparation recovery or the Task 031 tiny walkthrough.

## Outcome template and exact next action

Record changed files, actual parent/root/code/recipe identities, durable local/Box
paths, pair/region and actual file/byte counts, per-source/summary transformations,
full QA scope/findings, asset dispositions, space/I/O, failed attempts, checksum
methods/fallback traffic, restore selection/results and authenticated completion
identities. Record researcher recipes, simplicity and unresolved issues. Preserve
Task 030A's independently owned publication status in narrow shared-doc edits.

Exact next action after all acceptance gates: scope Task 031's chipping/band-
selection simplification and tiny walkthrough using the verified cleaned release
and existing Box setup. Update this task and both queues, then stop.

## Contract preparation outcome (2026-10-27)

Prepared this task and linked it from `docs/todo.md` and `tasks/README.md`.
Independent read-only reviews checked the actual cleaner/QA interface and the
local-parent/concurrent-publication boundary. Task 030A's running status and
edits were preserved; Task 030B execution remains Pending.

Validation: all 66 local links/anchors across these three documents resolve;
fences/whitespace and `git diff --check` pass. Planning read repository code/docs
only. No external payload reads/hashing, environment changes, cleaning, production
outputs or Box operations occurred. No new package code or policy is planned.

No blocking user decision remains. Exact next action: wait for Task 030A's
verified local-ready handoff; when Task 030B execution is requested, authenticate
that parent, freeze this task's operational plan and execute this contract.
Do not wait for Task 030A's Box completion or start Task 031 here.

## Execution freeze (2026-10-27)

The user authorized automatic execution after Task 030A local readiness, including
all routine steps and Box publication without another approval. The five-minute
watcher was actually created in this chat, then deleted after the handoff passed.
Authenticated handoff SHA-256:
`742e8ba77ee1d3744231dc11eb6723f8d6e59b39fafefdc49fb78d0520f6d320`.
Parent root SHA-256:
`435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8`.
All report/plan/catalog identities, 369 pairs, 12 regions, 418 companions,
3,919 aliases, complete native scans and unchanged parent inventory/stats passed.
Only documented repairable findings remain in source QA; the 34 differing-grid
paired consistency checks are explicitly deferred to cleaned-grid validation.

Separate frozen plan:
`/Volumes/x10pro/kelpseg/backups/task030b_cleaned_ca_bc_v1/plan.json`, SHA-256
`47d3452cfff39e69b4dbc1bd88edc943d07d3e338c109531609a37127c0a5df0`.
Execution code: `203c5a778b106792d68856bb126e54b40ed78f16`; per-file implementation
hashes and actual runtime versions are in the plan. Recipe SHA-256:
`6403fddd4670861c32bd36268e3c35ab817d06a09a9bdba62ba8748e2d4476d1`.
No recipe adjustment was needed. Header-only crop geometry over every processing
window has maximum 263,169 native pixels, below 16,777,216. Target scope is
2,905,415,276 pixels; conservative tiled output budget is 65,737,772,237 bytes,
plus separate headroom/evidence/128 MiB restored-payload allowances, against
628,066,570,240 free bytes. Final/staging and this receipt prefix were absent.

The complete CLI dry run passed before starting exactly one production cleaner.
The existing environment uses `uv run --frozen --no-sync`; no environment or
Task 030A process changes occurred. Task 030A continues its separate Box work.

## Local cleaned release (2026-10-27)

Exactly one production cleaner completed successfully at 16:37 PDT, with no
failed preparation attempt. It published all 369 pairs/12 regions atomically.
All 2,905,415,276 output image pixels and the same aligned label pixels passed
the independent full cleaned checker: no issues or skipped required checks.
The metadata-only review reconciled every count/transition/audit, exact parent
source row and per-region identity, all 3,919 aliases and 418 companion
associations. There are 425 inactive references including seven parent controls;
only the five crosswalk/manifest snapshots are copied into `parent/`.
The parent inventory, sizes, mtimes and inodes remain unchanged.

Cleaned root `manifest.json` SHA-256:
`43815a8a7e412d0f0ed021c813c6c3b4f3a9a532a4fcbb3f9624a91bbdd5ba61`.
Final local tree: 747 files / 18,662,320,805 bytes. Pixel partition:
1,126,293,123 original-image nodata + 36,925,269 outside-label footprint
- 24,053,323 intersection = 1,139,165,069 final exclusions;
1,766,250,207 retained + exclusions = 2,905,415,276 total pixels.
34,423,997 image pixels and 1,097,832,004 labels changed. Existing label 3
count is 41,354,652; 21,587 final label-3 pixels remain over valid imagery.
All final excluded image pixels have label 3 (zero false negatives).
Target-grid class transitions and per-source counts remain in the external
`qa_sources.json`/`qa_summary.json` and release `sources.json`.

All five declared-65535 sources normalized 21,552,051 image pixels, with
5,203 label changes. All 34 offset/different-grid pairs aligned successfully.
Nine BC pairs have outside-annotation coverage; BC's 12,871,065 valid image
pixels outside that coverage became 0/label3. Stored class-zero and existing
ignore labels were preserved under the approved rules. No new class mapping,
filtering, deduplication or masks were introduced. Native shared-label scan
counts are separate from target-grid transformation counts. Unknown physical
bands, companion semantics, completeness and annotation truth remain limits.

Local QA completion was announced before Box work. Finalized independent
SHA256/SHA1 catalog and verified Box publication are the remaining gates.

## Outcome (2026-10-27)

Completed the authorized Task 030B exactly once through cleaning, full automatic
QA, Box publication, bounded restoration and researcher handoff. The temporary
five-minute watcher was created, authenticated the local-ready gate and was
then deleted before production. Box work did not wait for Task 030A's upload.
No failed production attempt, restart, partial reuse, environment synchronization,
package change or scientific-policy change occurred. The original/organized
parent inventory and metadata remain unchanged after publication.

### Durable artifacts and authenticated identities

- Local release: `/Volumes/x10pro/kelpseg/data/3_cleaned/ca_bc/v1/`.
- Exact Box release: `kelp-box:kelpseg/data/3_cleaned/ca_bc/v1/`.
- Local evidence: `/Volumes/x10pro/kelpseg/backups/task030b_cleaned_ca_bc_v1/`.
- Box evidence: `kelp-box:kelpseg/transfers/task030b_cleaned_ca_bc_v1/`.
- Root manifest SHA-256: `43815a8a7e412d0f0ed021c813c6c3b4f3a9a532a4fcbb3f9624a91bbdd5ba61`.
- Parent root: `435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8`.
- Operational plan: `47d3452cfff39e69b4dbc1bd88edc943d07d3e338c109531609a37127c0a5df0`.
- Recipe: `6403fddd4670861c32bd36268e3c35ab817d06a09a9bdba62ba8748e2d4476d1`.
- Finalized dual-hash catalog: `b56bfce3e03d8a09fe08983e25789d23250e0cfddbed075db344a8dad56053be`.
- QA summary: `54d3c3ead41de796eefe68ccc435aef6af1fd487510392c9a879892c7b5da4cd`.
- Evidence catalog: `d53bfe8113d82bbb21ad4a3327d6b1346606e6d300a1078d2221b5c971f26b4a`.
- Final transfer completion: `1b044c5b851eb35ed379c4e52a1c9ba4a7df0077da3c3d261bd539d65e78730d`.

Runtime: Python 3.12.11, NumPy 2.4.4, Rasterio 1.5.0, GDAL 3.12.1. Execution
revision was `203c5a778b106792d68856bb126e54b40ed78f16`; exact producing-file
hashes are frozen in the plan. Existing source/fixture/installed-package tests
from Task 029B remain implementation evidence; no package implementation changed.
The cleaner took 1,607 seconds, ending 16:37 PDT. Finalized SHA256/SHA1 were
calculated together in one independent read and compared against all manifest
entries. No redundant full output scan or second output tree was added.

### Publication and restoration evidence

Current account/root/quota and actual largest file (185,825,833 bytes) passed
Box preflight. The separate 1,048,676-byte isolated round trip passed native
SHA1 and downloaded SHA256 checks. Direct `rclone copy --immutable --checksum`
used transfers1/checkers2 and ordinary bounded rclone retry settings. The release
upload finished at 17:20 PDT: all 747 remote paths, sizes and nonempty native
SHA1 values matched, with zero fallback/readback bytes and no transfer errors.
The finalized release is 18,662,320,805 bytes; its full QA/count/lineage results
are recorded above and in the allowlisted evidence.

The metadata-selected restore list was frozen before download. Three complete
pairs cover every declared case within the unchanged 128 MiB payload cap:

- `003_20220424_173818_2427`: extra archive plus declared65535.
- `007_20211212_184127_227a`: ordinary CA.
- `012_20210812_193014_80_2416_clip0`: BC alignment and outside coverage.

Restoration downloaded 108,284,380 payload bytes plus 7,149,393 control bytes
(15 files, including all nine controls/parent snapshots). Every selected
path/size/SHA256 and root/parent identity matched. The existing cleaned checker
scanned exactly 23,444,214 image and label pixels across the three restored pairs,
with no issues or skipped checks, using only restored directories. All 369
identity rows, 3,919 aliases and 418 inactive companion references in restored
controls matched. The unchanged original full manifest remains intact; no subset
completion was fabricated and no whole-release verifier ran on the sample.

The explicit evidence allowlist contains 47 finalized files including the tiny
round-trip fixture, plus the directly authenticated catalog and final marker:
49 remote files / 6,276,279 bytes. Every evidence file passed native SHA1; zero
fallback bytes. Restored payload copies, temporary/live files and draft notes
were excluded. `completion.json` was uploaded last and read back at 17:22 PDT;
only then was local completion published atomically. Final exact remote evidence
inventory and local parent/release stability passed. Detailed receipts include
`release_verification.json`, `restore_result.json`, `evidence_verification.json`,
`completion_readback.json` and closed operation logs. No later remote write occurred.

### Repository handoff and limits

Changed this task, `docs/quickstart.md`, `docs/box_backup.md`,
`docs/data_artifacts.md`, `docs/todo.md` and `tasks/README.md`. Preserved concurrent
Task 030A closeout and unrelated Task 031 draft/architecture edits. The guide now
records actual production and fresh-directory fetch/authenticate/verify recipes;
portable loading does not follow original operational absolute paths.

Simplicity: existing plain cleaner/checker functions and one small TOML recipe
performed production. No new package command, framework, recovery machinery,
mask output, scientific remapping, code removal or dependency was needed.
One-off receipt producers are external and published with their exact inputs,
checks and logs. Standard CLI logs showed every expensive phase and source.
Physical band identity, companion semantics, original completeness and annotation
truth remain recorded evidence limits. No unresolved execution blocker remains.

Documentation validation: 92 local links/anchors resolve across the six owned
documents; fenced blocks are balanced and `git diff --check` passes. Final
completion-marker references match the actual catalog, QA, release-verification
and restore receipts. Production/checksum/restore checks supply behavioral
evidence; no package change required rerunning the existing fixture suite. An
independent final read-only review found no actionable inconsistency between
the six documents and the closed QA/publication/restore receipts.

Exact next action: hand the verified cleaned release to the existing Task 031
planning chat for chipping/band-selection simplification and the tiny walkthrough
when requested. This chat stops after Task 030B; no Task 031 work ran here.
