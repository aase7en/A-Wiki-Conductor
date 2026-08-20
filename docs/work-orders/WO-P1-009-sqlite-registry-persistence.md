# WO-P1-009: SQLite Registry Persistence

Status: done
Lane/files: `src/a_conductor/persistence.py`, `src/a_conductor/__init__.py`, `tests/test_persistence.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-009-sqlite-registry-persistence.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Persist the Phase 1 Project/A-Worker registry locally with stdlib SQLite so assignments and worker state survive application restart, without implementing the later durable task broker yet.

Acceptance:
- tests written before implementation;
- stdlib `sqlite3` only;
- schema has explicit version metadata;
- Project, Worker, AssignmentRecord/mutation flag round-trip through SQLite into a valid `ControlPlaneRegistry`;
- worker state round-trips without bypassing registry validation;
- writes are transactional and foreign keys enabled;
- database parent directory may be created as an explicit persistence action;
- invalid/corrupt persisted enum/reference data fails explicitly rather than being silently repaired;
- no credentials/secrets stored;
- no process/network/UI/task-broker behavior;
- full tests, compileall, and `git diff --check` pass.

## Reference pattern

- `src/a_conductor/registry.py` is the validated in-memory authority model.
- `PROJECT-PLAN.md` Control Center requirement: remember projects/assignments.
- C0 recommendation: SQLite first; no Redis/Kafka for local MVP.

## Steps

1. Write failing SQLite round-trip/schema/corruption tests.
2. Capture RED result.
3. Implement versioned `SQLiteRegistryStore` minimally.
4. Run tests to GREEN.
5. Review transaction/foreign-key behavior and scope boundary vs future task broker.
6. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No task/lease/evidence broker tables beyond registry persistence.
- No migration framework dependency.
- No process/network/UI behavior.
- No credentials/secrets.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- `python -m pytest tests -q --basetemp=runtime/pytest-temp`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after reusable worker-pool registry commit `61db9af`. Scope is Phase 1 registry persistence only, not the later task broker.

- [2026-08-20] RED checkpoint: `src/a_conductor/persistence.py` confirmed absent; targeted persistence tests failed during collection with `ModuleNotFoundError: a_conductor.persistence` as expected.

- [2026-08-20] GREEN checkpoint: implemented stdlib-only versioned `SQLiteRegistryStore` for Project/Worker/Assignment registry state. Targeted persistence tests 9 passed; full suite 159 passed; compileall PASS; `git diff --check` PASS. Corrupt worker state/schema version/assignment reference fails explicitly. No task/lease/evidence broker tables, process/network/UI behavior, or secrets added.
