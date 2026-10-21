# WO-P1-687 - SF-WEB-0: Sunday Family Web/PWA Contract and Dependency Gate

Identity schema: GITHUB_ISSUE_V1
Issue: #687
Status: DRAFT_FOR_ROOT_REVIEW - CONTRACT ONLY; no implementation authorized
Risk: R0 bounded docs bootstrap; future API/security/service changes require R2/R3 classification
Topology: CONTROL_PLANE_ONLY (A-Wiki-Conductor)

## 1. Goal and Authority

Define the bounded Monitor API and Sunday Family web shell boundaries for the SF-WEB sequence, reusing accepted read authorities without creating another control plane. This draft elaborates PROJECT-PLAN.md section 27, the accepted WO-P1-555 / PR #557 direction, docs/plans/2026-09-26-sunday-family-web-pwa-roadmap.md, and docs/contracts/sunday-family-web-runtime-boundary-v1.md. Those authorities win over this draft. Root acceptance is required before this becomes a successor implementation packet.

The driving issue records LOCAL-USABLE-1 as reached (GOT-1/FMG-1/COCKPIT-1 closed). This is the post-LOCAL-USABLE-1 contract lane, not a fresh claim that the existing HTTP service is already a complete headless product.

Authority remains: durable Conductor sources -> normalized read projections -> Conductor Monitor API -> browser presentation. Conductor alone owns task/claim/admission/reconciliation/receipt/retry/review/acceptance and Command Gateway truth. SRM owns execution-local supervision/evidence only. Browser state, a successful HTTP request, a stream event, or SRM status never constitutes task acceptance or replay authorization.

## 2. Bootstrap Identity and Scope

- Baseline: GitHub main and local origin/main verified at `7cb757d79f97bb0442565c93575e23d47039c806` on 2026-10-20; root working checkout is intentionally stale and was not changed.
- Worktree: `A:\GitHub\_worktrees\AWC-wo687-sfweb0`; branch: `docs/wo687-sfweb0`; base and HEAD: the full baseline SHA above; origin: `https://github.com/aase7en/A-Wiki-Conductor.git`.
- Bootstrap owner: assigned DOCS-ONLY author session `ses_ea5fd8e87ffe3v5SgcuHXFGHM8`, under the explicit one-file task; no product/source claim is acquired or implied.
- Sole allowed repository edit: `docs/work-orders/WO-P1-687-sfweb0-contract-gate.md`. No source, tests, dependencies, frontend scaffold, shared continuity docs, other repositories, runtime configuration, listeners, or credentials may change.
- No commit, staging, push, PR, merge, installation, or live browser/service activation in this lane. Root owns review and any later publication/continuity fold.
- Workflow: bounded docs bootstrap under FAST_EXECUTION_PROTOCOL.md / COLLAB_PROTOCOL.md; GLM offload NOT_BENEFICIAL for this assigned single-document authoring lane. Binding security/API acceptance remains a root-reviewed R2/R3 successor gate, not an R0 bypass.

## 3. Reuse Audit at the Pinned Main

