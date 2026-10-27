# Task 027: Verify Box and back up raw ZIPs, reference, and audit

Status: Pending — contract ready; execution and uploads not started.

Depends on: Tasks 025 and 026.

Execution: Local inventory/hashing, a small Box round trip, then explicit rclone
copies and verification. This contract does not itself start those operations.

## Abstract

Establish a verified UCLA Box backup of the current dataset's variant 1 (three
unchanged raw ZIPs), the complete legacy reference package, and the complete provenance audit.
Keep ordinary folders, manifests, and copy/download recipes. Completion means
all declared payloads are verified and the reference/audit can be restored;
successful upload commands alone are insufficient.

Variants 2 (organized intermediate) and 3 (cleaned intermediate) remain future
work. No source extraction, renaming, repair, deduplication, splitting, training,
or intermediate production occurs here. Original files stay unchanged.

## Inputs and reading route

Follow the normal entry path, then read
[data_artifacts.md](../docs/data_artifacts.md),
[documentation.md](../docs/documentation.md), and the relevant outcomes of
[Task 025](025_capture_legacy_reference.md#outcome-2026-10-26) and
[Task 026](026_inventory_originals_and_cleanup_provenance.md#outcome-2026-10-26).
Use [cleanup_provenance.md](../docs/cleanup_provenance.md) only to interpret scope;
do not repeat the inventory or require another delivery-completeness decision.

The project layout treats the current dataset and later datasets equally, using
the same delivery/variant/release rules and no mandatory baseline dataset. Follow
[the add-region flow](../docs/data_artifacts.md#adding-regions-and-combined-datasets).
Task 027 still transfers only the five inputs below; do not create or ingest a
new regional dataset as part of this backup.

The user selected the three ZIPs as sufficient raw sources for the current
dataset. CA/BC folder copies are optional later preservation, not required here. Exact
input allowlist, with last-observed sizes to recheck during execution:

| Input under `/Volumes/x10pro/kelpseg/` | Scope | Observed bytes |
|---|---|---:|
| `zip_archive/ca_data.zip` | One unchanged raw archive | 15,966,180,991 |
| `zip_archive/extra_data.zip` | One unchanged raw archive | 1,092,258,731 |
| `zip_archive/Planet8bSR_BC_Labelled.zip` | One unchanged raw archive | 5,092,052,520 |
| `references/legacy_ps8b_v1/` | Entire closed package, including checkpoint, inputs, predictions, previews, producers, manifests and checksum sidecar | 807,971,035 (53 files) |
| `audits/task026_originals_v1/` | Entire closed package, including reports, traces, previews, producers, fixtures, manifests and checksum sidecar | 10,750,297 (45 files) |

The observed total is 101 payload files / 22,969,213,574 bytes, before new backup
receipts and the small transfer fixture. Reconcile actual identities; never
force these counts by omitting unexpected files. The reference manifest SHA-256
is `3ab76901075e84a35dee2d37b0d30f0c9366a0a9f0d435213b671277bf88def8`;
the audit manifest SHA-256 is
`71859fa0d2b091348603f05b9fc3b6684154d13041d6d692eb157b3410d4ed20`.
Reverify both package sidecars and standalone verifiers before transfer.

`rclone` and remote `kelp-box` are configured locally. Configuration is not
proof of authentication, permissions, capacity, or a working backup. Do not
display configuration files, tokens, or authenticated request/response dumps.

## Expected outputs and layout

Create a fresh local receipt workspace at
`/Volumes/x10pro/kelpseg/backups/task027_raw_reference_audit_v1/` during execution.
Do not put backup receipts in either immutable source package. Proposed remote
project root: `kelp-box:kelpseg`. Use the existing intended project folder if
provided; if the configured remote already points at it, do not nest another
`kelpseg` folder. Record the resolved account, folder ID/link, and root before
any remote writes. This is proposed organization, not an existing remote claim.

```text
<project-root>/
  data/1_raw/ca_bc_sources_v1/      # ordinary source bundle: three original ZIPs
  references/legacy_ps8b_v1/       # exact original package-relative tree
  audits/task026_originals_v1/     # exact original package-relative tree
  transfers/task027_raw_reference_audit_v1/
    checks/roundtrip_v1/           # small, explicitly inventoried fixture
    receipts/                     # catalogs, verification receipt, restore recipe
    completion.json               # published last; no self-referential hashes
```

Local receipt outputs:

| File/directory | Required content |
|---|---|
| `backup_plan.json` | Exact source/destination mappings, project folder ID/link, three payload prefixes, receipt prefix, input identities, verification and resume rules |
| `preflight.json` | Tool version, resolved account/target, permissions, capacity/upload-limit evidence, largest file, available restore space, and unknowns |
| `payload_manifest.csv`, `payload.sha256`, `payload.sha1` | One row/checksum per payload: original path, project-relative destination, size, SHA-256 identity, SHA-1 transfer checksum, source metadata, package/catalog identity and hash provenance |
| `raw_files.txt` | Only the three allowed ZIP basenames, for filtered copying |
| `roundtrip/`, `roundtrip.json` | Small fixture, clean downloaded copy, before/after hashes, remote identities and command results |
| `remote_inventory.json` | Actual listings for only the three mapped payload prefixes, with provider identities/versions, sizes and native SHA-1 hashes or explicit missing-hash status |
| `fallback/` (only if needed) | Affected-file list, reason, fresh local check, streamed remote SHA-256 and diagnostic outcome |
| `restored/` | Fresh reference/audit downloads, kept separate from original packages |
| `verification.json` | Exact inventory/hash comparison, per-file verification method, restore results, source metadata changes, fallback reasons, failures and retries |
| `invocations.txt`, closed logs, `README.txt` | Exact commands and short restore/verification instructions; no credentials |
| `manifest.json` | Atomically published local completion only after remote completion has been read back and verified |

Copy the finalized payload catalog, checksum list, verification receipt and
restore recipe to the transfer's remote `receipts/`, and read them back to check
their hashes. Payloads remain in their project data/reference/audit locations;
the transfer receipt references them without making duplicate backup trees.
Keep payload and receipt inventories separate. Neither receipt hashing nor
completion hashing includes its own file; no circular checksum references.
Record additional small local producer/verifier files if needed, outside Git.

In Git, create a short `docs/box_backup.md` during execution with the actual
verified remote paths and copy/download/check recipes. Link it from the router
and artifact contract once it exists. Update this task and both queues at
closure; keep full transfer logs/inventories outside Git.

## Implementation contract

### 1. Freeze the plan and check actual Box constraints

- Mark In progress only when execution is requested. Recheck the five input
  roots, strict package inventories, and output/input path separation. Reject
  symlinks, missing inputs, duplicate destination paths, and unexpected package
  files; do not silently follow, repair, remove, or ignore them.
- Record local rclone version and resolved remote/account/project context using
  bounded read-only checks. Use the intended shared project folder when supplied,
  or create the proposed project folder during authorized execution. Confirm
  access to the three versioned payload prefixes and isolated transfer prefix.
  Reserve the later variant-2/3, chip/split and run locations from
  [the storage contract](../docs/data_artifacts.md#box-project-organization-and-upload-verification)
  without populating them now. Do not change sharing or
  account settings, reconnect an unrelated account, or inspect unrelated files.
- Establish account-specific maximum upload size and sufficient capacity for
  the declared backup. `rclone about --json` may help with quota but does not by
  itself establish a per-file limit. Obtain missing facts from authenticated
  provider metadata or actual account information; record their source/date.
  Missing/unsupported fields mean unknown, not unlimited. No tier-based guess.
- The largest current object is 15,966,180,991 bytes. If the account cannot
  accept it intact, or essential constraints cannot be established, stop before
  bulk copying and report the concrete limit/missing evidence with a proposed
  lossless transport alternative. This contract does not authorize substituting
  chunks, recompressing ZIPs, dropping an archive, or changing storage service.
- Check local free space for receipts, the small round trip, and complete fresh
  reference/audit restores. Default verification reads Box checksums, not all
  ZIP contents. Budget about 0.82 GB for package restores plus fixture/control
  files; if fallback is needed, stream only affected files without a second
  local ZIP copy. Record traffic/time estimates and actual fallback traffic.

### 2. Freeze source hashes and verify the small round trip

- Freeze a SHA-256 identity and SHA-1 transfer checksum for every payload. When
  no trusted dual-hash catalog exists, calculate both in one sequential read,
  recording size/mtime before and after. Reconcile package SHA-256 values with
  existing manifests/sidecars. Reuse an existing immutable-release catalog only
  with valid recorded identity/provenance; size/mtime alone is not enough. The
  three raw ZIPs currently need their initial catalog; do not hash them anew in
  several separate preflight/post-upload passes. Rclone's own transfer hashing
  may still read files; do not promise exactly one disk read overall.
  Do not unpack/test-decode ZIPs. The backup checks faithful transfer, not
  scientific validity or completeness of all historical deliveries.
- Produce sorted portable destination paths in the payload catalog. Keep image,
  label and archive names unchanged inside their source packages/ZIPs. Preserve
  raw delivery train/val names within archives as historical provenance only.
- Generate a tiny local fixture: a deterministic 2 MiB binary file, a short
  JSON file, and a nested filename containing spaces. Hash and inventory it.
  Upload only this fixture first, download it into a fresh local directory, and
  require exact paths, sizes, and SHA-256 equality. Record remote object IDs
  where available. Leave the fixture in the transfer's `checks/roundtrip_v1/`.
- Bulk payload copying may begin only after the account/size gates, frozen
  catalog, and verified round trip pass. Failure is evidence to resolve, not
  permission to skip this gate. A successful dry run is not a round trip.

### 3. Copy only the allowlisted payloads; make retries explicit

- Use direct rclone copies from the existing source roots to their mapped
  destination prefixes. Filter the raw ZIP folder with `raw_files.txt`; do not
  recursively upload `/Volumes/x10pro/kelpseg`. Copy every file in the two closed
  packages, retaining their package-relative paths exactly. Do not add control
  files inside those packages; their verifiers require exact inventories.
- Default to one file transfer at a time and modest checking concurrency.
  Record exact flags, exit codes, counts and bounded retry behavior. Use
  `--immutable` as a guard; it is not a substitute for content verification.
  Do not use `sync`, `move`, deletion/purge commands, or ignore-checksum options.
- Fresh versioned payload/transfer prefixes are the default; the shared project
  root may already exist. Check ownership and catalog identity for each payload
  prefix independently; do not infer that fixed reference/audit paths are empty.
  Before resuming a partial backup, verify
  its plan/catalog identity, unchanged local inputs, and existing remote bytes
  against the frozen catalog using native SHA-1/size/path checks, with affected
  readback fallback when needed. Existing identical objects can be reused; a
  conflicting object or ambiguous ownership must stop, never overwrite.
  Do not rely on `--ignore-existing`, equal size, or timestamps as identity.
- Reconcile remote listing rows before turning them into maps/sets. Reject
  duplicate relative paths and ambiguous provider identities rather than
  choosing one. Extra/missing payloads are failures, not silently excluded data.
  Do not delete unknown objects to make the comparison pass.
- Preserve completed-object receipts across interruptions. Rclone/backend
  behavior determines whether an incomplete large object can resume; do not
  promise byte-level upload continuation. Reattempting that object may be needed.

### 4. Verify native checksums; use readback fallback only when needed

- List only the three payload prefixes, then map their entries to project-relative
  paths and match the frozen catalog exactly. Other datasets elsewhere in the
  project are outside this transfer's scope; they are neither extra payloads
  nor targets for recursive hashing. Reject duplicate/missing/extra objects
  inside the declared prefixes, and require successful listings.
- Default: compare every object's valid **Box-reported SHA-1** (40 hexadecimal
  characters), size and path with the frozen local catalog, without `--download`.
  Require one checksum per expected object and record `provider_sha1_verified`;
  missing hashes are not successful size-only matches. Save the provider/object
  identity used. A
  successful `rclone copy --checksum` exit alone does not prove this comparison.
- Fallback: when a native checksum is missing or differs, record the affected
  paths/reason, recheck local identity and retry remote metadata within a bounded
  attempt budget, then stream **those files only** with
  `rclone hashsum SHA256 ... --download`. Require equality with
  the frozen SHA-256 values. If native SHA-1 disagreed but readback matches,
  retain that discrepancy and its resolution; never erase the failed check.
  Record successful fallback as `readback_sha256_verified`. Actual byte mismatch
  remains a failure to resolve, not permission to overwrite a conflicting object.
- Whole-backup download verification is optional for an explicit deep audit or
  a documented issue affecting the whole scope. Do not run it routinely merely
  because SHA-256 is in the local manifest. This provider-checksum default and
  affected-file fallback apply to future dataset uploads too.
- Download the entire reference and audit packages into fresh `restored/`
  subdirectories. Recheck hashes and run each restored `verify_package.py` with
  isolated imports, without the original package/data roots or legacy imports.
  Use `uv run --no-sync` for the existing Python environment. No model inference
  or archive extraction is needed to establish restoration.
- Compare source metadata and catalog identity before/after transfer. Rehash
  affected inputs if metadata changes or catalog trust is lost; freeze a new
  plan if content changed. Do not reread all 23 GB solely for a routine second
  local hash pass. State whether source stability used metadata/catalog checks
  or fresh byte hashes; do not claim a fresh post-upload hash audit when skipped.
  Preserve source contents/permissions and original package manifests. Record
  actual algorithms and comparisons, not just an unqualified "verified" label.

### 5. Publish completion after verification

Finalize the verification receipt and short restore recipe, copy them and the
payload catalog/checksums to the transfer's `receipts/`, then read those control files
back and compare hashes. Freeze the uploaded logs before hashing/copying them.

Prepare the transfer's remote `completion.json` referencing the finalized
catalog and receipt hashes, payload counts/bytes, destination identity and
verification results.
Upload it last and read it back to check identity/content. A locally prepared
marker or partially uploaded folder does not establish remote completion.
Only then publish local `manifest.json` atomically and mark Task 027 Complete.
If transfer/verification fails, retain partial receipts and record the exact
remaining action; never label the complete scope backed up prematurely.

## Planned direct-command recipe (not executed)

The following uses the proposed paths. During execution, replace them only with
the resolved recorded plan; verify installed help before relying on flags.
Build catalogs/receipts with ordinary Python if needed; no new repository
`scripts/` workflow, sync framework, package implementation, or daemon.

```bash
TASK027_SOURCE='/Volumes/x10pro/kelpseg'
TASK027_RECEIPTS='/Volumes/x10pro/kelpseg/backups/task027_raw_reference_audit_v1'
TASK027_PROJECT='kelp-box:kelpseg'
TASK027_TRANSFER="$TASK027_PROJECT/transfers/task027_raw_reference_audit_v1"

# Read-only preflight; quota output alone does not establish upload-size limits.
rclone version
rclone lsd kelp-box:
rclone about kelp-box: --json
rclone backend features kelp-box:

# Run these copies only after the verified small round trip and frozen plan.
rclone copy "$TASK027_SOURCE/zip_archive" "$TASK027_PROJECT/data/1_raw/ca_bc_sources_v1" --files-from-raw "$TASK027_RECEIPTS/raw_files.txt" --immutable --checksum --transfers 1 --checkers 2
rclone copy "$TASK027_SOURCE/references/legacy_ps8b_v1" "$TASK027_PROJECT/references/legacy_ps8b_v1" --immutable --checksum --transfers 1 --checkers 2
rclone copy "$TASK027_SOURCE/audits/task026_originals_v1" "$TASK027_PROJECT/audits/task026_originals_v1" --immutable --checksum --transfers 1 --checkers 2

# Capture each scoped listing; compare path, Size and native SHA-1 with the catalog.
# No --download: these requests read provider metadata, not the full ZIP contents.
rclone lsjson "$TASK027_PROJECT/data/1_raw/ca_bc_sources_v1" --recursive --files-only --hash-type SHA1
rclone lsjson "$TASK027_PROJECT/references/legacy_ps8b_v1" --recursive --files-only --hash-type SHA1
rclone lsjson "$TASK027_PROJECT/audits/task026_originals_v1" --recursive --files-only --hash-type SHA1

# Fallback template ONLY for a recorded affected file; select its exact remote path.
# rclone hashsum SHA256 '<affected-remote-file>' --download --output-file '<fresh-fallback-report>'
```

Document exact fixture upload/download, restored-package, receipt publication,
and completion read-back commands when executed. `--checksum` can fall back
when a backend lacks a usable hash; explicit native-checksum comparison or the
affected-file SHA-256 fallback is required. Do not claim a provider SHA-1 check
is a remote SHA-256 readback. Record the actual algorithm and method per file.
The standing policy for subsequent uploads is owned by
[data_artifacts.md](../docs/data_artifacts.md#box-project-organization-and-upload-verification).

## User decisions required

None for this contract update. A specific parent/project folder link is useful
if the user has one; otherwise use the proposed `kelpseg` project folder under
the intended UCLA Box root during execution. Do not require the user to create
it manually. Default to the stated five inputs and fresh versioned destinations.
Clarify only if the intended
account/project root is ambiguous, authorization needs interactive repair, or
actual upload/capacity constraints prevent the approved unchanged-file scope.
Present concrete evidence and a reviewable proposed alternative first; do not
ask for repeated permission to perform already authorized execution steps.

This request authorizes updating the contract/policy and proposing organization
only. No Box connection, folder creation, round trip, upload, account change, or
large hashing job is started now. Leave status Pending until execution is requested.

## Plan/spec before execution

Write `backup_plan.json` before remote writes. Record root mappings, raw-file
allowlist, package identities, project folder ID/link, three payload prefixes,
receipt prefix, counts/bytes, account-limit evidence, collision/retry rules,
dual-hash catalog origin/reuse, native-checksum and affected-file fallback
commands, local space/traffic budget, and completion criteria. No payload or
fixture upload before that plan exists.
Record deviations and unresolved constraints here without broadening to other
datasets or starting Task 028. Useful independent read-only checks can be
delegated; one coordinator owns remote writes and completion publication.

## Smoke and validation

- Reopen catalog/plan/receipts; reject missing/duplicate identities, source/output
  overlaps, conflicting resumed objects, and incomplete scopes. Small disposable
  fixtures can verify checksum comparison, duplicate detection, and refusal
  behavior if a local helper is implemented; do not test failures on originals.
- Pass the real small upload/download round trip before any bulk transfer.
- Require exact coverage within the three payload prefixes and native SHA-1
  matches for every file, or successful affected-file SHA-256 fallback. Record
  the actual method and zero unexplained missing/differing/duplicate/extra files.
- Restore and independently verify both closed packages. Verify source
  metadata/catalog stability, rehash only affected/untrusted inputs, and state
  the evidence level; no routine full post-upload raw-ZIP rehash is required.
- If a checksum helper is implemented, use small fixtures to demonstrate that
  absent/malformed hashes cannot pass as size-only checks, a mismatch invokes
  affected-file fallback, and unrelated project datasets are not in the scan.
- Read back receipt/control hashes and the last-published completion marker.
- Verify Markdown links/diffs and run `git diff --check`. No training tests are
  required for a transfer/docs-only task. If tracked source changes become
  necessary, run focused checks and required Ruff via `uv run --no-sync`.

## Acceptance criteria

- The account/destination and actual size/capacity constraints are recorded;
  all three ZIPs fit intact, or the task remains explicitly incomplete.
- Project organization uses the same delivery/dataset/release namespaces for
  current and future datasets. The current CA/BC source bundle is an ordinary
  named input; it is not an implicit parent or required member of later
  collections. Do not populate future dataset folders during this transfer.
- All three original ZIPs plus both entire immutable packages exist on Box at
  unambiguous recorded project paths, with exact payload inventories and native
  SHA-1/size matches or recorded affected-file SHA-256 readback verification.
  No file passes with size-only evidence; normal verification does not require
  all ZIPs to be downloaded again.
- A small round trip and complete fresh reference/audit restores pass. Inputs
  remain unchanged; manifests, recipes and completion support later recovery
  without relying on the original absolute source paths or training registry.
- The uploaded control files and final completion marker are verified before
  local completion and task closure. No partial backup is described as complete.
- Routine upload/download uses documented ordinary rclone copies and one local
  path/plan specification; generation rules/short docs stay in Git, receipts and
  payloads outside. No custom storage service or permanent scripts workflow.
- Variants 2/3, experimental splits, and the reusable researcher walkthrough
  remain deferred. Stop before Task 028 or any data-preparation implementation.

## Non-goals

Backing up duplicate CA/BC trees or old derived collections;
extracting/repacking/chunking archives; deduplicating/renaming/cleaning inputs;
producing intermediates or split assignments; authenticating other services;
changing sharing/account settings; training, inference, or a storage framework.

## Outcome template

Record actual remote account/project root and prefix; source/catalog hashes;
size/capacity evidence; file/byte counts; small round-trip and remote checksum
results (actual native algorithm and per-file fallback scope, not an implied
full download); restored-package checks; source stability evidence; completion
marker/receipt identities; durable external outputs; changed repo docs;
failures/retries and remaining work.
Mark Complete only for the full declared verified backup. Exact next action:
scope Task 028's installable package/researcher-guide/removal contract, retaining
variants 2/3 and their preparation rules for the later bounded tasks. Stop.
