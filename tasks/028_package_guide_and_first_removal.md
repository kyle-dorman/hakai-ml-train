# Task 028: Installable package, researcher guide, and first removal pass

Status: Complete — 2026-10-27.

Depends on: Tasks 025–026. Task 027 may continue independently; preserve its
shared environment and transfer inputs throughout concurrent implementation.

Execution: Local code, packaging, synthetic CPU checks, and documentation.
Use a separate task-specific environment while Task 027 runs. This task does
not change original data, transfer processes, or backup status.

## Abstract

Establish the small installable `kelpseg` package and researcher entry point
before adding replacement workflows. Supply working setup/path checks, a short
guide, automated correctness checks, and an explicit first removal of unrelated
applications. Keep the working Planet implementations and their useful tests
until their own replacements land. This is a foundation task, not a wholesale
namespace migration or an implementation of preparation/training/inference.

## Inputs and reading route

Read the normal entry documents, then
[architecture.md](../docs/architecture.md),
[product.md](../docs/product.md),
[documentation.md](../docs/documentation.md), and the storage/Git and local-root
sections of [data_artifacts.md](../docs/data_artifacts.md).
Read [experiments.md](../docs/experiments.md) for output conventions; do not
change historical run/checkpoint identities.

Use `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.gitignore`,
`README.md`, retained source/configs/tests, and the completed outcomes of
[025](025_capture_legacy_reference.md),
[026](026_inventory_originals_and_cleanup_provenance.md), and
[027](027_verify_box_and_back_up_raw_reference_audit.md).
Do not repeat the data audit or restore/download large data for this task.

Observed starting constraints, to recheck before editing:

- The project has no build backend or installed command; its lock entry is
  virtual. The legacy implementation imports as `src.*`.
- Pytest injects both the checkout and `scripts/` into its import path. Passing
  those tests alone cannot establish installation correctness. There is no CI.
- Some retained imports rely on transitive dependencies. The chipper imports
  TorchGeo; the Planet model/diagnostic tests still need the legacy ML stack.
- Task 027 uses the current environment for standalone package verifiers.
  Its pending upload does not authorize changing that environment underneath it.

## Expected outputs

| Location | Deliverable |
|---|---|
| `pyproject.toml`, `uv.lock`, `.python-version` | Python 3.12, `uv_build`, installed `kelpseg` command, explicit retained dependencies, reproducible lock |
| `src/kelpseg/{__init__,__main__,paths}.py`, `src/kelpseg/cli/{__init__,paths}.py` | Small package, Typer root and separate command handler, reusable machine-path loading and read-only checks |
| `configs/paths.example.toml`, `.gitignore` | Copyable path settings and ignored `paths.local.toml` |
| `tests/test_package_cli.py`, `tests/test_paths.py` | Focused checks for actual interface behavior and invalid inputs |
| `.github/workflows/checks.yml` | Frozen Python 3.12 setup, CPU fixture tests, packaging smoke, Ruff and hygiene checks |
| `README.md`, `docs/quickstart.md` | Current setup and short researcher guide, with working commands distinguished from future workflows |
| `docs/index.md`, `docs/documentation.md`, `docs/architecture.md` | Guide routing/ownership and accurate package-versus-legacy status |
| Explicit source/config/dependency removals below | Retired unrelated applications without discarding Planet correctness coverage |
| This task and both queues | Outcome, validation, limitations, and exact Task 029A handoff |

Build outputs, temporary installation environments, and test artifacts stay
ignored/disposable. No durable data artifact or Box write is expected.

## Implementation contract

### 1. Freeze the bounded implementation plan

Recheck Task 027's outcome and checkout changes before mutation. Preserve other
work. Mark this task In progress and align the queue only when implementation
is selected. Record a short file/removal/dependency/check plan here first;
resolve ordinary implementation choices without another approval gate.

Use distribution name `kelpseg`, import name `kelpseg`, and command `kelpseg`.
Retain version `0.1.0` unless an actual packaging conflict requires otherwise.
Use Python `>=3.12,<3.13` and a bounded `uv_build` backend requirement, resolved
and recorded during implementation. Preserve the simple frozen setup command.
Do not upgrade the entire ML stack merely to create the package.