| Existing surface | Verified behavior | Decision and bounded gap |
|---|---|---|
| `src/a_conductor/monitor_api.py` (MON-1 / WO-P1-596) | Inert until start; stdlib HTTP server; loopback config; per-server random bearer; constant-time comparison; exact Host and absent-or-exact Origin; duplicate security-header refusal; authenticated GET `/healthz`, `/snapshot`, `/stream`, `/monitor`; typed failures; bounded drop-oldest subscriber queues; tracked connection shutdown and restart-generation guard | WRAP/EXTEND its read-provider and security/lifecycle semantics in an additive ASGI adapter. Existing `/stream` is `application/x-ndjson`, NOT SSE. Do not silently reinterpret or remove legacy routes or weaken auth. |
| `src/a_conductor/monitor_projection.py` | Pure `build_monitor_views` composes bounded health/timeline/STM/correlation views from injected observations, with public-field filtering and explicit UNKNOWN/STALE | REUSE as Hook/STM monitor view; not a task store. Apply value-level secret policy as well as key allowlists before browser exposure. |
| `src/a_conductor/cockpit_projection.py` | Frozen cockpit DTOs and pure lane/snapshot composition; durable-source provenance; transport separate from execution; explicit stale/drift/incomplete/unknown semantics; terminal success needs gate proof; origin is display-only; deterministic fingerprint | REUSE state derivation. Add an explicit bounded public serializer/composer at the service boundary; do not assume dataclass output/fingerprint is a browser-safe serializer or expose all fields by default. Missing read ports stay unavailable, not fabricated healthy. |
| `src/a_conductor/instance_monitor.py` | Local PID-file read, bounded log tail, error scanning and native memory reads; no periodic subprocess spawning | REUSE only behind selected instance/read authorities. PID-file numbers are observations, not verified process ownership. Raw tails, paths and exception strings are not automatically public API payloads; redact/allowlist/bound them first. |
| `src/a_conductor/monitor_page.py` (UI-1 / WO-P1-599) | Constant self-contained read-only HTML; same-origin bearer fetch; fragment consumed then removed; memory-only token; GET snapshot polling with bounded backoff; explicit truth markers | RETAIN as diagnostic/rollback compatibility surface. React is a separate presentation build, not a second authority. Do not call this page a React shell or SSE client. |

The HTTP server accepts an injected dictionary provider; it does not itself assemble all cockpit and Hook/STM sources. SF-WEB-1 must prove headless read composition through existing service/read ports without importing or starting Tk, scraping widgets, initiating commands, or reading arbitrary client-supplied paths. This adapter/composition work is new transport/presentation glue, not new scheduling, persistence, replay logic, or an SRM dependency.

## 4. Proposed Monitor API v1 Contract

The following versioned routes are the target of SF-WEB-1, not routes claimed to exist today. Preserve legacy behavior until a separately reviewed migration permits removal. All browser-consumed health, snapshot and SSE data requires the same local authorization boundary.

| Method and path | Success shape | Failure behavior |
|---|---|---|
| GET `/api/v1/health` | JSON: `api_version: "sunday-family.monitor.v1"`, `status: "OK"` or `"DEGRADED"`, bounded typed `conditions` | HTTP 503 when the read service cannot produce its required projection; listener liveness alone is never authority readiness |
| GET `/api/v1/monitor/snapshot` | One coherent bounded JSON snapshot envelope defined below | HTTP 503 for unavailable/invalid source projection; no empty-success fallback |
| GET `/api/v1/events` | `text/event-stream; charset=utf-8`, snapshot/error events and comment heartbeats | Authorize before headers; HTTP errors before streaming, typed error event after headers; disconnect never changes execution truth |

No command routes in SF-WEB-1..3. Other methods on these paths return typed 405 after authorization. Unknown routes return typed 404 without echoing input. Optional projects/fleet/executions read routes from the roadmap are deferred until a child WO declares their exact sanitized DTO and accepted read authority; no general database/filesystem API.

### Snapshot envelope

- `api_version`: literal `sunday-family.monitor.v1`; unsupported versions are not silently accepted.
- `generated_at`: UTC timestamp for the composed read view, not last meaningful execution progress.
- `cockpit`: bounded public projection of the accepted CockpitSnapshot: lane/task/claim/execution identity where recorded, state, markers, typed blocker, transport, activity/progress timestamps, provenance, gates, replay-safety and next-safe-action display. Public schema must explicitly enumerate fields and limits in SF-WEB-1; no arbitrary dataclass dump.
- `monitor`: existing sanitized health/timeline/STM/correlation view, or explicit typed unavailable marker if optional reads fail. Required-read failure returns 503; optional failure remains visible in the envelope.
- `stale`, `stale_reason`, `degraded_observability`: retain source truth; transport delivery cannot clear these markers. Service loss adds client DISCONNECTED/STALE presentation without rewriting source task state.
- `monitor_stream_degraded`: boolean delivery-gap marker (false in standalone snapshots); distinct from source degradation and never evidence of execution failure.

Snapshots are read-only copies of one bounded observation pin; never mix identities from separate pins. Keep UNKNOWN, STALE, EVIDENCE_INCOMPLETE and TERMINAL_UNHARVESTED visible. No completion inferred from exit code alone, absent records, a heartbeat, UI timers, or transport reconnection. Preserve existing gate and origin-display provenance semantics.

