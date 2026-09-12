# WO-P1-226 — ZRA-2 reviewer execution bridge over accepted ZRA-1 transport

Status: NEXT_READY_AFTER_ASTRA_PACKET_REPAIR / R3 / DESIGN_GAP_STOP_IF_NO_EXISTING_WINNER_AUTHORITY
Date: 2026-09-12 (Asia/Bangkok)
Repository: `aase7en/A-Wiki-Conductor`
Base at packet creation: `origin/main@60aba770fd457d04f1e31040b9dfd7af3927f669`
Release base after accepted WO225/post-main: `origin/main@7afb33d738086db50bc027c4c47165179a1cb96f`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo226-zra2-reviewer-execution`
Branch: `docs/wo-p1-226-zra2-reviewer-execution-bridge`
Parent roadmap: WO-P1-165 / Issue #214 / ZRA-2
Immediate predecessor: WO-P1-225 C0 READ_ONLY lease/task binding repair
Downstream: WO-P1-223 strict semantic result/C1 evidence -> WO-P1-205 Phase D
Integrator: GPT-5.6 Sol
Preferred implementation executor after release: ZCode GLM-5.3 MAX
Risk: R3 execution/provider/lease/recovery trust boundary

## 1. Why this WO exists

Fresh GPT-5.6 Sol archaeology found a missing canonical node in the ZRA-2 critical path:

```text
C0 deterministic review task + trusted route
  -> REVIEWER EXECUTION              <-- missing production bridge
  -> durable reviewer execution/artifacts
  -> C1 semantic ReviewEvidence
```

WO210 already described this ordering. WO201/C1 explicitly does **not** own reviewer execution/provider dispatch.

The current C0 implementation proves deterministic review-task identity and a typed `DirectReviewRoute`, but it does not execute the reviewer. C1 cannot safely validate artifacts that have never been produced through an accepted production route.

This WO closes only that missing reviewer-execution transport/handoff seam. It does not parse ACCEPTED/REJECTED semantics into `ReviewEvidence`; that remains WO223/C1.

## 2. External release gate

Do not mutate product source from this packet until all are true from actual current evidence:

1. WO225 exact source repair is frozen, independently reviewed, accepted by GPT, merged, and post-main verified.
2. Repaired C0 refuses any route unless the exact review `ParallelReadyTask` proves at least:
   - `HarnessDispatch.mutation_intent == READ_ONLY`;
   - `WorkerLeaseRequest.mutation_intent == READ_ONLY`;
   - `WorkerLeaseRequest.mutable_scope == ()`;
   - lease task identity is exactly bound to the review contract/packet identity as released by WO225.
3. Issue #214 explicitly marks `WO226_REVIEWER_EXECUTION_NEXT_READY` or equivalent.
4. A fresh isolated implementation worktree/branch/claim is created from then-current main.
5. No overlapping source owner exists for the released mutable scope.
6. Independent Astra pre-implementation contract audit exact commit `f99cd9aadceb903649cdbf577935267a362540eb` has been folded into this packet: proven duplicate-winner/multiplicity and cleanup-API findings are now binding RED/stop conditions.

WO225 is now accepted/merged/post-main at `7afb33d738086db50bc027c4c47165179a1cb96f`; gate 1 is satisfied. GPT-5.6 Sol may publish `WO226_REVIEWER_EXECUTION_NEXT_READY` only after this amended packet is frozen and the live claim/scope gate remains non-overlapping.

If any remaining gate is absent or ambiguous: checkpoint and STOP. Do not infer mutation authority from this packet alone.

## 3. Durable archaeology facts — authority, not design guesses

### 3.1 Accepted ZRA-1 real-provider path exists and MUST be reused

Issue #213 / WO179 ZRA-1 LIVE-3 is accepted by independent GLM review and GPT integration acceptance.

Live accepted facts include:

- one real authorized `cointh-glm / GLM-5.3` turn;
- zero human relay inside model execution;
- exact task-bound response;
- canonical provider admission + WorkerLease;
- supervised ZCode child/process ownership;
- exact task/report/response hashing;
- no orphan process;
- provider admission RELEASED;
- WorkerLease RELEASED;
- same-identity duplicate assessment `REUSE_COMPLETED`, `retry_authorized=False`;
- no credential-shaped material in preserved artifacts.

Therefore WO226 must **REUSE/WRAP/EXTEND the accepted ZRA-1 source path**. It must not create a second ZCode transport, provider authority, lease store, execution store, retry engine, scheduler, process supervisor, or secret resolver.

Relevant accepted source authorities include:

- `zcode_production_assembly.assemble_zcode_execution`
- `zcode_runner.SupervisedZCodeRunner`
- `supervised_run_coordinator.SupervisedRunCoordinator`
- `execution_store.SQLiteExecutionStore`
- `execution_deduplication.ExecutionFingerprintSpec` / `DuplicateExecutionGuard`
- `worker_lease.WorkerLeaseBroker` / canonical lease store
- `provider_config_store.SQLiteProviderConfigStore` / provider admission authority
- `RecoveryReconciliationService`
- accepted owned-process/supervised execution authorities

### 3.2 Three identities are distinct by design

Do not conflate these identities:

1. **dispatch-context identity** — C0/Harness/ProviderAdmission identity, e.g. LIVE-3 `exec-zra1-live-3` or C0 `graph-dispatch-...`;
2. **durable job identity** — accepted ZRA-1 production assembly currently derives `job:<task_contract_ref>`;
3. **durable runtime execution identity** — `SupervisedRunCoordinator` creates/reuses `DurableExecutionRecord.execution_id`, e.g. LIVE-3 `exec-cdfb98243b274caf`.

LIVE-3 independent adjudication explicitly proved the derived runtime execution ID is bound to the dispatch identity through canonical admission/batch + task/runtime identity. Equality is neither required nor expected.

Therefore any contract that requires:

```text
DurableExecutionRecord.execution_id == DirectReviewRoute.dispatch_execution_id
```

is wrong for the accepted production path and MUST NOT be implemented.

Required relation instead:

```text
route.dispatch_execution_id
  == canonical ProviderAdmission.execution_id
  == accepted dispatch-context identity

