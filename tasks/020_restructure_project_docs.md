# Task 020: Restructure active project documentation

Status: Complete

## Goal

Replace the duplicated catch-all instruction files and generic multi-dataset
README with a routed documentation structure focused on the current
PlanetScope 8-band baseline/LORO project.

## Outcome

Rewrote `AGENTS.md` as a concise operating contract and reduced `CLAUDE.md` to a
pointer. Replaced the generic README with current PS8B orientation. Added routed
product, architecture, artifact, experiment, documentation, TODO, and backlog
docs under `docs/`. Updated the task router and W&B task.

The active W&B destination is now documented as:

```text
entity: kdorman90-ucla
project: kelpseg
```

The new suite's W&B group remains intentionally undecided until Task 013.

## Validation

- Verify all relative Markdown links resolve.
- Search active docs for stale non-PS8B workflow and incorrect W&B guidance.
- Run `git diff --check`.

## Next action

Task 001: build the raw merge organizer.
