# WO-P1-201 — ZRA-2 Phase C trusted review-evidence composition gate

Status: PREPARED / BLOCKED_PHASE_B_ACCEPTANCE / NO SOURCE MUTATION AUTHORIZED
Parent: WO-P1-165 / Issue #214 / ZRA-2 Phase C
Base: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Branch: `docs/wo-p1-201-zra2-phase-c-gate`
Owner: GPT-5.6 Sol integrator
Preferred future executor: ZCode GLM-5.3 after explicit release
Risk: R3 identity/review-authority boundary

## Dependency gate

Do not implement Phase C until all are true:
- WO-P1-195 Phase B exact candidate independently accepted;
- required Phase-B merge/post-main verification complete;
- Issue #214 explicitly marks Phase C NEXT_READY;
- fresh implementation claim/worktree/mutable-scope gate is published.

Until then: `SAFE_TO_MUTATE_PHASE_C=NO`.

## Canonical Phase-C objective

From WO-P1-165:
compose existing review adapter / trusted ReviewBridge evidence without importing A-Wiki internals and without creating a second review lifecycle.

Phase C is a composition seam only. It does not own reviewer execution, provider dispatch, A-Wiki review lifecycle, job state, merge, retry, lease, or scheduler authority.

## Reuse authority map

Existing authorities to reuse unchanged:
- `zero_relay.ResultIdentity` — exact author task/result/attempt/generation/author execution identity;
- `zero_relay.ReviewEvidence` — exact review evidence vocabulary consumed by Phase A decision logic;
- `AgentMailboxAssignment` — bounded review task/mailbox assignment identity;
- `ReviewMailboxResultReader` — validates trusted review result task/provider/model/head/task hash and strips untrusted ready/merge/retest fields;
- `ReviewResultForwarder` / A-Wiki ReviewBridge boundary — existing trusted review ingest boundary;
- `DurableExecutionRecord` — durable reviewer execution identity/state from existing execution authority.

Do not create a second ReviewBus, ReviewBridge, execution store, reviewer store, or acceptance state machine.

## Gap proven during GPT preflight

`ReviewMailboxResult` alone is intentionally insufficient to construct `zero_relay.ReviewEvidence`.
It carries task/provider/model/reviewed-head/task-sha + sanitized verdict/findings, but does not carry authoritative:
- author `result_ref` / `result_sha256`;
- attempt_id;
- generation;
- reviewer_execution_id;
- task_contract_ref.

`AgentMailboxAssignment.result_ref` points to the review result artifact; it must NOT be confused with the author result being reviewed.

Therefore Phase C must compose independent trusted inputs rather than letting reviewer payload mint authority fields.

## Proposed composition contract

Preferred new pure/bounded seam after release:
`src/a_conductor/zero_relay_review_evidence.py`

Preferred focused tests:
`tests/test_zero_relay_review_evidence.py`

Exact API may be refined after fresh re-pin, but the semantic inputs should be existing typed authorities such as:
- author `ResultIdentity`;
- trusted `AgentMailboxAssignment`;
- validated `ReviewMailboxResult`;
- durable reviewer `DurableExecutionRecord`;
- explicit trusted ReviewBridge outcome only if needed to map verdict/disposition.

No raw dict/string from reviewer output may directly set `task_contract_ref`, author result hash, attempt, generation, reviewer execution identity, or merge/ready authority.

## Required cross-binding

Before constructing `zero_relay.ReviewEvidence`, fail closed unless all applicable facts agree:
- review assignment task/provider/model/head/task packet hash is trusted by existing adapter;
- review result is bound to that exact assignment;
- author ResultIdentity remains the exact result under review;
- review task/evidence is provably bound to that author result identity rather than merely sharing task prose;
- reviewer durable record execution_id is the reviewer_execution_id;
- reviewer execution is terminal/usable under existing execution-state semantics;
- reviewer execution is distinct from author_execution_id;
- attempt and generation come from author ResultIdentity / trusted task contract, never reviewer prose;
- disposition is mapped only from an accepted bounded verdict vocabulary;
- UNKNOWN/ambiguous/malformed verdict becomes typed fail-closed/recovery, never ACCEPTED.

If current review task packet does not durably bind the author result digest/attempt/generation, do not invent that binding in Phase C. Report `DESIGN_GAP_RESULT_BINDING` and stop for integrator scope decision.

## RED-first matrix for future implementation

Required cases at minimum:
1. valid accepted independent review produces exact `ReviewEvidence` matching `ResultIdentity`;
2. rejected review maps to bounded non-accepted disposition;
3. malformed/raw truthy disposition rejected;
4. task hash mismatch fails closed;
5. provider/model/head mismatch fails closed via existing adapter;
6. author result_sha drift fails closed;
7. author result_ref drift fails closed;
8. attempt mismatch fails closed;
9. generation mismatch fails closed;
10. reviewer execution id equals author execution id fails independence;
11. reviewer execution unknown/running/recovery-required cannot authorize ACCEPTED;
12. reviewer execution record from wrong job/task/work order fails closed if those bindings exist in the selected contract;
13. review artifact hash must not be substituted for author result hash;
14. reviewer payload `ready=true`, `merge=true`, or similar prose never becomes authority;
15. missing ReviewBridge confirmation fails closed if the selected contract requires forwarding/ingest;
16. duplicate identical inputs remain deterministic;
17. same reviewer verdict applied to a different author result is rejected;
18. no filesystem/provider/scheduler/lease/job mutation from the pure composition function;
19. no import of A-Wiki internals;
20. no second review lifecycle or persistence store.

## Verification ladder

After future source authorization:
- focused Phase-C tests;
- `tests/test_zero_relay.py`;
- `tests/test_review_mailbox_adapter.py`;
- execution-record/store tests justified by consumed record fields;
- AgentMailboxAssignment tests;
- related review/closeout tests only where call paths are actually affected;
- compile/import;
- diff/scope/UTF-8/U+FFFD/secret-like added-line checks;
- exact-SHA independent review + hosted CI.

## Forbidden scope

Until explicitly expanded, future Phase-C child must not modify:
- A-Wiki repository or internals;
- review_mailbox_adapter behavior unless a proven contract gap requires a separately adjudicated extension;
- zero_relay Phase-A decision semantics;
- Phase-B materializer;
- ZRA-3 / ZRA-4 source;
- Worker runtime / launcher / provider credentials / live DB;
- scheduler/job/lease/provider/retry authorities.

## Acceptance boundary

Phase C is complete only when one exact author result + one exact independent trusted review can be converted into `zero_relay.ReviewEvidence` without caller-forged authority fields and without a duplicate review lifecycle.

Completion of this docs packet does not release source mutation.
