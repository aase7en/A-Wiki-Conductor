# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / concrete read-only Windows I/O**

## Active work order

`docs/work-orders/WO-P1-007-readonly-io-backends.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Provider-neutral typed domain models complete.
- [x] Serena runtime-manager contract extracted from validated prototype.
- [x] Pure runtime ownership/collision classifiers complete.
- [x] Serena reusable worker config + dynamic project binding complete.
- [x] Read-only Windows runtime observer boundary complete.
- [x] Normalized pure A-Worker status evaluator complete; full suite 113 tests.
- [x] WO-P1-006 implementation commit: `26ea225`.

## Active checklist — WO-P1-007

- [x] Open/claim work order.
- [ ] Commit coordination checkpoint before source changes.
- [ ] Write failing strict-backend tests first.
- [ ] Capture RED result.
- [ ] Implement allowlisted PowerShell inspection runner.
- [ ] Implement loopback-only `/readyz` HTTP probe.
- [ ] Run full tests green.
- [ ] Compileall + mutation/security scan + diff check.
- [ ] Optional live read-only smoke against current Conductor runtime.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-007 coordination commit: `26ea225`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp to avoid Hermes temp cleanup noise.

## DECISION_REQUIRED

`DR-C1-001` — GitHub publication visibility/public-safety. Recommended default: **private-first**.

## Constraints

- Concrete I/O is read-only and allowlisted only.
- No lifecycle mutation, generic shell, non-loopback HTTP, or credential access.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Next safe action

Commit WO-P1-007 coordination checkpoint, then write failing security/backend tests before implementation.