Keep runtime dependencies limited to the installed package's actual imports
(Typer initially). Put retained checkout-only ML/geospatial dependencies in a
`legacy` dependency group, default-enabled alongside `dev`, so ordinary frozen
setup still runs retained tests. Later tasks promote dependencies into runtime
as their installed workflows arrive. Verify runtime-only wheel installation
separately from the full checkout/test environment.

### 2. Build a real, small package and command

- Package only `src/kelpseg/` into the wheel. Do not ship the legacy `src.*`
  namespace, `scripts/`, tests, notebooks, external data, or checkout-specific
  configuration as runtime requirements. Keep legacy code in the repository
  temporarily; this task does not satisfy the final no-`scripts/` gate.
- Use Typer for argument parsing, help, and command registration, with ordinary
  workflow functions and Python's TOML/path facilities underneath. Declare
  Typer as a direct runtime dependency and resolve a compatible version during
  implementation. No plugin registry, recipe inheritance, or class-path
  interface.
- Register the installed command in `[project.scripts]` as
  `kelpseg = "kelpseg.cli:app"`. Keep `cli/__init__.py` to the root Typer app,
  version/help handling, and explicit command registration; put the path-check
  handler in `cli/paths.py`. Add other handler modules only as their workflows
  arrive. Do not build a single expanding parser/dispatch file.
- Implement `uv run kelpseg --help`, `uv run kelpseg --version`, and
  `uv run kelpseg check-paths --paths paths.local.toml`. These are the primary
  researcher recipes. Support the installed command directly and
  `python -m kelpseg` through the same Typer app.
- Keep command handlers thin: accept typed options, call reusable functions,
  and present useful results/errors. Machine-path loading/checking belongs in
  `kelpseg.paths`; later preparation/training/prediction work belongs in its
  own workflow modules. Those functions must be callable from notebooks and
  tests without Typer command/context objects. Import heavy workflow code
  inside the relevant handler so help/version remain lightweight.
- Reusable functions return typed settings/results and raise ordinary package
  exceptions; they never print or exit. Only the Typer handlers format results
  or errors. Successful commands return 0; expected settings/path problems
  return nonzero with an actionable stderr message and no traceback.
- Keep most workflow settings in recipe files rather than duplicating every
  setting as a flag. The approved future command style is
  `uv run kelpseg train --recipe <recipe-file>`; it is not implemented here.
  Later tasks define their small set of explicit recipe/path/output options.
- Help, version, and path checks must work without eager ML/geospatial imports,
  model downloads, W&B login, Box access, or a mounted research data volume.
  Unknown commands/options fail with a concise corrective message.
- Do not register placeholder preparation, train, predict, evaluate, or LORO
  commands. Their task contracts define and implement them later.

### 3. Establish machine paths and output conventions

The example TOML contains one `[paths]` table with `data_root` and `runs_root`.
Keep the existing data-root meaning: the artifact root, normally
`/Volumes/x10pro/kelpseg`, containing data/reference/audit families. A runs root
may be beneath it. Do not require a flat or disjoint storage hierarchy.

Researchers copy the example to ignored `paths.local.toml` and edit these two
ordinary strings. Accept absolute paths, `~`, and paths relative to the TOML's
directory; resolve independently of the invoking working directory. Reject
unknown tables/keys, missing/empty/non-string values, and malformed TOML with
the filename/key and a useful correction. No arbitrary environment expansion,
automatic drive discovery, cloud credentials, or machine-specific tracked file.
The required `--paths` option selects exactly one settings file; do not search
parent directories or silently discover/fall back to another file. Keep the
documented placement `kelpseg check-paths --paths <file>`.

`check-paths` prints the resolved settings file and roots and checks whether
they are existing directories. Missing roots or file-valued paths fail clearly;
the guide tells the researcher how to create/select their intended directories.
The command never creates directories, changes files, scans a dataset, or claims
to validate write permissions, dataset contents, band order, or a Box backup.
Later workflow tasks add their actual input/count/band/output preflight.

