# Researcher quickstart

The installed `kelpseg` command currently checks machine paths and reports
help/version information. Preparation, training, prediction, and evaluation
arrive in later tasks; see [the roadmap](todo.md). The retained legacy Planet
code is development/reference material, outside the installed package.

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
only Typer and its dependencies. New workflows will add their runtime needs as
they are implemented.

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

The required `--paths` option chooses exactly one file. There is no search for
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

## Later workflows and outputs

The selected future training style is
`uv run kelpseg train --recipe <recipe-file>`. It is not available yet.
Preparation, band/chip selection, training, prediction, scoring, LORO, and
adding a region will gain copyable recipes here when implemented. Most settings
will live in those recipes, with a few explicit command options.

Later run-producing commands will use `<runs_root>/<run_id>/`, with resolved
settings/input identities at the root and `checkpoints/`, `metrics/`, and
`figures/` underneath. This is an agreed layout, not an implemented run manager.
The reusable real-data walkthrough begins after Box and cleaned-data
establishment in Task 031. Current automated fixtures use temporary synthetic
data, requiring no Box/W&B login, GPU, model weights, or research-data download.

See [data and artifacts](data_artifacts.md) for storage/backup rules and
[experiments](experiments.md) for model, checkpoint, and run identity rules.
