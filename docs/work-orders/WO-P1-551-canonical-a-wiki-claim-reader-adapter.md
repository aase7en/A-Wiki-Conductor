# WO-P1-551 — canonical A-Wiki claim reader and Conductor task binding adapter

Status: CONTRACT DISCOVERY / WAITING_EXTERNAL — no product/source mutation authorized
Issue: #551
Risk: R3 — repo-claim authority, task binding, mutable dispatch admission
Topology: CONTROL_PLANE_ONLY (the only mutation target is A-Wiki Conductor; A-Wiki is an external authority/dependency)
Authority repo: `aase7en/A-Wiki-Conductor`
Base: `c4d4cf4da830cb313a4569a386edcff0a77266c2`
Branch: `codex/wo-p1-551-claim-reader-contract`
Worktree: `/Users/aase7en/.codex/worktrees/wo551-claim-reader-contract/A-Wiki-Conductor-codex-supervisor`

## Authority framing

A-Wiki is the owner of durable cross-agent repository/work-order claim identity. A-Sunday Conductor is an adapter at the runtime admission boundary. A Conductor `WorkerLease` remains runtime mutation authority and is not a repo-coordination claim. This work adds no competing claim store, scheduler, lease authority, review state, or receipt system.

Reuse classification: `WRAP -> EXTEND` the accepted A-Wiki ↔ A-Conductor integration contract and existing Conductor admission/DEX reconciliation authorities. Do not `REPLACE` or create a peer claim authority.

## User-confirmed gap

The user confirmed there is no approved reader/API that returns current A-Wiki repo/work-order claims bound to each Conductor task ID. Therefore WO-P1-549 / PR #550 remains mutable fail-closed with `CANONICAL_MUTABLE_CLAIM_AUTHORITY_UNAVAILABLE`. This work must not infer task binding from worker status, a copied claim string, a projected WIP counter, or a local TTL/runtime lease.

## Reuse and dependency audit

- A-Wiki `main` and `origin/main` were read-only verified at `25102e44950ccd28c2d22eafc6e6f1d2119f18ad`.
- A-Wiki Issue #58 is OPEN. Its accepted architecture says durable COLLAB/Git claim identity is canonical, local TTL `a-claim` is a derived same-machine enforcement cache, and Conductor `WorkerLease` is a separate runtime authority. Its source migration remains pending.
- A-Wiki `docs/protocols/universal-routing.md` and `docs/protocols/model-switching.md` are the reuse sources for model cost/routing; no separate model router is part of this WO.
- Conductor `docs/contracts/a-wiki-a-conductor-integration.md` assigns `repo_coordination_claim` to A-Wiki OWNER / Conductor ADAPTER and `runtime_lease` to Conductor OWNER.
- Reuse DEX-2b `docs/work-orders/WO-P1-260-dex-2b-conductor-reconciliation-receipt.md`, Issue #348, the merged DEX identity/receipt boundary, #526 admission/worktree contract, and the existing #498 PRE_DISPATCH guard. Do not create a second receipt or admission authority.
- No A-Wiki files were changed. Only public-safe A-Wiki docs/protocols and the public issue were read; no secret or private Drive file was read.

## Current bounded phase — contract discovery only

The first phase documents the required producer/consumer boundary and waits for the A-Wiki owner to publish or explicitly accept a machine-readable reader contract that can identify the current canonical claim and its task binding. This WO does not guess the schema or claim API. No Conductor source file, A-Wiki file, provider route, or runtime dispatch is authorized by this phase.

Once the upstream contract exists, a fresh claim must pin the exact Conductor repository, worktree, branch, HEAD, task/claim identity, and source scope before any adapter implementation. Rerun the full mutation gate immediately after contract discovery.

## Required adapter behavior after the upstream gate

- Read the A-Wiki-owned canonical claim through its accepted read interface; never mint or write a repo-coordination claim.
- Bind the canonical claim identity/generation to the exact Conductor `task_id`, repository/worktree/branch/HEAD, and declared mutation scope using only fields the accepted upstream contract defines.
- Reconcile current claim state before provider eligibility, scheduling, lease mutation, or executor invocation.
- Fail closed on missing, stale, ambiguous, unbound, mismatched, superseded, or unreadable claim evidence. Keep mutable A-Faster refill disabled until the full binding is verified.
- Preserve the existing global WIP limit, one-hotspot-one-owner rule, #498 PRE_DISPATCH guard, WorkerLease ownership, DEX binding digest and receipt/reconciliation behavior.
- Keep secrets and private claim payloads out of telemetry, Git, task logs, and provider prompts. Record only bounded validated identity/evidence references.

## Acceptance for any later implementation phase

1. The accepted upstream reader contract and exact mapping semantics are recorded without changing A-Wiki from this repository.
2. RED-first deterministic tests prove exact task-to-claim binding and denial on all missing/stale/ambiguous/mismatched cases before provider/scheduler/lease/runner side effects.
3. Existing #498 PRE_DISPATCH and DEX receipt/reconciliation invariants remain intact.
4. Exact scope, strict UTF-8, diff and added-line secret scans pass; focused and related deterministic tests pass.
5. Independent exact-SHA R3 review has P0/P1/P2 = 0; exact-head CI and required runtime evidence pass; expected-head merge and post-main verification are recorded.
6. #549 is resumed only after the adapter is accepted; mutable refill remains fail-closed until then.

## Bootstrap claim — contract documentation only

- Claim: `WO-P1-551-CONTRACT-DISCOVERY-001`
- Repo/worktree/branch/starting HEAD: `aase7en/A-Wiki-Conductor` / this worktree / `codex/wo-p1-551-claim-reader-contract` / `c4d4cf4da830cb313a4569a386edcff0a77266c2`
- Exact mutable scope: this WO file only. `CURRENT-WORK.md` and `handoff.md` remain owned by the active #549 checkpoint lane; pointer updates for #551 are recorded there.
- `SAFE_TO_MUTATE=YES` applies only to this new governance document in this clean isolated worktree.
- `SAFE_TO_MUTATE=NO` for Conductor product/source/runtime changes and all A-Wiki changes until the upstream reader contract, a fresh task-bound claim, and the full R3 gate exist.
- Typed blocker: `CANONICAL_MUTABLE_CLAIM_AUTHORITY_UNAVAILABLE`.
- No provider inference/dispatch, GLM call, JEV call, or A-Wiki mutation was performed.

## Exact next safe action

Wait for A-Wiki Issue #58 (or an explicitly accepted A-Wiki reader contract) to expose current canonical claim identity and task binding. Then refresh both repositories' exact SHAs and create a new, narrowly scoped adapter implementation claim. Until then preserve #549/#550 fail-closed and do not re-enable mutable refill.
