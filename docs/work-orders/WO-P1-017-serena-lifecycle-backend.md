# WO-P1-017: Serena Lifecycle Backend Composition

Status: in_progress
Lane/files: `src/a_conductor/serena_lifecycle_backend.py`, `src/a_conductor/__init__.py`, `tests/test_serena_lifecycle_backend.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-017-serena-lifecycle-backend.md`
Branch: main
Model tier: mid/high

## Goal + Acceptance criteria

Build the Serena-specific `LifecycleStepBackend` composition layer that executes only symbolic steps already approved by the pure lifecycle planner/executor. The backend must delegate host mutation to injected bounded collaborators; it must not contain broad shell/process/network behavior itself.

Acceptance:
- tests written before implementation;
- every supported `LifecycleStep` maps to one explicit collaborator operation;
- unsupported/invalid step state fails closed;
- mutating process steps delegate only to the existing exact-owned process controller adapter;
- backend translates collaborator outcomes into `LifecycleStepResult` without leaking secrets/raw command lines;
- `START_OWNED_PROCESS` accepts `STARTED` or idempotent `ALREADY_RUNNING` as success;
- `TARGETED_STOP` accepts `STOPPED` or idempotent `NOT_RUNNING` as success;
- recovery-required owned-process outcomes propagate `recovery_required=True`;
- `WAIT_READY`, project identity, release verification, assignment clearing, evidence emission are explicit injected boundaries;
- no real Serena/tunnel/A-Worker 3 mutation in this work order;
- targeted tests + full suite + compileall + `git diff --check` pass.

## Reuse

- `src/a_conductor/lifecycle.py` symbolic steps.
- `src/a_conductor/lifecycle_executor.py` backend/checkpoint execution contract.
- `src/a_conductor/owned_process.py` exact-owned mutation primitive.
- `src/a_conductor/serena_runtime.py` worker/project configuration models.

## Forbidden

- No broad process termination.
- No arbitrary shell command execution.
- No secret resolution/logging in this composition layer.
- No direct SQLite journal writes; executor/checkpoint sink owns that boundary.
- No real Serena/tunnel/A-Worker 3 mutation.
- No Git remote/push.

## Steps

1. Commit coordination checkpoint.
2. Write RED tests for step mapping/outcome propagation.
3. Implement backend composition only.
4. Run targeted tests.
5. Run full suite/compileall/diff/static I/O scan.
6. Update work order/current-work/handoff and commit.

## Checkpoint log

- [2026-08-20] Opened after P1-016 commit `8c4cb8c`; worktree clean. Stage B live integration remains gated by `DR-P1-002`.