### SSE framing and recovery

- `event: snapshot` carries one compact JSON snapshot envelope in `data:` followed by a blank line. Send an initial fresh snapshot on subscription, then bounded updates from one shared producer rather than one authority poll per browser.
- `event: monitor_error` carries the typed JSON error object below. A `: heartbeat` comment at a bounded interval (target 15 seconds) indicates transport activity only; it is not new source evidence.
- Start with existing producer cadence 0.5 seconds and per-subscriber queue bound 64 (hard maximum 256); bound total subscribers and request lifetimes in the child implementation. Slow consumers must not block the producer or other clients. Drop-oldest marks the affected client's next frame degraded; after any detected gap the client fetches a fresh snapshot.
- Maximum serialized snapshot/event data is 262144 UTF-8 BYTES, checked after encoding, with bounded collection/string materialization beforehand. Never truncate JSON or SSE frames. Oversize yields a complete small typed error; validate multibyte boundary cases rather than copying the legacy character-count check.
- No durable replay/event log is promised by this read-model stream. No SSE `id`/Last-Event-ID replay contract in v1; reconnect always obtains current snapshot and visibly resets continuity. Backoff is capped at 30 seconds; authentication refusal stops automatic reconnect until explicit reauthentication.
- Use an authenticated `fetch` streaming SSE parser with Authorization header; native EventSource cannot supply this bearer header. Never move the bearer to a query string or drop auth to accommodate EventSource. Abort streams on teardown; bound line/frame buffering and reject malformed/unknown version payloads visibly.
- JSON/SSE responses use `Cache-Control: no-store`; intermediary buffering/compression must not delay bounded delivery. Browser disconnect releases subscription/resources; restarting the monitor cannot stop/retry/accept a task or revive an old producer generation.

### Typed error vocabulary

Common response/event object: `{"error":"MONITOR_..."}` plus optional bounded enum `gate`; never bearer, raw exception, stack trace, path, arbitrary request value, or credential. Existing names are reused; new names below are proposed for the additive adapter.

| Code | HTTP / stream meaning |
|---|---|
| `MONITOR_FORBIDDEN` | 403; gate is HOST, ORIGIN, TOKEN or corresponding `_DUPLICATE`; missing/invalid auth fails closed |
| `MONITOR_NOT_FOUND` | 404; unknown/invalid route |
| `MONITOR_READ_ONLY` | 405; prohibited method, no authority mutation |
| `MONITOR_PROJECTION_UNAVAILABLE` | 503 before headers or monitor_error event; required read/serialization failed |
| `MONITOR_FRAME_OVERSIZED` | 503 before headers or monitor_error event; encoded payload exceeds bound |
| `MONITOR_CAPACITY_EXCEEDED` (new) | 503 before subscribing; bounded subscriber budget exhausted |
| `MONITOR_VERSION_UNSUPPORTED` (new) | Typed client rejection or 400 for an explicitly unsupported protocol-version request; no inferred compatibility |

Configuration/lifecycle codes remain operational failures, not invented HTTP success: `MONITOR_HOST_MUST_BE_LOOPBACK`, `MONITOR_PORT_INVALID`, `MONITOR_POLL_INVALID`, `MONITOR_QUEUE_BOUND_INVALID`, `MONITOR_PROVIDER_INVALID`, `MONITOR_CONFIG_INVALID`, `MONITOR_ALREADY_RUNNING`, `MONITOR_POLLER_TERMINATING`, `MONITOR_STOP_INCOMPLETE`. Client DISCONNECTED/STALE is presentation vocabulary separate from backend error and task state.

## 5. Local Authentication and Network Boundary

