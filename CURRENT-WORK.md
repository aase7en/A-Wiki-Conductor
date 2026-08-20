# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / pure lifecycle decision policy**

## Active work order

`docs/work-orders/WO-P1-010-lifecycle-decision-planner.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Provider-neutral typed domain models complete.
- [x] Serena runtime-manager contract extracted from validated prototype.
- [x] Runtime safety classifiers + read-only observer + strict I/O backends complete.
- [x] Live read-only Conductor smoke: PID VALID, process OWNED, port OWNED, ready HTTP 200.
- [x] Normalized worker status evaluator complete.
- [x] Reusable in-memory Project/A-Worker registry complete.
- [x] SQLite registry persistence complete; full suite 159 tests.
- [x] WO-P1-009 implementation commit: `f32f192`.

## Active checklist — WO-P1-010

- [x] Open/claim work order.
- [ ] Commit coordination checkpoint before source changes.
- [ ] Write failing START/STOP/RESTART/RELEASE policy tests first.
- [ ] Capture RED result.
- [ ] Implement pure lifecycle context/plan types + decision planner.
- [ ] Run full tests green.
- [ ] Compileall + I/O/mutation scan + diff check.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-010 coordination commit: `f32f192`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

`DR-C1-001` — GitHub publication visibility/public-safety. Recommended default: **private-first**.

## Constraints

- Lifecycle policy is pure and symbolic only.
- No target mutation, cleanup, profile rendering, shell/process/network/filesystem/persistence I/O.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Next safe action

Commit WO-P1-010 coordination checkpoint, then write failing lifecycle-policy tests before implementation.
