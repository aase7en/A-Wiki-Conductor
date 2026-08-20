# WO-P1-027: Lifecycle Coordinator

Status: in_progress
Lane/files: `src/a_conductor/lifecycle_coordinator.py`, `src/a_conductor/__init__.py`, `tests/test_lifecycle_coordinator.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-027-lifecycle-coordinator.md`
Branch: main
Model tier: high

## Goal

Create the application-level lifecycle coordinator that is the sole path from UI/service lifecycle commands to the existing pure planner and checkpointed executor. It owns worker-state transitions but delegates context observation and Serena step execution to injected factories.

## Acceptance

- tests first / RED before implementation;
- every command obtains a fresh `LifecycleContext`, calls `plan_lifecycle`, and executes only the approved plan;
- PROCEED start/restart transitions worker to STARTING before execution; stop to STOPPING;
- successful/no-op start/restart => READY; successful/no-op stop => STOPPED;
- REFUSED leaves existing worker state unchanged;
- RECOVERY_REQUIRED/FAILED execution transitions worker to ERROR;
- backend factory is not required for non-PROCEED plans;
- checkpoint sink is always passed to executor for PROCEED transactions;
- transaction IDs are non-empty and generated per command;
- state persistence failure is surfaced as coordinator error, never hidden;
- coordinator has no process/Git/network/SQLite implementation;
- full suite + compileall + diff/static I/O scan pass.

## Forbidden

- No direct process/tunnel/Git/filesystem mutation.
- No Serena config assembly in this module.
- No UI dependency.
- No remote/push.

## Checkpoint log

- [2026-08-20] Opened after Serena config-store commit `95ceb5d`; worktree clean.
