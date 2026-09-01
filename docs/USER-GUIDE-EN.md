# A-Sunday Conductor — User Guide (English)

Latest: 2026-08-26 (v0.7.0) · Supported OS: **Windows 10/11** (full features) · Python 3.11+ (developer install)

---

## Glossary (read this first if the terms are new)

| Term | What it means (plain English) |
|---|---|
| **Project** | A folder on your computer with code/files — the "workspace" the AI will work in |
| **Connector** | The local Serena/MCP endpoint behind one ChatGPT tunnel lane — each has a name, port, Tunnel ID and **Bound Project** launch/config binding |
| **Tunnel ID** | The bridge's password (starts with `tunnel_` + 32 characters) — created on OpenAI Platform, pasted into the app |
| **Worker** | A logical scheduler/CRUD slot. It lives in the **Scheduler Registry [Advanced]** and is not the same thing as live connector health |
| **Serena** | The internal program that acts as the AI's "hands" — lets it read/edit project files |
| **MCP** | The protocol standard that lets AI call tools (read files, run commands) |
| **Plugin** | What you create in ChatGPT to connect to a Tunnel — you name it yourself (e.g. Sunday-Worker-1) |
| **Port** | A door number (e.g. 18011) each Connector uses for local communication — unique per connector |
| **Second Brain** | Knowledge/rules/memory the AI must read before working — e.g. A-Wiki's AGENTS.md |
| **Active Project** | The most recent project Serena actually activated in that connector runtime. `UNKNOWN` means there is no trustworthy activation evidence yet |
| **Instance** | Another name for Connector (used interchangeably) — one bridge setup in `C:\AI\serena-instances\` |

---

## How everything connects

```
┌─────────────────── ChatGPT (internet side) ────────────────────┐
│                                                                │
│   Chat 1 [Plugin: Sunday-Worker-1] ──── Tunnel ID: tunnel_abc │
│   Chat 2 [Plugin: Sunday-Worker-2] ──── Tunnel ID: tunnel_def │
│   Chat 3 [Plugin: Sunday-Worker-3] ──── Tunnel ID: tunnel_ghi │
│                                                                │
└──────┬──────────────────┬──────────────────┬───────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─── A-Sunday Conductor (on your computer) ──────────────────────┐
│                                                                │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐           │
│  │ Connector 1 │   │ Connector 2 │   │ Connector 3 │           │
│  │ :18011     │   │ :18012     │   │ :18013     │           │
│  │ tunnel_abc │   │ tunnel_def │   │ tunnel_ghi │           │
│  └──────┬─────┘   └──────┬─────┘   └──────┬─────┘           │
│         │                │                │                   │
│         ▼                ▼                ▼                   │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐           │
│  │ Project A  │   │ Project B  │   │ Project C  │           │
│  │ A:\GitHub\ │   │ A:\GitHub\ │   │ A:\GitHub\ │           │
│  │ my-app     │   │ other-app  │   │ third-app  │           │
│  └────────────┘   └────────────┘   └────────────┘           │
│                                                                │
│  Key rule: 1 Plugin = 1 Tunnel ID = 1 Connector lane         │
│  Change project = press "Change Project" then Stop → Start    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## First-time setup (5 steps)

| Step | What to do | Button |
|---|---|---|
| 1 | Open the app → Setup Wizard opens automatically | (automatic) |
| 2 | Install everything the Wizard asks (uv, Python, Serena, tunnel-client) | [Next] through steps |
| 3 | Create a Tunnel ID on OpenAI Platform (Settings → Tunnels → New) | Click link from Wizard |
| 4 | Enter connector name + pick project folder + paste Tunnel ID | Wizard final step |
| 5 | Go to ChatGPT → create a Plugin pointing to your Tunnel | In browser |

## Daily use (3 steps)

| Step | What to do | Button |
|---|---|---|
| 1 | Open the app → check **AI EXECUTION SLOTS — LIVE**: CONNECTION should be READY; inspect ACTIVE PROJECT / BOUND PROJECT / [DRIFT] | In app |
| 2 | Go to ChatGPT → open the chat with that Plugin | In browser |
| 3 | Chat with the AI — it sees your project through the Connector | (chat) |

## Add a new chat (4 steps)

