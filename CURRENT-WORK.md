# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

None.

## Completed resilient foundation

- AC-RES-001 durable execution record: `0a3040d`
- AC-RES-002 supervised subprocess: `03a623d`
- AC-RES-003 transport-loss state + claim preservation: `f9838a5`
- AC-RES-004 recovery reconciliation + repo identity gate: `bb5dab0`
- AC-RES-005 duplicate execution protection: `a0a2e52`
- AC-RES-006 output backpressure: `9cc3c46`
- AC-RES-007 fake executor + fault injection: completion commit is the immediate transaction

## AC-RES-007 evidence

- 12 deterministic scenario tests; all 10 contract scenarios plus delayed-advance and duplicate-launch-rejection.
- fake advances only via explicit `advance()`; no threads/timers/sleeps/network/real process spawn.
- launch count observable; duplicate request assessed `ATTACH_RUNNING` with job claim preserved; no scenario relaunches (`actual_start_count == 1`).
- transport loss while running preserved the original; completed-before-delivery result recovered without relaunch.
- never-started provenance distinguishable from unknown process state; malformed result and unknown process produce `RECOVERY_REQUIRED` with retry not permitted.
- wrong branch identity blocks recovery before collect.
- 300 KB stdout stays fully durable on disk while AC-RES-006 tail returns bounded bytes.
- package exports: `DeterministicFaultExecutor`, `FakeLaunchObservation`, `FaultScenario`.
- full suite 726 passed, 1 skipped (display-dependent UI test).
- temp stores/repos only; no real Serena/tunnel/PID `25396` mutation.

## Invariant

Do not use real Serena outages as the recovery test harness. Fault scenarios stay explicit and deterministic; production recovery decisions remain in AC-RES-003/004/005/006.

## Next safe action

Open `WO-AC-RES-008` (Serena adapter integration) per the PROJECT-PLAN resilient MVP sequence, with the A-Wiki reuse-before-build gate before any adapter work.
