# GLM / WO-P1-201 — ZRA-2 Phase C trusted review-evidence composition

STATUS: HOLD — DO NOT IMPLEMENT UNTIL RELEASED

This packet is intentionally pre-shaped so a later ZCode GLM-5.3 invocation can begin immediately after Phase B acceptance without rediscovering the architecture. It is not current mutation authority.

## External release gate

Before any source/test mutation, verify ALL of the following from durable Git/GitHub authority:

1. WO-P1-195 / ZRA-2 Phase B exact candidate has an independent GPT/integrator acceptance verdict.
2. Phase B is merged and any required post-main verification is green.
3. GitHub Issue #214 explicitly marks Phase C `NEXT_READY`.
4. A fresh Phase-C implementation claim names exact owner, branch, worktree, mutable paths, forbidden paths, base SHA, and dependencies.
5. The claimed worktree is isolated, clean except for explained owned changes, and has no overlapping mutable lane.

If any condition is false or unknown:

`BLOCKED_EXTERNAL_AUTHORIZATION`

Write/checkpoint that state and STOP. Do not create a source branch, do not edit tests/source, and do not reinterpret this packet as authorization.

## Canonical objective

Compose existing trusted review/mailbox/ReviewBridge evidence into the existing `zero_relay.ReviewEvidence` vocabulary without importing A-Wiki internals and without creating a second review lifecycle.

This is an identity/evidence adapter, not a review engine.

## Mandatory source pointers after release

Read these symbols first at the released base SHA:

- `src/a_conductor/zero_relay.py`
  - `ResultIdentity`
  - `ReviewEvidence`
  - `ReviewDisposition`
  - `classify_relay_decision`
- `src/a_conductor/agent_change_packets.py`
  - `AgentMailboxAssignment`
- `src/a_conductor/review_mailbox_adapter.py`
  - `ReviewMailboxResult`
  - `ReviewMailboxResultReader.read`
  - `ReviewResultForwarder.forward`
  - `build_review_result_forwarder`
- `src/a_conductor/execution_record.py`
  - `DurableExecutionRecord`
  - `ExecutionProcessState`
  - `TransportState`
- related tests:
  - `tests/test_zero_relay.py`
  - `tests/test_review_mailbox_adapter.py`
  - execution-record/store tests actually touched by the chosen contract

Read `docs/work-orders/WO-P1-201-zra2-phase-c-review-evidence-gate.md` before designing the API.

## Critical preflight fact

Do NOT confuse these identities:

- `AgentMailboxAssignment.result_ref` is the review-result artifact location.
- `zero_relay.ResultIdentity.result_ref/result_sha256` is the AUTHOR execution result being reviewed.

The review artifact hash is not authority for the author result hash.

`ReviewMailboxResult` is deliberately sanitized and insufficient by itself to construct `ReviewEvidence`; it does not carry authoritative author result ref/hash, attempt, generation, reviewer execution identity, or task_contract_ref.

Therefore the Phase-C adapter must compose independent trusted typed inputs rather than trusting free-form reviewer output.

## Preferred bounded shape

After release, prefer a new small module rather than changing multiple established authorities:

- candidate source: `src/a_conductor/zero_relay_review_evidence.py`
- focused tests: `tests/test_zero_relay_review_evidence.py`

The exact names may change only if the released implementation work order says so.

A reasonable semantic input set is:

- author `ResultIdentity`;
- trusted `AgentMailboxAssignment`;
- validated `ReviewMailboxResult`;
- durable reviewer `DurableExecutionRecord`;
- existing trusted ReviewBridge/forward outcome if needed to prove ingest acceptance.

Do not introduce another database/store/scheduler/reviewer bus.

## Authority-binding requirements

Fail closed unless the selected contract proves all required bindings:

1. the mailbox assignment is the exact review task expected for this author result;
2. the review result passed `ReviewMailboxResultReader` binding checks;
3. task/provider/model/head/task hash are consistent with the trusted assignment;
4. the author `ResultIdentity` remains exact and unchanged;
5. task_contract_ref, author result_ref/result_sha256, attempt_id, and generation come from the author result/trusted task contract — never reviewer prose;
6. reviewer_execution_id comes from the durable reviewer execution record;
7. reviewer execution is terminal/usable under existing execution semantics;
8. reviewer execution is distinct from author_execution_id;
9. disposition is mapped through a bounded typed vocabulary only;
10. unknown/ambiguous/malformed verdict cannot become ACCEPTED;
11. reviewer-supplied `ready`, `merge`, `ci`, `retest`, or similar convenience fields never become authority;
12. if ReviewBridge confirmation is required by the selected architecture, lack/mismatch of confirmation fails closed;
13. same review evidence cannot be replayed onto a different author result identity.

If the existing review task packet/assignment cannot prove that it was generated for the exact author result digest + attempt + generation, do NOT invent the binding. Report:

`DESIGN_GAP_RESULT_BINDING`

with exact source evidence and STOP for integrator adjudication.

## RED-first campaign

Before implementation, add focused tests that fail on the released base for the missing composition seam. Cover at least:

- accepted independent review -> exact `ReviewEvidence`;
- bounded rejected disposition;
- malformed/raw-string/truthy disposition rejected;
- task hash drift;
- provider/model/head mismatch through existing adapter;
- author result_ref drift;
- author result_sha256 drift;
- attempt mismatch;
- generation mismatch;
- author execution id == reviewer execution id;
- reviewer execution still RUNNING/STARTING/UNKNOWN/RECOVERY_REQUIRED;
- reviewer durable record bound to the wrong job/task/work order when those bindings are available;
- review artifact hash cannot substitute for author result hash;
- untrusted ready/merge/retest/ci fields ignored;
- missing/mismatched ReviewBridge confirmation if used;
- identical input is deterministic;
- an accepted review for result A cannot authorize result B;
- no scheduler/provider/lease/job mutation from the pure composition seam;
- no A-Wiki internal imports;
- no new review persistence/lifecycle authority.

Include positive controls beside negative cases.

## Implementation constraints

- Reuse typed classes and validators already in the repo.
- Prefer a pure function / frozen dataclass boundary.
- Stable typed error codes; do not leak raw exception text.
- No retry loop.
- No network/provider call.
- No live DB or Worker/runtime mutation.
- No A-Wiki mutation.
- No source changes outside the released work order's mutable scope.
- No weakening existing tests.

## Verification

At minimum after GREEN:

1. focused Phase-C tests;
2. `tests/test_zero_relay.py`;
3. `tests/test_review_mailbox_adapter.py`;
4. only execution-record/store tests justified by imports/call paths;
5. compile/import check;
6. `git diff --check`;
7. strict UTF-8 / no U+FFFD;
8. changed-path scope audit including untracked files;
9. added-line secret-like scan;
10. exact candidate SHA freeze + result/checkpoint;
11. push Draft PR;
12. STOP at hosted CI or independent acceptance gate.

Do not self-accept or self-merge.

## Required handback

Write the child work-order result named by the released implementation packet. It must include exact:
- base SHA;
- candidate SHA;
- changed files;
- RED/GREEN evidence;
- tests/results;
- P0/P1/P2/P3 self-audit;
- any `DESIGN_GAP_*`;
- PR URL;
- `merge_performed=false`;
- next safe action.

Then stop at the first external gate and resume later from durable state.
