# WO-P1-230 — ZRA-2 review task-contract provider-authority bridge

Status: PREPARED / NEXT_READY AFTER CLAIM / R3
Parent chain: WO216/WO219/WO222 accepted C0 -> WO230 -> WO226 completion -> WO223/C1 -> WO205 Phase D
Owner: GPT-5.6 Sol architecture/acceptance; bounded implementation owner: GLM-5.3 MAX
Base for packet: `origin/main@251df211afc1ee5452f3652675d7a2f38c526876`
Issue authority: #214

## 1. Why this predecessor exists

WO226 reviewer execution candidate `cc398d6b1bff329d7145d0a98662add108b423ab` closed the original Astra AF1-AF4 campaign but remains `CHANGES_REQUIRED`.

Two direct-review authority failures were reproduced independently:

1. terminal-unusable cleanup can release admission+lease while persisted provider admission generation is wrong/unknown because the cleanup path disables expected-generation checking;
2. a `ParallelReadyTask` with no provider endpoint/security/generation authority can still reach one model effect and a usable WO226 handoff.

Further read-only archaeology proved the second issue is not safely solved by adding more ad-hoc `if` checks in WO226:

- accepted production `ParallelReadyExecutor` / `ProductionElasticWorkerExecutor` require canonical provider authority;
- production provider authorization reuses `ProviderExecutionRequirement` + `ProviderExecutionAuthority` and covers provider-store identity, configuration generation, canonical security policy, readiness and quota;
- `ProviderExecutionRequirement` security provenance is derived from persisted `task-contract/v1` bytes;
- the accepted ZRA-1 ZCode assembly treats provider snapshot profile/credential/endpoint as canonical authority and caller values only as assertions;
- current ZRA-2 review v1 publishes a Markdown prompt whose logical contract ref is `zra2-review-v1:<digest>`. That artifact cannot directly satisfy `ProviderExecutionRequirement.from_task_contract_file()`, whose `task_contract_ref` is a project-relative persisted task-contract authority file and whose operation identity wraps a base operation into `provider-op:<sha>`.

Therefore forcing WO226 to trust caller-supplied `ProviderPolicyTaskSecurity`, ambient snapshot state, or a newly invented policy/requirement representation would create a second provider-authority path. That is forbidden.

## 2. Architecture decision

Version the direct-review task publication protocol without changing v1 history.

WO230 adds an explicit review-v2 authority sidecar that reuses the existing `task-contract/v1` schema while keeping the actual ZCode reviewer prompt as a deterministic Markdown packet.

Recommended deterministic v2 artifact pair:

- review prompt: `runs/zra2-review-v2-<digest>.md`
- review authority contract: `runs/zra2-review-v2-<digest>.task.json`
- semantic result destination: `runs/zra2-review-result-v2-<digest>.json`

For v2, `ReviewTaskRefs.contract_ref` MUST be the project-relative authority-contract path (`*.task.json`), not a synthetic `zra2-review-v2:<digest>` string. `TaskPacketFile.task_contract_ref`, `HarnessDispatch.task_contract_ref`, GraphDispatch `work_order_ref`, lease task authority where required, and `ProviderExecutionRequirement.task_contract_ref` must therefore converge on that same project-relative contract path.

The Markdown prompt remains `TaskPacketFile.path`. Its exact SHA-256 is independently bound into the task-contract metadata and into the ZCode packet operation identity.

## 3. task-contract/v1 v2 authority envelope

The persisted JSON MUST validate against existing `schemas/task-contract.schema.json`; do not create a second schema.

It must deterministically bind at least:

- `schema_version=1.0.0`;
- deterministic review task id/version;
- READ_ONLY authority (`mutation_allowed=false`);
- project id supplied as an explicit trusted input and included in the v2 identity digest;
- reviewed exact HEAD with `identity_policy=EXACT`;
- fixed review security policy derived from bytes, not caller prose:
  - privacy class appropriate for repository review (default `INTERNAL` unless the active task contract proves a stronger classification is required);
  - network policy `DENIED` for task egress;
  - empty network allowlist by default;
  - `secret_access=false`;
- bounded elapsed/retry policy;
- deterministic metadata containing:
  - review protocol/schema id;
  - exact author `ResultIdentity` fields;
  - exact reviewed HEAD;
  - review identity digest;
  - review prompt relative path;
  - review prompt SHA-256;
  - semantic result destination ref;
  - bounded whole-response semantic requirements for downstream C1.

Do not put provider id, model id, endpoint URL, credential ref, generation, quota, or mutable runtime state into these deterministic task bytes. Those remain canonical provider-store/route authority consumed later through existing provider execution authority.

## 4. Publication / crash contract

Reuse `NativeFileSystem.create_text_if_absent()` only. No raw Path write, temp-file publication, second no-clobber primitive, or overwrite.

Recommended publication order:

1. deterministic Markdown prompt;
2. verify prompt exact bytes/path/hash;
3. deterministic task-contract authority JSON which binds that prompt path/hash;
4. verify authority exact bytes/path/hash.

A crash after prompt publication but before authority publication is a safe partial state: replay may verify the exact prompt and create the deterministic missing authority file. Divergent existing bytes on either path are typed collision/recovery. Authority sidecar present with missing/divergent prompt is fail-closed; never fabricate provider authority from it.

