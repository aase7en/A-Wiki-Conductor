# WO-P1-025: CLI-Inspired Desktop Shell + Projects/Workers Screen

Status: in_progress
Lane/files: `src/a_conductor/desktop_ui.py`, `src/a_conductor/desktop_app.py`, `src/a_conductor/__main__.py`, `src/a_conductor/__init__.py`, `tests/test_desktop_ui.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-025-desktop-shell.md`
Branch: main
Model tier: mid/high

## Goal

Build the first usable A-Conductor desktop adapter over `ControlCenterService` using stdlib Tkinter 8.6: compact dark CLI-inspired Projects/Workers layout, activity panel, keyboard-first command palette, and safe project/assignment actions.

## Architecture classification

`NEW` UI adapter over existing service. Tkinter is not a core architectural dependency; the UI consumes immutable service snapshots and may be replaced later without redesigning the control plane.

## Acceptance

- tests first / RED before implementation;
- dark/near-dark compact theme with restrained semantic colors;
- top status bar, Projects list, Workers view (3 slots), action row, Activity/Log panel;
- Add Project uses directory picker and existing read-only service registration;
- Assign requires selected project + worker and persists through service;
- Release calls service and surfaces stable error code only;
- Refresh renders persisted state without filesystem/process side effects;
- Start/Stop/Restart controls are present but disabled until lifecycle wiring work order;
- Ctrl+K opens a minimal command palette for Add Project / Assign / Release / Refresh;
- UI shows project assignment, state, worker ID, and path clearly;
- `python -m a_conductor` launches desktop app using per-user local database path;
- smoke mode can construct/refresh/destroy UI without entering long-running mainloop;
- tests do not require external packages;
- full suite + compileall + diff/static scan pass.

## Forbidden

- No process/tunnel lifecycle mutation in this work order.
- No Git/repository mutation.
- No API/credential values in UI.
- No remote/push.

## Checkpoint log

- [2026-08-20] Opened after Control Center service commit `3326bcb`; Tkinter 8.6 verified available.
