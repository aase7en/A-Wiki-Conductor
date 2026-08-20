# WO-P1-028: Local Serena Lifecycle Assembly

Status: in_progress
Lane/files: `src/a_conductor/lifecycle_assembly.py`, `src/a_conductor/control_events.py`, `src/a_conductor/__init__.py`, `tests/test_lifecycle_assembly.py`, `tests/test_control_events.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-028-local-lifecycle-assembly.md`
Branch: main
Model tier: high

## Goal

Assemble persisted Control Center + Serena configuration into the authoritative lifecycle coordinator without bypassing existing planner/executor/process safety boundaries. Add a minimal append-only local event log that emits opaque evidence refs only.

## Acceptance

- tests first / RED before implementation;
- context provider derives assignment/project/process/port/tunnel/worktree/ready/identity facts from current service/config/observer state;
- context provider never mutates host/repository state;
- active-task remains `False` in Phase 1 until task broker exists (explicitly documented, not guessed from UI);
- backend factory reconstructs per-worker operations from persisted worker/project/reference metadata;
- duplicate tunnel refs become collision for the requesting worker; no active binding reuse;
- reference store is constructed from persisted paths only; file content is read only when token provider resolves a requested token;
- assignment service delegates release to ControlCenterService;
- event log is append-only SQLite and stores only event ID/type/worker/project/timestamp; no secret/token values;
- factory exposes one `build_local_lifecycle_coordinator(...)` helper using SQLite journal + coordinator + ControlCenterService state persistence;
- tests use temp DB/dummy/fake observer only; no live tunnel/process mutation;
- full suite + compileall + diff/static scan pass.

## Forbidden

- No direct live A-Worker 3 mutation.
- No active Conductor/Phase6 targeting.
- No tunnel provisioning.
- No Git mutation.
- No secret values in event log.
- No remote/push.

## Checkpoint log

- [2026-08-20] Opened after lifecycle coordinator commit `045e7df`; worktree clean.
