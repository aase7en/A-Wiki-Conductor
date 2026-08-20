# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

`docs/work-orders/WO-AC-RES-007-fault-injection.md`

Status: `IN_PROGRESS`

## Completed resilient foundation

- AC-RES-001 durable execution record: `0a3040d`
- AC-RES-002 supervised subprocess: `03a623d`
- AC-RES-003 transport-loss state + claim preservation: `f9838a5`
- AC-RES-004 recovery reconciliation + repo identity gate: `bb5dab0`
- AC-RES-005 duplicate execution protection: `a0a2e52`
- AC-RES-006 output backpressure: `9cc3c46`

## AC-RES-007 micro-steps

- [x] 007-A contract + coordination checkpoint
- [ ] 007-B RED deterministic fake scenario tests
- [ ] 007-C implement fake executor
- [ ] 007-D integrated AC-RES recovery/fault tests
- [ ] 007-E regression + safety verification
- [ ] 007-F close/commit

## Invariant

Do not use real Serena outages as the recovery test harness. Fault scenarios are explicit and deterministic, and production recovery decisions stay in AC-RES-003/004/005/006.

## Next safe action

Commit coordination checkpoint, then write RED tests for fake lifecycle facts and integrated no-duplicate/recovery/backpressure behavior using temp stores/repos only.
