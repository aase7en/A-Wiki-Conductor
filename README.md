<div align="center">

# A-Sunday Conductor

**Local autonomous control plane for coordinating AI agents, coding agents, MCP servers, and A-Wiki memory.**

Pure desktop app · Python stdlib only · No server · No cloud · [Download](#-download--install)

</div>

---

## What it does

A-Sunday Conductor is a **Windows desktop app** (macOS/Linux groundwork in progress) that manages your AI coding agents through **Serena MCP connectors**:

| Capability | Description |
|---|---|
| 🔌 **Connector fleet** | Auto-discovers and manages Serena tunnel instances — start/stop/restart, health monitoring, auto-start on app open |
| ➕ **Create connectors** | One click to create a new ChatGPT connector (name + project + Tunnel ID) — port auto-assigned, template-generated |
| 📊 **Live MONITOR** | Per-connector state, PID, memory, log tail — auto-refresh every 5s, no CMD windows needed |
| 👥 **Worker slots** | Add / rename / delete worker slots dynamically (no fixed 3-slot limit) |
| ⚙️ **Engine config** | Per-worker language backend, tool toggles, base modes, timeouts — every checkbox has a hover explanation |
| 🧠 **Second Brain** | Inject brain rules (A-Wiki) into every connector's system prompt |
| 🔀 **Project rebind** | Switch a connector's project without recreating it |
| 🌐 **Bilingual UI** | Thai ↔ English, including error popups, config tooltips, and the user guide |
| 🚪 **Clean exit** | Closing the app stops all connectors and reaps stale processes |
| 💾 **Drive backups** | Connector deletion zips a backup to the A-Wiki-Data Google Drive layer |

## Download & Install

### For most users (Windows 10/11)

1. Go to **[Releases](https://github.com/aase7en/A-Wiki-Conductor/releases)**
2. Download `A-Sunday-Conductor-Setup.exe`
3. Run it — if SmartScreen warns, click **More info → Run anyway** (normal for unsigned apps)
4. The app appears in your Start Menu as **A-Sunday Conductor**

> No admin rights needed — installs to `%LOCALAPPDATA%\Programs\A-Sunday Conductor\`

### Portable (no install)

Download `A-Sunday-Conductor-Portable.exe` and run it from anywhere.

### For developers (pip)

```bash
git clone https://github.com/aase7en/A-Wiki-Conductor.git
cd A-Wiki-Conductor
python -m pip install -e .[test]
a-conductor        # opens the app
```

## Quick start (3 steps)

```
① Add Project → ② select + Assign to a Worker → ③ press Start
```

For ChatGPT connectors:
```
① Create tunnel in OpenAI Platform → ② press + Connector in the app → ③ Start → ④ create plugin in ChatGPT
```

Full walkthrough: the **Guide** button inside the app (Thai or English).

## The connector fleet

Each connector = one tunnel = one parallel ChatGPT chat lane. One OpenAI API key can own multiple tunnels.

| Convention | Meaning |
|---|---|
| `Sunday-Worker-N` / port `1801N` | System name (N = 1, 2, 3, …) |
| `Sunday-works N - <Name>` | CMD window title |
| `SunDay-Worker N-Conduct` | Display name (matches your ChatGPT plugin) |

Connectors are **not locked to projects** — use the **เปลี่ยนโปรเจกต์ / Change Project** button to rebind any connector to a different project.

## Architecture

```
┌─────────────────────────────────────────────────┐
│ A-Sunday Conductor (desktop app, Tk)             │
│  ├── PROJECTS / WORKERS / CONNECTORS / MONITOR  │
│  └── SQLite (registry, settings, preferences)   │
├─────────────────────────────────────────────────┤
│ Connector instances (validated per-folder)       │
│  sunday-worker-N/  →  instance.ps1 + scripts   │
│  └── Serena engine (MCP server per connector)  │
├─────────────────────────────────────────────────┤
│ OpenAI Secure MCP Tunnels (one per connector)    │
│  tunnel_XXXX → ChatGPT connector/plugin        │
└─────────────────────────────────────────────────┘
```

- **Python stdlib only** — zero external dependencies
- **~1000 tests** — unit, integration, E2E, adversarial bug-hunt
- **CI on 3 OS** — Windows, Ubuntu, macOS

## Documentation

- [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md) — คู่มือภาษาไทย (also bundled in the app)
- [`docs/USER-GUIDE-EN.md`](docs/USER-GUIDE-EN.md) — English user guide
- [`PROJECT-PLAN.md`](PROJECT-PLAN.md) — authoritative product vision & architecture
- [`docs/plans/cross-platform-plan.md`](docs/plans/cross-platform-plan.md) — macOS/Linux/RPi/Umbrel roadmap
- [`docs/adr/ADR-0001-mcp-gateway-deferred.md`](docs/adr/ADR-0001-mcp-gateway-deferred.md) — MCP gateway decision record

## Data & secrets

| What | Where |
|---|---|
| App database | `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` |
| Tunnel IDs (secrets) | `L:\My Drive\A-Wiki-Data\secrets\a-conductor-tunnels.md` (private Drive layer) |
| Connector backups | `L:\My Drive\A-Wiki-Data\backups\a-conductor-instances\` (auto-synced) |

## Development

```bash
python -m pip install -e .[test]
python -m pytest tests/ -q        # ~1000 tests
python -m a_conductor --smoke     # headless smoke
python scripts/build_portable.py  # portable exe
python scripts/build_installer.py # setup installer
```

## Credits

A-Sunday Conductor uses [Serena](https://github.com/oraios/serena) (MIT License, Copyright (c) 2025 Oraios AI) as its internal semantic code engine. All user-facing tooling and branding are A-Sunday Conductor's own.

---

<div align="center">

**"A"** = the AI co-developer · **"Sunday"** = น้องซันเดย์ · **"Conductor"** = the founding codename

</div>
