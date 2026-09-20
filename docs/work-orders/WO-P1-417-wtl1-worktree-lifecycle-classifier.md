# WO-P1-417 — WTL-1 deterministic read-only worktree lifecycle classifier

Status: CLAIMED / GOVERNANCE_BOOTSTRAP
Issue: #417
Parent: #415 / #397
Topology: CONTROL_PLANE_ONLY
Risk: R2
Claim: WO-P1-417-WTL1-READONLY-CLASSIFIER-001
Authority repo: A-Wiki-Conductor
Branch: feat/wo-p1-417-wtl1-worktree-lifecycle-classifier
Base: f46531dbe79ef5764f2a344f966f0c93abb0c392

## Goal

Implement a deterministic, fail-closed, read-only classifier for worktree
lifecycle/cleanup eligibility. WTL-1 classifies evidence only. It never removes,
prunes, archives, cleans, resets, stashes, switches, deletes branches, or mutates
Git metadata.

Only RELEASED_SAFE_TO_ARCHIVE may set cleanup_eligible=True. WTL-2 is the
separate future R3 executor and is forbidden here.

## Exact mutable scope

- src/a_conductor/worktree_lifecycle.py
- src/a_conductor/worktree_lifecycle_observation.py
- tests/test_worktree_lifecycle_classifier.py
- tests/test_worktree_lifecycle_observation.py
- docs/work-orders/WO-P1-417-wtl1-worktree-lifecycle-classifier.md

All other tracked paths are read-only.

## Reuse-only authorities

- registry.windows_worktree_key
- project_identity.ProjectIdentityService
- native read-only Git status/identity seams
- continuity_guard fact vocabulary / precedence style
- worker lease facts / canonical lease authority
- goal closeout fold/release evidence
- DurableExecutionRecord / ExecutionProcessState
- owned-process / Windows exact process identity observation
- control-center/local-instance registry
- native_git_transactions read-only snapshot boundary

No existing authority above may be mutated in WTL-1.

A minimal injected RemoteEvidencePort is allowed for open PR / remote branch /
unmerged evidence. Failure/unavailability is EVIDENCE_INCOMPLETE, never safe.

## Lifecycle states

ACTIVE_OWNED
REVIEW_FROZEN
MERGED_NOT_FOLDED
RELEASED_SAFE_TO_ARCHIVE
DIRTY_PROTECTED
CLAIM_CONFLICT
PROCESS_OR_EXECUTION_ACTIVE
REMOTE_UNMERGED
UNOWNED_UNKNOWN
EVIDENCE_INCOMPLETE

## Evidence precedence

Protective evidence wins:
1. canonical/instance root protection
2. exact live process or live durable execution
3. active/conflicting claim/lease
4. tracked dirty or any untracked bytes
5. exact durable review freeze
6. open PR / remote branch / unmerged commits
7. merged ancestry with incomplete fold/release
8. RELEASED_SAFE_TO_ARCHIVE only when every required fact is freshly proven
9. missing/stale/conflicting facts => EVIDENCE_INCOMPLETE
10. no durable facts => UNOWNED_UNKNOWN

Names, age, path suffixes and PID numbers alone grant no authority.

## DTO contract

WtlWorktreeFacts must preserve repo/worktree identity, exact HEAD/branch/detached
state, dirty/untracked evidence, claim/lease, fold/release, durable execution,
exact process identity, remote evidence, durable task refs, observation time and
input fingerprint. Unknown must remain distinguishable from observed absence.

WtlClassification must include worktree key, classified HEAD, lifecycle state,
cleanup_eligible, ordered typed reasons, evidence refs, classifier version,
classification time and input fingerprint.

## RED-first matrix

