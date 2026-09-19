# WO-P1-381 — Work-Order Identity Collision Remediation / Atomic Allocation Guard

Status: CLAIMED / GOVERNANCE_BOOTSTRAP
Issue: #381
Identity schema: GITHUB_ISSUE_V1

## Binding

- Topology: CONTROL_PLANE_ONLY
- Risk: R3 coordination / durable authority identity
- Authority repo / execution repo: A-Wiki-Conductor
- Worktree: /Users/aase7en/GitHub/_worktrees/awiki-wo381-identity-guard
- Branch: fix/wo-p1-381-work-order-identity-guard
- Base: 2a461ae22ab28ad3b48f15660ab818f700faab30
- Claim: WO-P1-381-WO-ID-COLLISION-GUARD-001
- Integrator: GPT-5.6 Sol
- Preferred bounded implementer: GLM-5.3 MAX
- Evidence: runs/WO-P1-381/

## Problem / factual evidence

At claim time, accepted main contains two different work-order documents with numeric
identity WO-P1-260:

- docs/work-orders/WO-P1-260-dex-2b-conductor-reconciliation-receipt.md
- docs/work-orders/WO-P1-260-a-faster-durable-lanes.md

GitHub chronology shows DEX-ARCH-1 reserved DEX WO259/WO260 before the later
Context Guard/A-Faster lanes reused those numbers. The duplicate is authority
identity drift, not a Git content conflict.

Existing repository policy already says future WO numbers are allocated at claim
time to avoid collisions. This task EXTENDS that authority with an atomic
GitHub-backed allocation rule; it creates no task DB, scheduler, claim/lease
store, review authority, or runtime state.

## Decision / allocation rule

For NEW GitHub-backed Work Orders after this contract is accepted:

`GitHub Issue #N -> WO-P1-N`

GitHub's repository-local issue number is reused as the atomic numeric allocator.
Legacy accepted Work Orders keep their historical identity unless an actual
collision requires reconciliation.

Collision ownership follows durable chronology. For the current collision:
- DEX retains WO-P1-259 and WO-P1-260.
- A-Faster durable-lane authority rebinds from provisional WO-P1-260 to
  canonical WO-P1-374 (its existing Issue #374).
- Context Rollover Guard Issue #369 must rebind to WO-P1-369 before merge.
- Claude/Kilo adapter Issues #375/#376 use WO-P1-375 / WO-P1-376 at their
  next re-pin.

Historical execution pointers, run directories, hashes and immutable evidence
that literally contain the provisional WO number are preserved as historical
facts and explicitly marked non-authoritative after rebind; do not rewrite them.

## Mutable scope

- NEW docs/contracts/work-order-identity-v1.md
- NEW tests/test_work_order_identity.py
- RENAME docs/work-orders/WO-P1-260-a-faster-durable-lanes.md
  -> docs/work-orders/WO-P1-374-a-faster-durable-lanes.md
- .agents/skills/a-faster/references/durable-lanes.md
- this Work Order

## Forbidden scope

- .agents/skills/a-fasttask/** (open PR #338 owns that hotspot)
- DEX WO259/WO260 docs, ADR, execution-admission contract, PROJECT-PLAN
- CURRENT-WORK.md / handoff.md / COLLAB.md
- src/a_conductor/**, runtime/provider/job/claim/lease state
- force-push, rebase/history rewrite, reset/clean/stash, deleting historical evidence

## Failure model

1. Two files reuse one WO-P1-N -> deterministic CI/test failure.
2. An opt-in GITHUB_ISSUE_V1 record declares Issue #M but filename WO-P1-N where M != N -> failure.
3. Rebinding rewrites historical run identity/digest -> failure; historical evidence must remain literal and clearly historical.
4. A DEX identity is renamed merely because it conflicts with a later claimant -> failure; earlier durable chronology retains ownership.
5. A new local allocator/store is introduced -> failure; reuse GitHub issue numbering only.
6. PR #338 hotspot is touched -> claim conflict / fail closed.

## Acceptance

1. RED-first proof catches current duplicate WO260 before the A-Faster rename.
2. Full docs/work-orders scan has zero duplicate numeric WO-P1-N identities.
3. GITHUB_ISSUE_V1 opt-in validation proves Issue #N == WO-P1-N.
4. A-Faster canonical Work Order is WO-P1-374; Issue #374 is recorded.
5. Historical WO260 lane/run/digest examples remain truthful and are labeled historical/non-authoritative.
6. DEX WO259/WO260 content is untouched.
7. .agents/skills/a-fasttask/** untouched.
8. diff/scope/UTF-8/secret checks pass.
9. Independent exact-SHA R3 review P0/P1/P2=0.
10. Exact-head hosted CI passes before GPT acceptance/merge.

## Replay safety

This is repository policy/test/docs work only. A transport/session loss does not
authorize redispatch. Recover task pointer, process/session, result, Git HEAD,
dirty state and remote branch before any retry. Same mutable hotspot has one
owner at a time.
