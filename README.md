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

**Latest public release:** `v0.6.0` - Terminal Command Center + Real Monitor

**Current development version:** `0.7.0` - not released yet; stable publication remains gated by WO-P1-096 live connector TTL evidence.

**Current program state:** Sunday Family Multi-Model Agent Harness - **AHA-7A truthful provider operator read model is complete; WO125 provider operator read service is the active product frontier. Ultra pre-implementation review found no P0 and identified required P1/P2 contract hardening before source implementation.**

> Direction: one A-Sunday Conductor entry point recovers SSoT, routes only eligible worker/model/harness capacity, preserves durable claims/evidence, reviews and repairs results, and continues without human result copy/paste. `CONFIGURED != READY`, `READY != AUTHORIZED`, and agent `PASS` is evidence rather than merge authority.

### Delivery checklist

- [x] **v0.6.0 released** - terminal command center, real monitor, worker/connector management, Second Brain, installer/portable builds.
- [x] **AHA-0 / AHA-1 / AHA-2 / AHA-3** - capability vocabulary, provider/harness/trust/quota contracts, secure provider configuration, and bounded Claude Code harness.
- [x] **AHA-4 / 4A / 4B** - durable dispatch, supervised backend, atomic worker leasing/fallback, heartbeat and stale-owner recovery.
- [x] **AHA-5** - durable GPT <-> external-agent review/repair bridge with file-first no-copy-back results.
- [x] **AHA-6 / 6A / 6A.1 / 6B** - parallel READY execution, provider runtime assembly/admission, and policy-bounded elastic worker capacity.
- [x] **Post-AHA-6B safety gate** - provider admission lifetime, generation + trust/egress enforcement, output persistence safety, elastic fencing/recovery, and dispatch evidence binding (WO117/118/119/120/121).
- [x] **Loop Engineer protocol** - stable task/status/result destinations and bounded multi-agent lane rules (WO123).
- [x] **Stable external-agent mailbox** - constant per-agent machine-local prompt path with exact task/result authority and no human result copy-back (WO122).
- [x] **AHA-7A truthful provider read model** - configuration, runtime readiness, and task authorization are distinct; readiness/quota authority is reused and secret/endpoint values are excluded.
- [x] **Windows owned-process reliability hardening (WO129)** - bounded post-termination UNKNOWN re-observation without retrying termination or weakening MISMATCH/PID ownership safety.
- [ ] **AHA-7B - IN PROGRESS** - WO125 canonical provider snapshot/read service, then WO126 Settings display, WO127 bounded Edit/Disable/Test, and WO128 selection-reason/fallback observability through existing authorities only.
- [ ] **AHA-8** - additional providers one adapter at a time after AHA-7 contracts stabilize.

> **v0.7.0 release gate:** source already identifies as `0.7.0`, but GitHub Latest remains `v0.6.0`. Do not publish `v0.7.0` until WO-P1-096 proves hosted/remote MCP success after the relevant TTL on tunnel-client v0.0.13 with zero manual Start actions and completes final release E2E.

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
