# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / Windows owned-process controller**

## Active work order

`docs/work-orders/WO-P1-016-windows-owned-process-controller.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] Contracts/local Git/provider-neutral runtime safety stack complete.
- [x] Registry + SQLite persistence complete.
- [x] Lifecycle planner/executor/journal/recovery stack complete.
- [x] Stage A self-owned dummy-runtime integration GREEN; full suite 235 passed.
- [x] P1-015 commit: `bf9d1eb`.

## Active checklist — WO-P1-016

- [x] Open/claim work order.
- [ ] Commit coordination checkpoint.
- [ ] Inspect validated start/stop scripts read-only.
- [ ] Capture active Conductor PID/health baseline.
- [ ] Write failing owned-process tests first.
- [ ] Implement allowed-root spec + exact-PID controller.
- [ ] Run integration only against Stage A dummy process.
- [ ] Confirm active Conductor PID/health unchanged.
- [ ] Run full suite + compileall + diff/mutation review.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-016 coordination commit: `bf9d1eb`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.

## DECISION_REQUIRED

- `DR-C1-001`: GitHub publication; private-first recommended; no remote/push.
- `DR-P1-002`: Stage A production mutation may target only self-owned dummy resources. Real Serena/tunnel/A-Worker 3 remains gated.

## Constraints

- Exact owned process only; no broad kill.
- No `shell=True`.
- Mutable PID/log paths restricted to allowed runtime root.
- No Serena/tunnel/A-Worker 3 mutation.
- No writes to `serena-test`, A-Wiki, Phase6, or external runtime roots.

## Next safe action

Commit coordination state, inspect validated prototype start/stop ownership pattern read-only, then write failing tests before implementation.
