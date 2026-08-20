# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Resilient Execution Supervisor MVP**

## Active work order

`docs/work-orders/WO-AC-RES-008-serena-transport-adapter.md`

Status: `IN_PROGRESS`

## Completed resilient foundation

- AC-RES-001 durable execution record: `0a3040d`
- AC-RES-002 supervised subprocess: `03a623d`
- AC-RES-003 transport-loss state + claim preservation: `f9838a5`
- AC-RES-004 recovery reconciliation + repo identity gate: `bb5dab0`
- AC-RES-005 duplicate execution protection: `a0a2e52`
- AC-RES-006 output backpressure: `9cc3c46`
- AC-RES-007 fake executor + fault injection: `97f6a06`

## AC-RES-008 micro-steps

- [x] 008-A reuse gate + coordination + contract checkpoint
- [ ] 008-B RED adapter scenario tests
- [ ] 008-C implement deterministic mapping + binding observer
- [ ] 008-D integrated recovery tests via fake executor
- [ ] 008-E regression + safety verification
- [ ] 008-F close/commit/push

## Infrastructure note

GitHub remote created 2026-08-20 (explicit user decision): private repo `aase7en/A-Wiki-Conductor`; `main` pushed and tracking `origin/main`.

## Invariant

Do not use real Serena outages as the recovery test harness. The adapter maps observations only; transport/recovery/dedup/artifact decisions stay in AC-RES-003/004/005/006.

## Next safe action

Write RED deterministic tests for `serena_transport_adapter` event classification and binding identity mapping, then implement the mapping without I/O.
