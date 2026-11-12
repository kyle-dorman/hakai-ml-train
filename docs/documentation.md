# Documentation guide

For navigation, start with `docs/index.md`. This file owns documentation
process and source-of-truth boundaries. Read it before adding, moving, deleting,
or substantially rewriting durable docs.

## Ownership

- `AGENTS.md`: concise repository operating contract and entry path.
- `README.md`: human-facing current-project orientation and setup.
- `docs/quickstart.md`: one sequential tiny workflow from installation through
  preparation, training, copied-model inference and labeled reporting.
- `docs/guides/preparation.md`: detailed input schemas, paths, preparation,
  split/window selection and pixel statistics.
- `docs/guides/training.md`: reusable training settings, loss/model options,
  initialization, portable models and completed-epoch resume.
- `docs/guides/prediction_reporting.md`: prediction/report commands, outputs,
  interpretation and errors.
- `docs/guides/diagnostics.md`: augmentation, shoreline and temporal diagnostics.
- `docs/reference/ca_bc_release.md`: release-specific locations, inventories,
  restoration commands and trusted historical verification references.
- `docs/box_backup.md`: general current restore and backup operations.
- `docs/history.md`: compact completed-study and recovery router.
- Historical recipe references: preserved launch instructions, explicitly
  historical; numbered tasks still own results and scientific qualifications.
- `docs/gpu_setup.md`: remote GPU access, bootstrap, authentication and data
  staging; distinguish locally checked instructions from remote validation.
- `docs/index.md`: read/skip router; it does not duplicate owned content.
- `docs/product.md`: research purpose, claim boundary, success criteria, and
  non-goals.
- `docs/architecture.md`: active technical workflow, interfaces and implementation
  boundaries.
- `docs/paper_methods.md`: concise paper-oriented study summary; detailed
  implementation evidence remains in methods and study records.
- `docs/methods.md`: scientific explanation of implemented preparation, isolation,
  model inputs/selection, reconstruction, scoring and coverage.
- `docs/data_artifacts.md`: storage roots, git policy, artifact families, and
  provenance.
- `docs/cleanup_provenance.md`: audited collection lineage, historical cleanup
  decisions, and remaining evidence limits; detailed traces stay external.
- `docs/experiments.md`: W&B, local run registry, checkpoint, prediction, and
  comparison contracts.
- `docs/todo.md`: current status, open queue, and next action.
- `docs/backlog.md`: unselected future ideas only.
- `tasks/README.md`: task-file shape and handoff rules.
- Numbered task files: implementation scope, acceptance, detailed evidence, and
  outcome for one agent-sized unit.

## Write rules

- Put current task order and status in `docs/todo.md`.
- Put detailed implementation evidence in the numbered task file.
- Put future unselected ideas in `docs/backlog.md`.
- Keep product, architecture, artifact, and experiment docs as current
  contracts, not chronological logs.
- Replace stale text; do not append caveats to a conflicting old instruction.
- Prefer a short pointer to the owner doc over duplicated content.
- Update routers and direct links in the same change when paths move.
- Use the current Planet 8/4/3-band binary kelp scope. Retire unrelated
  legacy examples as their implementations are removed. Distinguish planned
  replacement commands and policies from behavior already implemented.
- Keep the quickstart sequential and small. Extend focused guides for advanced
  options; do not append completed-study narratives to operating instructions.
  At handoff, record where a researcher needs help and fix those gaps.
- Methods owns detailed split isolation, nodata/ignore, padding, reconstruction
  and coverage explanations; guides retain operating instructions and cautions.
  LORO-specific normalization provenance and claim qualifications belong in its
  task/write-up. Historical audit questions do not become current blockers.

## Task outcomes

When a task closes:

1. Change its status and add a concise `## Outcome` section.
2. Record changed files, durable external artifacts, validation, unresolved
   issues, and exact next action.
3. Update `docs/todo.md` with only the compact status and next-task change.
4. Update a contract doc only if the task changed that contract.

Do not paste long logs or full artifact inventories into `docs/todo.md`.

## Docs-change checklist

- Does every statement belong in this file rather than another owner doc?
- Do `AGENTS.md`, `README.md`, `docs/index.md`, and `docs/todo.md` agree?
- Does the task queue point to the same current/next task?
- Are W&B entity/project statements consistent with `docs/experiments.md`?
- Are unrelated legacy examples absent and planned features labeled clearly?
- Do all relative Markdown links resolve?
- Does `git diff --check` pass?
