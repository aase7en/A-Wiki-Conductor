# GLM/ZCode long-shift prompt — WO-P1-226 ZRA-2 reviewer execution bridge

/goal Execute exactly `docs/work-orders/WO-P1-226-zra2-reviewer-execution-bridge.md` only after its release gate is satisfied.

You are the bounded implementation/review lane for the missing ZRA-2 reviewer-execution node. GPT-5.6 Sol remains integrator, trust-boundary owner, exact-SHA acceptor, merge/release authority.

## G0 — recover before mutation

Read in order:

1. `00-AGENT-ENTRY.md`
2. `PROJECT-GRAPH.yaml` zero-relay route only
3. repo `AGENTS.md`
4. actual repo/worktree/remote/branch/HEAD/dirty/claim/overlap state
5. active Issue #214 checkpoints
6. `docs/work-orders/WO-P1-226-zra2-reviewer-execution-bridge.md`
7. WO225 exact repair/acceptance/post-main evidence
8. accepted ZRA-1 evidence on Issue #213 / WO179 LIVE-3
9. WO216/C0 current source and tests
10. WO223 packet only as downstream C1 contract, not mutation authority
11. independent Astra WO226 contract audit exact commit `f99cd9aadceb903649cdbf577935267a362540eb`; read the report by exact Git object because it is review-branch evidence, e.g. `git show f99cd9aadceb903649cdbf577935267a362540eb:docs/reviews/WO-P1-226-astra-contract-review.md`; Q1-Q4 are architecture questions, not extra defect claims
12. `DEFECT_LESSONS.md` before any `src/a_conductor/` mutation

Actual Git/GitHub/runtime/durable state overrides this prompt's stale snapshots.

WO225 is now independently accepted, merged and post-main verified at `main@7afb33d738086db50bc027c4c47165179a1cb96f`. Before mutation, re-verify that ancestry and require Issue #214 to explicitly publish `WO226_REVIEWER_EXECUTION_NEXT_READY` after the Astra packet amendment is frozen. If either fact is absent/drifted, write durable `BLOCKED_PREDECESSOR` and STOP.

## Critical trust model

Do NOT make these IDs equal:

```text
DirectReviewRoute.dispatch_execution_id   # dispatch/provider-admission context
DurableExecutionRecord.execution_id       # actual supervised runtime execution
```

Accepted LIVE-3 proved they are distinct. They must be cross-bound through exact task/packet/provider/model/project/worker/repo/branch/HEAD/runtime fingerprint + canonical admission/batch authority.

Never identify the runtime execution by newest row, newest run directory, timestamp proximity or PID. The sacrificial LIVE-3 proof's latest-row shortcut is forbidden in production.

Use existing deterministic execution fingerprint/dedup authority.

## Architecture constraints

Reuse existing accepted authorities:

- ZRA-1 supervised ZCode transport/assembly;
- execution store + fingerprint/dedup;
- provider configuration/admission;
- Worker lease broker/store;
- supervised process ownership/recovery;
- secret-reference resolution;
- repaired C0 `ParallelReadyTask` + `DirectReviewRoute`.

Do not add a second scheduler, GraphDispatch authority, provider store/semaphore, lease store, execution store, retry engine, ReviewBus, mailbox registry, process supervisor or secret resolver.

Preferred new bounded module:

`src/a_conductor/zero_relay_review_execution.py`

Preferred focused tests:

`tests/test_zero_relay_review_execution.py`

A minimal backward-compatible extension to `zcode_production_assembly.py` / `zcode_runner.py` is allowed only if the WO226 archaeology proves it is necessary for READ_ONLY execution or exact public fingerprint identity. Record the proof before editing.

GPT archaeology has already proven two concrete gaps you must re-verify on the then-current main before mutation:

1. current `assemble_zcode_execution()` requires an already-active MUTATION lease + non-empty mutable scope before returning a runner, so it cannot supply a true dedup fingerprint-before-effect path for a READ_ONLY reviewer;
2. `SupervisedZCodeRunner` exposes no public fingerprint/spec method, while `SupervisedRunCoordinator` owns the canonical `fingerprint_spec()` / `fingerprint_for_argv()` logic.

Independent Astra audit exact commit `f99cd9aadceb903649cdbf577935267a362540eb` additionally proved three binding facts:

3. current dedup/coordinator/store is observational, not an atomic single-winner launch fence: barrier-forced same-fingerprint callers can both see empty lookup and create two durable runtime IDs;
4. current duplicate assessment uses only `matches[0]`, so an older RUNNING equivalent can be hidden by a newer completed equivalent;
5. provider and WorkerLease cleanup have different replay contracts: provider lost-ack requires exact admission reread of terminal `RELEASED`; WorkerLease already-released uses `(False,True)` and exact owner fencing.

