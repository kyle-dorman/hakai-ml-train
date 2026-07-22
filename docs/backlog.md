# Backlog

This file holds unselected future ideas only. It is not the active queue, a
decision record, or a substitute for a numbered task. Read `docs/todo.md` for
current work.

## Ideas after the baseline/LORO suite

- Repeat selected folds with additional random seeds after the single-policy
  comparison is stable.
- Compare another architecture only after the evaluation and matching-TIFF
  pipeline is verified end to end.
- Add qualitative error review for the source TIFFs with the largest paired
  baseline/LORO performance changes.
- Examine whether Channel Islands region IDs `ca_005` and `ca_006` should remain
  separate geographic folds after the first results are available.
- Test region-aware or domain-adaptation methods only after the plain LORO
  baseline is complete.
- Compare the baseline's generic SMP eight-band ImageNet adaptation with a
  PS8B-aware input projection after the primary suite is complete. The current
  behavior repeats RGB first-layer filters cyclically across the eight channels
  and scales them by `3/8`, while retaining deeper ImageNet weights. A future
  controlled variant could preserve the deeper encoder, map the known
  PlanetScope red/green/blue bands explicitly to their corresponding pretrained
  filters, and initialize Coastal Blue, Green I, Yellow, Red Edge, and NIR
  input weights independently. Treat this as a separately versioned model
  experiment, not a correction to the current baseline.
