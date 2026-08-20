# A-Conductor — Current Work

Last updated: 2026-08-20

## Current phase

**Phase 1 — Multi-Serena Control Center / lifecycle integration test strategy**

## Active work order

`docs/work-orders/WO-P1-014-lifecycle-integration-test-strategy.md`

Status: `IN_PROGRESS`

## Completed foundation

- [x] C1 contracts/invariants + JSON Schemas validated.
- [x] Local Git safety baseline on `main`.
- [x] Typed provider-neutral domain + runtime safety + read-only observation/status layers complete.
- [x] Reusable Project/A-Worker registry + SQLite persistence complete.
- [x] Pure lifecycle decision planner + checkpointed transaction executor complete.
- [x] Append-only SQLite lifecycle journal complete.
- [x] Pure lifecycle recovery/resume planner complete.
- [x] P1-013 implementation commit: `fcd3d61`.
- [x] Full suite after P1-013: 233 passed.
- [x] Initial read-only P1-014 preflight: candidate `a-worker-03` root absent, port `18013` no listener, `A:/GitHub/serena-test` exists as unapproved candidate.

## Active checklist — WO-P1-014

- [x] Open/claim work order.
- [ ] Commit coordination checkpoint.
- [ ] Inspect `A:/GitHub/serena-test` identity/status read-only.
- [ ] Define Stage A self-owned dummy-process lifecycle harness.
- [ ] Define Stage B isolated A-Worker 3 Serena/transport integration.
- [ ] Define evidence/rollback/abort/success gates.
- [ ] Identify unresolved user/provider prerequisites.
- [ ] Secret/UUID/tunnel-ID scan + `git diff --check`.
- [ ] Update checkpoint/handoff and commit.

## Repository state

- Branch: `main`
- HEAD before WO-P1-014 coordination commit: `fcd3d61`
- Git remote: none
- Use exact per-command `-c safe.directory=A:/GitHub/A-Wiki-Conductor`; global Git config unchanged.

## DECISION_REQUIRED

### DR-C1-001 — GitHub repository publication

Recommended default: **private-first**. No remote/push yet.

### DR-P1-002 — Live lifecycle integration test strategy

Design resolution is being prepared in WO-P1-014. No live mutation target has been provisioned/approved yet.

## Constraints

- Docs/read-only inventory only in WO-P1-014.
- No runtime/process/tunnel mutation or provisioning.
- No writes to candidate test repo, A-Wiki, Phase6, or external runtime roots.
- No Git remote/push.

## Next safe action

Commit the P1-014 coordination checkpoint, inspect the candidate test repo read-only, then write the staged integration-test strategy.
