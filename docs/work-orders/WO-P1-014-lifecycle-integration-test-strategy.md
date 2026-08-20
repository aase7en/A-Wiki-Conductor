# WO-P1-014: Lifecycle Integration Test Strategy

Status: in_progress
Lane/files: `docs/contracts/lifecycle-integration-test-strategy.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-014-lifecycle-integration-test-strategy.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Resolve the design side of `DR-P1-002` without provisioning or mutating runtime resources. Define a staged lifecycle integration-test strategy that proves concrete mutation safety first against a self-owned dummy process, then against a dedicated isolated Serena-backed `A-Worker 3` target.

Acceptance:
- read-only inventory of candidate worker root/port/test project;
- separate Stage A self-owned dummy-process test from Stage B Serena/tunnel integration;
- define exact preconditions, identity/ownership gates, checkpoint/evidence requirements, rollback, abort conditions, and forbidden targets;
- candidate resources are recorded as candidates only, not silently reserved/provisioned;
- active Conductor and Phase6 workers are explicitly forbidden as first mutation targets;
- no credential/tunnel ID copied into tracked docs;
- no process start/stop, directory provisioning, tunnel/config changes, or repository mutation;
- determine what additional user/credential/provider action is actually required before Stage B;
- `git diff --check` and secret-like scan pass.

## Current read-only evidence

- candidate `C:/AI/serena-instances/a-worker-03` root: absent at inspection time;
- candidate health port `18013`: no LISTENING socket observed at inspection time;
- `A:/GitHub/serena-test`: exists and is only a candidate until its repository/worktree safety state is inspected;
- existing validated runtime roots remain `conductor` and `phase6`; legacy material remains retained for rollback.

## Steps

1. Commit coordination checkpoint.
2. Inspect `serena-test` repository/worktree identity read-only.
3. Define Stage A dummy-process lifecycle harness.
4. Define Stage B isolated A-Worker 3 / Serena / transport test.
5. Define evidence, rollback, abort, and success gates.
6. Identify unresolved prerequisites requiring explicit user/provider action.
7. Verify docs contain no secrets/tunnel identifiers and no accidental provisioning instruction execution.
8. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No process lifecycle mutation.
- No creation of `a-worker-03` directories/config/profile/tunnel binding.
- No port reservation.
- No writes to `serena-test`, A-Wiki, Phase6, or external runtime roots.
- No credential/tunnel secret access.
- No Git remote/push.

## Verify commands

- read-only Git/project status checks only;
- `git diff --check` in A-Conductor;
- secret/UUID/tunnel-ID pattern scan on new tracked docs.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after recovery planner commit `fcd3d61`. Initial read-only preflight: candidate A-Worker 3 root absent; port 18013 had no listener; `A:/GitHub/serena-test` exists as an unapproved candidate.
