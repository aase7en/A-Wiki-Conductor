# WO-P1-467 — ZRA-3A Child-B Preparation-Ref Durable Provenance Design

Status: DESIGN_ONLY_CANDIDATE / AWAITING EXACT-SHA R3 DESIGN REVIEW
Revision: REPAIR-0001 (pre-freeze) — recovery determinism: one driving job owns at most ONE distinct `preparation_ref`; intentional rerun requires a NEW driving job.
Identity schema: GITHUB_ISSUE_V1
Issue: #467
Parent: #215
Accepted design authority: #452 / PR #454 (WO-P1-452)
Accepted Child A: #461 / PR #466 (WO-P1-461)
Exact base re-derived: `cb5f9b6b5188df68abb57fa9967b70a4004cca04` (current main, clean worktree, branch `docs/wo-p1-467-zra3a-childb-prep-ref-design`)
Topology: CONTROL_PLANE_ONLY
Risk: R3 DESIGN_ONLY — durable provenance seam resolution; zero source mutation in this WO.
Claim: WO-P1-467-CHILDB-PREP-REF-DESIGN-WINDOWS-002

## 0. Exact binding

Mutable scope is EXACTLY this file:
- `docs/work-orders/WO-P1-467-zra3a-childb-preparation-ref-provenance-design.md`

Everything else is READ-ONLY. No source, tests, runtime, store, schema, `CURRENT-WORK.md`, or `handoff.md` mutation. No commit/push/merge from this lane; integrator acceptance follows the WO452 §21 gate shape.

## 1. Problem being resolved

WO452 §10.1 leaves one DESIGN_GAP open for Child B:

> "The ref must be durable before the first prepare attempt. … Child B must obtain or checkpoint the ref through an already-accepted durable operation/task evidence seam before the first call. If no such caller-side durable seam is available at Child-B release time, stop at `DESIGN_GAP` rather than inventing a second idempotency store."

A volatile `preparation_ref` held only in process/chat memory is insufficient: a crash before observing the prepare response would lose the recovery key, and the no-blind-replay property of WO452 §10/§11 would degrade into duplicate-run risk. This WO resolves the gap against exact current main `cb5f9b6...` by classifying every candidate seam REUSE → WRAP → EXTEND → REJECT and choosing the smallest truthful design.

This revision (repair window 002) closes one review-found defect of the frozen candidate: the earlier text let several DISTINCT preparation refs accumulate on one driving job and read a new ref on the same job as an intentional rerun. After a crash between checkpoint commit and `prepare_run`, more than one distinct ref made "which intent is current?" undecidable without forbidden latest/sequence/time inference. The corrected design adds a one-distinct-ref invariant per driving job (§5), a count-based fail-closed recovery (§5.3), and moves intentional reruns onto distinct authoritative driving jobs (§5.2).

Hard constraints inherited from WO452 (all still verified at this base):

- GraphStore never infers the ref from time, latest rows, prose, branch names, filenames, or mutable process state (§10.1);
- the ref is not a `graph_run_id`, not a job/task/completion authority (§10.1);
- preparation and durable job creation remain separate authority transactions (§16);
- no second idempotency/replay ledger, scheduler, retry engine, or completion plane may be invented (§17, §23);
- Child B does not dispatch, does not select successors, does not rank/select providers/models (§18).

Repair invariants adopted by REPAIR-0001 (binding for the first Child-B path):

- one already-authoritative driving job owns at most ONE distinct `preparation_ref`; provenance reads are therefore deterministic — zero distinct refs ⇒ missing, one distinct ref ⇒ the ref, more than one ⇒ ambiguous — and every missing/ambiguous outcome fails closed with no latest-event/highest-sequence/newest-time selection;
- duplicate checkpoint rows carrying the same canonical ref are idempotent evidence for that same ref;
- an intentional graph rerun requires a NEW already-authoritative driving job, created by the existing lifecycle authority outside Child B, carrying a fresh opaque/domain-separated `preparation_ref`;
- Child B never creates jobs and never uses `job_id` itself as the ref;
- JobStore checkpoint evidence is provenance for the opaque ref only — never activation-binding storage (WO452 §17); the REUSE/WRAP classification of the checkpoint seam is unchanged and no new store/schema/task/job/idempotency/retry/completion authority is added.

