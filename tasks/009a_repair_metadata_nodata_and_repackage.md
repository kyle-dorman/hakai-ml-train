# Task 009A: Repair metadata-aware nodata statistics and repackage

Status: Complete

Depends on: Tasks 002–009

Execution: Local code, canonical-artifact repair, and archive replacement.

## Abstract

Repair a confirmed nodata-definition defect before the canonical archive is
transferred. The current raw-merge, chipper, validators, analysis, and filter
logic treat a pixel as nodata only when every retained image band equals zero.
Five California source TIFFs instead declare `65535` as nodata. Their manifest
nodata counts are wrong and the 50% filter did not remove every qualifying
chip. A complete California image-nodata-versus-label-nodata audit then found
one false-negative label defect in `004_20210525_174950_2463`: 5,203 source
pixels are image nodata but not label class `3`. The same audit established
that the 30 British Columbia raw source labels contain only classes `0` and
`1`, so their merged labels can be deterministically rebuilt with
image-derived class `3` nodata before their chips are regenerated.

Fix the code to derive nodata from each source TIFF, repair the one affected
California derived label and all 30 BC derived labels, re-chip only those 31
source fragments, patch statistics for the other affected California sources
without rewriting their NPZs, re-run every dependent selection and summary,
and package a new v2 archive. Preserve the v1 evidence and explicitly document
that this is a scoped label/chip repair rather than a complete raw-merge or
369-source chipping rerun.

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

The full California raster audit used image nodata as truth and label class `3`
as prediction. Only five of 339 TIFFs had any false negative or false positive:

| Source TIFF | Effective nodata | FP | FN | Decision |
|---|---:|---:|---:|---|
| `004_20210525_174950_2463` | 65535 | 0 | 5,203 | Repair label nodata and re-chip source. |
| `008_20201010_180745_2304` | 0 | 21,471 | 0 | Accept minimal edge-only FP. |
| `008_20201116_185541_2416` | 0 | 486 | 0 | Accept minimal edge-only FP. |
| `009_20201109_180527_2212` | 0 | 358 | 0 | Accept minimal edge-only FP. |
| `008_20201110_185814_2405` | 0 | 153 | 0 | Accept minimal edge-only FP. |

For `004_20210525_174950_2463`, the 5,203 unique false-negative source pixels
are stored label class `2` and appear as 5,190 non-ignore pixels across four
currently active overlapping chips. The source has 77 original chip windows.

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
5. When all retained bands lack nodata metadata, use the explicit effective
   nodata value `0`. This was approved on 2026-07-20 after a full blockwise
   audit confirmed that none of the 325 metadata-missing TIFFs contains the
   value `65535`; the least-nodata visual check showed all-band-zero pixels
   confined to image-edge areas.
6. Repair `004_20210525_174950_2463` so every image-nodata pixel is derived
   label class `3`, then regenerate its complete 77-chip source fragment. Do
   not repair the four California FP-only edge discrepancies listed above.
7. Apply the same image-derived nodata labeling to all 30 BC merged labels.
   BC image nodata uses the same declared-or-effective-zero contract; set label
   class `3` exactly where the image nodata mask is true, retain classes `0`
   and `1` elsewhere, then regenerate every BC source fragment.
8. Hash every rewritten NPZ freshly for v2. Reuse v1 NPZ hashes only for
   unchanged retained chips whose relative path and byte size still match.

Default the repaired archive to
`planet8b_all_regions_1024_512_v2.zip`. Never overwrite or silently relabel the
Task 009 v1 archive.

## Nodata contract

- Read the source image's declared per-band nodata values through Rasterio.
- For the current single-valued TIFFs, a source pixel is nodata when every
  retained band equals its declared nodata value.
- Record enough source nodata metadata in portable raster/chip metadata for
  later NPZ validation without reopening the original TIFF.
- When all retained bands have missing nodata metadata, record that status and
  use the approved explicit effective nodata value `0`. Fail on partially
  missing or inconsistent per-band declarations, NaN nodata, or another
  representation that the implementation has not deliberately specified.
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

## Updated execution steps (2026-07-20)

This ordered list is the resumable execution path after context compaction:

1. Finish forward-code and fixture coverage for declared nodata, explicit
   missing-metadata effective nodata `0`, derived label class `3`, scoped
   source-fragment re-chipping, and mixed fresh/reused archive hashes.
2. Run a report-only label repair over the one selected California source and
   all 30 BC sources. Record pre-repair label hashes, TP/FP/FN/TN, pixels that
   would change, source-fragment chip counts, and every affected downstream
   artifact. Refuse apply if any non-nodata BC label value is outside `{0, 1}`.
