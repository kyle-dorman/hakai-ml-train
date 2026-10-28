# Task 030A: Build and publish organized intermediate 2

Status: Complete — local build/QA and Box publication verified on 2026-10-27.

Depends on: completed Tasks 027, 029A and 029B. Task 029B's current handoff is its
[preparation-wide simplification outcome](029b_clean_organized_sources.md#preparation-wide-simplification-outcome-2026-10-27),
committed in `203c5a7`. Task 029B provides
one-pass preparation with no restart support.

Execution: Local production organization, read-only QA, and verified Box copy.
The current request authorizes the local build, QA and verified Box publication.

## Abstract

Use the implemented organizer to build the first complete unsplit variant-2
release from the declared raw ZIP members, then publish its exact contents to
Box with checksum verification and a bounded restoration check. Organization
changes names and layout only; image, label and companion bytes stay unchanged.

This is an execution/publication task, not another preparation implementation.
Stop after the organized release, QA, verified backup and researcher recovery
recipe. Shared cleanup implementation belongs to Task 029B; the full cleaned
variant-3 build/publication belongs to Task 030B. No chipping or splits here.

Task 030B depends on this task's verified **local** release and handoff, not its
Box publication. Announce local readiness promptly, then continue Box work in
this chat while Task 030B may run separately against the immutable local parent.

## Inputs and reading route

Follow the normal entry path, then read
[data_artifacts.md](../docs/data_artifacts.md),
[box_backup.md](../docs/box_backup.md),
[documentation.md](../docs/documentation.md), and the organization/check sections
of [quickstart.md](../docs/quickstart.md). Read
[Task 029A's outcome](029a_organize_raw_sources.md#outcome-2026-10-27)
and its researcher-maintainability follow-up for current package paths;
[Task 027's outcome](027_verify_box_and_back_up_raw_reference_audit.md#outcome-2026-10-27)
owns trusted raw/Box evidence. Read Task 029B's actual completed outcome and
source-check API before freezing QA commands; do not treat its planned CLI as
implemented. Use [architecture.md](../docs/architecture.md) and
[cleanup_provenance.md](../docs/cleanup_provenance.md) only for source-check
interpretation and unresolved scientific evidence limits.

Use the existing `configs/organize/ca_bc.toml`, `configs/regions.csv`, ignored
`paths.local.toml`, and external `preparation_inputs/ca_bc/v1/` catalog. Never
substitute repaired `merged_all_regions_v1` TIFFs for original ZIP members or
regenerate a catalog simply because converter code has changed.

The following are Task 029A's frozen expectations, to verify during preflight:

| Evidence | Expected identity/scope |
|---|---|
| Input catalog `catalog_manifest.json` SHA-256 | `923c2da76f94006d02b2f14728fbfc3268eb8c9813c82cd54cbfaa93a8fde003` |
| Logical organization plan SHA-256 | `093990dde1d538e64dce72e001790b5802d8a0977a24b31cbd67c22350143fb8` |
| Membership | 369 pairs: 339 CA-family and 30 BC tiles; 12 regions |
| Companions | 418: 325 CA masks, one CA overview, 90 BC image auxiliaries, two BC label auxiliaries |
| Aliases | 3,919 rows; 290 pair owners with known long aliases, 79 without verified long aliases |
| Payload before generated controls | 1,156 files; 28,564,758,070 uncompressed bytes |

These are metadata-plan observations, not proof that the full release exists
or its payloads passed verification. Reconcile differences; do not force counts
by dropping identities/assets. Preserve regions 005 and 006 separately, repeated
images with different labels, shared BC mosaics, all delivery associations and
exact member paths. The six BC full scenes remain outside this release scope.
Raw delivery train/val paths remain provenance, never new assignments.

## Expected outputs and ownership

| Location | Deliverable |
|---|---|
| `/Volumes/x10pro/kelpseg/data/2_organized/ca_bc/v1/` | Complete organizer release: primary rasters, all declared companions, region/source/alias/asset tables, input snapshots and completion manifest |
| `kelp-box:kelpseg/data/2_organized/ca_bc/v1/` | Exact verified copy of that release, without added QA/transfer files |
| `/Volumes/x10pro/kelpseg/backups/task030a_organized_ca_bc_v1/` | Frozen operational plan, build logs, QA reports, dual-hash catalog, remote listings/checks, bounded restores, receipts and atomic transfer completion |
| `kelp-box:kelpseg/transfers/task030a_organized_ca_bc_v1/` | Verified portable transfer/QA evidence and final publication marker, separate from release payload |
| `docs/quickstart.md`, `docs/box_backup.md` | Actual build/fetch/verify recipes, output meanings and corrective errors |
| `docs/data_artifacts.md` | Compact current release identity/location and evidence limits after publication |
| This task, `docs/todo.md`, `tasks/README.md` | Outcome, exact validation, unresolved issues and next action |

Use existing package code under `src/kelpseg/prepare/` and thin CLI handlers.
No new preparation command, storage service or repository `scripts/` helper
is expected. Record exact commands and any small one-off receipt producers in
the external transfer package. Reusable fixes belong in package code with
focused tests; a substantial implementation gap becomes a separate bounded
task rather than silently expanding this production task.

## User decisions required

None blocking for the plan. Safe defaults are the existing `ca_bc/v1` recipe,
copy mode, ordinary release folders, separate receipts, direct rclone copies,
the existing checksum/fallback policy, and a 128 MiB restoration payload cap.
No new annotation, mask, band or split policy is selected here.

On later execution, proceed within this contract without reapproving routine
steps. Stop the affected operation for contradictory membership/parent hashes,
unresolved output conflicts, unsupported/corrupt inputs, or insufficient storage
or upload capacity. Record exact evidence and a concrete resolution. Do not
drop files, overwrite a closed release, invent semantics, change the storage
service or widen the declared scope to get a pass.

## Execution contract

### 1. Freeze a reviewable operational plan before expensive work

Reread the entry documents and actual Task 029B handoff. Mark only this task
In progress when its execution is requested; preserve unrelated/concurrent work.
Do not synchronize an environment used by another running chat. A frozen
environment check can use the established environment or a separate one.

Verify the volume is mounted before creating paths. Inspect existing production,
staging and transfer prefixes: fresh destinations are the default. A matching
existing release may be independently verified without rebuilding it. New
organization requires fresh final/staging paths. Interrupted work is never reused;
inspect it and choose a fresh release or explicitly remove the failed attempt
before rerunning from the beginning. Contradictory/corrupt evidence stops the operation.
Do not assume absence from Task 029A's historical outcome is still current.

Validate the catalog manifest against the trusted identity above and its table
hashes; build the whole plan using the installed functions. Reuse Task 027's
archive SHA-256 identities only with their named catalog provenance and unchanged
stability evidence. Size/mtime alone cannot establish a new content identity.
Rehash affected archives if inputs changed or the prior evidence cannot be
trusted. Preserve earlier packages, receipts, smoke releases and originals.

Write `plan.json` in the separate receipt workspace with code/environment and
recipe/catalog identities, exact membership/assets/aliases, resolved roots,
expected bytes, plan hash, free-space evidence, QA commands/settings, restore
selection/budgets and transfer mapping. Freeze it atomically before copying.
Later discoveries use explicit supplements; never silently rewrite a frozen plan.

Budget one roughly 28.6 GB payload tree plus controls, logs, at most 128 MiB
of restored payload and explicit working headroom. Staging and final release
share a filesystem and are renamed, not duplicated. Estimate full-scan decoded
pixels and verification I/O separately: shared BC mosaics can make scans costly,
and the organizer already performs several required integrity reads. Record
actual available space and largest output file; do not promise one total pass.

### 2. Build unchanged variant 2 with the existing interface

These organizer commands are implemented:

```bash
uv run kelpseg organize --recipe configs/organize/ca_bc.toml --paths paths.local.toml --dry-run
uv run kelpseg organize --recipe configs/organize/ca_bc.toml --paths paths.local.toml
```

There is no resume mode. Both final and staging paths must be fresh.
Capture normal progress logs outside the release. Dry-run must show the complete
scope/destination and expected plan hash before copying. It does not verify
member bytes. Stream declared ZIP members directly; no whole-archive extraction,
hard-linking to originals, raster rewrite, alignment, deduplication or filtering.

Require per-role source-stream SHA-256 and independent copied-byte verification,
all companion associations, internal TIFF header records and exact inventories.
Physical bands and unknown companion meanings stay unestablished where evidence
does not supply them. Sidecar contents, including old internal names, stay intact;
the organizer's header records explicitly exclude sidecar interpretation.

Use the fresh sibling incomplete directory as one attempt's output. There are
no locks, receipts, recovery journals or matching-output reuse. Failure stops the
run and retains incomplete work for inspection; a retry starts from the beginning.
Finalization publishes only after all checks pass. Existing completed releases
are inspected through the read-only verifier, never by rerunning organization.

The existing library verification is
`kelpseg.prepare.organize.verify_organized_release(release, plan)`. It checks
every payload/control hash, inventory, logical inputs, provenance and headers
against the plan. There is no separate organizer verification subcommand or
`--report` flag. Use its completion-time verification evidence; do not repeat
full-release reads without a new integrity reason. Authenticate the root
`manifest.json` SHA-256 separately because it does not hash itself.

### 3. Perform source QA without changing the release

Use Task 029B's implemented source-profile checker through its documented
CLI/library, freezing actual flags/settings in `plan.json` before execution.
Run quick structure/header checks over all primary pairs and full source pixel
checks over all selected primary images/labels in bounded blocks. Record actual
checked pixels/files, unknown/skipped checks, findings and actionable failures.
Byte hashes alone do not prove pixel decodability or valid class values.

Original grid mismatches, source label `nodata=0` with valid class zero, and
audited missing/different image nodata declarations are preservation findings
for this stage. Use explicit audited source settings, not cleaned 0/3 invariants
or undocumented fallbacks. Record these repairable findings for Task 030B;
unsupported classes, unreadable pixels, missing georeferencing or ambiguous
pairing/identity block publication until resolved. Never discard a failed check
or suppress arbitrary errors to produce success. If the source checker cannot
express an expected source condition, record the gap and resolve it explicitly.

Any reused full-scan result must be keyed to verified identical bytes and the
same relevant settings/sidecar context, with every reused owner mapped to the
evidence. Do not implement a cache merely for this task or silently sample a
scan advertised as full. Opaque companions need byte/ownership verification;
their pixel semantics are not established by scanning the primary TIFFs.

Put QA reports outside input/release directories; confirm neither checker nor
GDAL created sidecars or changed payloads. Reconcile per-region counts, original
and output grids/nodata, alias coverage and asset dispositions against the frozen
plan and release tables. Distinguish internal TIFF headers from any observations
made with external sidecars active. No new previews/coverage rasters are required.

Local organizer completion and publishable QA are distinct gates. A release
that fails QA remains unchanged with failure evidence; do not call it a verified
Box publication or mutate its bytes to repair it.

### 4. Finalize local hashes, announce readiness, then publish to Box

Freeze `payload_hashes.csv` covering **every finalized release file**, including
all controls and `manifest.json`, with sorted relative paths, sizes, SHA-256
and SHA-1. Reconcile SHA-256 with the organizer manifest and trusted root hash.
Use a trusted existing dual-hash catalog if valid; otherwise compute both hashes
together in one deliberate finalized-file read, with stability checks. Keep
this catalog and its authenticated identity outside the closed release.

#### Local-ready milestone and immediate notification

After organization, all local source QA, and the finalized transfer hash catalog
pass, write `local_ready.json` atomically in the receipt workspace. Include the
absolute immutable parent path, dataset/release, plan/root-manifest identities,
membership/asset counts, QA report paths/results, known repairable findings and
the Task 029B code/settings handoff. Record local readiness in this task and the
queue, keeping Task 030A In progress until Box verification finishes.

Immediately send a clear commentary update: **"Task 030A local work is complete.
You can start Task 030B now. Box upload and verification are continuing."** Include
the local parent and handoff paths. Do not wait for the upload or a final task
response to announce readiness, and do not pause for approval before continuing
the authorized Box steps. A failed local gate means Task 030B is not ready.

Task 030B must read the immutable local parent and write separate variant-3
outputs/receipts. Neither chat may modify the parent's files or synchronize an
environment the other is using. Keep transfer evidence outside both releases.
Coordinate shared documentation through narrow edits: preserve Task 030B's
active status and later queue changes when recording Task 030A publication.

Confirm the actual Box account/project is the recorded UCLA project under
`kelp-box:kelpseg`; recheck authentication, available quota and per-file upload
limit. Task 027's capacity observations are not permanent guarantees. Do not
print credentials, change sharing/account settings or create nested duplicates
of the intended project root.

Before bulk copying, upload/download a small deterministic fixture in the new
transfer's `checks/roundtrip_v1/` and require exact paths, sizes and SHA-256.
Use a fresh local restore directory; cap this fixture at 4 MiB. Freeze remote
prefix ownership/plan identity before upload. Existing objects can
only be reused after path/size/native-hash verification against this catalog.

Copy the exact release tree with direct rclone operations, normally
`rclone copy <release> kelp-box:kelpseg/data/2_organized/ca_bc/v1 --immutable --checksum --transfers 1 --checkers 2`.
Record exact invocation, exit codes and retries. No sync/move/delete, overwrite,
size-only acceptance or custom synchronization framework. An unrelated/conflicting
remote object blocks completion; it is not silently deleted or replaced.

Compare every remote relative path, size and **nonempty SHA-1** with the frozen
local catalog; require exact inventory. `--checksum` alone is insufficient.
Retain listings and per-file results with method `provider_sha1_verified`.
For missing/disagreeing native checksums, preserve the failure, recheck affected
local identity and use bounded metadata retries followed by affected-file streamed
SHA-256 readback as needed. Record `readback_sha256_verified` only on actual
equality; byte disagreement blocks completion. No routine whole-release remote
readback is required. Record actual fallback traffic and findings.

### 5. Prove bounded recovery and close publication atomically

Before downloading, freeze `restore_selection.json` from member sizes and
release tables, with explicit files, hashes, reasons and total bytes. Download
all release control files plus selected primary/companion payloads into a fresh
restore root. Default payload cap is **128 MiB**; budget controls separately.

Cover a CA pair/mask, an extra-archive pair, a BC pair with mismatched original
grids, BC image auxiliaries and a label auxiliary. Task 029A's two real smoke
pairs total only 21,932,688 payload bytes and are a useful starting point;
they omitted extra-archive payloads and label-sidecars. Choose additional files
using metadata rather than scanning payloads. If this coverage cannot fit the
cap, record the exact sizes and resolve the selection/budget explicitly before
download; do not silently widen it or claim omitted cases passed.

Authenticate the downloaded root manifest against the trusted local root hash,
check all downloaded controls and sample paths/sizes/SHA-256, reopen selected
TIFF headers and reconcile their identities/asset relationships with the tables.
Keep the complete manifest intact. A sample directory is incomplete by design:
do not run the whole-release verifier on it or fabricate a subset completion
manifest. Report a bounded restoration, not a full restored-release validation.

Freeze an explicit evidence upload allowlist/catalog: plans/supplements, QA
reports, closed logs, checksum catalogs, remote checks, restore selection/results,
receipt producers and recovery instructions. Exclude downloaded payload copies,
temporary files and live state. Upload only those finalized files and the bounded
round-trip fixture under the separate transfer prefix. Verify every evidence
file by the same native/fallback policy or direct SHA-256 readback for small
controls, and require the exact allowlisted remote inventory.

Upload `completion.json` **last**, then read back and authenticate that marker.
Keep hash relationships noncircular: the marker references finalized evidence-
catalog and release-root hashes; the evidence catalog covers the other finalized
evidence files but excludes itself and the marker. Verify that catalog directly
by SHA-256 readback. Publish local transfer completion atomically only after
remote marker verification. Later logs stay outside the closed evidence package.
Release `manifest.json` means local organization completed; transfer
`completion.json` means Box publication passed.

Update the researcher guide and Box recovery instructions with actual paths,
completion identities and ordinary fetch/hash checks. A full fresh restore can
use `verify_organized_release()` after all files arrive; it must first authenticate
the manifest from the recorded trusted root identity. Explain outputs and
corrective errors without requiring source edits or detailed QA-mask inspection.

## Smoke and validation

- Preflight: trusted catalog/plan identities, complete counts/associations,
  mounted roots, explicit space/scan/restore budgets and no conflicting writers.
- Production: all declared member copies and independent output hashes, exact
  completed inventory/provenance, unchanged original bytes and no modifications
  from checking; quick/full source evidence with all expected findings recorded.
- Failure: use Task 029B's one-pass fixtures for interruption safety; do not
  deliberately interrupt or corrupt production. A real interruption stops the
  attempt; retain evidence and plan a full fresh rerun. Independently verify an
  existing completed release without rerunning organization for demonstration.
- Transfer: fresh bounded round trip; every release file verified by Box SHA-1/
  size/path or affected-file SHA-256 readback; exact inventory, bounded restore,
  verified receipt files and authenticated final remote/local completion.
- Documentation-only changes: inspect Markdown/diffs, resolve local links and
  anchors, balance fences and run `git diff --check`. Do not synchronize the
  environment or run unrelated model tests for documentation changes.
- If package code changes are necessary, run relevant existing focused tests,
  `uv run ruff format --check .` and `uv run ruff check .`; broad code changes
  also require `uv run pre-commit run --all-files`. Record unrelated preexisting
  failures. No GPU, W&B, training or scientific parameter tuning is required.

## Acceptance criteria

- `ca_bc/v1` contains all 369 declared pair identities and 418 companions, with
  unchanged source bytes and all source/member/hash/grid/alias associations;
  all expected scope counts reconcile, including controls separately.
- Local immutable completion is authenticated and tied to the frozen plan.
  Source QA is complete at its stated levels; known repairable conditions are
  carried forward explicitly and unsupported/corrupt inputs remain blockers.
- The local-ready handoff is recorded and announced before Box work, allowing
  Task 030B to start in another chat while this task finishes publication.
- The exact release and its separate evidence package are verified on Box;
  every file has checksum evidence, bounded recovery passes and final marker
  verification completes. Successful transfer exit status alone is insufficient.
- Original archives, earlier releases/reference/audit/receipts and concurrent
  work are preserved. No cleaning, new assignments or deduplication occurred.
- Everyday build/fetch/verify uses documented settings and ordinary
  commands. Record the simplicity check and any obsolete code/options removed;
  no removal is expected for this execution-only task. No framework is added.

## Non-goals

Variant-3 production; alignment or nodata repair; mask/physical-band inference;
label truth claims or historical-delivery completeness claims; binary remapping;
filtering/background removal; chips, collections/splits, models or new regions;
raw archive repackaging; the Task 031 walkthrough; full remote readback by default.

## Outcome template and exact next action

Record changed repository files; actual code/recipe/catalog/plan and root-manifest
identities; final file/byte and per-region/role counts; raw identity reuse or
rehash reasons; source QA scope/results/unknowns and Task 030B repair findings;
source stability, failed one-pass attempts and I/O/space budgets; local/Box paths;
per-file native/fallback evidence and traffic; bounded restoration selection/
results; verified receipt/catalog/marker hashes; researcher recipe/simplicity
check; unresolved issues and a completion claim limited to the evidence.

Mark Complete only after every production acceptance gate passes. Task 030B may
already have started after the local-ready notification. If it has not, the exact
next action is to scope its cleaned-release build/publication contract using this
verified local parent and Task 029B's completed cleaner/settings. Carry source QA
findings forward; do not start cleanup in this task. Update this task's publication
status in both queues without overwriting concurrent Task 030B progress, and stop.

## Contract preparation outcome (2026-10-27)

Prepared this contract and linked it from `docs/todo.md` and `tasks/README.md`,
preserving Task 029B as the active implementation in its other chat. Independent
read-only reviews checked the organizer/QA boundary and Box integrity/recovery
gates. The contract distinguishes source preservation from cleaned invariants,
local completion from publication, and bounded restoration from full readback.

Validation: all 63 local links/anchors across these three documents resolve;
fences/whitespace and `git diff --check` pass. This planning work used repository
docs/code only: no external payload reads/hashing, environment changes, production
outputs or Box operations. Concurrent Task 029B code/docs edits are preserved.

Planning is complete; execution remains Pending. Task 029B has since completed
and was committed as `203c5a7`. The user requested a local-ready notification so
Task 030B can begin independently of Box publication; that milestone is now
explicit above. No blocking user decision is needed. Exact next action: when
Task 030A execution is requested in a new chat, reread the current Task 029B
handoff, freeze the source-QA commands and operational plan, then execute this
contract and announce the local-ready milestone before continuing Box work.

## Execution freeze (2026-10-27)

Execution is authorized by the current user request, including Box publication
without another approval. The mounted `/Volumes/x10pro` had 656,657,973,248
available bytes. Production final/staging paths and the transfer workspace were
fresh. Existing unrelated queue/contract changes were preserved. The existing
Python 3.12 environment is used with `uv run --no-sync`; no environment sync or
package changes are planned.

Frozen external plan:
`/Volumes/x10pro/kelpseg/backups/task030a_organized_ca_bc_v1/plan.json`, SHA-256
`790b1bf5879e79f27f0fde1550e2c24fc79f29b371f701282cc663a49aafe8cd`.
The catalog and logical plan match the trusted identities above. The authenticated
Task 027 catalog/completion/manifest and all three original archive size/mtime
records match, permitting documented archive-hash reuse. Every selected member
is still hashed during organization and independently checked after copying.

`plan_supplement.json` corrects the planning estimate to primary rasters only:
2,905,415,276 image pixels, 15,737,515,636 native label pixels and approximately
62.2 GB decoded arrays across all owner scans. It also freezes a 90,741,406-byte
payload restoration selection, plus all controls; the limit remains 128 MiB.
No cached or sampled full-scan evidence is used.

Organization completed in one attempt at 16:02 PDT. Its completion-time verifier
checked 1,162 files covered by the manifest; the manifest itself is separately
authenticated by the local QA/hash gate. Source QA uses the unchanged
`configs/check/planet8_source.toml` with explicit missing-image-nodata fallback
0, classes 0–4 and 512-pixel blocks. Expected repairable source findings remain
explicit in both reports; any unsupported finding or incomplete scan stops
publication. Local-ready and Box gates are still pending.

## Local-ready handoff (2026-10-27)

All local gates passed. The immutable parent is
`/Volumes/x10pro/kelpseg/data/2_organized/ca_bc/v1/`. Root `manifest.json`
SHA-256: `435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8`.
The finalized release contains 1,163 files / 28,568,499,959 bytes.
`payload_hashes.csv` SHA-256:
`c287f7a8b5ae2ac9abd2f73d85fbbf837b0b316b447f2c948d71ba0461251f88`.

Atomic handoff:
`/Volumes/x10pro/kelpseg/backups/task030a_organized_ca_bc_v1/local_ready.json`.
Both QA reports and `qa_summary.json` are beside it. All 369 pairs decoded:
2,905,415,276 image pixels and 15,737,515,636 native label pixels. Zero unsupported
findings; preservation-stage acceptance retains 34 pair-grid mismatches,
355 label-nodata declarations and 326 paired-nodata findings. Label nodata is
absent for 325 sources, zero for 30 and already 3 for 14. Image nodata is absent
for 325 (explicit fallback 0), zero for 39 and 65535 for five.

Task 030B may now start separately, using Task 029B's existing cleaner/settings
and exact parent provenance. Grid mismatches include all 30 BC pairs plus
`002_20210419_182256_240c`, `008_20201010_180745_2304`,
`008_20201110_185814_2405`, and `008_20201116_185541_2416`. Preserve valid
class-zero background; source labels can contain classes 0–4. Physical band
identity and companion semantics remain unestablished. Parent inventory/stats
and every finalized SHA-256 match the completion manifest; neither source QA
nor GDAL created sidecars or altered payloads. No Task 030B operation ran here.

Task 030A remains In progress until its authorized Box publication, exact
checksums, bounded restoration and final marker verification complete. Do not
modify this parent or synchronize the environment used by the other chat.

## Outcome (2026-10-27)

**Complete.** Built the unchanged, unsplit `ca_bc/v1` organized release in one
fresh attempt, completed all local QA/hash gates, announced the local-ready
handoff before starting Box operations, and verified publication at 17:14 PDT.
Task 030B started independently against that parent and remains active in its
other chat. No cleanup, chipping, splitting or model work ran here.

### Release and identities

- Local: `/Volumes/x10pro/kelpseg/data/2_organized/ca_bc/v1/`.
- Box: `kelp-box:kelpseg/data/2_organized/ca_bc/v1/`,
  [folder 431680482261](https://app.box.com/folder/431680482261), under the
  authenticated UCLA project/account recorded above.
- Receipts: `/Volumes/x10pro/kelpseg/backups/task030a_organized_ca_bc_v1/` and
  `kelp-box:kelpseg/transfers/task030a_organized_ca_bc_v1/`.
- 369 image/label pairs, 418 companions and 3,919 aliases across 12 regions:
  1,156 payload files / 28,564,758,070 bytes, plus seven controls /
  3,741,889 bytes; **1,163 files / 28,568,499,959 bytes** total.
- Per-region pair counts: 001=22, 002=59, 003=17, 004=29, 005=21, 006=35,
  007=32, 008=65, 009=14, 010=33, 011=12, 012=30. Companions remain 325 CA
  masks, one CA overview, 90 BC image auxiliaries and two BC label auxiliaries.
  Known long aliases cover 290 owners; 79 have none verified. Repeated images,
  different labels, shared mosaics and all declared associations remain intact.

Producing package commit: `203c5a778b106792d68856bb126e54b40ed78f16`;
Python 3.12.11, existing `.venv`, `uv run --no-sync`. No package implementation,
dependency, recipe or environment change was required. Exact module hashes and
lock/environment identities are in `plan.json`.

| Identity | SHA-256 |
|---|---|
| Organization recipe | `01417a83db7888e7cc1c669b1d6cf4636e1451669485720f2045043a217256ab` |
| Source-check recipe | `a142e0741af0f548d18e35cd6da3dd9246ba820bab194f989831614daaa771bc` |
| Trusted input catalog manifest | `923c2da76f94006d02b2f14728fbfc3268eb8c9813c82cd54cbfaa93a8fde003` |
| Logical organization plan | `093990dde1d538e64dce72e001790b5802d8a0977a24b31cbd67c22350143fb8` |
| Frozen operational plan | `790b1bf5879e79f27f0fde1550e2c24fc79f29b371f701282cc663a49aafe8cd` |
| Explicit plan supplement | `f64050ea21a8c186d5d597e345956697a9f956e32f51e8cf3efd25d866f737ae` |
| Release root manifest | `435e1fbc30d413f9941c3bcb56be074df9e2e863e564479b05fca04c87c817a8` |
| Finalized dual-hash catalog | `c287f7a8b5ae2ac9abd2f73d85fbbf837b0b316b447f2c948d71ba0461251f88` |
| Atomic local-ready handoff | `742e8ba77ee1d3744231dc11eb6723f8d6e59b39fafefdc49fb78d0520f6d320` |
| Evidence catalog | `c73ab72e6fac3b619ac4e82100108c739e0c3678717d33edb9f6727e519b9cf1` |
| Authenticated remote/local completion marker | `471cfb2902287ee10e9a92b2a54ae46c568a029decf92eb2f5e843bab63b39ae` |

### Local validation and scientific limits

The organizer hashed selected ZIP-member streams, made independent physical
copies for repeated members, recorded internal headers, and independently
verified output bytes before publication. No whole archives were extracted.
The three original archive identities were reused from the authenticated Task
027 catalog chain with unchanged size/nanosecond-mtime evidence. Original inode,
device, size and mtime also remained unchanged through final publication.
No fresh whole-archive hash pass was claimed or needed.

Quick QA covered all 369 primary pairs; full QA decoded exactly 2,905,415,276
image and 15,737,515,636 native label pixels, including every shared-mosaic
owner. All full records have completed pixel counts; no unsupported issue,
unreadable pixel, skipped source or unknown primary georeferencing remains.
Stored classes observed were 0–3 within the explicit allowed 0–4 vocabulary.

Both unmodified checker reports retain their non-passing source-profile status
for expected repairable conditions. The separate preservation-stage acceptance
passed with all 34 pair-grid, 355 label-nodata and 326 paired-nodata findings
retained. Grid-dependent paired consistency was skipped only where original
grids differ; those labels still received complete native-grid scans. The
local-ready section records nodata distributions and the four CA mismatch IDs.
Task 030B must preserve valid class-zero background and apply the existing
alignment/coverage/nodata policy into its separate release.

Checker observations used internal georeferencing, disabled PAM, native unmasked
pixels and no overview decimation. Exact header/table reconciliation against
the frozen plan passed in `provenance_reconciliation.json`. Payload/control
inventories, size/mtime/inode snapshots and finalized SHA-256 values remained
unchanged after checking. No GDAL sidecars were created. Physical band identity,
companion pixel semantics, historical completeness and label truth remain
unestablished. This is source preservation, not a cleaned-release claim.

The original free-space budget was 656,657,973,248 bytes, with 10 GiB working
headroom, one payload tree and a 128 MiB restored-payload cap. The largest file
was 260,471,934 bytes. The supplement corrected the initial decoded-cost
estimate to 738 primary rasters before copying; actual full-scan counts match
that estimate (approximately 62.2 GB decoded arrays). Required source/copy,
verification, pixel-QA and finalized dual-hash reads remained distinct. There
was no failed or interrupted preparation attempt and no partial-work reuse.

### Box verification and bounded recovery

Fresh authentication confirmed account `40477689073`, `kdorman90@ucla.edu`,
project folder `431635691068`, a 161,061,273,600-byte upload limit and sufficient
reported capacity. The unusually large quota remains a reported value, not an
unlimited-storage claim. Both release/transfer prefixes were fresh. A
1,048,676-byte deterministic fixture passed exact path/size/SHA-256 upload and
fresh download before bulk copying.

`release_upload.log` records the direct immutable/checksum copy with one
transfer, two checkers, bounded retries 3/5 and exit 0. The upload ran from
approximately 16:05:48 to 17:13:23 PDT (log creation/exit-receipt timestamps).
No errors/retries were reported in the default-level log; internal low-level
retry counts are not exposed at that verbosity. No sync, move, delete or
conflicting-object overwrite occurred.

All **1,163** remote paths, sizes and nonempty native SHA-1 values matched the
finalized local catalog, with unique provider IDs and exact inventory.
`release_verification.json` records every file as `provider_sha1_verified`;
release fallback traffic was zero. Its SHA-256 is
`1521b5c6bc0474eca61cdef5aa8ed72c94693759c305a025946cb8ab178071dd`.

The frozen restoration selected CA `007_20211212_184127_227a` plus its mask,
extra-archive `001_20210419_182256_240c`, and mismatched BC
`012_20210811_184459_09_245c_clip3` with all five image/label auxiliaries.
All 19 selected files passed size/SHA-256 checks: 90,741,406 payload bytes plus
3,741,889 control bytes, below the 128 MiB payload cap. The complete manifest
was authenticated, primary headers exactly matched source tables, and ownership/
member relationships reconciled. Two overview companions lack independent CRS
metadata and emit a retained Rasterio warning; no primary lacks georeferencing.
No companion semantics were inferred. This is a bounded restoration, not a
full restored-release validation. `restore_result.json` SHA-256:
`972aab9546629d2c2068a306d2ada38259209c06ec172c94e67f4c95af67df48`.

The evidence catalog covers 45 finalized files, including the fixture; catalog
and final marker make **47 remote files / 9,337,156 bytes**. Every evidence file
matched provider SHA-1/path/size; fallback traffic was zero. The catalog also
passed direct SHA-256 readback. Downloaded payload copies, drafts, temporary
files and live closing logs were excluded. The marker was uploaded last, read
back byte-for-byte and authenticated, then local `completion.json` was published
atomically. The marker carries per-file evidence verification methods and
references the release root and evidence catalog without circular hashes.
Later closing logs remain outside that closed package.

### Repository handoff and exact next action

Changed Task 030A files: this task, `docs/todo.md`, `tasks/README.md`,
`docs/quickstart.md`, `docs/box_backup.md`, and `docs/data_artifacts.md`.
Preexisting contract/queue edits and concurrent Task 030B/031 documentation,
architecture changes and status entries were preserved through narrow edits.
Generated data, reports, receipt producers and hashes remain outside Git.

The researcher recovery recipe uses ordinary rclone fetches, a pinned root
manifest SHA-256 and the installed read-only verifier. Routine build/fetch/check
needs settings, not Python source edits. No obsolete package code/options were
removed because this was execution only; no framework or installed command was
added. Source QA, all finalized hashes, exact Box/evidence checks and the bounded
restore passed. Documentation validation passed: 88 local links/anchors,
balanced fences, inspected diffs and `git diff --check`. No unrelated model
tests or environment sync were run.

No unresolved Task 030A blocker remains. Task 030B is already active in another
chat; its exact next action remains its separate cleaned-release publication
and checks, using this immutable parent and the source-QA findings above. Its
status and Task 031 planning remain owned by those chats. Do not execute either
here. Task 030A stops after this closeout.
