# Changelog

All notable changes to A-Sunday Conductor are documented here.

## [0.7.0] — 2026-08-26

### Added
- **Inline row actions** — `Edit` cell in every PROJECTS/WORKERS/CONNECTORS row + `+ Add` row when a table is empty (PR #81)
- **Unified connector editor** — one dialog for alias + Tunnel ID + project path (PR #81)
- **Live connector states** — CONNECTORS table auto-refreshes every 15s without pressing Rescan (PR #90)
- **Masked tunnel pairing** — TUNNEL column shows last 4 chars (e.g. `...e3f1`) for instant ChatGPT-side matching (PR #90)
- **Graph Engineering foundation** — TaskGraph/TaskNode/TaskEdge domain + acyclic builder + SQLite store (PRs #91-92, backend only)

### Fixed
- **Singleton dialogs** — Donate/Guide/Preferences/Add Worker/Brain Config/Edit Connector no longer stack duplicate windows; re-open lifts the existing one (WO-P1-069)
- **Close-time confirm** — the app asks before stopping RUNNING connectors, preventing silent chat disconnection (PR #90, WO-P1-068)
- **Rescan summary** — logs "พบ N ตัวเชื่อม: X READY, Y STOPPED" instead of appearing silent (PR #90)
- **PS1 UTF-8 BOM** — generated `.ps1` files carry a BOM so Thai project paths survive PowerShell 5.1 (PR #85)
- **Quoted project paths** — `--project` substitutions are double-quoted so spaces can't split the MCP command line (PR #85)
- **Brain activation warning** — saving the Second Brain now states that running connectors need a restart for chats to pick it up (PR #82, WO-P1-067)
- **Wizard instance numbering** — new instances number past the fleet (Sunday-Worker-2, 3, ...) instead of always Sunday-Worker-1 (PR #81)
- **PROJECTS row height** — two-line rows (name + path) visible without clipping (PR #81)
- **Donate QR bundled** — PromptPay QR ships inside every build (PR #80)
- **GPU context unbind** — GL context released after render so Tk text doesn't corrupt (PR #87)

## [0.6.0] — 2026-08-26

### Added
- **Terminal command center** — native Tk/Ttk operational layout with the Sunday Family particle portrait, first-class Add Brain action, and responsive compact/standard/wide workflows
- **Real system overview** — native CPU, RAM, and session-uptime sampling with bounded CPU history and no periodic subprocesses
- **GPU Sunday Family renderer** — optional OpenGL particle portrait with subtle pointer gaze/parallax and an automatic Canvas fallback
- **Inline row actions** — every PROJECTS/WORKERS/CONNECTORS row carries an `Edit` action; empty tables show a `+ Add ...` row (PR #81)
- **Unified connector editor** — Edit on a connector opens one dialog for alias, Tunnel ID, and project path (PR #81)
- **Donate QR shipped** — `assets/donate-promptpay-qr.png` bundled with every build; DONATE.md carries the PromptPay/TrueWallet number (PR #80)
- **Brain activation warning** — saving the Second Brain now states that running connectors must restart for chats to pick it up (WO-P1-067, PR #82)

### Fixed
- **Compact reachability** — action rows and Worker/Connector/Monitor/Activity surfaces remain selectable and readable at the supported minimum window size
- **Deterministic shutdown** — Tk timers, monitor work, renderer callbacks, contexts, and the owned executor are released when the window closes or is destroyed directly
- **Cross-platform metrics** — Linux CPU accounting excludes guest time and unavailable platform metrics remain explicitly unknown
- **Live language surfaces** — Thai, Simplified Chinese, and English explanations refresh without translating canonical English action labels
- **Wizard fleet numbering** — newly created instances number past the existing fleet instead of reusing `Sunday-Worker-1` (PR #81)
- **PROJECTS row readability** — sidebar rows are tall enough to show name + path (PR #81)
- **Fleet-safe monitor tests** — test fixtures no longer probe the live fleet port 18011 (PR #81)
- **Generated PowerShell reliability** — generated `.ps1` files use a UTF-8 BOM and quoted `--project` paths; Windows CI isolates the subprocess-heavy local-instance suite from unrelated pytest state (PR #85)
- **GPU/Tk repaint isolation** — native WGL/GLX contexts are unbound after map/resize/display callbacks and bounded buffer rebuilds so ordinary Tk/GDI repaints do not inherit stale GL state (PR #87)

## [0.5.0] — 2026-08-24

### Added
- **PanedWindow layout** — every panel is drag-resizable; no more disappearing panels
- **Interactive particle-face logo** — 120px header canvas whose eyes track the pointer with bounded, gentle motion
- **Responsive button grids** — actions wrap at narrow widths and flow in one row on wide windows
- **English action labels** — canonical English button text across the app regardless of help language
- **Tri-lingual help** — Thai / 中文 / English tooltips and teaching text (zh-CN falls back to English where untranslated)

### Fixed
- **Splash screen** — now a `Toplevel` over the single Tk root; the main window reliably appears after the splash
- **+Worker dialog** — widget values are read before the dialog is destroyed, so workers actually get added
- **PowerShell spawn storm** — connector memory sampling switched to native `ctypes` calls (zero periodic process spawns; see DEFECT_LESSONS #1)

## [0.4.3] — 2026-08-24

### Added
- **Donate dialog** — button in status bar; shows GitHub Sponsors link + PromptPay/TrueWallet QR code (auto-detected from `assets/donate-promptpay-qr.png`)
- **CHANGELOG.md** — this file

### Fixed
- **DPAPI encryption** — wizard now genuinely encrypts the API key with Windows CryptProtectData (was plaintext despite `.dpapi` filename)

## [0.4.2] — 2026-08-24

### Added
- **Google Stitch backend** — 4th MCP backend option in Setup Wizard; generates `node <path>/artifact-keyserver.mjs` YAML; saves Stitch API key to `sti-key.txt`

## [0.4.1] — 2026-08-24

### Added
- **Node.js auto-install** — wizard downloads Node.js v22 LTS portable ZIP (no admin)
- **Backend selection** — wizard step 3 offers Filesystem (easy) vs Serena (full code analysis)

## [0.4.0] — 2026-08-23

### Added
- **Setup Wizard** — one-stop installer that auto-downloads uv + Python 3.13 + Serena + tunnel-client + creates the first connector instance; opens automatically on first run when no connectors exist

## [0.3.2] — 2026-08-23

### Added
- **Brand watermark** — status bar (bottom-right) with app name, version, developer credits
- **Check Update button** — checks GitHub Releases for newer versions, opens download page
- **MIT License** — fully open source
- **GitHub Sponsors** — `.github/FUNDING.yml` + sponsor badge in README
- **Privacy Policy** (PRIVACY.md) — local-only app, no telemetry
- **Security Policy** (SECURITY.md) — vulnerability reporting

## [0.3.1] — 2026-08-23

### Added
- **Splash screen** — pixel logo + animated particles + version/credits on launch

## [0.3.0] — 2026-08-23

### Added
- **Full bilingual UI** (Thai ↔ English) — buttons, tooltips, error popups, config explanations, user guide
- **MONITOR panel** — live state/PID/memory/log-tail per connector
- **Clean shutdown** — closing the app stops all connectors and reaps processes
- **UX polish** — horizontal scrolling, hover full-path tooltip, right-click copy
- **Cross-platform groundwork** — platform-aware paths/processes, CI on Windows+Ubuntu+macOS
- **Connector management** — create (+ Connector), rename, safe-delete with Drive backups
- **Worker management** — add / rename / delete worker slots dynamically

## [0.2.x] — 2026-08-22

### Added
- E2E real-system test suite (24 adversarial scenarios)
- Instance rebind (change project without recreating)
- Second Brain injection
- Toggle-ification of all config fields
- Upstream check (GitHub API)
- Initial public release (v0.2.0)

---

Format: [Keep a Changelog](https://keepachangelog.com/)
