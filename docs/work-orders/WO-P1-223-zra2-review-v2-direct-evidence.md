# WO-P1-223 — ZRA-2 review protocol v2 + direct review evidence composition

Status: PREPARED / HOLD_AFTER_WO225_AND_WO226 / R3
Parent: WO-P1-221 / WO-P1-201 / WO-P1-216 / WO-P1-219 / WO-P1-225 / WO-P1-226 / Issue #214
Immediate predecessor chain: WO225 repaired C0 READ_ONLY route authority -> WO226 accepted reviewer-execution handoff
Integrator/architecture owner: GPT-5.6 Sol
Preferred implementation executor: ZCode GLM-5.3 MAX
Repository: A-Wiki-Conductor
Prepared base: `60aba770fd457d04f1e31040b9dfd7af3927f669`
Risk: R3 protocol identity / durable review evidence / anti-replay

## 1. Why this WO exists

Historical C0 was accepted, merged and post-main verified on `main@60aba770fd457d04f1e31040b9dfd7af3927f669`, but GPT later proved a C0 trust-boundary defect: a route could claim READ_ONLY while its lease/task authority was not equivalently bound. WO225 repairs that boundary and WO226 then supplies the missing production reviewer-execution handoff. WO223 must consume those accepted successors rather than the historical C0 route in isolation.

The repaired/versioned review-task protocol must bind the author `ResultIdentity`, exact reviewed HEAD, deterministic review task bytes, persisted task provenance, a truthful READ_ONLY reviewer route, and the accepted WO226 reviewer-execution handoff. It still requires one strict machine-readable semantic review response shape before `ReviewEvidence` can be created. Its task text constrains the verdict vocabulary in prose only.

C1 therefore cannot safely convert arbitrary reviewer prose into `zero_relay.ReviewEvidence`.

GPT architecture decision on Issue #214:

- direct ZCode review evidence may be validated locally from accepted C0 route + durable execution truth + exact durable artifacts;
- mailbox-specific `ReviewBridge` forwarding is **not** a mandatory precondition for direct C1 evidence composition because no authoritative worker -> mailbox `agent_id` mapping exists for this direct route and `ReviewResultForwarder` has no production direct-route caller;
- A-Wiki ReviewBus remains the accepted external review integration/governance boundary and must not be cloned;
- if review task semantics change, accepted `zra2-review-v1` must not be silently reused. A new explicit protocol identity is required.

This WO remains the bounded semantic-evidence successor only if post-WO226 archaeology still confirms the gap and finds no already-accepted equivalent reader/schema.

## 2. Release gate

Do not mutate source merely because this packet exists.

WO223 becomes source-READY only when all are true:

1. actual `origin/main` contains the accepted WO225 C0 READ_ONLY lease/task binding repair and its post-main verification;
2. actual `origin/main` contains the accepted WO226 reviewer-execution bridge and its post-main verification;
3. Issue #214 explicitly marks WO223/C1 as NEXT_READY after those predecessors;
4. WO221/WO223 archaeology still confirms there is no existing strict direct-review semantic result contract/validator that makes WO223 unnecessary;
5. the accepted WO226 execution handoff preserves dispatch-context identity and actual durable runtime execution identity distinctly and proves their cross-binding by accepted fingerprint/admission/task/runtime authority;
6. no overlapping claim owns any mutable WO223 source/test path;
7. a fresh worktree/branch is created from then-current main and is clean;
8. exact scope/owner/claim is checkpointed before source mutation.

If an existing trusted implementation already solves the gap, classify `REUSE / WO223_NOT_NEEDED` and STOP.

If any authority item is UNKNOWN, `SAFE_TO_MUTATE_WO223=NO`.

## 3. Architecture decisions already settled by GPT

### 3.1 Version the protocol

The semantic response contract changes review-task meaning. Therefore introduce a new explicit review protocol identity (recommended `zra2-review-v2`; another explicit successor label is acceptable only if the exact rationale is recorded).

