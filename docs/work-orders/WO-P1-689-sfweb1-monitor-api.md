# WO-P1-689 - SF-WEB-1 Read-Only Monitor API

Identity schema: GITHUB_ISSUE_V1
Issue: #689
Status: AUTHOR_VERIFIED_FOR_REVIEW; independent R3 review and acceptance pending
Risk: R3 (authorization, concurrency and lifecycle), superseding issue's R2 estimate
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

Explicit AUTHOR assignment binds aase7en/A-Wiki-Conductor at
`d16066ddd5bc061f2a41896fcb18dfc3d1d0c91b` to
`A:\GitHub\_worktrees\AWC-wo689-sfweb1`, branch
`feat/wo689-sfweb1-monitor-api`, owner session `ses_ea346211affez2Q7uixgdtQgUJ`.
This is the bounded local claim for this assignment; no GitHub posts authorized.
No existing WO689 or matching worktree/branch was present at entry. Root checkout
is stale/dirty and untouched. Global integrator owns shared continuity fold and
independent review; this author cannot accept or merge its own candidate.

Allowed: this WO, pyproject.toml, src/a_conductor/web_api.py,
src/a_conductor/web_api_auth.py, tests/test_web_api.py; additive optional row bounds
on existing desktop_control.py cockpit read ports; lazy-load the two existing
desktop_ui exports in src/a_conductor/__init__.py (headless import gate);
ignored runs/WO-P1-689
evidence and isolated .venv. No legacy monitor changes, shared continuity, A-Wiki, SRM,
frontend, live DB, runtime configuration, credential file, PR, merge or issue post.

## R3 Failure Model and Implementation Contract

Authority remains durable sources -> existing cockpit projection -> public DTO ->
HTTP view. No command/store/retry/replay/acceptance authority. Reject ambiguous
headers, foreign/null origins, rebinding Host, invalid bearer before route work.
Per-lifespan random bearer, constant-time comparison, no token in logs/responses.
Only numeric loopback binding; prebound socket pins actual ephemeral port.
Default 8756 refuses collisions; explicit 0 requests OS-selected port.

Reuse MonitorApiServer's bounded subscriber/drop-oldest producer machinery without
starting its legacy listener. One shared bounded producer, cached read observations,
finite request/send/stream lifetimes and subscriber/connection caps. A wedged
provider remains one owned daemon producer, never replaced/replayed on restart;
shutdown failure is explicit. No per-browser polling or unbounded thread creation.
Optional monitor read is explicitly unavailable until an accepted read port is
injected. CLI reads only operator-selected existing DB via existing cockpit
read-only ports, pins/rechecks observations and preserves missing-source markers;
never calls DesktopControlService.open(), migrations, Tk or subprocess polling.

Explicit latest assignment chooses required FastAPI/Uvicorn runtime dependencies,
GET /api/v1/snapshot and /api/v1/stream, status=ok health and token failures=401.
These supersede the draft's optional-extra recommendation/route/token defaults.
Retain /api/v1/monitor/snapshot and /api/v1/events aliases, API version envelope,
readiness 503, snapshot/update SSE and typed monitor_error events. No CORS,
WebSocket, SSR, write route, query bearer, automatic tunnel or browser activation.

Public DTO explicitly enumerates fields, excludes paths/logs/raw exception text,
enforces field grammars/value policy, collection bounds before serialization and
262144 UTF-8-byte wire bound. Invalid/oversize sources yield complete typed errors,
not empty successful data. Source UNKNOWN/STALE/gates/provenance remain visible.

## Dependency Admission

PyPI metadata verified 2026-10-21: fastapi 0.156.4 (Python >=3.10, MIT,
github.com/fastapi/fastapi); uvicorn 0.54.0 (Python >=3.10, BSD-3-Clause,
github.com/Kludex/uvicorn); httpx 0.28.1 (Python >=3.8, BSD-3-Clause,
github.com/encode/httpx). Python 3.11 supported by all declared ranges.
Retain upstream license/notice obligations in distributions. No independent
Starlette pin or broad standard extras. Full resolver, pip check, dependency audit
and import/regression evidence must be recorded before candidate freeze.

## Verification and Handoff

RED-first tests: snapshot/health/SSE, auth/duplicate headers/null+foreign Origin/
rebinding/CSRF, read-only methods, malformed/oversize UTF-8 DTO, stale source,
drop-oldest isolation, subscriber limit, disconnect/reconnect and restart token,
headless existing-file read with no DB writes, real loopback socket binding.
Run python -m pytest tests/test_web_api.py -v; identity+monitor+cockpit regressions;
attempt python -m pytest tests/ -x --timeout=300. Scope/UTF-8/diff checks, commit
and push only assigned branch. No PR, merge or GitHub posts. Root must perform
independent exact-SHA R3 review before any browser client/acceptance.

## Public DTO and Resource Limits

Envelope fields: api_version, generated_at, cockpit.lanes, monitor, stale,
stale_reason, degraded_observability, monitor_stream_degraded. monitor is a typed
optional-read-port-unavailable object, not fabricated Hook/STM health.
Lane identity fields: work_order_ref, task_ref, lane, execution_id, lease_id,
provenance. Lane fields: state, state_markers, blocker_code, transport_state,
capacity_class, wait_reason, replay_safety, next_safe_action, hook_state, wtl_state,
execution_id, job_id, last_activity, last_meaningful_progress, next_recheck_at,
countdown_seconds, active_mutation_child, gates, origin_display. Gate fields:
verification, review, merge, post_main, ci, provenance. Origin display fields:
status, reason, origin_ref, origin_surface. No worktree/repo path, raw prose,
exception, provider configuration, log tail, credential or arbitrary nested map.