Document the future run layout under `<runs_root>/<run_id>/`: resolved settings
and input identities at the root, `checkpoints/`, `metrics/`, and `figures/`.
Label it as a convention for later commands, not an implemented run manager.
No new registry, automatic run allocator, or speculative training schema here.

### 4. Retire explicitly unrelated applications

Before removal, independently verify the saved Task 025 reference identity.
Task 027's remote restore verification remains owned by its running thread;
concurrent repository work must preserve its environment and payloads.
Do not regenerate reference predictions,
alter either closed package, or rerun legacy inference as a packaging check.

Remove this first-pass allowlist after checking live imports/config references:

- `src/models/hab_baseline.py`, `src/models/terratorch.py`,
  `src/models/eomt_dino.py`, and `src/deploy/`.
- `configs/eelgrass-rgb/`, `configs/mussels-rgb/`,
  `configs/mussels-goosenecks-rgb/`, `configs/kelp-rgb/`, and
  `configs/kelp-rgbi/`. The old RGB/RGBI configs are multiclass drone workflows,
  not the future Planet binary spectral recipes.
- `configs/kelp-ps8b/hab_baseline.yaml`, `unet_dofa_large.yaml`, and
  `upernet_dofa_large.yaml` in that same directory.
- The two SKEMA notebooks under `notebooks/`; retire
  `notebooks/visualize_augmentations.py` and `src/transforms.py` if the live
  reference check confirms their unrelated, unused status.
- In `src/data.py`, remove the unrelated `WebDataset`, `WebDataModule`,
  `MAEDataModule`, and `KOMBaselineRGBIDataModule` branches and their imports.
  Retain `NpzSegmentationDataset` and the Planet `DataModule`.
- Remove `src/models/llrd.py` and its optimizer branch only after confirming
  all `llrd_opts` consumers were removed with DOFA recipes.

Keep `src/models/smp.py`, the Planet loader, `trainer.py`, callbacks, losses,
schedulers, Planet preparation/evaluation/run-context code, relevant configs,
and existing focused tests until the responsible replacement tasks land.
Do not migrate all of them under `kelpseg` or create compatibility shims here.
Retain historical task records and tracked split tables; Task 032 owns moving
generated split artifacts out of Git. Historical links may name removed code;
active docs/configs must not advertise removed workflows.

Audit dependencies against what remains. Candidates to remove as direct
requirements are `habitat-mapper`, `terratorch`, `lightly`, `einops`, `datasets`,
`webdataset`, `onnx`, `onnxscript`, and `transformers`, plus unused `pydantic`/
`rich` and notebook tooling. Remove only when retained code has no direct need;
a transitive lock entry may legitimately remain. Explicitly declare retained
direct imports such as `numpy`, `rasterio`, `PyYAML`, the Lightning CLI's
`jsonargparse` support, and `shapely` if the footprint tool remains. Keep
TorchGeo while the old chipper imports it and Hugging Face Hub while SMP uses
its mixin. Avoid opportunistic rewrites to eliminate these dependencies early.

### 5. Start the researcher guide and automation

Keep `README.md` to orientation, setup, supported command summary, and links.
Create `docs/quickstart.md` for copyable setup, local paths, path checking,
expected output/errors, and verification instructions. Route it from the index
and assign its ownership in the documentation guide. Correct the README's
Task 027 status against its actual outcome at execution time.

Explain that prep, chipping, training, prediction, scoring, LORO, and add-region
recipes arrive with their implementation tasks. Link their owners; do not
invent runnable commands. Keep development task history out of everyday
instructions. The reusable real-data walkthrough still begins at Task 031.

Add one Python 3.12 CPU CI job using frozen dependencies, the package checks,
retained synthetic tests, Ruff, and pre-commit hygiene. Select a runner
compatible with the locked wheels; prefer a CPU setup that avoids CUDA
downloads and document the actual runner choice.
Initial dependency/tool installation may use network access; test execution
must not need external data, weights, credentials, a GPU, or online services.
Do not add a repository `scripts/` helper to run checks. Keep local and CI
recipes aligned. Do not claim a hosted CI pass until one has actually run.

## User decisions required

