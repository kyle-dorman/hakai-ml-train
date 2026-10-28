# Documentation index

Start with `AGENTS.md`, then [todo.md](todo.md) and the selected task under
[tasks](../tasks/README.md).

The current work rebuilds this fork for Planet 8/4/3-band binary kelp
segmentation. The installed package provides CLI/path checks, byte-preserving
organization, quick/full directory checks, shared cleanup, and native-band
chipping with optional labels, source-level baseline/LORO assignments and
manifest-based window selection. A NumPy loader selects bands and pads partial
edges. Preparation writes run once into a fresh output and stop on failure.
Retained legacy Planet implementations support the ongoing replacement;
model workflows arrive through later numbered tasks. Tasks 000–023 describe the
preceding completed PS8B study.

## Read by task

- [quickstart.md](quickstart.md): researcher setup, available commands, paths,
  output/errors, and reusable Python functions.
- [product.md](product.md): research scope, experiments, scientific boundaries.
- [architecture.md](architecture.md): current-to-target pipeline, identity,
  splitting, prediction and metric contracts.
- [box_backup.md](box_backup.md): verified Box paths and recovery recipes.
- [data_artifacts.md](data_artifacts.md): storage, original-data uncertainty,
  cleanup provenance, Box, and Git policy.
- [cleanup_provenance.md](cleanup_provenance.md): observed collection lineage,
  recorded cleanup decisions, and unresolved data semantics from Task 026.
- [experiments.md](experiments.md): initialization, resume, W&B, checkpoints,
  comparisons, and local/remote validation.
- [documentation.md](documentation.md): read before changing durable docs.
- [todo.md](todo.md): current task, next action, and ordered roadmap.
- [backlog.md](backlog.md): optional unselected ideas.
- [tasks/README.md](../tasks/README.md): task contracts and historical records.

Read only the documents needed for the selected task. Current-facing documents
own decisions; detailed historical runs and outcomes remain in numbered tasks.
