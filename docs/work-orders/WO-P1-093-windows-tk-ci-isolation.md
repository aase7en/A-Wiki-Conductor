# WO-P1-093 — Windows Tk CI isolation

Status: COMPLETE / MERGED
Owner: GPT-5.6 Sol via Remote Desktop Commander
Branch: `fix/wo-p1-093-windows-tk-ci-isolation`
Worktree: `A:\GitHub\A-Wiki-Conductor-ci-tk`
Base: `origin/main @ ab28dc7ea428e3253ce20cc155fb7b92e7719a8a`

## Goal

Repair the repeated hosted-Windows Tk `0x80000003` CI blocker without weakening GE-6 tests or mixing scheduler scope. `test_interactive_logo.py` is a Tk/GUI suite and must run with the existing GUI process rather than the generic remaining-core loop.

## Evidence / trigger

PR #104 exact head `70f4e85` passed its GE-6 scheduler tests but Windows CI run `33146745054` failed three consecutive attempts at `tests/test_interactive_logo.py:283` with `Windows fatal exception: code 0x80000003`. This crosses the `DEFECT_LESSONS.md #11` threshold: investigate/repair instead of another rerun.

## Allowed scope

- `.github/workflows/ci.yml`
- `tests/test_build_installer.py`
- this work order

## Forbidden scope

- GE-6 scheduler/tests/WO/handoff
- PR #108 installer target ownership
- North Star runtime files
- AHA production code

## Acceptance

- RED regression proves `test_interactive_logo.py` is absent from the GUI-suite grouping on the base.
- CI groups `test_interactive_logo.py` with GUI/Tk tests and excludes it from the generic per-file loop.
- No test is deleted, xfailed, or skipped merely to make CI green.
- Focused regression and `git diff --check` pass locally.
- PR exact-head CI is green before merge.
- After merge, PR #104 owner reconciles current `main` and reruns exact-head CI before GE-6 merge.

## Next safe action

Add the workflow-structure regression first, capture RED, then make the smallest CI grouping change.
## Checkpoint — local GREEN

- Safety gate: branch/worktree clean at creation; no overlap with GE-6, PR #108, North Star, or PR #117 allowed files.
- RED: focused workflow regression failed because `tests/test_interactive_logo.py` was absent from the GUI block.
- Fix: move that existing Tk test file into the Windows GUI-suite pytest process and add it to `$alreadyRun`; no skip/xfail/test deletion.
- Focused workflow regression: **1 passed**.
- `tests/test_interactive_logo.py`: **22 passed, 1 skipped** locally (local Tk installation limitation produced the existing safe skip).
- `tests/test_build_installer.py`: **22 passed**.
- `git diff --check`: PASS.

Status: COMPLETE / MERGED

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #118 merged into main as `ad1062827f1b177cde8af3f01e71da02ee0d2727`.
