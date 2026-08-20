# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Durable Work-class Runtime Foundation**

## Active work order

None.

Most recently completed: `WO-P1-034 — Durable Job State + Checkpoint Store`.

## Completed foundation

- [x] Phase 1 local Control Center MVP.
- [x] Native filesystem/subprocess execution core.
- [x] Fixed Git + verification adapters.
- [x] Transactional exact-file Git stage/commit with optimistic preconditions and hook/signing isolation.
- [x] Durable job state around opaque A-Wiki work-order refs.
- [x] Optimistic job versioning, worker claim state, attempt budgets, recovery classification, append-only checkpoint/evidence metadata.
- [x] P1-034 verification: 31 targeted + 492 full-suite tests, compileall/diff/schema safety PASS; Conductor PID 25396 preserved.

## External/deferred gates

- `DR-P1-003`: Worker 3 live Stage B remains `BLOCKED_EXTERNAL` until unique authorized transport provisioning exists.
- A-Wiki companion registration payload is prepared but not yet applied.
- GitHub remote remains intentionally absent.

## Next safe action

Open the next bounded work order for the durable job service/runner boundary: bind a durable job to an execution adapter through explicit checkpoints without adding background scheduling or duplicating A-Wiki planning.
