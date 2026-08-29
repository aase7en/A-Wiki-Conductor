# WO-P1-109 — Native execution temp-orphan sweep

Created: 2026-08-29
Owner: GPT-5.6 Sol runtime hygiene lane
Status: COMPLETE / MERGED PR #143 / POST-MERGE MAIN CI GREEN
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-native-temp-sweep`
Branch: `fix/wo-p1-109-native-temp-orphan-sweep`
Base: `origin/main@d2190414dcd8b51868a2c8214616425f2cb9dea9` (final base reconciled after PR #141)

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
- new temp trees use a versioned name `a-conductor-exec-v2-<created-epoch>-...`; the encoded creation epoch is the stable age/provenance anchor even if partial cleanup refreshes directory metadata. Legacy pre-v2 residue keeps the conservative older-of-mtime/ctime fallback.

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
- broader native/supervised/job/Claude runtime before final stable-provenance repair: **190 passed**;
- compileall + `git diff --check`: PASS;
- sweep is prefix-only, symlink-skip, active-lock aware, max 32 candidates, one deletion attempt per stale candidate;
- local stale cleanup reduced residues to **2 recent dirs (~8.6-8.7h)** and preserved both because they are below the 24h threshold.

Next: reconcile latest accepted main, rerun gates, commit/push/open PR, exact-head CI/re-audit/merge.

## Final-base checkpoint

Accepted main reconciled to `d2190414dcd8b51868a2c8214616425f2cb9dea9` after PR #141. Post-reconcile verification:
- native execution before final stable-provenance repair: **28 passed**;
- broader native/supervised/job/Claude runtime before final stable-provenance repair: **190 passed**;
- installer workflow contract: **22 passed**;
- no source/scope conflict with GE-11R1 or CI Node24 changes.

Next: exact remote diff audit -> PR -> 3-OS CI/frozen smoke -> post-CI re-audit -> expected-head merge -> accepted-main verification.

## Final stable-provenance repair checkpoint

Staff re-audit found the older-of-mtime/ctime anchor was not fully stable across POSIX filesystems because both timestamps can change after partial directory mutation. A deterministic RED test reproduced the intended invariant by refreshing directory metadata on a versioned stale temp tree; the old implementation returned `removed == 0`.

Repair:
- new execution temp directories now encode their creation epoch in a versioned basename;
- the sweeper uses that encoded epoch as the stable age anchor;
- legacy pre-v2 names retain the prior conservative mtime/ctime fallback;
- owner-lock, symlink, prefix, fail-soft and max-32 bounds are unchanged.

Post-repair evidence:
- new stable-provenance tests: **2 passed**;
- `tests/test_native_execution.py`: **30 passed**;
- native/supervised/job/Claude + installer composition: **219 passed**;
- live `%TEMP%` audit: exactly **2** legacy app-owned directories remain, both ~9h old and therefore intentionally preserved under the 24h threshold;
- production-helper probe: one disposable stale v2 app-owned directory was removed (`removed=1`) while both real recent legacy directories survived unchanged.

Next: diff/compile checks -> independent/adversarial review -> commit/push PR #143 -> exact-head CI -> remote re-audit -> expected-head merge -> post-merge main CI.

## Merge closeout - 2026-08-29

PR #143 merged with exact-head guard from `452b57aa93753eb17e83e264890130fd5c3d45ea` as `d554d084a9925715ea7588c97c81d3c61a002eb2`. Exact-head CI run `33242882386` and post-merge main CI run `33243187844` both passed Windows, Ubuntu, and macOS, including Windows build/archive/frozen smoke. Live hygiene validation removed only a disposable stale v2 temp tree and preserved the two real recent legacy residues below the 24h threshold.
