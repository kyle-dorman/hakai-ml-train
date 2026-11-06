# Documentation index

Start with `AGENTS.md`, then [todo.md](todo.md) and the selected task under
[tasks](../tasks/README.md).

The current work rebuilds this fork for Planet 8/4/3-band binary kelp
segmentation. The installed package provides CLI/path checks, byte-preserving
organization, quick/full directory checks, shared cleanup, and native-band
chipping with optional labels, source-level baseline/LORO assignments and
manifest-based window selection with overlapping training and disjoint chip
validation/test. Streaming NumPy pixel statistics use selected training images
with an explicit optional cap. A NumPy loader selects bands and pads partial
edges. Isolated and combined augmentation previews use exact stock Albumentations
classes and capped normalization on training examples only. Full CA/BC chips, split controls and tiny v2 are published on Box; see
the [restore recipe](quickstart.md#restore-and-use-the-full-cabc-chip-release). Preparation writes run once into a fresh output and stop on failure.
Installed Python helpers provide manifest-selected training/validation tensors,
SegFormer B3 and loss/confusion functions. Retained legacy Planet implementations
support the ongoing replacement. The installed `train` command provides Lightning
training, validation, EMA, portable models and completed-epoch resume. Python
bundle loading predicts supplied image arrays; the
[installed tiny walkthrough](quickstart.md#tiny-v2-installed-training-walkthrough)
covers all four spectral recipes and both variants. The separate
[validation report](quickstart.md#post-training-validation-diagnostics) adds
post-training boundary/patch/probability diagnostics and false-color examples.
[Task 034](../tasks/034_gpu_machine_preparation_and_baseline_launch.md) is complete:
GPU setup, baseline comparisons and B0/B1 handoff are recorded; tiled/georeferenced
prediction is implemented by `predict` in [Task 035](../tasks/035_image_only_tiled_inference.md).
[Task 036](../tasks/036_shared_scoring_and_reports.md) implements `predict-chips`
and one shared `report` command for saved chip/TIFF predictions;
[Task 036B](../tasks/036b_temporal_error_analysis.md) adds `temporal-report`
for labeled percentage-change comparisons and dated summaries. Tasks 000–023 describe the
preceding completed PS8B study.

## Read by task

- [quickstart.md](quickstart.md): researcher setup, available commands, paths,
  output/errors, and reusable Python functions.
- [gpu_setup.md](gpu_setup.md): remote-first Linux GPU setup checklist;
  verified host installation and tiny CUDA checks; Task 034 records launch readiness.
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
