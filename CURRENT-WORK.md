# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / lifecycle transaction executor**

## Active work order

`docs/work-orders/WO-P1-011-lifecycle-transaction-executor.md`

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
- [x] Pure START/STOP/RESTART/RELEASE lifecycle decision planner complete.
- [x] P1-010 implementation commit: `1b36658a91f462778d04cbd88f77674a529b98dd`.
- [x] Full suite after P1-010: 177 passed.

## Active checklist — WO-P1-011

- [x] Reconcile actual HEAD/worktree after context handoff.
- [x] Open/claim work order.
- [ ] Commit coordination checkpoint before source changes.
- [ ] Write failing transaction/checkpoint tests first.
- [ ] Capture RED result.
- [ ] Implement injected lifecycle step backend + checkpoint sink protocols.
- [ ] Ensure non-PROCEED plans never call backend.
- [ ] Ensure every successful PROCEED step checkpoints before next step.
- [ ] Ensure failed/uncertain mutation and checkpoint-after-mutation failure stop with recovery semantics.
- [ ] Run full tests green.
- [ ] Compileall + I/O/mutation scan + diff check.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-011 coordination commit: `1b36658a91f462778d04cbd88f77674a529b98dd`
- Git remote: none
- Worktree reconciliation before P1-011: only the new WO file was untracked; no unrelated drift found.
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

`DR-C1-001` — GitHub publication visibility/public-safety. Recommended default: **private-first**.

## Constraints

- Executor is abstract/injected only; no concrete host/process mutation backend.
- No subprocess/PowerShell/network/filesystem/SQLite implementation in `lifecycle_executor.py`.
- No live start/stop/restart of current Conductor/Phase6 runtime.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Next safe action

Commit the P1-011 coordination checkpoint, then write failing lifecycle transaction/checkpoint tests before implementation.
