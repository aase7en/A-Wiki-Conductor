# WO-P1-012: SQLite Lifecycle Checkpoint Journal

Status: done
Lane/files: `src/a_conductor/lifecycle_journal.py`, `src/a_conductor/__init__.py`, `tests/test_lifecycle_journal.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-012-sqlite-lifecycle-journal.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Implement a durable local SQLite checkpoint sink for `LifecycleExecutor` without adding a task broker or any host/runtime mutation capability.

Acceptance:
- tests written before implementation;
- stdlib `sqlite3` only;
- journal is append-only through its public API;
- checkpoint identity is `(transaction_id, sequence_no)`;
- writing the exact same checkpoint twice is idempotent;
- same transaction/sequence with different payload fails explicitly and never overwrites history;
- sequence numbers are contiguous from 1 for new writes; gaps are rejected;
- checkpoints load in sequence order and reconstruct typed `LifecycleCheckpoint` values;
- invalid persisted enum/sequence/component schema data fails explicitly;
- journal can coexist in the same SQLite file as Phase 1 registry tables without deleting/replacing them;
- no `tasks`, `leases`, or generic broker tables are introduced;
- no process/network/UI/runtime lifecycle mutation;
- full tests, compileall, and `git diff --check` pass.

## Reference pattern

- `src/a_conductor/lifecycle_executor.py` checkpoint sink contract.
- `src/a_conductor/persistence.py` stdlib SQLite transaction/error patterns.
- Continuity invariant: mutation is not durable-complete until checkpoint persistence succeeds.

## Steps

1. Write failing journal/idempotence/conflict/gap/coexistence tests.
2. Capture RED result.
3. Implement versioned `SQLiteLifecycleJournal` minimally.
4. Run targeted then full tests to GREEN.
5. Review append-only and corruption behavior.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No task/lease scheduler/broker tables.
- No checkpoint UPDATE/DELETE API.
- No process/tunnel/Serena mutation.
- No network/UI/provider integration.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `python -m pytest tests -q --basetemp=runtime/pytest-temp`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after lifecycle transaction executor commit `74bc59b`. Scope is append-only lifecycle checkpoint persistence only; future task broker remains out of scope.

- [2026-08-20] RED checkpoint: `src/a_conductor/lifecycle_journal.py` confirmed absent; targeted journal tests failed during collection with `ModuleNotFoundError: a_conductor.lifecycle_journal` as expected.

- [2026-08-20] GREEN checkpoint: implemented versioned append-only `SQLiteLifecycleJournal` with transaction/sequence identity, exact-duplicate idempotence, conflict/gap rejection, typed ordered load, explicit corruption/schema errors, and coexistence with registry tables. Targeted journal tests 19 passed; full suite 216 passed; compileall PASS; `git diff --check` PASS; source scan shows no UPDATE/DELETE path for lifecycle checkpoint history. No task/lease broker or runtime mutation added.
