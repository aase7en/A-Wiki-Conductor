# WO-P1-216 — ZRA-2 Phase C0 production review-task provenance + trusted route binding

Status: READY / SOURCE IMPLEMENTATION AUTHORIZED AFTER BOOTSTRAP GATE
Parent: WO-P1-165 / Issue #214 / ZRA-2
Predecessor design: WO-P1-210
Downstream: WO-P1-201 Phase C1 -> WO-P1-205 Phase D
Integrator: GPT-5.6 Sol
Implementation owner when invoked: ZCode GLM-5.3 MAX
Repository: A-Wiki-Conductor
Implementation branch: `feat/wo-p1-216-zra2-phase-c0-binding`
Implementation base: `8700d21887500965ffc33bcbffa1f33602d9c2f6`
Risk: R3 identity / review-route authority

## 1. Durable release evidence

Phase B is complete and post-main verified at merge commit
`8700d21887500965ffc33bcbffa1f33602d9c2f6`.

Issue #214 records:
- accepted repaired Phase-B exact source identity;
- fresh-main fold through PR #291;
- byte-for-byte equality of the six reviewed Phase-B paths;
- post-main verification 321 passed, 1 expected platform skip;
- Phase C0 may proceed only under a fresh claim/worktree/scope.

This worktree was created fresh from that merge commit.
At WO creation there was no open PR mutating the planned new files:
- `src/a_conductor/zero_relay_review_task.py`
- `tests/test_zero_relay_review_task.py`

Before source mutation the executor MUST re-pin all of this. Historical facts do not override newer actual state.

## 2. Objective

Implement the missing production provenance seam between one exact accepted author result and one trusted independent-review execution route.

The only accepted Phase-C0 flow is:

```text
zero_relay.ResultIdentity
  -> deterministic versioned review identity
  -> deterministic bounded review TaskPacketFile
  -> collision-safe persistence through accepted NativeFileSystem authority
  -> existing scheduler/provider/lease/harness route selection
  -> validated direct-review route binding
  -> later reviewer execution
  -> WO201 Phase C1 (NOT this WO)
```

Phase C0 does NOT create `zero_relay.ReviewEvidence`, classify a relay verdict, forward ReviewBridge results, merge, close jobs, release leases, or transition a job to COMPLETE.

## 3. Reuse-before-build decisions

Classification:
- review-task storage authority: REUSE `NativeFileSystem.create_text_if_absent`
- packet vocabulary: REUSE `TaskPacketFile`
- author identity: REUSE `ResultIdentity`
- scheduler/provider/lease/dispatch cross-binding: REUSE `ParallelReadyTask` where possible
- review mailbox publisher: DO NOT USE for the direct route unless an authoritative mailbox-agent mapping is separately proven
- ReviewBridge/result forwarding: DEFER to C1
- new scheduler/provider/lease/registry: FORBIDDEN

Fresh archaeology found `ParallelReadyTask` already cross-validates:
- selected assignment vs graph dispatch;
- selected worker vs sole lease candidate;
- project identity;
- worktree identity;
- branch identity;
- expected HEAD;
- provider identity;
- task packet contract vs harness dispatch;
- provider execution authority when present;
- lease TTL vs execution timeout.

Prefer consuming that validated aggregate rather than cloning its validation logic.
If its current semantics cannot express a read-only independent review route without changing established execution assembly, checkpoint `DESIGN_GAP` and STOP rather than broad-refactoring it.

## 4. Initial mutable scope

Authorized source/test scope for the first implementation attempt:

- NEW `src/a_conductor/zero_relay_review_task.py`
- NEW `tests/test_zero_relay_review_task.py`
- this WO file and the WO216 GLM prompt/checkpoint/result evidence

Read-only imports from existing modules are allowed.

Forbidden source mutation without a new integrator scope expansion:

- `src/a_conductor/zero_relay.py`
- `src/a_conductor/parallel_ready_execution.py`
- `src/a_conductor/agent_change_packets.py`
- `src/a_conductor/review_mailbox_adapter.py`
- scheduler/store/provider/lease modules
- `src/a_conductor/goal_closeout.py`
- A-Wiki repository
- global coordination files (`CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`) during normal implementation

