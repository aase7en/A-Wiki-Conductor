# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / durable lifecycle checkpoint journal**

## Active work order

`docs/work-orders/WO-P1-012-sqlite-lifecycle-journal.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Provider-neutral typed domain models complete.
- [x] Serena runtime-manager contract extracted from validated prototype.
- [x] Runtime safety classifiers + read-only observer + strict Windows I/O backends complete.
- [x] Live read-only Conductor smoke: PID VALID, process OWNED, port OWNED, ready HTTP 200.
- [x] Normalized worker status evaluator complete.
- [x] Reusable Project/A-Worker registry + SQLite persistence complete.
- [x] Pure lifecycle decision planner complete.
- [x] Abstract lifecycle transaction executor with transaction-scoped checkpoints complete.
- [x] P1-011 implementation commit: `74bc59b`.
- [x] Full suite after P1-011: 197 passed.

## Active checklist — WO-P1-012

- [x] Open/claim work order.
- [ ] Commit coordination checkpoint before source changes.
- [ ] Write failing append-only/idempotence/conflict/gap/coexistence tests first.
- [ ] Capture RED result.
- [ ] Implement versioned `SQLiteLifecycleJournal`.
- [ ] Run targeted and full tests green.
- [ ] Compileall + diff check + append-only/schema review.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-012 coordination commit: `74bc59b`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

`DR-C1-001` — GitHub publication visibility/public-safety. Recommended default: **private-first**.

## Constraints

- Lifecycle journal only; no task/lease scheduler/broker tables.
- Append-only public API; conflicting duplicate checkpoints must never overwrite history.
- No live process/tunnel/Serena lifecycle mutation.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Next safe action

Commit the WO-P1-012 coordination checkpoint, then write failing SQLite lifecycle journal tests before implementation.
