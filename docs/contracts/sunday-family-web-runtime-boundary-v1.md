# Contract — Sunday Family Web Runtime Boundary v1

Status: roadmap contract for WO-P1-555
Version: `sunday-family.web-runtime.v1`

## Purpose

Define one cross-platform operator UI boundary for Sunday Family without creating a second control plane or letting a browser directly own execution.

## Product roles

- **Sunday Family** — product/package/operator experience.
- **A-Sunday Conductor** — authority, durable task/claim/routing/retry/review/acceptance/Command Gateway control plane.
- **SunDayRemoteMCP** — headless execution/capability substrate.
- **A-Faster** — accelerated scheduler/router profile over accepted task/claim authority.
- **A-NightShift** — persistent continuation behavior.
- **GLM / workers** — bounded labor.
- **JEV** — READ_ONLY advisory only.
- **Sunday Family Web/PWA** — eyes + operator control surface; never project SSoT.
- **Serena** — optional semantic/runtime dependency while required; dashboard is manual diagnostics only.

## UI framework baseline

Long-term primary operator UI:
- React
- TypeScript
- Vite
- standards-based HTML/CSS
- PWA manifest + service worker
- responsive browser-first layout

No server-side rendering is required for the local control center. Native wrappers are optional launch conveniences, never a second UI implementation.

## Backend/API baseline

A-Conductor owns the operator-facing service boundary.

Preferred future implementation baseline:
- Python service in the A-Conductor process family;
- FastAPI/Starlette + Uvicorn, subject to dependency/provenance review in the implementation WO;
- REST/JSON for snapshots and bounded command requests;
- SSE as the default one-way live Monitor event stream;
- WebSocket only if a later accepted requirement proves SSE + request/response insufficient.

This planning contract adds no runtime dependency yet.

## Read path

`DURABLE AUTHORITY -> NORMALIZED MONITOR PROJECTION -> A-CONDUCTOR MONITOR API -> SUNDAY FAMILY WEB/PWA`

The frontend never reconstructs task truth from local browser state.

## Command path

`SUNDAY FAMILY WEB/PWA -> A-CONDUCTOR COMMAND GATEWAY -> AUTHORITY/CLAIM/SAFETY/REPLAY CHECK -> SUNDayRemoteMCP`

Forbidden:
- `BROWSER -> SRM MUTATION`
- `BROWSER STATE -> PROJECT TRUTH`

## Local-first network defaults

- loopback only;
- no LAN/public listener by default;
- no anonymous remote control;
- no secrets returned to frontend payloads;
- explicit CORS/origin policy;
- state-changing requests require anti-CSRF/session protection appropriate to the chosen transport;
- remote access requires a separately accepted authenticated transport/tunnel profile.

## PWA behavior

The PWA may cache static application assets and non-sensitive help content.
It must not cache task/claim truth, execution completion, provider credentials, command authorization, or mutable state transitions as offline authority.
Offline/stale state must render explicit `STALE`, `DISCONNECTED`, or `UNKNOWN` semantics.

## Native packaging

Normal use must not require a native dashboard UI implementation. Optional platform launchers may start/attach to the local A-Conductor service, wait for bounded readiness, and open the Sunday Family URL/PWA.

## Serena Dashboard policy

`SERENA_DASHBOARD_AUTO_OPEN = FALSE`

Allowed only by explicit operator action for deep diagnostics while Serena remains an active dependency. Sunday Family may project a selected subset of accepted Serena runtime diagnostics but must not clone Serena's internal semantic-tooling UI.

## Compatibility / retirement rule

Tk/Ttk remains supported through LOCAL-USABLE-1 and while any required operator capability exists only there.
Tk/Ttk retirement is allowed only after Web/PWA parity, Monitor truth, Command Gateway, recovery/unknown-outcome visibility, Windows/macOS/Linux smoke, required Pi/headless smoke, and rollback documentation all pass.

No big-bang rewrite.
