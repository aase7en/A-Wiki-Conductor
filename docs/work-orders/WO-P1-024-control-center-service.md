# WO-P1-024: Control Center Application Service

Status: in_progress
Lane/files: `src/a_conductor/control_center.py`, `src/a_conductor/__init__.py`, `tests/test_control_center.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-024-control-center-service.md`
Branch: main
Model tier: mid/high

## Goal

Create the local application-service/facade used by the desktop Projects/Workers screen. It owns registry/persistence transactions and immutable UI projections, but not process lifecycle execution.

## Acceptance

- tests first / RED before implementation;
- fresh persistent store bootstraps exactly A-Worker 1–3 once;
- reopening preserves projects/workers/assignments;
- project registration validates existing directory read-only and never `git init`/modify target;
- deterministic project ID may be generated from normalized path when not supplied;
- duplicate root registration returns the existing project instead of creating path aliases;
- assign enforces existing registry worktree conflict rules and persists atomically after success;
- release requires STOPPED via registry and persists;
- immutable screen snapshot projects each worker with assigned project/display/path and state;
- service exposes no process start/stop yet; lifecycle wiring remains separate;
- persistence failures do not silently report success;
- full suite + compileall + diff/static no-repo-mutation scan pass.

## Forbidden

- No repository mutation or Git command.
- No process/network/tunnel action.
- No task-router/coordination duplication.
- No Git remote/push.

## Checkpoint log

- [2026-08-20] Opened after Stage B provisioning gate checkpoint; local Control Center work remains unblocked.
