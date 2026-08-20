# WO-P1-021: Read-Only Git Project Identity Verifier

Status: completed
Lane/files: `src/a_conductor/project_identity.py`, `src/a_conductor/__init__.py`, `tests/test_project_identity.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-021-git-project-identity.md`
Branch: main
Model tier: mid/high

## Goal

Implement the read-only project identity boundary used by Serena lifecycle operations using fixed direct-argv Git operations only.

## Acceptance evidence

- RED: module missing before implementation.
- Runner API exposes only `show_toplevel`, `branch`, `head`, `is_ancestor`.
- Concrete commands are limited to `rev-parse` and `merge-base --is-ancestor`, with per-command `safe.directory`, `shell=False`, bounded timeout.
- `EXACT`, `AUTHORIZED_SUCCESSOR`, `NO_GIT`, and `READ_ONLY_DISCOVERY` policies implemented.
- Exact Git policies verify resolved worktree root equality.
- Git failures map to stable codes without stderr leakage.
- Targeted tests: `13 passed`.
- Full suite: `326 passed in 5.67s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Forbidden command scan found no checkout/switch/reset/clean/fetch/pull/rebase/stash/push command in verifier source.
- Live read-only smoke on A-Wiki-Conductor: branch `main`, HEAD `8616381f2e42...`, identity success.
- No Git mutation/network operation performed.

## Checkpoint log

- [2026-08-20] Opened after P1-020 commit `5ea47c4`.
- [2026-08-20] Coordination commit `8616381`.
- [2026-08-20] RED module-missing checkpoint.
- [2026-08-20] GREEN targeted 13/13, full 326/326, live read-only smoke passed. Complete.