If deterministic RED evidence proves a narrow extension outside this scope is necessary, persist the evidence, classify exact needed change, and STOP for GPT scope adjudication.

## 5. C0a target contract

### Inputs

One valid `zero_relay.ResultIdentity` and existing `NativeFileSystem` authority.

No caller-provided path, provider, model, reviewer prose, branch, HEAD, worker, or mailbox agent may influence C0a identity.

### Canonical identity

Use an explicit schema/domain separator, version 1.
Canonical bytes MUST include every `ResultIdentity` field exactly once with unambiguous encoding:

- `task_contract_ref`
- `task_sha256`
- `result_ref`
- `result_sha256`
- `attempt_id`
- `generation`
- `author_execution_id`

Prefer canonical JSON with fixed keys, sort order, separators, UTF-8, plus a fixed domain string; an equivalently deterministic versioned encoding is acceptable if proven by tests.

Derive a SHA-256 identity digest from canonical bytes.

### Deterministic names

Use only the digest plus fixed protocol literals for paths/refs. A recommended shape is:

```text
review_contract_ref = zra2-review-v1:<digest>
review_task_path     = runs/zra2-review-<digest>.md
review_result_ref    = runs/zra2-review-result-<digest>.json
```

Raw author/user strings may appear inside task content only; they must never become path segments.

### Review task bytes

The rendered task must bind the exact `ResultIdentity` and fixed protocol requirements for an independent reviewer, including at minimum:
- exact author task/result identity;
- attempt/generation;
- author execution identity;
- reviewer must be independent from author execution;
- review target must be the route-bound exact HEAD;
- bounded verdict vocabulary expected downstream;
- reviewer prose is evidence only, never merge/complete authority;
- external gates remain GPT/Conductor authority.

Do not put a fresh arbitrary caller prompt into identity-bearing bytes.

### Persistence

Reuse `NativeFileSystem.create_text_if_absent()`.
Required behavior:
- same deterministic path + exact same bytes -> reuse same logical packet;
- same deterministic path + divergent bytes -> typed collision;
- concurrent same bytes -> converge;
- concurrent divergent bytes -> preserve winner and typed collision;
- vanished/unverifiable raced state -> fail closed;
- mutation forbidden / missing fixed parent / unsupported filesystem primitive -> fail typed;
- returned SHA equals exact persisted UTF-8 bytes.

No raw `Path.write_text`, `os.replace`, ad-hoc temporary file publication, or second no-clobber implementation in the new module.

## 6. C0b target contract

### Preferred authority input

Consume a `ParallelReadyTask` whose `task_packet` is the exact C0a review packet.

The route must represent an independent review execution and MUST use `MutationIntent.READ_ONLY`.

C0b should add only review-specific cross-binding not already guaranteed by `ParallelReadyTask`.
Do not duplicate scheduler/lease/provider validation merely to make the new module self-contained.

### Required output

Create a small immutable typed route-binding value suitable for later WO201/C1 consumption. Exact class name is implementation-owned, but it must preserve at minimum:

- review task contract ref/path/SHA;
- deterministic review result destination ref;
- digest or other stable binding to the exact author `ResultIdentity`;
- selected reviewer worker identity;
- dispatch execution id (future durable reviewer execution must match this);
- provider id;
- model id;
- project id;
- worktree;
- branch;
- exact reviewed HEAD;
- fixed role/protocol meaning `independent-review`;
- enough information to prove the direct route was READ_ONLY.

Do not call this value `ReviewEvidence`; that authority belongs to Phase C1 after the reviewer result and durable execution record exist.

### Review-specific checks

At minimum prove:
- `route.task_packet` is the exact C0a packet;
- harness dispatch task contract equals packet contract;
- mutation intent is READ_ONLY;
- expected branch is present;
- expected HEAD is exact and carried forward;
- review result destination equals C0a deterministic result ref;
- author execution identity cannot equal the review dispatch execution id;
- no caller can override provider/model/worktree/branch/head/worker facts after `ParallelReadyTask` validation.

