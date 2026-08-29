<div align="center">

<img src="assets/logo-face.png" alt="A-Sunday Conductor Logo" width="120" height="120" style="border-radius: 12px;" />

[![Release](https://img.shields.io/github/v/release/aase7en/A-Wiki-Conductor?style=flat-square&color=blue)](https://github.com/aase7en/A-Wiki-Conductor/releases)
[![CI](https://github.com/aase7en/A-Wiki-Conductor/actions/workflows/ci.yml/badge.svg?style=flat-square)](https://github.com/aase7en/A-Wiki-Conductor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)]()
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub-ea4aaa?style=flat-square&logo=github)](https://github.com/sponsors/aase7en)

</div>

# A-Sunday Conductor

**A local autonomous control plane for coordinating AI agents, coding agents, MCP servers, and memory.**

Pure desktop application — no server, no cloud required. Ships as a native Windows app; only a handful of small Python dependencies (Pillow, plus ModernGL/pyopengltk on Windows for the optional GPU logo).

---

## Overview

A-Sunday Conductor manages your AI coding agents through Serena MCP connectors. Each connector is a tunnel between ChatGPT and a local Serena instance bound to a specific project. One OpenAI API key supports multiple tunnels, enabling parallel chat sessions across different codebases.

## Key Features

| Feature | Description |
|---------|-------------|
| Terminal command center | Dark Tk/Ttk operator UI: projects, workers, connectors, monitor, and copyable activity console |
| Inline row actions | Every table row carries an `Edit` action; empty tables show a `+ Add ...` row to guide first-time users |
| Real system overview | Measured CPU, RAM, and session uptime (native APIs, no background processes) |
| Setup Wizard | One-stop first-run installer (uv, Python, Serena, tunnel-client, optional Node.js) with 4 backend choices incl. Google Stitch |
| Connector fleet | Auto-discovers and manages Serena tunnel instances with health monitoring |
| One-click creation | Create new ChatGPT connectors with auto-assigned ports from validated templates |
| Live monitoring | Per-connector state, PID, memory usage, and log tail with 15-second refresh |
| Worker management | Dynamic worker slots (add, rename, delete) with no fixed limit |
| Engine configuration | Per-worker language backend, tool toggles, base modes, and timeouts |
| Second Brain | Inject brain rules from A-Wiki into every connector's system prompt (applies on connector start) |
| Project rebinding | Switch any connector's project without recreating it |
| Tri-lingual interface | Thai, English, and 中文 help/tooltips (action buttons stay English by design) |
| Clean shutdown | Closing the app stops all connectors and reaps stale processes |
| Drive backups | Connector deletion zips a backup to the A-Wiki-Data Google Drive layer |
| Update checking & Donate | In-app GitHub release checker; PromptPay/TrueWallet QR and GitHub Sponsors |

## Project Status & Roadmap

**Latest public release:** `v0.6.0` — Terminal Command Center + Real Monitor

**Current development version:** `0.7.0` — not released yet

**Current program state:** Sunday Family Multi-Model Agent Harness — **AHA-4 durable supervised backend assembly is merged; AHA-4A worker leasing is active in Draft PR #131**

> Direction: move from manually selecting individual workers/plugins toward one A-Sunday Conductor entry point that recovers SSoT, selects an eligible worker/model/harness, verifies evidence, falls back safely, and continues without prompt copy/paste.

### Delivery checklist

- [x] **v0.6.0 released** — terminal command center, real monitor, worker/connector management, Second Brain, installer/portable builds.
- [x] **AHA-0** — capability vocabulary gate (`CAPABLE != AUTHORIZED`).
- [x] **AHA-1** — provider/harness/trust/quota/dispatch contracts.
- [x] **AHA-2** — secure provider configuration + observed health/quota; `CONFIGURED != READY`.
- [x] **AHA-3** — bounded Claude Code harness adapter merged in PR #116 (`ab28dc7`); fake-runner/read-only gates and 3-OS CI proven.
- [x] **AHA-4** — durable graph dispatch + Claude durable backend + supervised runner + production assembly merged through PR #130.
- [ ] **AHA-4A — ACTIVE** — atomic worker lease broker work is owned by Draft PR #131; not complete until that lane passes its own review/CI/merge gates.
- [ ] **AHA-4B** — heartbeat, stale-owner recovery, quarantine, fairness/backpressure.
- [ ] **AHA-5** — GPT plan/review ↔ GLM implement/repair loop without human prompt copying.
- [ ] **AHA-6** — parallel independent READY tasks through isolated worktrees/scopes.
- [ ] **AHA-6B** — optional elastic worker capacity after fixed-pool correctness is proven.
- [ ] **AHA-7** — Models & Agents operator UI with health/quota/trust/selection reason.
- [ ] **AHA-8** — additional providers only after the contract is stable.

<details>
<summary><strong>Target autonomous loop</strong></summary>

```text
GOAL
  -> recover durable SSoT
  -> decompose READY tasks
  -> inspect worker/provider eligibility
  -> atomic lease / fallback
  -> execute bounded task packet
  -> collect evidence
  -> deterministic verify + independent review
  -> repair or checkpoint
  -> continue until complete
```

Worker fallback never steals an active worker: busy, owned, overlapping, dirty-unknown, unhealthy, or incompatible workers are skipped.

</details>

See [Agent Harness Accelerator](docs/plans/2026-08-28-sunday-family-agent-harness-accelerator.md) and [Worker Auto-Fallback + GLM-5.3 Benchmark](docs/plans/2026-08-28-worker-auto-fallback-and-glm-benchmark.md).

## Install

### Windows (recommended)

Download `A-Sunday-Conductor-Setup.exe` from [Releases](https://github.com/aase7en/A-Wiki-Conductor/releases) and run it. No admin rights required.

> If SmartScreen warns, click **More info > Run anyway**. This is normal for unsigned applications; code signing is pending.

### Portable

Download `A-Sunday.Conductor.exe` (the Portable build — GitHub renders the space in "A-Sunday Conductor.exe" as a dot) and run from anywhere.

### From source

```bash
git clone https://github.com/aase7en/A-Wiki-Conductor.git
cd A-Wiki-Conductor
python -m pip install -e .[test]
a-conductor
```

## Quick Start

```
1. Add Project        -> select a folder
2. Assign to Worker   -> click project (left) + worker (right) + Assign
3. Start              -> connector tunnel starts automatically
```

For ChatGPT connectors:

```
1. Create tunnel      -> OpenAI Platform > Settings > Tunnels
2. + Connector        -> name + project path + Tunnel ID
3. Start              -> wait for READY status
4. Create plugin      -> ChatGPT > create connector pointing to your tunnel
```

See the in-app Guide button for the full walkthrough (Thai or English).

## Architecture

```
+---------------------------------------------------+
|  A-Sunday Conductor (desktop app, Tk)              |
|    Projects / Workers / Connectors / Monitor       |
|    SQLite (registry, settings, preferences)        |
+---------------------------------------------------+
|  Connector instances (one per tunnel)              |
|    sunday-worker-N/ -> instance.ps1 + scripts     |
|    Serena engine (MCP server per connector)       |
+---------------------------------------------------+
|  OpenAI Secure MCP Tunnels                         |
|    tunnel_XXXX -> ChatGPT connector/plugin        |
+---------------------------------------------------+
```

- Dependencies: `Pillow`, `moderngl` + `pyopengltk` (Windows GPU logo; optional at runtime with automatic Canvas fallback)
- Full test suite runs on every push — see the CI badge above
- CI on Windows, Ubuntu, and macOS

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide (Thai)](docs/USER-GUIDE.md) | Full walkthrough in Thai |
| [User Guide (English)](docs/USER-GUIDE-EN.md) | Full walkthrough in English |
| [Install Guide](INSTALL.md) | Step-by-step installation |
| [Project Plan](PROJECT-PLAN.md) | Product vision and architecture |
| [Cross-Platform Plan](docs/plans/cross-platform-plan.md) | macOS/Linux/RPi/Umbrel roadmap |
| [Agent Harness Accelerator](docs/plans/2026-08-28-sunday-family-agent-harness-accelerator.md) | Multi-model routing/dispatch roadmap |
| [Worker Auto-Fallback + GLM-5.3 Benchmark](docs/plans/2026-08-28-worker-auto-fallback-and-glm-benchmark.md) | Lease broker, fallback policy, delegation benchmark |
| [Privacy Policy](PRIVACY.md) | Data handling (local-only) |
| [Security Policy](SECURITY.md) | Vulnerability reporting |
| [License](LICENSE) | MIT |

## Data and Secrets

| Data | Location |
|------|----------|
| Application database | `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` |
| Tunnel IDs | Private Drive layer (`secrets/a-conductor-tunnels.md`) |
| Connector backups | Private Drive layer (`backups/a-conductor-instances/`) |

## Development

```bash
python -m pip install -e .[test]
python -m pytest tests/ -q
python -m a_conductor --smoke
python scripts/build_portable.py
python scripts/build_installer.py
```

## Credits

A-Sunday Conductor uses [Serena](https://github.com/oraios/serena) (MIT License) as its internal semantic code engine. The management interface, installer, and control plane are A-Sunday Conductor's own.

## Support This Project

If this tool is useful to you, consider supporting its development:

[![Sponsor on GitHub](https://img.shields.io/badge/sponsor-GitHub-ea4aaa?style=for-the-badge&logo=github)](https://github.com/sponsors/aase7en)

**Thai residents:** PromptPay and TrueWallet accepted — see [DONATE.md](.github/DONATE.md) for details.

---

<div align="center">

**A** — the AI co-developer | **Sunday** — dedicated to the family | **Conductor** — the founding codename

[Report Bug](https://github.com/aase7en/A-Wiki-Conductor/issues) | [Request Feature](https://github.com/aase7en/A-Wiki-Conductor/issues) | [Sponsor](https://github.com/sponsors/aase7en) | [Donate (TH)](.github/DONATE.md)

</div>