The successor identity must change every deterministic identity-bearing surface derived from protocol semantics, including at minimum:

- review contract ref;
- canonical review identity digest/domain;
- deterministic task path;
- deterministic result destination/ref if retained as a logical ref;
- exact review task SHA-256.

Do not overwrite or reinterpret existing `zra2-review-v1` artifacts.

### 3.2 Strict whole-response semantic schema

The reviewer must return JSON only, no Markdown fence/prefix/suffix.

Recommended v2 whole-response shape:

```json
{
  "schema": "zra2-review-result-v2",
  "review_contract_ref": "zra2-review-v2:<digest>",
  "reviewed_head": "<exact normalized git sha>",
  "review_task_sha256": "<exact review task sha256>",
  "verdict": "ACCEPTED|REJECTED",
  "findings": []
}
```

The implementation may refine bounded `findings` structure before freeze, but it must not add lifecycle-authority fields. Unknown authority-like fields such as `ready`, `merge`, `complete`, `retry`, `accepted_for_merge` must fail closed rather than become truth.

Strict parser requirements:

- exact UTF-8, no replacement decoding;
- JSON object root only;
- duplicate keys rejected;
- bounded total bytes;
- bounded key set;
- exact schema identifier;
- exact `ACCEPTED|REJECTED` vocabulary only unless GPT explicitly expands it before implementation freeze;
- no truthy aliases (`PASS`, `true`, `1`, lowercase shortcuts) by default;
- bounded findings count/size;
- findings are evidence only.

### 3.3 Reuse existing execution/artifact authority

Reuse, do not replace:

- `execution_record.DurableExecutionRecord` for reviewer execution/job/work-order/project/worker/backend/repo/branch/head/artifact refs/state;
- existing execution store API as the record authority;
- `execution_artifacts.ExecutionArtifactService` for confined artifact access where its contract is sufficient;
- existing ZCode `stdout.log` exact response bytes;
- existing `zcode-report/1` report;
- repaired C0 `DirectReviewRoute` from accepted WO225;
- accepted WO226 reviewer-execution handoff (exact final merged type/symbol), preserving both dispatch-context identity and actual durable runtime `execution_id` plus exact execution fingerprint/artifact refs;
- author `zero_relay.ResultIdentity`;
- final `zero_relay.ReviewEvidence` and `ReviewDisposition`.

Do not add a review-result store, execution store, scheduler, provider authority, lease authority or second review lifecycle.

### 3.4 Production ZCode report shapes are not identical

Fresh post-main archaeology found at least two relevant report producers:

- in-process `zcode_runner` report includes `schema`, `execution_id`, `task_contract_ref`, `task_packet_sha256`, `selection_sha256`, `response_bytes`, `response_sha256`, `session_id`;
- `zcode_supervised_helper` report includes `schema`, `execution_id`, `task_packet_sha256`, `response_bytes`, `response_sha256`, `session_id`, and may add `exit_state`, but does not carry `task_contract_ref`.

Do not fabricate missing report fields or require one producer's optional fields from the other.

Cross-bind only facts actually owned by each active production path. When a report lacks `task_contract_ref`, use trusted `DurableExecutionRecord.work_order_ref` plus the repaired `DirectReviewRoute.review_contract_ref` and accepted WO226 reviewer-execution handoff if current production assembly proves that binding.

The report/runtime `execution_id` must bind to the WO226 handoff's actual durable runtime execution identity, **not** to `DirectReviewRoute.dispatch_execution_id`. The route dispatch ID remains the dispatch/provider-admission context identity and is expected to differ from the supervised runtime execution ID on the accepted ZRA-1 production path.

If actual current production assembly disproves this proposed binding, checkpoint exact evidence and STOP for GPT scope/architecture adjudication.

### 3.5 Raw bytes are authority, not replacement-decoded text

`ExecutionArtifactService` exposes both `raw` and replacement-decoded `text`. C1 semantic parsing must use captured `raw` bytes and strict UTF-8 decode.

