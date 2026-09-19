# WO-P1-225 — ZRA-2 C0 direct-review READ_ONLY lease/task binding repair

Status: PREPARED / C0_REPAIR_NEXT / C1_HOLD
Parent: WO-P1-216 / WO-P1-219 / WO-P1-220 / WO-P1-221 / Issue #214
Owner: GPT-5.6 Sol integrator
Preferred executor: ZCode GLM-5.3
Base: `origin/main@60aba770fd457d04f1e31040b9dfd7af3927f669`
Risk: R3 — review-route mutation authority / exact task identity

## 1. Why this repair exists

C0 was accepted and integrated after WO219/WO220 repaired persisted-byte and route-path provenance. Fresh post-main C1 archaeology found an authority field that C0 did not cross-bind.

The accepted C0 contract says the direct route must be READ_ONLY and must reuse existing scheduler/provider/lease/harness authority. Current implementation checks only `HarnessDispatch.mutation_intent` before returning a frozen `DirectReviewRoute(mutation_intent="READ_ONLY")`.

It does **not** verify the corresponding `WorkerLeaseRequest.mutation_intent` or exact lease task identity.

Current positive C0 fixture proves the gap rather than merely suggesting it:

```text
LEASE_INTENT=MUTATION
LEASE_MUTABLE_SCOPE=('runs/**',)
HARNESS_INTENT=READ_ONLY
ROUTE_INTENT=READ_ONLY
MISMATCH_ACCEPTED=True
```

The same accepted fixture also has:

```text
LEASE_TASK_ID=task-review-node
REVIEW_CONTRACT=zra2-review-v1:<digest>
LEASE_TASK_MISMATCH_ACCEPTED=True
```

Thus a `ParallelReadyTask` carrying a mutation-authorized lease for a different task can currently mint a route that claims to be a read-only independent review route.

This is a trust-boundary defect. It blocks C1 consumption until repaired, independently reviewed, safely integrated and post-main verified.

## 2. Root cause

`ParallelReadyTask.__post_init__` already cross-validates many route facts:

- selected assignment;
- sole lease candidate worker;
- project;
- worktree;
- branch;
- HEAD;
- graph-dispatch work-order vs harness contract;
- task-packet contract vs harness contract;
- provider identity/authority;
- lease TTL vs execution timeout.

But it does not require:

- `lease_request.mutation_intent` to agree with `HarnessDispatch.mutation_intent`;
- `lease_request.task_id` to equal the review task contract.

The generic aggregate may have historical reasons for allowing those shapes. WO225 therefore must **not** broaden generic `ParallelReadyTask` semantics without separate evidence.

The narrow C0 binder is the correct first repair boundary because it is the authority that asserts `DirectReviewRoute.role == independent-review` and `mutation_intent == READ_ONLY`.

### 2A. Interrupted-lane claim reconciliation

Fresh GPT observation after the first ZCode dispatch found a protected source worktree already carrying in-scope edits but no durable WO225 claim on Issue #214:

`A:\GitHub\_worktrees\A-Wiki-Conductor-wo225-src`

Historical observation at that gate:

- branch `fix/wo-p1-225-c0-readonly-lease-binding`;
- base/HEAD `60aba770fd457d04f1e31040b9dfd7af3927f669`;
- dirty only `src/a_conductor/zero_relay_review_task.py` and `tests/test_zero_relay_review_task.py`;
- no `runs/WO-P1-225` checkpoint;
- ZCode processes existed on the host, but process existence alone did not prove task ownership.

This historical observation is not permanent state. On resume, recover actual state again.

If the existing dirty WO225 lane still exists:

1. preserve it; never reset/clean/stash/rebase/switch/recreate merely to satisfy a clean-start assumption;
2. inspect exact base/HEAD/status/diff and prove dirty paths remain inside released scope;
3. recover any durable owner/session evidence that may have appeared since this checkpoint;
4. before any further source mutation, publish/reconcile the missing claim on Issue #214 with actual executor/session, worktree, branch, base/HEAD, dirty paths, mutable/forbidden scope and overlap result;
5. state truthfully that pre-claim edits were recovered/protected, not retroactively pre-authorized;
6. continue only if the same owner is proven and the lane is non-overlapping; otherwise `CLAIM_OWNER_UNKNOWN` and STOP.

A branch name, worktree name or running ZCode PID is never sufficient ownership authority by itself.

## 3. Binding repair semantics

Before `bind_direct_review_route()` may return a `DirectReviewRoute`, prove all existing checks plus:

1. `route_task.lease_request` is the existing typed `WorkerLeaseRequest` carried by `ParallelReadyTask`;
2. `route_task.lease_request.mutation_intent is LeaseMutationIntent.READ_ONLY`;
3. because `WorkerLeaseRequest` already enforces READ_ONLY => empty `mutable_scope`, do not duplicate that invariant beyond a defensive assertion/check justified by typed state;
4. `route_task.lease_request.task_id == review.refs.contract_ref` (same exact review contract used by task packet / HarnessDispatch / GraphDispatch work-order);
5. no caller-supplied route field can downgrade a MUTATION lease to a returned READ_ONLY route;
6. no foreign task lease can authorize this review route.

Recommended typed failures:

- `REVIEW_LEASE_NOT_READ_ONLY`
- `REVIEW_LEASE_TASK_MISMATCH`

Equivalent bounded names are acceptable if consistent with current module conventions and tests.

## 4. Protocol identity rule

This repair changes route validation only.

Do **not** change accepted `zra2-review-v1` task bytes, canonical author identity, deterministic task path, review result ref, or content SHA merely to fix lease validation.

If source archaeology proves task bytes must change, STOP with `DESIGN_GAP` and return to GPT. Do not silently mutate `zra2-review-v1` semantics.

## 5. Initial mutable scope

