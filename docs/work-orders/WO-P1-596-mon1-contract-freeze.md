# WO-P1-596 — P6 MON-1 read-only Monitor API contract freeze

Issue: #596
(Roadmap §P6; P5 STM-1A/1B accepted/post-main. This WO is the governance /
contract-freeze boundary; source mutation remains blocked until a separate
source claim passes the normal mutation gate.)
Class: CONTROL_PLANE_ONLY
Risk: R3 (authenticated local API surface adjacent to control truth; strict read-only boundary)
Executor route: Windows ZCode + GLM-5.3 MAX primary session
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo596-mon1-contract`
Branch: `docs/wo-p1-596-mon1-contract-freeze`
Bootstrap base: `64804534a426686bf3ff52e0ccbcdd3d39460a76` (= origin/main)

## Goal

Freeze the MON-1 read-only Monitor API contract before implementation
(WO-P1-547/WO-P1-592 pattern: contract-freeze claim first, separate source
claim after the mutation gate). P7 UI-1 lanes consume this frozen contract.

## READ_ONLY shaping evidence (2026-10-06, main 6480453)

- Accepted derived surfaces: `hook_bus.py` (drain/dispatch HookRecords,
  health), `hook_stm.py` (read → FRESH/STALE/UNKNOWN projections, partitions),
  `hook_producer_wiring.py` (producer binding, bounded admission view).
- Read-only consumer pattern precedent: `cockpit_projection.py`.
- No HTTP/web-server surface exists in `src/a_conductor/` today (grep: no
  http.server/flask/uvicorn/aiohttp usage) — MON-1's local API is NEW, with
  stdlib-only preference.
- No existing equivalent monitor API (reuse gate: REUSE derived reads +
  projection patterns; NEW bounded API module only).

## Frozen contract (v1)

1. **Projection only**: a pure monitor projection module derives view models
   from injected read callables (bus drain snapshot, STM read results,
   existing durable store readers). The API layer performs NO writes, holds
   no authority, and never mutates control/execution truth. Monitor restart
   must not disturb execution (exit gate).
2. **Views (bounded, sanitized)**: fleet (worker/connector state from
   existing durable sources), timeline (recent hook records), lane view,
   hook-health (degraded/counters/conditions), STM view (partition states
   incl. STALE/UNKNOWN + rebuild_required), evidence refs, and the MSP-3
   correlation view (chat-origin/command → claim/lane/run). No secrets, no
   raw prompts, no private payloads in any view (same privacy classes as the
   Hook Contract).
3. **Transport**: localhost-bound stdlib HTTP server (`127.0.0.1` only;
   never 0.0.0.0), one bounded JSON endpoint set (`GET` only) +
   `GET /stream` (bounded live view, server-sent-events-style newline JSON;
   bounded queue with typed backpressure drop-oldest; stream restart
   tolerated).
4. **Authentication (fail-closed)**: every request requires (a) `Origin`
   absent-or-equal to the configured local origin AND (b) an
   `Authorization: Bearer <token>` matching a per-boot random token (never
   logged, never in views), AND (c) `Host` header exactly `127.0.0.1:<port>`
   (DNS-rebinding protection). Any mismatch ⇒ typed 403. No token ⇒ 403.
   These gates must be proven by localhost tests with webpage-originated
   CSRF attempts and non-local Host headers BEFORE any browser/extension
   client connects (roadmap exit gate).
5. **No command authority**: no POST/PUT/DELETE; no endpoints that mutate
   anything; ACT-1 remains P8 scope.
6. **Liveness**: read-only E2E test proves views render while a fake producer
   feeds the bus; monitor process stop/start leaves control truth unchanged.

## Failure model (RED matrix for the source claim)

- missing/invalid/wrong-origin token ⇒ 403 (each gate independently)
- DNS-rebinding Host header (e.g. `evil.example`) ⇒ 403
- webpage-originated CSRF (Origin: https://page) ⇒ 403
- oversized/malformed request ⇒ typed 4xx, no crash
- stream consumer slower than producer ⇒ bounded drop + visible degraded
  marker, no unbounded memory
- STM STALE/UNKNOWN ⇒ surfaced truthfully, never hidden as fresh
- bus/STM failure ⇒ 5xx-or-empty-view with typed reason; control truth
  unchanged; monitor restart clean
- no listening surface when disabled ⇒ default OFF until explicitly started

## Non-goals

Web UI, extension UI (P7), command gateway (P8 ACT-1), #498B/C/D wiring,
remote (non-localhost) binding, TLS, authentication beyond the per-boot
token, any durable store, any scheduler/retry authority.

## Source mutation gate (separate claim)

Before source mutation: read DEFECT_LESSONS.md; rerun identity/ownership/
scope/collision gate; freeze exact paths — expected NEW
`src/a_conductor/monitor_api.py` (+ optional `monitor_projection.py`),
NEW `tests/test_monitor_api.py` (+ optional projection test), nothing else.

## Acceptance criteria (this WO)

Docs-only: this WO merges with identity-fixture + CI green; contract frozen
above; implementation gated to the next source claim per the failure model.

## Claim

Claim ID: `WO-P1-596-MON1-CONTRACT-FREEZE-WIN-001`
Posted to Issue #596 at bootstrap; released on WO merge or supersession.