Port deterministic crash/no-clobber tests for:

- both absent;
- exact replay;
- prompt-only exact recovery;
- prompt collision;
- authority collision;
- authority references wrong prompt hash/path;
- concurrent exact publication convergence;
- concurrent divergent publication preserves winner and typed collision;
- invalid UTF-8 / malformed JSON / task-contract schema violation where relevant.

## 5. ProviderExecutionRequirement compatibility proof

WO230 MUST prove, using only existing provider-authority APIs, that the v2 authority artifact can be consumed by:

`ProviderExecutionRequirement.from_task_contract_file(...)`

with:

- provider authority database path supplied by the execution routing layer;
- exact current provider id;
- exact expected configuration generation;
- `task_contract_ref == ReviewTaskRefs.contract_ref` (the persisted authority JSON relative path);
- `base_operation_ref == ZCodeTaskPacketIdentity.canonical_operation_ref()` for the exact Markdown prompt packet.

Then prove an existing `ParallelReadyTask` can be constructed such that:

- `task_packet.task_contract_ref == provider_requirement.task_contract_ref`;
- GraphDispatch `work_order_ref == task_contract_ref`;
- GraphDispatch `operation_ref == provider_requirement.operation_ref`;
- `provider_requirement.base_operation_ref` equals the exact packet canonical operation;
- requirement security equals task provider security;
- requirement generation equals task expected generation;
- provider endpoint/security/generation triple is complete;
- READ_ONLY lease/harness intent and exact reviewed HEAD remain bound.

This is compatibility proof only. WO230 does NOT execute a live provider, reserve provider admission, spawn ZCode, or change provider/store/lease semantics.

## 6. Initial source/test scope

Allowed source/test mutation after a fresh claim:

- MODIFY `src/a_conductor/zero_relay_review_task.py`;
- MODIFY `tests/test_zero_relay_review_task.py`;
- WO230 result/checkpoint evidence.

Read-only imports allowed from:

- `schemas/task-contract.schema.json` / existing schema validation helpers;
- `claude_code_harness.TaskPacketFile`;
- `provider_execution_authority.ProviderExecutionRequirement`;
- `parallel_ready_execution.ParallelReadyTask`;
- `zcode_runner.ZCodeTaskPacketIdentity`;
- existing provider/task/lease/dispatch types.

Forbidden without explicit Sol scope expansion:

- `provider_execution_authority.py`;
- `provider_policy.py`;
- `parallel_ready_execution.py`;
- provider config/store schemas;
- worker lease / job / GraphDispatch semantics;
- WO226 source;
- semantic C1 parser/evidence source;
- GoalCloseout / Phase D;
- live provider/runtime/secret mutation.

If v2 cannot be expressed in this scope while preserving existing authority identities, checkpoint `DESIGN_GAP` with the exact conflicting invariant and STOP.

## 7. Required RED/GREEN matrix

At minimum:

1. v1 remains byte/identity compatible and all existing v1 tests remain green;
2. v2 same inputs -> identical digest/paths/prompt/authority bytes;
3. changing any author ResultIdentity field, reviewed HEAD or trusted project id changes v2 identity;
4. v2 task-contract validates existing schema;
5. task-contract security bytes derive exactly the expected `ProviderPolicyTaskSecurity` through `ProviderExecutionRequirement`;
6. missing/corrupt/divergent authority sidecar fails closed;
7. prompt SHA/path rebound inside sidecar fails closed;
8. v2 `TaskPacketFile` + `ProviderExecutionRequirement` + GraphDispatch operation/work-order identity construct a valid `ParallelReadyTask` without mutating production provider code;
9. requirement/task security drift, generation drift, operation-ref drift, work-order drift fail at existing authority boundaries;
10. no provider/model/endpoint/credential/generation value can be injected through review prompt metadata to override canonical routing authority;
11. no external mailbox/C1/merge/complete authority introduced.

## 8. Handoff to WO226

WO230 acceptance does not merge or complete WO226.

After WO230 is accepted/merged/post-main, WO226 repair resumes on a fresh exact main/PR314 reconciliation. Its provider preflight must then consume the v2 `ParallelReadyTask` with a present `ProviderExecutionRequirement` and reuse existing `ProviderExecutionAuthority` semantics rather than ambient/caller policy fragments. WO226 still must repair terminal-unusable expected-generation cleanup.

Until then:

`SAFE_TO_ACCEPT_WO226=NO`.

## 9. Handoff to WO223/C1

WO223 semantic C1 remains downstream. The review-task protocol v2 identity/publication subset is moved to WO230; WO223 should consume accepted WO230 artifacts read-only and focus on strict response/report/artifact validation and `ReviewEvidence` composition.

## 10. Completion gate

GLM stops at one frozen exact SHA with:

- RED-first evidence;
- focused + directly related C0/provider-authority compatibility tests;
- compile/import/diff/UTF-8/scope checks;
- exact changed paths within released scope;
- durable result/checkpoint;
- hosted exact-head CI triggered/observed according to policy;
- no self-acceptance/merge.

GPT/Astra independent exact-SHA review remains mandatory before merge/post-main release to WO226.
