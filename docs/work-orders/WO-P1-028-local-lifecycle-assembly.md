# WO-P1-028: Local Serena Lifecycle Assembly

Status: completed
Lane/files: `src/a_conductor/lifecycle_assembly.py`, `src/a_conductor/control_events.py`, `src/a_conductor/__init__.py`, `tests/test_lifecycle_assembly.py`, `tests/test_control_events.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-028-local-lifecycle-assembly.md`
Branch: main
Model tier: high

## Goal

Assemble persisted Control Center + Serena configuration into the authoritative lifecycle coordinator without bypassing existing planner/executor/process safety boundaries. Add a minimal append-only payload-free event log.

## Acceptance evidence

- RED: control-event/lifecycle-assembly modules missing before implementation.
- Context provider derives current assignment/project/process/port/tunnel/worktree/ready/identity facts from service/config/observer state and performs no mutation.
- Unassigned workers produce an explicit planner-friendly context without requiring Serena runtime config.
- Duplicate persisted tunnel refs become `TUNNEL_COLLISION` for the requesting worker.
- `active_task=False` is explicit Phase 1 behavior until task broker exists.
- Backend factory reconstructs token/reference/tunnel/preflight/identity/process/assignment/evidence boundaries from persisted metadata.
- Reference files are not read during context observation; token content is read only when profile rendering requests the reference.
- Assignment clear delegates to `ControlCenterService.release_worker`.
- SQLite event log is append-only and stores only event ID/type/worker/project/timestamp; no payload/secret/token/command/stdout/stderr columns.
- `build_local_lifecycle_coordinator()` wires ControlCenterService + config store + observer + exact process controller + SQLite journal + evidence log.
- Targeted assembly/event tests passed after using a fresh pytest basetemp; earlier transient failures were pytest temp-state noise.
- Full suite: PASS.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Static assembly forbidden scan clean; event-log sensitive-field scan clean.
- No live tunnel/process/Worker 3 mutation.

## Checkpoint log

- [2026-08-20] Opened after lifecycle coordinator commit `045e7df`.
- [2026-08-20] Coordination commit `111b78c`.
- [2026-08-20] RED missing-module checkpoint.
- [2026-08-20] GREEN targeted/full verification. Work order complete.
