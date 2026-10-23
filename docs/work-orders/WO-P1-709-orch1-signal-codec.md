# ORCH-1/1 Signal Codec

Issue: #709

Status: AUTHOR_VERIFIED / READY_FOR_INDEPENDENT_REVIEW; not runtime acceptance.
Risk: R3 / CONTROL_PLANE_ONLY (closed internal serialized contract).
Owner: `ses_e95d401a4ffetSwLcX7fm5kOR2`, AUTHOR only.
Claim: ORCH-1-1-CODEC-001 / issuecomment-6372749346.
Base: `8edb3c5` (fresh origin/main, includes foundation design PR710).
Worktree: `A:\GitHub\_worktrees\AWC-orch1-codec`.
Branch: `feat/orch1-signal-codec`.
Device: `ff685af5-9031-4b3b-84ff-61dc8f1a840c`.

## Scope And Authority

Explicit task authorizes this codec slice only, commit and push, NO PR/merge.
Mutable allowlist: this WO, `src/a_conductor/orchestration.py`,
`tests/test_orchestration.py`. No listeners, stores, registration, commands,
authority readers, task canonicalization, authentication, network or file I/O.
No source exists at base at either proposed path; design claim is released.
Reuse classification: EXTEND package with pure internal DTO, no new coordinator.
Shared CURRENT-WORK.md, handoff.md and COLLAB.md remain integrator-owned;
this WO and the driving issue carry checkpoints for integrator fold-back.
Already-delegated author route: GLM_OFFLOAD=NOT_BENEFICIAL, no provider calls.

## Frozen Codec Contract

Latest explicit task overrides the design's proposed envelope and bounds:
six required keys `signal_type`, `task_ref`, `source`, `timestamp`, `payload`,
`metadata`; five lowercase kinds including `outcome`; UTF-8 <=65536 bytes;
container nesting <=32 counting the root object as level 1.
No compatibility decoder for the unshipped proposed design envelope.

`task_ref` and `source` are nonempty opaque printable ASCII refs <=128 chars;
refs are not resolved or canonicalized here. `timestamp` is an extended ISO-8601
date-time with seconds and an explicit timezone (Z or offset), <=40 chars.
Producer time is not freshness authority. Optional keyword `expected_source`
on decode checks a separately supplied bound reference, not authentication.

Payload uses the design's closed reference-only per-kind schema:
- enqueue: target, intent_ref, trigger, plus parent_binding_ref for PARENT_QUEUE
  OR ready_plan_ref and task_map_ref for WORKER_BATCH.
- replay: enqueue fields plus recovery_evidence_ref and prior_submission_ref
  for PARENT_QUEUE OR prior_execution_ref for WORKER_BATCH.
- utilization: census_ref, ready_set_ref, activation_ref, provider_observation_ref.
- lifecycle: hook_event_ref, subject_ref, observation_ref.
- outcome (task extension): decision, reason_code, evidence_refs; optional
  submission_ref or execution_ref (mutually exclusive), observability_degraded.
  Decisions are OBSERVED_ONLY, NO_ACTION, DENIED, RECONCILIATION_REQUIRED,
  SUBMISSION_OBSERVED, DISPATCH_OBSERVED; labels confer no authority.

All refs <=256 printable ASCII chars. Metadata is a closed optional provenance
object: correlation_ref, binding_ref, producer_ref, audit_ref, evidence_refs.
Evidence lists contain <=16 refs, no arbitrary nested objects/raw commands.
Metadata is untrusted provenance, not an authority receipt.
No numeric values are needed by this schema: reject numeric JSON tokens before
conversion, including huge ints/exponents and NaN/Infinity. Reject lone surrogates,
unknown keys at every object level, missing keys, coercions and non-exact types.
Encode revalidates mutable dictionaries on every call; frozen dataclass does not
claim deep immutability. Deterministic sorted compact ASCII-escaped JSON bytes.

## Failure Model And Verification

Bound byte length before decode; lexical string-aware container-depth scan before
JSON parse avoids decoder recursion. Duplicate-key hook applies at every depth.
Encoded input is prevalidated with bounded traversal before JSON serialization.
All invalid inputs become OrchestrationError with bounded reason code only;
no raw input or parser exception is exposed. No effect can follow decode here.

Required codes: SIGNAL_TYPE_UNKNOWN, SIGNAL_MISSING_KEY, SIGNAL_DUPLICATE_KEY,
SIGNAL_DEPTH_EXCEEDED, SIGNAL_SIZE_EXCEEDED, SIGNAL_ENCODING_INVALID.
Additional closed failure reasons: SIGNAL_JSON_INVALID, SIGNAL_UNKNOWN_KEY,
SIGNAL_VALUE_INVALID, SIGNAL_SOURCE_MISMATCH.

Acceptance: RED-first round-trips for all kinds and both effect targets;
malformed/duplicate/unknown/missing/type/numeric/UTF8/surrogate/time/source
negative matrix; exact byte and nesting bounds; deterministic encoding;
cycles and invalid DTOs fail typed; fresh import with guarded write/network/
process effects proves module body inert. No live-system testing needed.
Run focused codec suite, work-order identity, directly related guard/HookBus
tests, diff/UTF8/scope checks. Independent exact-SHA R3 review and hosted CI
are later integrator gates, not claimed by AUTHOR. No PR/merge.

## Checkpoint

Bootstrap complete; full mutation gate rechecked against clean isolated base,
sole issue claim and exact three-file allowlist. Only those three paths changed.

RED evidence: focused suite collection failed with ModuleNotFoundError before
source existed. First GREEN: 63 tests. Extended timestamp challenge reproduced
`+01:99` normalization (1 failed / 75 passed); strict offset grammar repaired it.
Duplicate numeric-key challenge reproduced premature SIGNAL_VALUE_INVALID
(1 failed / 77 passed); numeric hooks now discard tokens without conversion
to a schema-forbidden null, so duplicate detection runs before value validation.
No numeric position or null value is accepted by this closed schema.

Final verification command (2026-10-23 UTC):
`python -B -m pytest -q -p no:cacheprovider tests/test_orchestration.py tests/test_work_order_identity.py tests/test_codex_queue_submission_guard.py tests/test_a_faster_utilization_guard.py tests/test_hook_bus.py tests/test_hook_stm.py`

Result: **392 passed**, including **78 codec cases**, 33 work-order identity
cases and 281 related cases. Fresh guarded subprocess import blocks writes,
network/process creation and module-initiated file reads. Its `-c` probe sets
`__file__` explicitly because this interpreter's import instrumentation requires
it; no production import workaround was added. `-B` suppresses incidental pyc
writes by Python's loader, not codec behavior. Importing source necessarily
lets the loader read source; module body performs no file I/O.

No source caller/registration, production effect or live-runtime proof is claimed.
Independent exact-SHA review and hosted CI are NOT_RUN, retained as integrator
gates. AUTHOR delivery stops after commit/push and issue checkpoint, no PR/merge.
Next safe action: integrator reads pushed exact HEAD, independently reviews the
slice-local outcome/metadata closure and failure matrix before accepting /1.
Keep branch/worktree for review; no cleanup is authorized.