Current repository HEAD at materialization time is not a substitute for the route's exact reviewed HEAD. Do not silently consult ambient cwd Git as authority inside a pure binding function unless the contract explicitly requires a separately injected observation.

## 7. Mailbox boundary

Direct programmatic ZCode review is the initial authorized production path.

Do not publish an external mailbox assignment merely to create authority.
`AgentMailboxAssignment.agent_id` participates in external mailbox filesystem routing, and no accepted production worker->mailbox-agent identity mapping is currently proven.

If any code path needs external mailbox publication without such authority, fail/stop with:
`MAILBOX_AGENT_ID_AUTHORITY_MISSING`.

Never synthesize `agent_id` from worker_id, provider_id, model_id, plugin label, or human nickname.

## 8. Required RED-first test campaign

Write RED tests BEFORE production code.

### G1 — deterministic C0a identity
- exact positive ResultIdentity control;
- repeat exact input -> exact same canonical bytes/digest/ref/path/result-ref;
- each individual ResultIdentity field changed -> identity changes;
- field-order/internal dict-order cannot change canonical identity;
- Thai/emoji/Windows-style ref strings hash exact UTF-8 bytes;
- raw path-like input cannot affect deterministic path shape;
- malformed identities remain rejected by existing ResultIdentity validators.

### G2 — review task rendering
- exact persisted bytes contain every required authoritative field exactly/unambiguously;
- fixed protocol text stable across calls;
- no timestamps/random UUID/current cwd/current branch/environment values in bytes;
- task content cannot claim merge/complete authority;
- task content requires independent review and exact route-bound HEAD.

### G3 — no-clobber persistence
- missing target -> create;
- same existing bytes -> reuse;
- different existing bytes -> typed collision;
- deterministic barrier-driven same-input concurrency -> one physical artifact / all callers converge;
- deterministic divergent race -> conflicting bytes survive / loser fails typed;
- target vanishes after collision -> verification failure, no blind retry;
- mutation disabled;
- missing `runs` parent;
- directory target;
- size bound where applicable;
- unsupported link primitive -> fail closed;
- no sleep-based correctness test.

### G4 — C0b direct route binding
Construct valid existing authority fixtures for `ParallelReadyTask`, then test:
- exact positive READ_ONLY review route;
- task packet mismatch;
- dispatch task contract mismatch where construction path permits isolated falsification;
- PROJECT_MUTATION rejected;
- missing expected branch rejected;
- author execution id == review dispatch execution id rejected;
- deterministic result destination mismatch rejected;
- author `ResultIdentity` A cannot bind packet/route B;
- same provider/model/head but different author result SHA cannot replay;
- stale attempt/generation cannot replay;
- old packet cannot bind a route for a different candidate HEAD.

Do not mutate internal frozen objects merely to fabricate impossible states; where `ParallelReadyTask` already prevents a mismatch, assert that its constructor is the authority boundary and document the test as delegated protection rather than reproducing validation.

### G5 — authority/import fence
Prove the new module does not create/import a second:
- scheduler;
- provider store;
- lease store;
- retry engine;
- ReviewBus/ReviewBridge implementation;
- mailbox filesystem publisher for direct route;
- filesystem publication implementation;
- A-Wiki internal package.

## 9. Adversarial / falsification campaign after GREEN

Use remaining work budget to attack the design, not just rerun happy tests.

At minimum attempt:
- concurrent 8+ thread and, if cheap/portable, multi-process same identity publication;
- identity differential fuzz over every `ResultIdentity` field;
- Unicode normalization differences: prove bytes are treated exactly as contract states, do not normalize silently;
- path injection strings in refs/contract ids;
- same digest path forced to divergent bytes by injected race;
- stale route object vs different current repository HEAD: binding must remain exact to route authority, not ambient state;
- same worker/provider/model but different dispatch execution id;
- direct-route attempt to smuggle PROJECT_MUTATION;
- external-mailbox temptation: prove no `agent_id` guessing path was introduced;
- test-vacuity challenge: replace/no-clobber regression would fail the race test;
- circular import / architecture dependency check.

If a novel P0/P1/P2 appears, persist a deterministic reproducer and repair only if inside this WO scope. Otherwise checkpoint for GPT.

