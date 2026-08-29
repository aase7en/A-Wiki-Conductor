# WO-P1-109 — Native execution temp-orphan sweep

Created: 2026-08-29
Owner: GPT-5.6 Sol runtime hygiene lane
Status: LOCAL_VERIFIED / PR PENDING
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-native-temp-sweep`
Branch: `fix/wo-p1-109-native-temp-orphan-sweep`
Base: `origin/main@392047a0395f30cc1d6ed7d8c2c3f7c0457a5e37`

## Trigger

WO-P1-107 made persistent AV/indexer locks explicit as `COMMAND_CLEANUP_FAILED`, but intentionally left the private temp tree behind after the retry budget. A live-machine audit on 2026-08-29 found 17 `%TEMP%\a-conductor-exec-*` directories; 15 were older than ~28 hours and several were 5-8 days old.

This is confirmed cleanup debt, not a theoretical finding.

## Scope / safety

Allowed:
- `src/a_conductor/native_execution.py`
- `tests/test_native_execution.py`
- `DEFECT_LESSONS.md`
- this work order

No background cleaner, detached process, scheduler, timer, live connector or user-directory traversal. Automatic cleanup may inspect only the OS temp root and directories whose basename starts exactly `a-conductor-exec-`.

## Design

- stale threshold: 24 hours, six times the longest currently configured production native timeout (4h Claude supervised path);
- skip recent candidates and symlinks; active executions hold an OS lock marker and are never swept;
- stale cleanup is best-effort and must never change command semantics if cleanup itself fails;
- reuse `_remove_temp_tree_with_permission_retry`; no second deletion policy;
- run at most 32 single-attempt stale deletions before creating the next private execution temp directory; primary command cleanup retains its existing retry budget.
- age uses the older of mtime/ctime so a failed partial deletion cannot make an old orphan look newly created.

## Acceptance

- deterministic RED proves stale prefixed dirs are currently not swept;
- stale prefixed dir is removed; recent prefixed dir remains;
- unrelated dirs and symlinks remain untouched;
- PermissionError/OSError while sweeping is fail-soft and does not block the command;
- existing command cleanup retry/result semantics remain unchanged;
- native + supervised/job regression passes;
- local cleanup removes only stale app-owned residues and reports any locked survivors;
- exact-head CI, remote diff/review, merge and accepted-main verification pass.

## Local verification checkpoint

- initial live audit: 17 app-owned temp dirs; 15 stale >24h, several 5-8 days old;
- TDD RED proved no sweep API; later REDs caught unbounded retry work, active-run age race, and mtime-refresh false recency;
- focused native execution: **28 passed**;
- broader native/supervised/job/Claude runtime: **190 passed**;
- compileall + `git diff --check`: PASS;
- sweep is prefix-only, symlink-skip, active-lock aware, max 32 candidates, one deletion attempt per stale candidate;
- local stale cleanup reduced residues to **2 recent dirs (~8.6-8.7h)** and preserved both because they are below the 24h threshold.

Next: reconcile latest accepted main, rerun gates, commit/push/open PR, exact-head CI/re-audit/merge.