The user selected Typer on 2026-10-27, with the
`uv run kelpseg <command> --recipe ...` style, separate thin command handlers,
and reusable functions underneath. No further blocking decisions are required.
Package/command name, path-file shape, bounded removal list, and the existing
Python/uv direction are safe defaults within the authorized rebuild.
Training architecture options, band indices, cleanup recipes, split policies,
and GPU settings remain with their later tasks. Stop only for a concrete new
conflict that cannot be resolved inside this scope; do useful independent work
before presenting it.

The user initially authorized preparation only, then explicitly requested
implementation on 2026-10-27. Proceed in an isolated environment while Task 027
continues. Keep both statuses explicit and do not mark the backup complete.

## Smoke and validation during implementation

1. Record the pre-change test/lint baseline. Use the existing environment
   without syncing until Task 027 is finished. Separate unrelated failures
   from regressions; do not delete tests or relax checks to hide them.
2. After edits, regenerate the lock intentionally, run `uv lock --check`, then
   `uv sync --python 3.12 --frozen`. Ensure project installation is no longer
   virtual. Verify the installed uv build syntax before scripting checks.
3. Build wheel and sdist with `uv build`; inspect their contents. Build a wheel
   from the sdist as well, so a local checkout cannot hide missing sources.
4. Export frozen runtime requirements with all default groups excluded and
   without the editable project; install
   them and each built wheel in a separate fresh disposable Python 3.12
   environment, one environment per wheel.
   From an unrelated temporary directory with `PYTHONPATH` unset, verify
   `import kelpseg`, its installed file/version, `kelpseg --help`, `--version`,
   `python -m kelpseg`, and a real temporary path-check fixture. Test the wheel
   built from the sdist too. Do not use checkout imports or `--no-deps` alone
   as evidence of complete installability.
5. Test CLI failures and strict path loading, including malformed/unknown/
   missing settings, a missing directory, a file in place of a directory,
   spaces in paths, `~`, relative paths invoked from another directory, and
   no writes on either success or failure. A temporary fixture needs no drive.
   Include unreadable files, a directory supplied as the settings file, and
   invalid UTF-8. Verify expected errors use stderr and nonzero exit codes,
   successful commands return 0, and reusable functions neither print nor exit.
   Use Typer's CLI test runner for command behavior and directly test the
   reusable path functions without CLI context. Check that `check-paths`
   remains an explicit subcommand even while it is the only workflow command;
   help/version must not invoke it or import heavy workflow dependencies.
6. Run `uv run pytest` against the retained suite and new tests. Preserve
   nodata/ignore semantics, chip geometry and corrupt-resume refusal, source
   splits/joins, overlap-before-threshold, unique-pixel counts, coverage, and
   centered-padding coverage. Existing legacy test-during-fit diagnostics are
   historical behavior, not a requirement for the new training design.
7. Run `uv run ruff format --check .`, `uv run ruff check .`, and
   `uv run pre-commit run --all-files`. Pre-commit may fix files; review any
   changes and rerun affected checks. Check current links and
   `git diff --check`. Check retained imports/config references after removal.

New installed-package checks must run independently of pytest's legacy import
path additions. Keep those additions only while retained tests need them;
do not silently use them as proof that the new distribution works.

## Acceptance criteria

- A frozen Python 3.12 install, wheel, and sdist produce the actual installed
  `kelpseg` package and small command outside the checkout.
- Runtime-only installation excludes checkout-only legacy dependencies; normal
  frozen checkout setup includes the default `dev` and `legacy` groups.
- A researcher can copy/edit one path file and obtain useful resolved-path
  output/errors without Python edits, services, ML initialization, or data.
- The documented `uv run kelpseg ...` interface uses Typer with separate thin
  command handlers. Reusable workflow functions remain independent of Typer;
  recipe settings do not turn into an exhaustive flag interface.
- The first removal list and exclusively unused dependencies are retired;
  retained Planet code/tests still work. Remaining legacy debt is explicit.
- The short guide describes only available commands as runnable. The routine
  path/setup changes are simple; future workflows extend the same interface.
- Automated CPU fixtures and distribution checks exist and their local results
  are recorded, alongside lint/hygiene results and any preexisting failures.
  Installed-package evidence is separate from legacy checkout-test evidence.
