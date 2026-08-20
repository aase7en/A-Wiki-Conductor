# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Durable Work-class Runtime Foundation**

## Active work order

`docs/work-orders/WO-P1-034-durable-job-state.md`

Status: `IN_PROGRESS`

## Goal

Add provider-neutral durable job runtime state around opaque A-Wiki work-order references without duplicating A-Wiki planning/orchestration.

## Completed foundation

- [x] Phase 1 local Control Center MVP.
- [x] Native filesystem/subprocess execution core.
- [x] Fixed Git + verification adapters.
- [x] Transactional exact-file Git stage/commit with optimistic preconditions and hook/signing isolation.
- [x] A-Wiki ↔ A-Conductor responsibility contract.

## P1-034 checklist

- [x] Open work order.
- [x] Reuse gate: classify as `WRAP + EXTEND` of A-Wiki work-order/handoff semantics.
- [x] Define durable job-state contract.
- [ ] Claim + coordination checkpoint commit.
- [ ] Write RED pure transition-policy tests.
- [ ] Implement `job_state.py`.
- [ ] Write RED SQLite store/concurrency/checkpoint tests.
- [ ] Implement `job_store.py`.
- [ ] Export public bounded API.
- [ ] Run targeted/full/compileall/diff/schema safety verification.
- [ ] Close work order + release claim + commit.

## External/deferred gates

- `DR-P1-003`: Worker 3 live Stage B remains `BLOCKED_EXTERNAL` until unique authorized transport provisioning exists.
- A-Wiki companion registration payload is prepared but not yet applied to the A-Wiki repo.
- GitHub remote remains intentionally absent.

## Repository

- branch: `main`
- baseline before P1-034: `23443fe`
- no Git remote

## Next safe action

Claim P1-034, commit docs/coordination checkpoint, then write RED tests for pure state transitions before persistence implementation.