Exact intended source/test scope:

- `src/a_conductor/zero_relay_review_task.py`
- `tests/test_zero_relay_review_task.py`
- this WO checkpoint/result evidence

Read-only inspection is allowed for:

- `src/a_conductor/parallel_ready_execution.py`
- `src/a_conductor/worker_lease.py`
- `src/a_conductor/zcode_production_assembly.py`
- current C0/WO219/WO220 evidence
- relevant tests

Do not modify generic scheduler/provider/lease/ParallelReady semantics without a separate GPT scope release.

## 6. RED-first minimum matrix

Write the intended RED tests before source repair.

### Required discriminators

1. existing current-positive shape with `lease_request.mutation_intent=MUTATION` + Harness READ_ONLY must fail typed;
2. same shape with non-empty mutation `mutable_scope` cannot mint a READ_ONLY route;
3. actual READ_ONLY lease with `mutable_scope=()` and exact `task_id == review_contract_ref` succeeds;
4. READ_ONLY lease with foreign `task_id` fails typed;
5. same worker/provider/model/project/worktree/branch/head but wrong lease task still fails;
6. same review contract but MUTATION lease still fails even if mutable scope points only under `runs/**`;
7. author execution == reviewer execution remains rejected;
8. task packet / dispatch contract / result destination / HEAD / author binding regressions remain rejected.

At least tests 1 and 4 must fail on current main for the exact missing authority checks.

## 7. Test fixture correction

The previous C0 positive fixture imported generic `_task()` from `test_parallel_ready_execution`, whose default lease is mutation-capable.

Do not keep that false-positive shape as the positive independent-review control.

Prefer one of:

- adapt the C0-local `_route_task()` helper to replace the lease request with an actual READ_ONLY lease, empty mutable scope, and exact review contract task id; or
- construct a purpose-built C0 review `ParallelReadyTask` fixture locally.

Do not weaken production checks to preserve an invalid old test fixture.

## 8. Production execution prerequisite remains separate

WO225 repairs C0 route truth only.

Fresh archaeology also found the roadmap node order:

`C0 route -> reviewer execution -> C1 ReviewEvidence`.

Current repository still requires a separately proven production execution adapter for the direct READ_ONLY reviewer. Do not solve that transport/wiring gap inside WO225.

Specifically:

- C1/WO221/WO223 does not own provider dispatch/reviewer execution;
- mutation-capable `zcode_production_assembly` requires a MUTATION lease and cannot be silently reused as READ_ONLY review execution;
- `GraphDispatchParallelRunner` / GraphDispatch construction is not automatically proof that HarnessDispatch/task-packet reviewer execution is live.

Record any newly discovered existing adapter and stop for GPT if scope expansion would be required.

## 9. Adversarial campaign after GREEN

Attack at least:

- mutate only lease intent from READ_ONLY -> MUTATION while keeping every other route fact identical;
- mutate only lease task id;
- preserve same worktree/head/provider/model but use a lease for another task;
- forged route task with mutation Harness vs read-only lease;
- stale HEAD;
- foreign author result SHA/attempt/generation;
- wrong result destination;
- packet bytes changed after materialization;
- candidate/lease worker drift;
- test vacuity: revert the new binder checks and prove new REDs fail.

No sleep-based correctness needed.

## 10. Verification floor

After GREEN run at minimum:

1. `tests/test_zero_relay_review_task.py`;
2. prior WO222/C0 relevant floor:
   - `tests/test_native_execution.py`
   - `tests/test_zero_relay_repair_materializer.py`
   - `tests/test_zero_relay.py`
   - `tests/test_claude_code_harness.py`
   - `tests/test_parallel_ready_execution.py`
   - `tests/test_agent_change_packets.py`
   - `tests/test_review_mailbox_adapter.py`;
3. relevant lease tests only if imported behavior needs verification;
4. compile/import changed source;
5. `git diff --check`;
6. strict UTF-8 / no U+FFFD;
7. changed tracked/untracked scope audit;
8. added-line secret/credential-shape scan;
9. exact v1 canonical task bytes regression proving no protocol-byte drift;
10. deterministic reproducer from §1 must flip from `MISMATCH_ACCEPTED=True` to typed rejection;
11. freeze exact SHA / Draft PR / hosted CI;
12. independent exact-SHA R3 review by a non-author;
13. GPT exact-SHA acceptance + safe fresh-main integration/post-main proof.

## 11. Forbidden scope

Without a separate GPT release, do not modify:

- `parallel_ready_execution.py`;
- `worker_lease.py`;
- scheduler/provider/admission stores;
- execution-store schemas;
- ZCode runtime/provider credentials;
- ReviewBridge/mailbox lifecycle;
- C1 evidence composer;
- Phase D / ZRA-3 / ZRA-4 source;
- A-Wiki;
- live Worker/process/DB state.

No self-merge or self-acceptance.

## 12. Dependency effect

Until WO225 is accepted, merged and post-main verified:

- `C1/WO221 source mutation = HOLD`;
- `WO223 source mutation = HOLD`;
- no `ReviewEvidence` may consume the current C0 route as proven READ_ONLY;
- Phase D remains downstream HOLD.

After WO225 closes, the next critical dependency is the actual **reviewer execution** node between C0 and C1. GPT will separately adjudicate/packet that seam; do not fold it into this repair.

## 13. Handoff

Freeze one exact candidate and record:

- base/head/worktree/branch/PR;
- exact changed paths;
- RED failures on current-main behavior;
- root cause;
- GREEN/adversarial/regression totals;
- v1 byte-stability proof;
- P0/P1/P2/P3 findings;
- hosted CI state;
- `merge_performed=false`;
- exact next safe action.

At first external gate, checkpoint and STOP. Do not poll or jump to another roadmap node.
