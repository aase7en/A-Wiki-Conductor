# WO-P1-011: Lifecycle Transaction Executor + Checkpoint Contract

Status: done
Lane/files: `src/a_conductor/lifecycle_executor.py`, `src/a_conductor/__init__.py`, `tests/test_lifecycle_executor.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-011-lifecycle-transaction-executor.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement a provider/OS-neutral executor for an already-approved `LifecyclePlan`, using injected step backend and checkpoint sink only. No concrete host mutation backend is introduced in this work order.

Acceptance:
- tests written before implementation;
- `REFUSE`, `NOOP`, and `RECOVERY_REQUIRED` plans never call the mutation backend;
- `PROCEED` executes symbolic steps in exact plan order;
- each successful step produces a checkpoint before the next step;
- step failure stops subsequent execution;
- backend-declared uncertain/partial mutation returns `RECOVERY_REQUIRED`;
- checkpoint failure after a mutating step returns `RECOVERY_REQUIRED` and never proceeds;
- completed result records completed symbolic steps and evidence refs;
- no subprocess/filesystem/network/persistence implementation in this module;
- full tests, compileall, I/O scan, and `git diff --check` pass.

## Reference pattern

- `src/a_conductor/lifecycle.py`.
- `docs/contracts/core-domain.md` checkpoint/recovery invariants.
- `PROJECT CONTINUITY` protocol: durable checkpoint after meaningful mutation boundaries.

## Steps

1. Write failing transaction/checkpoint tests.
2. Capture RED result.
3. Implement injected backend/checkpoint protocols and executor.
4. Run tests to GREEN.
5. Review mutation-step checkpoint failure semantics.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No concrete process/tunnel/filesystem mutation backend.
- No subprocess/PowerShell/network/SQLite implementation.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `python -m pytest tests -q --basetemp=runtime/pytest-temp`
- `python -m compileall -q src`
- `git diff --check`
- source scan for I/O/mutation imports.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after pure lifecycle policy commit `1b36658`. This executor remains abstract/injected; concrete target mutation is intentionally deferred.

- [2026-08-20] RED checkpoint: `src/a_conductor/lifecycle_executor.py` confirmed absent; targeted executor tests failed during collection with `ModuleNotFoundError: a_conductor.lifecycle_executor` as expected. Durable semantics chosen: `completed_steps` contains only successfully checkpointed steps.

- [2026-08-20] Contract hardening: added required `transaction_id` and 1-based `sequence_no` to checkpoints/results so durable stores can distinguish concurrent/retried lifecycle transactions. Blank transaction IDs fail before backend calls.
- [2026-08-20] GREEN checkpoint: implemented abstract lifecycle transaction executor with injected step backend/checkpoint sink, strict non-PROCEED no-backend behavior, step->checkpoint ordering, halt-on-failure, recovery on backend uncertainty or checkpoint failure after mutating steps, and safe normalization of backend exceptions. Targeted tests 20 passed; full suite 197 passed; compileall PASS; `git diff --check` PASS; I/O/mutation scan clean. No concrete host mutation backend added.
