# WO-P1-763 — SFU26 Card 03: Fleet/Work Identity Read DTO (Pure Projection)

Identity schema: GITHUB_ISSUE_V1
Issue: #763
Status: AUTHOR LANE — candidate for review/CI/merge gates
Risk: R2 (pure read-model projection; no canonical-claims writes; no local_instances lifecycle changes; no web/client changes)
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

- Base `69c0a2eb4c21b43ed3345bac886acd3efbaf7b32` (origin/main verified at bootstrap).
- Worktree `/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo763-fleet`; branch `feat/wo763-fleet-identity`.
- Program authority: SFU26 roadmap card `CAND-SFU26-03`. Standalone-first per cards 06/08/09/10 — web exposure deferred to card 04/UX-2 (owns client changes; avoids a second client-validator amendment).
- Exclusive files: NEW `src/a_conductor/fleet_projection.py`, NEW `tests/test_fleet_projection.py`, this WO. `awiki_claim_reader.py`, `local_instances.py`, `cockpit_projection.py`, `web_api.py` UNTOUCHED (consume-only by import; `web_api.py` not even imported — session records arrive as injected data).

## Verified Inputs (discovery 2026-11-15)

- **Claim** (`awiki_claim_reader.py`, 20 tests): `ClaimTaskBinding(task_id, claim_id, generation, repository, worktree, branch, head_sha, agent, scope)`; NO timestamps anywhere → expiry must be typed `EXPIRY_UNKNOWN`, never STALE; `worktree`/`scope` raw paths must NOT project (scope as count only); failure codes code-only (no diagnostic echo).
- **Lease**: reuse `CockpitLeaseObservation` AS-IS (`cockpit_projection.py:215-238`: lease_id, worker_id, worktree_key, branch, expected_head, health ACTIVE/STALE/EXPIRY_UNKNOWN/QUARANTINED, acquired/heartbeat/expires) — do not copy or redefine.
- **Session records** (`web_api.py:431-494`): worker `{id, display_name, created_at}`; connector `{id, name, state:"STOPPED", created_at}`; honest "app-session" scope comment :493; `project_path`/`tunnel_id` never project.
- **Local instance** (`local_instances.py`): `LocalInstance(name, project_path, health_address, instance_root, tunnel_configured, tunnel_suffix≤4)`; health READY/STOPPED/UNKNOWN; NO timestamps → age typed NOT_CARRIED; exclude project_path/health_address/instance_root (machine paths).
- **Remote device**: ABSENT in AWC (verified grep) → constant typed `UNKNOWN` + `REMOTE_DEVICE_OBSERVATION_UNAVAILABLE`.
- **Conventions**: staleness AVAILABLE/STALE/UNKNOWN (negative age → UNKNOWN); typed reason `^[A-Z][A-Z0-9_:\-]{0,127}$`; tz-aware ISO only (naive → None/UNKNOWN); frames ≤256 rows; provenance labels like cockpit (`DURABLE_EXECUTION_RECORD`, `WORK_ORDER_DECLARED`).

## Deliverables

1. **NEW pure module `fleet_projection.py`** (no clock — `now` injectable; no I/O; frozen+slots; `non_authoritative` init=False pinned):
   - `FleetView` composer `project_fleet_view(*, claim_bindings=(), lease_observations=(), worker_sessions=(), connector_sessions=(), local_instances=(), now=None) -> FleetView` producing per-source-class typed record groups + a cross-source identity summary:
     - claim records: safe handles only (claim_id, task_id, agent, generation, branch, head_sha, repository, scope_count) + `expiry: EXPIRY_UNKNOWN` + provenance `AWIKI_CLAIM_BINDING`;
     - lease records: pass-through of CockpitLeaseObservation fields (import the type, do not duplicate);
     - worker/connector sessions: `scope: "app-session"` label; state UNKNOWN (workers) / as-recorded STOPPED (connectors); NEVER fleet-ready promotion;
     - local instances: name, tunnel_configured, tunnel_suffix, health; age NOT_CARRIED;
     - remote devices: single constant typed record (UNKNOWN, REMOTE_DEVICE_OBSERVATION_UNAVAILABLE);
     - cross-source joins: same branch+head_sha across claim+lease → linked identity handle; MISMATCHED (same branch different head, or same task_id different claim) → typed conflict record (`IDENTITY_CONFLICT` with the divergent fields named), never merged; duplicate ids within one class → dedup first-wins + duplicate_count.
   - `available/provenance/reason` framing per record group; empty input class → typed empty (not unavailable); malformed injected record (bad sha shape, naive timestamp, blank id, path-shaped value in a safe field) → typed per-record rejection with code, neighbors survive; ALL duck-typed attribute access wrapped (card-08/09 P2 class — raising property → typed record, never exception escape).