Prefer a shared **pure pre-effect execution-plan seam** that derives the exact `SupervisedRunIdentity`, operation ref, fixed argv, `ExecutionFingerprintSpec`, and fingerprint before lease/admission/process/secret-value effects; the launch assembly must consume or exactly revalidate that same plan before spawn. Do not duplicate the fingerprint formula.

After pure planning/dedup observation, prove ONE canonical durable launch winner through an EXISTING authorized authority before lease/admission/model effect. A second guard check, capacity=1, same-owner lease reentry or EXISTING provider admission is not winner proof. Also prove a durable winner->lease/admission association before model effect so restart can reconstruct cleanup ownership. If either authority does not already exist inside released scope, checkpoint `DESIGN_GAP` with exact call graph and STOP; do not invent a second lock/store/journal/schema.

Do not modify scheduler/AHA-6 semantics by default.

## G1 — archaeology/reuse map

Trace exact current source/call paths for:

- repaired `bind_direct_review_route` and its `ParallelReadyTask` invariants;
- accepted ZRA-1 `assemble_zcode_execution`;
- `SupervisedZCodeRunner` -> `SupervisedRunCoordinator`;
- `ExecutionFingerprintSpec`, `DuplicateExecutionGuard`, execution store lookup;
- provider snapshot/admission acquisition/validation/release;
- WorkerLeaseBroker acquisition and canonical release;
- execution recovery/owned-process semantics;
- accepted LIVE-3 proof composition, but distinguish sacrificial proof-only shortcuts from production APIs.

Write compact table:

`seam | path/symbol | authority | REUSE/WRAP/EXTEND/NOT_USED | gap | mutable?`

If a new authority would be required, checkpoint `DESIGN_GAP` and STOP.

## G2 — RED first: identity/fingerprint

Before GREEN production code, prove at least:

- dispatch-context ID may differ from runtime execution ID;
- exact execution plan/fingerprint is derivable before any lease/admission/process/secret-value/store-mutation side effect;
- launch assembly consumes/recomputes the same plan and rejects plan drift before spawn;
- runtime record is located by exact fingerprint, never latest row;
- unrelated latest execution cannot be selected;
- `ExecutionFingerprintSpec` does not bind worker identity, so every duplicate/post-run record must separately satisfy `record.worker_id == route.reviewer_worker_id == lease.worker_id`;
- same fingerprint from a foreign worker fails closed/recovery; it is neither reused nor bypassed with a second launch;
- task SHA/contract/HEAD/provider/model/runtime changes cannot replay old execution;
- completed exact fingerprint reuses/reconstructs execution state without second model/launch/acquire effect; cleanup/reconcile may still be required;
- running/unknown duplicate state never launches a second child;
- barrier-forced two same-fingerprint callers with identical owner/session facts produce <=1 canonical model-effect winner; count durable runtime IDs and model-effect port entries;
- older RUNNING + newer completed same-fingerprint records are detected in both insertion orders; never let `matches[0]`/newest ordering hide the live record;
- multiple completed equivalents require canonical winner/reconcile proof, not newest-row collapse;
- exact durable winner->WorkerLease/ProviderAdmission association exists before model effect and is reconstructable after restart.

Use deterministic store fixtures/barriers, not sleeps. If the single-winner or durable resource-association proof cannot be implemented using an existing authorized authority inside released scope, checkpoint `DESIGN_GAP` before any model call and STOP.

## G3 — durable winner/resource association, then READ_ONLY ZCode assembly

Before any launch-capable assembly work, prove the existing-authority single-winner + winner/resource-association requirements from G2. Do not use dedup recheck, provider capacity, same-owner lease reentry or EXISTING admission as a substitute. If the proof needs shared/global dedup mutation, a new lock/store/journal/schema, scheduler changes or another unapproved authority, checkpoint `DESIGN_GAP` and STOP before model/process effect.

Only after that proof exists: current accepted ZRA-1 assembly is mutation-capable. If reviewer execution cannot reuse it without weakening gates, make the smallest backward-compatible extension.

Reviewer mode must require:

- exact READ_ONLY canonical WorkerLease;
- empty mutable scope;
- empty requested mutable scope;
- exact task packet hash/path/contract;
- exact provider/model/generation/endpoint/secret-reference authority;
- accepted supervised lifecycle only;
- existing ZCode protocol fail-closed permission behavior remains intact: every observed `interaction/requestPermission` request is denied with `approved=false`, with no new permission-grant path.

Never weaken mutation-mode validation. Do not treat prompt text alone as a read-only enforcement boundary. Do not report the permission-denial regression as proof that every possible app-server write is universally mediated; identify the actual runtime/tool/OS write authority if a broader sandbox claim would be required, otherwise keep the claim narrow.