3. Transactionally repair the 31 derived merged label TIFFs. For California,
   change only the 5,203 image-nodata false negatives to class `3`. For BC,
   write class `3` exactly at image nodata while preserving `0`/`1` elsewhere.
   Preserve immutable pre-repair label evidence and validate post-repair masks.
4. Re-chip the complete deterministic source fragment for each repaired label:
   one 77-window California fragment plus all 30 BC fragments. Do not re-chip
   the other 338 sources. Stage replacements, verify image/source windows and
   label remapping, then atomically replace scoped NPZs and fragment manifests.
5. Recompute metadata-aware statistics for all five `nodata=65535` California
   sources. Rebuild the consolidated original 6,003-row inventory from source
   fragments and reapply the approved `nodata_pct > 50` removal policy.
6. Regenerate active-manifest QA, source/global/region summaries, Task 008
   `exclude_all` training selection, and the California plus BC nodata-label
   confusion audit. Reconcile active plus original and new removals exactly to
   6,003 chip IDs and verify the temporal split join is unchanged.
7. Build `planet8b_all_regions_1024_512_v2.zip`. Freshly hash every rewritten
   California/BC NPZ and all changed metadata; reuse v1 hashes only for
   unchanged retained NPZs after path/size and no-rewrite checks.
8. Clean-extract v2 and verify ZIP integrity, inventory/path/size joins,
   freshly hashed members, a stratified fresh sample of reused hashes, repaired
   nodata masks/counts, and portable operation without raw TIFF access.
9. Record the final outcome, update the current contract docs and task queue,
   mark Task 009A complete, and stop before Task 010.

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

### 3. Repair derived labels and re-chip only affected source fragments

- Add report-only and explicit apply modes for derived-label repair; no manual
  raster or NPZ edits.
- For `004_20210525_174950_2463`, set derived label class `3` wherever all eight
  image bands equal declared nodata `65535`. Preserve every non-nodata label
  pixel and prove the resulting image-versus-label nodata FN count is zero.
- For all 30 BC sources, require pre-repair labels to use only classes `0` and
  `1`, set class `3` exactly at the image nodata mask, and preserve `0`/`1`
  elsewhere. Require zero BC nodata-label FP and FN after repair.
- Preserve pre-repair label hashes and either immutable label snapshots or a
  deterministic row/pixel-level repair record sufficient to roll back.
- Re-chip the complete 77-window California source fragment and every BC source
  fragment through the corrected chipper. Stage and validate all replacements
  before atomically changing canonical files.
- Record every rewritten NPZ path, old/new byte size and SHA-256, fragment hash,
  source ID, and reason. No source outside these 31 may have an NPZ rewritten.

### 4. Patch remaining statistics without re-chipping

- Add a dedicated restartable repair command with `--dry-run` and explicit
  `--apply`; do not use an ad hoc notebook or manual CSV edit.
- Recompute `class_0_pixel_count`, `class_1_pixel_count`,
  `ignore_pixel_count`, `nodata_pixel_count`, `nodata_pct`, and
  `total_pixel_count` from the existing NPZs for every chip belonging to an
  affected source. Patch only values that differ.
- Update the other four affected California per-source fragment manifests and
  the consolidated canonical manifest consistently. Use the regenerated
  California/BC fragments as source of truth for their rows. Update
  source-level count summaries and portable source nodata metadata.
- Preserve immutable snapshots of pre-repair manifests and a row-level repair
  manifest containing old/new values, source nodata metadata, reason, and
  content hashes.
- Prove every NPZ outside the explicitly re-chipped 31-source scope is unchanged
  with an operation log, trusted v1 inventory reconciliation, and stratified
  size/hash evidence.

### 5. Reapply dependent policies and summaries

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

### 6. Build a v2 archive with mixed fresh hashes and hash reuse

- Extend the packaging workflow with an explicit prior-inventory/hash-reuse
  option. The v1 inventory is the source of reused individual-NPZ hashes.
- Reuse a chip hash only when its relative path and byte size match the trusted
  v1 inventory and the repair transaction confirms that the NPZ was not
  rewritten. Freshly hash every NPZ regenerated from the California or BC
  repaired-label scope, even if its compressed byte size happens to match v1.
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

Build a tiny fixture containing California-style and BC-style `uint16` sources,
including missing nodata metadata with approved effective value zero and a
declared 65535 source. Create one California nodata false negative and one BC
0/1-only label, plus existing NPZ/manifest rows with stale statistics, then
prove that:

1. dry-run reports exact label changes, re-chip scope, and incorrect rows without
   mutation;
