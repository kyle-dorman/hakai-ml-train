# Box backup and recovery

The verified project root is `kelp-box:kelpseg`, [Box folder 431635691068](https://app.box.com/folder/431635691068), under the UCLA account `kdorman90@ucla.edu`. Task 027 backed up the current delivery as an ordinary raw source bundle:

- `data/1_raw/ca_bc_sources_v1/`: the three unchanged source ZIPs.
- `references/legacy_ps8b_v1/`: complete legacy reference package.
- `audits/task026_originals_v1/`: complete original-data audit package.
- `transfers/task027_raw_reference_audit_v1/`: round-trip fixture, receipts, and completion marker.

To restore into a new local project-shaped directory, choose a fresh `DEST` and run:

```bash
DEST='/path/to/fresh/kelpseg-restore'
rclone copy kelp-box:kelpseg/data/1_raw/ca_bc_sources_v1 "$DEST/data/1_raw/ca_bc_sources_v1"
rclone copy kelp-box:kelpseg/references/legacy_ps8b_v1 "$DEST/references/legacy_ps8b_v1"
rclone copy kelp-box:kelpseg/audits/task026_originals_v1 "$DEST/audits/task026_originals_v1"
rclone copy kelp-box:kelpseg/transfers/task027_raw_reference_audit_v1/receipts "$DEST/receipts"
(cd "$DEST" && shasum -a 256 -c receipts/payload.sha256)
```

The full checksum check reads the restored ZIPs. For the two packages, also run their standalone verifiers from an isolated working directory using this repository's environment:

```bash
cd /private/tmp
uv run --no-sync --project /path/to/hakai-ml-train python -I "$DEST/references/legacy_ps8b_v1/verify_package.py"
uv run --no-sync --project /path/to/hakai-ml-train python -I "$DEST/audits/task026_originals_v1/verify_package.py"
```

For future transfers, follow the [artifact verification policy](data_artifacts.md#box-project-organization-and-upload-verification): compare Box SHA-1, size, and paths with a local catalog; stream a SHA-256 readback only for affected files when native hashes are absent or disagree. Avoid overwriting versioned releases. Task 027's full evidence and completion identity are in its [outcome](../tasks/027_verify_box_and_back_up_raw_reference_audit.md#outcome-2026-10-27).
