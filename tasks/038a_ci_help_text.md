# Task 038A: Normalize styled CLI help in CI tests

Status: Complete.

## Abstract and scope

Repair the two help-text assertions failing in GitHub Actions run 43276005865.
Terminal styling splits option names with ANSI codes. Preserve CLI behavior and
the existing import-isolation and installed-distribution checks.

## Inputs, plan and expected outputs

Use the failed job log, `tests/test_augmentation_preview.py` and
`tests/test_distribution.py`. Apply Click's existing `unstyle` helper before
matching help text, following `tests/test_package_cli.py`. Exercise the checks
with terminal styling forced. Update this record and the task routers.

## User decisions required

None. The user requested this fix. No commit or push is authorized.

## Validation and acceptance

Run both affected tests with `TERM=xterm-256color FORCE_COLOR=1 NO_COLOR=1`,
repository hygiene, Ruff formatting/lint and `git diff --check`. The tests must
still check option presence and blocked workflow imports. No production work,
CLI behavior changes or new-region work belongs in this task.

## Outcome

Completed 2026-11-12. Changed the two test files above to remove ANSI styling
from help text before matching commands/options. Existing option-presence,
import-isolation and wheel/sdist installation checks remain intact. This follows
the existing test helper convention; no new dependency or application behavior
was introduced. Updated `docs/todo.md` and `tasks/README.md` for closure.

Validation:

- `TERM=xterm-256color FORCE_COLOR=1 NO_COLOR=1 uv run --frozen pytest -q
  tests/test_augmentation_preview.py::test_cli_and_preview_help_remain_lightweight
  tests/test_distribution.py tests/test_repository_hygiene.py`: **20 passed**.
- `uv run ruff format --check .`: passed (163 files).
- `uv run ruff check .` and `git diff --check`: passed.

No durable external artifacts or production workloads. No unresolved local
failure; remote CI needs a future user push to validate this revision.

The user subsequently authorized committing this fix and its task notes. This
supersedes the earlier no-commit instruction; no push was requested. Exact next
action: push when ready and check CI, then separately select and bound Task 039.
Task 042 remains the final handoff.
