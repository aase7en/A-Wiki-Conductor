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
