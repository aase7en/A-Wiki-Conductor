# WO-P1-394 — HOOK-1c lifecycle ControlEvent OBSERVE wiring

Status: CLAIMED / READY_FOR_IMPLEMENTATION
Issue: #394
Identity schema: GITHUB_ISSUE_V1
Risk: R3 — lifecycle / observability interface boundary
Topology: CONTROL_PLANE_ONLY

## Binding

- authority/execution repo: `A:\GitHub\A-Wiki-Conductor`
- worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo394-lifecycle-hook-observe`
- branch: `feat/wo-p1-394-lifecycle-hook-observe`
- base: `00323f7d50f8b0cb6f50cd38928a4d6cf4b98a45`
- claim: `WO-P1-394-HOOK1C-LIFECYCLE-OBSERVE-001`
- integrator: GPT-5.6 Sol
- preferred bounded implementer: GLM-5.3 MAX
- dependencies: accepted WO-P1-383 + accepted WO-P1-391

## Reuse classification

REUSE / WRAP only:
- `SQLiteLifecycleEvidenceService`
- `ControlEvent.recorded_at`
- `ControlHookContext`
- `normalize_control_event`
- existing `SerenaOperationResult.error_code` as bounded degradation signal

No Hook Bus, STM, monitor store, scheduler, task DB, claim authority, review authority,
or second event store is authorized.## Goal

After the authoritative lifecycle control event is durably appended, optionally
project that exact persisted event through the accepted HOOK-1 normalizer to an
injected OBSERVE sink.

The durable control event remains authority. The Hook path is secondary
observability only.

Required invariant:

`OBSERVABILITY_DEGRADED != EXECUTION FAILURE`

Control-event persistence failure keeps its existing lifecycle failure semantics.
Only context/normalization/sink failures after a successful append may degrade
without making an otherwise-safe lifecycle execution fail or require recovery.

## Settled composition seam

Extend `SQLiteLifecycleEvidenceService` with optional injected:
- a context factory producing `ControlHookContext` for the appended event;
- an OBSERVE sink callable receiving the normalized Hook envelope.

Default when no Hook collaborators are supplied: exact legacy behavior.

When Hook collaborators are present:
1. append the ControlEvent first;
2. require `event.recorded_at` to be present;
3. obtain context and require `context.occurred_at == event.recorded_at`;
4. normalize via existing `normalize_control_event`;
5. deliver only the validated normalized envelope to the sink.

No second timestamp may replace the persisted `recorded_at`.## Degradation semantics

If context construction, timestamp equality, Hook normalization, or sink delivery
fails after the ControlEvent append succeeds:
- do NOT roll back or rewrite the ControlEvent;
- do NOT turn the lifecycle step into FAILED / RECOVERY_REQUIRED;
- return the existing authoritative `event.event_id` as `evidence_ref`;
- return `SerenaOperationResult(success=True, error_code="OBSERVABILITY_DEGRADED")`;
- never deliver an invalid or secret-bearing envelope to the sink.

The lifecycle executor already treats `success=True` as successful; this Work
Order MUST include an end-to-end lifecycle assertion proving a throwing Hook sink
still permits otherwise-safe lifecycle completion.

No new degradation persistence/store is authorized in this micro-step.

## Mutable scope ONLY

- `src/a_conductor/lifecycle_assembly.py`
- `tests/test_lifecycle_assembly.py`
- this Work Order

Everything else read-only.

## Forbidden

- `src/a_conductor/control_events.py`
- `src/a_conductor/control_hook_adapter.py`
- Hook Contract docs/schema
- lifecycle planner/coordinator/executor semantics
- SQLite schema/migration
- A-Faster/A-FastTask
- SunDayRemoteMCP / WO-P1-389
- CURRENT-WORK / handoff / COLLAB
- new Hook Bus / STM / monitor persistence
- reset/clean/stash/rebase/force-push/history rewrite## RED-first acceptance

Before implementation prove failing regressions for:
1. successful append reaches injected sink as a normalized OBSERVE envelope;
2. sink `occurred_at` is byte-for-byte the persisted `ControlEvent.recorded_at`;
3. context timestamp drift is never emitted and degrades only observability;
4. normalization failure is never emitted and degrades only observability;
5. throwing sink degrades only observability;
6. fake-secret-corpus context is rejected before sink delivery;
7. control-event append failure retains existing failure/recovery semantics;
8. lifecycle execution remains COMPLETE when the Hook sink alone fails.

## GREEN

- existing lifecycle assembly tests remain green;
- existing control-event + control-hook-adapter tests remain green;
- new sink envelope validates against accepted Hook Contract schema;
- exact source event identity projection is preserved;
- no schema migration;
- no new authority/state store;
- diff/scope/UTF-8/U+FFFD/secret checks clean.

## R3 gates

- exact-SHA independent review;
- exact-head hosted CI;
- GPT-5.6 Sol acceptance;
- expected-head merge;
- post-main focused verification.

## Replay safety

Recover durable pointer/process/result/Git before redispatch.
RUNNING is never duplicated. TERMINAL_UNHARVESTED is harvested first.

Implementation must stop with `DECISION_REQUIRED` rather than widening scope
or inventing a new observability authority.

## Checkpoint — author attempt-0001 (2026-09-20)

- Implementer: GLM-5.3 MAX (Kilo), claim WO-P1-394-HOOK1C-LIFECYCLE-OBSERVE-001.
- Base: dispatch HEAD dad41a7005c0733575b710ea1c5048032950fc8f (clean worktree,
  branch feat/wo-p1-394-lifecycle-hook-observe).
- Implementation: `SQLiteLifecycleEvidenceService` gained optional injected
  `hook_context_factory` (ControlEvent -> ControlHookContext) and
  `hook_observe_sink` (envelope -> None) collaborators; both-or-none enforced at
  construction (`HOOK_COLLABORATORS_INCOMPLETE`). After a successful append:
  require `event.recorded_at`, require `context.occurred_at == event.recorded_at`
  (byte equality), normalize via existing `normalize_control_event`, then deliver
  the validated envelope to the sink. Any secondary failure (missing recorded_at,
  factory throw, timestamp drift, normalization failure, sink throw) returns
  `success=True, evidence_ref=event.event_id, error_code=OBSERVABILITY_DEGRADED`
  with no lifecycle FAILED/RECOVERY conversion; append failures keep the existing
  `success=False, recovery_required=True` semantics. Collaborators propagate
  additively through `LocalSerenaBackendFactory` and
  `build_local_lifecycle_coordinator`; defaults preserve legacy callers
  (`desktop_control.py` unchanged and green).
- RED evidence: 11 new tests failed before implementation with `TypeError:
  SQLiteLifecycleEvidenceService.__init__() got an unexpected keyword argument
  'hook_context_factory'` (runs/WO-P1-394/author/attempt-0001/red.md);
  8 pre-existing tests stayed green at RED.
- Timestamp authority: sink `occurred_at` is the exact persisted SQLite
  `recorded_at` read back from the database row (test monkeypatches only the
  test-scoped clock in `a_conductor.control_events` to persist Hook-contract
  `Z`-shaped timestamps; no production timestamp conversion). With the current
  production `+00:00` store format, delivery deterministically degrades
  (`OBSERVABILITY_DEGRADED`, sink not called) — the `+00:00`->`Z` projection
  remains deferred to its own Work Order per WO-P1-391.
- GREEN evidence: tests/test_lifecycle_assembly.py 19 passed;
  test_control_events.py + test_control_hook_adapter.py +
  test_lifecycle_assembly.py 174 passed; test_hook_contract_schema.py +
  test_work_order_identity.py 130 passed; related lifecycle/
  coordinator/executor/serena-operations 63 passed; test_desktop_control.py
  34 passed; py_compile OK; `git diff --check` clean.
- Proofs: exact scope = the 3 allowed paths; forbidden-path diff vs dad41a7
  empty (incl. control_events.py -> SQLite schema unchanged,
  control_hook_adapter.py, Hook Contract docs/schema, planner/coordinator/
  executor semantics, pyproject.toml); strict UTF-8 and zero U+FFFD in all 3
  mutated files; added-line secret scan: only the sanctioned
  `fake-secret-corpus/1` marker `sk-FAKE...` required by RED item 6; tests
  touch only tmp_path + monkeypatch (no network/runtime host side effects).
- Status: READY_FOR_REVIEW at the candidate commit on
  feat/wo-p1-394-lifecycle-hook-observe; no self-accept/merge. Next:
  independent exact-SHA R3 review + exact-head CI.