2. **NEW tests**: per-class field sets pinned (introspection: NO worktree/scope-raw/project_path/tunnel_id/health_address/instance_root/pid/naive-stamp anywhere — grep-proof fixtures embedding each forbidden value); session-never-promoted (worker/connector records carry no fleet-ready vocabulary); remote UNKNOWN constant; EXPIRY_UNKNOWN on claims; conflict cases (branch+head mismatch, task_id divergence, same id different class); dedup + duplicate_count; malformed neighbors survive; raising-attr typed records; empty classes typed; determinism (same inputs → equal view); purity (no clock/env/network/provider imports); frozen+slots; join only when both sides valid (mixed valid/invalid does not half-join).

## Acceptance

- RED-first (ModuleNotFoundError + behavioral RED) recorded verbatim.
- Per-file green: `tests/test_fleet_projection.py`, neighbors `tests/test_awiki_claim_reader.py`, `tests/test_local_instances.py`, `tests/test_work_order_identity.py` (incl. this WO); `python3 -m compileall -q src/a_conductor`; no npm changes; diff = 3 files only.
- Delivery gate: frozen local commit → independent review → adviser concurrence → push → PR → exact-head CI → merge expected head → post-main CI (macOS capacity rerun precedent) → checkpoint + close on #763.

## Checkpoint

