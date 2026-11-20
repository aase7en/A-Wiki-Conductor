# WO-P1-210 — ZRA-2 Phase C0 deterministic review-task + route-binding gate

Status: PREPARED / HOLD UNTIL PHASE-B POST-MAIN ACCEPTED
Parent: WO-P1-165 / Issue #214 / ZRA-2 Phase C
Related: WO-P1-201 Phase-C trusted review-evidence composition
Owner: GPT-5.6 Sol integrator / architecture
Preferred future executor: ZCode GLM-5.3 after explicit release
Base at packet creation: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Branch: `docs/wo-p1-210-zra2-phase-c0-assignment-gate`
Risk: R3 — review task/result identity and route authority

## 1. Why Phase C must be split

WO-P1-201 correctly defines the final trusted `zero_relay.ReviewEvidence` composition seam, but fresh production-call-site archaeology proves an earlier authority seam is missing.

At this base:

- `AgentMailboxAssignment` exists;
- `publish_agent_mailbox_assignment()` exists;
- `ReviewMailboxResultReader` exists;
- `ReviewResultForwarder` / `build_review_result_forwarder()` exist;
- tests exercise these components;
- **there is no production caller constructing/publishing `AgentMailboxAssignment`;**
- **there is no production caller of `build_review_result_forwarder()` / `ReviewResultForwarder`;**
- `ReviewMailboxResult` intentionally does not carry authoritative author `result_ref/result_sha256/attempt/generation/reviewer_execution_id/task_contract_ref`.

Therefore Phase C cannot safely begin at "convert ReviewMailboxResult to ReviewEvidence". The review task itself must first be deterministically bound to the exact author result identity and routed through existing scheduling/provider/worker authorities.

Phase C is split into:

```text
C0a  exact ResultIdentity -> deterministic review TaskPacketFile
C0b  trusted selected review route + exact packet -> review binding / execution contract
C1   trusted review result + reviewer durable execution -> zero_relay.ReviewEvidence
C2   classify relay decision / Phase-D handoff
```

WO-P1-201 becomes C1, not the first production composition step.

## 2. External release gate

No C0 source implementation until all are durably true:

1. repaired Phase-B tree has independent WO204 PASS;
2. GPT/integrator accepted that exact repaired tree;
3. WO209 fold candidate from fresh main is green;
4. Phase B is merged and post-main byte/CI verification is complete;
5. Issue #214 explicitly marks `PHASE_C0_NEXT_READY`;
6. fresh current main/source state is re-pinned;
7. fresh isolated implementation branch/worktree/claim/mutable-scope is published;
8. no overlapping owner is mutating the selected Phase-C0 source/test paths.

Until then:

`SAFE_TO_MUTATE_PHASE_C0=NO`

## 3. Existing authorities to reuse

### Exact author result identity

Reuse `zero_relay.ResultIdentity` unchanged:

- `task_contract_ref`
- `task_sha256`
- `result_ref`
- `result_sha256`
- `attempt_id`
- `generation`
- `author_execution_id`

No reviewer or caller may redefine these fields.

### Exact task packet authority

Reuse `claude_code_harness.TaskPacketFile`:

- `task_contract_ref`
- `path`
- `sha256`

C0a must follow the same deterministic/no-clobber publication discipline accepted for Phase B rather than invent a second file authority.

After Phase-B acceptance, reuse `NativeFileSystem.create_text_if_absent()` for exact no-clobber publication.

### Route / worker / provider authority

Reuse existing typed route facts rather than free strings:

- `HarnessDispatch` for task contract, project, worktree, expected branch/head, provider/model, strategy, mutation intent and execution dispatch identity;
- `SelectedAssignment` / existing scheduler decision for selected worker identity;
- `WorkerLeaseCandidate` / canonical Worker lease authority for worker/worktree/branch/head/ownership/mutation compatibility;
- existing provider profile/admission/configuration authority for provider/model route;
- existing GraphDispatch / ParallelReady execution composition where applicable.

Do not create a ZRA-specific worker registry, provider map, lease registry or scheduler.

### Review adapter / ReviewBridge

Reuse:

- `AgentMailboxAssignment` as the existing bounded assignment/binding vocabulary where applicable;
- `ReviewMailboxResultReader` for exact result-vs-assignment binding;
- `ReviewResultForwarder` for sanitized A-Wiki ReviewBridge ingest;
- existing trusted A-Wiki CLI boundary.

Do not import A-Wiki internals.

## 4. Critical production-call-site facts

Fresh repository archaeology at this packet base found:

1. `AgentMailboxAssignment` production construction is absent. References outside its defining module are the review adapter and tests.
2. `publish_agent_mailbox_assignment()` has only test callers.
3. `build_review_result_forwarder()` has only test callers.
4. `ReviewResultForwarder` has only its factory + test callers.
5. generic `domain.Agent` has no production constructor call and therefore must not be promoted to trusted mailbox-agent authority merely because the type exists.
6. `Assignment` / `SelectedAssignment` and worker lease/scheduler authorities do have production callers.
7. `HarnessDispatch` already carries provider/model/worktree/branch/head/task-contract route facts.
8. `WorkerLeaseCandidate` already carries worker/worktree/branch/head/runtime/project/ownership/dirty/mutation facts.

