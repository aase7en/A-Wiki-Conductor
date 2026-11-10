# SundayFamily UX-1: Surface Audits

Date: 2026-11-10 | Issue: #739 | Design evidence, not runtime acceptance.

Method: code-verified at main@16b897a by delegated audit agents, 2026-11-10; feeds UX-1 design.
ผู้เขียนรวบรวมผล audit ที่ orchestrator ส่งมา ไม่ได้รัน shell, Git หรือทดสอบ runtime ซ้ำ
HEAD/branch/clean state เป็นข้อมูลจาก orchestrator ไม่ใช่ผลตรวจ Git ของผู้เขียน
Anchors ด้านล่างอ้างฐาน audit นี้; ชื่อไฟล์ Python อยู่ใต้ `src/a_conductor/`
หาก audit ให้เพียงชื่อไฟล์ จะใช้ file-level anchor โดยไม่สร้างเลขบรรทัดขึ้นเอง
รหัส T/M/W ใช้อ้างกลับจาก design packet; LOC เป็นค่าประมาณ ไม่ใช่ performance metric

## 1. Tk Desktop

### T1. Module Inventory

| Surface / file anchor | LOC / structure | บทบาท |
|---|---|---|
| `desktop_ui.py` | 6,791; god-class ~213 methods | Main window + dialogs |
| `desktop_control.py` | 1,315 | `DesktopControlService` facade |
| `desktop_app.py` | 181 | CLI entry + splash |
| `splash.py` | 167 | Splash |
| `gpu_particle_logo.py`, `interactive_logo.py` | 820 + 843 | Decoration |
| `setup_wizard.py` | 667 | OS setup |
| `i18n.py` | 517 | Thai / 中文 / English |
| `guide_html.py` | 248 | Embedded help |
| `serena_activity.py`, `update_checker`, `error_explanations_en`, `config_blurbs`, `folder_size`, `memory_presence` | Included in ~1,950 Tk-only support LOC | Diagnostics/help/support |

Desktop-only surface รวมประมาณ 12,000 LOC; decoration รวม splash/ส่วนเกี่ยวข้องประมาณ
1,830 LOC (~18% ตาม audit estimate ของ cosmetic surface) ไม่ใช่คำรับรองว่าจะลด RAM ได้ 18%

### T2. Main Window: One Window, No Tabs

ทุกช่วงบรรทัดในตารางนี้อ้าง `desktop_ui.py`

| พื้นที่ | Anchor | สิ่งที่ audit พบ |
|---|---|---|
| Header | `desktop_ui.py:1287-1397` | GPU logo, ONLINE/OFFLINE pulse, SLOTS/REGISTRY, Add Brain/Guide/Settings |
| Teaching strip | `desktop_ui.py:1399-1409` | Typewriter guidance |
| Workflow toolbar | `desktop_ui.py:1411-1440` | 9 worker-lifecycle buttons |
| Projects | `desktop_ui.py:1447-1500`, `desktop_ui.py:2887-2949` | List, native directory picker, assignment, memory-presence, Copy Activate = `SERENA_ACTIVATION_PROMPT` clipboard |
| System overview | `desktop_ui.py:1508-1605`, `desktop_ui.py:2730-2885` | PROJECTS / AI SLOTS LIVE / ACTIVE DRIFT / CONTROLLER / PROJECT DISK async walk; CPU/MEMORY/UPTIME + CPU sparkline |
| Scheduler registry | `desktop_ui.py:1607-1698` | Hidden ADVANCED worker-slot tree |
| AI execution slots | `desktop_ui.py:1700-1849`, `desktop_ui.py:5628-5855` | SLOT/PORT/CONNECTION/BOUND PROJECT/TUNNEL/AUTO/ACTIVE PROJECT [DRIFT]/LAST SWITCH; 11 lifecycle buttons; ≤15s live display, 15s auto-refresh, auto-start on launch |
| Monitor | `desktop_ui.py:1886-2349` | Connector state/PID/MEM/recovery/log tail; Graph via 2 askstring prompts; Cockpit lane projection |
| Activity/log | `desktop_ui.py:1853-1884` | Copy menu |
| Status bar | `desktop_ui.py:1828-1851` | Check Update via GitHub Releases; Donate |

### T3. Dialog Inventory