- Bind only `127.0.0.1` initially. No `0.0.0.0`, LAN/public exposure, automatic tunnel, forwarded-header trust, or anonymous local-data access. IPv6 or localhost aliases need an explicit tested Host/origin convention, not implicit wildcard acceptance.
- Port is explicit configuration: 0 permits OS-selected ephemeral development/test binding, whose actual port is reported locally; stable installed port allocation is SF-WEB-5 scope with collision refusal. Do not silently reuse another service/worker port or guess a fixed production port here.
- Require an unguessable local bearer before data on every read endpoint/stream. Preserve constant-time validation and duplicate Host/Origin/Authorization rejection. Validate exact `127.0.0.1:<bound-port>` Host; absent Origin only for a correctly authenticated non-browser/local request, otherwise exact approved origin. Reject foreign/null origins, ambiguous authorities and DNS-rebinding attempts before projection/provider invocation.
- Default browser shell is same-origin static assets served by the Conductor service. Asset delivery must never embed credentials or authority data. Token handoff follows the reviewed local-launch pattern (fragment removed immediately, memory only); no token in API responses, templates, access logs, analytics, query strings, localStorage, IndexedDB or service-worker caches. Recheck generation/token invalidation on service restart; the current server object creates its token at construction, not necessarily every start call.
- Vite is a local development asset server, not a second authority. Preferred integration tests use the built same-origin shell. Any Vite proxy/development origin requires a separate exact dev-only Host/origin policy and DNS-rebinding/CSRF tests, no wildcard CORS, no production relaxation, no token injection in source or committed config, and no proxy that erases an untrusted incoming Origin before validation.
- Source paths, raw logs and correlation string values may contain secrets even when keys look public. Only explicit browser-safe fields/values pass; raw diagnostic file access and provider credentials stay out. Do not copy GPL Serena application code; dashboard auto-open remains false and diagnostics require explicit action.
- SF-WEB-1's deterministic auth/origin/CSRF/DNS-rebinding tests must pass BEFORE any browser/extension client connects, per the parent contract. Concurrency/auth/lifecycle changes require R3 framing and independent review.

## 6. Framework and Dependency Gate

Verified `pyproject.toml` at the pinned SHA: Python >=3.11; setuptools>=68; direct runtime dependencies Pillow>=10, Markdown>=3.10.3,<4, tkinterweb>=4.25.3,<5, tkinterweb-tkhtml>=2.1.1,<3, tkinterweb-tkhtml-extras>=1.3.1,<2, and Windows-only moderngl>=5.12 / pyopengltk>=0.0.4. Test extras are pytest>=7 and jsonschema>=4.23. Current entrypoint is desktop-only `a_conductor.desktop_app:main`. No FastAPI, Starlette, Pydantic or Uvicorn constraint is declared there.

Recommendation: follow the accepted FastAPI application / Starlette ASGI transport baseline and Uvicorn development server. Prefer minimal FastAPI + plain Uvicorn dependencies in an optional web-service extra rather than broad standard extras unless each extra is justified. Do not independently pin Starlette outside FastAPI's compatible range. This document installs/adds nothing and selects no unverified exact package versions or new entrypoint name.

Static conflict verdict: NO DIRECT DECLARED CONSTRAINT CONFLICT FOUND. This is NOT a resolver/install, transitive-compatibility, vulnerability, license, frozen-build, or cross-platform certificate. The ASGI application must remain importable without Tk/GUI/GPU modules; optional web dependencies must not become mandatory for current desktop usage without an explicit packaging decision.

Before dependency addition, SF-WEB-1 must record exact selected distributions/versions, upstream provenance and license obligations, Python 3.11 support, full transitive resolution alongside current dependencies, clean-environment installation and `pip check`, relevant regression/import tests, and known security findings. Verify supported OS combinations without assuming optional performance extras work everywhere; no global installs. Failures block dependent API/browser work, not existing desktop operation. Uvicorn development binding is explicitly loopback, single producer/service ownership, reload disabled for lifecycle proof; no `0.0.0.0` or multi-worker process proliferation.

Documentation checked 2026-10-20 via Context7 official FastAPI docs: https://fastapi.tiangolo.com/deployment/versions/ (let FastAPI select compatible Starlette), https://fastapi.tiangolo.com/deployment/manually/ (ASGI/Uvicorn), https://fastapi.tiangolo.com/tutorial/ (standard install extras). Examples' public-bind defaults are not adopted. Exact dependency/provenance proof remains a successor admission gate.

