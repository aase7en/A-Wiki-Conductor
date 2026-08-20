# WO-P1-029: Desktop Lifecycle Wiring

Status: in_progress
Lane/files: `src/a_conductor/desktop_control.py`, `src/a_conductor/desktop_ui.py`, `src/a_conductor/desktop_app.py`, `src/a_conductor/__init__.py`, `tests/test_desktop_control.py`, `tests/test_desktop_ui.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-029-desktop-lifecycle-wiring.md`
Branch: main
Model tier: high

## Goal

Enable Start/Stop/Restart in the desktop shell through a thin `DesktopControlService` that combines `ControlCenterService` with the authoritative `LifecycleCoordinator`. Run lifecycle commands off the Tk main thread and surface only stable lifecycle result/error codes.

## Acceptance

- tests first / RED before implementation;
- desktop control facade delegates project/assignment methods to ControlCenterService and lifecycle methods to LifecycleCoordinator;
- default desktop bootstrap uses one shared ControlCenterService instance for registry state and lifecycle state persistence;
- lifecycle buttons remain disabled if the supplied UI service has no lifecycle capability;
- with lifecycle-capable service, button enablement is state/assignment aware;
- lifecycle command executes in background executor; Tk main thread only polls future and renders result;
- while command is pending, lifecycle controls are disabled;
- result activity line contains action/worker/result state/reason code only;
- coordinator/control errors surface stable code only, no raw exception/secret text;
- UI refreshes after lifecycle completion/failure;
- `python -m a_conductor --smoke` remains non-mutating and passes on fresh DB;
- no direct process/tunnel/Git logic in desktop files;
- full suite + compileall + diff/static scan pass.

## Forbidden

- No PID/tunnel/profile handling in UI or desktop facade.
- No direct process/network/Git mutation in desktop files.
- No live Worker 3 provisioning.
- No remote/push.

## Checkpoint log

- [2026-08-20] Opened after local lifecycle assembly commit `e5405ca`; worktree clean.