| Dialog / anchor | รายละเอียด |
|---|---|
| Setup Wizard: `desktop_ui.py:3066-3354`; `setup_wizard.py` | 6 steps: uv/Python/Serena/tunnel-client check, installs, first connector Filesystem/Serena/Stitch backend, Tunnel ID + API key DPAPI encryption, finish; auto-open when zero connectors |
| Runtime Setup: `desktop_ui.py:3910-4063` | Per-worker runtime |
| Preferences: `desktop_ui.py:4285-5198` | Language combo; MODELS & AGENTS provider trust class, egress boundary, concurrency, evidence |
| Guide: `desktop_ui.py:5199-5355` | tkinterweb |
| Worker Config: `desktop_ui.py:5357-5627` | Serena language backend, ENGINE_TOOLS grid, LANGUAGES, MODES |
| Second Brain: `desktop_ui.py:6366-6519` | 2 folders + 2 must-read files, A-Wiki defaults |
| Other dialogs: `desktop_ui.py` (file-level audit anchor) | Add/Rename Worker; Add/Edit/Rename/Delete Connector; delete zip backup to Drive when folder exists; tunnel regex; rebind; Set Tunnel ID; Check Engine Update for Serena upstream; ~60 Thai/EN error codes; close-request stop-all confirm |

### T4. Audit Classification (Not A Retirement Authorization)

| Class | Features |
|---|---|
| A: carry over | Setup Wizard OS-install path (trim Serena), Guide+i18n, Preferences language/shutdown, Second Brain, Projects read-only diagnostics, Activity log, Cockpit+Graph, system metrics, error explanations, self-update, Donate |
| B: retire Serena-era UI | Worker slots/scheduler/Add-Rename-Release Worker, Start/Stop/Restart Worker, Copy Activate, Runtime Setup, Worker Config, ACTIVE PROJECT drift, Check Engine Update, supervised flag |
| C: design decision | Connector lifecycle (SundayMCP Windows/Mac tunnel runtime still live); Models & Agents read-only vs editor; tunnel-ID management; rebind; delete+Drive backup; Connector log tail; decoration |

Classification evidence: T2/T3 anchors; supervised flag and auxiliary behavior are
file-level findings in `desktop_ui.py` / `desktop_control.py`, not newly line-verified here.

### T5. Tk-Only Capabilities And Test Limits

File-level anchors: `desktop_control.py`, `setup_wizard.py`, `folder_size`,
`memory_presence`, `update_checker`; dialog anchors T2/T3.
No web equivalent was found for real process start/stop/reap, native directory picker,
DPAPI encryption, system package installation, folder-size/memory-presence probes,
connector log tail, or self-update. The web command endpoint is an accepted stub (W3).
No systray/login-item/registry feature was found even in Tk (`desktop_app.py`, `desktop_ui.py`).
Audit counted ~26 GUI test files under `tests/`, using headless-skip patterns;
smoke is headless-safe; effective Tk coverage is Windows-desktop-only, not OS parity.
`AGENTS.md:74-81` documents entrypoints, smoke isolation, GPU workaround and packaging.

## 2. Monitor Page And Inspector

### M1. Page, Transport And Render Contract

| File / anchor | Verified audit finding |
|---|---|
| `monitor_page.py` (`_PAGE`, file-level) | Compile-time constant HTML; vanilla JS; Health / Timeline / STM partitions / Correlation / Inspector; `esc()` on sinks |
| `monitor_page.py` (file-level) | Fragment `#token=` stripped by `history.replaceState`; token memory-only; same-origin Bearer GET `/snapshot`; 403 halts polling |
| `monitor_page.py` (file-level) | CSP `default-src 'none'; style-src/script-src 'unsafe-inline'; connect-src 'self'`; healthy poll 2000ms, exponential backoff to 30000ms |
| `monitor_api.py`, `desktop_app.py`, `web_api.py` (file-level) | Legacy stdlib `/monitor` server has test callers but no production entrypoint; production `a-conductor-web` serves no HTML |
| `monitor_page.py:137-174` | Tools/Hooks/Skills groups; name/state/detail/provenance; last 128 rows; detail = phase / hook_class / routing_hint (+ deprecated/duplicate) |
| `monitor_page.py:137-174` | READY/UNKNOWN/STALE/DISCONNECTED allowlist (+ skills-only AVAILABLE); projection failure badge + `INSPECTOR_NOT_PROVIDED` / `INSPECTOR_PROJECTION_INVALID`; per-group truncated badge |

