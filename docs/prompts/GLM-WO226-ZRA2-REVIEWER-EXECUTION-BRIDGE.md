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
11. `DEFECT_LESSONS.md` before any `src/a_conductor/` mutation

Actual Git/GitHub/runtime/durable state overrides this prompt's stale snapshots.

If WO225 is not independently accepted + merged + post-main verified and Issue #214 does not explicitly release WO226, write a durable `BLOCKED_PREDECESSOR` checkpoint and STOP. Do not mutate source.

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

Prefer a shared **pure pre-effect execution-plan seam** that derives the exact `SupervisedRunIdentity`, operation ref, fixed argv, `ExecutionFingerprintSpec`, and fingerprint before lease/admission/process/secret-value effects; the launch assembly must consume or exactly revalidate that same plan before spawn. Do not duplicate the fingerprint formula.

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
- completed exact fingerprint reuses exact record without second model call;
- running/unknown duplicate state never launches a second child.

Use deterministic store fixtures/barriers, not sleeps.

## G3 — READ_ONLY ZCode assembly only if required

Current accepted ZRA-1 assembly is mutation-capable. If reviewer execution cannot reuse it without weakening gates, make the smallest backward-compatible extension.

Reviewer mode must require:

- exact READ_ONLY canonical WorkerLease;
- empty mutable scope;
- empty requested mutable scope;
- exact task packet hash/path/contract;
- exact provider/model/generation/endpoint/secret-reference authority;
- accepted supervised lifecycle only;
- existing ZCode protocol fail-closed permission behavior remains intact: every `interaction/requestPermission` request is denied with `approved=false`, with no new permission-grant path.

Never weaken mutation-mode validation. Do not treat prompt text alone as a read-only enforcement boundary.

## G4 — reviewer execution coordinator RED/GREEN

Implement one bounded no-relay reviewer execution attempt over the repaired C0 route.

Required positive chain:

```text
validated C0 task+route
 -> duplicate/fingerprint preflight
 -> canonical READ_ONLY lease/provider admission authorities
 -> accepted ZRA-1 supervised ZCode run
 -> exact durable execution record by fingerprint
 -> exact artifact refs / terminal classification
 -> canonical resource release/recovery
 -> immutable reviewer-execution handoff
```

The handoff must preserve both dispatch-context identity and actual durable runtime execution ID distinctly, plus the exact canonical provider-admission and WorkerLease identities used for the attempt.

Return a usable handoff only after provider-admission + WorkerLease cleanup/release truth is canonically proven terminal. If cleanup is ambiguous, return `RECOVERY_REQUIRED` and preserve evidence; do not fabricate a handoff and do not repeat the model call on replay.

Do not parse reviewer semantic ACCEPTED/REJECTED here. WO223/C1 owns semantic evidence.

## G5/G6 — adversarial + recovery

Attack:

- unrelated latest execution row;
- duplicate/restart race;
- provider generation drift;
- lease ownership/HEAD/worktree drift;
- timeout after external model effect may already have happened;
- crash after durable execution result before handoff;
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
- no latest-row/latest-dir heuristic;
- no live provider call unless GPT separately authorizes exactly one bounded attempt;
- changed scope exactly matches released files;
- UTF-8/diff/secret/import fences pass;
- unresolved P0/P1/P2 count is zero before candidate freeze.

## G9/G10 — freeze and handoff

Freeze one coherent exact SHA, push implementation branch, open/update Draft PR, trigger hosted CI, audit remote diff against released scope, then write:

`runs/WO-P1-226/result.md`

Record exact SHAs, tests, identity map, fingerprint rule, replay/recovery evidence, resource-release evidence, findings, CI state and next safe action.

STOP at independent exact-SHA R3 review / GPT acceptance. Do not merge. Do not self-accept. Do not continue into WO223, Phase D, ZRA-3 or ZRA-4.

Use the full useful long-shift budget inside this one lane. If context rolls over, recover from durable WO/result/checkpoint evidence and continue only when the same lane remains READY.