- No original/package/backup is changed and no data processing, transfer,
  production training, or later numbered task starts.

## Non-goals

Implementing variants 2/3, chipping, splits, a new model/trainer, portable model
bundles, inference/scoring, LORO, cloud integration, a generic config framework,
full legacy migration, exact checkpoint reproduction, or the real walkthrough.

## Outcome template for implementation

Record changed/removed files and direct dependencies; package/build/lock
identities; exact frozen setup and installed-wheel/sdist results; retained
fixture checks and automation; guide/path/output simplicity check; remaining
legacy imports/dependencies/scripts; preexisting failures; external artifacts
(normally none); and unresolved issues. Mark Complete only after acceptance.

Exact next action: scope Task 029A's generic raw → organized implementation
contract using Task 026's provenance and declared dataset/region mappings.
Do not implement preparation in the Task 028 window. Update both queues and stop.

## Implementation plan — 2026-10-27

The user approved the three defaults above and explicitly selected execution.
Keep Task 027's existing `.venv`, external payloads, and transfer files intact;
use `/tmp/kelpseg-task028-env` for new installation and validation. The earlier
wait-for-backup implementation gate is replaced by this isolation and a fresh
local Task 025 verification; that backup still closes only in its own thread.

1. Verify the reference and record the existing test/lint baseline without
   syncing the shared environment.
2. Implement the small Typer/path package and focused tests; independently
   remove only the allowlisted unrelated code and imports.
3. Configure `uv_build`, runtime/dev/legacy dependency boundaries, resolve the
   lock with minimal version changes, and install into the isolated environment.
4. Add the short guide and CPU CI; verify package distributions outside the
   checkout and run the retained fixtures, lint, and pre-commit checks.
5. Review changes, record exact outcomes/limitations, update queues, and stop.

## Contract preparation outcome — 2026-10-27

Prepared this contract alongside Task 027 at the user's request. Independent
read-only audits checked packaging/automation and removal/import boundaries.
No implementation, dependency resolution, environment mutation, dataset read,
or transfer was performed. The preparation also links this contract from both
queues while preserving Task 027's active status and work.

Validation: reviewed the contract and queue changes; all 52 local Markdown
links across the three changed/new preparation documents resolve and code
fences balance. `git diff --check` passes. Independent packaging and removal
reviews found no blocking issues; the packaging review clarified separate
fresh installation environments for the checkout-built and sdist-built wheels.
No behavioral tests or lint were run for this docs-only preparation.

Changed preparation files: this task, `docs/todo.md`, and `tasks/README.md`.
Existing/concurrent Task 027 changes are preserved. External artifacts: none.
No unresolved user decision blocks implementation. Exact next action: after
Task 027 completes, select this task, reread the entry documents and contract,
record the short implementation plan, and execute its package/guide/removal
scope. Task 028 remains Pending execution; this preparation is complete.

The user subsequently selected Typer for the CLI. Updated this contract and
the researcher-interface section of `docs/architecture.md` with the installed
entry point, separate handlers, reusable functions, recipe-oriented command
style, and corresponding checks. This remains a documentation-only plan;
no Typer dependency was installed and implementation is still pending.
Validation: both updated documents' 10 local links resolve, code fences
balance, the argparse restriction is removed, and `git diff --check` passes.

## Outcome (2026-10-27)

Implemented the package/guide/removal scope after the user explicitly selected
execution. The approved defaults are part of the implementation: Typer with
separate thin handlers, reusable functions without CLI context, explicit path
selection, and separate runtime versus retained legacy dependencies.

Changed repository files:

- `src/kelpseg/`: installed root/module command, `check-paths`, strict TOML
  loading, frozen `PathSettings`, and ordinary `PathSettingsError` exceptions.
  Help/version/path checking avoid ML/geospatial imports; settings checks do
  not create directories, discover alternative settings, or touch data.
- `pyproject.toml`, `uv.lock`: `kelpseg` 0.1.0 using `uv_build`; Typer is the
  only direct runtime dependency. Default `dev`/`legacy` groups preserve simple
  frozen checkout setup and the retained tests. The dev group includes the
  build backend so source rebuilds can run offline with its locked version.
  Lock entries fell from 264 to 131, with no version changes among retained
  packages. Lightly/Einops remain transitive requirements of retained tooling.