The current artifact service computes a full-file digest and then separately reads the requested bytes. Close this potential digest/read TOCTOU seam in C1 by requiring one complete non-truncated captured response and independently proving:

`sha256(captured_raw) == artifact_slice.sha256`

plus exact byte count against report metadata.

If the artifact exceeds the accepted whole-response bound or the slice is truncated, fail closed. Do not concatenate arbitrary multi-read snapshots unless a separate stable-snapshot authority is proven.

### 3.6 ReviewBridge is not a mandatory direct-C1 identity gate

For the direct ZCode path, strict local durable validation may compose `zero_relay.ReviewEvidence` without first forwarding through the mailbox-specific `ReviewResultForwarder`.

Do not fabricate `AgentMailboxAssignment.agent_id`.

A-Wiki ReviewBus remains the accepted external review integration/governance system. A later separately scoped adapter may forward already-validated/sanitized direct review evidence when an authoritative direct API/mapping exists. WO223 does not create that API.

## 4. Initial mutable scope after release

Preferred bounded source/test scope:

- MODIFY `src/a_conductor/zero_relay_review_task.py` only for explicit v2 protocol/task identity support;
- MODIFY `tests/test_zero_relay_review_task.py` for v2 identity/rendering/anti-replay regression;
- NEW `src/a_conductor/zero_relay_review_evidence.py`;
- NEW `tests/test_zero_relay_review_evidence.py`;
- this WO and its GLM prompt/checkpoint evidence.

Read-only dependencies may include:

- `src/a_conductor/zero_relay.py`;
- `src/a_conductor/execution_record.py`;
- `src/a_conductor/execution_store.py`;
- `src/a_conductor/execution_artifacts.py`;
- `src/a_conductor/zcode_runner.py`;
- `src/a_conductor/zcode_supervised_helper.py`;
- `src/a_conductor/supervised_execution.py`;
- `src/a_conductor/supervised_run_coordinator.py`;
- `src/a_conductor/review_mailbox_adapter.py`;
- existing production assembly/callers.

Forbidden without a fresh GPT scope expansion:

- scheduler semantics;
- provider/admission semantics;
- WorkerLease semantics;
- execution-store schema;
- artifact-service semantics;
- mailbox assignment/agent-id semantics;
- ReviewBus/ReviewBridge implementation;
- Phase D / GoalCloseout source;
- ZRA-3 / ZRA-4 source;
- live runtime/provider/credentials/processes;
- A-Wiki source or internal imports.

If a deterministic RED proves one narrow existing dependency must change, persist the reproducer and STOP for GPT scope adjudication instead of broad-refactoring.

## 5. Required archaeology before RED

Trace actual current production construction/call paths for:

1. `MaterializedReviewTask` / `DirectReviewRoute`;
2. `ParallelReadyTask` -> harness/backend selection for direct ZCode review;
3. `DurableExecutionRecord` creation and terminal transitions;
4. `ExecutionArtifactService` confinement/read semantics;
5. in-process `zcode_runner` report production;
6. supervised-helper report production and collection;
7. execution-store record reread after terminal state transition;
8. existing parser/schema helpers that can be reused;
9. `zero_relay.ReviewEvidence` and `classify_relay_decision` consumers;
10. any current production caller of `ReviewResultForwarder` or direct ReviewBus adapter.

Classify every seam `REUSE / WRAP / EXTEND / NOT_USED`.

Do not start source mutation until this archaeology proves the smallest implementation boundary.

## 6. RED-first matrix

Write deterministic failing tests before production implementation for at least:

### Protocol v2 identity/task

1. same author + same HEAD + v1 vs v2 => different contract/digest/task path/task SHA;
2. v1 artifact cannot bind a v2 route/result;
3. v2 render requires JSON-only exact response contract;
4. changing semantic schema/version changes identity-bearing bytes;
5. author identity/HEAD anti-replay from C0 remains intact;
6. existing v1 deterministic behavior remains regression-stable.

### Direct semantic result validation

