# WO-P1-599 — P7 UI-1 read-only Hook Monitor web page

Issue: #599
(Roadmap §P7; P6 MON-1 COMPLETE/post-main. This WO is the governance
bootstrap + contract freeze; source mutation is gated to the separate source
claim below per the normal mutation gate.)
Class: CONTROL_PLANE_ONLY
Risk: R3-adjacent (authn-boundary UI surface; read-only by construction)
Executor route: Windows ZCode + GLM-5.3 MAX primary session
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo599-ui1-bootstrap`
Branch: `docs/wo-p1-599-ui1-bootstrap`
Bootstrap base: `08f4fa6e493421f847ab3782eaa78806e9a0e513` (= origin/main)

## Goal

Minimal read-only web monitor page consuming the frozen MON-1 contract
(GET /snapshot + /stream + per-boot bearer token). One self-contained static
HTML+JS page — NO frontend build toolchain (the repository has none), NO
broad frontend rewrite, NO extension/desktop adapter in this slice (later
slices against the same frozen projection).

## REUSE / WRAP / EXTEND / NEW decision

- REUSE: `monitor_projection.py` view models verbatim (sanitized, bounded,
  truthful); `monitor_api.py` authn gates (token/Origin/Host fail-closed);
  `cockpit_projection.py` vocabulary for labels only.
- EXTEND (minimal, declared): `monitor_api.py` gains exactly ONE new GET
  route `GET /monitor` serving the static page bytes (same authn gates as
  every other route; Content-Type text/html; no dynamic server-side
  templating).
- NEW: `monitor_page.py` — pure module returning the page bytes (const
  string; zero runtime construction from state; no secrets).

## Frozen source scope (source claim)

- NEW `src/a_conductor/monitor_page.py`
- NEW `tests/test_monitor_page.py`
- MODIFY `src/a_conductor/monitor_api.py` — exactly the `/monitor` route +
  import; nothing else
- MODIFY `tests/test_monitor_api.py` — route rows only (authn-gated, HTML
  content-type, no token echo)

## Frozen page contract (v1)

1. **Self-contained**: single HTML document, inline CSS/JS, no external
   requests (CSP `default-src 'none'; style-src 'unsafe-inline';
   script-src 'unsafe-inline'; connect-src 'self'`).
2. **Token handling**: read ONCE from `location.hash` (`#token=...`),
   stripped from the URL immediately, held in memory only, never in
   localStorage/sessionStorage/cookies, never logged, never sent anywhere
   except the `Authorization` header to the same origin.
3. **Data**: poll `GET /snapshot` (interval ≥1s, backoff on 403/503) and
   optionally open `GET /stream` (ndjson); render when data arrives only.
4. **Truth semantics (exit gate)**: UNKNOWN / STALE / DEGRADED are rendered
   as explicit labeled badges — never as healthy/current/success; missing
   view fields render "UNKNOWN" placeholders, never blanks that look
   healthy; a 403 shows a "token required / forbidden" state, not an empty
   dashboard.
5. **Read-only**: the page issues GET requests only; no POST/PUT/DELETE
   controls exist; no mutation affordances of any kind.
6. **Views**: health (degraded badge + counters + conditions), timeline
   (bounded recent records), STM partitions (state badges incl.
   rebuild_required), correlation (state + entries or UNKNOWN).

## Failure model (RED matrix for the source claim)

- no/invalid token (page JS + /monitor route) ⇒ forbidden state, no data fetch loop with the bad token
- token never appears in page source served bytes; hash stripped on load
- snapshot 503/403/backoff ⇒ explicit degraded/error state, not blank
- STALE/UNKNOWN/DEGRADED views render labeled badges (DOM assertions)
- stream unavailable ⇒ snapshot polling continues
- oversized/malformed JSON ⇒ typed client-side error state, no crash
- /monitor route itself enforces token/Origin/Host gates (403 rows)
- page bytes are constant (no state interpolation server-side)

## Non-goals

Extension UI, desktop UI adapter, MSP-3 full lane view (correlation view
already exposes what MON-1 provides), P8 ACT-1 command surface, any
frontend build system, authn beyond the existing per-boot token.

## Acceptance criteria (this bootstrap)

Docs-only: this WO merges with identity-fixture + CI green; contract frozen
above; source work gated to the next claim.

## Claim

Claim ID (bootstrap): `WO-P1-599-UI1-BOOTSTRAP-WIN-001` — released on merge.
Source claim (to be posted under the same issue): `WO-P1-599-UI1-SOURCE-WIN-001`.