- `tests/test_package_cli.py`, `tests/test_paths.py`,
  `tests/test_distribution.py`: settings/error/no-write/lightweight-import
  checks plus actual isolated installation of both distribution build paths.
- `.github/workflows/checks.yml`: frozen Python 3.12 setup on macOS 15 arm64,
  offline CPU fixture/distribution checks, Ruff, and pre-commit. The runner
  architecture is checked explicitly; hosted CI has not been run.
- `configs/paths.example.toml`, `.gitignore`, `README.md`,
  `docs/quickstart.md`, `docs/index.md`, `docs/documentation.md`, and
  `docs/architecture.md`: real setup/path recipes, reusable API, output/error
  explanations, planned run layout, guide routing, and accurate remaining
  workflow boundaries. No placeholder training/prediction command is exposed.
- Removed 38 allowlisted unrelated model/export/config/notebook/transform
  files. Pruned unrelated data-module and LLRD optimizer branches from
  `src/data.py` and `src/models/__init__.py`. All Planet correctness tests,
  relevant configs/scripts, trainer/model, and preparation/evaluation code
  remain until their replacement tasks.
- `planet8b_image_splits.csv` and `run.sh`: fixed preexisting line-ending/
  end-of-file hygiene found by pre-commit. Parsed split rows are identical;
  no assignment or shell command changed. Both queues and this task record
  the completed outcome; concurrent Task 027 changes are preserved.

Validation and evidence:

- Before editing, all 94 existing tests passed. The standalone Task 025
  verifier passed all 51 payload hashes and six input/label/prediction/preview
  checks, including repeat tolerance `1e-6`, without legacy repository imports.
  No inference was rerun and the reference package was not changed.
- Installed with `UV_PROJECT_ENVIRONMENT=/tmp/kelpseg-task028-env uv sync
  --python 3.12 --frozen`; `uv lock --check` passes. The original shared `.venv`
  has no new `kelpseg` installation and was never synchronized by this task.
- All **139 tests passed**: 138 retained/new path/CLI checks together, plus the
  independent offline distribution test. The one existing Rasterio
  `is_tiled` deprecation warning remains; it appeared in the baseline too.
- The distribution test builds wheel/sdist, rebuilds from the source archive
  in an unrelated directory using the locked installed dev build backend
  (`--no-build-isolation`), then installs each wheel in its own fresh environment
  with hash-locked runtime requirements. Imports resolve to those installations,
  legacy modules/dependencies are absent, dependency checks pass, and real
  help/version/module/path commands work outside the checkout.
- `uv build` also produced ignored `dist/kelpseg-0.1.0.tar.gz` and
  `dist/kelpseg-0.1.0-py3-none-any.whl`; the real installed command reports
  `kelpseg 0.1.0`. Ruff format/check and pre-commit pass, including explicit
  checks of new files that are not yet tracked. Current Markdown links/fences
  and `git diff --check` pass. Independent integration reviews found no
  remaining actionable issues after selecting the supported macOS 15 runner.

Simplicity check: routine setup changes two strings in one ignored TOML file;
CLI handlers only present reusable functions; the wheel installs without the
old model stack. Most future workflow settings remain recipe values. No
storage service, plugin registry, training schema, or compatibility shim was
introduced.

Durable external artifacts: none created or modified. Disposable environments
and test builds live outside the shared environment; distribution outputs are
ignored. Task 027 remains responsible for remote verification/backup closure.
Its original inputs, packages, transfer process, and environment were preserved.

Remaining limits: the replacement preparation/training/prediction workflows
are not implemented; retained `src.*`, `scripts/`, and legacy dependencies are
deliberate temporary debt. Mac CPU results do not establish CUDA compatibility
or production sizing. Hosted CI awaits a push/run; no remote pass is claimed.

Exact next action: select and scope Task 029A's generic raw → organized
implementation contract using Task 026's provenance and dataset/region mapping
requirements. Do not start that implementation here. Task 027 continues to its
own verification outcome in the upload thread. Stop this task.
