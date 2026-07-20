# Task 009A: Repair metadata-aware nodata statistics and repackage

Status: Pending

Depends on: Tasks 002–009

Execution: Local code, canonical-artifact repair, and archive replacement.

## Abstract

Repair a confirmed nodata-definition defect before the canonical archive is
transferred. The current raw-merge, chipper, validators, analysis, and filter
logic treat a pixel as nodata only when every retained image band equals zero.
Five California source TIFFs instead declare `65535` as nodata. Their NPZ image
and label arrays are already usable—the image values remain `uint16` and the
corresponding labels are generally remapped to `-100`—but their manifest
nodata counts are wrong and the 50% filter did not remove every qualifying
chip.

Fix the code to derive nodata from each source TIFF, repair existing artifacts
in place without re-chipping unchanged arrays, re-run every downstream
selection and summary affected by the corrected counts, and package a new v2
archive. Preserve the v1 evidence and explicitly document the user-approved
exception that this repair patches existing manifests rather than reproducing
the full raw-merge and chipping run.

This task ends with a clean-extraction-verified local v2 archive. It does not
transfer data or materialize experimental folds.

## Confirmed defect and audit baseline

The affected source TIFFs are:

```text
003_20210613_175056_2264.tif
003_20220413_182313_227b.tif
003_20220424_173818_2427.tif
003_20220510_173816_241f.tif
004_20210525_174950_2463.tif
```

`ca_003` is San Diego and `ca_004` is Palos Verdes. All five TIFFs declare
`65535` as nodata. The initial direct NPZ audit found 173 active chips from
these sources: 105 contain at least one all-band-`65535` pixel, and 35 contain
more than 50% all-band-`65535` pixels. Every one of the 173 active manifest
rows currently reports 0% nodata. For
`003_20220424_173818_2427`, 8 of 24 active chips exceed 50% metadata-declared
nodata and one is 100% nodata.

Treat these as pre-task observations to reproduce, not acceptance counts to
force if the full audit finds additional metadata cases or a different valid
mask interpretation.

## Inputs

- Canonical merged TIFFs and labels under
  `/Volumes/x10pro/kelpseg/merged_all_regions_v1`
- Canonical chip root
  `/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1`
- Task 007 filter history and the active 50% threshold
- Task 008 training selection and summaries
- Task 009 v1 archive, inventory, and checksum sidecar
- `src/prepare/make_chip_dataset.py`
- `src/prepare/remove_tiles_with_nodata_areas.py`
- `src/prepare/remove_bg_only_tiles.py`
- `scripts/merge_planet8b_regions.py`
- `scripts/validate_planet8b_raw_merge.py`
- `scripts/validate_chip_dataset.py`
- `scripts/analyze_planet8b_nodata.py`
- `scripts/package_planet8b_dataset.py`
- `docs/architecture.md` and `docs/data_artifacts.md`

## User decisions required

No blocking choice remains. The user approved these decisions on 2026-07-20:

1. Read the nodata value from each source TIFF rather than assuming zero.
2. Avoid a full re-chip when existing NPZ image and label arrays are correct.
   Recompute and patch the affected per-chip statistics instead.
3. Re-run all downstream artifacts whose membership or summaries depend on
   those statistics.
4. Reuse previously computed individual-chip hashes when packaging, subject to
   an explicit auditable trust check, rather than hashing every unchanged NPZ
   again.

Default the repaired archive to
`planet8b_all_regions_1024_512_v2.zip`. Never overwrite or silently relabel the
Task 009 v1 archive.

## Nodata contract

- Read the source image's declared per-band nodata values through Rasterio.
- For the current single-valued TIFFs, a source pixel is nodata when every
  retained band equals its declared nodata value.
- Record enough source nodata metadata in portable raster/chip metadata for
  later NPZ validation without reopening the original TIFF.
- Fail explicitly on missing nodata metadata, inconsistent per-band nodata
  declarations, NaN nodata, or another representation that the implementation
  has not deliberately specified. Do not silently fall back to zero.
- Compare using the stored source dtype. Do not cast `65535` through `uint8` or
  otherwise wrap it to another value.
