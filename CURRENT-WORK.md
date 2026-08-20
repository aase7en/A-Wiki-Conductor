# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / SQLite registry persistence**

## Active work order

`docs/work-orders/WO-P1-009-sqlite-registry-persistence.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Provider-neutral typed domain models complete.
- [x] Serena runtime-manager contract extracted from validated prototype.
- [x] Runtime safety classifiers, observer, strict read-only backends, normalized worker status complete.
- [x] Live read-only Conductor smoke: PID VALID, process OWNED, port OWNED, ready HTTP 200.
- [x] Reusable in-memory Project/A-Worker registry complete; full suite 150 tests.
- [x] WO-P1-008 implementation commit: `61db9af`.

## Active checklist — WO-P1-009

- [x] Open/claim work order.
- [ ] Commit coordination checkpoint before source changes.
- [ ] Write failing SQLite round-trip/schema/corruption tests first.
- [ ] Capture RED result.
- [ ] Implement versioned `SQLiteRegistryStore`.
- [ ] Run full tests green.
- [ ] Compileall + diff check + persistence-boundary review.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-009 coordination commit: `61db9af`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

`DR-C1-001` — GitHub publication visibility/public-safety. Recommended default: **private-first**.

## Constraints

- SQLite stores registry state only; no task broker tables yet.
- stdlib-only; no migration framework dependency.
- No process/network/UI behavior.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Next safe action

Commit WO-P1-009 coordination checkpoint, then write failing persistence tests before implementation.