2. apply repairs derived labels and regenerates only selected source fragments;
3. corrected `>50%` membership is removed transactionally;
4. background selection is regenerated from repaired membership;
5. v2 packaging freshly hashes rewritten NPZs, reuses an unchanged NPZ hash,
   rejects reuse after a path/size mismatch, and verifies after extraction.

## Validation

- All 369 source TIFF nodata declarations are inventoried with no silent
  fallback.
- Corrected nodata counts independently match source-window masks for every
  affected chip.
- The repaired California source has zero image-nodata false negatives; the
  four accepted edge-only California FP cases remain explicitly reported.
- All 30 BC derived labels use class `3` exactly at image nodata and have zero
  nodata-label FP/FN.
- Exactly the selected one California plus 30 BC source fragments are re-chipped;
  all other NPZ content remains unchanged.
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
  re-chip; NPZ rewrites are limited to the selected one California plus 30 BC
  source fragments and are fully recorded.
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
- Do not re-chip sources outside `004_20210525_174950_2463` and the 30 BC
  sources or rebuild the complete raw merge.
- Do not rewrite NPZ arrays merely to normalize `65535` to zero.
- Do not delete or overwrite the v1 archive or its historical evidence.

## Outcome template

Record changed repository files; source nodata inventory; reproduced and final
affected-source/chip counts; California and BC label confusion before/after;
derived-label changes; re-chipped source/NPZ inventory; manifest fields
repaired; added removals; final active, removal, and training-selection counts;
proof that out-of-scope NPZs were not rewritten; transaction and rollback
evidence; v2 archive path, bytes,
SHA-256, member counts, and clean-extraction result; reused versus freshly
computed hash counts and trust assumptions; validation commands; unresolved
issues; and the exact Task 010 transfer command template.

## Outcome

Completed locally on 2026-07-20. No remote transfer, fold materialization, or
training work was started.

### Implementation

- Added `src/prepare/nodata.py` as the shared declared/effective nodata
  contract and replaced zero-only checks across the active merge, chipping,
  analysis, validation, and packaging paths.
- Added `scripts/repair_planet8b_nodata_metadata.py` with report-only and
  explicit apply modes. Apply stages labels and complete source fragments,
  quarantines canonical targets, atomically replaces scoped artifacts, and
  restores labels, NPZs, and manifests together on failure.
- The repair rebuilds BC merged labels from the original raw `{0,1}` labels on
  the image grid, fills outside raw-label coverage as class `0`, and assigns
  class `3` exactly at image nodata. This corrected a stale pre-task statement:
  nine existing BC merged labels contained class `3` outside image nodata from
  the former outside-coverage rule, although all 30 raw BC labels were exactly
  `{0,1}` as required.
- Extended v2 packaging to trust the checksum-verified v1 inventory only for
  unchanged retained NPZs with matching archive path and byte size. Every
  retained NPZ recorded in `rewritten_npz_inventory.csv` is forced through a
  fresh SHA-256 calculation even if its size matches v1.
- Added focused coverage for declared `0`, declared `65535`, missing-metadata
  effective `0`, California false-negative repair, BC raw-label rebuilding,
  and forced-fresh archive hashing.

Changed repository files are the nodata/repair/packaging source and tests,
active validators and merge/chipper utilities, this task and queue routing,
and the current README/architecture/artifact documentation. Large generated
artifacts remain outside git.

### Repair evidence and counts

The durable repair root is:

```text
/Volumes/x10pro/kelpseg/chips_all_regions_1024_512_v1/
  repair_history/metadata_nodata_v2
```

It contains the pre-mutation plan and hashes, active-manifest snapshot, 42
mutable-manifest snapshots, 31 immutable pre-repair label TIFFs, source nodata
inventory, pre/post label audits, row-level statistic repairs, rewritten-NPZ
inventory, added and combined removals, summaries, log, and completion
metadata.

- Source inventory: 369 TIFFs; 44 have declared nodata metadata and 325 use the
  approved explicit effective value `0`. Effective values are 364 zero and the
  five known California `65535` sources; no additional nonzero case appeared.
- The metadata-aware five-source audit reproduced 173 formerly active chips:
  68 at 0%, 70 in `(0, 50]`, and 35 above 50% nodata.
- Pre-repair selected-label confusion across the 31-source scope was
  TP=124,679,847, FP=12,871,065, FN=5,203. The California source owned all
  5,203 false negatives; the BC false positives came from the superseded
  outside-coverage assignment. Post-repair FP=0 and FN=0 for all 30 BC labels,
  and the repaired California source has FN=0. The four accepted California
  edge-only false-positive sources were not rewritten.
