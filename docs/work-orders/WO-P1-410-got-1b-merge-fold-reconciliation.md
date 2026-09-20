# WO-P1-410 — GOT-1b-A typed merge-fold reconciliation

Status: ACTIVE / READY_FOR_REVIEW
Issue: #410
Risk: R3 — mutation-authority admission path
Topology: CONTROL_PLANE_ONLY

## Binding
- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo410-merge-fold-reconciliation`
- Branch: `feat/wo-p1-410-merge-fold-reconciliation`
- Base / dispatch head: `80d812cc5043a01a53e1f3ace99bbd5e7b672c04`
- Claim: `WO-P1-410-GOT1B-MERGE-FOLD-RECONCILIATION-001`
- Owner/integrator: GPT-5.6 Sol
- Author: GLM-5.3 MAX via admitted Kilo harness
- Evidence: `runs/WO-P1-410/author/attempt-0001/` (gitignored)

## Problem

GoalCloseout intentionally requires the projection fold when continuity is
`MERGED_NOT_FOLDED`, but `ContinuityProjectionFoldAdapter` publishes only
through `AgentChangeApplier.apply()` and generic `apply()` admits only `FRESH`
+ `safe_to_mutate`. The canonical action that repairs accepted merge-fold debt
(`ReconciliationAction.COMPLETE_MERGE_FOLD`) is therefore denied by the very
state it exists to resolve.

Scope is GOT-1b-A ONLY. GOT-1b-B durable MergeFoldFact/ContinuitySnapshotProvider
producers are out of scope here, as is GOT-1a #409 composition scope.

## Exact mutable tracked scope
- `src/a_conductor/agent_change_packets.py`
- `src/a_conductor/goal_closeout.py`
- `src/a_conductor/continuity_projection.py`
- `tests/test_agent_change_packets.py`
- `tests/test_continuity_projection.py`
- `tests/test_goal_closeout.py`
- `docs/work-orders/WO-P1-410-got-1b-merge-fold-reconciliation.md`

Everything else read-only.

## Settled contract

1. Generic `AgentChangeApplier.apply()` remains FRESH-only. No generic
   `allow_non_fresh` flag is ever added.
2. A separate explicit typed reconciliation admission path exists for ONLY
   `ReconciliationAction.COMPLETE_MERGE_FOLD`.
3. The typed path reuses the full existing mutation pipeline: active
   lease/health, task/owner/worktree/branch/head, mutable/forbidden scope,
   content precondition, atomic write/read-back, existing typed failures.
4. Typed reconciliation identity binds at least: action == COMPLETE_MERGE_FOLD,
   `task_id`, active `lease_id`, `candidate_sha`, exact `merge_commit`, exact
   fold `checkpoint_ref` / merge key, repo/worktree/branch/head identity
   (enforced by existing gates), and a requested target set restricted to the
   canonical continuity projection targets (`CURRENT-WORK.md`, `handoff.md`,
   `COLLAB.md`).
5. At apply time the trusted `ContinuitySnapshot` must classify
   `MERGED_NOT_FOLDED` for the exact merge identity. UNKNOWN, CLAIM_CONFLICT,
   DIRTY, HEAD_DRIFT, STALE_LOCAL, generic RECONCILE_REQUIRED and unrelated
   SSOT_DRIFT remain fail-closed.
6. SSOT_DRIFT is tolerated only when its contradicting sources are precisely
   the canonical projection targets being repaired; unrelated drift denies.
7. `FoldRequest` gains the minimum additive merge identity needed by the
   adapter, populated by the executor from the `MergeEvidence` holder; the
   adapter never invents merge identity.
8. `ContinuityProjectionFoldAdapter` uses the typed reconciliation path only
   for the exact merge-fold action; normal projection writes keep generic
   FRESH-only behavior.
9. Canonical targets remain exactly `CURRENT-WORK.md`, `handoff.md`,
   `COLLAB.md`; renderer behavior and machine sentinel semantics unchanged.
10. `continuity_guard.py` classification is untouched; `MERGED_NOT_FOLDED`
    remains unsafe generically.
11. No `job_store`/`worker_lease` schema or state-machine change; no new
    task/store/authority/provider path.
12. Crash replay stays effect -> durable fold checkpoint last. Partial or
    ambiguous fold remains recovery-required; deterministic identical replay
    may converge and CAS the checkpoint, never blind retry.
13. GOT-1a #409 composition scope untouched; no production snapshot provider
    created in this lane.

## Verification
- Focused three owned test files (RED-first fault matrix)
- `tests/test_work_order_identity.py`
- Related continuity/goal-closeout/agent-change regression files
- `python -m py_compile` on changed sources
- `git diff --check`
- Strict UTF-8 / no U+FFFD for changed files
- Added-line credential/secret-shaped scan
- Exact scope audit; `continuity_guard.py` / `job_store.py` / `worker_lease.py`
  confirmed unchanged
- Independent exact-SHA R3 review + exact-head CI + GPT expected-head merge /
  post-main verify (integrator-owned; not self-performed)

## Author evidence

- Attempt: 0001 — GLM-5.3 MAX via Kilo harness, this worktree.
- RED proof: `runs/WO-P1-410/author/attempt-0001/red_raw.txt` — owned
  suites RED before implementation (missing
  `MergeFoldReconciliation`/`MERGE_FOLD_TARGETS` import errors; 3
  `FoldRequest.merge_commit` failures in the closeout suite).
- Implementation: `MergeFoldReconciliation` typed identity +
  `AgentChangeApplier.apply_merge_fold_reconciliation` (shared
  `_active_lease`/`_continuity_snapshot`/`_materialize` pipeline; typed
  admission codes `RECONCILIATION_TARGET_UNSUPPORTED`,
  `RECONCILIATION_CLASSIFICATION_DENIED`,
  `RECONCILIATION_RECONCILE_REQUIRED`,
  `RECONCILIATION_MERGE_IDENTITY_MISMATCH`,
  `RECONCILIATION_DRIFT_UNRELATED`); `FoldRequest.merge_commit` populated
  by the executor from `MergeEvidence`; adapter selects the typed path
  only when the request carries merge identity (bound against
  `ProjectionFacts.merge_commit`, `PROJECTION_MERGE_MISMATCH` otherwise).
- Tests: 248 passed across the three owned files
  (`green_owned.txt`); 183 passed across related regression +
  work-order identity (`green_regression.txt`); zcode e2e helper 11
  passed.
- Verification: `py_compile` clean; `git diff --check` clean; strict
  UTF-8 / no U+FFFD on all seven changed paths; added-line
  credential/secret-shaped scan clean (941 added lines); exact scope =
  the seven allowed paths vs dispatch head `80d812cc`;
  `continuity_guard.py` / `job_store.py` / `worker_lease.py` unchanged.
- Status: READY_FOR_REVIEW — awaiting independent exact-SHA R3 review and
  exact-head CI on the pushed branch head. Integrator (GPT-5.6 Sol)
  merges; no self-accept/merge by the author lane.
