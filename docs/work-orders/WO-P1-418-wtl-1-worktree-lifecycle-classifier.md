# WO-P1-418 — WTL-1 deterministic worktree lifecycle classifier

Status: CLAIMED / READY_FOR_IMPLEMENTATION
Issue: #418
Parent: #415 WTL-0
Topology: CONTROL_PLANE_ONLY
Risk: R3 — lifecycle/cleanup eligibility authority boundary (read-only in this WO)
Authority repo: A:\GitHub\A-Wiki-Conductor
Execution repo: A:\GitHub\A-Wiki-Conductor
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo418-wtl1
Branch: feat/wo-p1-418-wtl-1-classifier
Base SHA: f46531dbe79ef5764f2a344f966f0c93abb0c392

## Goal

Implement WTL-1 as a deterministic read-only classifier + observation layer for worktree lifecycle state. It must never delete, prune, archive, remove, reset, stash, or mutate Git/worktree state.

Only RELEASED_SAFE_TO_ARCHIVE may set cleanup_eligible=True. Missing, stale, contradictory, dirty, active, frozen-review, remote-unmerged, or merge-not-folded evidence fails closed.

## Claim / owner

Claim ref: WO-P1-418-WTL1-CLASSIFIER-001
Owner: A-Faster mutable lane
Replay safety: source/test edits are Git-bounded; recover pointer/process/result/Git before redispatch.

## Mutable scope — exact

- src/a_conductor/worktree_lifecycle.py
- src/a_conductor/worktree_lifecycle_observation.py
- tests/test_worktree_lifecycle_classifier.py
- tests/test_worktree_lifecycle_observation.py
- docs/work-orders/WO-P1-418-wtl-1-worktree-lifecycle-classifier.md

Everything else is read-only unless an explicit scope-expansion checkpoint is recorded first.

## Reuse requirements

Reuse/wrap existing authorities; do not create a second registry/store:
- registry.windows_worktree_key
- ProjectIdentityService / project identity seams
- existing Git status --short --untracked-files=all observation
- LeaseFact, MergeFoldFact, ContinuitySnapshot vocabulary / fail-closed precedence
- existing worker lease / job-store lease read facts
- FoldEvidence / GoalCloseout fold state
- DurableExecutionRecord / execution process state
- exact process identity observation (owned_process.py, windows_observer.py)
- existing instance registry keyed by worktree identity
- native Git transaction boundary in read-only mode

A small injected RemoteEvidencePort is allowed for open-PR/remote-branch/unmerged observation. It is read-only and is not a registry/store/authority. Unavailable remote evidence => EVIDENCE_INCOMPLETE.

## Required lifecycle states

At minimum:
- DIRTY_PROTECTED
- ACTIVE_OWNED
- PROCESS_OR_EXECUTION_ACTIVE
- CLAIM_CONFLICT
- REVIEW_FROZEN
- REMOTE_UNMERGED
- MERGED_NOT_FOLDED
- EVIDENCE_INCOMPLETE
- UNOWNED_UNKNOWN
- RELEASED_SAFE_TO_ARCHIVE

Protective evidence outranks permissive evidence.

## Required DTO semantics

Classifier input must distinguish observed absent from not collected / unknown for optional evidence.

Output must bind:
- canonical worktree key
- exact head SHA at classification
- lifecycle state
- cleanup_eligible
- precedence-ordered reason codes
- evidence refs
- classification timestamp
- classifier version
- input fingerprint sufficient for deterministic replay/audit

No worktree name/age inference is allowed.

## RED-first acceptance matrix

1. canonical root + dirty tracked => DIRTY_PROTECTED
2. tracked dirty only => DIRTY_PROTECTED
3. untracked bytes only, including .serena/ => DIRTY_PROTECTED
4. active lease => ACTIVE_OWNED
5. conflicting leases/claims => CLAIM_CONFLICT
6. exact live process or live durable execution => PROCESS_OR_EXECUTION_ACTIVE
7. stale/unverified PID identity => EVIDENCE_INCOMPLETE
8. merged ancestry but fold not released => MERGED_NOT_FOLDED
9. merged + folded/released + clean + no lease/process/remote + complete evidence => RELEASED_SAFE_TO_ARCHIVE
10. open PR / remote branch / unmerged commits => REMOTE_UNMERGED
11. exact frozen review candidate => REVIEW_FROZEN
12. required merge/fold/remote evidence missing => EVIDENCE_INCOMPLETE
13. no durable facts => UNOWNED_UNKNOWN
14. HEAD changed since inventory/snapshot => EVIDENCE_INCOMPLETE
15. dirty + merged => DIRTY_PROTECTED
16. live process + released lease => PROCESS_OR_EXECUTION_ACTIVE

## Safety / forbidden behavior

WTL-1 MUST NOT:
- call worktree remove/prune
- delete/archive files
- delete branches
- mutate Git metadata
- release claims/leases
- mutate task/job/fold/review state
- infer safety from naming conventions or age
- broad-kill processes
- create a cleanup queue/store

WTL-2 is a separate later R3 work order requiring fresh re-pin/classification immediately before any consequential cleanup.

## Verification

RED first, then:
- focused classifier tests
- observation tests with injected providers
- related registry/project-identity/continuity/lease/execution/process observation tests as applicable
- py_compile
- git diff --check
- exact scope audit
- strict UTF-8 / U+FFFD check
- added-line secret scan

Freeze exact candidate SHA, then require independent GLM-5.3 MAX R3 review + exact-head hosted CI before acceptance/merge.

## Stop / escalation

Stop and checkpoint on:
- need to mutate outside exact five paths
- need for a new store/registry/lease/cleanup authority
- remote observation cannot remain read-only/injected
- ambiguous claim/ownership
- deterministic evidence contradicts the WTL-0 contract

No self-merge or self-accept.
