# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / Stage A integration preparation**

## Active work order

None at this checkpoint. `WO-P1-014` is complete; next safe work is Stage A self-owned dummy-runtime integration.

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Provider-neutral runtime/domain/safety/read-only observation stack complete.
- [x] Reusable Project/A-Worker registry + SQLite persistence complete.
- [x] Pure lifecycle planner + checkpointed executor + append-only journal + recovery/resume planner complete.
- [x] Full suite after P1-013: 233 passed.
- [x] Lifecycle integration test strategy complete.
- [x] Stage A = self-owned dummy process; no external credential/tunnel required.
- [x] Stage B = dedicated isolated A-Worker 3 Serena/transport target only after Stage A.
- [x] Candidate A-Worker 3 root absent and port 18013 had no listener at read-only inspection time; not reserved.
- [x] Candidate `serena-test` repo inspected read-only: main, clean, no remote; mutation remains forbidden.

## DR-P1-002 status

Partially resolved by strategy: the first mutation-capable integration work may proceed only against a self-owned dummy runtime created by the test harness. Real Serena/tunnel mutation remains gated until Stage A passes and a dedicated A-Worker 3 target is provisioned safely.

## Repository state

- Branch: `main`
- HEAD before P1-014 docs implementation commit: `8b3b632` coordination checkpoint; verified P1-014 docs batch is ready to commit.
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Recommended default: **private-first**. No remote/push yet.

### DR-P1-002 — Real Serena/tunnel lifecycle integration

Stage A dummy-runtime testing may proceed without additional external credentials. Stage B remains gated pending dedicated A-Worker 3 runtime/transport resources and a safe live target.

## Constraints

- Stage A may start/stop **only processes spawned and fingerprinted by its own test harness**.
- No active Conductor/Phase6 process may be targeted.
- No writes to `serena-test`, A-Wiki, Phase6, or external runtime roots during Stage A.
- No Git remote/push.

## Next safe action

Commit P1-014. Then open a bounded Stage A work order for a self-owned dummy runtime helper + concrete lifecycle mutation backend constrained to test-owned temporary resources.