AND

DurableExecutionRecord.execution_id
  == actual supervised runtime execution identity

AND both are cross-bound through the same exact task/packet/provider/model/project/worktree/branch/HEAD/runtime fingerprint.
```

### 3.3 Sacrificial LIVE-3 proof used a production-unsafe record lookup shortcut

The preserved LIVE-3 proof script used:

```sql
SELECT execution_id FROM execution_records ORDER BY rowid DESC LIMIT 1
```

That was acceptable only inside its isolated sacrificial single-execution proof environment. It is forbidden in WO226 production code.

Production handoff MUST identify the exact durable execution from deterministic execution identity/fingerprint authority, e.g. existing `ExecutionFingerprintSpec` + `SQLiteExecutionStore.find_by_fingerprint`, with exact identity revalidation.

Never use latest row, latest timestamp, newest run directory, ambient PID, or directory enumeration as execution identity.

### 3.4 C0 route is protocol/route authority, not execution completion

`DirectReviewRoute` currently carries deterministic task/author/route facts but does not own runtime execution state.

WO226 output must be a separate typed immutable handoff, conceptually such as:

```text
DirectReviewExecutionHandoff
  route identity
  dispatch-context identity
  execution fingerprint
  actual durable execution_id
  durable record version/state
  stdout_ref
  report_ref
  result_ref
  exact task packet ref/hash
  provider/model/project/worker/repo/worktree/branch/HEAD
  canonical provider admission id/batch/dispatch identity
  canonical WorkerLease id/session/task identity
  canonical cleanup/release outcome refs or typed proven terminal cleanup state