## 7. React / TypeScript / Vite Shell Boundary

Frontend belongs to A-Wiki-Conductor in a separate directory, proposed `web/sunday-family/`, outside `src/a_conductor/`; child WO must verify path/ownership before scaffold. Do not reuse or overwrite the stale root checkout's untracked `frontend/` contents. Node dependencies/build output stay separate from Python source/package discovery; built assets may be served by the same local service through a later explicit packaging seam.

React + strict TypeScript + Vite, client rendering only: no SSR, Node backend, duplicate scheduler/store, provider client, arbitrary command UI, browser filesystem bridge or SRM endpoint. SF-WEB-2 contains read-only Overview/Fleet/Runtime/Activity derived from the contracted snapshot. Other navigation may show honest unavailable placeholders, never fabricated data/actions. Honor the established compact CLI-inspired near-black, thin-border, monospaced operational visual language, responsive desktop/mobile and keyboard-accessible states. PROJECT-PLAN section 27 supersedes DESIGN.md's historical Tk-only framework wording, not its visual intent; no shared design edits here.

Validate versioned input at runtime as well as TypeScript compile time; use text-safe rendering, bounded in-memory state, cancellation and capped reconnect. Last-known values may remain visible only with explicit stale/disconnected labels, never as current truth. No browser write-back, offline action queue or optimistic consequential transitions. PWA readiness means asset-relative routing and separate cache policy seams, not service-worker implementation in SF-WEB-2.

## 8. Ordered Successor Slices and Acceptance Gates

Each row requires a fresh child WO/claim, exact source allowlist, current baseline and risk classification; this table is not source mutation authority. Canonical order is `0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7`. Disjoint exploratory work may overlap only under root-approved claims; it cannot claim a later acceptance gate early.

| Slice | Dependency / risk floor | Bounded acceptance criteria |
|---|---|---|
| SF-WEB-1 - read-only Monitor API | Root accepts SF-WEB-0; stable accepted monitor/cockpit read seams; R3 for auth/lifecycle/concurrency | Dependency/provenance gate passes; headless provider wiring proven without Tk/subprocess polling; versioned snapshot + real SSE + health; public DTO/byte/resource bounds; no command routes; legacy monitor compatibility; deterministic unauthorized/duplicate-header/foreign-origin/null-origin/rebinding/CSRF, malformed serialization, oversize Unicode, source drift, slow client, gap/reconnect, stop/restart tests; independent review before any browser client. |
| SF-WEB-2 - read-only web shell | Accepted 1 and API security gate; R2 | Separate React/TS/Vite build/type checks and locked provenance; read-only Overview/Fleet/Runtime/Activity; authenticated header-bearing SSE/snapshot; UNKNOWN/STALE/degraded/terminal-unharvested fixtures; no SRM or mutation calls; desktop and narrow/mobile browser/keyboard smoke; no-secret/network assertions. |
| SF-WEB-3 - PWA/local experience | Accepted 2; R2, R3 if launcher/session authority changes | Manifest/icons/installability and bounded static-only service worker; API/SSE/auth/commands NEVER cached; restart/offline/disconnected truth visible; no offline command queue; cache upgrade clears obsolete assets without deleting authority data; optional launcher opens local URL only after authenticated bounded readiness. |
| SF-WEB-4 - Command Gateway controls | Accepted read-only 1..3 plus separately accepted action authority; R3 | Enumerated actions only through Conductor Command Gateway; target/task/claim/version preconditions, auth/session/anti-CSRF/replay/duplicate/ambiguity tests; rejected intents cause zero effect; result followed by authoritative read-back, never optimistic acceptance; no arbitrary shell/argv/SQL/prompt/file or direct SRM mutation endpoint. |
| SF-WEB-5 - cross-platform service packaging | Accepted 1..4; R3 | One headless service/asset story with Windows/macOS/Linux and required Pi/Umbrel/headless smoke, clean install/restart/shutdown/port collision/session handling and rollback; optional native launchers only; no mandatory GUI executable or duplicate service/producer. No automatic real enrollment, paid hosting or production credential issuance. |
| SF-WEB-6 - parity / optional Tk retirement | Accepted 1..5; R3 release/retirement decision | Explicit capability parity matrix incl. monitoring provenance, Command Gateway, recovery/unknown outcomes and copyable diagnostics; required OS/browser/mobile/Pi smoke and rollback documentation; root accepts evidence before any Tk fallback removal. No big-bang rewrite or automatic retirement. |
| SF-WEB-7 - authenticated remote operator mode | Accepted local/parity sequence; separate opt-in/threat-model/transport decision; R3 | TLS + explicit auth/origin/session policy, revocation/session expiry, remote abuse/resource bounds and anti-CSRF tests; no anonymous data/control or direct SRM exposure; remote failures preserve local recovery; separately authorized deployment/tunnel/credentials. Not a local-use prerequisite. |