Maximum256 lanes/degradation entries,16 markers per lane; ASCII reference/code
grammar128 characters, aware timestamp40 characters; countdown integer0..2^31.
Maximum262144 UTF-8 bytes after encoding, no NaN/Infinity. Max16 subscribers
(configurable1..64), queue64 (1..256), connections32 (1..128), producer cadence0.5s,
stream lifetime300s, send deadline10s, request deadline10s, heartbeat15s.
Source-cache age >max(2s,3 producer intervals) fails closed. Optional DB reads
fetch at most257 rows per authority, refuse overflow, cap SQLite row bytes262144,
query VM budget2s and busy wait1s. Defaults for legacy desktop callers unchanged.

## Author Checkpoint

Final API tests47 passed; affected API/identity/legacy-monitor/cockpit/desktop
control/app/UI matrix313 passed (runs/WO-P1-689/final-focused.xml). Fresh-process
headless import, real Uvicorn SSE/disconnect/reconnect, actual numeric loopback
socket, unchanged DB bytes, stale-cache denial, restart token invalidation,
capacity/drop-oldest and blocked-send cleanup verified. CLI help and pip check
PASS. Latest Starlette emits an httpx TestClient deprecation warning; tests still
pass with requested httpx0.28.1. No cross-platform runtime proof claimed.

Isolated pip editable install initially hit Windows PermissionError on a generated
launcher; uv install completed full resolution. Installer tools upgraded to
pip26.2.2/setuptools84.2.1. A stale incomplete pip24 dist-info (only2 marker files)
was quarantined in the owned venv, not deleted. Final pip-audit: no known
vulnerabilities found (editable local application skipped); this is advisory
database coverage, not a security certificate. Exact resolved graph and failures
are recorded in runs/WO-P1-689/result.md.

Standalone CLI keeps its bearer in process memory only, with no stdout/file/URL
token handoff. Trusted in-process embedding can obtain app.state.feed.token;
production launcher/session handoff is explicitly deferred, not silently unsafe.
Standalone DB composition exposes accepted durable execution/lease observations;
CC/activity and optional Hook/STM reads remain explicitly unavailable. Callers may
inject the accepted full service cockpit_projection read method via create_app.

GLM_OFFLOAD=BLOCKED:SECRET_SOURCE_UNAVAILABLE; no secret disk search or provider
call. RDC ping unavailable (tool not found), Worker1..5 not exposed in this harness.
Exact assigned local author fallback used. Shared CURRENT-WORK.md/handoff.md fold
remains integrator-owned; this WO and ignored result are the author handoff.
Candidate is not accepted; independent R3 review/hosted CI remain root gates.

Full regression attempt1:6690 collected,5725 passed/10 skipped, stopped at the
new stalled-send test in a process which had imported pre-repair code. Final
focused313 includes the repair and47 API tests, all green. Fresh full attempt2:
6692 collected; process terminated around56% with Windows fatal exception
0x80000003 during garbage collection in socket.makefile while unchanged legacy
test_monitor_api.py::test_snapshot_serialization_failure_is_typed_503 ran.
This matches the documented failure family in DEFECT_LESSONS.md #11, but is not
a full-suite pass or proof that every remaining test was exercised. No source
change or hidden skip was made to suppress the crash. Minimum requested identity,
monitor, cockpit and affected desktop regression gates pass in final-focused.xml.

## 2026-10-21 Author Repair: Pre-Header Transport Bounds

Explicit AUTHOR repair assignment for PR #691 continues this same bounded claim
and branch from clean `f7a4d044494c7643dd7ab45cadb7768befcdba9c`.
Independent report `runs/WO-P1-689/review-20261021-/result.md` SHA256
`cc2ea48b9b85e1f6bcb675d51b7f7fdbc232ff8e7ee34ed792b2307c772357e0`
has one confirmed P1. Shared continuity remains integrator-owned and unchanged.

RED: real CLI fixture, both 40 idle sockets and 40 incomplete-header sockets
remained registered after 5.5s; valid bearer health returned503 in both cases
(`repair-red.xml`,2 failed). ASGI cannot observe those connections. Uvicorn's
existing concurrency setting is post-header; timeout_notify is a worker callback,
not a request-header deadline. No new provider or coordination primitive needed.

Repair: explicit h11 transport protocol rejects excess accepted sockets before
registration/parsing; retains limit_concurrency=config.max_connections and adjusts
the upstream inclusive-boundary check inside the protocol. Header deadline5s
(configurable >0..5) starts at admission, never renews on trickle, covers reused
partial headers, cancels on complete headers/disconnect/shutdown. Keep-alive5s
and graceful shutdown10s retained; WebSocket protocol disabled explicitly.
This protection is wired through the CLI's Uvicorn configuration; create_app by
itself is ASGI-only and cannot secure another embedding's HTTP transport.

GREEN: `repair-api-final.xml`:58 passed (original47 plus11 new cases); both
40-socket attacks bounded to <=32 retained connections, then0, all peer sockets
closed and authenticated health200. Configured-cap boundary, immediate excess
refusal, fixed trickle/reused-header deadlines, live SSE timer cancellation and
two start/stop cycles with pending-header cleanup pass. Earlier repair-green.xml
and repair-api.xml retain intermediate Windows socket-error/fixture-race failures;
they are investigation history, not final GREEN evidence.
`repair-regressions.xml`:155 passed = identity33 + monitor30 + cockpit92.
pip check and git diff --check PASS. Full repository suite not rerun for this
bounded repair; prior full-suite crash limitation above remains unchanged.

Next gate: focused independent exact-new-SHA review and exact-head CI by integrator.
Author may commit/push this branch only; no PR/merge/GitHub posts/acceptance.