```

Exact names are implementation-owned after archaeology.

Do not call this `ReviewEvidence`. C1 owns semantic review evidence.

### 3.5 Direct supervised ZCode raw result authority

For the direct ZCode path, physical response authority is the bounded supervised execution artifact set (`stdout_ref`, report, result metadata) owned by the durable execution record.

C0's deterministic `review_result_ref` remains protocol-level route/result identity. Do not force the ZCode child to write arbitrary caller-selected paths merely to make these refs equal.

WO223/C1 is responsible for strict raw-byte semantic validation after WO226 proves the exact execution/artifact provenance.

## 4. Architecture decision

Preferred classification:

| Seam | Decision |
| --- | --- |
| ZCode transport/process lifecycle | REUSE |
| execution store/fingerprint/dedup | REUSE |
| provider config/admission authority | REUSE |
| Worker lease authority | REUSE |
| secret reference/resolution | REUSE |
| recovery reconciliation | REUSE |
| scheduler/GraphDispatch | NOT REIMPLEMENTED |
| reviewer execution orchestration | WRAP/EXTEND in bounded ZRA-2 module |
| READ_ONLY ZCode assembly support | EXTEND existing ZRA-1 assembly only if required |
| reviewer semantic parser | DEFER WO223/C1 |

Do not modify AHA-6 scheduler/parallel execution merely to transport one review unless archaeology proves the accepted ZRA-1 path cannot be wrapped safely. A broad scheduler/result-policy refactor is not authorized by default.

## 5. Preferred production shape

Prefer one new bounded module such as:

`src/a_conductor/zero_relay_review_execution.py`

with focused tests:

`tests/test_zero_relay_review_execution.py`

It should consume a **validated repaired-C0 route/task** plus injected existing authorities. It must not select a different worker/provider/model/task.

Conceptual one-attempt flow:

```text
validated ParallelReadyTask + DirectReviewRoute
  -> re-bind exact C0 identities
  -> require ZCODE_APP_SERVER execution strategy for this direct ZCode path
  -> derive pure execution plan + exact fingerprint BEFORE external effect
  -> inspect ALL equivalent fingerprint records, not matches[0]
      any multiplicity/live/ambiguous conflict -> RECOVERY_REQUIRED / no launch
      exact single completed equivalent -> validate exact route/worker/runtime facts
      no equivalent execution -> candidate-to-launch only
  -> acquire/prove ONE canonical durable launch winner through an EXISTING authority
      no second guard check / capacity=1 / same lease+admission reentry as winner proof
      no existing authorized winner seam -> DESIGN_GAP and STOP
  -> acquire/reuse exact canonical READ_ONLY WorkerLease + ProviderAdmission
  -> durably associate winner + fingerprint + lease/admission identities BEFORE model effect
      no existing canonical association seam -> DESIGN_GAP and STOP
  -> accepted ZRA-1 supervised ZCode assembly/run
  -> locate/reconcile ALL exact durable executions by fingerprint (never latest-row)
  -> prove task/provider/model/project/worker/repo/branch/HEAD/runtime bindings
  -> terminal/recovery classification
  -> retain exact artifact refs
  -> reconcile/release exact provider admission + WorkerLease using their actual API semantics
  -> immutable DirectReviewExecutionHandoff only after execution + cleanup truth are proven