## 10. Long-shift execution loop

This WO is designed for long GLM execution without relying on one context window.

Use a durable loop:

```text
BOOTSTRAP
  -> RE-PIN
  -> READ ACTIVE POINTERS
  -> SELECT NEXT LOCAL GOAL
  -> RED
  -> GREEN
  -> SELF-REVIEW
  -> ADVERSARIAL FALSIFY
  -> REGRESSION
  -> STATIC/HYGIENE
  -> CHECKPOINT
  -> RE-PIN
  -> NEXT LOCAL GOAL if still READY
```

Maintain compact durable state under existing WO/runs conventions. At minimum preserve:
- current goal id G0..G7;
- current branch/HEAD/base;
- changed files;
- RED evidence;
- GREEN evidence;
- novel findings;
- unresolved decisions;
- exact next safe action.

After context compression or later invocation, read the checkpoint first. Never restart completed campaigns from chat memory.

Suggested nested goals:
- G0 bootstrap/release/claim gate
- G1 fresh architecture + call-site proof
- G2 C0a RED/GREEN
- G3 C0a race/adversarial proof
- G4 C0b RED/GREEN using `ParallelReadyTask`
- G5 anti-replay + authority-fence campaign
- G6 relevant regression/static/hygiene
- G7 freeze candidate + durable handback

## 11. Verification floor

Required after GREEN:
1. `tests/test_zero_relay_review_task.py`
2. `tests/test_native_execution.py`
3. `tests/test_zero_relay_repair_materializer.py`
4. `tests/test_zero_relay.py`
5. `tests/test_claude_code_harness.py`
6. `tests/test_parallel_ready_execution.py`
7. `tests/test_agent_change_packets.py`
8. `tests/test_review_mailbox_adapter.py`
9. provider/scheduler/lease tests only when actual imported production types justify them
10. `python -m compileall -q` on changed source
11. file diagnostics for changed source/tests
12. `git diff --check`
13. strict UTF-8 / no U+FFFD
14. changed tracked/untracked scope audit
15. added-line secret-like scan
16. hosted CI on frozen candidate
17. independent exact-SHA R3 review by a non-author

A platform-specific expected skip is allowed only when existing suite semantics already classify it that way and the reason is recorded.

## 12. Commit / PR authority

GLM may:
- mutate only released WO216 paths;
- commit coherent implementation/evidence batches;
- push this WO216 branch;
- create/update a Draft PR for WO216;
- post bounded durable checkpoints to Issue #214 if local tooling/auth permits and content contains no secrets.

GLM may NOT:
- merge any PR;
- mark its own implementation accepted;
- mutate A-Wiki;
- release C1 or Phase D;
- deploy/restart Workers/providers;
- change credentials/secrets;
- bypass CI or independent review.

## 13. External stop gates

STOP immediately after the current atomic safe step when any occurs:
- base/main/source drift changes the architecture materially;
- overlapping owner/claim appears;
- dirty state is unexplained;
- required scope expansion outside WO216;
- missing authoritative route field;
- need for worker->mailbox-agent mapping;
- need to change `ParallelReadyTask`/scheduler/provider/lease semantics;
- live credential/provider/runtime action would be required;
- hosted CI is non-terminal or failing after candidate freeze;
- candidate reaches GPT/integrator acceptance gate;
- merge/post-main verification is needed;
- UNKNOWN authority/state.

Do not poll/wait at an external gate. Do not jump to C1, Phase D, ZRA-3, launcher backlog, or unrelated work to stay busy.

## 14. Acceptance boundary

WO216 candidate is ready for independent review only when all are true:
- deterministic review packet binds exact `ResultIdentity`;
- packet persistence is no-clobber/idempotent through existing NativeFileSystem;
- direct review route binding reuses validated existing execution authority;
- route is READ_ONLY and independent from author execution;
- no mailbox-agent identity is invented;
- anti-replay matrix passes;
- no duplicate authority/system is introduced;
- relevant regression/static/hygiene is green;
- candidate is committed/pushed and worktree is clean;
- Draft PR exact head is recorded;
- hosted CI has been triggered.

