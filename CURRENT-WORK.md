# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / pre-live-lifecycle safety checkpoint**

## Active work order

None. `WO-P1-013` is complete. The next implementation boundary is blocked by `DR-P1-002` because concrete lifecycle code can affect live Serena/tunnel processes.

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Provider-neutral typed domain models complete.
- [x] Serena runtime-manager contract extracted from validated prototype.
- [x] Pure runtime ownership/collision classifiers complete.
- [x] Reusable Serena worker config + dynamic project binding complete.
- [x] Read-only Windows observer + strict allowlisted Windows I/O complete.
- [x] Live **read-only** Conductor smoke: PID VALID, process OWNED, port OWNED, `/readyz` HTTP 200.
- [x] Normalized A-Worker status evaluator complete.
- [x] Reusable Project/A-Worker registry + SQLite persistence complete.
- [x] Pure START/STOP/RESTART/RELEASE lifecycle decision planner complete.
- [x] Abstract checkpointed lifecycle transaction executor complete.
- [x] Append-only/idempotent SQLite lifecycle journal complete.
- [x] Pure lifecycle recovery/resume planner complete.
- [x] Full suite after P1-013: **233 passed**.

## P1-013 recovery guarantees

- Journal checkpoints must match the approved lifecycle plan as an exact prefix.
- Transaction/action/sequence/step mismatch -> `REFUSE`.
- `CONSISTENT_WITH_JOURNAL` is the only reconciliation state that may return `RESUME`.
- `MUTATION_AHEAD_OF_JOURNAL` or `UNKNOWN` -> `RECOVERY_REQUIRED`.
- `UNEXPECTED_DRIFT` -> `REFUSE`.
- No vanished-worker mutation is blindly repeated from journal absence alone.

## Repository state

- Branch: `main`
- HEAD before P1-013 implementation commit: `c74fa12` coordination checkpoint; verified P1-013 implementation batch is ready to commit.
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Need explicit visibility/public-safety decision before GitHub remote creation. Recommended default: **private-first**.

### DR-P1-002 — Live lifecycle integration test strategy

The next concrete backend will gain capability to render runtime profiles and start/stop owned Serena/tunnel processes. Testing it against either current validated worker (`Sunday-Conducter` or Phase6) can intentionally disconnect an active work session.

Recommended resolution: **create/use a dedicated free/sacrificial A-Worker test slot (prefer A-Worker 3) with isolated runtime root, SERENA_HOME, health port, tunnel/runtime binding, logs, and a disposable/read-only test project before any live start/stop test.**

Do not use active Conductor or Phase6 workers as the first mutation target.

## Constraints

- No live process/tunnel/Serena mutation until DR-P1-002 is resolved and a dedicated test target is identified.
- No A-Wiki/Phase6 mutation.
- No Git remote/push until DR-C1-001 is resolved.

## Next safe action

Commit the verified P1-013 batch and continuity checkpoint. After that, safe work may continue on documentation/mock-only contracts, but concrete lifecycle mutation/live integration must wait for the dedicated-worker test strategy gate.