- Exactly 31 complete source fragments were re-chipped: the 77-window
  California source plus all 30 BC sources, totaling 724 regenerated NPZs.
  The final active collection retains 482 of those rewritten NPZs. No source
  outside that scope had NPZ content rewritten.
- Corrected statistics added 35 removals: 1 each from
  `003_20210613_175056_2264`, `003_20220413_182313_227b`, and
  `003_20220510_173816_241f`; 8 from `003_20220424_173818_2427`; and 24 from
  `004_20210525_174950_2463`.
- Active plus combined removals reconcile exactly to all 6,003 chip IDs:
  4,602 active and 1,401 removed. The active set has 367 source TIFFs, all 12
  regions, 47 true-size partial chips, 44,854,174,488 compressed NPZ bytes,
  and no chip above 50% nodata. Its manifest SHA-256 is
  `b8b14d8db7910fe7de69803a669ce8922b07fa401a0d99999019f5cc1f12886f`.
- The refreshed `exclude_all` selection joins all 4,602 active chips one-to-one:
  3,210 positive chips are selected, while 440 clean-background and 952 mixed
  background/nodata chips are excluded. The training selection and summary
  SHA-256 values are
  `200db4b41f84cacd00296b86f5cc50174368f568fa8540eb1c704567484b38fa`
  and
  `2531b1494f21cfcc54a6339a5517190bcf20a224f9dc64e3d72512e89f9fb0ce`.
- `planet8b_temporal_image_splits.csv` was not changed and still joins all 369
  source TIFF IDs exactly.

### V2 archive

```text
/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v2.zip
/Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v2.zip.sha256
```

- ZIP bytes: 44,859,496,084
- ZIP SHA-256:
  `1244ecfe2cc4cee624bb5661087f0126ea239367bda60efd823b4fcb9b7399db`
- Members: 4,624 total, including 4,602 NPZs and one 4,623-row inventory.
- Inventory SHA-256:
  `9e1e393229ba4bf22ab5b30bdf6756f3c9a4737c27ff67bb3d9e125e5830c408`
- Hash provenance: 4,120 unchanged NPZ hashes reused from v1; 482 rewritten
  retained NPZs rejected from reuse and freshly hashed; 21 manifest/metadata
  members freshly hashed. The trusted v1 archive and inventory hashes are
  `6640757c19d803a000834b34abdb20c71a5359e215e8edf08b4958123c4ab098`
  and
  `a07d8326a8b3946907aeb04c0fac042e714a7c226b96c24d6f93302c33f01fbc`.
- Clean extraction passed outer checksum, ZIP integrity, full path/size joins,
  all fresh-member hashes, a 74-chip fresh sample of reused hashes, portable
  manifest joins, and stratified NPZ validation without raw TIFF access. The
  temporary extraction and staging trees were removed after verification.
- The v1 archive and sidecar remain unchanged as historical evidence and are
  not the Task 010 transfer candidate.

### Validation

Successful validation included:

```text
uv run pytest: 53 passed
uv run ruff format --check <14 changed Python files>: passed
uv run ruff check <14 changed Python files>: passed
uv run pre-commit run --files <Task 009A change set>: passed
git diff --check
scripts/validate_planet8b_raw_merge.py: 369/369 raster pairs passed
scripts/validate_chip_dataset.py: 4,602 manifest rows matched 4,602 NPZs
scripts/package_planet8b_dataset.py verify: clean extraction passed
```

Repository-wide `ruff format --check .` and `ruff check .` remain blocked by
two unrelated pre-existing notebook issues in
`notebooks/create_skema_aux_files.ipynb` and
`notebooks/export_skema_models_onnx.ipynb`; Task 009A did not modify those
legacy notebooks. An all-files pre-commit pass otherwise reached and passed
its Ruff hooks, but the end-of-file hook attempted unrelated normalization of
`run.sh` and `planet8b_image_splits.csv`; those two files were restored exactly
before the clean change-set-only pre-commit pass. No unresolved data or archive
issue remains.

### Next action

Start Task 010 only after the user supplies the remote alias/user, upload
directory, extracted data parent, compatibility-path choice, and repo
branch/commit. Use this command shape with the v2 files only:

```bash
rsync --partial --progress \
  /Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v2.zip \
  /Volumes/x10pro/kelpseg/archives/planet8b_all_regions_1024_512_v2.zip.sha256 \
  <user>@<host>:<remote-staging>/
```

Then verify the remote checksum, extract under the approved data parent, and
run the Task 009A archive verifier before recording the canonical remote root.
