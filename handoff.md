# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-29 — WO-P1-102 / AHA-4A worker lease broker

## Current Objective

Close AHA-4A with atomic, retry-safe worker leasing and fail-closed mutation scope. No AHA-4B stale reclaim, second scheduler/store/lifecycle, or A-Wiki claim duplication.

## Repository State

- Worktree: `A:\GitHub\A-Wiki-Conductor-aha4a-lease`
- Branch: `feat/wo-p1-102-aha4a-worker-lease-broker`
- Reconciled `origin/main`: `39f0253cc4f8896cffa78b6772ce6ffd2e229736`
- PR #131 is Draft; branch requires one final fix/checkpoint push.
- Shared root remains protected/read-only.

## Latest defects repaired

1. `allowed_scope` was stored but not enforced. Mutation scope is now fail-closed: literal paths may be covered by an allowed glob; wider/unproven mutable globs are rejected.
2. Same `session_id/task_id` retry after uncertain delivery could select a second worker. Active owner/task is now unique and retry attaches the existing lease; request-contract drift fails closed.
3. Required capability drift is persisted/checked so retry cannot silently weaken or change the task contract.
4. Resume verification found two race outcome-classification defects: attach-to-existing could be mislabeled `LEASED`, and proposed lease-ID equality could hide the attach when two brokers generated the same ID. The store now returns atomic `created` status; `EXISTING` no longer depends on ID comparison.

## Evidence

- focused worker lease: **36 passed**;
- registry/persistence/graph/job/lease regression: **220 passed**;
- focused race repeat: **10/10 PASS**;
- compileall + diff-check: PASS;
- concurrency cases include competing tasks, overlapping mutable scopes, same-owner convergence, and explicit `EXISTING` classification.

## Next Safe Action

Update WO checkpoint, inspect bounded diff/scope/secret gates, commit/push the preserved dirty checkpoint, merge latest accepted `origin/main`, rerun regression, update PR #131, run independent read-only review, then require exact-head Windows/Ubuntu/macOS CI before merge.

## Safety

`SAFE_TO_MUTATE = YES` only inside this isolated worktree and WO-P1-102 scope.