Then STOP at `BLOCKED_EXTERNAL_CI_OR_GPT_ACCEPTANCE` and hand back exact SHA/PR/evidence/remaining advisories.


## GLM implementation claim — WO216 C0 (2026-09-12, under WO214 MASTER v4 Q2)

- Claim: ZCode GLM-5.3 MAX implements WO-P1-216 C0 per the Issue #214 release (`PHASE_C0_NEXT_READY`, release commit `8a5603c7f3c757f32b02382547f9d95a1603188b`).
- Release gate verified fresh this session: PR #291 MERGED into main `8700d21887500965ffc33bcbffa1f33602d9c2f6`; independent post-main byte check: **7/7 tracked fold paths exact** (six reviewed Phase-B paths + WO213 fold doc); Issue #214 records post-main 321 passed + Phase-B ACCEPTED + explicit C0 release naming this exact worktree/branch/scope.
- Worktree re-pinned: `feat/wo-p1-216-zra2-phase-c0-binding` @ `8a5603c` (base = accepted merge `8700d21`), clean; no open PR touches the two planned NEW files; no overlapping mutable lane.
- Mutable scope (exact): NEW `src/a_conductor/zero_relay_review_task.py`, NEW `tests/test_zero_relay_review_task.py`, this WO + runs/ evidence. All other modules read-only.
- SAFE_TO_MUTATE_PHASE_C0=YES.

## Phase C0 evidence (GLM implementation lane, 2026-09-12)

- Lane: worktree `A-Wiki-Conductor-wo216-zra2-phase-c0` @ `feat/wo-p1-216-zra2-phase-c0-binding`, base release `8a5603c7` (on accepted Phase-B `8700d218`); claim posted Issue #214 (comment 5642660674) after full re-pin (clean/synced/vacant lane, no overlapping PR).
- RED first: full G1-G5 matrix written before module; captured collection failure (`ModuleNotFoundError: a_conductor.zero_relay_review_task`).
- GREEN: focused tests **34 passed / 0 failed**; verification-floor related suites (native_execution, zero_relay_repair_materializer, zero_relay, claude_code_harness, parallel_ready_execution, agent_change_packets, review_mailbox_adapter) **302 passed / 1 expected POSIX FIFO skip**.
- C0a: canonical versioned JSON bytes (schema `zra2-review-v1`, fixed keys, sort_keys, exact UTF-8 incl. Thai/emoji) -> SHA-256 digest -> deterministic refs (`zra2-review-v1:<digest>`, `runs/zra2-review-<digest>.md`, `runs/zra2-review-result-<digest>.json`); deterministic renderer binding every ResultIdentity field + fixed reviewer protocol; persistence ONLY via `NativeFileSystem.create_text_if_absent` with same-bytes reuse, typed `REVIEW_TASK_COLLISION` on divergence, `REVIEW_TASK_STATE_UNVERIFIABLE` on vanished race, native codes passed through typed; no second publication implementation (G3 source fence).
- C0b: `bind_direct_review_route(ParallelReadyTask, MaterializedReviewTask, author)` validates packet identity (contract+sha+path-suffix), dispatch contract equality, READ_ONLY intent, branch presence, deterministic destination equality, author!=reviewer execution, author-refs<->materialized binding; returns frozen `DirectReviewRoute` (role `independent-review`, worker/dispatch/provider/model/project/worktree/branch/exact-HEAD facts, author digest binding). Delegated protections documented: `ParallelReadyTask.__post_init__` proved itself the authority boundary during test construction (derived `graph-dispatch-*` execution identity, job/work-order cross-fences).
- Checks: compileall OK; `git diff --check` OK; strict UTF-8/no-U+FFFD OK; changed tracked scope = exactly the 2 authorized NEW paths + this doc; credential-shape scan 0 hits.
- Module SHA256 `02723aadf68b6962...`; tests SHA256 `41ea7e3774e36df9...`.
- STATUS=PHASE_C0_FROZEN / INDEPENDENT_REVIEW_REQUIRED - GLM authored this candidate and is NOT its independent reviewer. No C1/Phase-D/merge self-authorization.
