# WO-P1-094 — AHA-4 / GE-7 durable graph dispatch

Status: REVIEW_READY — PR #119 / FINAL SHA PENDING
Owner: GPT-5.6 Sol integrator
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha4`
Branch: `feat/wo-p1-094-aha4-durable-graph-dispatch`
Base: `origin/main@023c7b65026b0ff536cd1d802d6010e381a4447a`

## Goal

Connect one accepted GE-6 `SelectedAssignment` to the existing durable job-control execution path. Preserve the single job lifecycle, attempt counter, execution backend, dedup/recovery authority, and evidence path.

## Reuse gate

Classification: **REUSE + WRAP + EXTEND**.

Reuse:
- `DurableJobControlService`
- `SQLiteJobStore`
- `DurableJobExecutionCoordinator`
- supervised execution + canonical duplicate guard
- accepted `GE-0007`

Forbidden: second scheduler, job state machine, attempt counter, execution store, process runner, duplicate guard, or internal routing through `operator_dispatch.py`.
## Allowed scope

- new `src/a_conductor/graph/dispatch.py`
- new `tests/test_graph_dispatch.py`
- `src/a_conductor/job_control.py` + `tests/test_job_control.py` only for the smallest required public lifecycle seam
- package exports only if required
- this WO, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`

## Forbidden scope

- GE-6 scheduler semantics/tests except read-only integration use
- provider configuration / live gateway / user database
- PR #108 installer files
- North Star integration branch files
- A-Wiki repository mutation
- worker lease/fallback/heartbeat semantics (AHA-4A/4B)

## Acceptance

1. `{graph_id, graph_run_id, node_id}` deterministically maps to one collision-safe durable job identity.
2. Retry of the same key reuses/reconciles the existing job; a different graph run is distinct.
3. Exact scheduled worker is claimed through optimistic version/CAS semantics; stale/conflicting ownership cannot execute. Dispatch mode is resolved from injected authoritative worker facts; unknown/mismatched mode fails closed before durable launch.
4. Gate refusal occurs before `EXECUTING`, consumes no attempt, and leaves durable blocked/releasable state.
5. Successful dispatch reaches `VERIFYING` only through existing `execute_operation()` / coordinator.
6. Backend uncertainty reaches `RECOVERY_NEEDED`; reconnect/retry reconciles durable state and never blind-relaunches.
7. Existing execution fingerprint/dedup remains authoritative for external launch; this adapter does not reimplement it.
8. One node-local dispatch failure does not mutate unrelated graph assignments.
9. Focused deterministic tests, compileall, diff-check, and exact-head 3-OS CI pass before merge.

## Safety gate

Verified before mutation:
- remote: `https://github.com/aase7en/A-Wiki-Conductor.git`
- base/current main: `023c7b65026b0ff536cd1d802d6010e381a4447a`
- isolated worktree/branch were absent before creation
- shared root remains protected/dirty and is untouched
- PR #108 + North Star scopes do not overlap this claim
- PR #104 / GE-6 merged and exact reviewed head is ancestor of current main

`SAFE_TO_MUTATE = YES` only inside this isolated worktree and allowed scope.

## First micro-step

Write RED tests for stable dispatch identity, idempotent create/recover, exact worker claim, gate-before-attempt, success→VERIFYING, and recovery reconciliation. Then add the thinnest graph-dispatch wrapper over existing job control.
## Checkpoint — local implementation review ready

Implemented in bounded scope:
- deterministic SHA-256 durable `job_id` from `{graph_id, graph_run_id, node_id}`;
- immutable dispatch-metadata checkpoint pins project/work-order/operation/mode/attempt policy and the exact scheduled worker, preventing implicit worker fallback inside the same graph-run key;
- authoritative injected worker dispatch-mode resolver; unknown/mismatch fails closed;
- exact scheduled-worker CAS claim;
- gate deny -> durable `BLOCKED`, claim released, attempt count unchanged;
- `INTERACTIVE_PULL` -> durable `OFFERED`/claimed state only, no fake model push;
- `PROGRAMMATIC_PUSH` -> existing `gate()` + `execute_operation()` coordinator path;
- success -> `VERIFYING`; uncertainty -> `RECOVERY_NEEDED`; retry reconciles without relaunch;
- response-loss-after-GATING regression resumes once; node-local failure does not corrupt an independent dispatch.

Verification:
- `tests/test_graph_dispatch.py`: **18 passed**;
- graph/job-control/dedup/recovery suite: **183 passed in 7.08s**;
- AHA-2/AHA-3 + durable-dispatch regression set: **107 passed in 6.82s**;
- no scheduler/store/dedup/process-runner replacement introduced.

Next: compileall + diff-check, final scope/secret audit, checkpoint continuity, commit/push Draft PR, exact remote diff review, then 3-OS CI.

Final local gate before PR:
- `python -m compileall -q src/a_conductor`: PASS;
- staged `git diff --check`: PASS;
- exact staged scope: 8 allowed files only;
- bounded changed-file secret-pattern scan: PASS;
- forbidden duplicate/runtime scan in `graph/dispatch.py`: no sqlite/subprocess/dedup/operator-dispatch/scheduler-loop imports.

Local acceptance is GREEN. Draft PR #119 is open. Remote audit of head `3b97cfa` found one additional identity defect: the same graph-run key could silently change its scheduled worker. A failing regression was added and the immutable dispatch metadata now pins `worker_id`; focused dispatch is 18/18 green. Old-head CI run `33158379414` had Ubuntu/macOS green and a Windows supervised-command timeout/attach failure outside this PR's changed files; the same supervised suite passes locally 5/5 repeated runs. Push the worker-pin fix to create the final candidate SHA, then require fresh exact-head 3-OS CI before merge.
