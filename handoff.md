# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-28 — WO-P1-095 / AHA-4 Claude durable backend bridge

## Current Objective

Eliminate manual prompt copying by placing the accepted AHA-3 Claude Code harness under the same durable job-control authority now used by accepted GE-6/GE-7 graph dispatch.

## Repository State

- Repository: `aase7en/A-Wiki-Conductor`
- Worktree: `A:\GitHub\A-Wiki-Conductor-aha4-bridge`
- Branch: `feat/wo-p1-095-aha4-harness-durable-bridge`
- Base/accepted main: `5cc417c92450eba796fa9af1cf3da037663b1eea`
- Work order: `docs/work-orders/WO-P1-095-aha4-claude-durable-backend.md`
- Shared root remains protected/read-only.

## Accepted Baseline

- AHA-1 provider/harness contracts merged `c3ca84c`.
- AHA-2 provider config/readiness merged `ca4cd98`.
- AHA-3 bounded read-only Claude Code adapter merged `ab28dc7`.
- GE-6 scheduler merged `023c7b6`.
- PR #119 durable graph-dispatch final head `70e80c1d958b08137bf5c70a44cca369ac4aadac` passed 3-OS CI run `33159443742` and merged as `5cc417c92450eba796fa9af1cf3da037663b1eea`.
## Architecture Boundary

Classification: **REUSE + WRAP + EXTEND**.

Authority remains:
- `SQLiteJobStore`
- `DurableJobExecutionCoordinator`
- `JobExecutionBackend`
- `ClaudeCodeHarnessAdapter`
- existing supervised execution + canonical duplicate guard for future real launch

Current archaeology: `JobExecutionBackend.execute(operation_ref, worker_id)` lacks job/work-order/project context required by the resilient execution identity contract. WO-P1-095 may add one immutable bounded context seam if RED tests prove it necessary. Existing native backend must remain compatible and may ignore unused context.

The Claude job backend must return only `JobBackendResult`; it does not transition job state itself. Provider/harness success is evidence, never completion authority.

External process launch remains injected in this slice. The next micro-slice must adapt AHA-3 `ClaudeCodeInvocation` to the existing supervised runner/dedup path rather than build another launcher or duplicate guard.

## Protected Parallel Work

- PR #108 installer target ownership: do not touch.
- `feat/north-star-runtime-sunday-family`: do not touch.
- A-Wiki main is read-only; current A-Wiki phase 8+ remains HOLD.
- live provider DB/gateway/credentials remain out of scope.
## Local Evidence

- Claude backend + job execution + native operations: **33 passed**.
- Broader provider/harness/job-control/graph/dedup/supervised regressions: **106 passed**.
- Full local run: **1398 passed / 4 skipped**; 31 failures + 8 errors confined to unrelated local PermissionError instance-file tests and GPU framebuffer tests.
- GPT completed the blocked GLM archaeology: reuse SupervisedCommandRunner/DuplicateExecutionGuard; future missing seam is supervised environment propagation from NativeCommandSpec to OwnedProcessSpec.

## Next Safe Action

1. compileall + diff-check + exact scope/secret audit;
2. commit/push Draft PR for WO-P1-095;
3. audit exact remote diff and require exact-head Windows/Ubuntu/macOS CI;
4. merge only when green;
5. next micro-slice: supervised Claude runner adapter, no new process supervisor/dedup.

## Safety

`SAFE_TO_MUTATE = YES` only in `A:\GitHub\A-Wiki-Conductor-aha4-bridge` and WO-P1-095 allowed scope.