This means Phase C0 must compose existing *live* scheduling/provider/lease authorities and must not treat unused generic Agent metadata as authority.

## 5. C0a — deterministic review task materializer

### Objective

Given one exact accepted `ResultIdentity`, produce one deterministic bounded review `TaskPacketFile` whose bytes cryptographically bind the reviewer task to that exact author result.

### Preferred packet semantics

Use a versioned schema/domain separator, e.g. `zra2-review-task-v1`.

The rendered task must bind at minimum:

- author `task_contract_ref`;
- author `task_sha256`;
- author `result_ref`;
- author `result_sha256`;
- `attempt_id`;
- `generation`;
- `author_execution_id`;
- fixed independent-review instruction;
- fixed output schema expectations;
- explicit statement that reviewer prose is not merge/complete authority.

No free-form caller-supplied review instruction may change identity unless a separately approved bounded field is explicitly part of the canonical identity.

### Deterministic identity

Derive a canonical digest from versioned canonical bytes over the exact ResultIdentity fields.

Preferred shapes after release:

```text
review_contract_ref = zra2-review-v1:<digest>
review_task_path     = runs/zra2-review-<digest>.md
review_result_path   = runs/zra2-review-result-<digest>.json
```

Exact names may be refined by the released implementation packet, but identity must be deterministic and root-confined.

### Publication rules

- fixed existing parent (`runs`) only;
- no directory tree invention unless separately authorized;
- no raw `Path.write_text`, `os.replace`, or ad-hoc temp authority inside materializer;
- reuse `NativeFileSystem.create_text_if_absent()`;
- same path + same exact bytes => idempotent reuse;
- same path + different bytes => typed collision;
- missing/unverifiable raced state => fail closed;
- returned `TaskPacketFile.sha256` equals exact persisted UTF-8 bytes.

## 6. C0b — trusted review route binding

C0b runs only after C0a packet exists and a normal scheduler/provider/lease path has selected a reviewer execution route.

It must cross-bind:

- exact C0a `TaskPacketFile`;
- selected worker identity;
- canonical worker lease/candidate facts;
- `HarnessDispatch`;
- provider profile/config generation/admission as required by the selected execution path;
- exact review result destination;
- expected branch/head/worktree/project.

Required checks include:

- dispatch `task_contract_ref == review_task.task_contract_ref`;
- dispatch provider/model equal accepted provider authority;
- worktree/branch/head match worker lease authority;
- scheduler-selected worker matches lease worker;
- review route is independent of `author_execution_id` at the execution identity layer;
- mutation/read-only intent matches the review task contract;
- result destination is root-confined and deterministic for this review identity;
- current head has not drifted from exact reviewed candidate head.

## 7. Direct ZCode route vs external mailbox route

### Direct programmatic ZCode review — preferred initial production path

For a direct ZCode reviewer dispatched through existing programmatic execution authority:

- do **not** require mailbox publication merely to manufacture authority;
- the exact TaskPacketFile is the task authority;
- scheduler/lease/provider/HarnessDispatch are route authority;
- durable reviewer execution record is execution authority;
- a typed assignment/binding object may be constructed for `ReviewMailboxResultReader` / `ReviewResultForwarder` only from those trusted facts;
- `role` should be a fixed protocol value such as `independent-review`, not caller prose;
- if `agent_id` is not consumed by the direct forwarding trust checks, treat it as metadata only and do not let it select filesystem target/path.

Current `ReviewResultForwarder` authority checks depend on assignment:

- `task_id`;
- `provider_id`;
- `model_id`;
- `base_head`;
- `task_sha256`;
- `worktree` for A-Wiki ingest target.

These fields must be sourced from exact C0a + route authorities.

### External mailbox route — NOT authorized by default

`publish_agent_mailbox_assignment()` derives the mailbox filesystem target from `assignment.agent_id`.

There is currently no proven production authority mapping a selected Worker to an external mailbox `agent_id`.

Therefore external mailbox publication must fail closed with:

`MAILBOX_AGENT_ID_AUTHORITY_MISSING`

unless a later explicit packet identifies and proves an existing authoritative mapping.

Do **not** silently set `agent_id = worker_id`, provider name, model name, plugin label, or human-supplied nickname.

This restriction does not block a direct programmatic ZCode review route.

## 8. C1 handoff contract

Once the review execution produces a result and existing adapter validates/forwards it, WO-P1-201 C1 consumes:

- original exact `ResultIdentity`;
- exact C0a review task identity;
- trusted route/binding facts from C0b;
- sanitized `ReviewMailboxResult`;
- trusted ReviewBridge forward response/confirmation as required;
- durable reviewer `DurableExecutionRecord` / exact reviewer execution ID.

C1 then creates `zero_relay.ReviewEvidence` only after proving:

- task/result/attempt/generation still equal original ResultIdentity;
- review task was deterministically generated for that exact ResultIdentity;
- reviewer result binds exact review task/provider/model/head/task SHA;
- reviewer execution is terminal usable and independent from author execution;
- ReviewBridge confirmation is for the same task;
- disposition is bounded/typed.

Reviewer result artifact hash must never substitute for author result hash.

## 9. RED-first implementation matrix after release

### C0a identity

- exact ResultIdentity positive control;
- task SHA drift changes review-task identity;
- author result SHA drift changes identity;
- result ref drift changes identity;
- attempt drift changes identity;
- generation drift changes identity;
- author execution ID drift changes identity;
- malformed ResultIdentity rejected by existing type;
- same identity deterministic bytes/path/ref;
- same bytes idempotent reuse;
- different bytes at deterministic path typed collision;
- raced same bytes converge;
- raced different bytes preserve conflict and fail typed;
- missing parent/mutation forbidden/file-size/UTF-8 cases;
- unsafe source strings never become path authority.

### C0b route binding

- dispatch task contract mismatch;
- provider mismatch;
- model mismatch;
- worktree mismatch;
- branch mismatch;
- head mismatch;
- project mismatch;
- selected worker vs lease worker mismatch;
- stale/released/expired lease where selected execution path requires it;
- provider generation/admission drift where required;
- wrong review result destination;
- head changes after review task materialization;
- author/reviewer execution identity alias once durable reviewer execution exists;
- external mailbox request without agent-id authority => `MAILBOX_AGENT_ID_AUTHORITY_MISSING`.

### C0→C1 anti-replay

- task packet generated for Result A cannot review Result B;
- review output for packet A cannot be rebound to packet B;
- same provider/model/head but different result SHA cannot replay;
- same author result but stale attempt/generation cannot replay;
- old review result cannot authorize new candidate head.

## 10. Preferred implementation shape after release

Do not pre-authorize exact filenames before fresh main re-pin, but likely bounded additions are:

- `src/a_conductor/zero_relay_review_task.py`
- `tests/test_zero_relay_review_task.py`

C0b may live in the same module only if it stays a pure composition/validation seam. If route composition would require touching established execution assembly, stop for an explicit scope expansion rather than modifying broad production code opportunistically.

Avoid modifying:

- `zero_relay.py` Phase-A decision semantics;
- generic `AgentMailboxAssignment` schema unless a proven impossible binding demands a separate adjudication;
- `ReviewMailboxResultReader` / `ReviewResultForwarder` semantics without a failing contract test proving necessary change;
- scheduler/provider/lease stores.

## 11. Verification ladder after release

1. focused C0a tests;
2. focused C0b route-binding tests;
3. Phase-B `NativeFileSystem` no-clobber tests;
4. `tests/test_zero_relay.py`;
5. `tests/test_agent_change_packets.py`;
6. `tests/test_review_mailbox_adapter.py`;
7. scheduler/lease/dispatch tests only for actually imported typed authority;
8. provider tests only for actually consumed authority;
9. compile/diagnostics;
10. `git diff --check`;
11. strict UTF-8 / no U+FFFD;
12. exact changed-path + untracked audit;
13. secret-like added-line scan;
14. hosted CI;
15. independent exact-SHA R3 review.

## 12. Stop gates

STOP and checkpoint immediately on:

- Phase B not post-main accepted;
- Issue #214 C0 release absent;
- source/main drift invalidating this architecture;
- no trusted source for a required route field;
- need to invent worker→mailbox agent mapping;
- route overlap/ownership conflict;
- need to mutate a store/authority outside released scope;
- ambiguous execution/review state;
- hosted CI non-terminal;
- independent review/GPT acceptance/merge/post-main gate.

Unknown authority never becomes a guessed default.

## 13. Acceptance boundary

Phase C0 is accepted only when:

1. exact ResultIdentity deterministically creates one exact bounded review TaskPacketFile;
2. persisted packet bytes are collision-safe and idempotent through accepted filesystem authority;
3. a trusted production review route can bind that packet to provider/model/worktree/branch/head/worker without caller-forged authority;
4. direct ZCode route does not depend on an invented mailbox-agent registry;
5. external mailbox publication remains blocked unless authoritative `agent_id` mapping exists;
6. the resulting binding gives WO201/C1 enough evidence to prove the review belongs to the exact author result;
7. no duplicate scheduler/provider/lease/review/filesystem authority is introduced;
8. exact candidate receives green CI and independent R3 review.

Acceptance of this design packet does not authorize source mutation.

## 14. Current roadmap effect

After Phase-B post-main verification, the ZRA-2 critical path becomes:

```text
Phase C0a review task materialization
  -> Phase C0b trusted review route binding
  -> reviewer execution
  -> existing review-result reader / ReviewBridge forward
  -> WO201 Phase C1 ReviewEvidence composition
  -> classify_relay_decision
  -> WO205 Phase D closeout composition
```

Do not skip C0 and ask C1 to invent missing review-task provenance.