- 2026-11-15: lane bootstrapped @`69c0a2e`; issue #763; discovery + exclusion law recorded; implementation pending.
- 2026-11-15 (Phase 0 baselines, @`69c0a2e`): `tests/test_awiki_claim_reader.py` = 56 passed, 5 errors (pre-existing network-gated real-upstream tests: urllib HTTPS setup errors in offline environment); `tests/test_local_instances.py` = 1 failed, 22 passed (pre-existing `test_orchestrator_start_applies_brain_before_launch`: Windows-only absolute-path fixture `A:\GitHub\A-Wiki` rejected as non-absolute on macOS); `tests/test_work_order_identity.py` = 33 passed. Recorded as base truth for the regression gate.
- 2026-11-15 (Phase 1 RED, verbatim): (1) collection: `E   ModuleNotFoundError: No module named 'a_conductor.fleet_projection'` / `ERROR tests/test_fleet_projection.py` / `1 error in 0.28s`. (2) Behavioral RED against a transient stub: `62 failed, 25 passed in 0.65s` (stub replaced by the real implementation in the same exclusive file; final diff carries only the real module).
- 2026-11-15 (Phase 2 design decisions):
  - Record types (all frozen+slots, each with pinned init=False `non_authoritative=True`): `FleetClaimRecord` (claim_id, task_id, agent, generation, branch, head_sha, repository, scope_count, expiry, provenance, duplicate_count), `FleetLeaseRecord` (available, provenance, reason, observation — embeds the injected `CockpitLeaseObservation` by reference; zero field duplication; joins read branch/expected_head through the same wrapped duck-read helper), `FleetAppSessionRecord` (kind worker|connector, session_id, label, created_at, scope, state, age_seconds, staleness, duplicate_count), `FleetLocalInstanceRecord` (name, tunnel_configured, tunnel_suffix, health, staleness), `FleetRemoteDeviceRecord` (state, reason), `FleetRecordRejection` (source_class, code, field, source_index — code-only, no value echo), `FleetIdentityLink` (claim_id, lease_id, branch, head_sha), `FleetIdentityConflict` (code, divergent_fields, claim_ids, lease_ids, task_id, branch), `FleetIdentitySummary`, `FleetRecordGroup`, `FleetView`.
  - Reason vocabulary (all match `^[A-Z][A-Z0-9_:\-]{0,127}$`): rejections `RECORD_TYPE_UNSUPPORTED`, `RECORD_FIELD_MISSING`, `RECORD_ATTRIBUTE_UNREADABLE`, `IDENTIFIER_BLANK`, `IDENTIFIER_INVALID`, `IDENTIFIER_TOO_LONG`, `SAFE_FIELD_PATH_SHAPED` (backslash, leading `/` or `~`, `..` segment, drive-letter prefix), `HEAD_SHA_INVALID` (`[0-9a-f]{40}`), `GENERATION_INVALID`, `SCOPE_SEQUENCE_INVALID`, `TIMESTAMP_NAIVE`, `TIMESTAMP_INVALID`, `SESSION_STATE_INVALID`, `LABEL_INVALID` (via IDENTIFIER_* on label), `LEASE_PROVENANCE_REQUIRED`, `LEASE_HEALTH_INVALID`, `LOCAL_HEALTH_INVALID`, `TUNNEL_CONFIG_INVALID`, `TUNNEL_SUFFIX_INVALID` (>4 chars); group-level `FRAME_ROW_LIMIT_EXCEEDED` (256 rows/group), `RECORD_FRAME_INPUT_INVALID` (non-list/tuple frame → group available=False). Group provenance labels: claims `AWIKI_CLAIM_BINDING` (mandated), leases `COCKPIT_LEASE_OBSERVATION`, sessions `APP_SESSION_RECORD`, instances `LOCAL_INSTANCE_RECORD`, remote `AWC_TOPOLOGY_CONSTANT`.
  - Join/conflict rules: link only when a deduped-valid claim and a deduped-valid lease share branch AND head (`head_sha == expected_head`); same branch different head → `IDENTITY_CONFLICT` divergent `("head_sha",)`; one task_id mapping to multiple claim_ids → `IDENTITY_CONFLICT` divergent `("claim_id",)`; an equal id across two different classes is neither merged nor deduped nor flagged (records stay distinct). Rejected records never join (mixed valid/invalid never half-joins). Unavailable lease observations (available=False, ids None) pass through untouched and skip id validation.
  - Dedup keys: claims→claim_id, leases→lease_id, workers/connectors→session_id, instances→name; first-wins per class, survivor's `duplicate_count` counts suppressed duplicates, group carries the total.
  - Other: claim worktree/scope raw values never read or projected (scope = `len` only); lease stamps left to cockpit authority (pass-through, not re-parsed); instance health absent/None → typed `UNKNOWN`; instance staleness pinned `NOT_CARRIED`; sessions get age/staleness (AVAILABLE, negative→UNKNOWN) only when `now` injected; `now` naive/non-datetime → `ValueError("FLEET_NOW_MUST_BE_TZ_AWARE")` (caller contract); duck-typed injection for all classes (claims/sessions/instances are data, not imports — `awiki_claim_reader`, `local_instances`, `web_api` are never imported).
- 2026-11-15 (Phase 3 GREEN + regression): `tests/test_fleet_projection.py` = 87 passed; neighbors byte-identical to Phase 0 baselines (56 passed / 5 pre-existing errors; 1 pre-existing failed / 22 passed; 33 passed); `python3 -m compileall -q src/a_conductor` OK; `git status --porcelain` = exactly 3 files (WO doc + NEW module + NEW test), zero modifications to existing tracked files.
