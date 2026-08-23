# Changelog

All notable changes to A-Sunday Conductor are documented here.

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
