# WO-P1-033: Transactional Git Stage + Commit

Status: in_progress
Lane/files: `src/a_conductor/native_git_transactions.py`, `src/a_conductor/__init__.py`, `tests/test_native_git_transactions.py`, `docs/contracts/native-git-transactions.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-033-transactional-git-mutations.md`
Branch: main
Model tier: high

## Goal

Add narrowly scoped Git stage/commit transactions over the Native Execution Core with exact state preconditions. Prevent blind staging/commit when HEAD, worktree status, or staged diff drifted after observation.

## Acceptance

- RED tests first, including real temporary Git repositories.
- `snapshot()` captures exact HEAD plus status and cached-diff evidence.
- Stage requires explicit non-directory pathspecs and exact expected HEAD/status-hash/cached-diff-hash from a prior snapshot.
- Any precondition drift refuses before mutation.
- Commit requires exact expected HEAD/status-hash/cached-diff-hash and refuses an empty staged diff.
- First commit implementation is noninteractive/deterministic: skip repository commit hooks and disable GPG signing. Hook/sign support is a future explicit policy.
- Every mutating command declares `mutation_intent=True`; read-only scopes refuse before Git mutation.
- No reset/clean/checkout/stash/rebase/merge/push/fetch/pull/remote operations.
- No generic Git argv passthrough.
- Full suite + compileall + diff/static safety gates pass.

## Forbidden

- No blanket stage `.` or directory pathspec.
- No force options.
- No network Git operations.
- No destructive history/worktree operations.
- No live mutation of another repo during tests; integration tests use temporary repos only.

## Verify

- `python -m pytest tests/test_native_git_transactions.py -q`
- `python -m pytest -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened from clean P1-032 commit `88a863f`.
