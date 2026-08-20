# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Durable Work-class Runtime Foundation**

## Active work order

`docs/work-orders/WO-P1-036-native-operation-registry.md`

Status: `IN_PROGRESS`

## Goal

Resolve opaque operation refs to enum-backed fixed native adapter calls and return digest-only evidence to the durable job execution coordinator.

## Completed foundation

- [x] Native execution core.
- [x] Fixed Git/verification adapters.
- [x] Transactional Git mutations.
- [x] Durable job state/checkpoint store.
- [x] Durable job execution coordinator (`0de7365`).

## P1-036 checklist

- [x] Open work order.
- [x] Define native operation registry contract.
- [ ] Claim + coordination checkpoint commit.
- [ ] Write RED registry/backend tests.
- [ ] Implement `native_operations.py`.
- [ ] Add end-to-end coordinator/store evidence test.
- [ ] Export bounded public API.
- [ ] Run targeted/full/compileall/diff/static safety verification.
- [ ] Close work order + release claim + commit.

## Next safe action

Claim P1-036, commit coordination checkpoint, then write RED tests proving fixed dispatch and digest-only durable evidence.