## G4 — reviewer execution coordinator RED/GREEN

Implement one bounded no-relay reviewer execution attempt over the repaired C0 route.

Required positive chain:

```text
validated C0 task+route
 -> pure plan/fingerprint preflight
 -> inspect/reconcile ALL equivalent fingerprint records
 -> one EXISTING-authority durable launch winner
 -> exact READ_ONLY lease/provider admission acquisition/reuse
 -> durable winner+lease+admission association BEFORE model effect
 -> accepted ZRA-1 supervised ZCode run
 -> reconcile exact durable execution record set by fingerprint (never matches[0]/latest)
 -> exact artifact refs / terminal classification
 -> exact provider + WorkerLease cleanup/recovery using their real API contracts
 -> immutable reviewer-execution handoff only after cleanup truth
```

The handoff must preserve both dispatch-context identity and actual durable runtime execution ID distinctly, plus the exact canonical provider-admission and WorkerLease identities used for the attempt.

Return a usable handoff only after provider-admission + WorkerLease cleanup/release truth is canonically proven terminal. If cleanup is ambiguous, return `RECOVERY_REQUIRED` and preserve evidence; do not fabricate a handoff and do not repeat the model call on replay.

Provider lost-ack cleanup rule: a repeated release may raise `PROVIDER_ADMISSION_NOT_ACTIVE`; that exception alone is not success. Re-read the exact admission by canonical identity and accept terminal `RELEASED` only after provider/dispatch/batch/generation binding still matches. WorkerLease cleanup accepts only canonical `(True,False)` or `(False,True)` for the exact lease/session/task; malformed/contradictory/foreign-owner results are recovery, and an old cleanup attempt must never release a newer owner's lease.

`REUSE_COMPLETED` means no new model/launch/acquire effect; exact cleanup/reconcile effects may still be necessary.

Do not parse reviewer semantic ACCEPTED/REJECTED here. WO223/C1 owns semantic evidence.

## G5/G6 — adversarial + recovery

Attack:

- unrelated latest execution row;
- barrier-forced duplicate/restart race where two same-fingerprint callers both observe empty lookup before either record exists; assert <=1 canonical model-effect winner;
- same-owner lease reentry + EXISTING admission during that race (must not authorize a second winner);
- older RUNNING + newer completed same-fingerprint records in both insertion orders;
- provider generation drift;
- lease ownership/HEAD/worktree drift;
- timeout after external model effect may already have happened;
- crash after resources are acquired/associated but before model effect;
- crash after durable execution result before handoff;
- provider release committed + acknowledgement lost -> repeat NOT_ACTIVE + exact RELEASED reread;
- WorkerLease already-released, contradictory/malformed result, foreign owner, and old-ID replay after new owner;
- crash/ambiguity during provider or lease release;
- stale C0 route replay;
- forged route/lease/admission objects;
- secret-like output/log leakage;
- test vacuity where a latest-row implementation would incorrectly pass.

No blind retry. UNKNOWN remains recovery-consuming.

## G7/G8 — regression/static/self-review

Run only justified related suites plus the WO226 verification floor. Confirm:

- repaired C0 remains green;
- accepted ZRA-1 mutation path remains behavior-compatible;
- no new scheduler/provider/lease/store authority;
- no semantic review parser added;
- no mailbox identity invented;
- no latest-row/latest-dir or `matches[0]`-only multiplicity heuristic;
- one durable launch-winner authority and durable winner/resource association are proven through existing authorized seams, or the result is `DESIGN_GAP` before model effect;
- no shared/global dedup semantics changed without explicit GPT scope release;
- permission-denial evidence is not overclaimed as universal write mediation;
- no live provider call unless GPT separately authorizes exactly one bounded attempt;
- changed scope exactly matches released files;
- UTF-8/diff/secret/import fences pass;
- unresolved P0/P1/P2 count is zero before candidate freeze.

## G9/G10 — freeze and handoff

Freeze one coherent exact SHA, push implementation branch, open/update Draft PR, trigger hosted CI, audit remote diff against released scope, then write:

`runs/WO-P1-226/result.md`

Record exact SHAs, tests, identity map, fingerprint + all-equivalent multiplicity rule, durable launch-winner authority, durable winner->lease/admission association proof (or exact `DESIGN_GAP`), replay/recovery evidence, provider-vs-WorkerLease cleanup evidence, findings, CI state and next safe action.

STOP at independent exact-SHA R3 review / GPT acceptance. Do not merge. Do not self-accept. Do not continue into WO223, Phase D, ZRA-3 or ZRA-4.

Use the full useful long-shift budget inside this one lane. If context rolls over, recover from durable WO/result/checkpoint evidence and continue only when the same lane remains READY.
