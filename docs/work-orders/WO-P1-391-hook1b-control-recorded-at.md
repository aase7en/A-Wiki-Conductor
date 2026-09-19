# WO-P1-391 — HOOK-1b Persisted Control-Event Timestamp Surface

Status: CLAIMED / GOVERNANCE_BOOTSTRAP
Issue: #391
Identity schema: GITHUB_ISSUE_V1
Risk: R3 — control-event read-model interface
Topology: CONTROL_PLANE_ONLY

## Binding

- repo: aase7en/A-Wiki-Conductor
- worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo391-control-recorded-at
- branch: feat/wo-p1-391-control-recorded-at
- base: 3067bd32569d7bcd6cc41e18c1c97a9a4f7db9c9
- claim: WO-P1-391-HOOK1B-CONTROL-RECORDED-AT-001
- integrator: GPT-5.6 Sol
- preferred implementer: GLM-5.3 MAX
- predecessor: WO-P1-383 HOOK-1 pure control normalizer (accepted)
- roadmap: docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md

## Reuse classification

EXTEND only the existing control event read model.

The SQLite schema already owns the durable timestamp column:
`control_events.recorded_at TEXT NOT NULL`.

Do not add:
- a new timestamp column/store/table;
- another clock/event log;
- Hook emission or a Hook Bus;
- lifecycle callback wiring;
- task/claim/retry/review/acceptance authority.

## Goal

Surface the exact already-persisted `recorded_at` value on store-produced
`ControlEvent` objects so later Hook wiring can use durable event time rather
than synthesize a second observation time after the write.

This Work Order intentionally stops before lifecycle Hook emission.

## Compatibility contract

`ControlEvent` gains one final optional field:

`recorded_at: str | None = None`

The default is required so existing direct construction such as:

`ControlEvent(event_id, event_type, worker_id, project_id)`

continues to work without modification. Directly constructed legacy/test values
therefore have unknown timestamp (`None`), not invented time.

Store-produced values:
- `append()` MUST return the exact `recorded_at` string inserted into SQLite;
- `get()` MUST select and return the persisted value exactly;
- `list_recent()` MUST select and return each persisted value exactly;
- append -> get -> list round trips preserve byte-for-byte timestamp equality;
- no timestamp conversion to Hook RFC3339-Z occurs here; later projection may
  normalize `+00:00` to `Z` under its own accepted Work Order.

## Truth / failure rules

- persisted database value is factual authority for store-produced event time;
- do not recompute time on get/list;
- do not infer missing legacy timestamps;
- existing `recorded_at NOT NULL` schema remains unchanged;
- malformed historical DB values, if any, are surfaced as stored by this narrow
  read-model step; validation/normalization belongs to the Hook projection boundary.

## Mutable scope ONLY

- src/a_conductor/control_events.py
- tests/test_control_events.py
- this Work Order

Everything else read-only.

## Forbidden

- SQLite schema/table migration
- control_hook_adapter.py or its tests
- lifecycle_assembly.py / lifecycle coordinator/runtime wiring
- A-Faster/A-FastTask
- WO386/WO389
- CURRENT-WORK/handoff/COLLAB/PROJECT-PLAN
- reset/clean/stash/rebase/force/history rewrite

## RED-first acceptance

Before production mutation add failing tests proving:
1. append result lacks access to the actual persisted timestamp;
2. get/list do not currently carry recorded_at;
3. direct four-positional-field ControlEvent construction remains valid after the
   intended interface change;
4. DB schema remains exactly the same five columns.

Prefer checking persisted equality by reading the row directly from SQLite after
append rather than asserting a fragile wall-clock interval.

## GREEN verification

- python -m pytest -q tests/test_control_events.py
- python -m pytest -q tests/test_control_hook_adapter.py tests/test_lifecycle_assembly.py
- python -m py_compile src/a_conductor/control_events.py
- git diff --check
- exact scope / UTF-8 / U+FFFD / secret scan
- PR CI + independent exact-SHA review before merge
- post-main focused verification

## Next dependency

Only after this interface is accepted may a separate Work Order wire lifecycle
event append -> explicit ControlHookContext -> non-authoritative OBSERVE sink.
That later wiring must define degradation reporting and prove that observability
failure cannot block otherwise-safe lifecycle execution.

## Replay safety

Recover pointer/process/result/Git before redispatch.
RUNNING never redispatches.
TERMINAL_UNHARVESTED is harvested first.
