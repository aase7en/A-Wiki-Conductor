# WO-P1-478 — Durable Worker Recovery Lifecycle History (Phase A)

Status: CANDIDATE_READY / R3 / UNCOMMITTED FOR GPT-5.6 SOL VERIFICATION
Issue: #478
Issue lane: WO-P1-478 (Phase A)
Risk: R3 recovery-evidence trust boundary (additive history, no new authority)
Topology: CONTROL_PLANE_ONLY
Owner/integrator: GPT-5.6 Sol
Author claim: WO-P1-478-PHASEA-WINDOWS-001 (dispatch identity only; no acceptance authority)
Date: 2026-09-22

## Exact binding

- repo: `aase7en/A-Wiki-Conductor`
- worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo478-worker-recovery-history`
- branch: `feat/wo-p1-478-worker-recovery-history`
- base SHA at dispatch: `e6f96e7526742cfaca65917933fc299b21bf439e`
- pre-mutation state: clean tree at base SHA; no commits made on this lane

## Proven problem

`instance_recovery` stores only the latest snapshot per instance and
DesktopControlService recovery events are RAM-only, so auto-recovery can hide
prior outages. Additionally, a successful restart saved READY with the
pre-start observation timestamp, so actual recovery completion time/downtime
could not be reconstructed.

## Deliverable (implemented)

Append-only lifecycle-history evidence written by the existing
`ConnectorRecoveryCoordinator` (the single existing recovery state machine) at
its existing decision points, persisted atomically with the recovery snapshot
by `SQLiteSerenaConfigStore`, plus a bounded read API ordered by durable
sequence.

### Mutable scope (5 tracked files)

1. `src/a_conductor/connector_recovery.py`
2. `src/a_conductor/serena_config_store.py`
3. `tests/test_connector_recovery.py`
4. `tests/test_serena_config_store.py`
5. `docs/work-orders/WO-P1-478-worker-recovery-lifecycle-history.md`

Forbidden (READ-ONLY): every other tracked path, including
`desktop_control.py`, `instance_create.py`, launcher templates, live DB,
live Worker files, and runtime processes.

## Design

- New `instance_recovery_history` table: `sequence INTEGER PRIMARY KEY
  AUTOINCREMENT` (durable, never reused), `instance_name`, `kind`,
  `from_state`, `to_state`, `reason_code` (bounded, reused `_reason` shape),
  `restart_count`, `observed_at`. No commandline/token/credential/share URL/
  tool payload/model text or any secret-bearing field.
- Event kinds are labels of existing coordinator decision points only:
  `SUPPRESSED`, `MANUAL_START`, `READY_OBSERVED`, `UNKNOWN_OBSERVED`,
  `OUTAGE_OBSERVED`, `RECOVERY_STARTED`, `RECOVERY_READY`, `RECOVERY_FAILED`,
  `RECOVERY_CANCELLED`. No second state machine; states remain exactly
  `ConnectorRecoveryState`.
- Optional store seam `save_connector_recovery_history(record, events)`;
  detected once in the coordinator. Stores without it behave exactly as
  before (no fabricated history). SQLiteSerenaConfigStore writes snapshot
  upsert + history inserts in ONE transaction (atomic) and returns the record.
- Successful restart now re-samples the clock AFTER `start_instance` returns
  and stamps READY `updated_at` and the `RECOVERY_READY` event with that fresh
  post-start time, so outage duration is reconstructable when the clock
  advances during start.
- No-ops log nothing: quiescent READY refresh, suppressed-STOPPED repeat, and
  same-reason non-autostart STOPPED repeat still early-return before any save,
  so they append zero history events.
- `clear_instance_flags`/`clear_connector_recovery` semantics unchanged for
  the snapshot; history rows deliberately survive (append-only evidence).
  Growth is bounded by transitions, which the existing backoff/failure-limit
  already rate-limits; reads are bounded (`LIMIT`, default 200, max 1000,
  `after_sequence` cursor).
- Schema migration is additive only (`CREATE TABLE IF NOT EXISTS`);
  `schema_version` stays `1`. Legacy/copied DBs gain the table on
  `initialize()` with existing `instance_recovery` rows preserved.
- Corrupt history rows fail closed on decode
  (`RECOVERY_HISTORY_CORRUPT`); invalid write/read arguments fail typed
  (`RECOVERY_HISTORY_INVALID`).

## Authority fences preserved

- No new watchdog, scheduler, timer, task/claim/execution/retry authority.
- History is evidence only; it never feeds decisions.
- `restart_count`, failure/backoff, manual stop/start, suppression semantics
  unchanged (existing tests green without modification).
- Process recovery does NOT imply task/session recovery. Phase-B follow-up
  (task/session continuity evidence) is documented here as a future lane only;
  nothing in Phase A claims or implements it.

## RED/GREEN acceptance mapping

1. Legacy DB initialize adds history table, preserves rows ->
   `test_legacy_database_initialize_adds_history_table_and_preserves_recovery_rows`
2. History survives store reopen ->
   `test_recovery_history_survives_store_reopen_ordered_by_sequence`,
   `test_coordinator_sqlite_history_flow_ready_refresh_and_reopen`
3. Stable READY refresh -> zero duplicate events ->
   `test_stable_ready_refresh_appends_zero_history_events` (+ SQLite flow test)
4. Unexpected STOPPED -> recovery -> READY ordered evidence, READY
   observed_at strictly later when clock advances during start ->
   `test_unexpected_stopped_recovery_ready_uses_fresh_post_start_time`
   (+ SQLite flow test: 3000.0 -> 3030.0)
5. Manual suppress / manual_start distinguishable ->
   `test_manual_suppress_and_manual_start_history_is_distinguishable`,
   `test_manual_start_after_degrade_preserves_restart_count_in_history`
6. restart_count behavior unchanged ->
   existing `test_unexpected_stopped_autostart_attempts_one_recovery`,
   `test_manual_start_clears_suppression_and_failure_budget` green, plus
   event `restart_count` assertions
7. Corrupt history rows fail closed ->
   `test_corrupt_recovery_history_row_fails_closed_on_decode`
8. Existing focused recovery/store suites remain green (see checkpoint)
9. Gate checks below

## Checkpoint (attempt A0001, 2026-09-22)

- RED reproduced first: `RecoveryHistoryEventKind` import error and missing
  store methods before implementation; both focused suites then GREEN.
- `python -m pytest tests/test_connector_recovery.py
  tests/test_serena_config_store.py -q` -> 40 passed.
- Related regression: `tests/test_connector_recovery_visibility.py
  tests/test_desktop_control_recovery.py tests/test_worker_resilience.py`
  -> 18 passed.
- Store-consumer sweep (all remaining tests importing
  serena_config_store/SQLiteSerenaConfigStore) -> 281 passed, 48 skipped
  (GUI environment skips), 0 failed.
- `git diff --check` clean; changed paths exactly the five allowed files;
  UTF-8 decode verified on all changed files; secret-shape scan over the diff
  clean.
- Changes left uncommitted on `feat/wo-p1-478-worker-recovery-history` for
  GPT-5.6 Sol verification and freeze. No commit/push/merge performed.

## Next safe action (for verifier)

Review diff at working tree vs `e6f96e75`; rerun the three command groups in
this checkpoint; then follow the standard delivery gate sequence
(exact reviewed head -> CI on that head -> merge expected-head only ->
post-main CI -> checkpoint on the driving issue).