7. exact ACCEPTED response -> exact `ReviewEvidence`;
8. exact REJECTED response -> `ReviewDisposition.REJECTED`;
9. malformed JSON;
10. duplicate JSON keys;
11. non-object root;
12. invalid UTF-8;
13. trailing/prefix prose or Markdown fence;
14. unknown schema;
15. wrong review contract ref;
16. wrong reviewed HEAD;
17. wrong review task SHA;
18. stale response from old HEAD;
19. result rebound to another author result/attempt/generation;
20. truthy/alias verdict values rejected;
21. unknown authority-like fields rejected;
22. oversized response / truncated artifact rejected;
23. excessive findings / oversized finding rejected.

### Durable execution/report binding

24. durable runtime `execution_id != route.dispatch_execution_id` is accepted only when WO226 handoff proves exact cross-binding through the same fingerprint/task/provider/admission/runtime identity;
25. report/runtime `execution_id` mismatch against the accepted WO226 durable execution identity fails closed;
26. reviewer execution equals author execution;
27. wrong worker/project/repo/worktree/branch/head/work-order fact;
28. nonterminal execution;
29. failed/cancelled/recovery/verification-required state cannot authorize ACCEPTED;
30. missing stdout/report refs/artifacts;
31. report unknown schema;
32. report execution id mismatch;
33. report task packet SHA mismatch;
34. report response byte-count mismatch;
35. report response SHA mismatch;
36. helper report path without `task_contract_ref` succeeds only when trusted record/route/WO226 handoff cross-binding proves contract identity;
37. in-process report with `task_contract_ref` mismatch fails closed;
38. report `EXIT_PENDING` cannot authorize review evidence;
39. `sha256(captured_raw) != artifact_slice.sha256` fails closed (TOCTOU discriminator);
40. artifact slice truncated or offset != 0 fails closed;
41. exact identical replay is deterministic.

### Authority fence

42. parser/composer cannot mutate execution/job/scheduler/provider/lease state;
43. no new mailbox agent mapping;
44. no A-Wiki internal import;
45. no new store/lifecycle authority;
46. findings cannot set ready/merge/retry/complete authority.

At least one test must be a non-vacuous pre-repair discriminator that fails on current main and passes only after the v2/C1 implementation.

## 7. Implementation target

Prefer two narrow responsibilities:

1. C0 protocol v2 support in `zero_relay_review_task.py` while preserving v1 behavior as immutable historical protocol;
2. a new pure/bounded `zero_relay_review_evidence.py` that validates one captured direct reviewer execution/result and returns existing `zero_relay.ReviewEvidence` only after every required identity/artifact/state cross-binding passes.

Suggested typed intermediate:

`ValidatedDirectReviewResult`

It must not be constructible from untrusted free strings alone. Its creation must occur only after durable artifact verification.

Keep semantic parsing pure once bytes/record/route are captured.

## 8. Adversarial/fault campaign after GREEN

Attack at least:

- byte mutation between report and stdout capture;
- byte mutation between artifact full-digest calculation and raw read;
- replay old response against new HEAD;
- replay same response against changed author result SHA/attempt/generation;
- report from another execution with same model/provider;
- helper vs in-process report-shape confusion;
- duplicate JSON keys where last-key-wins parser would otherwise hide conflict;
- Unicode edge cases and non-normalized but valid UTF-8 strings;
- path/ref traversal attempts through caller-provided artifact refs (must remain blocked by existing artifact authority);
- forged caller-created route/evidence-like objects where type/identity gates should reject;
- findings containing lifecycle-looking fields/strings;
- terminal-state/version rollover around execution-store reread;
- test-vacuity challenge showing a permissive prose parser would fail the new tests.

Prefer barriers/fault injection and captured immutable bytes over sleep timing.

## 9. Verification floor

After GREEN run, at minimum:

1. `tests/test_zero_relay_review_task.py`;
2. new `tests/test_zero_relay_review_evidence.py`;
3. `tests/test_zero_relay.py`;
4. `tests/test_execution_record.py`;
5. `tests/test_execution_store.py`;
6. `tests/test_execution_artifacts.py`;
7. relevant ZCode runner/helper/supervised execution/coordinator suites justified by actual imports/call path;
8. `tests/test_parallel_ready_execution.py`;
9. mailbox adapter suite as non-regression only if imported/read for archaeology;
10. Phase-A decision tests;
11. compile/import checks;
12. diagnostics on changed source/tests;
13. `git diff --check`;
14. strict UTF-8/no U+FFFD;
15. changed + untracked scope audit;
16. added-line credential/secret-like scan;
17. architecture/import fence;
18. hosted CI on frozen exact SHA;
19. independent exact-SHA R3 review by a non-author model/lane;
20. GPT exact-SHA adjudication before merge.

Do not rerun broad suites without a concrete dependency/call-path reason.

## 10. Long-shift loop

Use nested goals and durable checkpoints:

```text
G0 RECOVER / RE-PIN / CLAIM
G1 PRODUCTION ARCHAEOLOGY + REUSE MAP
G2 V2 IDENTITY/TASK RED
G3 V2 IDENTITY/TASK GREEN + ADVERSARIAL
G4 DIRECT RESULT RED
G5 DIRECT RESULT GREEN
G6 EXECUTION/REPORT ANTI-REPLAY + TOCTOU CAMPAIGN
G7 RELATED REGRESSION + STATIC/HYGIENE
G8 SELF-REVIEW / DIFF / AUTHORITY FENCE
G9 FREEZE EXACT SHA / PR / HOSTED CI
G10 DURABLE HANDOFF / STOP AT EXTERNAL GATE
```

After every meaningful mutation/campaign checkpoint:

- current Gx;
- repo/worktree/branch/base/HEAD;
- dirty/untracked state;
- changed paths;
- RED evidence;
- GREEN evidence;
- findings and severity;
- tests/outcomes;
- P0/P1/P2/P3 counts;
- external gate;
- exact next safe action.

Do not use chat memory as the only continuity layer.

## 11. Stop gates

Checkpoint and STOP immediately after the current atomic safe step on:

- WO221/WO223 archaeology disproves the need for WO223;
- WO225 or WO226 is no longer accepted/post-main verified, or their exact authority contract materially changes;
- current main/source semantics materially drift;
- overlap/claim conflict;
- required mutation outside released scope;
- need to change execution-store/artifact-service/scheduler/provider/lease semantics;
- ambiguous production report selection/binding that cannot be proven from current assembly;
- need to fabricate mailbox identity;
- required live credential/provider/runtime operation;
- hosted CI nonterminal/failure after freeze;
- independent review gate;
- GPT acceptance/merge/post-main gate;
- UNKNOWN authority.

Do not poll external gates and do not jump to Phase D/ZRA-3/ZRA-4 while blocked.

## 12. Acceptance boundary

WO223 candidate is ready for independent review only when all are true:

- v1 historical semantics remain unchanged;
- v2 explicitly versions the machine-readable semantic contract;
- direct result parser is strict, bounded and duplicate-key safe;
- accepted WO225 repaired route authority and accepted WO226 reviewer-execution handoff are exact predecessors;
- dispatch-context identity remains distinct from actual durable runtime execution identity and is cross-bound only through accepted WO226 evidence;
- durable record + report + exact captured stdout bytes + repaired route + WO226 handoff + author identity are cross-bound;
- both actual ZCode report producers used by the production path are handled truthfully without fabricated fields;
- TOCTOU-shaped digest/raw mismatch fails closed;
- no mailbox identity is invented;
- no second review/execution/store/lifecycle authority exists;
- exact `ReviewEvidence` is composed only from verified facts;
- relevant regression/adversarial/static gates are green;
- frozen SHA/PR/CI are recorded;
- non-author independent R3 review is pending/complete as applicable.

GLM implementation claim is not acceptance. GPT-5.6 Sol remains final integration/merge/release authority.
