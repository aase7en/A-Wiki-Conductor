# A-Sunday Conductor — User Guide (English)

Latest: 2026-08-22 (v0.3.0) · Supported OS: **Windows 10/11** (full features) · Python 3.11+ (developer install)

---

## 1. Where the program lives

The program is this repository (`A-Wiki-Conductor`) — a **pure desktop app**: no web server, no internet needed to run the UI (online only for GitHub push/pull).

| Form | How to open |
|---|---|
| Developer install (recommended now) | Open a terminal in the repo folder and type `a-conductor` |
| Portable single file | Run `A-Sunday Conductor.exe` built with PyInstaller (see §6) |

## 2. First-time setup (fork/clone)

```powershell
git clone https://github.com/aase7en/A-Wiki-Conductor.git
cd A-Wiki-Conductor
python -m pip install -e .[test]
a-conductor          # opens the app
```

Verify: `a-conductor --smoke` → must print `A-CONDUCTOR_SMOKE_OK projects=0 workers=3`

## 3. The main screen

```
┌ A-SUNDAY CONDUCTOR v0.3.0                   [Guide] [Settings]  ● ONLINE ┐
├ PROJECTS (left) │ WORKERS (right) — WORKER/STATE/PROJECT/PATH table
│                 │  Buttons: Add Project / Assign / Activate / Release / Refresh
│                 │        Start / Stop / Restart / Setup / Config / + Worker / Rename / Delete
├ CONNECTORS — INSTANCE / PORT / STATE / PROJECT / TUNNEL / AUTO
│  Buttons: Start / Stop / Start All / Toggle Auto / Rescan / + Connector / Rename / Delete
│        Set Tunnel ID / Change Project / Brain folders / Check engine updates
├ MONITOR — state/PID/memory/live log tail of the selected connector (auto-refresh)
└ ACTIVITY / LOG — every command is recorded
```

**Status colors**: green = READY · yellow = STARTING/BUSY/STOPPING · red = ERROR · gray = STOPPED/empty

**Handy everywhere**: hover a table row → dark tooltip shows the full path; right-click → Copy path; tables scroll horizontally; the window title always shows the version.

## 4. Everyday use

### 4.1 Manage projects & workers (Control Center)
1. **Add Project** → pick a project folder (registering *never touches* files inside it)
2. Click a project (left) + a worker (right) → **Assign**
3. **Start/Stop/Restart** control that worker's lifecycle

### 4.2 Engine config per worker (Config button)
Select a worker → **Config** → edit:
- **Language backend**: LSP or JetBrains
- **Tool timeout**: seconds per tool call
- **Excluded / Included / Fixed tools**: toggle tool sets (hover any checkbox for a one-line explanation)
- **Base modes**: checkbox grid (hover for what each mode does)
- Saved values take effect on the worker's *next start*

### 4.3 Manage ChatGPT connectors (CONNECTORS)
- The app **auto-discovers** from `C:\AI\serena-instances\*` (reads each one's `instance.ps1`)
- **Start / Stop / Start All / Toggle Auto / Rescan** as labeled
- **+ Connector**: create a new connector from the validated template (name + project + optional Tunnel ID; port auto-assigned; the CMD window is titled the next `Sunday-works N`)
- **Rename / Delete**: rename the display alias only (folder untouched) / safe delete (stops first, zips a backup to the A-Wiki-Data Drive layer, then removes)
- Selecting a row fills the **MONITOR** panel: state, PID, memory, error count, last log lines

### 4.3.1 One API key, many tunnels (parallel chats)

**Yes — one OpenAI account/API key can own several tunnels.** Each tunnel = one connector = one parallel ChatGPT chat lane.

To add a chat lane:
1. Create a new tunnel in the **OpenAI Platform (web)** — name it like the plugin you will create
2. In the app press **+ Connector** → name + project path + paste the Tunnel ID → Create
3. Press **Start** until READY (no Tunnel ID yet? set it later with the **Set Tunnel ID** button)
4. In ChatGPT → create the connector/plugin for that tunnel — **only while the connector is READY**, otherwise creation fails

### 4.3.2 One chat, several workers

**Yes — one chat can enable several connectors at once.** Each points to a different Sunday-Worker, so one chat can drive multiple projects.

Caveats: more tokens and possible context mixing — best when a task truly needs two projects. For everyday work prefer **one chat = one main worker** and enable extras on demand.

### 4.4 Activate a project in an AI chat
1. Select the project in **PROJECTS**
2. Press **Activate** → a standard Serena prompt (with the project path) is copied
3. Paste it into the AI chat connected to Serena

> The button only copies text — the app never activates Serena on the agent's behalf or edits project files.

### 4.5 Guide + Settings + language
Top-right: **Guide** opens this guide (language follows the app language). **Settings** has: **supervised mode**, **stop-all-connectors-on-exit** (default ON — closing the app stops every connector and reaps stale processes), and **Language / ภาษา** (Thai ↔ English; takes full effect on next app start). The window title always carries the version, e.g. `A-Sunday Conductor v0.3.0`.

## 5. Where the data lives

- Default database: `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` (kept from the pre-rename name so upgrades preserve data)
- Override: `a-conductor --database D:\path\my.sqlite`
- Secrets & connector backups: the private Drive layer `L:\My Drive\A-Wiki-Data` (`secrets/a-conductor-tunnels.md`, `backups/a-conductor-instances/`)

## 6. Distribution (all local — no web service needed)

| Form | Audience | How |
|---|---|---|
| pip (dev) | Python users | `python -m pip install -e .[test]`, then `a-conductor` |
| Portable exe | everyone | `python scripts/build_portable.py` → `dist/A-Sunday Conductor.exe` |
| Setup installer | public | `python scripts/build_installer.py` → `dist/A-Sunday-Conductor-Setup.exe` (per-user, no admin: Start Menu + Desktop + Add/Remove entry; bundles both language guides + third-party notices) |

> SmartScreen note: the executables are not yet digitally signed — Windows may warn on first run: **More info → Run anyway** (normal for unsigned apps; code signing is on the roadmap).

## 7. What you must bring yourself
A Serena engine per connector and OpenAI tunnel IDs (created in the OpenAI Platform web UI). See the Thai guide §7 for the validated machine layout.

## 8. Troubleshooting
Every error popup explains itself in-app (missing prerequisite + how to fix). Deeper issues: check ACTIVITY / LOG and the MONITOR panel's log tail.

## 9. For developers
`python -m pytest tests/ -q` — the suite covers registry, connectors CRUD, i18n, installer, E2E and an adversarial bug-hunt set.

## Connecting other AI platforms
ChatGPT uses the tunnel system above. Claude / Codex / Grok / others: see the Thai guide's per-platform section (same pattern: expose Serena, point the platform at it).

## Credits

A-Sunday Conductor uses [Serena](https://github.com/oraios/serena) (MIT License) as its internal semantic code engine — full credit to the Serena team. The management UI, installer, and control plane are A-Sunday Conductor's own.
