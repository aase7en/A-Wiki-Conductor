# WO-P1-383 — HOOK-1 A-Conductor Control Event Normalization Foundation

Status: CLAIMED / GOVERNANCE_BOOTSTRAP
Issue: #383
Identity schema: GITHUB_ISSUE_V1
Risk: R3 — contract/runtime boundary
Topology: CONTROL_PLANE_ONLY

## Binding

- Authority repo: aase7en/A-Wiki-Conductor
- Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo383-hook1-control-normalization
- Branch: feat/wo-p1-383-hook1-control-normalization
- Base: 6c49b6d1168372337dac3a18e6894c69436d6f8b
- Claim: WO-P1-383-HOOK1-CONTROL-NORMALIZATION-001
- Integrator: GPT-5.6 Sol
- Preferred bounded implementer: GLM-5.3 MAX
- Planning authority: docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md P2 / HOOK-1
- Contract dependency: accepted Hook Contract v1 from WO-P1-258

## Reuse classification

EXTEND existing A-Conductor event/lifecycle seams:
- src/a_conductor/control_events.py
- lifecycle evidence service / existing ControlEvent authority
- accepted Hook Contract v1

Do NOT add another event store or mutate SQLiteControlEventLog/table/schema.
Do NOT wire runtime/lifecycle side effects in this micro-step.

## Goal

Add the smallest pure normalization adapter that converts one existing
authoritative ControlEvent plus explicit observed Hook context into one valid
Hook Contract v1 OBSERVE envelope.

This is a projection/adapter only. It does not create durable truth, publish to
a Hook Bus, mutate task state, or enforce a GUARD.

## Architecture decisions

1. Existing production ControlEvent IDs are `event-<uuid4hex>`. Normalize
   them deterministically to `hk-<same 32 hex>`. Re-projecting the same
   ControlEvent therefore returns the same normalized semantic-event identity
   without another identity store. Nonconforming legacy/custom IDs fail typed.
2. Existing lifecycle actions START/STOP/RESTART/RELEASE map to:
   `control.start.after`, `control.stop.after`,
   `control.restart.after`, `control.release.after`.
   Unknown event types fail typed; never invent vocabulary.
3. Normalized class is OBSERVE, phase `after`, domain `control`, source
   `a-conductor`, privacy INTERNAL. This micro-step emits no GUARD, COMMAND,
   ADVISORY or adapter-capability payload.
4. ControlEvent does not expose its SQLite `recorded_at`. Therefore
   `occurred_at`, `source_version`, `device_id`, and `host_os` are
   explicit observed inputs. Do not re-read or alter the event store.
5. `worker_id` and `project_id` MUST NOT be inferred as Hook
   `lane_id`, `task_id`, or `work_order`. Those and repo/claim/execution
   context are emitted only when supplied explicitly by an authoritative
   caller context.
6. No source+sequence dedupe fallback. No sequence is invented.
7. Production source must not add a jsonschema dependency. Tests may validate
   generated envelopes against the accepted JSON Schema using the existing
   test-only jsonschema dependency.
8. Unknown/invalid inputs fail with bounded typed normalization error codes.
   Adapter errors do not mutate existing ControlEvent or task truth.

## Mutable scope

- NEW src/a_conductor/control_hook_adapter.py
- NEW tests/test_control_hook_adapter.py
- this Work Order

Everything else is read-only.

## Forbidden

- src/a_conductor/control_events.py
- src/a_conductor/lifecycle_assembly.py or any lifecycle wiring
- Hook Contract docs/schema/tests
- SQLite schema/table changes
- __init__.py/public export churn unless a later Work Order explicitly requires it
- A-FastTask/A-Faster
- WO381 / adapter WO375/WO376
- CURRENT-WORK / handoff / COLLAB / PROJECT-PLAN
- any Hook Bus/STM/Monitor store
- scheduler/task/claim/lease/retry/review/acceptance authority
- reset/clean/stash/rebase/force/history rewrite

## Failure model

- malformed `event-<uuidhex>` -> typed normalization failure;
- unsupported ControlEvent event_type -> typed normalization failure;
- invalid/non-UTC occurred_at -> typed normalization failure;
- invalid semver/device/host/context field -> typed normalization failure;
- explicit optional context that violates Hook bounds -> fail, never truncate;
- unknown optional context omitted, never inferred;
- secret/raw prompt/raw command fields have no input surface in this adapter.

## RED / GREEN acceptance

