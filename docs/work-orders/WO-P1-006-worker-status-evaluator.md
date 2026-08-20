# WO-P1-006: Normalized A-Worker Status Evaluator

Status: in_progress
Lane/files: `src/a_conductor/worker_status.py`, `src/a_conductor/__init__.py`, `tests/test_worker_status.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-006-worker-status-evaluator.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement pure deterministic status evaluation that maps observed process/port/tunnel/readiness/project-identity facts into the canonical A-Worker health states used by future CLI/UI.

Acceptance:
- tests written before implementation;
- evaluator is pure and performs no I/O;
- precedence is deterministic for project missing, PID mismatch, tunnel collision, port collision, unknown ownership, stopped/stale process, unhealthy readiness, project-identity failure, ready/busy;
- stale PID metadata does not become a destructive cleanup action here;
- output contains normalized state plus safe reason/error code and non-secret PID/project identifiers;
- no provider/model/product names required by evaluator;
- `pytest`, `compileall`, mutation/import scan, and `git diff --check` pass.

## Reference pattern

- `docs/contracts/serena-runtime-manager.md` sections 12-13.
- `src/a_conductor/runtime_safety.py`.
- `src/a_conductor/windows_observer.py`.
- `src/a_conductor/domain.py::HealthState` vocabulary.

## Steps

1. Write failing status-precedence tests.
2. Capture RED result.
3. Implement immutable observation/status models + pure evaluator.
4. Run tests to GREEN.
5. Review precedence against runtime-manager contract.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No process/network/filesystem I/O.
- No cleanup/start/stop/restart logic.
- No UI.
- No broker/provider integration.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `pytest -q --basetemp=runtime/pytest-temp`
- `python -m compileall -q src`
- `git diff --check`
- scan evaluator source for I/O/mutation imports/primitives.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after read-only Windows observer commit `af1979e`. Scope is pure normalized status evaluation only.
