# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / reusable worker pool registry**

## Active work order

`docs/work-orders/WO-P1-008-worker-pool-registry.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Provider-neutral typed domain models complete.
- [x] Serena runtime-manager contract extracted from validated prototype.
- [x] Pure runtime ownership/collision classifiers complete.
- [x] Serena reusable worker config + dynamic project binding complete.
- [x] Read-only Windows observer + strict concrete read-only backends complete.
- [x] Live read-only Conductor smoke: PID VALID, process OWNED, port OWNED, ready HTTP 200.
- [x] Normalized A-Worker status evaluator complete.
- [x] WO-P1-007 implementation commit: `e0682cc`.

## Active checklist — WO-P1-008

- [x] Open/claim work order.
- [ ] Commit coordination checkpoint before source changes.
- [ ] Write failing worker/project registry tests first.
- [ ] Capture RED result.
- [ ] Implement in-memory registry + Windows worktree normalization.
- [ ] Run full tests green.
- [ ] Compileall + I/O/persistence scan + diff check.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-008 coordination commit: `e0682cc`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

`DR-C1-001` — GitHub publication visibility/public-safety. Recommended default: **private-first**.

## Constraints

- Registry is in-memory only and side-effect free with respect to filesystem/process/network.
- Do not duplicate A-Wiki work-order/claim semantics.
- No runtime lifecycle mutation.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Next safe action

Commit WO-P1-008 coordination checkpoint, then write failing registry tests before implementation.
