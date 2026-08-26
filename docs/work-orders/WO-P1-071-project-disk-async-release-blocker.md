# WO-P1-071 — PROJECT DISK async/cancellable release blocker

Created: 2026-08-26
Owner: GPT-5.6 Sol MAX — release blocker repair
Status: READY_FOR_PR — TDD repair implemented; focused deterministic suite green; GitHub Windows GUI CI required
Branch: `fix/project-disk-async-release`
Base: PR #97 final head `923dd6b7dd74e5a78b29f8e6d688276ca1a57ff0` (contains current main `6f7dfd5`)

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