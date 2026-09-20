# WO-P1-409 — GOT-1a Production GoalCloseout Projection Wiring

Status: CLAIMED / IMPLEMENTATION_READY
Issue: #409
Parent: #405
Topology: CONTROL_PLANE_ONLY
Risk: R3
Authority repo: `A:\GitHub\A-Wiki-Conductor`
Execution repo: same repo
Branch: `feat/wo-p1-409-got-1a-production-closeout`
Base SHA: `c85484c23f6de86cf69edf1df6ab8b6e003cefd9`
Owner: GPT-5.6 Sol integrator; bounded GLM-5.3 MAX author after fresh quota/readiness.
Claim: `WO-P1-409-GOT-1A-PRODUCTION-CLOSEOUT-001`
Evidence: `runs/WO-P1-409/`

## Goal

Wire the already-accepted GoalCloseout and ContinuityProjectionFoldAdapter into a production composition seam without creating a second lifecycle, store, renderer, task authority, or continuity authority.

GOT-1a is composition/wiring only. GOT-1b / Issue #410 separately owns the MERGED_NOT_FOLDED trust-boundary reconciliation problem.

## Integrator decision D1

A production closeout entry may promote an existing job from `VERIFYING` to `REVIEW_PENDING` only when verification evidence is identity-bound to the same task and attempt and is durably checkpointed. If that proof is missing, stale, contradictory, or cannot be reconstructed from durable authority, fail closed and do not promote.

The canonical state graph already permits `VERIFYING -> REVIEW_PENDING`. This WO must not change `goal_closeout.py` planner/executor semantics.

## Reuse classification

`REUSE -> WRAP`.

Reuse:
- `DurableJobControlService`
- `GoalCloseoutExecutor` / `plan_goal_closeout`
- `SQLiteJobStore`
- `SQLiteWorkerLeaseStore`
- `AgentChangeApplier`
- `ContinuityProjectionFoldAdapter`
- existing native filesystem / lease / continuity / candidate observation authorities

No new persistence table, read model, scheduler, task store, claim store, review store, or Markdown-derived authority is allowed.

## Exact mutable scope

Only:
- `src/a_conductor/job_control.py`
- `src/a_conductor/goal_closeout_assembly.py` (new)
- `tests/test_goal_closeout_assembly.py` (new)
- `docs/work-orders/WO-P1-409-got-1a-production-closeout-wiring.md`

Everything else is read-only.

Specifically forbidden in GOT-1a:
- `src/a_conductor/goal_closeout.py`
- `src/a_conductor/continuity_projection.py`
- `src/a_conductor/agent_change_packets.py`
- `src/a_conductor/worker_lease.py`
- `src/a_conductor/job_store.py`
- `src/a_conductor/zero_relay_review_execution.py`
- `src/a_conductor/zero_relay_review_verification.py`
- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`

## Required design

1. Add a thin `goal_closeout_assembly.py` composition layer only.
2. Adapt the canonical lease store release signature to `LeaseReleasePort.release(lease_id)` while binding the existing session/task/clock identity.
3. Build projection facts only from durable/observed authorities. Never parse rendered Markdown as authority.
4. Assemble `AgentChangeApplier -> ContinuityProjectionFoldAdapter -> GoalCloseoutExecutor` using existing authorities.
5. Add a bounded `DurableJobControlService` closeout entry that performs at most one durable closeout stage per call.
6. Preserve CAS / `RELOAD_REPLAN` behavior. No internal blind retry.
7. VERIFYING jobs may enter REVIEW_PENDING only under D1. No direct COMPLETE shortcut added here.
8. FRESH/policy-required folds must work end-to-end.
9. Merge-required or post-main facts that are UNKNOWN stay fail-closed.
10. `MERGED_NOT_FOLDED` remains structurally blocked by current AgentChangeApplier in this WO; Issue #410 owns the narrow reconciliation authority. Do not weaken the applier here.

## RED-first acceptance

At minimum prove before implementation:
- current `DurableJobControlService` has no production closeout entry;
- current production composition does not assemble the projection fold;
- a bounded fixture representing canonical continuity targets receives no fold through current facade.

After implementation prove:
- real existing stores + injected deterministic continuity provider can drive the bounded facade through the existing executor;
- all three canonical projection targets are written only through AgentChangeApplier and read-back verified;
- matching fold checkpoint is written only after confirmed fold;
- exact active lease is released through the canonical lease authority and release checkpoint semantics remain intact;
- REVIEW_PENDING may become COMPLETE only through existing GoalCloseoutExecutor rules;
- idempotent republish causes no unnecessary writes;
- stale/unknown continuity or contradictory identity fails closed;
- merge-required/post-main UNKNOWN does not become complete;
- existing `tests/test_goal_closeout.py` and `tests/test_continuity_projection.py` pass unchanged.

## Verification

Run:
- focused `tests/test_goal_closeout_assembly.py`
- unchanged `tests/test_goal_closeout.py`
- unchanged `tests/test_continuity_projection.py`
- directly related job-control/job-state/agent-change tests as needed
- `python -m compileall` or focused compile
- `git diff --check`
- exact four-path scope
- strict UTF-8 / no U+FFFD
- added-line secret scan

Freeze exact candidate SHA, then independent exact-SHA R3 review and exact-head hosted CI. GPT-5.6 Sol owns acceptance/merge/post-main verification.

## Replay safety

GLM/result completion is only a claim. Every delegated run must persist a durable pointer under `runs/WO-P1-409/`. A new chat/session recovers pointer/process/result/Git before any redispatch. RUNNING is never duplicated. TERMINAL_UNHARVESTED is harvested first.

## Stop conditions

Stop mutation and return typed blocker if:
- scope must expand into any forbidden file;
- D1 cannot be satisfied from durable evidence without changing state semantics;
- production composition would require a second continuity/task/claim store;
- GOT-1b authority semantics become necessary to make a test pass;
- actual main/head/claim ownership drifts.
