# WO-P1-221 — ZRA-2 direct-review result provenance contract

Status: PREPARED / HOLD FOR WO220 ADJUDICATION / NO SOURCE MUTATION AUTHORIZED
Parent: WO-P1-201 / WO-P1-210 / WO-P1-216 / WO-P1-219 / Issue #214
Owner: GPT-5.6 Sol integrator architecture lane
Preferred future executor: ZCode GLM-5.3 only after explicit release
Base at packet creation: `3e10b0464017f30b250314ba3ece9ebf9edf202f`
Risk: R3 reviewer-result identity / trust boundary

## 1. Why this packet exists

Fresh C1 archaeology after the WO219 provenance repair exposed a boundary that the older WO201 design predates.

The accepted direction for Phase C0 is a **direct programmatic ZCode review route** that deliberately avoids inventing an external mailbox `agent_id`. The C0 route is READ_ONLY against the reviewed project. That means Phase C1 cannot silently fall back to an `AgentMailboxAssignment` merely to reuse `ReviewMailboxResultReader`.

Current runtime facts at this base:

- `HarnessDispatch.evidence_destination_ref` is validated and serialized, but no production execution consumer writes that destination;
- ZCode durable `result.json` is the six-key supervised **process result**, not the semantic review verdict;
- the exact model/reviewer response bytes are written to `stdout.log`;
- `report.json` (`zcode-report/1`) binds `execution_id`, `task_contract_ref`, `task_packet_sha256`, runtime selection identity, response byte count and `response_sha256`;
- `DurableExecutionRecord` binds reviewer execution/job/work-order/project/worker/backend/repo/branch/head and durable artifact refs/state;
- existing `ReviewMailboxResultReader` expects mailbox-result bytes plus `AgentMailboxAssignment`; it is not a direct ZCode-result reader;
- current C0 review task text constrains verdict vocabulary, but a fixed machine-readable direct-review response schema/path contract is not yet proven.

Therefore C1 must not invent a reviewer payload schema, conflate supervised `result.json` with review semantics, or fabricate mailbox identity.

## 2. External release gate

This packet is HOLD unless WO220 independently adjudicates PR #299 exact repair and one of these becomes true:

1. WO220 proves the existing C0 contract already supplies a trustworthy machine-readable result contract, in which case this packet may be CLOSED/NOT_NEEDED; or
2. WO220 returns a bounded result-contract finding (`DIRECT_REVIEW_RESULT_CONTRACT_MISSING` or equivalent) and GPT/integrator explicitly releases WO221.

Even after release, no C1 source mutation until:

- repaired C0 exact SHA is independently accepted;
- repaired C0 is safely integrated into main without merging a known-defective intermediate tree alone;
- post-main byte/CI verification is complete;
- Issue #214 marks the direct-result/C1 step NEXT_READY;
- fresh claim/worktree/base/scope is published.

Until then:

`SAFE_TO_MUTATE_WO221=NO`

## 3. Existing authorities to reuse

### Reviewer execution truth

Reuse `DurableExecutionRecord` and the existing execution store/artifact boundaries. Relevant fields include:

- `execution_id`
- `job_id`
- `work_order_ref`
- `project_id`
- `worker_id`
- `backend_id`
- `repo_root`
- `branch`
- `head_before`
- `operation_ref`
- `stdout_ref`
- `result_ref`
- `report_ref`
- `transport_state`
- `execution_state`
- terminal timestamps/version.

Do not create a reviewer execution store.

### Exact reviewer response bytes

For the ZCode path, reuse existing durable artifacts:

- `stdout.log` = exact model response bytes;
- `report.json` = `zcode-report/1` response byte/hash binding;
- supervised `result.json` = child-process terminal result only.

Never treat `result.json` exit metadata as the semantic review verdict.

### Author/result identity

Reuse `zero_relay.ResultIdentity` unchanged.

### C0 route identity

After C0 acceptance, consume the accepted `DirectReviewRoute` (or its final accepted equivalent) as the route binding for:

- review task contract/ref/hash;
- reviewed HEAD;
- author digest/result/attempt/generation binding;
- reviewer worker/provider/model/project/worktree/branch/head;
- reviewer dispatch execution id;
- READ_ONLY protocol role.

Do not reconstruct these from raw strings when an accepted typed route object exists.

