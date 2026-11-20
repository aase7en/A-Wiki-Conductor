# WO-P1-698 — SF-WEB-6: Web/Tk parity

Issue: #698
Status: P2 AUTHOR CANDIDATE (independent R3 acceptance pending)
Risk: R3 (mutation authority extension)
Topology: CONTROL_PLANE_ONLY

## Parity Matrix Summary
- At parity: 5 features (status, start/stop, assign, live monitor)
- P1 gaps (this slice): Worker create/delete, Connector create
- P2 author slice: session connector rename/delete, native CPU/RAM metrics
- Remaining parity gap: persisted Tk connector authority is not wired to the web registry
- Tk retirement: NOT ready until P1 closes

## P1 Server Endpoints (this slice)
- POST /api/v1/workers — create worker slot
- DELETE /api/v1/workers/{worker_id} — delete stopped worker
- POST /api/v1/connectors — create connector with project + tunnel_id

## P1 Client Components (next slice)
- WorkerCreateButton + dialog
- WorkerDeleteButton + confirmation
- ConnectorCreateWizard (simplified)

## Tests
- tests/test_web_api_p1_gaps.py — server endpoint tests

## P2 Author Extension (2026-10-23)

- Owner: P2 AUTHOR, claim `WO-P1-698-P2-AUTHOR-20261023`, Issue comment 6372211250.
- Base: `de5e231fe85754191ffee102682c5b5eece97567`; branch `feat/wo698-parity-p2`;
  worktree `A:/GitHub/_worktrees/AWC-wo698-parity-p2` on Windows device
  `ff685af5-9031-4b3b-84ff-61dc8f1a840c`.
- R3 / CONTROL_PLANE_ONLY. Delivery is commit + push only, NO PR or merge.
- Scope: existing web API mutation section, minimal connector PATCH admission in
  `web_api_auth.py`, focused Python tests, web shell source/component tests, this WO.
  Required web integration prerequisite: `vite.config.ts` and `tests/proxy.test.ts`
  exact P2 GET/PATCH/DELETE allowlist; existing proxy otherwise refuses all P2 calls.
  Shared continuity fold remains integrator-owned. No installed DB, config, process,
  credential, provider or persistent connector authority changes.
- Prerequisites discovered: closure-local request DTOs cannot resolve with deferred
  annotations; `_stamp({})` rejects all mutation timestamps. Repair these minimally
  and enable P1 regression tests rather than retaining a blanket skip.
- Authority/failure model: retain bearer, exact Host/Origin, confirmation, no-store
  and existing mutation-rate policy. PATCH may rename only the identified existing
  connector; DELETE requires an explicit STOPPED state, never unknown/running.
  Do not accept client-supplied lifecycle state. No endpoint starts/stops processes.
- Extend the existing session-only connector registry with list/rename/delete; list
  DTOs expose ID, name and state only, never project paths or tunnel IDs. Label this
  limitation in UI/API. This is NOT persisted Tk connector parity or Tk retirement.
- Metrics reuse `SystemMetricsSampler` with one sampler per app; no subprocesses,
  no fabricated zeros for unavailable readings, authenticated no-store GET.
- Acceptance: connector rename/delete success and refusal (auth, confirmation,
  malformed name, missing ID, running/unknown state, rate limit); real sampler DTO
  and unsupported-metric nulls; client render, confirmation/cancel, request failure,
  refresh and unmount cleanup tests; related server tests + client build/test green.
- Evidence: focused test/build output and final checkpoint here, detailed runtime
  evidence may use `runs/WO-P1-698/`. Independent R3 review/acceptance remains pending
  after AUTHOR delivery; do not self-accept or claim LIVE validation.

### P2 Verification Checkpoint

- Implemented authenticated `GET /api/v1/metrics` using one native sampler per app;
  `GET /api/v1/connectors` sanitized app-session DTO; confirmed/rate-limited
  `PATCH /api/v1/connectors/{id}` and stopped-only `DELETE` with audit timestamps.
- Request models moved to module scope to resolve deferred annotations. Replaced
  invalid `_stamp({})` mutation calls with aware UTC timestamps. Restored both
  P1 CRUD and SF-WEB-4 mutation tests (no new test skips).
- Client: `ConnectorRow`, `ConnectorsPanel`, `MetricsPanel`, authenticated no-store
  requests, explicit delete confirmation, inline rename/cancel, refresh and request
  cancellation. Error refresh removes old metrics rather than displaying stale data
  as current. Proxy allows exact P2 calls only and retains Host/Origin admission.
- RED: new API contract initially 15 failed / 2 passed after correcting a test
  fixture `httpx.Headers.update` usage; failures included existing POST 422 and
  PATCH 405, absent metrics sampler. GREEN targeted P1/P2 27 passed before final
  additional rename-rate-limit test.
- Final Python: `python -m pytest tests/test_web_api.py tests/test_web_api_mutations.py
  tests/test_web_api_p1_gaps.py tests/test_web_api_p2_gaps.py tests/test_system_metrics.py
  tests/test_work_order_identity.py -q --tb=short`: **129 passed, 6 existing skips**.
  Skips remain the legacy read-only route assertion (5) and headless-import check (1);
  no full-repository regression or hosted CI certificate is claimed.
- Final client: `npm test`: **70 passed** (7 files), including real Vite proxy
  forwarding with preserved bearer/confirmation and negative Host/Origin/routes.
  `npm run build`: PASS, TypeScript + Vite 6.4.5, 39 modules. Locked install:
  `npm ci --ignore-scripts`: 154 packages, audit reports 0 vulnerabilities.
- Native Windows sampler probe returned actual CPU 20.8333%, used RAM 15180759040
  of 17061388288 bytes; these are observation-time evidence, not fixture constants.
- Playwright fixture-only browser smoke rendered CPU/RAM/session rows, rename,
  delete cancel/confirm and disconnect. Separate returned layout proof:
  viewport/document widths **1280/1280** and **390/390**; session cleared on disconnect.
  No live production token, installed DB, real connector or process was touched.
  Preview processes stopped. Integrated Browser binding was unavailable; existing
  Playwright browser was used as fallback.
- AUTHOR-only delivery: candidate is not independent-reviewed/accepted, and live
  persisted connector parity / Tk retirement is NOT complete. Existing P1 worker
  command route still returns acceptance metadata, not actual process execution;
  that pre-existing behavior was not expanded into runtime authority here.
- Next safe action: integrator reviews exact pushed SHA and decides the persisted
  connector authority successor. Shared `CURRENT-WORK.md` / `handoff.md` fold is
  reserved to integrator to avoid cross-lane conflicts. No PR/merge requested.
- Cleanup: retained worktree for review; no deletion/branch cleanup authority.