Future SRM changes are forbidden in these CONTROL_PLANE_ONLY slices unless a genuinely missing execution capability is separately approved as CROSS_REPO with exact-SHA compatibility-set identity and global WIP counted once. Browser/API delivery never expands SRM authority.

## 9. Conflicts, Open Gates and Stop Conditions

- Existing stream/media type mismatch is real: NDJSON and polling exist; SSE is future additive work. Preserve legacy tests and clients, not an unsupported claim that MON-1 already satisfies SF-WEB-1.
- Cockpit truth and Hook/STM monitor dictionaries are distinct projections; full headless composition/public serialization remains unproven. Never expose raw observations, derive truth twice, or import desktop UI to bypass that gap.
- No direct dependency conflict was found in declared constraints; transitive resolution/provenance remains NOT_RUN. Block runtime dependency admission until evidence exists, not until an imagined framework incompatibility is fixed.
- Bearer authentication conflicts with native EventSource custom-header limitations and careless cross-origin Vite setup. Fetch-stream SSE and same-origin delivery are the chosen bounded approach; never relax the security gate for convenience.
- Existing legacy stream length checks count characters; v1 must prove UTF-8 byte limits. Existing random token is per object construction; test restart lifetime rather than assuming rotation at every start.
- Historical DESIGN.md Tk-only prose is superseded for long-term framework choice by section 27; Tk stays supported until parity. No design/shared-doc changes in this bootstrap.
- Any missing ownership, ambiguous source identity, dependency failure, secret exposure, need for source/shared-doc edits, public binding, command authority growth, or unaccepted SRM seam is a STOP / root-adjudication boundary.

## 10. Bootstrap Verification and Handoff

Required checks: exact sole-file scope including untracked files; `git diff --check` plus added-file whitespace verification (untracked files are absent from normal diff); strict UTF-8 with no replacement characters/BOM; exactly one issue identity line matching filename; existing identity suite must report 33 passed and include this untracked WO in its corpus. No runtime/source test result is claimed by this docs gate.

Verification on 2026-10-20:

- `python -B -m pytest tests/test_work_order_identity.py -q -p no:cacheprovider --basetemp=C:\Users\aase7en\AppData\Local\Temp\kilo\wo687-identity-20261020`: 33 passed; corpus guard includes untracked work orders.
- `git diff --check`: exit 0; additional explicit added-file trailing-whitespace/final-newline check PASS.
- Strict UTF-8 decoder, no BOM/replacement character, exactly one issue identity and one schema marker, empty tracked/index diffs, and sole untracked-file allowlist: PASS. Initial verifier used culture-sensitive .NET StartsWith on U+FEFF and falsely reported a BOM; raw prefix `23-20-57-4F` and ordinal first-codepoint check proved no BOM, and the corrected verifier passed. No file repair was necessary.
- No dependency installation/resolution, API/browser activation, source/test/shared-doc edit, staging, commit or push performed. These checks establish draft integrity, not successor implementation acceptance.

Checkpoint: draft contract complete and bootstrap checks passed. Next safe action is root review of this exact file/diff and dependency/security decisions, then separately authorize a claimed SF-WEB-1 packet. SAFE_TO_MUTATE_SOURCE = NO. Shared CURRENT-WORK.md/handoff.md fold remains root-owned and intentionally untouched by this one-file author.
