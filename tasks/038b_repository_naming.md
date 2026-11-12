# Task 038B: Use kelpseg in current repository instructions

Status: Complete.

## Abstract, inputs and plan

The user chose `kelpseg` for all current naming. Remove the old checkout name
from current operating examples in `docs/gpu_setup.md`,
`docs/guides/diagnostics.md` and `docs/reference/ca_bc_release.md`.
Use the repository's current SSH URL copied from GitHub when cloning into a
folder named `kelpseg`, so the instructions work before or after a GitHub rename.
Preserve recorded historical commands, machine paths and CI links as evidence.

## User decisions required

None for text cleanup. Renaming the actual GitHub repository or moving this
checkout is outside this documentation edit. Package/import/command names
already use `kelpseg`.

## Acceptance and validation

Current examples use `kelpseg`; no application behavior, artifact identity or
historical evidence changes. Inspect the diff, check remaining old-name matches,
verify changed relative links, run repository hygiene and `git diff --check`.
No commit or push unless requested. The next roadmap task remains 039.

## Outcome

Completed 2026-11-12. Updated the three operating documents named above and
the queue/task index. Current checkout examples use `kelpseg`; cloning accepts
the actual SSH URL from GitHub and explicitly names the destination. No
speculative renamed GitHub URL is presented as live.

Validation: all 18 repository hygiene tests passed; `git diff --check` passed.
Reviewed the documentation diff and verified the new task links resolve.
The ten remaining old-name occurrences belong to historical task records and
historical GPU recipes (recorded paths, commands and a CI run URL).
No current operating guide retains the old checkout name.

No code, external artifacts, local folders or GitHub settings changed. The user
subsequently authorized committing these documentation changes; no push was
requested. Exact next action: rename the GitHub repository and update both local
checkouts when ready. The roadmap remains 039 then 042.
