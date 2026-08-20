# WO-AC-RES-007: Fake Executor + Fault Injection

Status: complete
Lane/files: `src/a_conductor/fault_injection.py`, `src/a_conductor/__init__.py`, `tests/test_resilient_fault_injection.py`, `docs/contracts/fault-injection.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-AC-RES-007-fault-injection.md`
Branch: main
Model tier: high

## Goal

Provide a deterministic local fake executor that simulates real transport/process timing failures and proves the AC-RES-001..006 recovery primitives without intentionally breaking real Serena.

## Reuse classification

`NEW TEST SUPPORT + WRAP`: the fake is test infrastructure only. Production recovery decisions continue to use AC-RES-003/004/005/006; the fake must not become a second production execution engine.

## Required scenarios

- normal success
- disconnect before launch
- disconnect immediately after launch while original remains running
- disconnect mid-command
- disconnect after completion before result delivery
- delayed execution
- large stdout
- nonzero exit
- malformed result
- unknown process state

## Acceptance

- fake has deterministic explicit scenario + manual `advance()`; no sleep/race dependency.
- launch count is observable to prove no duplicate launch.
- fake can write durable stdout/stderr/result evidence under the record run directory.
- fake implements the supervised inspect/collect shape used by AC-RES-004 tests.
- integrated tests prove transport loss while running preserves original and duplicate request attaches.
- completed-before-delivery result is recovered without relaunch.
- never-started transport loss is distinguishable from started/unknown provenance.
- unknown process/result returns recovery required, not retry.
- wrong repo identity blocks recovery.
- large stdout stays durable and AC-RES-006 returns bounded output.
- no real Serena/PID 25396 mutation.

## Micro-steps

- [x] 007-A contract + coordination checkpoint
- [x] 007-B RED fake scenario tests
- [x] 007-C implement deterministic fake
- [x] 007-D integrated AC-RES recovery/fault tests
- [x] 007-E regression/safety verification
- [x] 007-F close/commit

## Forbidden

- No real Serena outage injection.
- No real worker/tunnel restart/kill.
- No background thread/timer race harness.
- No production automatic retry/failover.
- No A-Wiki/Phase6 mutation.

## Checkpoint log

- [2026-08-20] Opened from clean AC-RES-006 completion `9cc3c46`.
- [2026-08-20] Resume reconciliation (GLM 5.3/ZCode): fake implementation + 12 scenario tests found present-but-untracked and passing; verified against contract/acceptance, added package exports, full regression, closure.

## Completion evidence

- 12 deterministic scenario tests passed, covering all 10 contract scenarios plus delayed-advance and duplicate-launch-rejection.
- fake advances only through explicit `advance()`; no threads, timers, sleeps, network, or real process spawn.
- `actual_start_count` stays 1 in every scenario: duplicate request assessed `ATTACH_RUNNING` with job claim preserved; completed-before-delivery result recovered without relaunch.
- never-started provenance is distinguishable from unknown process state; malformed result and unknown process return `RECOVERY_REQUIRED` with retry not permitted.
- wrong branch identity blocks recovery (`RECOVERY_BLOCKED`) before any collect.
- 300 KB stdout stays fully durable on disk while AC-RES-006 tail returns bounded bytes.
- integrated with production AC-RES-003/004/005/006 services; the fake encodes no production recovery decision.
- package exports added: `DeterministicFaultExecutor`, `FakeLaunchObservation`, `FaultScenario`.
- full suite 726 passed, 1 skipped (display-dependent UI test).
- temp stores/repos only; no real Serena/tunnel mutation; PID `25396` unchanged.