Truth colors: READY/AVAILABLE `#8f8`, UNKNOWN `#fc6`, STALE `#f96`, DEGRADED
`#f66`, DISCONNECTED `#c9f`. UNKNOWN/STALE/DEGRADED never healthy.
The page row allowlist is narrower than the five-state backend vocabulary:
target React must preserve backend DEGRADED, not infer READY from page fallback behavior.

### M2. Projection And Collectors

| File-level anchor | Contract / limitation |
|---|---|
| `inspector_projection.py` | Pure/no-I/O; frozen rows; InspectorState READY/UNKNOWN/STALE/DISCONNECTED/DEGRADED; ToolPhase REGISTERED/STARTED/CONNECTED/INJECTED/UNKNOWN is metadata, not runtime readiness |
| `inspector_projection.py` | 4096 raw / 200 display character bounds; whole-field `[REDACTED]`; `deque(maxlen=128)` per section; counts recomputed from retained rows; truncated+dropped evidence |
| `inspector_sources.py` | Real read-only tool collectors from instance markers + readyz; transport evidence → DISCONNECTED; other probe failure → DEGRADED `TOOL_PROBE_FAILED` |
| `inspector_sources.py` | Static hook contracts → UNKNOWN, `contract-only` provenance; contract presence never proves hook liveness |
| `inspector_sources.py` | A-Wiki schema-v3 `skills-registry.json`; mtime freshness default 7 days; AVAILABLE requires inside-root existing path, not execution authorization; deprecated/duplicate derived |
| `inspector_sources.py` | Collector code-only notes exist but are not surfaced: `TOOLS_DISCOVERY_UNAVAILABLE`, `TOOL_MARKER_UNREADABLE:<sha12>`, etc. |

### M3. Wiring Reality And Safe Display

File-level anchors: `monitor_projection.py`, `inspector_sources.py`, `web_api.py`.
No production caller invokes `build_monitor_views` or `collect_local_*`; callers found
were tests. FastAPI `/api/v1/snapshot` pins monitor to
`{"error":"MONITOR_PROJECTION_UNAVAILABLE"}`. No Inspector endpoint exists in `web_api.py`.
Slice 2 must wire collectors → provider → snapshot and surface sanitized notes.

| Bound | Rendering implication |
|---|---|
| 128 rows / section | Show retained counts, `truncated`, `dropped`; never call retained count a full inventory |
| Safe integer range through ±2^53 | Preserve source validation; don't silently coerce oversized IDs/counters |
| Unknown enum | UNKNOWN, never READY |
| Free text ≤200 display chars | Escaped plain text; preserve source caps; never reveal hidden raw text |
| Secret family | Authorization/Bearer, URL userinfo, share links, PEM, sk-/ghp_/tunnel_<32hex>/akia/xox* prefixes; authorization/bearer/token/secret/password/api-key/credential/cookie assignments including Unicode confusables → whole-field `[REDACTED]` |
| Tunnel pairing | Never emit tunnel IDs; only `tunnel_configured` boolean |
| Auth token | Never in page bytes, URLs, logs or error bodies; token-entry/session storage is a separate auth boundary |

Source of these bounds: `inspector_projection.py`; repair history and frozen
contract: `../work-orders/WO-P1-739-tool-hook-skill-inspector.md:80-116,184-392`.

## 3. React Web Surface

### W1. Stack And Delivery

File-level audit anchors: `web/sunday-family/package.json`, `web/sunday-family/src/`,
`web/sunday-family/vite.config.ts`, `web/sunday-family/public/sw.js`, `web_api.py`.
React 19 / Vite 6 / TS 5.9 strict; flat 13-file src, no router/state library;
single-page anchors, 79-line near-black monospace CSS, grid and 899px breakpoint;
manual fetch wrapper with runtime response validation.
PWA standalone manifest/manual service worker: API/SSE/auth never cached,
static cache-first, 64-entry precache bound, fail-closed shell, prod registration,
install prompt. Dev 5173 strict port proxies loopback to 127.0.0.1:8756.
Production `dist/` is gitignored and UN-SERVED: no StaticFiles/HTML route in
`web_api.py`. Default port 8756 and exact host:port auth gates must survive packaging.

### W2. Existing UI And Gaps

