# WO-P1-029: Desktop Lifecycle Wiring

Status: completed
Lane/files: `src/a_conductor/desktop_control.py`, `src/a_conductor/desktop_ui.py`, `src/a_conductor/desktop_app.py`, `src/a_conductor/__init__.py`, `tests/test_desktop_control.py`, `tests/test_desktop_ui.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-029-desktop-lifecycle-wiring.md`
Branch: main
Model tier: high

## Goal

Enable Start/Stop/Restart in the desktop shell through a thin facade over `ControlCenterService` + authoritative `LifecycleCoordinator`, with lifecycle work off the Tk main thread.

## Acceptance evidence

- RED: desktop-control module/background UI capability missing before implementation.
- `DesktopControlService` delegates project/assignment operations to the shared ControlCenterService and lifecycle operations to LifecycleCoordinator.
- `DesktopControlService.open()` builds the coordinator with the same ControlCenterService instance used by the UI.
- Legacy/non-lifecycle UI services retain disabled Start/Stop/Restart controls.
- Lifecycle-capable services enable controls based on selected assigned worker state (STOPPED=>Start, READY=>Stop/Restart).
- Lifecycle work executes through background executor; Tk main thread polls Future and renders result.
- Controls disable while command is pending.
- Result activity uses action/worker/execution state/reason code only.
- Known coordinator errors display stable code only; unknown exceptions collapse to `LIFECYCLE_COMMAND_FAILED` without raw text.
- Fresh-DB `python -m a_conductor --smoke` remains non-mutating.
- Full suite + compileall + `git diff --check`: PASS.
- Active Sunday-Conducter PID preserved through verification.
- Desktop static scan contains no direct process/tunnel/Git/API-key primitive.

## Checkpoint log

- [2026-08-20] Opened after local lifecycle assembly commit `e5405ca`.
- [2026-08-20] Coordination checkpoint committed.
- [2026-08-20] RED desktop-control/background UI checkpoint.
- [2026-08-20] GREEN facade/UI/full/smoke/preservation verification. Complete.