## 2. Current-main authority map (exact base `cb5f9b6...`)

| Authority | Source refs | Durable semantics accepted today |
| --- | --- | --- |
| GraphStore v2 run authority (Child A, merged) | `src/a_conductor/graph/store.py:134-136` (unique partial index on `graph_runs.preparation_ref`), `store.py:1098` (`prepare_run`), `store.py:30,385-407` (`_PREPARATION_DOMAIN = b"graph-run-preparation-v1\0"`, `_preparation_sha256`) | Server-side idempotency + replay ONLY. The run row does not exist before the first prepare; it cannot be the caller-side pre-prepare seam. |
| JobStore job records | `src/a_conductor/job_store.py:129-162` (`job_records`, `job_events` DDL), `job_store.py:284-345` (`create_job`, `JOB_ALREADY_EXISTS`) | Durable job lifecycle identity: `job_id`, `work_order_ref`, `project_id`, state, attempt budget, version. |
| JobStore checkpoint events | `job_store.py:445-506` (`checkpoint()`: `BEGIN IMMEDIATE`, state-preserving `from_state == to_state`, version bump, one `CHECKPOINT` event row carrying `checkpoint_ref` + optional `evidence_ref`), `job_store.py:508-569` (`list_events` ordered read) | Append-only, ordered, crash-committed operation/task evidence attached to an existing non-terminal job. Existing in-band grammar precedent: `operation:{operation_ref}:complete` (`job_execution.py:266-269`). |
| Operator protocol checkpoint surface | `src/a_conductor/operator_protocol.py:81` (`OperatorRequest.checkpoint_ref`), `operator_protocol.py:151-153` (`JOB_CHECKPOINT` requires `job_id`, `expected_version`, `checkpoint_ref`) | The accepted protocol surface already exposes exactly this durable evidence write to operators — no protocol extension needed. |
| Job execution coordinator | `src/a_conductor/job_execution.py:219-226` (EXECUTING transition is the last durable gate before external execution), `job_execution.py:101-117` (`JobExecutionContext`: `job_id`, `work_order_ref`, `project_id`, `worker_id`, `attempt_no`, `max_attempts` — no `operation_ref`, no version) | Coordinator context carries durable job/work-order/project/attempt identity but no intent token and no expected version for backend-side writes. |
| Graph dispatch | `src/a_conductor/graph/dispatch.py:72-92` (`GraphDispatchKey{graph_id, graph_run_id, node_id}`; derived `job_id = "graph-dispatch-" + sha256(...)`), `dispatch.py:96-125` (`GraphDispatchRequest.operation_ref`), `dispatch.py:240-259` (`_dispatch_metadata_ref` hash checkpoint written at dispatch) | Dispatch identity is derived FROM an existing `graph_run_id`; dispatch metadata is written at/after dispatch. Downstream of prepare by construction. |
| Execution records | `src/a_conductor/execution_record.py:110-139,122` (`DurableExecutionRecord.operation_ref`), `src/a_conductor/execution_store.py:214` (`operation_ref TEXT NOT NULL`) | Execution identity rows are created at execution start, after job claim — downstream of prepare. `operation_ref` there is also a static registry key (`native_operations.py:105-123`, `claude_code_job_backend.py:113-127`), i.e. class-of-operation identity, not per-intent identity. |
| Task packets / contracts | `src/a_conductor/claude_code_harness.py:145-154` (`TaskPacketFile{task_contract_ref, path, sha256}`) | Content identity of a packet file only. |
| Zero-Relay provenance | `src/a_conductor/zero_relay_author_provenance.py:1-39` (`author-attempt-v1:<uuid4 hex>`, `zra2-repair-` family, generation 0/1 lineage) | Family-specific author/review attempt identity minted by `SupervisedRunCoordinator` at `SAFE_TO_LAUNCH`. |
| GoalCloseout | `src/a_conductor/goal_closeout.py:268-326` (`GoalCloseoutFacts/Finding/Plan`) | Goal-completion evidence plane; fires at closeout boundaries, not before run preparation. |
| Manual runtime activation (#433) | `src/a_conductor/runtime_activation.py:86+`, `desktop_app.py:110-113` | Activation plane only; owns no preparation identity. |

Fact check at this base: `prepare_run` has no production caller yet (store definition + tests only). Child B will be its first production caller, so the caller-side seam must be settled before Child B source is authorized.

## 3. Constraint challenges — verdicts against current main

Every "known constraint/fact" from the tasking was re-derived from source rather than trusted:

1. "`GraphDispatchRequest.operation_ref` is downstream/circular because `GraphDispatchKey` already requires `graph_run_id`." — **CONFIRMED.** `dispatch.py:72-75` requires `graph_run_id` in the key; the dispatch request cannot exist before prepare. WO452 §17 additionally rejects dispatch metadata as pre-dispatch queryable authority. Stands.
2. "`JobExecutionContext` has durable job/work-order/project/attempt identity but does not itself carry `operation_ref`." — **CONFIRMED** (`job_execution.py:101-117`). It also carries no store version, so a backend cannot checkpoint through it directly. It does not need to: the ref travels as explicit caller evidence plus a committed checkpoint row, not as coordinator context. Extending the coordinator/context just to ferry the token is rejected as unnecessary mutation of accepted authority (§4.3).
3. "`execution_store` persists `operation_ref` for execution identity, but no generic pre-prepare graph-run intent use is accepted yet." — **CONFIRMED.** Rows are execution-scoped and post-claim; no accepted pre-prepare use exists; generalizing it would create a new accepted semantic on an existing authority without its own decision. Rejected.
4. "Zero-Relay author/review task identities are family-specific and cannot be generalized by analogy." — **CONFIRMED** (`zero_relay_author_provenance.py:35-39` grammar/family constants; generation lineage is classification-gated). Rejected as a source for graph-run preparation identity.
5. "Task packet/contract refs provide content identity but not an intentional-run/retry identity." — **CONFIRMED.** Two intentional reruns over byte-identical packets must yield distinct runs; content digests cannot express that. Rejected.
6. "Chat/process/time/latest-row/branch/filename inference is forbidden." — **UPHELD** (WO452 §10.1/§17; GraphStore and Child B both refuse every inference path; RED-tested in §10).

## 4. Candidate table

Criteria: (A) exists durably before first `prepare_run`; (B) survives crash / lost prepare response; (C) distinguishes intentional rerun from same-intent retry; (D) no `graph_run_id` circularity; (E) accepted ownership, no new durable authority.

| # | Candidate | A | B | C | D | E | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | `job_id` itself as the ref | yes | yes | **no** — a lifecycle/authority identifier is not an opaque minted intent token; using it would let job identity act as GraphStore run authority | yes | yes | REJECT as ref source; the selected checkpoint seam is valid because the job scopes ONE preparation intent, not because job identity is reused as GraphStore authority |
| 2 | `job_id` + `attempt_no` composite | yes | yes | **no** — attempt increments on every recovery attempt, so a lost-response retry on attempt 2 would derive a *different* ref and mint a duplicate run — exactly the failure §10 exists to prevent | yes | yes | REJECT as derivation |
| 3 | JobStore checkpoint event row (`checkpoint_ref` on the driving job) | **yes** — committed via `checkpoint()` before prepare is invoked | **yes** — `BEGIN IMMEDIATE` commit; recoverable via `list_events` after any crash | **yes** — same ref ⇒ same-intent replay; one job carries at most ONE DISTINCT ref (§5 invariant), and intentional rerun happens on a new distinct driving job (§5.2), never as a second ref on the same job | **yes** — needs only the driving `job_id` | **yes** — JobStore owns `job_events`; accepted API + accepted `JOB_CHECKPOINT` protocol surface; no schema change | **SELECTED — REUSE** |
| 4 | Execution record `operation_ref` | no — rows exist only after job claim / execution start | yes | no — registry-key semantics (`native_operations.py:105-123`), shared across all intents of the same operation class | yes | yes | REJECT |
| 5 | `TaskPacketFile` / `task_contract_ref`+sha | yes (file/digest) | yes | **no** — content identity, blind to intent | yes | yes | REJECT |
| 6 | GraphDispatch metadata | no — written at/after dispatch | yes | no | **no** — key requires `graph_run_id` | yes | REJECT (also WO452 §17) |
| 7 | Zero-Relay `author-attempt-v1` | no — minted at `SAFE_TO_LAUNCH` for author/review workloads | yes | yes | yes | **no** — family-specific grammar/lineage (`zero_relay_author_provenance.py:35-39`); generalizing by analogy is forbidden | REJECT |
| 8 | GoalCloseout evidence | no — completion-boundary plane | yes | no | yes | yes | REJECT |
| 9 | New GraphStore pre-prepare ref registry / new store | yes | yes | yes | yes | **no** — a second idempotency store; explicitly forbidden by WO452 §10.1/§23 | REJECT |
| 10 | Inference (time, latest row, chat, branch, filename, process state) | n/a | no | no | yes | **no** — forbidden | REJECT |

## 5. Decision — smallest truthful design

**REUSE the JobStore job-event checkpoint seam as the durable caller-side provenance authority; Child B adds only a bounded verify-before-prepare READ. No schema, protocol, store, or coordinator changes.**

This is a REUSE, not an EXTEND: the exact semantics WO452 §10.1 demands — durable-before-use, crash-committed, append-only evidence, caller-invocable, already exposed at the accepted `JOB_CHECKPOINT` protocol surface — are already implemented and accepted at `job_store.py:445-506` / `operator_protocol.py:151-153`. Declaring `DESIGN_GAP` would be false, because a fitting accepted seam demonstrably exists at Child-B release time. Inventing storage is forbidden and unnecessary.

First Child-B path invariant: **one driving job may own at most ONE DISTINCT graph-run preparation intent/ref.** This invariant is what makes recovery deterministic without any new durable authority: recovery is a pure count over the job's canonical checkpoint refs with fail-closed dispatch (§5.3) — never a selection by latest row, highest sequence, newest timestamp, or arbitrary first.

### 5.1 Roles (ownership split)

- **Intent author (accepted caller):** mints the `preparation_ref`, durably checkpoints it on the driving job through the existing `JobStore.checkpoint()` API (directly or via `OperatorRequest.JOB_CHECKPOINT`) BEFORE any prepare attempt. The driving job is created through the existing accepted `JOB_CREATE` path by the integrator/caller — Child B never creates jobs (WO452 §17 rejection of pre-created activation jobs stands; that rejection targets jobs invented *during preparation* as hidden state, not the accepted intent-holder job of the initiating operation). Each preparation intent uses its own driving job: the author checkpoints exactly one distinct ref per job and never adds a second distinct ref to a job that already carries one.
- **Child B preparation seam (future source, after acceptance):** validates inputs, verifies durable provenance by READ-ONLY `get_job` + `list_events` exact-match, then invokes `GraphStore.prepare_run` exactly once per call. Child B writes nothing to the job store and never mints refs.
- **GraphStore (Child A, unchanged):** sole writer of runs/bindings; sole enforcer of preparation digest/replay rules.

### 5.2 preparation_ref derivation and validation

- Grammar: `graph-run-preparation-v1:<32 lowercase hex>` — exactly `^graph-run-preparation-v1:[0-9a-f]{32}$`, 57 chars, opaque, domain-separated by prefix (grammar precedent: `graph-run-v1:<uuid4hex>` run ids, `author-attempt-v1:<uuid4hex>`, `zra2-repair-v1:<64hex>`). Minted with `uuid4` by the intent author only.
- No project/task/intent data is embedded — the token stays opaque per WO452 §10.1. Binding is enforced relationally:
  - **project/task binding:** the driving job row carries `project_id` + `work_order_ref`; Child B requires `job.project_id ==` preparation `project_id` and `job.work_order_ref ==` the preparation request's `work_order_ref`;
  - **intent binding:** WO452 §10.2 preparation digest over `graph_id`, `project_id`, `graph_definition_sha256`, and the canonical binding set; same ref + changed intent fails `GRAPH_RUN_PREPARATION_IDENTITY_MISMATCH` (already implemented, `store.py:1178-1181`).
- Evidence form: one `CHECKPOINT` event with canonical `checkpoint_ref = "graph-run-preparation:" + preparation_ref` (80 chars, well inside job-store text bounds); `evidence_ref` optional and never authoritative.
- Replay identity: exact ref + matching digest returns the same server-minted `run_id` per WO452 §10.3 / `store.py:1161-1198`.
- `job_id` itself remains REJECTED as a `preparation_ref` (§4 row 1): the seam is authoritative because the driving job scopes exactly ONE preparation intent, not because job identity is reused as GraphStore authority.
- Intentional rerun: requires a DISTINCT, already-authoritative driving job, created beforehand by the existing accepted lifecycle authority (`JOB_CREATE`) outside Child B — never during preparation (WO452 §16/§17; Child B never creates jobs). The author mints a fresh opaque ref and checkpoints it on that NEW job; the new ref has no durable run yet, so prepare mints a new run id. The previous job, ref, and run stay durably inert — no GC, expiry, cancel, or lifecycle transition. A second distinct ref checkpointed on the ORIGINAL job is never an intentional rerun; it is an ambiguity state that fails closed (§5.3).

### 5.3 Child-B verification order (all fail closed, typed, before any GraphStore write)

1. preparation_ref grammar exact match;
2. driving job exists and is not terminal;
3. job/project/work-order binding equality (§5.2);
4. recovery from the driving job: `list_events(job_id)` is scanned for `CHECKPOINT` events whose `checkpoint_ref` matches the canonical evidence form, reduced to the set of DISTINCT canonical refs; dispatch on the count, every branch failing closed BEFORE any GraphStore write — zero distinct refs ⇒ typed provenance-missing failure; exactly one distinct ref ⇒ that ref is recovered as THE job's preparation ref (duplicate identical checkpoint events are idempotent) and the submitted ref must equal it exactly; more than one distinct ref ⇒ typed provenance-ambiguous failure. Selection by latest event, highest sequence, newest timestamp, or arbitrary first is never attempted;
5. only then call `GraphStore.prepare_run(graph_id, project_id, preparation_ref, bindings)`.

Multiple same-ref evidence rows are idempotent (the distinct-ref count stays 1). A ref checkpointed on a *different* job never satisfies step 4 — no cross-job ref laundering. Because reruns use new driving jobs, a well-formed second distinct ref on the same job is treated as corruption/ambiguity, never as a rerun: it fails closed before any GraphStore write. A v1 (unmigrated) GraphStore surfaces Child A's `GRAPH_RUN_BINDING_AUTHORITY_UNAVAILABLE` with no auto-upgrade.

## 6. Crash matrix

| # | Crash point | Durable state before retry | Retry outcome |
|---|---|---|---|
| 1 | Before provenance durability (checkpoint not committed) | No evidence row; no run. Contract ordering (checkpoint BEFORE prepare) plus Child-B verification makes out-of-order prepare impossible (typed provenance failure, zero store writes). | Author re-checkpoints the same ref, then prepare mints the run. No orphan. |
| 2 | After checkpoint commit, before prepare | Canonical ref(s) durable on the driving job; no run exists. | Recovery collects DISTINCT canonical refs from the job: exactly one ⇒ recover that exact ref (duplicate identical events idempotent); retry prepare mints the run. Zero distinct ⇒ typed provenance-missing failure; >1 distinct ⇒ row 7. |
| 3 | Prepare commit, response lost | Run + bindings + evidence all durable. | Retry same ref/digest: Child A exact-compares durable run + binding set and returns the SAME `run_id`. No second run. |
| 4 | Same-intent retry (e.g., job recovery, new attempt) | Evidence row reused — the ref is attempt-independent by design (opaque token, not derived from attempt number). | Replay path ⇒ same `run_id`. |
| 5 | Same ref, changed intent | Ref durable; digest differs. | `GRAPH_RUN_PREPARATION_IDENTITY_MISMATCH`; fail closed; no mutation. Deliberate re-run requires a new DISTINCT driving job with a new ref (row 6). |
| 6 | Intentional rerun | NEW distinct authoritative driving job (created by existing lifecycle authority outside Child B) + fresh opaque ref checkpointed on that new job. | New `run_id`; prior job/ref/run remain durably inert evidence. Never a second distinct ref on the original job. |
| 7 | Multi-distinct-ref corruption/ambiguity (>1 distinct canonical refs on one driving job) | All refs durable; current intent not derivable. | Typed provenance-ambiguous failure BEFORE any GraphStore write. No latest/highest-sequence/newest-timestamp/arbitrary-first selection; repair is an out-of-band governance decision on the durable evidence, not an inference. |
| 8 | Other ambiguous provenance reads | — | Zero canonical refs ⇒ typed provenance-missing failure. Job binding mismatch ⇒ typed failure. Exactly one distinct ref ⇒ deterministic single prepare/replay outcome. Cross-job ref ⇒ never accepted. |

## 7. Ownership proof — no second authority

- Writers: `JobStore` remains the ONLY writer of `job_events` (via its accepted API / `JOB_CHECKPOINT`). `GraphStore.prepare_run` remains the ONLY writer of `graph_runs`/`graph_run_bindings`. Child B writes nothing anywhere.
- Readers: Child B reads job rows/events through an injected read-only port (`get_job` + `list_events`); GraphStore reads only its own store.
- No second scheduler/retry/completion authority: `CHECKPOINT` events are state-preserving (`from_state == to_state`, `job_store.py:477-479`) and drive no transitions; recovery stays with existing job/execution recovery; completion stays with existing closeout boundaries; #215 retains automatic NEXT_READY/successor selection; #433 retains generic/manual runtime activation; GraphStore retains run/binding persistence; provider route selection remains external — Child B only validates the explicit pre-pinned provider/model/effort per WO452 §13.1. No new durable lifecycle authority exists in this design.
- The one-distinct-ref invariant is enforced only by Child B's fail-closed READ of existing evidence (§5.3); the job store continues to hold no ref-selection or activation-selection authority (WO452 §17 preserved).

## 8. Future Child-B source contract (AUTHORIZED ONLY AFTER this design's exact-SHA acceptance)

Minimal likely scope (shape only; no mutation granted by this WO):

- ONE new bounded module under `src/a_conductor/graph/` (e.g. a preparation application seam): project-id resolution via existing ControlCenter registry; preparation input validation; contract/packet digest validation; exact `runtime_kind == "serena"` + explicit pre-pinned `provider_id/model_id/effort_level` validation (WO452 §13.1 — validate only, never choose); provenance verification per §5.3 via an injected read-only job-store port; a single `prepare_run` invocation; typed binding-to-`RuntimeActivationRequest` reconstruction with fresh digest checks (WO452 §14).
- Focused tests for preparation/binding reconstruction + the §10 RED matrix.
- Possibly `src/a_conductor/graph/__init__.py` export only if required.

Explicitly out of Child-B scope: `job_store.py`, `job_execution.py`, `graph/dispatch.py`, `graph/store.py` (unless review proves a typed-error constant addition unavoidable — that is scope creep requiring fresh acceptance), operator protocol, scheduler/dispatch, NEXT_READY, runtime activation, provider selection, any DDL anywhere. If the first production integration surface (which creates the driving job and initiates run preparation) is needed before Child C, it is its own future WO under the same boundary rules.

## 9. What would have falsified this design

Recorded for the reviewer: this REUSE verdict would be wrong if any of the following held at re-derivation time — (a) `JobStore.checkpoint()` were not crash-committed or not append-only; (b) the checkpoint evidence were unreachable through an accepted surface without protocol extension; (c) `list_events` lost ordering or rows; (d) WO452 §17's job-store rejection were read as banning ALL job-bound provenance (it bans jobs *created during preparation* as hidden activation state — the driving intent-holder job is accepted lifecycle, created before preparation through `JOB_CREATE`); (e) a single driving job ever needed to legitimately hold multiple distinct preparation refs across its lifetime (it must not: rerun ⇒ new distinct driving job, and >1 distinct refs on one job ⇒ fail closed per §5.3). None hold at `cb5f9b6...`.

## 10. RED-first matrix for future implementation

1. prepare attempted with zero distinct canonical graph-run-preparation refs on the driving job ⇒ typed provenance-missing failure; zero `graph_runs`/`graph_run_bindings` writes;
2. ref grammar violations (wrong prefix, uppercase hex, wrong length, whitespace, non-opaque structured payload) ⇒ typed failure before any read;
3. evidence present but driving-job `project_id` mismatched ⇒ typed failure;
4. evidence present but `work_order_ref` mismatched ⇒ typed failure;
5. evidence present and valid ⇒ `prepare_run` invoked exactly once with the identical ref; run id returned;
6. replay windows: checkpoint-only → retry completes preparation; prepare-commit-only (evidence pre-exists) → retry returns the SAME run id; both committed → retry fully idempotent;
7. same ref, changed digest ⇒ `GRAPH_RUN_PREPARATION_IDENTITY_MISMATCH` surfaced, nothing mutated;
8. intentional rerun via a NEW distinct authoritative driving job (created by the existing lifecycle authority outside Child B) plus a fresh ref checkpointed on that new job ⇒ distinct run id; original job/ref/run untouched;
9. terminal driving job ⇒ verification fails closed;
10. ref checkpointed on a different job never satisfies verification;
11. Child B performs zero writes to `job_events`/`job_records` (write-count assertion);
12. every inference channel (clock, latest rows, branch, filename, env, process state) fails typed as provenance-required;
13. `JOB_CHECKPOINT` operator-path evidence is accepted by the verification port (integration shape);
14. multiple same-ref evidence rows ⇒ exactly one prepare/replay outcome;
15. WO452 §13.1 regression guard: missing explicit provider/model/effort still fails closed inside the same seam;
16. v1 GraphStore + valid provenance ⇒ typed authority-unavailable, no auto-upgrade;
17. concurrent identical preparations (two callers, same evidence+ref) converge on one run via the existing unique index + transaction;
18. a second DISTINCT canonical ref on the same driving job (each ref individually well-formed and binding-correct) ⇒ typed provenance-ambiguous failure before any `graph_runs`/`graph_run_bindings` write — never treated as an intentional rerun;
19. recovery ordering-independence: with multiple distinct refs present, the outcome is the identical typed ambiguous failure regardless of event order, sequence, or timestamp — the recovery function is a distinct-ref set-count with fail-closed dispatch and contains no latest/highest-sequence/newest-timestamp/arbitrary-first selection path;
20. duplicate identical checkpoint events (same ref, N rows) ⇒ distinct-ref count 1 ⇒ recovery returns that exact ref and exactly one prepare/replay outcome.

## 11. Preserved boundaries

- #215 owns automatic NEXT_READY/successor selection — untouched.
- Child A / GraphStore owns durable run/binding persistence — unchanged source.
- #433 owns generic/manual runtime activation — unchanged.
- Provider route selection stays separate; Child B only validates explicit pre-pinned provider/model/effort.
- No new durable lifecycle, idempotency, scheduler, retry, or completion authority is created.

## 12. Source-release gate

Before ANY Child-B tracked source mutation, all of the following in order:

1. this exact governance candidate committed/pushed on this design-only branch, changed scope exactly this WO;
2. `git diff --check` clean; strict UTF-8 read clean; `tests/test_work_order_identity.py` passes; exact `git status` shows only the allowed path;
3. exact-head hosted CI green;
4. independent exact-SHA R3 design review returns P0/P1/P2 = 0;
5. GPT-5.6 Sol explicitly accepts the design;
6. expected-head merge; post-main CI green; current main re-pinned;
7. Issue #215 ownership split re-confirmed; open PR/worktree/claim overlap rechecked;
8. `DEFECT_LESSONS.md` re-read before `src/a_conductor/` mutation;
9. Child B receives a new exact issue/claim/worktree/branch with the §8 frozen scope;
10. §10 RED tests land before production code.

Until every gate passes:

`SAFE_TO_MUTATE_ZRA3A_CHILDB_SOURCE = NO`

## 13. Current verdict

The WO452 §10.1 DESIGN_GAP is resolved by REUSE: the accepted, crash-committed JobStore checkpoint-event seam (already exposed at the accepted `JOB_CHECKPOINT` operator surface) durably holds the caller-minted opaque `preparation_ref` before the first `prepare_run`; Child B recovers and verifies it read-only and fails closed otherwise. Recovery is deterministic because one driving job owns at most ONE DISTINCT preparation ref: zero distinct refs ⇒ provenance missing; exactly one ⇒ recover that exact ref (duplicate identical events idempotent); more than one ⇒ provenance ambiguous, failing closed before any GraphStore write, with no latest/sequence/time/arbitrary-first selection. Intentional rerun is expressed only by a new distinct authoritative driving job created by existing lifecycle authority outside Child B — never by a second ref on the same job — and `job_id` itself remains rejected as a ref: the seam is valid because the job scopes ONE preparation intent, not because job identity is reused as GraphStore authority. No candidate required an EXTEND; no second store is invented; every rejected alternative and inference path is recorded.

`SAFE_TO_MUTATE_ZRA3A_CHILDB_SOURCE = NO`

Exact next safe action: freeze this one-file governance SHA, rerun deterministic identity/hygiene checks and exact-head CI, then obtain a fresh exact-SHA independent R3 design review only after global review occupancy is verified zero.