| File-level anchor under `web/sunday-family/src/` | State today |
|---|---|
| `TokenGate` component | sessionStorage, never URL; per-tab, new window re-prompts |
| `SnapshotView` component | Lane table; honest stale/degraded banners |
| Connectors panel | List/rename/delete; session-scoped; explicit “Not persisted Tk connectors” |
| `MetricsPanel` component | Null → Unavailable, not zero |
| `HealthIndicator`, `LiveStream` components | Health 30s; SSE status bar |
| Activity surface | Honest placeholder |
| src inventory | No worker CRUD/create connector UI; no projects/claims/roadmap, hook/skill/batch/allowlist settings, tool usage, Jev, cross-device fleet, or i18n; English-only copy |

Component names are audit search anchors, not invented component file paths.

### W3. Backend API Inventory

All routes below are file-level findings in `web_api.py`; route names are exact search anchors.

| API | Current behavior |
|---|---|
| GET `/api/v1/health` | `degraded` hardcoded true; `OPTIONAL_MONITOR_UNAVAILABLE` |
| GET `/api/v1/snapshot`, `/monitor/snapshot` | `public_snapshot`: cockpit.lanes identity/state/markers/blocker/gates/origin_display; monitor error stub; stale/degraded_observability |
| GET `/api/v1/metrics` | CPU/memory/uptime |
| GET `/api/v1/stream`, `/events` | SSE; 15s heartbeat; 300s cap |
| POST `/workers`, DELETE `/workers/{id}` | Mutation routes; not called by frontend |
| POST `/workers/{id}/command` | STUB: accepted response, no execution; not called by frontend |
| POST `/connectors` | Session connector create, not called by frontend |
| GET `/connectors`, PATCH `/connectors/{id}`, DELETE `/connectors/{id}` | Session metadata, not persisted Tk registry; rename; STOPPED-only delete |
| GET `/mutations` | Audit ≤100; not called by frontend |

Mutation gates: X-Confirm + 1/min rate limit. Auth: loopback or Tailscale
100.64.0.0/10; Host/Origin/duplicate-header gates; hmac Bearer.
These existing routes do not prove accepted Command Gateway integration or permission
to expose controls in UX-1. Network behavior is evidence, not a new remote-mode policy.

### W4. Prior Commitments And Charter Coverage

| Charter area | Coverage at audit base | Evidence |
|---|---|---|
| Project/work tracking | PARTIAL: lanes only | W2 `SnapshotView`; W3 snapshot |
| Windows + Mac fleet | MISSING | W2 src inventory; W3 session connectors are not fleet |
| Tool usage | MISSING | W2 inventory; M3 unwired Inspector |
| Hook/skill/batch settings | MISSING | W2 inventory |
| Jev corner | MISSING; advisory-only required | W2 inventory; runtime boundary `:18` |

`WO-P1-698` parity checklist records persisted Tk connector authority not wired to
web registry. Roadmap `2026-09-26-sunday-family-web-pwa-roadmap.md:80-86` proposes
Overview/Projects/Fleet/Executions/Roadmap/Claims/Hooks/Providers/Runtime/Logs/Settings,
mostly unbuilt (W2). SF-WEB-0 read slices exclude command routes and defer project,
fleet and execution DTOs to child WOs (prior roadmap/contract context, not API claims).
Runtime boundary `sunday-family-web-runtime-boundary-v1.md:102-117` permits optional
bounded launchers, forbids premature Tk retirement; `:47-70` forbids browser authority.
Auto-connect token handoff needs its own security review: URL/file/stdout handoff
is deliberately excluded from this design; current token entry remains manual (W2).

## 4. Cross-Surface Synthesis

- Overlap: metrics, lanes/cockpit, status and logs repeat across T2/M1/W2, but have different transport/readiness and auth boundaries. Reuse normalized evidence, not three UI authorities.
- Dispersion: onboarding/secrets/process operations remain Tk-only (T5); Inspector exists as bounded code and legacy page rendering (M1/M2), not a production feed (M3).
- Wiring reality: production FastAPI provides lanes/metrics/SSE but no live Inspector or HTML/static hosting (W1/W3). A mockup cannot imply either gap is closed.
- Registry mismatch: session web connectors are not persisted Tk connectors (W2/W3/W4); they must not be relabeled as Windows/Mac fleet evidence.
- Consolidation target: one Thai-first presentation over existing authority; no second scheduler, claim store, direct SRM controls, or token bypass (runtime boundary `:47-100`).
- Tk carry-over is capability migration, not copying the worker-era UI or declaring retirement; parity/OS/recovery/rollback gate remains binding (`:112-117`).
