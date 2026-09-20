# WO-P1-409 — GOT-1a Production GoalCloseout Projection Wiring

Status: IMPLEMENTED / PENDING_INDEPENDENT_REVIEW
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

## Implementation checkpoint (2026-09-20, GLM-5.3 MAX author attempt-0001)

- RED proof captured at dispatch head `bdfda249f5ac2466335a0a33ecf84545a3f7c58d` in `runs/WO-P1-409/author/attempt-0001/red-proof.txt`: no `closeout` entry on `DurableJobControlService`, `goal_closeout_assembly` absent, bounded canonical fixture receives no fold through the current facade.
- `goal_closeout_assembly.py` (new): `WorkerLeaseReleaseAdapter` binds the canonical `SQLiteWorkerLeaseStore.release` signature into `LeaseReleasePort.release(lease_id)`; `completed_closeout_checkpoint_refs` reconstructs stage refs from the durable CHECKPOINT journal; `CloseoutEvidenceBundle` carries identity-bound observed evidence; `assemble_goal_closeout_facade` wires `AgentChangeApplier -> ContinuityProjectionFoldAdapter -> GoalCloseoutExecutor`; `ProductionGoalCloseoutFacade.next_stage` performs at most one durable stage per call and enforces D1 (VERIFYING -> REVIEW_PENDING only with identity-bound, journal-reconstructible verify checkpoint; missing/stale/contradictory proof fails closed).
- `job_control.py`: optional `closeout` composition + bounded `closeout_next_stage` entry + typed `JobControlError`.
- Verification: `tests/test_goal_closeout_assembly.py` 24 passed; unchanged `tests/test_goal_closeout.py` + `tests/test_continuity_projection.py` 154 passed; related job-control/job-state/job-store/job-execution/agent-change/worker-lease battery 144 passed; compileall, `git diff --check`, exact four-path scope, strict UTF-8, added-line secret scan (one benign `secrets/**` scope-glob fixture match) PASS.
- Stop state: READY_FOR_INDEPENDENT_EXACT_SHA_R3_REVIEW. Author does not merge or self-accept.

## Repair checkpoint (2026-09-20, GLM-5.3 MAX author attempt-0002 — integrator P1 findings)

Integrator audit of candidate `f20e8605aec4140bd6afac2d05032861b1ea7b01` returned
CHANGES_REQUIRED (runs/WO-P1-409/integrator-p1-findings.md):

- P1-1 production assembly gap: `assemble_goal_closeout_facade` had no production
  caller; `DurableJobControlService.open()` built no closeout, so production open
  callers stayed `CLOSEOUT_NOT_CONFIGURED`.
- P1-2 stale multi-stage evidence: `ProductionGoalCloseoutFacade` captured one
  static `CloseoutEvidenceBundle` at construction and reused it across
  verify checkpoint -> promotion -> fold -> release -> complete.

RED proof (before src mutation) at dispatch head `f20e860` in
`runs/WO-P1-409/repair/attempt-0002/` (red-proof.txt, red-pytest.txt,
red-behavior.py/.txt):

- P1-1: `test_open_composes_closeout_using_same_store_end_to_end` fails
  `ImportError: cannot import name 'GoalCloseoutCompositionConfig'`; open() has
  no closeout composition input.
- P1-2: `assemble_goal_closeout_facade()` rejects `evidence_provider` (TypeError,
  4 RED tests); behavioral contrast on unmodified code: static facade returned
  RELEASE_REQUIRED and durably released the lease while the current trusted
  observation (blocking finding) returned BLOCK — a proven stale decision.
- RED run: 5 failed / 25 passed (24 prior tests stayed green).

Repair (same four-path scope only):

- `goal_closeout_assembly.py`: added `CloseoutEvidenceProvider` protocol
  (trusted per-stage evidence source, re-observed exactly once at the beginning
  of each `next_stage()`), `StaticCloseoutEvidenceProvider` (deterministic
  single-bundle lanes), per-stage bundle lifecycle (`_begin_stage`/`_end_stage`/
  `_stage_bundle` with typed `EVIDENCE_BUNDLE_INVALID` /
  `EVIDENCE_STAGE_NOT_ACTIVE` guards); `_promotion_stage`, `_executor_stage`,
  `_build_facts` and `_projection_facts` now bind ONE immutable
  `CloseoutEvidenceBundle` snapshot per stage (no mid-stage re-read); added
  `GoalCloseoutCompositionConfig.compose(job_store=...)` typed open-path
  composition helper. `assemble_goal_closeout_facade` now takes
  `evidence_provider` (explicit production contract).
- `job_control.py`: `open()` accepts optional typed `closeout_composition`;
  composes the facade from the SAME `SQLiteJobStore` open() creates (asserted by
  test); ordinary open() without closeout stays backward compatible
  (`CLOSEOUT_NOT_CONFIGURED`).

Verification (attempt-0002):

- `tests/test_goal_closeout_assembly.py` 30 passed (24 prior adapted to the
  provider API, semantically equivalent; 6 new: open-composition end-to-end,
  plain-open backward compat, changed-evidence-between-stages BLOCK,
  refresh-exactly-once-per-stage, invalid-bundle typed fail-closed zero writes,
  one-immutable-snapshot-through-single-stage with merge-identity switch).
- Unchanged `tests/test_goal_closeout.py` + `tests/test_continuity_projection.py`
  154 passed; related job-control/job-state/job-store/job-execution/
  agent-change/worker-lease(+recovery) battery 177 passed.
- compileall/py_compile, `git diff --check`, exact four-path scope, strict
  UTF-8 (no U+FFFD), added-line secret scan: PASS.
- GOT-1b MERGED_NOT_FOLDED gate untouched (test_merged_not_folded_... green).
- Stop state: READY_FOR_INDEPENDENT_EXACT_SHA_R3_REVIEW on the new candidate
  SHA. Author does not merge or self-accept.

## Stop conditions

Stop mutation and return typed blocker if:
- scope must expand into any forbidden file;
- D1 cannot be satisfied from durable evidence without changing state semantics;
- production composition would require a second continuity/task/claim store;
- GOT-1b authority semantics become necessary to make a test pass;
- actual main/head/claim ownership drifts.
