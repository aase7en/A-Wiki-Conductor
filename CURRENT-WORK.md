# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Durable Work-class Runtime Foundation**

## Active work order

`docs/work-orders/WO-P1-035-durable-job-execution-coordinator.md`

Status: `IN_PROGRESS`

## Goal

Bind one explicitly invoked, already-gated durable job to an injected bounded execution backend while preserving optimistic state, evidence, attempt, and recovery semantics.

## Completed foundation

- [x] Native execution core.
- [x] Fixed Git/verification adapters.
- [x] Transactional Git mutations.
- [x] Durable job state/checkpoint store (`9382442`).

## P1-035 checklist

- [x] Open work order.
- [x] Define durable execution contract.
- [ ] Claim + coordination checkpoint commit.
- [ ] Write RED coordinator tests.
- [ ] Implement `job_execution.py`.
- [ ] Export bounded public API.
- [ ] Run targeted/full/compileall/diff/static safety verification.
- [ ] Close work order + release claim + commit.

## Deferred

No scheduler/background loop, model routing, worker routing, automatic retries, or concrete operation-ref resolver in this work order.

## Next safe action

Claim P1-035, commit coordination checkpoint, then write RED tests against an actual `SQLiteJobStore` plus injected fake backend.
