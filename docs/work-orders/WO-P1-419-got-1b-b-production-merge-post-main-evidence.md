# WO-P1-419 — GOT-1b-B production durable merge/post-main evidence provider

Status: CLAIMED / READY_FOR_IMPLEMENTATION
Issue: #419
Parent: #410 / #411 / GOT-1b
Topology: CONTROL_PLANE_ONLY
Risk: R3 — production closeout evidence provider feeds completion/reconciliation planning
Authority repo: A:\GitHub\A-Wiki-Conductor
Execution repo: A:\GitHub\A-Wiki-Conductor
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo419-got1bb-production-evidence
Branch: feat/wo-p1-419-got1bb-production-evidence
Base SHA: 0c4453cc725ed1804776dfa25bd3936bdc6652a1
Prerequisite accepted merge: PR #416 / GOT-1b-A merged at 0c4453cc725ed1804776dfa25bd3936bdc6652a1
Post-main CI: run 35494699488 SUCCESS at exact merge SHA

## Goal

Implement the smallest production READ-ONLY evidence provider that composes durable closeout authorities with bounded GitHub/local-Git observations into the existing CloseoutEvidenceBundle. No planner/classifier/store/lease/review/fold/completion authority may be duplicated or weakened.

The provider observes and binds facts; existing GoalCloseout planning and continuity classification remain the sole decision authorities.

## Claim

Claim ref: WO-P1-419-GOT1BB-PRODUCTION-EVIDENCE-001
Owner: A-Faster mutable lane
Replay safety: recover execution pointer/process/result/Git before redispatch; source mutation is Git-bounded.

## Exact mutable scope

- src/a_conductor/production_closeout_observation.py
- tests/test_production_closeout_observation.py
- docs/work-orders/WO-P1-419-got-1b-b-production-merge-post-main-evidence.md

Everything else is READ ONLY. Any need to edit another path is SCOPE_EXPANSION_REQUIRED.

## Reuse requirements

REUSE or WRAP existing accepted authorities:
- project_identity.StrictReadOnlyGitRunner style and fixed read-only Git argv
- goal_closeout_assembly.CloseoutEvidenceProvider / CloseoutEvidenceBundle
- goal_closeout.MergeEvidence and existing planner finding codes
- completed_closeout_checkpoint_refs and SQLiteJobStore CHECKPOINT events
- SQLiteWorkerLeaseStore health through existing lease surfaces
- zero_relay_review_evidence durable accepted-review evidence + re-pin pattern
- native_git_transactions snapshot/re-pin precedent
- upstream_check injected bounded-fetcher style only as a transport pattern

Do not change accepted authority modules.

## Allowed new seams

Inside production_closeout_observation.py only:
1. MergeObservationPort: bounded read-only PR merge observation.
2. PostMainRunObservationPort: bounded read-only CI run observation.
3. A fixed local-Git read-only ancestry wrapper sufficient to prove accepted candidate ancestry against an observed merge commit without mutating/fetching.
4. ProductionCloseoutEvidenceProvider composing the above with durable authorities into one re-pinned CloseoutEvidenceBundle.

No new persistence/store/queue/scheduler/claim/lease/review/fold/completion authority.

## Identity binding

A successful bundle must remain bound to the existing stage identity and exact facts, including as applicable:
- job_id / task_id / attempt_id / session_id
- candidate_sha
- branch / actual_head
- reviewed_head and accepted review disposition
- accepted merge commit SHA
- accepted candidate SHA and ancestry
- post-main run ID
- post-main run head SHA == exact accepted merge commit SHA
- post-main success
- canonical lease identity/state
- fold/release/verify/complete checkpoint refs already defined by GoalCloseout

Free-form Issue/Markdown text is never evidence.

## Stage snapshot / re-pin model

One evidence() call performs bounded ordered reads and returns only an internally consistent immutable bundle:
1. read durable checkpoint/review/lease facts;
2. read local Git head/branch;
3. read merge observation;
4. read post-main run observation;
5. re-read the durable checkpoint refs and local Git head;
6. compare first/last observations.

Any missing, unavailable, stale, contradictory, malformed or changed fact fails closed. Do not coerce UNKNOWN into success.

## Merge observation contract

Merge observation is read-only and explicit, not a bare bool. At minimum bind:
- observed / availability state
- repository identity
- PR number
- merged: bool | unknown
- merge_commit_sha: str | unknown
- pr_head_sha: str | unknown

PR head must match the configured accepted candidate. A merge commit absent from the local object database yields ancestry UNKNOWN/fail closed; this WO does not perform network Git fetch.

## Post-main observation contract

Post-main observation binds:
- repository identity
- workflow identity pinned by configuration
- run_id
- run head_sha
- conclusion / pending state

Only a run whose head_sha equals the exact accepted merge_commit_sha can set the existing post_main_success evidence. A green run for another SHA fails closed through existing planner semantics.

## Fold / release construction

Do not invent a second fold record. MergeFoldFact factual inputs must be derived from accepted merge identity + existing durable closeout checkpoint refs + canonical lease/release evidence. classify_continuity remains the sole classifier.

## RED-first acceptance matrix

Write tests first and capture RED before implementation. At minimum:
1. full bound observation success composes a bundle that existing GoalCloseout can consume;
2. post-main run head != merge commit -> existing POST_MAIN_IDENTITY_MISMATCH path / no success;
3. PR head != candidate -> MERGE_CANDIDATE_MISMATCH / fail closed;
4. merged unknown/unavailable -> no fabricated merge success;
5. post-main pending -> POST_MAIN_PENDING;
6. ancestry false/unknown -> MERGE_ANCESTRY_MISMATCH / fail closed;
7. checkpoint journal changes during observation -> typed provider failure, zero writes;
8. local HEAD changes during observation -> typed provider failure, zero writes;
9. accepted review record missing/non-ACCEPTED/reviewed_head mismatch -> existing REVIEW_* blocking evidence;
10. fold state derives only from existing journal refs; provider writes no fold record;
11. lease evidence uses canonical lease authority only;
12. remote/transport malformed/unavailable -> fail closed, no partial success bundle;
13. observation DTOs reject malformed SHA/run/repo identity as appropriate;
14. no network call occurs in pure planner/classifier modules;
15. provider performs no Git mutation/fetch/checkouts and no durable writes.

## Verification

- focused tests/test_production_closeout_observation.py
- unchanged tests/test_goal_closeout.py
- unchanged tests/test_goal_closeout_assembly.py
- unchanged tests/test_job_control.py
- unchanged tests/test_continuity_guard.py where relevant
- tests/test_work_order_identity.py
- py_compile changed source/test
- git diff --check
- strict UTF-8 / no U+FFFD
- added-line secret-shaped scan
- exact three-path scope audit

Freeze exact candidate SHA after deterministic GREEN. Require independent GLM-5.3 MAX R3 review + exact-head hosted CI before acceptance/merge.

## Forbidden

- no mutation of goal_closeout.py, goal_closeout_assembly.py, job_control.py, job_store.py, worker_lease.py, continuity_guard.py, continuity_projection.py, or any PR #416 path
- no second planner/classifier/store/lease/review/fold/completion authority
- no free-form issue/comment/Markdown acceptance evidence
- no network Git fetch
- no Git mutation
- no hidden retry/notification/wake/resume authority
- no secret-bearing durable data

## Stop conditions

STOP and checkpoint if correctness requires mutation outside the three paths, new durable schema/store, planner/classifier changes, network Git mutation/fetch, or evidence semantics inconsistent with accepted GOT-1a/1b-A contracts.

No self-review, self-accept, or self-merge.
