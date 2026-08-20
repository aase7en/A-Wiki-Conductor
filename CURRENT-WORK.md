# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / Stage A self-owned dummy runtime integration**

## Active work order

`docs/work-orders/WO-P1-015-stage-a-dummy-runtime-integration.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Provider-neutral runtime/domain/safety/read-only observation stack complete.
- [x] Reusable Project/A-Worker registry + SQLite persistence complete.
- [x] Lifecycle planner + checkpointed executor + append-only journal + recovery/resume planner complete.
- [x] Lifecycle integration strategy complete; P1-014 commit `ee5a75a`.
- [x] Stage A is explicitly limited to test-harness-owned dummy process/resources.

## Active checklist — WO-P1-015

- [x] Open/claim work order.
- [ ] Commit coordination checkpoint.
- [ ] Capture active Conductor PID/health baseline read-only.
- [ ] Add loopback dummy runtime helper under tests.
- [ ] Add real integration tests using only test-owned `Popen` child.
- [ ] Run targeted Stage A tests.
- [ ] Verify START -> READY checkpoints.
- [ ] Verify repeated START -> NOOP/no duplicate child.
- [ ] Verify STOP targets only owned child.
- [ ] Verify checkpoint failure after mutation -> RECOVERY_REQUIRED/no later steps.
- [ ] Confirm active Conductor PID/health unchanged after Stage A tests.
- [ ] Run full suite + compileall + diff check.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-015 coordination commit: `ee5a75a`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.
- Pytest: use ignored local `runtime/pytest-temp` basetemp.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Recommended default: **private-first**. No remote/push yet.

### DR-P1-002 — Real Serena/tunnel lifecycle integration

Stage A dummy-runtime integration may proceed. Stage B real Serena/tunnel mutation remains gated pending dedicated A-Worker 3 resources and safe live target.

## Constraints

- Any process started in this WO must be spawned by the test harness itself and retained via its exact `Popen` object.
- No broad process-name kill or external PID targeting.
- No Serena/tunnel/A-Worker 3 mutation.
- No writes to `serena-test`, A-Wiki, Phase6, or external runtime roots.
- No Git remote/push.

## Next safe action

Commit WO-P1-015 coordination checkpoint, capture active Conductor read-only baseline, then add dummy helper/integration tests.
