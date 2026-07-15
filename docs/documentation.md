# Documentation guide

For navigation, start with `docs/index.md`. This file owns documentation
process and source-of-truth boundaries. Read it before adding, moving, deleting,
or substantially rewriting durable docs.

## Ownership

- `AGENTS.md`: concise repository operating contract and entry path.
- `README.md`: human-facing current-project orientation and setup.
- `docs/index.md`: read/skip router; it does not duplicate owned content.
- `docs/product.md`: research purpose, claim boundary, success criteria, and
  non-goals.
- `docs/architecture.md`: active technical workflow and data/evaluation
  contracts.
- `docs/data_artifacts.md`: storage roots, git policy, artifact families, and
  provenance.
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
- Do not promote legacy non-PS8B surfaces back into active docs unless a task
  explicitly changes the project boundary.

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
- Are legacy non-PS8B examples absent from active documentation?
- Do all relative Markdown links resolve?
- Does `git diff --check` pass?
