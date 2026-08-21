# WO-P1-055: Alive Status + Themed Teaching Errors

Status: COMPLETE
Lane/files: `src/a_conductor/desktop_ui.py`, `tests/test_desktop_ui.py`, `docs/work-orders/WO-P1-055-alive-status-themed-errors.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: `chunk/p1-055-alive-status-themed-errors`
Baseline HEAD: `2a24c5b5e59c2453add53ad2e957c3616e1327c6`
Model tier: high

## Goal

Polish the Phase 1 desktop UI after onboarding/usability work without changing orchestration behavior:

1. Make the `ONLINE` indicator feel alive with a slow, subtle pulse while preserving the existing ONLINE/OFFLINE meaning.
2. Replace raw-code-only default error popups with an A-Conductor-themed teaching popup containing a short Thai explanation, the stable error code, and a next action.

## Reuse / scope gate

- Reuse existing `DesktopTheme`, `AConductorDesktopApp._handle_error`, activity log, and in-app guide.
- Do not add a second notification framework or external dependency.
- Do not change lifecycle, connector, worker, tunnel, persistence, or Serena engine behavior.
- Keep error codes stable for logs/tests; the explanation layer is presentation-only.

## Acceptance

- `ONLINE` gently alternates between semantic ready colors; `OFFLINE` remains error-colored and is not pulsed.
- Pulse styling is theme-owned, not a hard-coded one-off in the callback.
- Default error UI is a themed `Toplevel`, not a native raw-code-only message box.
- Every statically emitted `_handle_error("CODE")` has a teaching entry or intentional generic fallback coverage.
- `_handle_error` remains the single activity-log emission point (no duplicate error log from the popup renderer).
- No temporary/debug markers remain in production files.
- Existing UI behavior remains unchanged outside the presentation layer.
- Targeted desktop UI tests pass on a Tk-capable runner; local Tk-environment skips must be reported separately from code failures.

## Micro-steps

- [x] 055-A Recover partial working-tree intent and compare with current Phase 1 UI contract.
- [x] 055-B Clean implementation defects (theme pulse color, duplicate logging, debug marker) and tighten tests.
- [x] 055-C Run static checks + targeted tests; classify local Tk environment separately.
- [x] 055-D Review diff and update CURRENT-WORK/HANDOFF; commit checkpoint prepared on the feature branch.

## Recovery notes

Recovered on 2026-08-21 from an existing dirty working tree on this branch. Before recovery, only these files were modified:

- `src/a_conductor/desktop_ui.py`
- `tests/test_desktop_ui.py`

The partial delta already contained `ERROR_EXPLANATIONS`, a themed `_show_error`, status pulse scheduling, and two new UI tests. Review found three cleanup items before acceptance: duplicate activity logging inside `_show_error`, hard-coded dim-ready pulse color, and a trailing `# MARKER-TEST-8f3a` production marker.

## Local test-environment note

A first targeted run of four UI tests returned `4 skipped` because the current Python/Tk environment could not locate a usable `init.tcl` and referenced a stale PyInstaller-style `_MEI.../_tcl_data` path. This is an execution-environment limitation, not a test assertion failure; a Tk-capable verification pass is still required before closing the work order.

## Completion evidence

- `git diff --check`: clean.
- Python compile: `src/a_conductor/desktop_ui.py` and `tests/test_desktop_ui.py` compiled successfully.
- Static teaching-error coverage: 29 statically emitted `_handle_error("CODE")` codes, 0 missing explanations.
- Targeted desktop UI: 38 passed.
- First full-suite pass: 809 passed / 1 timing failure in `test_timeout_leaves_durable_running_execution_then_retry_attaches`; isolated rerun passed.
- Full-suite verification rerun: **810 passed**.
- Test-environment root cause: Sunday-Conducter inherited stale PyInstaller `TCL_LIBRARY`/`TK_LIBRARY` values pointing at an expired `_MEI...` directory. Verification used Python 3.13 with command-scoped Tcl/Tk overrides and a custom `--basetemp`; no system environment or tunnel/worker configuration was changed.