| Step | What to do | Button |
|---|---|---|
| 1 | Create a new Tunnel ID on OpenAI Platform | In browser |
| 2 | Click `+ Add Connector` in the CONNECTORS table (or the `+ Add` row if empty) | In app |
| 3 | Enter name + pick project + paste Tunnel ID → Save | In dialog |
| 4 | Go to ChatGPT → create a new Plugin pointing to that Tunnel ID | In browser |

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
┌ A-SUNDAY CONDUCTOR v0.7.0                   [Guide] [Settings]  ● ONLINE ┐
├ PROJECTS — register/select the project folder you want to work with
├ AI EXECUTION SLOTS — LIVE
│  SLOT / CONNECTION / ACTIVE PROJECT / BOUND PROJECT / LAST SWITCH / PORT / TUNNEL / AUTO
│  [DRIFT] = Active Project differs from the connector's Bound Project
├ SCHEDULER REGISTRY [ADVANCED] — logical Worker CRUD/scheduler state; hidden by default
├ MONITOR — state/PID/memory/live log tail of the selected connector (auto-refresh)
└ ACTIVITY / LOG — every command is recorded
```

**Status colors**: green = READY · yellow = STARTING/BUSY/STOPPING · red = ERROR · gray = STOPPED/empty

**Handy everywhere**: hover a table row → dark tooltip shows the full path; right-click → Copy path; tables scroll horizontally; the window title always shows the version.

## 4. Everyday use

### 4.1 Manage projects & workers (Control Center)
1. **Add Project** → pick a project folder (registering *never touches* files inside it)
2. Use **AI EXECUTION SLOTS — LIVE** for day-to-day connector/runtime truth.
3. Expand **Scheduler Registry [Advanced]** only when you need logical Worker assignment/CRUD/configuration.
4. Worker lifecycle and Connector lifecycle are different actors; button labels name which one they control.

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
Top-right: **Guide** opens this guide (language follows the app language). **Settings** has: **supervised mode**, **stop-all-connectors-on-exit**, **Language**, and a read-only **MODELS & AGENTS** status panel. The provider panel refreshes asynchronously and shows configured/ready/authorization, health, trust/egress, generation, model/harness, quota, safe provenance, and observation age without displaying endpoint or credential values. **Refresh** is manual in this first slice. The window title always carries the version, e.g. `A-Sunday Conductor v0.7.0`.

### 4.6 Hand-holding: which chat is which connector / port / project?

**Key fact:** the plugin name you set inside ChatGPT (e.g. `Sunday-Worker-1..5`) lives only on OpenAI's side — this app never sees or binds to that name. What actually links a chat to your machine is the plugin's **Tunnel ID**.

The real chain:

```
ChatGPT chat → plugin carries a Tunnel ID → on this machine: the matching connector + PORT
→ connector starts with a BOUND PROJECT → Serena may activate a different ACTIVE PROJECT during the chat
```

Rule to remember: **one plugin = one connector lane**, not one permanently fixed project. **BOUND PROJECT** is the connector launch/config binding. **ACTIVE PROJECT** is what Serena actually activated in the running session; `ACTIVE PROJECT [DRIFT]` means it differs from the binding. Changing the Bound Project requires connector edit + restart, while using **Copy Activate** in a connected chat can change the runtime Active Project without pretending the binding changed.

Step-by-step "which row is this chat?":

1. In ChatGPT, open the plugin/connector settings and copy its **Tunnel ID**.
2. In this app check the CONNECTORS table's **TUNNEL** column — each row shows the **last 4 characters of its Tunnel ID** (e.g. `...e3f1`) so you can match it against the ID shown in ChatGPT instantly (the full ID is treated as a secret and never displayed). Press **Edit** on the row to see "current: ...xxxx" and change the ID there.
3. Once matched: read the **AI EXECUTION SLOTS — LIVE** row: **CONNECTION**, **ACTIVE PROJECT**, **BOUND PROJECT**, **PORT**, masked **TUNNEL**, and **LAST SWITCH** are shown together.
4. If you see **[DRIFT]**, Active Project differs from Bound Project. Treat that as explicit evidence, not automatically as an error: decide whether the chat intentionally activated another project.

   > In short: AI EXECUTION SLOTS is the operator view of live connector/runtime truth. **Scheduler Registry [Advanced]** is the logical work-scheduling/CRUD view and is intentionally hidden by default.
5. To change the connector's default binding to project B: edit that connector's Bound Project → **Stop Connector** → **Start Connector**. To work temporarily in B in the current connected chat, use **Copy Activate** for B and verify ACTIVE PROJECT / [DRIFT] in the live slot.

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
