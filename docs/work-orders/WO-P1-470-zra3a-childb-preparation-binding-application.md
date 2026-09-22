# WO-P1-470 — ZRA-3A Child-B Preparation + Binding Application Seam

Status: ACTIVE / GOVERNANCE_BOOTSTRAP
Identity schema: GITHUB_ISSUE_V1
Issue: #470
Parent: #215
Accepted design authority: #452 / PR #454 and #467 / PR #469
Accepted Child A: #461 / PR #466
Exact source base: `7173619c9ad7f7b141a197e0b7a334005a5925f7`
Topology: CONTROL_PLANE_ONLY
Risk: R3
Claim: WO-P1-470-ZRA3A-CHILDB-PREPARATION-APP-WINDOWS-001
Owner: GPT-5.6 Sol integrator; bounded implementation may be delegated to GLM-5.3 MAX.

## 0. Exact lane binding

Repository: `A:\GitHub\A-Wiki-Conductor`

Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo470-childb-preparation-app`

Branch: `feat/wo-p1-470-zra3a-childb-preparation-application`

Base: `7173619c9ad7f7b141a197e0b7a334005a5925f7`

Mutable scope is EXACTLY:

- `docs/work-orders/WO-P1-470-zra3a-childb-preparation-binding-application.md`
- `src/a_conductor/graph/preparation_application.py`
- `tests/test_graph_preparation_application.py`

Everything else is READ-ONLY unless a fresh scope decision is recorded before mutation.

Explicitly forbidden without fresh acceptance:

- `src/a_conductor/job_store.py`
- `src/a_conductor/job_execution.py`
- `src/a_conductor/graph/dispatch.py`
- `src/a_conductor/graph/store.py`
- `src/a_conductor/graph/__init__.py`
- `src/a_conductor/runtime_activation.py`
- operator protocol
- scheduler / dispatch / NEXT_READY
- provider selection, ranking or fallback
- schema / DDL
- any SunDayRemoteMCP mutation

## 1. Goal

Implement the first bounded Child-B application seam accepted by WO452 and WO467.

The seam validates one already-authoritative graph-run preparation intent, proves its durable pre-prepare provenance from existing JobStore checkpoint evidence, invokes the already-accepted GraphStore v2 preparation primitive exactly once per call after all fail-closed checks, and reconstructs typed runtime-activation requests from trusted persisted/current authorities.

This WO does not create lifecycle, scheduler, retry, idempotency, completion, provider-selection, runtime-selection or NEXT_READY authority.

## 2. Preserved authority split

- Issue #215 exclusively owns automatic accepted-completion -> NEXT_READY continuation/provenance.
- JobStore owns job lifecycle and existing checkpoint-event evidence. Child B is READ-ONLY toward JobStore.
- GraphStore owns graph-run/binding persistence and replay through `prepare_run`.
- Issue #433 / accepted runtime-activation service owns generic/manual runtime activation.
- Provider/model/effort selection remains external. Child B validates one explicit pre-pinned route and never ranks, chooses or falls back.
- The intent author, outside Child B, creates the driving job and mints/checkpoints the preparation ref before the first prepare attempt.

## 3. preparation_ref provenance contract

Canonical opaque ref grammar:

`^graph-run-preparation-v1:[0-9a-f]{32}$`

Canonical JobStore checkpoint evidence:

`graph-run-preparation:` + `preparation_ref`

One already-authoritative driving job owns at most ONE DISTINCT canonical preparation ref.

Recovery is set/count based only:

- zero distinct canonical refs -> typed provenance-missing failure;
- exactly one -> that exact ref is the only acceptable submitted ref;
- duplicate rows of that same ref -> idempotent evidence;
- more than one distinct canonical ref -> typed provenance-ambiguous failure before any GraphStore write.

Never select by latest row, event sequence, timestamp, arbitrary first element, branch, filename, environment, process state or chat context.

Intentional rerun requires a NEW already-authoritative driving job plus a fresh ref. A second distinct ref on the same job is corruption/ambiguity, not a rerun.

## 4. Fail-closed verification order

Before `GraphStore.prepare_run`:

1. validate submitted ref grammar;
2. load the driving job and require non-terminal state;
3. require exact project-id and work-order binding;
4. read JobStore events and derive the DISTINCT canonical preparation-ref set;
5. require set size exactly one and exact equality with submitted ref;
6. validate project registration/root authority;
7. validate graph/preparation inputs and current task-contract/packet refs + SHA-256 digests;
8. require exact `runtime_kind == "serena"`;
9. require explicit non-empty `provider_id`, `model_id`, and `effort_level`;
10. validate the explicit route against current accepted provider authority without choosing a route;
11. reject non-empty node `worker_requirement` under the current #433 capability boundary;
12. invoke GraphStore `prepare_run` once;
13. read/reconstruct every `RuntimeActivationRequest` field explicitly from trusted binding/current authorities with fresh digest checks.

No JobStore write, job creation, provider selection, activation, dispatch, successor selection or NEXT_READY action is permitted in this seam.

## 5. Failure model

Typed failure classes may live in the new bounded module. Existing GraphStore/runtime typed failures are propagated where they already own the boundary.

At minimum distinguish:

- invalid preparation-ref grammar;
- provenance missing;
- provenance ambiguous;
- provenance identity mismatch;
- driving job missing / terminal / project mismatch / work-order mismatch;
- project authority unavailable or root mismatch;
- contract/packet reference or digest invalid/stale;
- runtime-kind authority unavailable;
- runtime capability authority unavailable;
- explicit provider/model/effort missing or unauthorized;
- GraphStore binding authority unavailable / preparation identity mismatch / recovery required;
- activation-request reconstruction stale or invalid.

A failure before prepare must cause zero GraphStore writes. No internal retry loop is added.

## 6. RED-first matrix

Production module creation is blocked until focused tests are first observed RED against the exact claimed branch.

Minimum RED cases:

1. zero canonical preparation refs -> provenance missing; no prepare call;
2. duplicate same-ref checkpoint rows -> accepted as one identity;
3. two distinct refs -> provenance ambiguous; no prepare call;
4. submitted ref differs from sole durable ref -> identity mismatch;
5. project binding mismatch -> fail closed;
6. work-order binding mismatch -> fail closed;
7. terminal driving job -> fail closed;
8. malformed/noncanonical checkpoint evidence cannot establish provenance;
9. ref checkpointed only on another job cannot establish provenance;
10. valid provenance invokes prepare exactly once with identical ref;
11. replay same ref + same intent returns same run id through GraphStore;
12. same ref + changed preparation surfaces GraphStore identity mismatch;
13. intentional rerun uses a distinct pre-existing driving job + new ref;
14. v1/binding-authority-unavailable GraphStore fails typed with no auto-upgrade;
15. missing provider/model/effort fails closed;
16. runtime kind other than exact `serena` fails closed;
17. non-empty `worker_requirement` fails current capability gate;
18. missing/stale contract bytes or digest fails closed;
19. missing/stale packet bytes or digest fails closed;
20. inference from latest/time/sequence/branch/env/process state is impossible;
21. Child B performs zero JobStore writes/job creation/provider selection/NEXT_READY/runtime mutation.

Tests must include spies/fakes proving call counts and mutation absence.

## 7. Implementation constraints

- Prefer one small injectable service/application object in `preparation_application.py`.
- Depend on narrow structural/protocol-style ports when practical; do not widen accepted stores.
- Reuse existing JobStore records/events, GraphStore v2 request/records, ControlCenter/project registry and runtime-activation request types.
- Do not copy authority logic into a second store/facade.
- Do not expose dataclass/CLI defaults as authority; all activation-request fields are populated explicitly.
- Do not add automatic activation to Child B unless a separately accepted boundary explicitly requires it.
- No package/dependency addition.

## 8. Execution / acceptance gates

1. This WO governance bootstrap is the first and only commit before source/test mutation.
2. Re-pin exact branch/HEAD/dirty state after the bootstrap commit/push.
3. Re-read `DEFECT_LESSONS.md` before source mutation (already done for this claim; re-pin remains required).
4. Write focused tests before the production module exists.
5. Run the focused tests and preserve observed RED evidence.
6. Only then implement the production module.
7. Focused GREEN + directly related GraphStore/JobStore/runtime/provider/identity tests must pass.
8. `py_compile`, strict UTF-8/no-BOM, `git diff --check`, work-order identity, scope audit and secret audit must pass.
9. Freeze one exact candidate SHA and stop source mutation.
10. Run exact-head hosted CI and one independent GLM-5.3 MAX R3 review in parallel.
11. P0/P1/P2 must be zero; batch any confirmed repairs and focused-rereview the new exact SHA.
12. GPT-5.6 Sol accepts only deterministic exact-SHA evidence.
13. Expected-head merge only; then post-main deterministic + hosted CI verification.
14. Fold closeout to #470/#215 and release the claim.

## 9. Replay / takeover safety

Before redispatch after timeout/session loss, recover process + durable runner pointer + result/exit + Git status/HEAD.

Never infer failure from chat loss or timeout.

- no production module + RED test changes present -> inspect and continue the same claim, do not recreate;
- candidate committed/pushed -> freeze and harvest/review, do not redispatch author;
- dirty/unknown/out-of-scope state -> fail closed and reconcile ownership before mutation.

## 10. Current bootstrap verdict

This document creates no product/runtime behavior.

After this one-file commit/push and a clean exact re-pin, the claim may advance to RED-FIRST source implementation within the two remaining owned paths only.

Until that re-pin:

`SAFE_TO_MUTATE_WO470_SOURCE = NO`