1. canonical dirty root -> DIRTY_PROTECTED / protected root
2. tracked dirty -> DIRTY_PROTECTED
3. untracked bytes including .serena -> DIRTY_PROTECTED
4. active lease -> ACTIVE_OWNED
5. conflicting leases -> CLAIM_CONFLICT
6. exact live process -> PROCESS_OR_EXECUTION_ACTIVE
7. stale PID / identity mismatch -> EVIDENCE_INCOMPLETE
8. merged but fold/release incomplete -> MERGED_NOT_FOLDED
9. fully merged+folded+released+clean+remote-clear -> RELEASED_SAFE_TO_ARCHIVE
10. open PR / remote branch / unmerged commits -> REMOTE_UNMERGED
11. detached exact review freeze -> REVIEW_FROZEN
12. required fold/merge/remote evidence missing -> EVIDENCE_INCOMPLETE
13. zero durable facts -> UNOWNED_UNKNOWN
14. HEAD drift since observation -> EVIDENCE_INCOMPLETE
15. dirty + merged -> DIRTY_PROTECTED
16. live process + released lease -> PROCESS_OR_EXECUTION_ACTIVE

## Forbidden

- no deletion/prune/archive executor
- no reset/clean/stash/checkout/rebase/branch deletion
- no new mutable global worktree registry
- no second task/claim/lease/review/completion store
- no continuity_guard/worker_lease/job_store/goal_closeout/registry mutation
- no CURRENT-WORK/handoff/COLLAB mutation
- no cleanup recommendation based on name/age alone

## Verification

RED first, then both focused test files. Run directly related tests selected by
imports/call graph, py_compile, git diff --check, strict UTF-8/no U+FFFD,
added-line credential/secret scan and exact scope audit. Freeze one exact SHA.

Acceptance is R2: independent exact-SHA review + exact-head hosted CI + GPT
acceptance/merge/post-main verification. Author result is a claim only.

## Bootstrap checkpoint

This initial commit is docs-only under the governance-bootstrap exception.
After commit/push, re-run the full mutation gate before source mutation.

## Implementation checkpoint (2026-09-20)

Status: IMPLEMENTED / AWAITING INDEPENDENT REVIEW.

- `src/a_conductor/worktree_lifecycle.py` — pure fail-closed classifier:
  `WtlWorktreeFacts` / `WtlClassification` DTOs, ten lifecycle states,
  typed reason codes with deterministic precedence (input-fingerprint
  integrity rank 0; protected root 1; live exact process / live durable
  execution 2; lease conflict 3; active lease 4; dirty/untracked 5; exact
  review freeze 6; remote unmerged 7; incomplete fold/release 8; proven
  release 9; missing-fact incompleteness 10; zero durable linkage 11).
  Reuses `windows_worktree_key`, `classify_process_ownership` /
  `ProcessObservation`, and `ExecutionProcessState`; adds
  `wtl_input_fingerprint` (SHA-256 over the canonical snapshot) so inputs
  and outputs are replayable/auditable. `cleanup_eligible` is true only
  for RELEASED_SAFE_TO_ARCHIVE and enforced in the DTO constructor.
- `src/a_conductor/worktree_lifecycle_observation.py` — read-only
  observation layer: `StrictGitObservationPort` (fixed read-only argv:
  `--no-optional-locks`, safe.directory, `-C`, rev-parse HEAD /
  rev-parse --abbrev-ref HEAD / status --porcelain=v1 only) plus
  injectable collector protocols for leases, durable executions, exact
  process identity, review freezes, merge/fold evidence, and the new
  minimal `WtlRemoteEvidencePort`. Missing/failing/unwired collectors map
  to UNKNOWN (None), never invented absence; collector failures fail
  closed. HEAD is re-read after collection for freshness (drift =>
  EVIDENCE_INCOMPLETE). Protected-root matching reuses
  `windows_worktree_key` over the canonical/instance roots supplied by
  the caller.
- RED-first: both test files were written and captured failing
  (ModuleNotFoundError, 2 collection errors) before implementation.
- GREEN: 102 focused tests pass; 161 imported-authority seam tests pass
  (registry / owned_process / windows_observer / continuity_guard /
  project_identity); py_compile clean; `git diff --check` clean; strict
  UTF-8 / no U+FFFD; added-line secret scan clean; scope audit shows
  exactly the five allowed paths.
- Defects found and fixed during verification: release gate initially
  granted RELEASE_PROVEN without proving merge/remote evidence present;
  protected-root matching initially seeded the protected set with the
  worktree's own key. Both now covered by tests.

Author result is a claim only: requires independent exact-SHA R2 review,
exact-head hosted CI, and GPT acceptance per the acceptance section.
