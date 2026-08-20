# WO-P1-025: CLI-Inspired Desktop Shell + Projects/Workers Screen

Status: completed
Lane/files: `src/a_conductor/desktop_ui.py`, `src/a_conductor/desktop_app.py`, `src/a_conductor/__main__.py`, `src/a_conductor/__init__.py`, `tests/test_desktop_ui.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-025-desktop-shell.md`
Branch: main
Model tier: mid/high

## Goal

Build the first usable A-Conductor desktop adapter over `ControlCenterService` using stdlib Tkinter 8.6.

## Acceptance evidence

- RED: desktop module missing before implementation.
- Dark/near-dark compact CLI-inspired theme with semantic state colors.
- Main shell contains ONLINE top bar, Projects list, three-slot Workers tree, action row, Activity/Log panel.
- Add Project / Assign / Release / Refresh call the existing application service only.
- Start/Stop/Restart controls are present but intentionally disabled until lifecycle wiring.
- Ctrl+K command palette implemented for common safe actions.
- Assignment/state/path/worker ID remain visible in worker table.
- `python -m a_conductor --smoke --database runtime\a-conductor-ui-smoke.sqlite` => `A-CONDUCTOR_SMOKE_OK projects=0 workers=3` in a separate process.
- Targeted tests: `9 passed, 1 skipped`; skipped test was an in-process second-Tk interpreter limitation, while separate-process smoke passed.
- Full suite: `363 passed in 6.32s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Desktop static scan found no subprocess/tunnel/Git-mutation/API-key primitives.
- Architecture: replaceable Tkinter adapter over service; core control plane remains UI-framework neutral.

## Checkpoint log

- [2026-08-20] Opened after Control Center service commit `3326bcb`; Tkinter 8.6 verified.
- [2026-08-20] Coordination commit `efafddb`.
- [2026-08-20] RED desktop-module checkpoint.
- [2026-08-20] GREEN UI actions/layout/tests + separate-process smoke; full suite 363/363. Complete.
