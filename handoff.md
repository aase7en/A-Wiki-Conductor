# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-28 — WO-P1-100 / AHA-4 supervised durable backend assembly

## Current Objective

Finish the production AHA-4 execution boundary by joining accepted durable Claude job execution to the accepted supervised Claude runner using exact per-job identity. No second process runner, lifecycle, execution store, retry loop, dedup system, scheduler, provider registry, or memory system.

## Repository State

- Repository: `aase7en/A-Wiki-Conductor`
- Worktree: `A:\GitHub\A-Wiki-Conductor-aha4-assembly`
- Branch: `feat/wo-p1-100-aha4-supervised-backend-assembly`
- reconciled current base: `7db34048a0dd002b9bfbe41408c83c7ec18df2ad`
- Work order: `docs/work-orders/WO-P1-100-aha4-supervised-backend-assembly.md`
- Dirty state: bounded WO-P1-100 implementation + tests + SSoT only; local verification green.
- Shared root remains protected/read-only.

## Accepted Baseline

- GE-6 scheduler merged `023c7b6`.
- durable graph dispatch merged `5cc417c9`.
- durable Claude backend PR #121 merged `0e9b93a`.
- supervised Claude runner PR #124 exact head `25cc694` passed 3-OS CI run `33176757259` and merged as `e933a53`.
- latest main `5dd9ab2` only refreshed independent connector-resilience evidence after PR #124.

## Architecture Boundary

Classification: **REUSE + WRAP + EXTEND**.

Accepted chains to join:

`DurableJobExecutionCoordinator -> ClaudeCodeJobBackend -> ClaudeCodeHarnessAdapter`

and

`ClaudeCodeInvocation -> SupervisedClaudeCodeRunner -> SupervisedCommandRunner -> DuplicateExecutionGuard -> SupervisedExecutionService -> OwnedProcessSpec`.

The missing seam is lazy per-job adapter construction after durable `JobExecutionContext` and non-secret provider metadata are known. Provider-unavailable paths must not resolve credentials or launch. Dispatch branch/HEAD must bind the supervised fingerprint; missing branch must fail closed before reference resolution.

## Protected Parallel Work

- Draft PR #125 / connector CR-2/CR-4: separate P0 v0.7.0 lane; do not touch its files.
- PR #108 installer target ownership: separate destructive-boundary lane; do not touch.
- North Star branch: protected integration lineage; do not touch.
- live connector fleet / tunnel-client binary / provider credentials: do not mutate.
- A-Wiki repository: read-only; its architecture says A-Wiki owns brain/policy/memory while A-Conductor owns dispatch/process control.

## Next Safe Action

1. refetch remote main and reconcile only if scope remains non-overlapping;
2. stage exactly the seven WO-P1-100 allowed files and inspect staged patch;
3. commit/push Draft PR and audit exact remote diff;
4. require exact-head Windows/Ubuntu/macOS CI including Windows packaging/frozen/Portable smoke;
5. merge only after green CI + final exact-head review; then release claim to AHA-4A.

## Safety

`SAFE_TO_MUTATE = YES` only in `A:\GitHub\A-Wiki-Conductor-aha4-assembly` and WO-P1-100 allowed scope.

## Verification checkpoint

- focused runner/backend/assembly: **25 passed in 1.49s**.
- broader Claude/provider/native/supervisor/dedup/job/graph: **237 passed in 13.43s**.
- compileall / diff-check / bounded real-secret-prefix scan: PASS.
- successful production assembly chain reaches durable `VERIFYING`; repeated unknown fingerprint does not blind relaunch.
