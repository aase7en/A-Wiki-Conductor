# WO-P1-021: Read-Only Git Project Identity Verifier

Status: in_progress
Lane/files: `src/a_conductor/project_identity.py`, `src/a_conductor/__init__.py`, `tests/test_project_identity.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-021-git-project-identity.md`
Branch: main
Model tier: mid/high

## Goal

Implement the read-only project identity boundary used by Serena lifecycle operations. Verify exact worktree/root/branch/HEAD policies using direct Git argv only; never mutate repository state.

## Acceptance

- tests first / RED before implementation;
- Git calls use argv + `shell=False` only;
- allowed commands limited to `rev-parse` and `merge-base --is-ancestor`;
- exact resolved worktree root must equal bound worktree path for Git policies;
- `EXACT`: expected branch/head, when supplied, must match exactly;
- `AUTHORIZED_SUCCESSOR`: current HEAD must equal or descend from expected HEAD; expected branch, when supplied, must match;
- `NO_GIT`: directory existence is sufficient and no Git subprocess is called;
- `READ_ONLY_DISCOVERY`: directory must exist; Git identity may be discovered without enforcing expected branch/head;
- command failures map to stable error codes without raw stderr leakage;
- no checkout/switch/reset/clean/fetch/pull/merge/rebase/stash/write commands;
- full suite + compileall + diff/static command scan pass.

## Forbidden

- No Git mutation.
- No network/fetch.
- No live Serena/tunnel mutation.
- No Git remote/push for this repository.

## Checkpoint log

- [2026-08-20] Opened after P1-020 commit `5ea47c4`; worktree clean.
