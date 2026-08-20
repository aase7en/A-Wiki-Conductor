# WO-P1-027: Lifecycle Coordinator

Status: completed
Lane/files: `src/a_conductor/lifecycle_coordinator.py`, `src/a_conductor/__init__.py`, `tests/test_lifecycle_coordinator.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-027-lifecycle-coordinator.md`
Branch: main
Model tier: high

## Goal

Create the application-level lifecycle coordinator that is the sole path from UI/service lifecycle commands to the existing pure planner and checkpointed executor.

## Acceptance evidence

- RED: module missing before implementation.
- Every command obtains fresh context, calls authoritative `plan_lifecycle`, then invokes checkpointed `LifecycleExecutor` only for the returned plan.
- START/RESTART PROCEED persists STARTING before backend creation; STOP persists STOPPING.
- COMPLETE/NOOP START/RESTART => READY; COMPLETE/NOOP STOP/RELEASE => STOPPED.
- REFUSED leaves worker state unchanged and never creates backend.
- Recovery-required plan/execution and failed execution transition worker to ERROR.
- Pre-execution state persistence failure stops before backend with `recovery_required=False`.
- Final-state persistence failure after PROCEED is surfaced with `recovery_required=True`.
- Non-empty per-command transaction ID enforced.
- Targeted tests: `12 passed`.
- Full suite: `386 passed, 1 skipped in 7.05s`; skip is the known in-process Tk environment limitation, separate-process desktop smoke previously passed.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Static coordinator I/O scan clean: no subprocess/SQLite/network/Tk/Git/PowerShell implementation.

## Checkpoint log

- [2026-08-20] Opened after Serena config store commit `95ceb5d`.
- [2026-08-20] Coordination commit `e0f0d8e`.
- [2026-08-20] RED module-missing checkpoint; test fixture aligned to authoritative `LifecycleContext.ready` field.
- [2026-08-20] GREEN targeted 12/12, full suite 386 + one known UI-env skip. Complete.
