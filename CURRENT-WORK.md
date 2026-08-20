# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / lifecycle safety foundation**

## Active work order

None at this checkpoint. `WO-P1-011` is complete; next planned micro-step is durable lifecycle checkpoint persistence.

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
- [x] Abstract lifecycle transaction executor complete with transaction-scoped durable checkpoint contract.
- [x] P1-011 full suite: 197 passed.

## P1-011 key safety results

- Non-`PROCEED` lifecycle plans never call the backend.
- A successful step is not considered durable-complete until its checkpoint records successfully.
- `transaction_id` is required and checkpoints are 1-based sequenced.
- Backend exception/uncertain outcome on a mutating step -> `RECOVERY_REQUIRED`.
- Checkpoint failure after a mutating step -> `RECOVERY_REQUIRED`; later steps do not run.
- No concrete host/process/filesystem/network/persistence backend exists in the executor.

## Repository state

- Branch: `main`
- HEAD before P1-011 implementation commit: `7d72c3a` coordination checkpoint; implementation batch is ready to commit.
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

`DR-C1-001` — GitHub publication visibility/public-safety. Recommended default: **private-first**.

## Constraints

- No live lifecycle mutation yet.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Next safe action

Commit P1-011, then open a bounded work order for an append-only/idempotent SQLite lifecycle checkpoint journal. This remains local persistence only and does not start/stop any runtime.
