# WO-P1-226 — ZRA-2 reviewer execution bridge over accepted ZRA-1 transport

Status: PREPARED / HOLD_AFTER_WO225 / R3
Date: 2026-09-12 (Asia/Bangkok)
Repository: `aase7en/A-Wiki-Conductor`
Base at packet creation: `origin/main@60aba770fd457d04f1e31040b9dfd7af3927f669`
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

If any gate is absent or ambiguous: checkpoint and STOP. Do not treat this prepared packet as mutation authority.

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
  -> derive exact execution fingerprint BEFORE external provider effect
  -> DuplicateExecutionGuard
      REUSE_COMPLETED -> validate exact record -> return same handoff, no new provider call
      ATTACH_RUNNING  -> typed WAIT/RECONCILE, no duplicate provider call
      UNKNOWN/BLOCKED -> RECOVERY_REQUIRED, no duplicate provider call
      SAFE_TO_LAUNCH  -> continue
  -> existing canonical READ_ONLY Worker lease authority
  -> existing canonical ProviderAdmission authority bound to route dispatch id + deterministic batch
  -> accepted ZRA-1 supervised ZCode assembly/run
  -> locate exact durable execution by fingerprint (never latest-row)
  -> re-read exact DurableExecutionRecord
  -> prove task/provider/model/project/worker/repo/branch/HEAD/runtime bindings
  -> terminal/recovery classification
  -> retain exact artifact refs
  -> existing admission/lease release/recovery semantics
  -> immutable DirectReviewExecutionHandoff
```

Do not parse reviewer JSON/verdict in this WO.

## 6. READ_ONLY assembly rule

Current accepted `assemble_zcode_execution()` is the mutation-capable ZRA-1 composition and currently requires a canonical `WorkerLease` with `LeaseMutationIntent.MUTATION` + authorized non-empty mutation scope.

WO226 may make the smallest backward-compatible extension needed for reviewer execution, for example a dedicated READ_ONLY assembly entrypoint or a shared internal validator with explicit mode.

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

- exact completed identity -> `REUSE_COMPLETED`; return validated existing handoff; no new provider/lease side effect;
- equivalent live identity -> attach/reconcile; never spawn second child;
- unknown/ambiguous identity -> fail closed/recovery;
- changed task SHA/contract/HEAD/provider/model/runtime profile -> different fingerprint and never reuse old result;
- multiple records for one fingerprint must be resolved only by existing duplicate authority; do not select newest heuristically.

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

- terminal usable execution -> release according to existing accepted semantics;
- release result must prove released or already released as defined by the canonical authority;
- ambiguous release -> `RECOVERY_REQUIRED` / retain evidence; no blind reacquire;
- crash window after model effect but before release/checkpoint must reconcile from durable execution/admission/lease state, not repeat model call;
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
12. exact fingerprint returns the exact runtime record;
13. latest unrelated execution cannot be selected;
14. same completed fingerprint returns identical handoff without second model call;
15. existing running fingerprint attaches/waits; no duplicate spawn;
16. ambiguous duplicate state is recovery, not launch;
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

26. provider admission is acquired/reused only under canonical authority;
27. Worker lease is canonical READ_ONLY and exact-owner bound;
28. lease/admission failure after earlier resource acquisition releases/reconciles safely;
29. ambiguous model execution keeps recovery truth and forbids blind retry;
30. terminal execution release uses exact admission/lease identity;
31. ambiguous release returns recovery and does not reacquire;
32. restart after model completion but before release resolves durable record without second provider call;
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
- duplicate fingerprint records / store race;
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
G2 EXECUTION IDENTITY MODEL + PURE FINGERPRINT RED
G3 READ_ONLY ZCODE ASSEMBLY RED/GREEN (only if required)
G4 REVIEW EXECUTION COORDINATOR RED/GREEN
G5 DUPLICATE/RESTART/RECOVERY CAMPAIGN
G6 RESOURCE RELEASE/CRASH-WINDOW CAMPAIGN
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
- need to add provider/lease/execution-store schema;
- need to alter scheduler/AHA-6 semantics;
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
- execution fingerprint rule;
- duplicate/replay outcomes;
- READ_ONLY assembly decision;
- provider/lease/recovery ownership map;
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