- Keep label ignore handling separate from image nodata counting. Verify, but
  do not assume, that corrected nodata pixels are `-100` in the existing NPZ
  labels.

## Plan/spec requirement

Before mutating the canonical root, write a concise repair plan in this task's
outcome workspace or a small generated JSON/Markdown artifact. It must list:

- every file to patch, regenerate, preserve, remove, or replace;
- the pre-repair hashes and row counts of all mutable manifests;
- the exact five-source audit and any additional source metadata anomalies;
- the transaction/rollback boundary for manifest and chip membership changes;
- which v1 archive hashes will be reused and the evidence required for reuse.

Run a report-only pass and inspect it before apply mode.

## Implementation contract

### 1. Correct forward code and tests

- Centralize source-aware nodata-mask construction so the raw merge, chipper,
  validators, and analysis utilities use one documented definition.
- Replace hard-coded all-band-zero checks in the active PS8B path.
- Make future chip manifests retain the source nodata value or equivalent
  portable metadata needed to validate NPZs without raw TIFF access.
- Update focused fixtures to cover both `nodata=0` and `nodata=65535`, including
  a `uint16` case that would fail if cast incorrectly.
- Keep legacy non-PS8B behavior outside this task unless shared code must change
  to make the active path correct.

### 2. Audit source TIFFs and existing NPZ content

- Enumerate nodata metadata for all 369 merged source TIFFs and confirm the
  complete set of distinct declarations.
- Reproduce the five-source findings above and report chip counts at 0%,
  `(0, 50]`, and `>50%` corrected nodata.
- Verify existing NPZ image arrays exactly match their source windows for the
  five affected TIFFs and that label arrays have `-100` wherever the source
  nodata mask requires it.
- If image or label content is wrong, stop before patching and record the
  smallest required re-chipping scope. Do not silently widen this task to a
  full re-chip.

### 3. Patch statistics without re-chipping

- Add a dedicated restartable repair command with `--dry-run` and explicit
  `--apply`; do not use an ad hoc notebook or manual CSV edit.
- Recompute `class_0_pixel_count`, `class_1_pixel_count`,
  `ignore_pixel_count`, `nodata_pixel_count`, `nodata_pct`, and
  `total_pixel_count` from the existing NPZs for every chip belonging to an
  affected source. Patch only values that differ.
- Update the five affected per-source fragment manifests and the current
  canonical manifest consistently. Update source-level count summaries and
  portable source nodata metadata.
- Preserve immutable snapshots of pre-repair manifests and a row-level repair
  manifest containing old/new values, source nodata metadata, reason, and
  content hashes.
- Do not rewrite any retained NPZ file. Prove this with an operation log and
  unchanged size/hash evidence for a stratified sample, plus the trusted v1
  inventory for the full retained set.

### 4. Reapply dependent policies and summaries

- Keep the already approved universal threshold at 50%; this task corrects its
  input statistics and does not select a new threshold.
- Transactionally remove newly identified chips where corrected
  `nodata_pct > 50`. Preserve a v2 removal manifest that distinguishes original
  Task 007 removals from Task 009A additions.
- Regenerate active-manifest summaries, nodata distributions/filter reports,
  chip QA, and any compact Task 006/007 evidence whose values changed.
- Re-run the Task 008 `exclude_all` training selector against repaired active
  membership and regenerate its global, region, and source-TIFF summaries.
- Reconcile active plus all removal records to the original 6,003-chip
  inventory without duplicate or missing chip IDs.
- Do not change `planet8b_temporal_image_splits.csv`; verify its source join
  after membership repair.

### 5. Build a v2 archive with hash reuse

- Extend the packaging workflow with an explicit prior-inventory/hash-reuse
  option. The v1 inventory is the source of reused individual-NPZ hashes.
- Reuse a chip hash only when its relative path and byte size match the trusted
  v1 inventory and the repair transaction confirms that the NPZ was not
  rewritten. Hash every new or changed file normally.
- Record the trusted v1 archive SHA-256, v1 inventory SHA-256, reuse criteria,
  reused count, newly hashed count, and rejected-reuse count in v2 metadata.
