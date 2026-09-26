# Sunday Family Web/PWA Control Surface Roadmap — 2026-09-26

Status: ACTIVE ROADMAP CANDIDATE
Work Order: `WO-P1-555`
Issue: #555
Topology: CONTROL_PLANE_ONLY planning; future implementation may require exact-SHA CROSS_REPO compatibility work.

## 0. Executive decision

Sunday Family becomes the long-term cross-platform operator experience for A-Sunday Conductor + SunDayRemoteMCP.

`HEADLESS CONTROL/EXECUTION CORE + WEB/PWA OPERATOR SURFACE`

not `NATIVE UI PER OS`, and not `SERENA DASHBOARD AS PRODUCT UI`.

Framework baseline:
- **Frontend:** React + TypeScript + Vite + PWA.
- **Backend authority/API:** A-Conductor-owned Python service; preferred future framework FastAPI/Starlette + Uvicorn after child-WO dependency/provenance review.
- **Read transport:** REST/JSON snapshots + SSE live Monitor stream.
- **Command transport:** bounded REST command requests through A-Conductor Command Gateway.
- **Execution:** SunDayRemoteMCP remains headless execution/capability substrate.
- **Optional native launchers:** startup/open-URL convenience only; no second UI.
- **Default network exposure:** loopback only.

## 1. Migration rule

The existing Tk/Ttk direction remains valid for the immediate LOCAL-USABLE-1 product gate. It is not the preferred long-term Sunday Family surface.

Do not stop current critical-path work for a rewrite.

`FINISH THE READ-ONLY TRUTH SEAM -> REUSE IT FROM WEB`

## 2. Authority remains unchanged

### A-Sunday Conductor owns
- task/work-order truth;
- claim/lease/mutation authority;
- roadmap and scheduling;
- provider admission;
- retry/replay authorization;
- review/acceptance/merge/release;
- Command Gateway;
- Monitor Projection/API;
- operator authorization policy.

### SunDayRemoteMCP owns
- filesystem/search/edit capabilities;
- Git inspection;
- process/terminal execution;
- durable execution supervision;
- output/status/cancel/harvest/recover;
- execution-local safety;
- semantic/LSP capability seams.

### Sunday Family Web/PWA owns
- presentation;
- responsive navigation;
- read-only monitor rendering;
- user intent capture for bounded commands;
- PWA install UX;
- local help/operator guidance.

It never owns task truth or mutation authority.

## 3. Relationship to current LOCAL-USABLE-1

Do not derail the active critical path:

`#433 RUNTIME-ACT-1 -> #429 COCKPIT-1B -> LOCAL-USABLE-1`

LOCAL-USABLE-1 may complete using the accepted Tk/Ttk Runtime Cockpit.
Web/PWA starts from the stable seams produced by Runtime Cockpit/Monitor Projection, runtime authority binding, Hook/STM observability, and Command Gateway contracts.

## 4. Sunday Family information architecture

Primary navigation: Overview, Projects, Fleet, Executions, Roadmap, Claims, Hooks, Providers, Runtime, Logs, Settings.

Overview should answer quickly: what is active, running, blocked/waiting, who owns each lane, exact task/claim/HEAD, what is ready to harvest, next safe action, and whether state is stale/degraded.

Keep the existing CLI-inspired, compact, information-dense Sunday Family visual direction.

## 5. Serena transition

`SERENA_DASHBOARD_AUTO_OPEN = FALSE`

Sunday Family may expose selected accepted Serena diagnostics: semantic runtime readiness, active project binding, language backend, capability subset, and health/error state.
Deep Serena inspection remains an explicit manual diagnostic action.
The roadmap does not authorize copying GPL Serena application code into permissive A-Sunday/SRM code.

## 6. Delivery phases

### SF-WEB-0 — Contract and dependency gate
Freeze API threat model, dependency/provenance decision, port/bind conventions, and browser-to-authority trust boundary.

