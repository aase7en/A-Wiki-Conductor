# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / Stage A production mutation primitive preparation**

## Active work order

None at this checkpoint. `WO-P1-015` is complete and verified.

## Completed foundation

- [x] C1 contracts/invariants + local Git baseline complete.
- [x] Provider-neutral runtime/domain/safety/read-only observation stack complete.
- [x] Reusable Project/A-Worker registry + SQLite persistence complete.
- [x] Lifecycle planner + checkpointed executor + append-only journal + recovery/resume planner complete.
- [x] Lifecycle integration test strategy complete.
- [x] Stage A self-owned dummy-runtime integration complete.
- [x] START -> READY -> checkpoints passed against a real child process owned by the test harness.
- [x] Repeated START -> NOOP without duplicate child.
- [x] STOP terminated only the test-owned child.
- [x] Checkpoint failure after spawn -> `RECOVERY_REQUIRED` and halted subsequent steps.
- [x] Full suite after Stage A: **235 passed**.
- [x] Active Sunday-Conducter preservation check: PID unchanged from pre-test baseline and `/readyz` remained HTTP 200.

## DR-P1-002 status

Stage A test-harness safety is **GREEN**. It is now reasonable to implement a production owned-process mutation primitive, but integration tests must continue targeting only the self-owned dummy runtime. Real Serena/tunnel/A-Worker 3 testing remains gated.

## Repository state

- Branch: `main`
- P1-015 coordination commit: `6467e67`.
- Verified P1-015 implementation batch is ready to commit.
- Git remote: none.
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Recommended default: **private-first**. No remote/push yet.

### DR-P1-002 — Real Serena/tunnel lifecycle integration

Still unresolved for Stage B. A production mutation primitive may be developed/tested only against Stage A dummy resources until a dedicated A-Worker 3 target is safely provisioned.

## Constraints

- No active Conductor/Phase6 target mutation.
- No A-Worker 3 provisioning yet.
- No writes to `serena-test`, A-Wiki, Phase6, or external runtime roots.
- No broad process termination.
- No Git remote/push.

## Next safe action

Commit P1-015, then open a bounded work order for a production **owned-process controller** whose integration target remains the Stage A dummy runtime only.
