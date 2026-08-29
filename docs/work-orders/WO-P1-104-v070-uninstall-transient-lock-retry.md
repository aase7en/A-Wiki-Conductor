# WO-P1-104 — v0.7 uninstall transient-lock retry

Date: 2026-08-28
Owner: GPT-5.6 Sol integrator
Status: SOURCE COMPLETE / MERGED
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-v070-uninstall-retry`
Branch: `fix/wo-p1-104-uninstall-transient-lock-retry`
Base: `origin/main@bbb392b1ea459e7e5103232845ec3bd463856dbd`
Parent: v0.7.0 release closeout / WO-P1-081 + WO-P1-083

## Defect

Exact-main CI Setup installed and smoked successfully in an isolated sandbox, but registered uninstall returned `UNINSTALL_PARTIAL`: `shutil.rmtree(target)` hit transient WinError 5 on the freshly executed Portable. No product process remained; an immediate bounded manual retry removed the target successfully. Live v0.6 registry, Start Menu, Desktop shortcut, and installed executable hashes were restored unchanged.

## Reuse / scope

Classification: **EXTEND** the existing synchronous registered-uninstall design. No new helper process, scheduler, background cleaner, or detached cleanup lifecycle.

Allowed mutable scope:
- `scripts/installer_main.py`
- additive `tests/test_installer_uninstall_retry.py` (or the existing uninstall-self-delete test only if smaller)
- this work order
- `DEFECT_LESSONS.md` only after verified prevention evidence

Forbidden scope:
- PR #125 connector recovery / live connectors
- PR #131 / WO-P1-102 worker leasing
- North Star
- CURRENT-WORK / COLLAB / handoff hotspots
- live v0.6 install as a destructive test target

## Required behavior

1. Target cleanup retries only transient `PermissionError` with a finite delay budget.
2. Unrelated `OSError` fails immediately; no masking or infinite retry.
3. Persistent lock still returns `UNINSTALL_PARTIAL` with the original failure visible.
4. Registered wrapper remains synchronous and authoritative; no detached helper returns.
5. Source/non-Windows behavior remains deterministic.
6. Unit tests use injected sleeper/delays; no wall-clock sleeps.
7. Exact-head 3-OS CI including Windows packaging/frozen smoke passes.
8. Exact-main CI artifact repeats sandbox install/smoke/registered-uninstall successfully; target + temp uninstaller disappear and live v0.6 state remains byte-identical.

## First TDD sequence

- RED: transient `PermissionError` twice then success currently returns partial / has no retry seam.
- GREEN: smallest bounded retry helper used by `do_uninstall()`.
- RED/GREEN: persistent `PermissionError` exhausts finite budget.
- RED/GREEN: unrelated `OSError` is attempted once only.
- focused installer regressions -> broader installer suite -> compileall/diff/secret gate -> PR/CI -> exact-main E2E.

## Local verification checkpoint — 2026-08-28

Exact-main artifact evidence before this source repair: unknown-target refusal exit 5 with sentinel byte-identical; sandbox install exit 0; marker/shortcuts/registry v0.7.0 present; installed Portable hash matched CI Portable; smoke exit 0. Registered uninstall then returned `UNINSTALL_PARTIAL` on transient WinError 5 for the freshly-smoked Portable. No product process remained and immediate manual retry removed the tree; live v0.6 registry/Start Menu/Desktop/exe hashes were restored unchanged.

TDD evidence for this repair:
- RED: new bounded-removal suite `4 failed` because no retry seam existed and `do_uninstall()` used direct `rmtree`;
- GREEN: new suite `4 passed`;
- combined installer ownership/self-delete/build/retry regression: `41 passed`;
- `python -m compileall -q scripts src/a_conductor`: PASS;
- `git diff --check`: PASS;
- bounded secret scan: 0 hits.

Next: exact scope/overlap gate -> commit/push -> PR -> exact-head 3-OS CI -> merge -> exact-main artifact sandbox install/smoke/uninstall repetition. Publication stays blocked until target and temp uninstaller both disappear with live v0.6 state unchanged.

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #132 merged into main as `c7aae70bfe0f24dddcd746f16e32f6c5f00b6a5f`.
