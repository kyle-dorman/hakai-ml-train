# Box backup and recovery

Use `kelp-box:kelpseg`, [Box folder 431635691068](https://app.box.com/folder/431635691068),
under the UCLA account `kdorman90@ucla.edu`. Use an account with access to that
project folder. Credentials stay outside Git, logs and manifests.

## Connect Box on a local machine

Install rclone first and confirm `rclone version` succeeds. On a Mac or other
machine with a browser, sign in to UCLA Box through UCLA's login flow in that
browser and confirm you can open the project folder. Then run:

```bash
rclone config
```

Create a remote named `kelp-box`, choose storage type `box`, and keep the default
client ID/secret unless the lab supplies its own. Select ordinary browser OAuth,
not service-account authentication, and answer yes to automatic browser
authentication. Complete the authorization in the browser/profile already
signed in to UCLA Box, then finish saving the remote in the terminal. No SSH
tunnel is needed when rclone and the browser run on the same machine.

Check access before copying data:

```bash
rclone lsd kelp-box:kelpseg/data
```

For a headless remote GPU host, use the
[SSH tunnel authentication procedure](gpu_setup.md#7-log-in-to-box--on-the-instance-with-your-macs-browser)
instead. Do not copy credentials into recipes or the repository.

## Restore an existing release

Choose an absent local destination and copy only the artifact family needed.
The [CA/BC release reference](reference/ca_bc_release.md) provides exact raw,
organized, cleaned, chip, split and tiny-input locations, trusted verification
values, and complete restore commands. It also preserves recovery instructions
for the legacy checkpoint reference and original-data audit.

Use the [tiny walkthrough](quickstart.md) for a small initial download. Full
canonical chips need about 65.6 GB. Source-TIFF workflows also need the cleaned
release. Preserve project-relative folders and point machine settings at the
restored root; absolute original-host paths in provenance are not dependencies.

## Back up new artifacts

Use ordinary versioned folders and explicit copies. Select a new release/run
folder; preserve previous outputs. Do not use deletion-propagating sync.
The example below assumes `SOURCE` is complete and the destination is new:

```bash
(
  set -e
  SOURCE='/path/to/completed/run'
  DEST='kelp-box:kelpseg/runs/my-new-run'
  rclone copy "$SOURCE" "$DEST" --immutable --size-only --ignore-checksum --transfers 1 --checkers 2
  rclone check "$SOURCE" "$DEST" --size-only
)
```

Before a large transfer on a new machine, test a small representative copy and
restore. After publication, compare relative paths, counts and sizes and open a
bounded restored sample with the intended loader. Keep resolved recipes, model
metadata and needed manifests beside their outputs. Record what was checked;
path/size checks are not checksum verification. Stop on failure and use a fresh
destination for a new attempt.

Older organized/cleaned releases already contain hashes and verification
records; their recovery recipes retain those checks. New work does not add
hashing, authentication catalogs or receipt systems. General layout and
immutability rules belong to [artifact policy](data_artifacts.md).