RED-first tests must prove at least:
1. same ControlEvent projected twice -> same `hk-` event_id;
2. malformed event id rejected;
3. START/STOP/RESTART/RELEASE exact mappings;
4. unknown event type rejected;
5. all generated envelopes validate against accepted Hook Contract schema;
6. required observed context invalid/missing fails;
7. worker_id/project_id are never silently projected as task/lane authority;
8. optional explicit task/lane/repo/claim facts pass through only when valid;
9. unknown optional facts remain omitted;
10. no sequence/dedupe/guard/command/adapter payload invented;
11. input objects remain unmodified;
12. control_events/lifecycle source blobs unchanged from dispatch base.

GREEN:
- focused tests pass;
- existing test_control_events + Hook Contract schema regression pass;
- diff/scope/UTF-8/U+FFFD/secret checks pass;
- no production jsonschema dependency added;
- independent exact-SHA R3 review + exact-head CI before merge.

## Replay safety

Recover pointer/process/result/Git before redispatch. RUNNING never
redispatches. TERMINAL_UNHARVESTED is harvested first. Model DONE is not
acceptance authority.

## Checkpoint — attempt-0001 READY_FOR_REVIEW (2026-09-19, GLM-5.3 MAX)

Status: implementation complete, awaiting independent exact-SHA R3 review +
exact-head CI. No merge/self-accept performed.

Scope actually mutated (exact): NEW `src/a_conductor/control_hook_adapter.py`,
NEW `tests/test_control_hook_adapter.py`, this Work Order checkpoint. Working
tree had no other changes (`git status --porcelain` showed only the two new
paths before this checkpoint edit).

RED evidence: `python -m pytest -q tests/test_control_hook_adapter.py` before
implementation -> collection error
`ModuleNotFoundError: No module named 'a_conductor.control_hook_adapter'`
(1 error), i.e. every test depended on the new module.

GREEN evidence (final): `tests/test_control_hook_adapter.py` 93 passed;
`tests/test_control_events.py tests/test_hook_contract_schema.py` 101 passed;
`tests/test_lifecycle_assembly.py` 8 passed; `py_compile` OK; `git diff
--check` clean; strict UTF-8 decode OK and zero U+FFFD in both new files;
`pyproject.toml` unchanged vs HEAD; production module contains no
`jsonschema` (test-only import, verified by source scan test and rg).

Identity proof: `event-<uuid4hex>` -> `hk-<same 32 hex>` is a pure
deterministic function; projecting the same ControlEvent twice returns the
identical envelope (tested, including full-envelope equality), so re-projection
needs no second identity store. Malformed/uppercase/wrong-prefix/wrong-length
source IDs fail `CONTROL_HOOK_EVENT_ID_MALFORMED`; no replacement identity is
invented.

Authority proof: envelope carries `lane_id`/`task_id`/`work_order` only when
the caller supplies them explicitly on `ControlHookContext`;
`worker_id`/`project_id` are never projected into any Hook authority field
(tested). No SQLite/schema/store mutation, no lifecycle wiring, no sequence,
no dedupe_key, no guard/command_request/adapter surface (tested key-set
bound). Forbidden-path blob equality vs dispatch HEAD
04b8d159aebf8cd957f31f177cd4b1cd5604bc52:
control_events.py 6cf1348d61319377085eb7902e3afa6205f05d01,
lifecycle_assembly.py 533682eeb7735c70a1d88b767e28bdce05a702ca,
__init__.py f0912298cb7712536f36b4b8920cc038e603d4ae,
hook-contract-v1.md 941f9731f9665fe109451a14cdc2b737555be99a,
hook-contract-v1.schema.json d176fd5e6393af6f5619fad372ad59aa858391ee,
test_hook_contract_schema.py c4dcaa36693c76bf274f7615236ef72c4e3ef53c,
test_control_events.py 4a2dd2846499c142722fd70b1c79259f39762217 — all equal.

Schema conformance proof: all four lifecycle mappings plus the
full-optional-context envelope and fractional-`occurred_at` envelope validate
with zero errors under `Draft202012Validator` against the accepted
`docs/contracts/hook-contract-v1.schema.json` loaded from disk in tests.
Adapter validation is schema-parity plus strict RFC3339 calendar/time bounds
(month 13 rejected), fail-not-truncate for every optional field, exact
`task_topology`/`host_os` enums, control-character/NUL/newline rejection, and
fake-secret-corpus/1 substring rejection on all emitted string values.

Secret scan verdict: only matches are the shared `fake-secret-corpus/1`
markers required by Hook Contract §11 for uniform leakage checks; no real
credentials touched.

Risks (bounded): adapter intentionally refuses nonconforming legacy/custom
source event IDs (fail-closed visibility loss, no task-truth impact); strict
calendar parsing is intentionally stricter than the JSON Schema pattern
(documented contract text says RFC 3339); `duration_ms`/`command_digest`/
`command_ref` are Hook fields deliberately not exposed in this micro-step.

Next: independent exact-SHA R3 review + exact-head CI on the pushed branch;
GPT integrator acceptance/merge.
