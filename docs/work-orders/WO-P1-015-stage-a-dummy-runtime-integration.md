# WO-P1-015: Stage A Self-Owned Dummy Runtime Integration

Status: in_progress
Lane/files: `tests/support/dummy_runtime.py`, `tests/test_stage_a_dummy_runtime.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-015-stage-a-dummy-runtime-integration.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Prove the lifecycle planner/executor/checkpoint journal against a **real child process owned entirely by the test harness**, without introducing a production mutation backend or touching Serena/tunnel/runtime workers.

Acceptance:
- tests/helper written before any production mutation backend;
- dummy runtime is launched only from the test process with `sys.executable`, unique marker, temp-owned files, and loopback-only `/readyz` health;
- test harness retains its own `Popen` ownership object and may terminate only that child;
- START lifecycle runs through executor to a live READY dummy process and persists ordered checkpoints;
- repeated START is planned/executed as NOOP without spawning a second child;
- STOP lifecycle terminates only the harness-owned child and checkpoints through released state;
- injected checkpoint failure after START mutation returns `RECOVERY_REQUIRED` and prevents later lifecycle steps;
- test cleanup terminates only the exact child object created by that test;
- no Serena/tunnel/A-Worker 3/external repo mutation;
- full tests, compileall, `git diff --check`, and active-runtime preservation check pass.

## Reference pattern

- `docs/contracts/lifecycle-integration-test-strategy.md` Stage A.
- `src/a_conductor/lifecycle.py`.
- `src/a_conductor/lifecycle_executor.py`.
- `src/a_conductor/lifecycle_journal.py`.

## Steps

1. Commit coordination checkpoint.
2. Add dummy loopback runtime helper under tests.
3. Write failing/real integration tests around test-owned backend behavior.
4. Execute Stage A tests only.
5. Confirm active Conductor health remains READY and PID unchanged after tests.
6. Run full suite and static checks.
7. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No production process mutation backend in `src/`.
- No process lookup/kill by broad executable name.
- No Serena/tunnel/connector calls.
- No provisioning of A-Worker 3.
- No writes to `serena-test`, A-Wiki, Phase6, or external runtime roots.
- No Git remote/push.

## Verify commands

- Stage A targeted tests with local pytest basetemp.
- full `python -m pytest tests -q --basetemp=runtime/pytest-temp`.
- `python -m compileall -q src tests/support`.
- `git diff --check`.
- read-only Conductor PID/health before/after test.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after lifecycle integration strategy commit `ee5a75a`. Stage A is test-harness-owned process integration only; no production mutation backend or Serena/tunnel target is in scope.
