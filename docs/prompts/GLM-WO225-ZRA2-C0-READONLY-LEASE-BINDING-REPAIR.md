/goal

Execute WO-P1-225 as the highest-priority bounded ZRA-2 repair when this ZCode lane is eligible.

PRIMARY REPO:
A:\GitHub\A-Wiki-Conductor

PRIMARY WORK ORDER:
docs/work-orders/WO-P1-225-zra2-c0-readonly-lease-binding-repair.md

ROLE:
You are ZCode GLM-5.3 working as the bounded long-shift implementation/test executor. GPT-5.6 Sol remains architecture/integration/exact-SHA acceptance/merge authority.

WHY THIS SUPERSEDES C1 SOURCE WORK:
Current main `60aba770fd457d04f1e31040b9dfd7af3927f669` contains accepted C0 code, but fresh deterministic archaeology proved a trust-boundary defect: `bind_direct_review_route()` can return a route claiming READ_ONLY while the selected `WorkerLeaseRequest` is MUTATION-capable and belongs to a different task id.

Exact current-main reproducer evidence:

```text
LEASE_INTENT=MUTATION
LEASE_MUTABLE_SCOPE=('runs/**',)
HARNESS_INTENT=READ_ONLY
ROUTE_INTENT=READ_ONLY
MISMATCH_ACCEPTED=True
LEASE_TASK_ID=task-review-node
REVIEW_CONTRACT=zra2-review-v1:<digest>
LEASE_TASK_MISMATCH_ACCEPTED=True
```

Do NOT continue WO221/WO223 source mutation while this defect remains. Preserve any WO221 archaeology/checkpoint already produced, then execute only this bounded repair.