### SF-WEB-1 — Read-only Monitor API
Versioned snapshot endpoints, SSE events, health/readiness, explicit stale/unknown provenance, no command routes.

### SF-WEB-2 — Sunday Family Web shell
React + TypeScript + Vite responsive shell with read-only Overview/Fleet/Runtime/Activity views and no consequential controls.

### SF-WEB-3 — PWA/local install experience
Manifest/icons, installable PWA, static-asset service worker, stale/disconnected UX, optional launcher that opens the local URL/PWA.

### SF-WEB-4 — Command Gateway controls
Add only bounded actions whose authority already exists. Every action shows target identity, current claim/version, accepted/rejected result, and resulting authoritative state. No arbitrary shell/argv/prompt endpoint.

### SF-WEB-5 — Cross-platform service packaging
One backend/service story for Windows, macOS, Linux, Raspberry Pi, and Umbrel/headless Linux. Native launchers remain optional convenience shims.

### SF-WEB-6 — Parity and Tk/Ttk retirement decision
Build an explicit parity matrix. Tk/Ttk becomes fallback/legacy only after required Web/PWA capabilities and rollback gates pass.

### SF-WEB-7 — Authenticated remote operator mode
Later, not a LOCAL-USABLE blocker. Require explicit opt-in, authentication, TLS, origin policy, no direct SRM exposure, and Command Gateway-only consequential control.

## 7. API design baseline

Read examples:
- `GET /api/v1/health`
- `GET /api/v1/monitor/snapshot`
- `GET /api/v1/projects`
- `GET /api/v1/fleet`
- `GET /api/v1/executions`
- `GET /api/v1/events` via SSE

Future command shape: `POST /api/v1/commands` with bounded action vocabulary and expected-version/identity fields.

Never expose raw shell, arbitrary argv/SQL, provider tokens, unrestricted file paths, direct Git mutation, or direct SRM tool execution.

## 8. Security and privacy

Required: loopback default, explicit port, strict origin policy, secret redaction, bounded payloads, anti-CSRF/session protection for mutations, safe log projection, fail-closed unknown command authority, and PWA caches that exclude secrets and authoritative mutable state.

Remote mode gets a separate threat model and acceptance gate.

## 9. Cross-platform verification

Cover Windows, macOS, Linux, Chromium-family browser, a second standards-compatible browser where practical, narrow/mobile viewport, Pi/headless service smoke when applicable, PWA installability, service restart/recovery, stale/offline rendering, and no-secret scans.

## 10. Framework ownership

A-Wiki-Conductor owns contracts, Monitor/Command service, Sunday Family frontend unless a later ADR proves a separate repo is better, packaging integration, UI/API tests, and authority/security policy.

SunDayRemoteMCP remains headless. A future CROSS_REPO WO may add execution-local events/capabilities, but never browser authority, Command Gateway, project scheduler, or UI state store.

## 11. Worktree/branch lifecycle for marathon automation

A completed lane may delete its task worktree and local/remote branch only after durable proof that the PR/commit is merged or formally abandoned, claim released, no running/unknown delegated execution references it, no unharvested result remains, no dependent worktree/PR remains, and required post-main verification is complete.

If GitHub/server policy rejects deletion, emit a typed cleanup blocker, preserve the branch/worktree, notify the human of the exact permission/protection gate, and continue independent roadmap work. Never force-delete or rewrite branch protection.

## 12. Priority

1. Complete active LOCAL-USABLE-1 prerequisites.
2. Stabilize normalized Monitor truth/API prerequisites.
3. Start SF-WEB-0/1 in disjoint capacity.
4. Build read-only Web/PWA before commands.
5. Add Command Gateway controls only after read-only proof.
6. Package cross-platform.
7. Decide Tk/Ttk retirement only after parity.

The Web/PWA direction supersedes the old **long-term** Tk/Ttk-only framework choice but does not invalidate current accepted Tk/Ttk work.
