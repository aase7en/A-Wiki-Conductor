# WO-P1-592 — STM-1B producer wiring to the Hook Bus core

Issue: #592
(P5 continuation under parent #547; STM-1A accepted/post-main per #547
closeout. Explicit user authorization for parallel continuation: #547
comment 5997303506, 2026-10-05.)
Class: CONTROL_PLANE_ONLY
Risk: R3 (shared event pipeline composition adjacent to control truth; bounded new-file scope)
Executor route: Windows ZCode + GLM-5.3 MAX primary session
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo547b-stm-producer`
Branch (bootstrap): `docs/wo-p1-547b-stm-producer-wiring`
Bootstrap base: `90cd18e26eef6ddb1409bf8f5c429611e073cf13` (= origin/main at bootstrap)

## Goal

Wire accepted producers to the accepted Hook Bus core (WO-P1-547 successor
boundary) without creating any new authority. The accepted producer seam
already exists and is unwired: `SQLiteLifecycleEvidenceService` accepts
optional `hook_context_factory` + `hook_observe_sink` collaborators
(both-or-neither, `HOOK_COLLABORATORS_INCOMPLETE` otherwise) and already
isolates hook-path failure as `OBSERVABILITY_DEGRADED` so control truth never
changes. `normalize_control_event` projects one authoritative `ControlEvent`
into a sanitized Hook Contract v1 OBSERVE envelope. `HookBus.accept` ingests
one wire envelope per call. This WO adds the missing bounded composition.

## READ_ONLY shaping evidence (2026-10-06, current main 90cd18e)

- `src/a_conductor/lifecycle_assembly.py:250-295` — injectable collaborator
  seam; `occurred_at` must equal `event.recorded_at`; any hook-path exception
  ⇒ `OBSERVABILITY_DEGRADED`, operation still succeeds.
- `src/a_conductor/control_hook_adapter.py` — pure
  ControlEvent→OBSERVE envelope projection; typed rejections; secret-marker
  rejection; only lifecycle_assembly references it in `src/`.
- `src/a_conductor/hook_bus.py:419-627` — `accept(bytes, HookIngressContext)`,
  dedupe/backpressure/caps, `drain`/`dispatch`, `end_session`.
- `src/a_conductor/hook_stm.py` — `HookStm.update/rebuild`, partitions,
  TTL/STALE/UNKNOWN, typed `StmError` (`STM_*` codes).
- grep proof: no construction site passes `hook_observe_sink` anywhere
  (src/ or tests/); no `HookBus(` construction outside its own module — no
  existing accepted equivalent wiring exists (REUSE/NEW: REUSE seam+bus+stm;
  NEW one composition module only).

## Frozen source scope (mutation gate; RED-first before implementation)

- NEW `src/a_conductor/hook_producer_wiring.py`
- NEW `tests/test_hook_producer_wiring.py`
- (this WO doc under the docs bootstrap)

## Frozen contract

1. `ControlEventProducerBinding` factory:
   `bind_control_event_producer(bus, *, device_id, source_version, host_os, session_id, serializer=json.dumps)` returns exactly `(hook_context_factory, hook_observe_sink)` compatible with `SQLiteLifecycleEvidenceService`'s collaborator contract.
2. `hook_context_factory(event)` returns a `ControlHookContext` with
   `occurred_at=event.recorded_at` (timestamp-consistency invariant) and the
   explicitly supplied device/source-version/host-os only; no ambient
   inference; invalid/missing `recorded_at` raises so the evidence service
   records `OBSERVABILITY_DEGRADED`.
3. `hook_observe_sink(envelope)` performs exactly one `bus.accept` of the
   serialized sanitized envelope under a `HookIngressContext(source="a-conductor",
   device_id, session_id)`. Admission outcomes are recorded for observability
   (bounded last-outcome view) and NEVER raise into the control path:
   `DUPLICATE`, `HOOK_BACKPRESSURE`, and every `HookBusError` are swallowed
   after being recorded; transport of the envelope into the bus is the only
   side effect.
4. No persistence, no scheduler, no retry, no network/process/Git side
   effects, no second store, no authority: bus/STM remain derived,
   bounded, rebuildable; authoritative `SQLiteControlEventLog` truth is never
   mutated by any wiring or bus outcome.

## Failure model (RED matrix before implementation)

- duplicate producer delivery → second accept classifies DUPLICATE; sink does not raise
- out-of-order sequence → bus marker path; sink does not raise
- producer/serialize exception → never propagates to the control path (evidence-service degraded contract holds)
- malformed/oversized envelope → typed bus rejection recorded, not raised
- backpressure (caps exhausted) → HOOK_BACKPRESSURE recorded, not raised; bus health degrades
- stale/unknown → HookStm read after wiring yields STALE/UNKNOWN per its own contract (composition preserves it)
- restart/rebuild → fresh bus + replay of envelopes reconstructs equivalent derived state; authoritative log remains the rebuild source
- authority contradicting STM → control operation result unchanged (success + evidence_ref) in every wiring-failure case
- context/ingress invalid (oversized ids, control chars) → typed rejection recorded, not raised
- collaborator contract: factory result satisfies both-or-neither and occurred_at consistency (integration row against the real `SQLiteLifecycleEvidenceService`)

## Non-goals

- Any mutation to `lifecycle_assembly.py`, `control_hook_adapter.py`,
  `hook_bus.py`, `hook_stm.py`, or their existing tests (accepted surfaces
  stay untouched; defects require a separate RED proof).
- Production composition-root hookup (desktop app constructing the wiring),
  P6 MON-1 consumers, P7 UI-1, P8 ACT-1 command gateway — separate scopes.
- durable STM database; command/mutation gateway; web/extension API.

## Acceptance criteria

1. RED-first: focused suite fails against the absent module first, then GREEN.
2. Targeted: `tests/test_hook_producer_wiring.py` green; related unmodified
   `tests/test_hook_bus.py` + `tests/test_hook_stm.py` +
   hook-contract/control-hook regressions green (exact set frozen at claim).
3. Hygiene: compileall, `git diff --check`, strict UTF-8, added-line secret
   scan 0 hits; changed files exactly the frozen new-file scope.
4. Exact candidate SHA frozen; independent exact-SHA R3 review (separate
   session; Codex GPT-6.1 Sol when quota admits, else separate GLM read-only
   lane) P0/P1/P2=0; hosted exact-head CI SUCCESS; expected-head merge; fresh
   post-main CI verified; claim released.

## Claim

Claim ID: `WO-P1-592-STM1B-PRODUCER-WIRING-WIN-001`
Posted to Issue #592 at bootstrap; released only after post-main verification
or explicit supersession.
