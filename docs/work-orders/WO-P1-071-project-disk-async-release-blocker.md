# WO-P1-071 — PROJECT DISK async/cancellable release blocker

Created: 2026-08-26
Owner: GPT-5.6 Sol MAX — release blocker repair
Status: COMPLETE / MERGED
Remote PR branch: `fix/project-disk-async-release` (PR #99)
Current local transport branch: `fix/project-disk-async-ci`
Reconciled base: `origin/main` `12a4c56db5704706ef3b2b25e291f2639627c05c` via merge commit `35fbc5e`

## Trigger / reproducer

PR #98 added `PROJECT DISK` by calling `project_disk_display()` synchronously from `_refresh_project_disk()` on the Tk UI thread.

Real workstation benchmark, read-only:
- `A:\GitHub\A-Wiki-Conductor` — 1,093,795,443 bytes — **52.1194 s**
- `A:\GitHub\A-Wiki-Conductor-glm-release-audit` — 542,282,526 bytes — 1.1383 s

This can freeze the app on project selection/refresh and violates the lightweight UI contract. The existing UI background executor has `max_workers=1`; placing a long disk scan there would also starve lifecycle/monitor work.

## Scope

Allowed:
- `src/a_conductor/folder_size.py`
- `src/a_conductor/desktop_ui.py`
- focused tests for folder-size async/cancellation/UI behavior
- this WO + bounded defect/continuity records

Forbidden:
- scheduler/graph production code
- live connector mutation
- shared main worktree
- A-Wiki

## Contract

1. UI thread never recursively walks a project folder.
2. Folder scan runs on a **dedicated single-worker executor**, separate from lifecycle/monitor executor.
3. One scan at a time; selecting a new project cancels/supersedes the old request cooperatively.
4. Stale result must never overwrite the currently selected project.
5. While pending show `…`; unavailable/cancelled remains `—` or is superseded.
6. Cache completed values by normalized project path; repeat selection may reuse cached value without blocking.
7. App shutdown cooperatively cancels scan and shuts down the dedicated executor; no long process-exit tail.
8. No subprocesses.

## TDD acceptance

- regression proves `_refresh_project_disk()` returns promptly while a deliberately blocked/slow scan runs in background;
- stale A result cannot overwrite selected B;
- cancellation signal reaches scanner;
- repeated same-path selection uses cache / does not launch duplicate work;
- close/shutdown sets cancellation and does not schedule callbacks afterward;
- existing folder-size formatting tests remain green;
- focused GUI tests green; full CI green before merge.

## Verification checkpoint — 2026-08-26

Red-first evidence:
- `tests/test_project_disk_async.py::test_app_exposes_dedicated_disk_executor_injection_seam` failed before implementation because `disk_executor` did not exist; four GUI tests were present but skipped locally because the audit venv's Tcl path is unusable.

Implemented:
- `folder_size_bytes(..., cancel_check=...)` cooperative cancellation, still no subprocess;
- dedicated `a-conductor-disk` single-worker executor, separate from the existing one-worker lifecycle/monitor executor;
- pending `…`, request-id/path stale-result guard, per-session path cache;
- cancellation/supersession on project changes and cooperative shutdown;
- injected executor seam for deterministic tests.

Focused result using isolated pytest temp root:
- `tests/test_folder_size.py tests/test_project_disk_async.py` → **10 passed, 4 skipped**;
- skips are local Tcl-environment only (`Can't find a usable init.tcl`); GitHub Windows GUI CI is the authoritative Tk gate;
- `git diff --check` clean;
- `folder_size.py` LSP diagnostics: none.

## CI routing correction — 2026-08-26

PR #99 Windows run `32938220760` first exposed two real async race assertions; commit `a678137` fixed the completed-Future/result-consumption race. The next run and its single bounded rerun no longer reported those assertions, but both Windows core processes terminated with `0x80000003` while `test_native_git_transactions.py` was spawning Git.

Root cause classification: the new `tests/test_project_disk_async.py` contains Tk tests but was not added to the repository's existing GUI/core process split. `.github/workflows/ci.yml` already documents that hosted Windows can emit `0x80000003` GC/native breakpoint failures when Tk/subprocess-heavy suites share the same long-lived pytest process.

Repair: run `test_project_disk_async.py` in `Run GUI test suite` and explicitly ignore it in `Run core test suite`. This does **not** skip coverage; it restores the intended CI isolation boundary. Fresh CI must pass before merge.

## Release gate

Do not publish `v0.7.0` from a SHA containing synchronous PROJECT DISK scanning. Merge this repair first with full CI green, then use the exact post-merge main build artifacts and perform sandbox installed acceptance.
## CI timing correction / latest checkpoint — 2026-08-26

- Fresh routed Windows run `32943940771` reached the GUI suite and failed only `test_stale_disk_result_cannot_overwrite_new_selection`; the prior core-process `0x80000003` contamination did not recur in that run.
- Diagnosis: `_poll_project_disk()` intentionally polls every 25 ms, while the regression called `root.update()` once and assumed a future 25 ms callback must already have fired. That is not deterministic on hosted runners.
- Repair: GUI tests now use a bounded event-loop wait (0.5 s maximum, 5 ms drain interval) for the designed poll callback. Production polling semantics were not weakened or complicated to satisfy a timing-fragile assertion. Cache completion uses the same bounded wait.
- Local focused verification: `tests/test_project_disk_async.py tests/test_folder_size.py` -> **10 passed, 4 skipped**; the four skips remain only the workstation Tcl-path problem.
- Branch merged latest `origin/main` `12a4c56` cleanly; stale `CURRENT-WORK.md`, `handoff.md`, and `COLLAB.md` branch checkpoints are deliberately removed from PR #99 so they cannot roll main back. Final continuity reconciliation belongs in `docs/repo-health-100` after all GPT-owned work closes.
- Next gate: commit/push this final PR #99 head, audit remote diff, require all CI checks green, re-audit, merge, fetch/reconcile.

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #99 merged into main as `e8195b1d16799140068abb09297198df4a725149`.