### Final Phase-A evidence vocabulary

Reuse `zero_relay.ReviewEvidence` unchanged if possible:

- author task contract/ref/hash/result ref/hash/attempt/generation copied from the author `ResultIdentity` after cross-binding;
- `reviewer_execution_id` from the trusted durable reviewer execution;
- `ReviewDisposition.ACCEPTED` or `.REJECTED` only from a bounded validated semantic verdict.

No reviewer prose may set merge/complete/ready authority.

## 4. Preferred architecture if WO220 confirms the gap

If C0 task bytes need to change to require a strict machine-readable response, do not reuse the existing `zra2-review-v1` contract identity. Introduce a versioned review protocol identity (for example `zra2-review-v2`) so contract ref, deterministic task path and result destination change with the protocol semantics. The exact version label remains an implementation decision, but same contract/path with different task bytes is forbidden.

### Protocol-version rule

### Option A — RECOMMENDED: durable stdout + report as direct-review semantic evidence

Keep the review execution READ_ONLY against the reviewed project.

C0 task protocol defines one strict response schema, returned as the entire reviewer response on stdout. C1 then reads existing durable execution artifacts and validates them without creating a second project result file.

Preferred response shape (exact schema may be refined only before source release):

```json
{
  "schema": "zra2-review-result-v1",
  "review_contract_ref": "zra2-review-v1:<digest>",
  "reviewed_head": "<exact git sha>",
  "review_task_sha256": "<exact task packet sha256>",
  "verdict": "ACCEPTED|REJECTED",
  "findings": []
}
```

Rules:

- output must be JSON only; no Markdown fence/prefix/suffix;
- bounded size inherited from existing execution/harness limits;
- strict UTF-8;
- fixed exact top-level key policy (or explicit bounded optional fields); no arbitrary authority keys;
- findings are evidence only and bounded; they never set lifecycle authority;
- verdict vocabulary maps one-to-one to `ReviewDisposition`;
- malformed/extra authority-bearing/truthy variants fail closed.

C1 validation chain:

```text
accepted ResultIdentity
+ accepted C0 DirectReviewRoute
+ DurableExecutionRecord
+ durable report.json
+ exact stdout bytes
    -> validate execution identity/state/artifact refs
    -> validate report schema + execution/task-packet binding
    -> sha256(stdout bytes) == report.response_sha256
    -> parse strict zra2-review-result-v1 JSON
    -> cross-bind contract/task hash/reviewed HEAD to C0 route
    -> cross-bind author fields to ResultIdentity/C0 route
    -> reviewer execution != author execution
    -> terminal usable reviewer execution only
    -> map ACCEPTED|REJECTED
    -> zero_relay.ReviewEvidence
```

This is `REUSE/WRAP`, not a second review lifecycle.

### Option B — backend-owned semantic artifact

A backend/harness could materialize a validated semantic result artifact into its own run directory after reading reviewer stdout. This is acceptable only if it reuses existing run-artifact authority and remains outside the reviewed project mutation surface.

Do not use `evidence_destination_ref` as proof that a project file exists unless a production writer/verification boundary actually owns it.

Option B is more invasive than A and requires separate scope if execution backend source must change.

### Option C — external mailbox route

Not preferred for the direct ZCode path. Current C0 archaeology found no authoritative worker -> external mailbox `agent_id` mapping. Do not fabricate one merely to reuse the mailbox reader.

External mailbox remains independently gated by `MAILBOX_AGENT_ID_AUTHORITY_MISSING` unless authoritative mapping appears.

## 5. Required direct-result cross-binding

Before any `ReviewEvidence` may be constructed, prove at minimum:

- input is accepted typed `ResultIdentity`;
- C0 route belongs to that exact author result identity and exact reviewed HEAD;
- durable record `execution_id == route.dispatch_execution_id`;
- durable record project/worker/repo/worktree/branch/head/work-order facts agree with the route where those fields are represented;
- execution is terminal usable under existing semantics; `RUNNING`, `PROCESS_EXITED_UNKNOWN_RESULT`, `RECOVERY_REQUIRED`, `VERIFICATION_REQUIRED`, failed/partial/cancelled states cannot authorize ACCEPTED;
- durable report is the expected ZCode report schema for the same execution;
- report task contract/ref/hash equals C0 review task identity;
- report response hash/byte count exactly matches stdout bytes;
- response JSON schema/contract/task hash/reviewed HEAD equals C0 route;
- reviewer execution is distinct from author execution;
- author `result_ref/result_sha256/attempt/generation/task` copied from ResultIdentity, never reviewer payload;
- no review artifact hash substitutes for author result hash;
- verdict only maps bounded `ACCEPTED|REJECTED` (or final explicitly approved vocabulary);
- findings cannot mint ready/merge/retry/complete authority.

