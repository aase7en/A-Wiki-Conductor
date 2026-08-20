# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Durable Work-class Runtime Foundation**

## Active work order

`docs/work-orders/WO-P1-038-durable-job-control-service.md`

Status: `IN_PROGRESS`

## Goal

Expose the durable job/native execution foundation through one bounded application service suitable for later Discord/Desktop adapters.

## Completed foundation

- [x] Native execution core.
- [x] Fixed Git/verification adapters.
- [x] Transactional Git mutations.
- [x] Durable job state/checkpoint store.
- [x] Durable job execution coordinator.
- [x] Allowlisted native operation backend.
- [x] Fresh Control Center worker native-adapter assembly (`543b1ab`).

## P1-038 checklist

- [x] Open work order.
- [x] Define control-service contract.
- [ ] Claim + coordination checkpoint commit.
- [ ] Write RED service/composition tests.
- [ ] Implement `job_control.py`.
- [ ] Export bounded public API.
- [ ] Run targeted/full/compileall/diff/static safety verification.
- [ ] Close work order + release claim + commit.

## Next safe action

Claim P1-038, commit coordination checkpoint, then write RED tests for bounded facade and real reopen durability.
