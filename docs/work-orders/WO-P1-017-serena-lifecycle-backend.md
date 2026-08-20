# WO-P1-017: Serena Lifecycle Backend Composition

Status: completed
Lane/files: `src/a_conductor/serena_lifecycle_backend.py`, `src/a_conductor/__init__.py`, `tests/test_serena_lifecycle_backend.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-017-serena-lifecycle-backend.md`
Branch: main
Model tier: mid/high

## Goal

Build the Serena-specific `LifecycleStepBackend` composition layer that executes only symbolic steps already approved by the pure lifecycle planner/executor. The backend delegates host mutation to injected bounded collaborators and contains no direct host I/O.

## Acceptance evidence

- RED: `ModuleNotFoundError: a_conductor.serena_lifecycle_backend` before implementation.
- Every supported `LifecycleStep` maps to one explicit collaborator operation.
- Invalid step fails closed with `UNSUPPORTED_LIFECYCLE_STEP`.
- `START_OWNED_PROCESS`: `STARTED`/`ALREADY_RUNNING` => success; refusal/recovery propagate safely.
- `TARGETED_STOP`: `STOPPED`/`NOT_RUNNING` => success; refusal/recovery propagate safely.
- Unexpected process mutation state => `UNEXPECTED_OWNED_PROCESS_STATE` with recovery required.
- Collaborator exception is intentionally not swallowed; `LifecycleExecutor` remains authoritative for mutating-step uncertainty classification.
- Targeted tests: `24 passed`.
- Full suite: `274 passed in 3.79s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Static composition I/O scan: no subprocess/SQLite/socket/url/open/Path host-I/O primitive.
- No real Serena/tunnel/A-Worker 3 mutation.

## Reuse

- `lifecycle.py` symbolic plans.
- `lifecycle_executor.py` transaction/checkpoint authority.
- `owned_process.py` exact-owned mutation primitive.
- `serena_runtime.py` configuration models.

## Forbidden maintained

- No broad process termination.
- No arbitrary shell command execution.
- No secret resolution/logging in composition layer.
- No direct SQLite journal writes.
- No live Serena/tunnel/A-Worker 3 mutation.

## Checkpoint log

- [2026-08-20] Opened after P1-016 commit `8c4cb8c`; worktree clean.
- [2026-08-20] Coordination commit `ab9d757`.
- [2026-08-20] RED module-missing checkpoint captured.
- [2026-08-20] GREEN targeted 24/24; full suite 274/274; static I/O scan clean. Work order complete.