## 6. RED-first matrix after release

At minimum:

1. valid exact accepted review -> exact `ReviewEvidence`;
2. valid rejected review -> `ReviewDisposition.REJECTED`;
3. stdout hash mismatch vs report;
4. response byte-count mismatch;
5. wrong report execution id;
6. wrong task contract;
7. wrong review task hash;
8. wrong reviewed HEAD;
9. wrong review contract ref;
10. stale response from old HEAD;
11. response from different author result/attempt/generation;
12. reviewer execution id == author execution id;
13. wrong worker/project/repo/worktree/branch/head in durable record;
14. nonterminal/recovery/failed/partial/cancelled execution;
15. missing stdout/report/result artifacts as applicable;
16. malformed JSON, duplicate keys if parser semantics make them ambiguous, non-object root;
17. unknown schema;
18. verdict `PASS`, `true`, `1`, lowercase/truthy variants rejected unless explicitly part of final vocabulary;
19. extra `ready`, `merge`, `complete`, `retry` fields do not become authority (prefer reject unknown authority-like keys);
20. oversized/binary/invalid UTF-8 response;
21. report says one SHA while file changes after read/check (TOCTOU boundary must be explicit and fail closed or use one captured byte value);
22. identical replay is deterministic;
23. same semantic result applied to another C0 route fails;
24. no filesystem/provider/scheduler/lease/job mutation from pure C1 reader/composer;
25. no A-Wiki internal import and no new review/execution store.

## 7. C1 module shape if Option A is accepted

Likely bounded additions after fresh main re-pin:

- `src/a_conductor/zero_relay_review_evidence.py`
- `tests/test_zero_relay_review_evidence.py`

Potential pure typed values may include a validated `DirectReviewResult` that exists only after durable artifact verification.

Do not modify `ReviewMailboxResultReader` merely to make direct ZCode fit a mailbox abstraction. Preserve mailbox route for mailbox use.

If the C0 task protocol needs a strict JSON response schema added, that is a bounded C0 protocol amendment and must be accepted/reviewed as part of the same exact review-task identity version. Do not silently change bytes under `zra2-review-v1` after acceptance; either repair before acceptance or version the protocol explicitly.

## 8. ReviewBridge / A-Wiki boundary

Do not assume that A-Wiki forward/ingest is author-result identity authority. It is a review integration boundary.

After direct result validation, fresh archaeology must decide whether governance requires ReviewBridge confirmation before `ReviewEvidence` construction. If required, add only a narrow adapter that forwards the already validated/sanitized result and cross-binds the returned task identity. Do not fabricate `AgentMailboxAssignment.agent_id` to reach the current mailbox-specific forwarder.

If a direct ReviewBridge API does not exist, record a separate bounded integration gap rather than importing A-Wiki internals or duplicating its lifecycle.

## 9. Stop gates

STOP/checkpoint on:

- WO220 has not resolved the result-contract question;
- C0 exact repair not independently accepted/merged/post-main verified;
- main/source architecture drift changes ZCode artifact semantics;
- a required durable route/execution field has no trusted source;
- need to mutate execution backend/harness outside released scope;
- need to invent mailbox agent mapping;
- need to invent a second execution/review/result store;
- ambiguous terminal execution semantics;
- ownership overlap;
- hosted CI / independent review / merge / post-main external gate.

Unknown provenance never becomes a guessed default.

## 10. Current roadmap effect

If WO220 confirms the missing result contract, the critical path becomes:

```text
C0 protocol/result-contract repair (if required)
  -> independent C0 rereview
  -> safe C0 integration + post-main proof
  -> C1a durable direct-review result validation
  -> C1b ReviewEvidence composition
  -> optional/required ReviewBridge confirmation under explicit policy
  -> Phase-A classify_relay_decision
  -> WO205 Phase D closeout composition
```

This packet is preparation only. It does not release source mutation.
