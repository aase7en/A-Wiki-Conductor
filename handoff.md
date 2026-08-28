# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-28 — WO-P1-102 / AHA-4A worker lease broker

## Current Objective

Implement atomic worker leasing + deterministic eligibility/fallback without creating a second scheduler, task store, lifecycle, dispatch system, retry loop, or A-Wiki claim system.

## Repository State

- Repository: `aase7en/A-Wiki-Conductor`
- Worktree: `A:\\GitHub\\A-Wiki-Conductor-aha4a-lease`
- Branch: `feat/wo-p1-102-aha4a-worker-lease-broker`
- Base/current main at claim: `08369ade59206cbe2bc80a314d49d3daa50038b7`
- Work order: `docs/work-orders/WO-P1-102-aha4a-worker-lease-broker.md`
- Shared root remains protected/read-only.

## Accepted Baseline

- GE-6 deterministic scheduler merged `023c7b6`.
- durable graph dispatch merged `5cc417c9`.
- durable Claude backend merged `0e9b93a`.
- supervised Claude runner merged `e933a53`.
- durable↔supervised production assembly PR #130 exact head `d389082` passed CI `33183355995` and merged `08369ade`.

## Architecture Boundary

Classification: **EXTEND + WRAP**. Reuse `ControlPlaneRegistry`, GE-6 worker facts, `windows_worktree_key`, GE overlap semantics and existing durable execution authority. A-Wiki work-order claims remain governance; this slice owns runtime capacity leasing only.

## Protected Parallel Work

- connector/release stability lanes;
- installer PR #108 lineage;
- North Star branch;
- provider DB/gateway/live credentials;
- A-Wiki repository.

## Next Safe Action

Stage only `worker_lease.py`, `test_worker_lease.py` and WO-P1-102 SSoT files; commit/push, open Draft PR, audit exact remote diff, then require exact-head 3-OS CI before merge.

## Safety

`SAFE_TO_MUTATE = YES` only inside this isolated worktree and WO-P1-102 allowed scope after claim commit/push.

## Implementation checkpoint

- atomic SQLite worker lease + active mutable-scope collision gate implemented;
- deterministic ordered fallback + typed preflight implemented;
- exact-owner idempotent release; expired metadata is not reclaimed in this phase;
- explicit read-only RDC fallback; mutation never falls to RDC;
- focused **29 passed**, race repeat **10/10**, related regression **140 passed**;
- compileall/diff/forbidden-import/secret checks PASS.
