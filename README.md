<div align="center">

<img src="assets/logo-face.png" alt="A-Sunday Conductor Logo" width="120" height="120" style="border-radius: 12px;" />

[![Release](https://img.shields.io/github/v/release/aase7en/A-Wiki-Conductor?style=flat-square&color=blue)](https://github.com/aase7en/A-Wiki-Conductor/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-1059%20passed-brightgreen?style=flat-square)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)]()
[![Sponsor](https://img.shields.io/badge/sponsor-GitHub-ea4aaa?style=flat-square&logo=github)](https://github.com/sponsors/aase7en)

</div>

# A-Sunday Conductor

**A local autonomous control plane for coordinating AI agents, coding agents, MCP servers, and memory.**

Pure desktop application. Python standard library only. No server. No cloud required.

---

## Overview

A-Sunday Conductor manages your AI coding agents through Serena MCP connectors. Each connector is a tunnel between ChatGPT and a local Serena instance bound to a specific project. One OpenAI API key supports multiple tunnels, enabling parallel chat sessions across different codebases.

## Key Features

| Feature | Description |
|---------|-------------|
| Connector fleet | Auto-discovers and manages Serena tunnel instances with health monitoring |
| One-click creation | Create new ChatGPT connectors with auto-assigned ports from validated templates |
| Live monitoring | Per-connector state, PID, memory usage, and log tail with 5-second refresh |
| Worker management | Dynamic worker slots (add, rename, delete) with no fixed limit |
| Engine configuration | Per-worker language backend, tool toggles, base modes, and timeouts |
| Second Brain | Inject brain rules from A-Wiki into every connector's system prompt |
| Project rebinding | Switch any connector's project without recreating it |
| Bilingual interface | Full Thai and English UI including tooltips and error messages |
| Clean shutdown | Closing the app stops all connectors and reaps stale processes |
| Drive backups | Connector deletion zips a backup to the A-Wiki-Data Google Drive layer |
| Update checking | In-app GitHub release checker with one-click download |

## Install

### Windows (recommended)

Download `A-Sunday-Conductor-Setup.exe` from [Releases](https://github.com/aase7en/A-Wiki-Conductor/releases) and run it. No admin rights required.

> If SmartScreen warns, click **More info > Run anyway**. This is normal for unsigned applications; code signing is pending.

### Portable

Download `A-Sunday-Conductor-Portable.exe` and run from anywhere.

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

- Python standard library only (zero external dependencies)
- 1010 tests (unit, integration, E2E, adversarial)
- CI on Windows, Ubuntu, and macOS

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide (Thai)](docs/USER-GUIDE.md) | Full walkthrough in Thai |
| [User Guide (English)](docs/USER-GUIDE-EN.md) | Full walkthrough in English |
| [Install Guide](INSTALL.md) | Step-by-step installation |
| [Project Plan](PROJECT-PLAN.md) | Product vision and architecture |
| [Cross-Platform Plan](docs/plans/cross-platform-plan.md) | macOS/Linux/RPi/Umbrel roadmap |
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