```

Do not parse reviewer JSON/verdict in this WO.

### 5.1 Mandatory pure pre-effect execution plan

Fresh GPT archaeology proved the current `assemble_zcode_execution()` cannot be used to compute the dedup fingerprint before external effects: it requires an already-active canonical `WorkerLease` and `ProviderAdmissionRecord` before it returns a `SupervisedZCodeRunner`, while `SupervisedZCodeRunner` itself exposes only `argv()` and `run()` and no public fingerprint/spec method.

WO226 MUST therefore create/reuse one **pure planning seam** before any lease/admission/process/secret-value effect. Exact symbol names are implementation-owned, but the plan must deterministically derive from trusted task/route/provider/runtime facts:

- verified `ZCodeTaskPacketIdentity` including full packet SHA;
- exact review contract / durable job identity;
- project/repo/branch/HEAD;
- selected provider/model + current provider generation/endpoint/runtime binding;
- derived `runtime_profile_ref` via the accepted ZCode runtime-identity function;
- canonical operation ref from the exact task packet;
- exact fixed ZCode argv;
- the exact `SupervisedRunIdentity` fields used later by the real coordinator;
- `ExecutionFingerprintSpec` and its SHA-256 fingerprint.

Planning MUST be side-effect free: no provider admission acquire/release, no WorkerLease acquire/release, no process spawn, no secret-value resolution, no execution/job-store mutation, and no newest-row/run-directory lookup.

Prefer one shared helper consumed by both preflight and launch assembly so the fingerprint inputs cannot drift. If launch assembly recomputes the plan, it MUST prove exact equality with the pre-effect plan before spawn. Do not copy the fingerprint formula into a second independent implementation.

The dedup gate then runs on this pure plan **before** lease/admission acquisition. However, Astra's independent barrier probe proved current dedup assessment is observational, not atomic launch ownership: two same-fingerprint callers can both observe no match and later create two durable runtime IDs. Therefore `SAFE_TO_LAUNCH` is only a candidate state, never launch authority by itself.

Before lease/admission acquisition or model/process effect, the coordinator must acquire/prove **one canonical durable winner** through an existing authorized authority with compare-and-set/ownership semantics. A second dedup check, provider capacity=1, same-owner WorkerLease reentry, or EXISTING ProviderAdmission are explicitly insufficient winner proof. If no existing authority within released scope can provide this, checkpoint `DESIGN_GAP` with the exact call graph and STOP; do not add a second lock/store/scheduler.

For replay wording, `REUSE_COMPLETED` means **no new model/launch/acquire effect**. Exact cleanup/reconcile effects may still be required after a lost acknowledgement and are governed by §10. `ATTACH_RUNNING` and blocked/unknown states never launch a second child.

### 5.2 Fingerprint is not reviewer-worker authority

Fresh GPT archaeology also proved `ExecutionFingerprintSpec` / `_identity_matches()` does **not** include `worker_id`. This is accepted shared dedup semantics and WO226 must not silently change it globally.

Therefore every duplicate assessment record and every post-run durable record MUST additionally prove:

`record.worker_id == DirectReviewRoute.reviewer_worker_id == selected lease.worker_id`

before reuse/attach/handoff. Same fingerprint + foreign worker is an identity conflict/recovery condition: do not reuse it and do not launch another child under the same fingerprint merely to work around the conflict.

### 5.3 Astra-proven multiplicity and crash-association blockers

Independent Astra contract audit exact commit `f99cd9aadceb903649cdbf577935267a362540eb` proved two current shared-authority limitations that WO226 must not paper over. The report is review-branch evidence, not main; source implementers must read it by exact Git object (for example `git show f99cd9aadceb903649cdbf577935267a362540eb:docs/reviews/WO-P1-226-astra-contract-review.md`) rather than assuming the path exists in their worktree:

1. `DuplicateExecutionGuard` + current coordinator/store are not an atomic single-winner launch fence. Barrier-forced same-fingerprint calls can both pass an empty lookup and create distinct durable runtime IDs.
2. shared duplicate lookup currently consumes `matches[0]`; store ordering may present a newer completed equivalent while an older RUNNING equivalent still exists. A single returned record is therefore insufficient multiplicity proof.

WO226 wrapper/coordinator must inspect/reconcile **all** equivalent fingerprint records available from the canonical execution store before launch, cleanup or handoff. If more than one equivalent exists and any member is live, unknown, identity-conflicting or otherwise not canonically collapsed to one winner, return typed recovery and perform no new model/launch/acquire effect.

A durable association between the chosen winner and the exact WorkerLease/ProviderAdmission identities must exist **before model effect** so restart after lost acknowledgement can reconstruct cleanup ownership without guessing from newest rows, worker-only lookup or ambient process state. Reuse an existing job/checkpoint/event/ownership authority if one truthfully supports this. If no existing canonical association seam exists within released scope, checkpoint `DESIGN_GAP` and STOP rather than inventing a new store/schema.

### 5.3 Sol architecture adjudication after Astra F1/F2/F3

Current-main archaeology after WO225/WO224 identifies two existing authorities that WO226 should try to REUSE before declaring a design gap. These are candidate composition seams, not permission to broaden shared-source scope silently.

**Single-winner candidate (Q1): durable GraphDispatch job execution CAS.** `GraphDispatchKey.job_id` is deterministic from graph/run/node. `GraphDispatchCoordinator.dispatch()` creates/loads that job, advances NEW/BLOCKED -> READY -> CLAIMED -> GATING under the selected worker, then delegates `execute_operation()`. `DurableJobExecutionCoordinator.execute()` performs the version-checked `GATING -> EXECUTING` transition before backend execution; its source explicitly treats that durable transition as the last gate before external execution. Two callers presenting the same pre-execution version cannot both win that CAS.

WO226 should therefore prefer proving that the repaired C0 `ParallelReadyTask.dispatch_request.key.job_id` is the canonical reviewer execution job and then reuse this existing durable execution gate. Do **not** create a second job id merely to obtain a lock. The supervised ZCode durable job id `job:<review_contract_ref>` remains a distinct downstream runtime identity and must be cross-bound, not equated, with the GraphDispatch durable job id. If the current route cannot truthfully bind to one canonical GraphDispatch job lifecycle, checkpoint `DESIGN_GAP` before any model/provider effect.

**Resource-reconstruction candidate (Q2): canonical owner-key reentry.** Existing authorities already support lost-ack reconstruction without a new resource-link schema:

- `WorkerLeaseBroker.acquire()` first resolves the active lease by exact `(session_id, task_id)`, revalidates the full request, and returns the same canonical lease as `EXISTING` when healthy;
- provider `acquire_admission()` resolves a prior record by exact `(provider_id, execution_id)`, cross-checks deterministic `batch_id` and configuration generation, and returns that prior record as `EXISTING` or typed recovery/terminal reconciliation rather than minting unrelated capacity.

WO226 may use these accepted reentry contracts to reconstruct exact lease/admission identities after lost acknowledgement, but only after the single-winner durable job gate is proven. Reentry/reconciliation must never become a way for a second caller to obtain launch authority. Cross-bind the recovered resource records back to route task, dispatch id, batch id, provider generation, reviewer worker/session/task and current durable job ownership.

Provider and lease cleanup remain API-specific: provider lost-ack release is resolved by exact prior admission reread/reconciliation, while WorkerLease release accepts only canonical released/already-released truth. Do not normalize them into one generic truthy cleanup abstraction.

## 6. READ_ONLY assembly rule

Current accepted `assemble_zcode_execution()` is the mutation-capable ZRA-1 composition and currently requires a canonical `WorkerLease` with `LeaseMutationIntent.MUTATION` + authorized non-empty mutation scope.

WO226 may make the smallest backward-compatible extension needed for reviewer execution, for example a dedicated READ_ONLY assembly entrypoint or a shared internal validator with explicit mode.

Fresh GPT archaeology proved the accepted ZCode protocol driver denies every observed `interaction/requestPermission` request with `{approved: false}` and no permission-grant path exists in that protocol source/tests. Reuse and regression-pin that behavior, but **do not overclaim it as a universal filesystem/tool sandbox**: Astra audit confirmed this only proves denial when such a permission request occurs, not that every possible app-server write is necessarily mediated by that request. A READ_ONLY assembly extension must not introduce any permission-grant path, rely on prompt wording as the mutation fence, or claim broader write prevention without identifying the actual accepted runtime/tool/OS mediation authority.

Required semantics for review execution:

- lease mutation intent is exactly `READ_ONLY`;
- lease mutable scope is empty;
- requested mutable scope is empty;
- review task packet is exact and hash-verified;
- repo/worktree/branch/HEAD/provider/model/generation/endpoint/secret-ref facts remain bound exactly as in accepted ZRA-1;
- no write authority is silently upgraded;
- existing mutation-capable `assemble_zcode_execution()` behavior remains byte/behavior compatible for its callers unless a separately justified repair is required.

Do not weaken accepted ZRA-1 gates to make review execution fit.

## 7. Deterministic batch / provider admission identity

Derive a versioned deterministic reviewer batch identity from trusted facts, not caller prose. A valid conceptual input set is:

```text
review contract ref
+ route dispatch-context identity
+ reviewed HEAD
+ exact task SHA
```

Use the existing provider admission store. Provider admission must bind:

- exact provider;
- route dispatch-context execution ID;
- deterministic batch ID;
- exact current provider generation;
- non-expired ACTIVE record before execution.

Do not create a second provider semaphore/store.

## 8. Durable execution fingerprint / replay rules

Use existing execution deduplication authority.

The fingerprint must be derived from the same trusted facts used by the actual supervised runner, including current accepted fields such as:

- project ID;
- durable job ID;
- work-order/review-contract ref;
- backend ID;
- repo root;
- branch;
- HEAD before execution;
- canonical operation ref derived from exact task identity;
- runtime profile ref;
- exact fixed ZCode argv.

Required replay semantics:

- compute the exact fingerprint from the pure pre-effect plan before lease/admission acquisition;
- enumerate/reconcile **all** canonical records for that fingerprint before deciding launch/reuse/cleanup; never rely on only `matches[0]`;
- zero matches -> still only a candidate-to-launch; a separate existing durable winner/ownership authority must succeed before acquire/model effect;
- exactly one completed equivalent -> revalidate exact worker/route/task/runtime facts, then reconstruct execution state; no new model/launch/acquire effect, but exact cleanup/reconcile may still be required;
- exactly one live equivalent -> revalidate exact worker/route/task/runtime facts, then attach/reconcile; never spawn second child;
- multiple equivalents where any member is live/unknown/identity-conflicting -> `RECOVERY_REQUIRED`; no launch, handoff or resource release based on a newer completed row;
- multiple completed equivalents are not silently collapsed by newest-time/rowid; require an existing canonical winner/reconcile proof or return recovery;
- same fingerprint with foreign reviewer worker -> identity conflict / recovery; no reuse and no second launch;
- unknown/ambiguous identity -> fail closed/recovery;
- changed task SHA/contract/HEAD/provider/model/runtime profile -> different fingerprint and never reuse old result.

`ExecutionFingerprintSpec` does not itself carry `worker_id`; worker equality is a separate mandatory route/record/lease cross-binding, not an inferred fingerprint property. Shared global dedup semantics are not modified by WO226 without separate GPT scope release; the bounded reviewer wrapper must add the stricter multiplicity gate it needs or STOP `DESIGN_GAP`.

## 9. Reviewer durable job / recovery semantics

Fresh archaeology must determine the smallest truthful use of the existing durable job authority.

Accepted ZRA-1 uses durable job identity derived from task contract and existing JobStore/recovery composition. Reuse this authority where needed for transport/recovery ownership.

Do not create a second lifecycle/state machine.

If recovery composition requires the exact existing reviewer job, job identity and worker ownership must be deterministic and cross-bound to the same review contract/route.

UNKNOWN execution/process state must remain recovery-consuming. Never release capacity or retry merely because a timeout occurred.

## 10. Resource release truth

Provider admission and Worker lease release are external authority effects.

Reuse existing release APIs and exact identity fences. Never infer release from local intent.

Required behavior:

- terminal usable execution -> reconcile/release according to the **actual canonical API contract**, not one generic boolean/idempotent adapter;
- provider-admission lost-ack replay: re-read the exact admission by canonical identity; accept terminal `RELEASED` only when provider/dispatch-context/batch/generation identity still matches. A repeated release raising `PROVIDER_ADMISSION_NOT_ACTIVE` is **not by itself** proof of success and must be followed by exact canonical reread/reconciliation;
- WorkerLease release accepts only the canonical truth shapes `(released=True, already_released=False)` or `(False,True)` for the exact lease/session/task owner. Malformed/contradictory/foreign-owner outcomes are recovery and must not yield handoff, reacquire capacity, or invoke the model; a newer owner's lease must remain untouched;
- a reusable `DirectReviewExecutionHandoff` may be returned only after both provider-admission and WorkerLease cleanup are canonically proven terminal/released and the exact durable winner/resource association is reconstructable;
- handoff preserves the exact admission/lease identities and cleanup proof needed to audit/reconstruct the no-orphan claim;
- ambiguous release -> `RECOVERY_REQUIRED` / retain evidence; no blind reacquire;
- crash window after model effect but before release/checkpoint must reconcile from durable execution + durable winner/resource association + exact admission/lease state, not repeat model call;
- replay after such a crash first reconciles **all** equivalent fingerprint records, then exact winner/resource identities, then cleanup; it must not select newest row or infer ownership from an old in-memory lease snapshot;
- `REUSE_COMPLETED` forbids new model/launch/acquire effects but does not forbid necessary exact cleanup/reconcile effects;
- no resource release from reviewer semantic verdict; transport/resource truth is separate from ACCEPTED/REJECTED.

WO224's separate GoalCloseout lease-release finding is not authority to broaden this WO into GoalCloseout source. Reuse/fix only the reviewer-execution resource path released here.

## 11. Initial mutable scope after release

Final scope must be re-pinned after WO225/post-main. Preferred maximum starting scope:

- NEW `src/a_conductor/zero_relay_review_execution.py`
- NEW `tests/test_zero_relay_review_execution.py`
- `src/a_conductor/zcode_production_assembly.py` + focused tests **only if** READ_ONLY assembly cannot be expressed without a bounded extension
- `src/a_conductor/zcode_runner.py` + focused tests **only if** a public pure fingerprint/spec seam is required to avoid private-field/latest-row lookup
- WO226/result/checkpoint evidence

Read-only archaeology is allowed across execution/provider/lease/recovery modules.

Not initially authorized:

- scheduler/graph readiness semantics;
- `ParallelReadyExecutor` / AHA-6 behavior;
- provider store schema;
- Worker lease store schema;
- execution store schema;
- ReviewBus/ReviewBridge/mailbox mapping;
- `zero_relay.ReviewEvidence` / Phase-A decision semantics;
- GoalCloseout source;
- ZRA-3/ZRA-4 source;
- A-Wiki repository;
- live credentials/config DB/runtime processes.

If any of these become necessary, checkpoint exact evidence and STOP for GPT adjudication.

## 12. RED-first matrix

Write intended REDs before GREEN production mutation.

### Route/authority binding

1. valid repaired-C0 READ_ONLY task/route reaches execution preflight;
2. MUTATION lease cannot execute review;
3. non-empty mutable scope cannot execute review;
4. lease task/ref mismatch fails closed;
5. wrong worker/project/worktree/branch/HEAD fails closed;
6. non-ZCode harness strategy cannot enter direct ZCode reviewer execution;
7. provider/model/generation/endpoint mismatch fails closed;
8. route dispatch ID != admission execution ID fails closed;
9. task packet contract/hash/path mismatch fails closed;
10. author execution identity cannot be reused as reviewer runtime execution.

### Identity / replay

11. runtime `execution_id` is allowed to differ from route dispatch ID and is preserved distinctly;
11a. pure execution plan/fingerprint can be computed with **zero** lease/admission/process/secret-value/store-mutation effects;
11b. the real launch assembly consumes/recomputes the same plan and fails closed on any plan drift before spawn;
11c. same fingerprint with `DurableExecutionRecord.worker_id != DirectReviewRoute.reviewer_worker_id` is recovery/identity conflict, never reuse or launch;
11d. READ_ONLY ZCode protocol permission request remains deterministically denied (`approved=false`) and no permission-grant path is introduced; this test is not reported as universal write-sandbox proof;
11e. barrier-forced two concurrent same-fingerprint requests with identical owner/session facts produce **at most one durable model-effect winner**; a second dedup check, capacity=1, same lease reentry or EXISTING admission alone must not satisfy this RED;
11f. exact winner/fingerprint/lease/admission association is durable before model effect and can be reconstructed after a crash; absent canonical association => `DESIGN_GAP` before model call;
12. exact fingerprint returns/reconciles the exact canonical record set;
13. latest unrelated execution cannot be selected;
14. same completed fingerprint returns/reconstructs the same execution without a second model/launch/acquire effect;
15. existing running fingerprint attaches/waits; no duplicate spawn;
16. ambiguous duplicate state is recovery, not launch;
16a. older RUNNING + newer completed same-fingerprint records are detected in both insertion orders; the newer completed record cannot hide the live equivalent;
16b. multiple completed equivalents are not silently collapsed by newest-row ordering; canonical winner/reconcile proof is required;
17. old task/result/head/provider/model/runtime identity cannot replay into new route;
18. deterministic batch ID stable on exact replay and changes on identity change.

### Execution/artifact handoff

19. successful supervised run returns typed handoff with exact record/artifact refs;
20. durable record work_order_ref/job/project/worker/backend/repo/branch/head mismatch fails closed;
21. missing stdout/report/result refs fails closed as applicable to the active producer contract;
22. timeout/unknown process outcome never fabricates success;
23. failed/cancelled/recovery/verification-required states are classified explicitly; do not call them semantic ACCEPTED;
24. exact task packet/report response identity is retained for downstream C1;
25. logical C0 `review_result_ref` never causes arbitrary child filesystem write.

### Resource/recovery

26. provider admission is acquired/reused only under canonical authority and only after one durable launch winner is proven;
27. Worker lease is canonical READ_ONLY and exact-owner bound; same-owner lease reentry is not launch-winner proof;
28. lease/admission failure after earlier resource acquisition releases/reconciles safely;
29. ambiguous model execution keeps recovery truth and forbids blind retry;
30. terminal execution cleanup uses exact admission/lease identity and the durable winner/resource association;
31. provider release lost-ack replay requires exact admission reread: `NOT_ACTIVE` alone is insufficient, exact terminal `RELEASED` + identity binding is required;
31a. WorkerLease cleanup accepts only `(True,False)` / `(False,True)` for the exact owner; false/false, true/true, malformed or foreign-owner results are recovery;
31b. old lease cleanup after a new owner appears never releases/touches the new owner's lease;
32. restart after model completion but before cleanup reconciles all execution records + exact resource identities without second model/launch/acquire effect;
32a. no usable handoff exists until exact provider + lease cleanup is canonically terminal;
33. no secret value enters task/argv/log/result/checkpoint.

### Authority fence

34. no scheduler selection inside WO226;
35. no second provider/lease/execution store;
36. no ReviewEvidence/verdict parser;
37. no mailbox agent-id invention;
38. no A-Wiki internal import;
39. no production use of `ORDER BY rowid DESC LIMIT 1` / latest-run heuristics;
40. human relay count for the composed reviewer execution = 0.

## 13. Adversarial/fault campaign after GREEN

Attack at least:

- unrelated execution created immediately before/after reviewer execution;
- barrier-forced two same-fingerprint callers that both observe an empty store before either creates a durable record; assert <=1 model-effect winner and <=1 canonical winner identity;
- same-owner WorkerLease reentry + EXISTING ProviderAdmission under the race; prove they do not substitute for launch ownership;
- older RUNNING + newer completed equivalent records in both insertion orders; never let `matches[0]`/newest ordering hide the live record;
- multiple completed equivalent records without canonical winner proof;
- provider generation changes between preflight and admission;
- lease ownership changes before launch;
- branch/HEAD drift before launch;
- child timeout after provider request may already have happened;
- durable record write succeeds but caller crashes before handoff;
- model result exists but admission release crashes;
- lease release ambiguous;
- run-dir artifact missing/truncated/corrupt (transport classification only; semantic byte validation belongs downstream);
- stale C0 route replayed against changed repaired-C0 task;
- forged `DirectReviewRoute`-like duck object;
- forged canonical-looking ProviderAdmission/WorkerLease object with mismatched identity;
- secret-like output/log scanning.

Prefer deterministic barriers/fault doubles over sleeps.

## 14. Verification floor

At minimum after GREEN:

- focused WO226 tests;
- repaired C0/WO225 tests;
- ZRA-1 `zcode_production_assembly` tests;
- ZCode runner/supervised coordinator/dedup tests justified by imports;
- provider admission tests;
- Worker lease broker/store tests;
- recovery/transport tests when used;
- relevant real-helper synthetic tests (no real provider call by default);
- compile/import;
- diagnostics on changed source/tests;
- `git diff --check`;
- strict UTF-8/no U+FFFD;
- tracked + untracked scope audit;
- added-line secret-like scan;
- architecture/import fence;
- hosted CI on frozen exact SHA;
- independent exact-SHA R3 review by non-author lane;
- GPT exact-SHA adjudication before merge.

A real provider call is **not** automatically authorized by this WO. ZRA-1 already proves real callability; only perform a new live call if GPT separately records a bounded live-proof need and exact one-attempt authority.

## 15. Long-shift goal loop

```text
G0 RECOVER / RE-PIN / RELEASE GATE
G1 LIVE-ZRA1 + C0 + EXECUTION AUTHORITY ARCHAEOLOGY
G2 EXECUTION IDENTITY MODEL + PURE FINGERPRINT + MULTIPLICITY RED
G3 DURABLE SINGLE-WINNER + WINNER/RESOURCE ASSOCIATION PROOF (DESIGN_GAP STOP IF ABSENT)
G4 READ_ONLY ZCODE ASSEMBLY RED/GREEN (only if winner/association proof exists)
G5 REVIEW EXECUTION COORDINATOR RED/GREEN
G6 DUPLICATE/RESTART/RECOVERY + CLEANUP LOST-ACK CAMPAIGN
G7 RELATED REGRESSION + STATIC/HYGIENE
G8 SELF-REVIEW / AUTHORITY-FENCE AUDIT
G9 FREEZE EXACT SHA / DRAFT PR / HOSTED CI
G10 DURABLE HANDOFF / STOP AT EXTERNAL REVIEW GATE
```

After each meaningful mutation/campaign checkpoint record:

- current Gx;
- repo/worktree/branch/base/HEAD;
- changed files;
- exact RED/GREEN evidence;
- newly discovered trust gaps;
- unresolved P0/P1/P2/P3;
- exact next safe action.

Use the full useful work budget inside this lane. Context rollover is not authority loss: checkpoint, recover from durable state, continue only if the same WO remains READY.

## 16. Stop gates

STOP after the current atomic safe step on any:

- WO225 not accepted/merged/post-main verified;
- current source materially disproves this authority model;
- need to equate dispatch-context ID with durable runtime execution ID;
- need to use latest-row/latest-dir heuristic for identity;
- no existing authorized durable single-winner seam can be proven before model effect (`DESIGN_GAP`);
- no existing canonical durable winner->lease/admission association can be proven before model effect (`DESIGN_GAP`);
- resolving F1/F2 would require changing shared/global dedup semantics outside released scope;
- need to add provider/lease/execution-store schema or a second lock/outbox/journal;
- need to alter scheduler/AHA-6 semantics;
- need to claim universal reviewer write sandbox from permission-denial evidence alone;
- need to invent a mailbox agent id;
- need to parse semantic ACCEPTED/REJECTED (belongs WO223);
- need for live credential/provider/runtime mutation;
- overlapping owner/claim;
- unexplained dirty state;
- scope expansion outside released files;
- hosted CI nonterminal/failure after freeze;
- independent review / GPT acceptance gate;
- UNKNOWN authority.

Do not jump to WO223 C1, Phase D, ZRA-3 or ZRA-4 merely to stay busy.

## 17. Result contract

Write durable result/checkpoint under the implementation lane, e.g.:

`runs/WO-P1-226/result.md`

Record:

- actual base/release evidence;
- exact changed paths;
- accepted ZRA-1 reuse map;
- route/dispatch/job/runtime execution identity map;
- execution fingerprint + all-equivalent multiplicity rule;
- canonical durable winner authority and proof, or exact `DESIGN_GAP` evidence;
- durable winner->lease/admission association authority and proof, or exact `DESIGN_GAP` evidence;
- duplicate/replay outcomes including older-live/newer-completed adversarial cases;
- READ_ONLY assembly decision;
- provider/lease/recovery ownership + lost-ack cleanup map;
- RED/GREEN/adversarial evidence;
- test totals;
- P0/P1/P2/P3 counts;
- frozen candidate SHA/PR/CI;
- `merge_performed=false`;
- exact next safe action.

Final implementation state must be one of:

- `CANDIDATE_FROZEN_FOR_INDEPENDENT_REVIEW`
- `BLOCKED_PREDECESSOR`
- `DESIGN_GAP`
- `RECOVERY_REQUIRED`
- `NO_SAFE_NEXT_ACTION`

GLM source completion is a claim, not acceptance. GPT-5.6 Sol remains exact-SHA integrator/merge/release authority.