- Drop removed chips and stale manifests from v2. Include repaired manifests,
  v2 filter/background evidence, and the row-level repair report.
- NPZ members may remain ZIP-stored as in v1 so rebuilding does not waste time
  recompressing already-compressed NPZ data.
- Compute a new SHA-256 for the complete v2 ZIP and write a new sidecar. The
  outer archive checksum cannot be reused.
- Perform clean extraction and structural/inventory validation. Do not repeat
  SHA-256 calculation for every unchanged extracted NPZ; use ZIP CRC/integrity,
  path/size reconciliation, the trusted reused inventory, and a stratified
  fresh NPZ hash sample. Fully hash all changed manifests and metadata.

## Planned interfaces and artifacts

Prefer these names unless implementation planning identifies a clearer
repo-native location:

```text
scripts/repair_planet8b_nodata_metadata.py
tests/test_repair_planet8b_nodata_metadata.py

/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1/
  repair_history/metadata_nodata_v2/
    pre_repair_active_manifest.csv
    repaired_rows.csv
    added_removals.csv
    repair_metadata.json
    repair.log

/Volumes/x10pro/kelpseg/archives/
  planet8b_all_regions_1024_512_v2.zip
  planet8b_all_regions_1024_512_v2.zip.sha256
```

The implementation may consolidate these files with an existing transactional
history abstraction, but it must not overwrite Task 007 or Task 009 evidence.

## Smoke test

Build a tiny fixture containing two `uint16` source TIFFs: one declares zero as
nodata and one declares 65535. Create existing NPZ/manifest rows with the old
zero-only statistics, then prove that:

1. dry-run reports only the incorrect rows and does not mutate files;
2. apply patches counts without rewriting NPZ bytes;
3. corrected `>50%` membership is removed transactionally;
4. background selection is regenerated from repaired membership;
5. v2 packaging reuses an unchanged NPZ hash, freshly hashes changed metadata,
   rejects reuse after a path/size mismatch, and verifies after extraction.

## Validation

- All 369 source TIFF nodata declarations are inventoried with no silent
  fallback.
- Corrected nodata counts independently match source-window masks for every
  affected chip.
- Existing NPZ image/label content is unchanged and valid for the five sources.
- Active plus removed chip IDs reconcile exactly to the original 6,003 chips.
- No active chip exceeds 50% metadata-declared nodata.
- Training selection joins one-to-one to repaired active membership.
- The v2 archive contains exactly the repaired active chip set and portable
  metadata, with no v1 manifest accidentally retained as current truth.
- Hash-reuse provenance is complete and all freshly hashed files verify.
- A clean extraction passes the packaging verifier without raw TIFF access.
- Run focused tests, the full repository test suite, Ruff format/lint over
  changed Python surfaces, pre-commit when appropriate, and `git diff --check`.

## Acceptance criteria

- The active code no longer assumes that PS8B nodata equals zero.
- The canonical collection is repaired without a full raw merge or full
  re-chip, and no retained NPZ is rewritten.
- Corrected counts and newly removed chips are recorded globally, by region,
  and by source TIFF.
- Task 008 selection artifacts are regenerated and reconciled.
- A versioned, clean-extraction-verified v2 archive and checksum exist locally.
- The v1 archive remains preserved but is explicitly marked superseded and is
  not used by Task 010.
- Task 010 needs only remote connection/destination details and the v2 archive.

## Non-goals

- Do not transfer the archive remotely.
- Do not materialize baseline or LORO views.
- Do not reselect the 50% threshold.
- Do not re-chip unaffected sources or rebuild the complete raw merge.
- Do not rewrite NPZ arrays merely to normalize `65535` to zero.
- Do not delete or overwrite the v1 archive or its historical evidence.

## Outcome template

Record changed repository files; source nodata inventory; reproduced and final
affected-source/chip counts; manifest fields repaired; added removals; final
active, removal, and training-selection counts; proof that retained NPZs were
not rewritten; transaction and rollback evidence; v2 archive path, bytes,
SHA-256, member counts, and clean-extraction result; reused versus freshly
computed hash counts and trust assumptions; validation commands; unresolved
issues; and the exact Task 010 transfer command template.