STARTUP / AUTHORITY GATE:
1. Read `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> `AGENTS.md` -> actual Git/claims -> `CURRENT-WORK.md` -> WO225 -> relevant protocol/evidence.
2. Read `DEFECT_LESSONS.md` before source mutation.
3. Re-pin current GitHub main, Issue #214, open PRs, active claims/worktrees and this packet branch. Do not trust creation-time SHAs if main moved.
4. Use a fresh isolated source worktree from then-current accepted main; do not mutate the protected dirty root checkout or the docs-only packet worktree.
5. Acquire/publish a non-overlapping WO225 claim for exactly the released source/test scope.
6. If another owner already repairs the same C0 defect, reconcile rather than duplicate.

ROOT CAUSE TO REPRODUCE, NOT ASSUME:
- `ParallelReadyTask.__post_init__` cross-binds project/worktree/branch/head/provider/task-packet/HarnessDispatch facts but does not require lease mutation intent or lease task id to equal the review contract.
- `bind_direct_review_route()` checks HarnessDispatch READ_ONLY but not `lease_request.mutation_intent` or `lease_request.task_id` before minting `DirectReviewRoute(mutation_intent="READ_ONLY")`.
- The old C0 positive fixture imports generic `_task()` whose lease defaults to MUTATION with mutable scope.

RED FIRST — REQUIRED:
Before production repair, capture deterministic failing tests proving at least:
1. MUTATION lease + READ_ONLY HarnessDispatch is rejected by direct-review binder;
2. MUTATION lease with `runs/**` scope cannot become a READ_ONLY review route;
3. true READ_ONLY lease + empty mutable_scope + `task_id == review_contract_ref` succeeds;
4. READ_ONLY lease with foreign task_id is rejected;
5. same provider/model/worker/worktree/branch/head but wrong lease task is rejected;
6. all existing packet/head/destination/author/reviewer anti-replay failures remain failures.

The RED must exercise current production binder behavior, not merely fail because a new helper/module is absent.

MINIMAL GREEN:
Repair `bind_direct_review_route()` in `src/a_conductor/zero_relay_review_task.py` with the smallest review-specific cross-binding:
- require typed lease request already carried by `ParallelReadyTask`;
- require `lease_request.mutation_intent is LeaseMutationIntent.READ_ONLY`;
- require `lease_request.task_id == review.refs.contract_ref`;
- preserve existing WorkerLeaseRequest invariant READ_ONLY => empty mutable_scope;
- keep all existing route identity/provenance checks.

Recommended typed codes:
- `REVIEW_LEASE_NOT_READ_ONLY`
- `REVIEW_LEASE_TASK_MISMATCH`

Equivalent bounded names are acceptable if current module conventions justify them.

TEST FIXTURE:
Correct the C0-local positive route fixture. Do not keep a mutation lease merely because generic AHA-6 `_task()` used one. Prefer replacing its lease request locally with:
- `mutation_intent=READ_ONLY`;
- `mutable_scope=()`;
- exact review contract as `task_id`;
while retaining existing project/worktree/branch/head/worker bindings.

PROTOCOL BYTES MUST NOT DRIFT:
This is route validation only. Do not change canonical `zra2-review-v1` bytes, deterministic contract digest/path, rendered task semantics, or result ref. Add a regression proving exact v1 bytes/identity remain stable.

DO NOT BROADEN GENERIC AUTHORITY:
Do not modify `ParallelReadyTask`, WorkerLeaseBroker/store, scheduler/provider/admission, or generic lease semantics just to repair this review-specific boundary. If deterministic evidence proves generic semantics MUST change, checkpoint exact DESIGN_GAP and STOP for GPT scope release.

ALLOWED MUTABLE SCOPE:
- `src/a_conductor/zero_relay_review_task.py`
- `tests/test_zero_relay_review_task.py`
- WO225 checkpoint/result evidence

READ-ONLY SUPPORTING ARCHAEOLOGY:
- `parallel_ready_execution.py`
- `worker_lease.py`
- `zcode_production_assembly.py`
- WO216/219/220/221/223 docs/evidence
- related tests

ADVERSARIAL CAMPAIGN AFTER GREEN:
- flip only lease intent READ_ONLY -> MUTATION;
- flip only lease task id;
- foreign lease for same worker/worktree/head/provider/model;
- Harness PROJECT_MUTATION vs read-only lease;
- stale head;
- wrong author result SHA/attempt/generation;
- wrong review result destination;
- packet bytes changed after persistence;
- candidate/worker drift;
- test-vacuity: locally demonstrate removing the new binder checks makes the new tests fail.

VERIFICATION FLOOR:
Run:
- focused `tests/test_zero_relay_review_task.py`;
- `tests/test_native_execution.py`;
- `tests/test_zero_relay_repair_materializer.py`;
- `tests/test_zero_relay.py`;
- `tests/test_claude_code_harness.py`;
- `tests/test_parallel_ready_execution.py`;
- `tests/test_agent_change_packets.py`;
- `tests/test_review_mailbox_adapter.py`;
- relevant WorkerLease tests only if actual imported behavior justifies them;
- compile/import changed source;
- diagnostics;
- `git diff --check`;
- strict UTF-8/no U+FFFD;
- tracked+untracked scope audit;
- added-line secret-shape scan;
- exact v1 task-byte stability proof.

Then freeze one coherent exact SHA, push a dedicated branch, create/update Draft PR, audit remote diff, record hosted CI state, and STOP for independent R3 review/GPT acceptance. Do not poll.

SEPARATE PREREQUISITE — DO NOT SOLVE HERE:
Canonical roadmap is:
`C0 route -> reviewer execution -> C1 ReviewEvidence`.
Reviewer execution is a separate node. Current archaeology has not yet proven a production READ_ONLY ZCode review execution adapter. Do not silently fold transport/wiring into this repair. Record any existing adapter you find; if source change would be needed, stop for GPT packet.

FORBIDDEN:
- C1/WO221/WO223 source implementation;
- Phase D / ZRA-3 / ZRA-4 source;
- generic scheduler/provider/lease/store redesign;
- mailbox identity fabrication;
- A-Wiki mutation;
- live provider/credential/process/DB changes;
- self-acceptance/merge/release.

LONG-SHIFT LOOP:
Use nested goals inside WO225:
`G0 recover/claim -> G1 reproduce authority mismatch -> G2 RED -> G3 minimal GREEN -> G4 adversarial -> G5 related regression/static -> G6 freeze/PR/checkpoint`.
Keep durable checkpoints so context rollover can resume without human relay.

STOP CONDITIONS:
Stop/checkpoint on ownership conflict, source drift, required scope expansion, UNKNOWN authority, hosted CI external gate, independent review gate, GPT acceptance, merge/post-main gate. Do not jump to unrelated backlog.

HANDOFF:
Record exact base/head/worktree/branch/PR, root cause, RED discriminator, changed paths, GREEN/adversarial/regression counts, v1-byte stability evidence, P0/P1/P2/P3 count, CI state, `merge_performed=false`, and exact next safe action.
