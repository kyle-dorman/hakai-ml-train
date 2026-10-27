# AGENTS.md

## Project

Rebuild this fork as a small, researcher-friendly toolkit for binary kelp
segmentation on Planet 8/4/3-band imagery. Scope: data preparation and chipping,
training, labeled evaluation, unlabeled inference, leave-one-region-out (LORO)
comparisons, and new-region transfer/fine tuning. A possible RGB DINOv3 variant
is a later controlled experiment, not a reason to retain unrelated frameworks.

Breaking APIs, config changes, and substantial code removal are authorized.
The known starting commit is `ac933fd667c2ddb445b8a622d8404387a2d056e2`.
Preserve a small legacy checkpoint reference before removing its implementation;
exact historical training reproduction is not required.

## Entry path and task size

Read this file, then `docs/index.md`, `docs/todo.md`, and the selected numbered
file under `tasks/`. Read only the owned docs routed for that task. For docs
changes, also read `docs/documentation.md`.

After compaction or in a new window, reread these entry documents and the active
task before editing. `tasks/README.md` owns task structure and handoffs.

Prefer small bounded tasks and independently scoped sub-agents. Do not start
multiple numbered tasks in one window. Close the selected task, record its
outcome and exact next action, update the queue, and stop. Roadmap slots become
full task contracts when selected; split them further when needed.

## Implementation direction

- Use Python 3.12, uv, a locked environment, and an installable
  `src/kelpseg/` package with `uv_build` as the target.
- The final repository has no `scripts/` directory. Expose a small installed
  command and short explicit recipes; do not move complexity into a framework.
- Favor plain functions, familiar geospatial/ML libraries, and actionable error
  messages for researchers with limited Python/ML experience. The current
  one-pass cleaner is an upper bound on file complexity, not a target to grow
  toward. Prefer smaller files that each do one clear job.
- Run steps in a plain sequence. If a step fails, stop; do not run the next step.
  Restart, resume, recovery and reuse of partial work are out of scope unless
  the user explicitly requests them. An agent-written task contract alone does
  not authorize those features.
- Group preparation code in `src/kelpseg/prepare/`. Keep researcher-maintained
  code explicit: plain functions, straightforward loops, one schema definition,
  and no clever shorthand or unnecessary layers.
- Show preparation progress by default in the CLI using standard Python logging:
  phases, current file, counts/bytes, and long-copy/hash updates. Explain rerun
  or resume decisions only for commands that support them.
- Remove unrelated dataset/model families and unused dependencies within the
  selected task. Preserve useful correctness tests as implementations change.
- Preserve user changes and unrelated work in a dirty checkout.
- Never describe a planned replacement command as already implemented.
- Apply the cross-task usability acceptance in `docs/todo.md`: simple settings,
  portable models, clear outputs/errors, and researcher instructions that grow
  with implementation. The reusable tiny walkthrough starts after dataset/Box
  establishment; focused correctness tests continue throughout.

## Scientific and data boundaries

- Keep region, acquisition date, source TIFF, band identity, and source window
  through preparation, splitting, prediction, and reporting.
- Never split chips from one source TIFF across train/validation/test. Keep
  acquisition-date groups intact for the temporal baseline; LORO holds out an
  entire region. Compare spectral variants on matching source assignments.
- Never select thresholds, recipes, or checkpoints using held-out test results.
- For overlap, reconstruct source probabilities before thresholding once. Score
  each covered source pixel once; aggregate TIFF confusion counts for metrics.
- Preserve explicit padding inversion, nodata, ignore index `-100`, and coverage
  reporting. Unlabeled prediction cannot depend on labels for alignment.
- Keep background-only chips in canonical data; express training exclusions
  separately. Evaluation remains representative of the declared input scope.
- Claims concern agreement with supplied labels on represented imagery.

Read `docs/product.md` for experiments and `docs/architecture.md` for pipeline
and metric boundaries.

## Storage and reconstruction

Never mutate original source imagery or labels. Inventory unknown original
collections and reconstruct/document cleanup before creating a replacement
cleaned release. Existing repaired data are historical evidence, not proof that
original membership or every cleaning decision is settled.

Large data, generated split assignments/manifests, checkpoints, predictions, and
reports belong outside Git. Keep generation rules, configs, tests, and human
cleanup documentation in Git. UCLA Box via rclone is the target transfer and
backup store; local roots and validation rules live in `docs/data_artifacts.md`.
Preparation is one pass: an interrupted run starts over into a fresh output.
There is no preparation restart, resume or partial-work reuse. Do not infer
recovery support from an expensive operation or add a general recovery system.
Refuse silent overwrites and duplicate or missing identities, and publish complete manifests
atomically.

## Local validation and remote work

Prepare and test as much as practical on the Mac before relocation. Use small
real examples and focused fixtures for preparation, band selection, loading,
forward/backward updates, validation, checkpoint save/load/resume, prediction,
evaluation, and transfer. Do not launch production training on the Mac. CUDA,
production batch sizing, and throughput checks remain GPU-host work.

Install with:

```bash
uv python install 3.12
uv sync --python 3.12 --frozen
```

For code changes, run relevant focused tests and:

```bash
uv run ruff format --check .
uv run ruff check .
```

Run `uv run pre-commit run --all-files` for broad code changes. There are existing
focused tests under `tests/`; lint is not behavioral proof. Record preexisting
unrelated failures explicitly. For docs-only work, inspect Markdown/diffs,
verify links, and run `git diff --check`.

## Experiments and handoffs

Keep W&B at `kdorman90-ucla/kelpseg` unless changed explicitly. The completed
`planet8b-loro-v3` suite is historical; new work must have distinct identities.
Read `docs/experiments.md` before changing run/checkpoint metadata.

Task outcomes record changed repo files, durable external artifacts,
validation, unresolved issues, and the exact next action. Detailed evidence
belongs in the task record, not this entry file or the current queue.
